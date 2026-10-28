#!/usr/bin/env python3
"""Offline safety tests; no Xcode, credentials, registry writes, or GitHub calls."""

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location("swift_release", Path(__file__).with_name("swift_release.py"))
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


class SwiftReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        subprocess.run(["git", "init", "--quiet", str(self.root)], check=True)
        self.write("Cargo.toml", '[package]\nname = "sia_storage_sdk"\nversion = "1.2.3"\n')
        self.write("Cargo.lock", "# locked dependencies\n")
        self.write("SiaStorageSDK.podspec", "s.version = '1.2.3'\n")
        self.write("Package.swift", 'url: "https://github.com/SiaFoundation/sia-storage-sdk/releases/download/v1.2.3/SiaStorageSDKFFI-1.2.3.xcframework.zip",\nchecksum: "' + "0" * 64 + '"\n')
        self.write("src/lib.rs", "// Rust FFI\n")
        self.write("swift/Sources/SiaStorageSDK/SiaStorageSDK.swift", "// Generated bindings\n")
        self.write(".github/placeholder", "")
        self.write("build/SiaStorageSDKFFI.xcframework.zip", "exact prebuilt archive bytes")
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)

    def write(self, path, content):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)

    def prepare(self):
        return release.prepare(self.root, 123456, 2)

    def mutate_metadata(self, **changes):
        path = self.root / release.METADATA
        data = json.loads(path.read_text())
        data.update(changes)
        path.write_text(json.dumps(data))

    def test_prepare_and_verify_preserve_exact_archive(self):
        data = self.prepare()
        self.assertEqual(release.verify(self.root), data)
        self.assertEqual(data["artifact_name"], "swift-release-123456-2")
        self.assertEqual(data["sha256"], hashlib.sha256(b"exact prebuilt archive bytes").hexdigest())
        self.assertEqual((self.root / release.RELEASE_DIR / data["archive"]).read_bytes(),
                         (self.root / "build/SiaStorageSDKFFI.xcframework.zip").read_bytes())

    def test_rebuilt_archive_is_rejected(self):
        data = self.prepare()
        self.write(str(release.RELEASE_DIR / data["archive"]), "rebuilt archive with different zip timestamps")
        with self.assertRaisesRegex(ValueError, "checksum"):
            release.verify(self.root)

    def test_changed_rust_input_is_rejected(self):
        self.prepare()
        self.write("src/lib.rs", "// new source merged after release PR preparation\n")
        with self.assertRaisesRegex(ValueError, "inputs changed"):
            release.metadata(self.root)

    def test_new_tracked_source_is_rejected(self):
        self.prepare()
        self.write("swift/Sources/SiaStorageSDK/New.swift", "// New API\n")
        subprocess.run(["git", "-C", str(self.root), "add", "swift"], check=True)
        with self.assertRaisesRegex(ValueError, "inputs changed"):
            release.metadata(self.root)

    def test_changed_generated_bindings_are_rejected(self):
        self.prepare()
        self.write("swift/Sources/SiaStorageSDK/SiaStorageSDK.swift", "// Stale generated bindings\n")
        with self.assertRaisesRegex(ValueError, "inputs changed"):
            release.metadata(self.root)

    def test_deleted_tracked_source_is_rejected(self):
        self.prepare()
        subprocess.run(["git", "-C", str(self.root), "rm", "-f", "src/lib.rs"], check=True, capture_output=True)
        with self.assertRaisesRegex(ValueError, "inputs changed"):
            release.metadata(self.root)

    def test_symlink_source_is_rejected_without_following(self):
        self.prepare()
        source = self.root / "src/lib.rs"
        source.unlink()
        source.symlink_to("../Cargo.toml")
        with self.assertRaisesRegex(ValueError, "regular tracked file"):
            release.metadata(self.root)

    def test_unrelated_changelog_does_not_invalidate_build(self):
        data = self.prepare()
        self.write("CHANGELOG.md", "Release notes updated\n")
        subprocess.run(["git", "-C", str(self.root), "add", "CHANGELOG.md"], check=True)
        self.assertEqual(release.verify(self.root), data)

    def test_changed_manifest_checksum_is_rejected(self):
        self.prepare()
        path = self.root / "Package.swift"
        path.write_text(path.read_text().replace(release.metadata(self.root)["sha256"], "f" * 64))
        with self.assertRaisesRegex(ValueError, "checksum differs"):
            release.metadata(self.root)

    def test_changed_podspec_version_is_rejected(self):
        self.prepare()
        self.write("SiaStorageSDK.podspec", "s.version = '1.2.4'\n")
        with self.assertRaisesRegex(ValueError, "CocoaPods version"):
            release.metadata(self.root)

    def test_archive_path_in_metadata_cannot_escape_staging(self):
        self.prepare()
        self.mutate_metadata(archive="../../other.zip")
        with self.assertRaisesRegex(ValueError, "archive name"):
            release.metadata(self.root)

    def test_invalid_run_id_is_rejected(self):
        self.prepare()
        self.mutate_metadata(run_id="123456\nforged_output=true")
        with self.assertRaisesRegex(ValueError, "run ID"):
            release.metadata(self.root)

    def test_bad_cocoapods_checksum_is_rejected(self):
        self.prepare()
        self.write(str(release.RELEASE_DIR / "CHECKSUMS.txt"), "wrong checksum")
        with self.assertRaisesRegex(ValueError, "CHECKSUMS.txt"):
            release.verify(self.root)

    def test_missing_archive_fails_closed(self):
        data = self.prepare()
        (self.root / release.RELEASE_DIR / data["archive"]).unlink()
        with self.assertRaisesRegex(ValueError, "missing or expired"):
            release.verify(self.root)

    def test_extra_release_asset_fails_closed(self):
        self.prepare()
        self.write(str(release.RELEASE_DIR / "stale-version.zip"), "old artifact")
        with self.assertRaisesRegex(ValueError, "extra files"):
            release.verify(self.root)


if __name__ == "__main__":
    unittest.main()
