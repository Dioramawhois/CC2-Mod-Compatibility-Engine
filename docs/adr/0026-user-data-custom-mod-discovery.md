# ADR-0026: discover custom mods in the game user-data folder

Status: accepted. Date: 2026-11-04. Extends the input collections in ADR-0008
and the startup/passive scanning behavior in ADR-0025.

## Problem

The GUI assembled its roots from Workshop, explicitly added folders and the
installation's `mods` folder. It omitted the game's standard user-data `mods`
folder, even though activation used that location for the generated package.
Custom mods placed where the game normally stores them could remain invisible.

## Decision

Use `game_user_dir()/mods` as an additional default input collection. On Windows
this is `%APPDATA%\Carrier Command 2\mods`; on macOS it is
`~/Library/Application Support/Carrier Command 2/mods`. Refresh the root before
each scan so a directory created after startup is discovered automatically.
Deduplicate roots and show both local locations in File locations.

An absent optional user folder does not block discovery. Existing files,
symlinks/junctions and mod content retain the existing filesystem validation;
the GUI does not create this input folder or execute its Lua/native payloads.
The existing owner-manifest check excludes generated `CC2-MCE` output from its
own inputs. Workshop and game-folder sources remain supported in place.

Discovering a mod does not select it. The saved selection, dependency resolution,
patch order, native review and automatic rebuild policy are unchanged. JSON
schema versions remain unchanged: source fingerprints and source reports use
the existing contracts.

## Validation

Tk fixtures reproduce both missing initial user mods and a missing folder
created during a session. They cover all three default input locations,
generated-output exclusion, unchanged source bytes and selection preservation.
The new mod stays unchecked and does not trigger a rebuild until selected.
Read-only inventory and frozen Windows packaging checks are separate evidence;
this change does not imply new game, multiplayer or macOS release acceptance.
