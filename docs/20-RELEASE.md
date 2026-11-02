# 20. Публичная Windows beta 0.4.0b1

Это новая версия CC2 ModLoader, GPL-3.0-or-later. Идентичность executable и
постоянной папки не меняется; существующие SDK/моды также обновляются на своих
страницах. Бета не включает новые непроверенные multiplayer DLL и не обходит
reviewed native profiles. Отдельного Workshop item не создаётся.

## Developer pipeline

1. Чистый checkout + Python 3.12+, `uv sync --frozen --extra dev`.
2. Обязательные pytest/Ruff/mypy и Windows/macOS core CI. Это не тест готового Mac app.
3. `build_windows.bat --no-pause`: готовит pinned tools, собирает exe, запускает
   реальный frozen Git/Lua и GUI smoke; сохраняет sidecar/JUnit.
4. По умолчанию tools скачиваются из release URL в
   `distribution/windows-build-tools.json`, строго по SHA. При bootstrap релиза
   developer может указать `CC2_MCE_TOOLS_ARCHIVE` на тот же проверенный архив.
   Игрок ничего не скачивает при старте. `--from-source` — только maintainer refresh.
5. После commit, `python -m tools.package_release` из build environment собирает
   clean-source и Windows ZIP, corresponding tool sources/build recipes, pinned
   tool archive и SHA256SUMS. Нужен заполненный `build/release-sources` по lock.
   Эта команда готовит assets локально и ничего не публикует сама.
6. Проверить CRC, source exclusions, notices и SHA; загрузить весь набор assets
   в один GitHub prerelease с точным source commit/tag и явными границами тестов.

## Assets и provenance

- Windows ZIP: CC2ModLoader.exe, player README, GPL/NOTICE, LICENSES всех runtime,
  SBOM.cdx.json и public RELEASE.json без личных путей, mod names или mod content.
- Source ZIP: только tracked clean commit через git archive; без бинарников,
  локального build/research, vanilla/SDK scripts и пользовательских файлов.
- Tool sources ZIP: точные Git, Lua и DLL dependency sources, pinned MSYS2 recipes
  и patches. Lock включает URL, commit и SHA; плавающий upstream patch не принимается.
- Build tools ZIP: byte-identical закреплённые инструменты для developer checkout.

Нельзя объявлять полную игровую совместимость по syntax/merge или menu smoke.
Полноценный multiplayer требует реального remote client, обычного host и dedicated
профиля/загрузчика. Current dedicated_server.exe не импортирует dinput8/GLFW;
клиентский proxy DLL и client offsets сами по себе этого не решают.
