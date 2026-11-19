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

    def render(self, template, *args, expect_error=False):
        result = subprocess.run(
            [CHEZMOI, "--config", str(self.config), "--source", str(ROOT),
             "--persistent-state", str(self.root / "state.boltdb"),
             "execute-template", *args],
            input=template, env=self.env, capture_output=True, text=True, timeout=20,
        )
        if expect_error:
            self.assertNotEqual(result.returncode, 0)
            return result.stderr
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

    def test_local_options_records_nix_system(self):
        self.config.write_text('[data]\nmachine_username = "tester"\nis_desktop = true\ngit_username = "test"\ngit_email = "test@example.com"\n')
        template = (ROOT / "dot_config/nix/local-input/default.nix.tmpl").read_text()
        for os_name in ("linux", "darwin"):
            for arch, nix_arch in (("amd64", "x86_64"), ("arm64", "aarch64")):
                with self.subTest(os=os_name, arch=arch):
                    prefix = '{{ $_ := set .chezmoi "os" "' + os_name + '" }}{{ $_ := set .chezmoi "arch" "' + arch + '" }}'
                    rendered = self.render(prefix + template)
                    self.assertIn('system = "' + nix_arch + '-' + os_name + '";', rendered)
                    self.assertIn('username = "tester";', rendered)
                    self.assertIn('isDesktop = true;', rendered)

    def profile_config(self, profiles, *, wsl=False, custom=True, desktop=True):
        self.config.write_text(
            '[data]\nmachine_username = "tester"\ngit_username = "test"\ngit_email = "test@example.com"\n'
            + 'is_desktop = ' + str(desktop).lower() + '\nis_wsl = ' + str(wsl).lower() + '\n'
            + 'custom_nix_profiles = ' + str(custom).lower() + '\n'
            + 'nix_home_profiles = ' + json.dumps(profiles, ensure_ascii=False) + '\n'
        )

    def test_profile_checkbox_maps_label_to_id(self):
        result = self.render(
            (ROOT / ".chezmoi.toml.tmpl").read_text(), "--init",
            "--promptBool", "Install desktop GUI applications=true,Is this a WSL environment=false,Home Managerの追加機能を個別に選びますか=true",
            "--promptString", "Git username=test,Git email=test@example.com",
            "--promptChoice", "Setting PC Type=private_pc",
            "--promptMultichoice", "追加機能を選択（Space:切替 / Enter:確定 / 未選択:追加なし）=ゲーム環境（Minecraft・Heroic）",
        )
        data = tomllib.loads(result)["data"]
        self.assertTrue(data["custom_nix_profiles"])
        self.assertEqual(data["nix_home_profiles"], ["gui-apps", "gaming"])

    def test_platform_checkbox_choices(self):
        for platform, wsl, label, expected in (
            ("linux", True, "ゲーム環境（Minecraft・Heroic）", "gaming"),
            ("darwin", False, "macOS用ツール（Lima・skhd）", "darwin"),
        ):
            with self.subTest(platform=platform, wsl=wsl):
                self.config.write_text("")
                prefix = '{{ $_ := set .chezmoi "os" "' + platform + '" }}'
                result = self.render(
                    prefix + (ROOT / ".chezmoi.toml.tmpl").read_text(), "--init",
                    "--promptBool", "Install desktop GUI applications=true,Is this a WSL environment=" + str(wsl).lower() + ",Home Managerの追加機能を個別に選びますか=true",
                    "--promptString", "Git username=test,Git email=test@example.com",
                    "--promptChoice", "Setting PC Type=private_pc",
                    "--promptMultichoice", "追加機能を選択（Space:切替 / Enter:確定 / 未選択:追加なし）=" + label,
                )
                self.assertEqual(tomllib.loads(result)["data"]["nix_home_profiles"], ["gui-apps", expected])

    def test_saved_multiple_profiles_and_empty_selection_are_preserved(self):
        for profiles in (["gui-apps", "gaming"], []):
            with self.subTest(profiles=profiles):
                self.profile_config(profiles)
                result = self.render((ROOT / ".chezmoi.toml.tmpl").read_text(), "--init", "--promptChoice", "Setting PC Type=private_pc")
                self.assertEqual(tomllib.loads(result)["data"]["nix_home_profiles"], ["gui-apps"] + [p for p in profiles if p != "gui-apps"])

    def test_wsl_rejects_saved_physical_session_profile(self):
        for profile in ("hyprland", "recording"):
            with self.subTest(profile=profile):
                self.profile_config([profile], wsl=True)
                error = self.render((ROOT / ".chezmoi.toml.tmpl").read_text(), "--init", "--promptChoice", "Setting PC Type=private_pc", expect_error=True)
                self.assertIn("このOS・WSL・デスクトップ構成ではprofile", error)

    def test_darwin_rejects_saved_linux_profile(self):
        self.profile_config(["gaming"])
        error = self.render('{{ $_ := set .chezmoi "os" "darwin" }}' + (ROOT / ".chezmoi.toml.tmpl").read_text(), "--init", "--promptChoice", "Setting PC Type=private_pc", expect_error=True)
        self.assertIn("このOS・WSL・デスクトップ構成ではprofile", error)

    def test_gui_follows_desktop_answer_on_reinitialization(self):
        for desktop in (False, True):
            with self.subTest(desktop=desktop):
                # Saved gui-apps from an earlier answer is recomputed, not trusted.
                self.profile_config(["gui-apps", "gaming"], desktop=desktop)
                rendered = self.render((ROOT / ".chezmoi.toml.tmpl").read_text(), "--init", "--promptChoice", "Setting PC Type=private_pc")
                expected = (["gui-apps"] if desktop else []) + ["gaming"]
                self.assertEqual(tomllib.loads(rendered)["data"]["nix_home_profiles"], expected)

    def test_available_choices_follow_os_wsl_and_desktop(self):
        labels = {
            "hyprland": "Hyprlandデスクトップ・Waybar・壁紙・ロック",
            "gaming": "ゲーム環境（Minecraft・Heroic）",
            "recording": "録画環境（OBS・Hyprlandキー連携）",
            "darwin": "macOS用ツール（Lima・skhd）",
        }
        init_template = (ROOT / ".chezmoi.toml.tmpl").read_text()
        output_template = (ROOT / "dot_config/nix/local-input/default.nix.tmpl").read_text()
        for platform, wsl, desktop, expected in (
            ("linux", False, True, ["hyprland", "gaming", "recording"]),
            ("linux", True, True, ["gaming"]),
            ("linux", False, False, ["gaming"]),
            ("linux", True, False, ["gaming"]),
            ("darwin", False, True, ["darwin"]),
            ("darwin", False, False, ["darwin"]),
        ):
            prefix = '{{ $_ := set .chezmoi "os" "' + platform + '" }}'
            for profile, label in labels.items():
                with self.subTest(platform=platform, wsl=wsl, desktop=desktop, profile=profile):
                    if profile not in expected:
                        self.profile_config([profile], wsl=wsl, desktop=desktop)
                        for template in (init_template, output_template):
                            error = self.render(prefix + template, "--init", "--promptChoice", "Setting PC Type=private_pc", expect_error=True)
                            self.assertIn("このOS・WSL・デスクトップ構成ではprofile", error)
                        continue
                    self.config.write_text("")
                    rendered = self.render(
                        prefix + init_template, "--init",
                        "--promptBool", "Install desktop GUI applications=" + str(desktop).lower() + ",Is this a WSL environment=" + str(wsl).lower() + ",Home Managerの追加機能を個別に選びますか=true",
                        "--promptString", "Git username=test,Git email=test@example.com",
                        "--promptChoice", "Setting PC Type=private_pc",
                        "--promptMultichoice", "追加機能を選択（Space:切替 / Enter:確定 / 未選択:追加なし）=" + label,
                    )
                    profiles = (["gui-apps"] if desktop else []) + [profile]
                    self.assertEqual(tomllib.loads(rendered)["data"]["nix_home_profiles"], profiles)
                    # Use the actual init output, including its string is_desktop.
                    self.config.write_text(rendered)
                    output = self.render(prefix + output_template)
                    expected_list = "homeProfiles = [\n" + "".join(f'    "{p}"\n' for p in profiles) + "  ];"
                    self.assertIn(expected_list, output)

    def test_physical_session_requires_desktop_answer(self):
        self.profile_config(["hyprland"], desktop=False)
        for template in (".chezmoi.toml.tmpl", "dot_config/nix/local-input/default.nix.tmpl"):
            with self.subTest(template=template):
                error = self.render((ROOT / template).read_text(), "--init", "--promptChoice", "Setting PC Type=private_pc", expect_error=True)
                self.assertIn("このOS・WSL・デスクトップ構成ではprofile", error)

    def test_profile_export_and_legacy_compatibility(self):
        for custom, desktop, profiles in (
            (True, True, ["gui-apps", "gaming"]),
            (True, False, ["gui-apps", "gaming"]),
            (True, True, []),
            (True, False, []),
            (False, True, ["gaming"]),
        ):
            with self.subTest(custom=custom, desktop=desktop, profiles=profiles):
                self.profile_config(profiles, custom=custom, desktop=desktop)
                rendered = self.render((ROOT / "dot_config/nix/local-input/default.nix.tmpl").read_text())
                if shutil.which("nix-instantiate"):
                    result = subprocess.run(["nix-instantiate", "--eval", "--strict", "--json", "--expr", rendered], capture_output=True, text=True, check=True)
                    data = json.loads(result.stdout)
                    if custom:
                        self.assertEqual(data["homeProfiles"], (["gui-apps"] if desktop else []) + [p for p in profiles if p != "gui-apps"])
                    else:
                        self.assertNotIn("homeProfiles", data)
                else:
                    self.assertEqual("homeProfiles" in rendered, custom)
        self.config.write_text('[data]\nmachine_username = "tester"\nis_desktop = true\ngit_username = "test"\ngit_email = "test@example.com"\n')
        rendered = self.render((ROOT / "dot_config/nix/local-input/default.nix.tmpl").read_text())
        self.assertNotIn("homeProfiles", rendered)

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
