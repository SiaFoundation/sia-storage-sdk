"""Exercise real Knope locally, without a remote or any release side effects."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[2]
KNOPE = shutil.which("knope")


@unittest.skipUnless(KNOPE, "knope is required for configuration integration tests")
class ReleaseConfigTests(unittest.TestCase):
    def test_release_preparation_and_dry_run(self):
        current = tomllib.loads((ROOT / "Cargo.toml").read_text())["package"]["version"]
        major, minor, patch = map(int, current.split("."))
        patch_version = f"{major}.{minor}.{patch + 1}"
        minor_version = f"{major}.{minor + 1}.0" if major else patch_version
        major_version = f"{major + 1}.0.0" if major else f"0.{minor + 1}.0"
        for bump, expected in (("patch", patch_version), ("minor", minor_version), ("major", major_version)):
            with self.subTest(bump=bump), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                config = tomllib.loads((ROOT / "knope.toml").read_text())
                for entry in config["package"]["versioned_files"]:
                    path = entry if isinstance(entry, str) else entry["path"]
                    destination = root / path
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(ROOT / path, destination)
                for path in ("knope.toml", "CHANGELOG.md"):
                    shutil.copyfile(ROOT / path, root / path)
                (root / ".changeset").mkdir()
                (root / ".changeset/test.md").write_text(f"---\ndefault: {bump}\n---\nTest release.\n")
                env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_TOKEN", "GH_TOKEN")}

                def run(*args):
                    return subprocess.run(args, cwd=root, env=env, check=True, text=True, capture_output=True).stdout

                run("git", "init", "-q")
                run("git", "config", "user.name", "Release Test")
                run("git", "config", "user.email", "test@example.invalid")
                run("git", "add", ".")
                run("git", "commit", "-qm", "fixture")
                original_pin = tomllib.loads((root / "Cargo.toml").read_text())["dependencies"]["sia_storage_ffi"]
                run(KNOPE, "prepare-release")
                cargo = tomllib.loads((root / "Cargo.toml").read_text())
                self.assertEqual(cargo["package"]["version"], expected)
                self.assertEqual(cargo["dependencies"]["sia_storage_ffi"], original_pin)
                lock = tomllib.loads((root / "Cargo.lock").read_text())
                self.assertEqual(next(p["version"] for p in lock["package"] if p["name"] == "sia_storage_sdk"), expected)
                for entry in config["package"]["versioned_files"]:
                    if isinstance(entry, str) or "regex" not in entry:
                        continue
                    patterns = entry["regex"]
                    for pattern in patterns if isinstance(patterns, list) else [patterns]:
                        matches = re.findall(pattern.replace("(?<version>", "(?P<version>"), (root / entry["path"]).read_text())
                        self.assertTrue(matches, entry["path"])
                        self.assertTrue(all(version == expected for version in matches), (entry["path"], matches))
                self.assertFalse((root / ".changeset/test.md").exists())
                self.assertIn(f"## {expected}", (root / "CHANGELOG.md").read_text())
                output = run(KNOPE, "release", "--dry-run")
                self.assertIn(f"tag v{expected}", output)
                self.assertEqual(run("git", "tag"), "")
                self.assertEqual(run("git", "remote"), "")


if __name__ == "__main__":
    unittest.main()
