# Screenshot provenance

These are captures of the actual CC2 ModLoader 0.4.0 beta 4 GUI on Windows,
using the same application sources and engine hash as the published executable.
They show file preparation and UI behavior in an isolated demonstration workspace.
No game was started by the capture process.

| Image | What was done |
| --- | --- |
| [Choose mods](images/01-choose-mods.png) | Checked AI Bridge, Island Airfields and the shared SDK; waited for the real analysis/activation transaction to complete in the private workspace. |
| [Load order](images/02-load-order.png) | Moved the selected packages through the real GUI order handler and waited for rebuilding to complete. |
| [Libraries](images/03-libraries.png) | Opened the Libraries tab on the same applied selection. The pictured SDK was explicitly selected; it is not evidence that these older Workshop packages declare dependencies. |
| [Overlap warning](images/04-overlap-warning.png) | Enabled two documentation-only example patches that intentionally overlap; the real Git/Lua pipeline produced the visible warning. |

The three named Workshop packages were copied byte-identically for the demo.
Installed original resources were copied unchanged as merge inputs. The two
“Example:” packages are owned demonstration patches, not published gameplay mods.
The existing generated package was excluded from discovery as usual.

The capture harness restricted writes to its private copied game/user folders.
It never installed DLLs or modified activation in the real installation.
Only the window's visible frame was captured; invisible resize margins were
excluded. No UI text, controls or results were painted into the images.

Your installed mod list can differ. The pictured combination and orange example
illustrate the workflow; they do not claim full gameplay compatibility.
See [Compatibility and verification](COMPATIBILITY.md).

[Capture hashes and selected order](images/capture-metadata.json)
