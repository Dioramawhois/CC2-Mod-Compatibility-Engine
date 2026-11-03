# Security policy

## Scope

CC2 ModLoader reads untrusted mod metadata and files, invokes a local Git merge
tool and Lua syntax checker, and manages its own generated mod and recorded
activation state. Native mod DLLs execute inside the game only after the
applicable compatibility checks; development scanning and validation do not
execute mod Lua or DLLs.

Security issues include unsafe path handling, archive traversal, XML external
entity access, unbounded resource consumption, unintended source writes,
incorrect native trust decisions, unsafe recovery or release-integrity failures.

## Reporting a vulnerability

Use the repository's **Security > Report a vulnerability** action if private
reporting is available. If it is unavailable, open a minimal issue asking a
maintainer for a private reporting channel, without publishing exploit details
or private files.

A useful report includes the affected release/tag, host OS, concise reproduction
steps, expected versus actual behavior and a small synthetic fixture where
possible. Do not attach passwords, tokens, personal saves, game executables,
private paths or executable mod payloads to a public report.

The project currently distributes a Windows beta. Check the release page for
the current build and its limitations; no long-term maintenance window or
security-response deadline is promised by this policy.

## Repository change policy

Changes intended for `main` must be submitted through a pull request, pass the
required automated checks against an up-to-date branch, and resolve review
conversations. Contributors should work in topic branches or forks. Direct
pushes, force-pushes and deletion of `main` are not an accepted contribution
workflow.

The policy requires the four Windows/macOS checks for Python 3.12 and 3.13,
applies the branch rules to administrators, and provides no extra bypass list.
The repository currently has a single owner with write access. The required
approval count is therefore zero: the owner can merge a passing PR without an
independent second approval. Making a second approval mandatory would prevent
that owner from merging their own changes until another trusted reviewer is
added. Passing CI is required in either case; it is not independent human review.

Changes to workflows, dependency locks, native trust profiles, executable
packaging and release code deserve explicit review. A declared library name or
author identity does not substitute for the native binary's verified hash and
supported game profile.

This document states policy. The enforcement settings live in GitHub branch
protection/rulesets and repository access controls, and must be audited there.
Do not treat the presence of `SECURITY.md` or a green local test result as proof
that a particular branch rule is enabled.

Branch protection reduces accidental and unauthorized changes. An administrator
who can change repository rules or access settings can also change those
protections. Limit administrative access, protect maintainer accounts and
review permissions as well as code; no repository document can make `main`
immutable against its own authorized administrators.

## Release and dependency integrity

Download application binaries from this repository's GitHub Releases page.
Release assets include SHA-256 checksums, source/build provenance and license
notices. Verify downloaded files against the matching release metadata when
investigating a damaged or unexpected download.

Checksums identify exact bytes and detect corruption; they do not by themselves
protect against a compromised release publisher. Build from a reviewed source
tag if that is part of your own trust requirements.

Do not bypass a failed DLL/profile check by editing expected hashes, renaming
an unknown DLL or replacing an existing loader blindly. Preserve the files and
report the mismatch. Supported runtime installation/upgrades use the app's
recorded backup and recovery workflow.
