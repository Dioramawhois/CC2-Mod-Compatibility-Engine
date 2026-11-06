# ADR-0037: SDK updates without replacing ModLoader for each runtime

Status: implemented for beta 12, 2026-11-07. Supersedes the per-SDK EXE rebuild
requirement in ADR-0019/0032/0036 for publisher-authenticated SDK releases.

The owner explicitly requested removing the unsupported-SDK barrier and repeated
EXE reinstalls. The SDK provider must be able to change independently of the
application. Removing a message while retaining the same blocker is insufficient.

## Trust and compatibility

The official SDK package carries `content/cc2x/runtime_update.json`: a bounded,
Ed25519-signed envelope identifying the publisher, exact game/runtime hashes,
byte length, monotonic release sequence, API levels/capabilities, source revision
and approved predecessor hashes. The public publisher key is bundled once with
ModLoader; a package cannot supply its own trust key. Verify signatures using
the pinned cryptography dependency, never a custom cryptographic implementation.
SDK source DLLs are read/hash/PE-checked, never loaded by development utilities.

Only a declared `cc2x.runtime` SDK library can provide the descriptor. A valid
newer signed release supplies the effective provider without changing the bundled
fallback. Preserve the existing exact game identity, resource paths, bounds,
plugin reviews and syntax gates. This authorizes SDK infrastructure updates,
not arbitrary DLL plugins, unknown installed loaders or new unreviewed modules.
Different signed binaries at one sequence are ambiguous and rejected.

An installed signed provider can stay current when the selected source is older.
Unavailable source packages do not prevent using an installed authenticated SDK.
Cached receipts grant recognition, not an automatic preference for an absent or
uninstalled DLL. This preserves Undo and avoids upgrading again solely because
an approval receipt remains cached. Versions with no signature remain usable
through the existing bundled/current/previous reviewed hashes.

## Installation and cache

Use the existing closed-game transaction and exact runtime backup/install/Undo.
Persist immutable, signature-verified receipts under the selected user's
`cc2-mce/runtime-providers`, after fresh source verification and before activation.
Receipts may survive a rolled-back installation: approval and active preference
are separate. Reverify cached signatures and target game identities every time.
Invalid unrelated receipts grant no native approval. The signed descriptor is
input metadata, recorded through source hashes and the optional report envelope;
it is not copied into the generated game content or merged as a resource.

## Contract and UI

Keep package schema 2. Add `runtime_provider` with the signed envelope and permit
`runtime_review.stage=publisher-signed`, including the publisher-key identity and
explicit validation scope. Such a review requires the envelope. Legacy reports
remain valid. Preserve file hashes, reproducible source order, runtime input
hashes and native rollback journals.

The GUI checkbox remains the authorized apply action. No approval dialog, terminal,
technical config edit or new preparation button. SDK verification failures name
the SDK and ask for a fresh library download; they no longer prescribe replacing
the application for each compatible SDK release. Preserve all 14 offline catalogs.

## Publisher operation and evidence

The private signing key stays outside all repositories and release archives.
SDK release tooling signs verified release metadata with an increasing sequence;
the public descriptor travels with future Workshop SDK updates. The native DLL
is not rebuilt just to deliver this metadata. Keep the original compiled source
record, corresponding source, licenses and byte hash. cryptography/cffi/pycparser
notices accompany the application distribution. Key rotation or a genuinely new
application protocol can still require an application update.

Fixtures exercise two future updates with one unchanged application, first
install/upgrade/Undo, unavailable SDK source, older source/no downgrade, unsigned
or altered manifests, wrong game/hash/size/architecture and unknown installed
loader refusal. Add cache/source races and bounded parsing cases. Run shared-code
Windows/macOS CI separately from frozen GUI and real gameplay evidence. Signature
verification is publisher authentication, not a fresh gameplay acceptance claim.
