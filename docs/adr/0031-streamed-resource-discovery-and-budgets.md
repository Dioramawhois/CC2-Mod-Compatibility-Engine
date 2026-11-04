# ADR-0031: stream resource discovery and separate collection/build budgets

Status: accepted for the beta 8 hotfix, 2026-11-04. Refines the historical
prototype limits in ADR-0006 without changing merge or native-code approval.

## Problem

A player reported `Input byte limit exceeded` immediately after opening the
downloaded application. Discovery applied one 16 MiB per-file / 256 MiB total
budget to all installed packages and retained every resource's bytes, including
unchecked mods. A legitimate large texture/model or a larger subscription
collection could therefore prevent the mod list from opening. Raising only
discovery's limits would leave later original/output verification failures and
increase memory use during repeated scans.

## Decision

1. Hash discovered resources incrementally with bounded buffers. Keep each
   resource's relative path, byte size, classification header and SHA-256 in the
   scan; do not retain the contents of unchecked mods. Reporting and source
   fingerprinting must not materialize resource contents.
2. Allow at most **512 MiB per resource** and **16 GiB of resource input per
   discovery**. Keep the existing entry, path-depth and selected-package-count
   bounds. Explicit smaller developer-supplied limits remain effective.
3. Bound materialized selected inputs and generated output independently at
   **1 GiB each**, with the same 512 MiB per-resource ceiling. Selected input
   includes content/root resources and `mod.xml`. Check these sizes before
   reading selected contents. Keep a **16 MiB per text-processing input** bound
   for Git/Lua/XML/JSON work and text originals. Scanning can index a larger
   text resource, but selecting it must fail with an actionable file diagnostic.
   Apply the resource policy to installed originals, payload verification and
   reuse as well as discovery. Stream generated-resource verification hashes.
   Metadata and technical configuration retain separate, tighter parser/read
   bounds; `mod.xml` and generated manifests retain 16 MiB read bounds, and
   existing smaller configuration-specific bounds still apply.
4. A deferred resource read must verify that its current size/hash matches the
   discovery snapshot. Retain regular-file, root containment, link/junction,
   file-identity and concurrent-change checks. Preserve post-analysis snapshot
   validation before publishing. No mod Lua or DLL is executed during scanning.
5. Distinguish per-file and aggregate byte-limit failures. Name the affected
   relative resource, actual bytes and applicable byte limit in diagnostics.
   Reject an unsupported input before replacing the active generated package.

Source/base/output hashes, mod order and JSON package/report schemas are
unchanged. This is a storage/read-boundary change; it does not permit binary or
DLL merging, weaken syntax validation, modify subscribed mods or alter native
runtime review. Keep the checkbox workflow, closed-game deferral, transactional
activation, recovery and all 14 offline language catalogs.

## Validation and release scope

Regression coverage must reproduce an asset above 16 MiB and a discovered
collection above 256 MiB, then exercise selected-resource analysis, activation
and output verification. Verify bounded scan memory, changed deferred sources,
explicit small limits, replacement-limit failures and oversized metadata.
Keep source reports and hashes identical for unchanged bytes.

These are filesystem, packaging and GUI-boundary checks, not fresh gameplay
acceptance. The beta 7 exact-binary menu results remain recorded separately in
[menu verification](../verification/main-menu-v4.md). They must not be relabeled
as beta 8 exact-binary acceptance. Multiplayer, dedicated-server, clean-machine
and packaged macOS acceptance remain separate gates.
