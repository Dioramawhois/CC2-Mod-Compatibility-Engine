# Build CC2 ModLoader from source

This is the second distribution route: build the Windows graphical executable
yourself instead of downloading the ready-to-use one. Once it is built, use
[the same installation and GUI workflow](INSTALLATION.md).

The commands below are for developers and people who choose to compile the app.
They are not prerequisites for using the published Windows executable.

## What you are building

The application is Python/Tk packaged by PyInstaller as `CC2ModLoader.exe`.
The normal build includes the pinned Git merge tool, Lua 5.3 syntax checker and
an exact reviewed CC2X runtime dependency. Building ModLoader does not rebuild
the game or compile gameplay mods into the SDK.

The SDK's C/C++ source and compiler-library sources are published separately.
Recompiling those native components is a separate developer task and is not
required to build the ModLoader executable from its Python source.

Beta 9 pins CC2X SDK **0.8.1-client-beta.1**. Its bundled runtime, source-archive
restore lock and native profile must identify the same reviewed DLL. Previous
runtime hashes permit a journaled upgrade or a known older source package;
they do not select a different provider or authorize arbitrary new DLL bytes.

## Supported build environment

Use 64-bit Windows with:

- **CPython 3.12 or 3.13, 64-bit**, including Tcl/Tk and `pip`. The project accepts
  Python 3.12+, but these two versions form the current CI matrix.
- **Git for Windows**, available from the developer terminal. The regression
  tests invoke real Git even when you obtained the source as a ZIP.
- Internet access for the first build, or the cached dependencies described
  below.
- A normal writable working folder. A path containing spaces is supported.

The standard build does not require Visual Studio, a C/C++ compiler, Zig, a
running game, a private SDK checkout or a Steam login. A Windows executable
should be built on Windows; the macOS core CI does not cross-compile it.

To verify the Python installation in PowerShell:

```powershell
py -3 --version
py -3 -m tkinter
git --version
```

The Tk command should open a small test window. Close it before continuing. If
`py` is not installed but `python` runs the required Python version, use
`python` in its place. The batch build checks `python` first, then the Windows
Python launcher.

## 1. Obtain the exact release source

Choose one of these acquisition methods. They are two ways to obtain source
for the same self-build route.

### Clone the release tag

```powershell
git clone --branch v0.4.0b9 --depth 1 https://github.com/Dioramawhois/CC2-ModLoader.git
Set-Location CC2-ModLoader
```

The tag fixes the application source used by the release. A normal Git clone
also includes the tracked reviewed native runtime dependency. It does not
require initializing Git submodules.

### Download the release source ZIP

From the [same release page](https://github.com/Dioramawhois/CC2-ModLoader/releases/tag/v0.4.0b9),
download **CC2ModLoader-0.4.0b9-source.zip**. Extract it, open its extracted root
folder, and open PowerShell there. The root contains `pyproject.toml`,
`build_windows.bat`, `cc2_mce`, `tests` and `tools`.

The source ZIP intentionally excludes the native SDK DLL. The build restores
the reviewed runtime automatically when it is absent, verifying the expected
hash. GitHub's automatic source ZIP/tarball also excludes that DLL. An arbitrary
`dinput8.dll` is not an acceptable replacement.

The runtime download is pinned by
[`distribution/windows-runtime.json`](../distribution/windows-runtime.json) to
the public SDK release asset, including its byte length and SHA-256. The helper
never installs into a game directory and never loads the DLL while building.

The application-source ZIP is distinct from `-sdk-source.zip` and
`-tool-sources.zip`: the latter contain corresponding native/dependency sources
for transparency and redistribution, not the ModLoader application project.

## 2. Build the executable

In PowerShell, from the source root:

```powershell
.\build_windows.bat
```

For an automated terminal session that should return without waiting for a key:

```powershell
.\build_windows.bat --no-pause
```

The script:

1. Finds Python 3.12+ and creates or reuses `.build-venv` inside the project.
2. Installs the application and development dependencies, with PyInstaller
   pinned to **6.22.3**.
3. Restores the pinned Windows Git/Lua tools if they are absent.
4. Ensures that the exact reviewed SDK runtime is available for the bundle.
5. Runs the regression suite and writes `build/test-results.xml`.
6. Builds a one-file graphical executable without a console window.
7. Checks the frozen sources, schemas and tools, then opens and closes the GUI
   using isolated preferences and a restricted PATH.

The result is:

```text
dist/
  CC2ModLoader.exe
  CC2ModLoader.build.json
```

The JSON sidecar records the executable, source and engine hashes, actual test
counts and the limits of the local build verification. Retain it when sharing
an independently built executable.

Do not use an older file from `dist` if the build ended with an error. A build
failure does not prove that an existing executable was updated.

## 3. Install your build

Close the game and any running ModLoader. Back up your previous ModLoader
executable, then copy `dist\CC2ModLoader.exe` beside `carrier_command.exe` in
your game folder. Open it normally and follow
[Install and use CC2 ModLoader](INSTALLATION.md).

The build itself does not install into your game, modify Workshop downloads,
activate a selected mod set or launch the game. Test scripts that explicitly
exercise a real installation are separate maintainer tools and should not be
run as part of the normal build instructions.

## Downloads, caches and an offline build

Normal use of the completed app is offline after Steam has downloaded the game
and selected mods. A first developer build is different: it may download Python
packages and pinned build dependencies.

The Git/Lua archive is defined by
[`distribution/windows-build-tools.json`](../distribution/windows-build-tools.json).
The archive may retain an older release version in its filename because its
verified contents are reused. The lock file's URL and SHA-256 define the exact
dependency; renaming another archive does not make it equivalent.

To use an already downloaded verified tools archive instead of downloading it:

```powershell
$env:CC2_MCE_TOOLS_ARCHIVE = 'C:\BuildDependencies\CC2ModLoader-0.4.0b1-build-tools.zip'
.\build_windows.bat --no-pause
```

For an exported source tree with no reviewed SDK DLL, an existing runtime file
can be supplied explicitly:

```powershell
$env:CC2_MCE_RUNTIME_FILE = 'C:\BuildDependencies\dinput8.dll'
.\build_windows.bat --no-pause
```

The file must match the expected reviewed runtime hash; an incompatible or
unknown file is rejected. These environment variables apply only to the current
PowerShell session unless you deliberately persist them.

The matching `CC2ModLoader-0.4.0b9-sdk-runtime.zip` can also restore the native
dependency: extract its directory structure into the application source root,
so the files appear under `cc2_mce\runtime_data\<reviewed-hash>\`. Do not put
the DLL at the application source root or in `tools_data`.

An entirely offline build additionally needs all required Python packages and
build-backend dependencies available in a local package cache or wheelhouse.
Setting the two native-dependency variables alone does not make `pip` offline.
The stock batch file uses `pip`; it does not itself perform a frozen `uv sync`.

## Run development checks with the locked environment

The repository includes `uv.lock`. Contributors can reproduce the Python
development dependency set with `uv`:

```powershell
uv sync --frozen --extra dev
uv run --frozen pytest -q
uv run --frozen ruff check cc2_mce tests
uv run --frozen ruff format --check cc2_mce tests
uv run --frozen mypy cc2_mce
uv run --frozen cc2-mce --version
uv run --frozen cc2-mce --config examples/mce.synthetic.toml build --dry-run
```

The last command uses synthetic fixtures. It is not game acceptance and does
not activate a game mod. A development GUI can also be started with
`python -m cc2_mce.gui` in an environment where the project and required tools
are installed; the packaged executable remains the supported player route.

The Windows/macOS CI matrix uses Python 3.12 and 3.13 for the shared code,
formatting, type checks, real Git fixtures and golden dry run. A skipped Tk
display test does not demonstrate GUI support, and core CI does not certify a
packaged macOS application or native SDK support on macOS.

## Build and release troubleshooting

| Failure | Check |
| --- | --- |
| Python 3.12+ is required | Install a supported 64-bit CPython with Tcl/Tk and pip; check which `python` or `py -3` the terminal launches. |
| `git` cannot be found in tests | Install Git for Windows on the build machine and reopen the developer terminal. |
| Python package download fails | Check network/proxy settings or prepare a complete local package cache; a source ZIP contains source, not every build dependency. |
| Native/tool checksum mismatch | Verify the exact release dependency and lock file. Do not change expected hashes to accept an unrelated file. |
| An existing native dependency is rejected | Preserve it and compare its source/version; the build does not silently trust an arbitrary DLL. |
| Test or GUI smoke failure | Read the first failure and retain `build/test-results.xml`; fix the cause before distributing the executable. |
| A shared-library or Tk import is missing | Check the CPython installation and rebuild in a fresh supported environment. |

Creating the official release asset set is a separate maintainer operation.
`tools/package_release.py` requires a clean reviewed Git commit, a matching
verified executable, passing regression metadata, exact dependency sources and
the pinned SDK/compiler inputs. A successful personal build does not grant
permission to bypass branch protection or replace an official release.

The asset set includes the standalone `CC2ModLoader.exe` and its `.sha256` as
well as the complete Windows ZIP. Publishing a numbered beta runs the serialized
latest-beta workflow, which verifies the versioned ZIP and mirrors the complete
release into the permanent download channel. A manual workflow dispatch accepts
an existing numbered beta. See [ADR-0027](adr/0027-standalone-exe-and-rolling-beta-download.md).

## Rebuilding native dependencies

The normal application build packages the reviewed SDK DLL; it does not compile
that C/C++ dependency from its source. If you also want to rebuild the SDK, use
the corresponding `-sdk-source.zip` and `-sdk-toolchain-sources.zip` assets and
the [exact SDK source revision](https://github.com/Dioramawhois/Carrier-Command-2-extender/tree/f322938094bf7ea9e30f3be841b3c744687385b8).
The exact native source revision, compiler hash and input hashes are recorded
in its `dinput8.build.json`.

A new or different native binary does not become trusted merely because it was
built locally. The application still requires the reviewed runtime/profile
bytes. Source changes, a different compiler or a mismatching result need their
own compatibility review; do not edit the expected hash simply to suppress a
failure. The separate tool-source archives likewise document the Git/Lua build
inputs and redistribution recipes rather than requiring every ModLoader user
to rebuild those tools.
