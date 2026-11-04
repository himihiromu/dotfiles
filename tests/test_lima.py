"""Check chezmoi migration and real Lima config merging without starting a VM."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CHEZMOI = shutil.which("chezmoi")
LIMACTL = shutil.which("limactl")


@unittest.skipUnless(CHEZMOI, "chezmoi must be installed")
class LimaTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lima-config-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / "chezmoi.toml"
        self.config.write_text("[data]\nis_desktop = false\n")
        self.chezmoi = [CHEZMOI, "--config", str(self.config),
                        "--persistent-state", str(self.root / "state.boltdb")]

    def run_command(self, args, **kwargs):
        result = subprocess.run(args, capture_output=True, text=True, timeout=30, **kwargs)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def yaml(self, content):
        return json.loads(self.run_command(
            self.chezmoi + ["execute-template", "--with-stdin",
                           "{{ .chezmoi.stdin | fromYaml | toJson }}"], input=content))

    def test_distribution_and_existing_default_migration(self):
        # Render the actual ignore rules for each OS, then let chezmoi apply them.
        for platform in ("darwin", "linux", "windows"):
            with self.subTest(platform=platform):
                source = self.root / platform / "source"
                source.mkdir(parents=True)
                shutil.copytree(ROOT / "dot_lima", source / "dot_lima")
                rendered = self.run_command(
                    self.chezmoi + ["execute-template"],
                    input='{{ $_ := set .chezmoi "os" "' + platform + '" }}'
                    + (ROOT / ".chezmoiignore").read_text())
                (source / ".chezmoiignore").write_text(rendered)
                home = self.root / platform / "home"
                target = home / ".lima/_config"
                target.mkdir(parents=True)
                previous = "provision:\n  - mode: user\n    script: '#!/bin/sh\\necho old'\n"
                (target / "default.yaml").write_text(previous)
                self.run_command(self.chezmoi + ["--source", str(source),
                    "--destination", str(home), "apply", "--force", "--exclude", "scripts"])
                if platform == "darwin":
                    self.assertIsNone(self.yaml((target / "default.yaml").read_text()))
                    self.assertEqual((target / "override.yaml").read_bytes(),
                                     (ROOT / "dot_lima/_config/override.yaml").read_bytes())
                else:
                    self.assertEqual((target / "default.yaml").read_text(), previous)
                    self.assertFalse((target / "override.yaml").exists())

    @unittest.skipUnless(LIMACTL, "limactl must be installed")
    def test_override_beats_conflicting_instance_settings(self):
        home = self.root / "lima"
        shutil.copytree(ROOT / "dot_lima/_config", home / "_config")
        env = dict(os.environ, LIMA_HOME=str(home))
        for arch in ("x86_64", "aarch64"):
            with self.subTest(arch=arch):
                instance = home / arch
                instance.mkdir()
                config = instance / "lima.yaml"
                config.write_text(f"""arch: {arch}
images:
- location: https://example.invalid/instance.img
  arch: {arch}
mounts:
- location: ~/Documents
  writable: false
- location: ~/ghq
  writable: false
- location: /tmp/lima
  writable: false
ssh:
  localPort: 60022
  loadDotSSHPubKeys: false
containerd:
  system: true
  user: true
provision:
- mode: user
  script: |
    #!/bin/sh
    echo instance-provision
portForwards:
- guestSocket: /run/user/{{{{.UID}}}}/docker.sock
  hostSocket: '{{{{.Dir}}}}/sock/wrong.sock'
""")
                merged = self.yaml(self.run_command(
                    [LIMACTL, "validate", "--fill", str(config)], env=env))
                image = next(i for i in merged["images"] if i["arch"] == arch)
                suffix = "amd64" if arch == "x86_64" else "arm64"
                self.assertEqual(image["location"],
                    "https://cloud-images.ubuntu.com/releases/noble/release/"
                    f"ubuntu-24.04-server-cloudimg-{suffix}.img")
                self.assertFalse(merged["containerd"]["system"])
                self.assertFalse(merged["containerd"]["user"])
                self.assertEqual(merged["ssh"]["localPort"], 60006)
                self.assertTrue(merged["ssh"]["loadDotSSHPubKeys"])
                mounts = {m["location"]: m for m in merged["mounts"]}
                for location in (str(Path.home() / "Documents"), str(Path.home() / "ghq"), "/tmp/lima"):
                    self.assertTrue(mounts[location]["writable"])
                # Old defaults must not duplicate the two global scripts/probe.
                self.assertEqual(len(merged["provision"]), 3)
                self.assertIn("instance-provision", merged["provision"][-1]["script"])
                self.assertEqual(len(merged["probes"]), 1)
                for item in merged["provision"] + merged["probes"]:
                    self.run_command(["bash", "-n"], input=item["script"])
                forwards = merged["portForwards"]
                self.assertEqual(len(forwards), 2)
                self.assertEqual(forwards[0]["guestSocket"],
                                 f'/run/user/{merged["user"]["uid"]}/docker.sock')
                # validate uses LIMA_HOME as the synthetic {{.Dir}}.
                self.assertEqual(forwards[0]["hostSocket"], str(home / "sock/docker.sock"))


if __name__ == "__main__":
    unittest.main()
