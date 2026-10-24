"""Render chezmoi templates and record bootstrap commands without applying Nix."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]
CHEZMOI = shutil.which("chezmoi")
SCRIPT = ROOT / ".chezmoiscripts/linux/run_after_once_05_nix_package_install.sh.tmpl"


@unittest.skipUnless(CHEZMOI, "chezmoi must be installed")
class NixBootstrapTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="nix-bootstrap-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home with spaces"
        self.home.mkdir()
        self.config = self.root / "chezmoi.toml"
        self.config.write_text("")
        self.env = dict(os.environ, HOME=str(self.home), USER="tester")

    def render(self, template, *args):
        result = subprocess.run(
            [CHEZMOI, "--config", str(self.config), "--source", str(ROOT),
             "--persistent-state", str(self.root / "state.boltdb"),
             "execute-template", *args],
            input=template, env=self.env, capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_independent_prompt_values(self):
        for desktop in (False, True):
            for wsl in (False, True):
                with self.subTest(desktop=desktop, wsl=wsl):
                    rendered = self.render(
                        (ROOT / ".chezmoi.toml.tmpl").read_text(), "--init",
                        "--promptBool", f"Install desktop GUI applications={str(desktop).lower()},Is this a WSL environment={str(wsl).lower()}",
                        "--promptString", "Git username=test,Git email=test@example.com",
                        "--promptChoice", "Setting PC Type=private_pc",
                    )
                    data = tomllib.loads(rendered)["data"]
                    self.assertEqual(data["is_wsl"], wsl)
                    self.assertEqual(str(data["is_desktop"]).lower(), str(desktop).lower())

    def test_non_linux_does_not_prompt_for_wsl(self):
        for platform in ("darwin", "windows"):
            with self.subTest(platform=platform):
                rendered = self.render(
                    '{{ $_ := set .chezmoi "os" "' + platform + '" }}'
                    + (ROOT / ".chezmoi.toml.tmpl").read_text(), "--init",
                    "--promptBool", "Install desktop GUI applications=true",
                    "--promptString", "Git username=test,Git email=test@example.com",
                    "--promptChoice", "Setting PC Type=private_pc",
                )
                self.assertIs(tomllib.loads(rendered)["data"]["is_wsl"], False)

    def bootstrap(self, distribution, desktop, wsl):
        data = f"[data]\nis_desktop = {str(desktop).lower()}\n"
        if wsl is not None:
            data += f"is_wsl = {str(wsl).lower()}\n"
        self.config.write_text(data)
        rendered = self.render(SCRIPT.read_text())
        os_release = self.root / "os-release"
        os_release.write_text(f"ID={distribution}\n")
        # Redirect only the OS identity file to a fixture; execute the real script.
        rendered = rendered.replace("/etc/os-release", str(os_release))
        subprocess.run(["bash", "-n"], input=rendered, text=True, check=True)
        log = self.root / "calls.json"
        bin_dir = self.root / "bin"
        bin_dir.mkdir(exist_ok=True)
        for name in ("sudo", "nix"):
            stub = bin_dir / name
            stub.write_text(
                f"#!{sys.executable}\nimport json, sys\nfrom pathlib import Path\n"
                f"Path({str(log)!r}).write_text(json.dumps(sys.argv))\n"
            )
            stub.chmod(0o755)
        result = subprocess.run(
            ["bash"], input=rendered,
            env=dict(self.env, PATH=f"{bin_dir}:{os.environ['PATH']}"),
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(log.read_text())

    def test_nixos_host_selection_ignores_desktop(self):
        for desktop in (False, True):
            for wsl in (False, True, None):
                with self.subTest(desktop=desktop, wsl=wsl):
                    call = self.bootstrap("nixos", desktop, wsl)
                    host = "nixos-wsl" if wsl else "nixos"
                    self.assertEqual(Path(call[0]).name, "sudo")
                    self.assertEqual(call[1:], [
                        "nixos-rebuild", "switch", "--flake",
                        f"github:himihiromu/my-nix-package-control#{host}",
                        "--override-input", "local-options",
                        f"path:{self.home}/.config/nix/local-input/default.nix",
                    ])

    def test_other_linux_uses_home_manager_even_on_wsl(self):
        for desktop in (False, True):
            for wsl in (False, True):
                with self.subTest(desktop=desktop, wsl=wsl):
                    call = self.bootstrap("ubuntu", desktop, wsl)
                    self.assertEqual(Path(call[0]).name, "nix")
                    self.assertEqual(call[1:], [
                        "run", "nixpkgs#home-manager", "--", "switch", "--flake",
                        "github:himihiromu/my-nix-package-control#myHomeConfig",
                        "--show-trace", "--override-input", "local-options",
                        f"path:{self.home}/.config/nix/local-input/default.nix",
                    ])


if __name__ == "__main__":
    unittest.main()
