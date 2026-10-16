"""Exercise the installed mise CLI without invoking Nix or applying dotfiles."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MISE = shutil.which("mise")


@unittest.skipUnless(MISE, "mise must be installed")
class MiseTasksTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mise-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home with spaces"
        config = self.home / ".config/mise"
        config.mkdir(parents=True)
        shutil.copyfile(ROOT / "dot_config/mise/config.toml", config / "config.toml")
        self.cwd = self.root / "unrelated project/sub directory"
        self.cwd.mkdir(parents=True)
        self.log = self.root / "calls.json"
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        # All external commands used by the tasks are inert recording stubs.
        for name in ("nix", "sudo", "nixos-rebuild", "nix-store"):
            stub = bin_dir / name
            stub.write_text(
                f"#!{sys.executable}\n"
                "import json, os, sys\n"
                "from pathlib import Path\n"
                "Path(os.environ['TEST_LOG']).write_text(json.dumps({\n"
                " 'command': Path(sys.argv[0]).name, 'args': sys.argv[1:],\n"
                " 'cwd': os.getcwd(), 'tty': [os.isatty(i) for i in range(3)]}))\n"
                "sys.exit(int(os.environ.get('TEST_EXIT', '0')))\n"
            )
            stub.chmod(0o755)
        self.env = {
            "HOME": str(self.home),
            "XDG_CONFIG_HOME": str(self.home / ".config"),
            "XDG_CACHE_HOME": str(self.root / "cache"),
            "XDG_DATA_HOME": str(self.root / "data"),
            "XDG_STATE_HOME": str(self.root / "state"),
            "PATH": f"{bin_dir}:{Path(shutil.which('bash')).parent}:/usr/bin:/bin",
            "MISE_YES": "1",
            "MISE_OFFLINE": "1",
            "MISE_TASK_RUN_AUTO_INSTALL": "0",
            "TEST_LOG": str(self.log),
        }
        self.flake = str(self.home / "ghq/github.com/himihiromu/my-nix-package-control")

    def run_mise(self, *args, cwd=None, expected=0):
        self.log.unlink(missing_ok=True)
        result = subprocess.run(
            [MISE, *args], cwd=cwd or self.cwd, env=self.env,
            capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def call(self):
        return json.loads(self.log.read_text())

    def test_global_discovery_environment_and_cwd(self):
        for cwd in (self.cwd, self.home):
            for name in ("js", "python", "future-environment"):
                with self.subTest(cwd=cwd, name=name):
                    self.run_mise("develop", name, cwd=cwd)
                    self.assertEqual(self.call()["args"], ["develop", f"{self.flake}#{name}"])
                    self.assertEqual(self.call()["cwd"], str(cwd))

    def test_arguments_are_not_shell_code(self):
        name = "custom;$(touch SHOULD_NOT_EXIST)"
        args = ["--command", "printf", "%s", "two words", "", "*", "$(pwd)"]
        self.run_mise("develop", name, *args)
        self.assertEqual(self.call()["args"], ["develop", f"{self.flake}#{name}", *args])
        self.assertFalse((self.cwd / "SHOULD_NOT_EXIST").exists())

    def test_missing_or_empty_environment(self):
        for args in ((), ("",)):
            result = self.run_mise("develop", *args, expected=2)
            self.assertIn("usage: mise develop", result.stderr)
            self.assertFalse(self.log.exists())

    def test_nix_failure_is_forwarded(self):
        self.env["TEST_EXIT"] = "42"
        self.run_mise("develop", "not-defined", expected=42)
        self.assertEqual(self.call()["args"], ["develop", f"{self.flake}#not-defined"])

    @unittest.skipUnless(os.name == "posix", "PTY test requires Unix")
    def test_terminal_is_forwarded(self):
        import pty

        master, slave = pty.openpty()
        try:
            result = subprocess.run(
                [MISE, "develop", "js"], cwd=self.cwd, env=self.env,
                stdin=slave, stdout=slave, stderr=slave, timeout=20,
            )
            self.assertEqual(result.returncode, 0)
            self.assertEqual(self.call()["tty"], [True, True, True])
        finally:
            os.close(master)
            os.close(slave)

    def test_existing_tasks(self):
        local_options = f"path:{self.home}/.config/nix/local-input/default.nix"
        cases = [
            (["home-manager", "build", "--dry-run"], "nix",
             ["run", "nixpkgs#home-manager", "--", "build", "--flake", f"{self.flake}#myHomeConfig", "--show-trace", "--override-input", "local-options", local_options, "--dry-run"]),
            (["nis-darwin", "build"], "sudo",
             ["nix", "run", "nix-darwin", "--", "build", "--flake", f"{self.flake}#mac-config", "--override-input", "local-options", local_options]),
            (["nixos", "build", "macbook-air", "--dry-run"], "sudo",
             ["nixos-rebuild", "build", "--flake", f"{self.flake}#macbook-air", "--override-input", "local-options", local_options, "--dry-run"]),
            (["nixos", "build", "--dry-run"], "sudo",
             ["nixos-rebuild", "build", "--flake", self.flake, "--override-input", "local-options", local_options, "--dry-run"]),
            (["nix", "update", "--offline"], "nix", ["flake", "update", self.flake, "--offline"]),
            (["nix", "gc", "--print-dead"], "nix-store", ["--gc", "--print-dead"]),
            (["nix", "build", "example#package"], "nix", ["build", "example#package"]),
        ]
        for invocation, command, args in cases:
            with self.subTest(invocation=invocation):
                self.run_mise(*invocation)
                self.assertEqual(self.call()["command"], command)
                self.assertEqual(self.call()["args"], args)


if __name__ == "__main__":
    unittest.main()
