# ADR-0027: standalone EXE and a permanent latest-beta download

Status: accepted, 2026-11-04, following the owner's direct-download request.

## Decision

Publish `CC2ModLoader.exe` and its `.sha256` alongside the complete versioned
Windows ZIP. The EXE must match the ZIP's recorded artifact hash exactly; this
distribution change does not rebuild or alter an accepted executable.

Retain GitHub prerelease status for beta versions. GitHub's built-in Latest
endpoint excludes prereleases, so use the dedicated `latest-beta` prerelease
and a permanent `/releases/download/latest-beta/CC2ModLoader.exe` address.
The rolling release mirrors all source release assets, including corresponding
sources, notices and verification metadata, with an additional `CHANNEL.json`
identifying the exact numbered version, source commit and hashes.

Only the rolling `refs/tags/latest-beta` pointer and its managed asset copies
may advance. Numbered version tags and their original archives are preserved.
Unknown channel ownership, immutable channels, mismatched artifact/source hashes
and older beta versions cannot replace the current channel. This mutable
distribution pointer does not change main-branch protection or product gates.

A serialized release-published workflow updates the channel after a numbered
beta is published; manual workflow dispatch supports an existing release.
Maintainer credentials are supplied by environment, never stored in source.

The publisher accepts an existing standalone checksum with either one LF or
one CRLF line ending, after checking the exact executable hash and filename.
It mirrors those original bytes without rewriting numbered assets. Malformed
lines, different hashes and different executable bytes are rejected. New
packages write checksums with LF on every host.

## Validation

Fixtures cover numeric beta ordering, branch/tag rejection and mismatched
version, source revision or EXE hashes. Live verification downloads the public
permanent link and compares it to the versioned Windows ZIP. The desktop app,
SDK, package/report schemas and game files are unchanged.
