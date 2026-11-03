# CC2 ModLoader notices

Copyright (c) 2026 CC2 ModLoader contributors.

CC2 ModLoader is free software: you may redistribute it and/or modify it under the
GNU General Public License as published by the Free Software Foundation, either
version 3 of the License, or (at your option) any later version.

It is distributed without any warranty, including the implied warranties of
merchantability or fitness for a particular purpose. See [LICENSE](LICENSE).

This license covers this project's original code and documentation. Third-party
components retain their own copyrights, licenses and notices. Carrier Command 2,
its executable, official SDK resources and third-party gameplay mods are not
included in the ModLoader executable or relicensed by this notice.

The 0.4.0b2 client candidate embeds one exact reviewed CC2X 0.6 development runtime
under its own GPL-3.0-or-later license. Its binary, clean build provenance, source
reference and original GPL/Lua MIT/MinGW/Zig notices are in cc2_mce/runtime_data.
Corresponding SDK source is available at
https://github.com/Dioramawhois/Carrier-Command-2-extender/tree/2eecbd93c3555fed9a2b3f25e5b9c91abb55196f.
No aircraft assets or gameplay plugins are linked into this common SDK binary.
Linked libc++, libc++abi and libunwind notices (Apache-2.0 WITH LLVM-exception)
are preserved alongside the runtime. Release assets include matching SDK sources
and Zig provider library sources, in addition to the separate Git/Lua sources.

The Windows distribution embeds unmodified Git for Windows binaries (a separate
process), Lua 5.3's syntax validator, CPython/Tcl/Tk, PyInstaller's bootloader and
Python dependencies. The release includes component licenses, exact versions and
hashes in its SBOM, and corresponding source/build references. Keep these files
when redistributing the package. The player's mods remain local and are never
uploaded by ModLoader.
