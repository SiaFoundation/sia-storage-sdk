# sia-storage-sdk

Language bindings for the [Sia Storage SDK](https://github.com/SiaFoundation/sia-sdk-rs), generated using [UniFFI](https://mozilla.github.io/uniffi-rs/).

## Supported Languages

- [Kotlin](kotlin/)
- [Python](python/)
- [Swift](swift/)

## Getting Started

See the [examples](examples/) directory for usage examples in each language.

## Changes and releases

Kotlin, Python, and Swift share one version, changelog, and `vX.Y.Z` release tag.
The Rust crate is the build helper; its version also supplies Python's dynamic
package version. `knope.toml` updates every binding's version and installation
example together. This preserves the existing lockstep version scheme.

For a user-facing change, install [Knope 0.22.2](https://knope.tech/installation/)
and run `knope document-change`, or add a uniquely named `.changeset/*.md`:

```markdown
---
default: patch
---

Describe the user-visible change across the affected bindings.
```

Use `patch`, `minor`, or `major` for the change's compatibility impact, not an
explicit next version. Knope follows pre-1.0 versioning: while the SDK is 0.x,
`major` advances the minor version and `minor`/`patch` advance the patch version.
Internal-only changes need no change file. PR CI validates every pending change
file and previews the next release without publishing anything.

Do not edit binding versions or release checksums in ordinary PRs, including
upstream SDK updates. Update the upstream revision and lockfile, regenerate
bindings as needed, and add changesets that preserve each upstream change's
compatibility classification. Existing changesets are retained until released.

### Maintainer workflow

1. Merging a change to `master` runs **Prepare Release**. With no pending change
   files it does nothing. Otherwise it updates versions/changelog, builds and
   tests the Swift XCFramework, records the exact ZIP's checksum, and opens or
   updates the bot-owned `release` PR. Normal Kotlin, Python, and Swift CI runs on
   that PR. The workflow can also be dispatched on `master` to recover a closed
   PR or failed preparation run.
2. Review the version, changelog, generated Swift sources, and checksum metadata,
   and wait for all build/test checks before merging. Do not manually edit or
   reuse the `release` branch; it is replaced with a fresh preparation.
3. Only merging that same-repository `release` PR creates a GitHub release, at
   the exact merge commit. It verifies the successful preparation run and
   source fingerprint, downloads its retained artifact, verifies both checksums,
   then lets Knope upload the ZIP and publish the root `vX.Y.Z` release. It never
   rebuilds the ZIP or pushes a checksum commit to `master`.
4. The published release triggers the existing tested Kotlin/Maven Central and
   Python/PyPI workflows. A Swift downstream smoke test installs the released
   version through Swift Package Manager. Swift's existing CocoaPods manifest
   and download layout remain compatible; this does not add a CocoaPods trunk
   publisher.

The artifact is retained for **90 days** (or a shorter repository retention
limit). Re-run Prepare Release **before merging** an old release PR so it gets a
fresh artifact. Missing/expired artifacts, source drift, or checksum mismatches
fail closed before a tag/release is created. If an expired or stale PR was already
merged, its changesets have been consumed: restore the release's change files (or
add a new patch changeset) in a new PR and prepare a fresh, higher version. Merely
re-running Prepare Release with no pending changes cannot recover that artifact.
If a publishing step fails, inspect
that workflow's logs and retry the failed run; do not move an existing tag or
rebuild a different Swift ZIP under the same version. If Knope left a draft
release after a partial upload, inspect and reconcile it before retrying rather
than creating a second release.

### Existing CI credentials

The release workflows follow the app-token pattern in
[sia-storage-js](https://github.com/SiaFoundation/sia-storage-js/blob/main/.github/workflows/prepare-release.yml).
They need the existing `SIA_CI_BOT_APP_ID` and `SIA_CI_BOT_PRIVATE_KEY` secrets,
with the app installed for this repository and Contents/Pull requests write
access. Using an app token ensures the release PR and published release trigger
other workflows. No credentials or repository settings are provisioned here.

Maven publication keeps using `SIGNING_KEY`, `SIGNING_PASSWORD`,
`MAVEN_CENTRAL_USERNAME`, and `MAVEN_CENTRAL_PASSWORD`. PyPI keeps the existing
`pypi` environment and trusted publisher for `python.yml`. Any environment
approval requirements still apply. Manual Kotlin/Python publishing remains
available for recovery and should only target the reviewed release tag.

Local checks (no publishing):

```sh
python3 .github/scripts/check_changesets.py
python3 -m unittest discover -s .github/scripts -p 'test_*.py'
knope --validate
knope prepare-release --dry-run
```

The integration test uses the real Knope executable when installed and operates
only in temporary repositories without remotes. Full platform builds require
Rust, Gradle/JDK, and macOS/Xcode and run in GitHub Actions.
