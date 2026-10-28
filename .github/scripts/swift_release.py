#!/usr/bin/env python3
"""Bind a Swift release manifest to one immutable, prebuilt XCFramework archive.

Run prepare after versioning and building the release PR, then commit its output
and generated Swift sources. The merge workflow must download that run's exact
artifact, not rebuild it: zip timestamps alone can change the SwiftPM checksum.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tomllib


ROOT = Path(__file__).resolve().parents[2]
METADATA = Path(".github/swift-release.json")
RELEASE_DIR = Path("build/release")
SOURCE_FILES = {
    "Cargo.toml", "Cargo.lock", "Package.swift", "SiaStorageSDK.podspec",
    "build.rs", "rust-toolchain", "rust-toolchain.toml",
}
SOURCE_PREFIXES = ("src/", "swift/", ".cargo/")
SEMVER = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")
SHA256 = re.compile(r"[0-9a-f]{64}")


def release_version(root):
    version = tomllib.loads((root / "Cargo.toml").read_text())["package"]["version"]
    if not isinstance(version, str) or not SEMVER.fullmatch(version):
        raise ValueError("Swift releases require a stable major.minor.patch version")
    expected_url = (
        "https://github.com/SiaFoundation/sia-storage-sdk/releases/download/"
        f"v{version}/SiaStorageSDKFFI-{version}.xcframework.zip"
    )
    manifest = (root / "Package.swift").read_text()
    urls = re.findall(r'url:\s*"([^"]+\.xcframework\.zip)"', manifest)
    if urls != [expected_url]:
        raise ValueError("Package.swift binary URL does not match the shared release version")
    podspec = (root / "SiaStorageSDK.podspec").read_text()
    if re.findall(r"s\.version\s*=\s*'([^']+)'", podspec) != [version]:
        raise ValueError("The CocoaPods version does not match the shared release version")
    return version


def digest(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def source_fingerprint(root):
    """Reject a release PR whose Swift/Rust inputs changed after its build.

    Include the generated bindings and the checksum-bearing manifest. Git's
    tracked file list also catches newly added/deleted source files at merge.
    Changelogs and unrelated language/docs changes need not invalidate a build.
    """
    paths = subprocess.check_output(
        ["git", "-C", str(root), "ls-files", "--cached", "--full-name", "-z"]
    ).decode().split("\0")
    selected = sorted({
        path for path in paths
        if path in SOURCE_FILES or path.startswith(SOURCE_PREFIXES)
    })
    required = {"Cargo.toml", "Cargo.lock", "Package.swift", "SiaStorageSDK.podspec"}
    if not required.issubset(selected):
        raise ValueError("Required Swift release inputs are not tracked by Git")
    result = hashlib.sha256()
    for name in selected:
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Swift release input must be a regular tracked file: {name}")
        result.update(name.encode() + b"\0" + digest(path).encode() + b"\n")
    return result.hexdigest()


def prepare(root, run_id, run_attempt):
    if run_id <= 0 or run_attempt <= 0:
        raise ValueError("A positive GitHub Actions run ID and attempt are required")
    version = release_version(root)
    source = root / "build/SiaStorageSDKFFI.xcframework.zip"
    checksum = digest(source)
    manifest = root / "Package.swift"
    content, count = re.subn(
        r'checksum:\s*"[0-9a-fA-F]+"', f'checksum: "{checksum}"', manifest.read_text()
    )
    if count != 1:
        raise ValueError("Expected exactly one SwiftPM binary checksum in Package.swift")
    manifest.write_text(content)
    archive = f"SiaStorageSDKFFI-{version}.xcframework.zip"
    release_dir = root / RELEASE_DIR
    release_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, release_dir / archive)
    (release_dir / "CHECKSUMS.txt").write_text(f"{archive}: {checksum}\n")
    metadata = {
        "schema": 1,
        "version": version,
        "run_id": run_id,
        "run_attempt": run_attempt,
        "artifact_name": f"swift-release-{run_id}-{run_attempt}",
        "archive": archive,
        "sha256": checksum,
        "source_sha256": source_fingerprint(root),
    }
    (root / METADATA).write_text(json.dumps(metadata, indent=2) + "\n")
    return metadata


def metadata(root):
    if not (root / METADATA).is_file():
        raise ValueError("No prepared Swift artifact; regenerate the release PR before publishing")
    data = json.loads((root / METADATA).read_text())
    version = release_version(root)
    expected_keys = {
        "schema", "version", "run_id", "run_attempt", "artifact_name", "archive",
        "sha256", "source_sha256",
    }
    if not isinstance(data, dict) or set(data) != expected_keys or data["schema"] != 1:
        raise ValueError("Unsupported Swift release metadata")
    if any(type(data[key]) is not int or data[key] <= 0 for key in ("run_id", "run_attempt")):
        raise ValueError("Invalid Swift artifact workflow run ID or attempt")
    expected_artifact = f"swift-release-{data['run_id']}-{data['run_attempt']}"
    if data["version"] != version or data["artifact_name"] != expected_artifact:
        raise ValueError("Prepared Swift artifact does not match this release")
    if data["archive"] != f"SiaStorageSDKFFI-{version}.xcframework.zip":
        raise ValueError("Unexpected Swift release archive name")
    if any(not isinstance(data[key], str) or not SHA256.fullmatch(data[key])
           for key in ("sha256", "source_sha256")):
        raise ValueError("Invalid prepared Swift artifact checksum")
    checksums = re.findall(r'checksum:\s*"([0-9a-f]+)"', (root / "Package.swift").read_text())
    if checksums != [data["sha256"]]:
        raise ValueError("Package.swift checksum differs from the prepared artifact")
    if source_fingerprint(root) != data["source_sha256"]:
        raise ValueError("Swift/Rust source inputs changed; regenerate the release PR before publishing")
    return data


def verify(root):
    data = metadata(root)
    release_dir = root / RELEASE_DIR
    archive = release_dir / data["archive"]
    if not archive.is_file():
        raise ValueError("Prepared Swift archive missing or expired; regenerate the release PR, do not rebuild on merge")
    if digest(archive) != data["sha256"]:
        raise ValueError("Downloaded Swift archive checksum does not match Package.swift")
    if (release_dir / "CHECKSUMS.txt").read_text() != f"{data['archive']}: {data['sha256']}\n":
        raise ValueError("CocoaPods CHECKSUMS.txt does not match the prepared archive")
    if {path.name for path in release_dir.iterdir()} != {data["archive"], "CHECKSUMS.txt"}:
        raise ValueError("Unexpected extra files in the Swift release asset directory")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--run-id", type=int, required=True)
    prepare_parser.add_argument("--run-attempt", type=int, required=True)
    subparsers.add_parser("metadata")
    subparsers.add_parser("verify")
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            data = prepare(ROOT, args.run_id, args.run_attempt)
        elif args.command == "metadata":
            data = metadata(ROOT)
        else:
            data = verify(ROOT)
        # Safe, constrained values: callers may append these to GITHUB_OUTPUT.
        for key in ("version", "run_id", "run_attempt", "artifact_name"):
            print(f"{key}={data[key]}")
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as error:
        print(f"Swift release: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
