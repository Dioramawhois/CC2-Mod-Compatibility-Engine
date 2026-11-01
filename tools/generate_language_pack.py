"""Developer-only language-pack generation from public UI strings; app runtime stays offline.

Generated data is checked in and validated for message/placeholder coverage. No mod names,
paths, user preferences, keys or game data are sent to the translation endpoint.
"""

import concurrent.futures
import json
import re
import time
import urllib.parse
import urllib.request
import unicodedata
from pathlib import Path

from cc2_mce.translations import EN

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = {"de": "de", "fr": "fr", "es": "es", "pt": "pt", "it": "it", "pl": "pl",
             "tr": "tr", "uk": "uk", "zh": "zh-CN", "zh-TW": "zh-TW", "ja": "ja", "ko": "ko"}
LABELS = {
    "de": ["Menü", "Sprache", "Systemsprache", "Spiel starten", "Mods", "Bibliotheken", "Ladereihenfolge"],
    "fr": ["Menu", "Langue", "Langue du système", "Lancer le jeu", "Mods", "Bibliothèques", "Ordre de chargement"],
    "es": ["Menú", "Idioma", "Idioma del sistema", "Iniciar juego", "Mods", "Bibliotecas", "Orden de carga"],
    "pt": ["Menu", "Idioma", "Idioma do sistema", "Iniciar jogo", "Mods", "Bibliotecas", "Ordem de carregamento"],
    "it": ["Menu", "Lingua", "Lingua di sistema", "Avvia gioco", "Mod", "Librerie", "Ordine di caricamento"],
    "pl": ["Menu", "Język", "Język systemu", "Uruchom grę", "Mody", "Biblioteki", "Kolejność ładowania"],
    "tr": ["Menü", "Dil", "Sistem dili", "Oyunu başlat", "Modlar", "Kütüphaneler", "Yükleme sırası"],
    "uk": ["Меню", "Мова", "Мова системи", "Запустити гру", "Моди", "Бібліотеки", "Порядок завантаження"],
    "zh": ["菜单", "语言", "跟随系统", "启动游戏", "模组", "库", "加载顺序"],
    "zh-TW": ["選單", "語言", "依照系統", "啟動遊戲", "模組", "程式庫", "載入順序"],
    "ja": ["メニュー", "言語", "システムに合わせる", "ゲームを起動", "MOD", "ライブラリ", "ロード順"],
    "ko": ["메뉴", "언어", "시스템 언어", "게임 실행", "모드", "라이브러리", "로드 순서"],
}


def fetch(language, values):
    payload = "\n".join(f"[[{index:04d}]] {value}" for index, value in values)
    query = urllib.parse.urlencode({"client": "gtx", "sl": "en", "tl": language, "dt": "t", "q": payload})
    for attempt in range(3):
        try:
            request = urllib.request.Request("https://translate.googleapis.com/translate_a/single?" + query,
                                             headers={"User-Agent": "CC2-ModLoader-language-pack-build"})
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.load(response)
            text = unicodedata.normalize("NFKC", "".join(part[0] for part in data[0] if part[0]))
            parts = re.split(r"\[{1,2}\s*(\d{1,4})\s*\]{1,2}", text)
            result = {int(parts[i]): parts[i + 1].strip() for i in range(1, len(parts), 2)}
            if set(result) != {index for index, _ in values}:
                debug = ROOT / "build/language-cache" / f"raw-{language}-{values[0][0]}.json"
                debug.write_text(json.dumps({"expected": [i for i, _ in values], "text": text}, ensure_ascii=False), encoding="utf-8")
                print(f"{language}: retry split for entries {values[0][0]}..{values[-1][0]}", flush=True)
                if len(values) > 1:
                    middle = len(values) // 2
                    return {**fetch(language, values[:middle]), **fetch(language, values[middle:])}
                plain = urllib.parse.urlencode({"client": "gtx", "sl": "en", "tl": language,
                                                 "dt": "t", "q": values[0][1]})
                with urllib.request.urlopen("https://translate.googleapis.com/translate_a/single?" + plain,
                                            timeout=30) as response:
                    single = json.load(response)
                return {values[0][0]: unicodedata.normalize("NFKC", "".join(p[0] for p in single[0] if p[0]))}
            return result
        except Exception:
            if attempt == 2:
                raise
            time.sleep(1 + attempt)


def build(code, target):
    cache = ROOT / "build/language-cache" / (code + ".json")
    if cache.exists():
        return code, json.loads(cache.read_text(encoding="utf-8"))
    entries = list(EN.items())
    chunks, current, size = [], [], 0
    for index, (_, value) in enumerate(entries):
        if current and size + len(value) > 1400:
            chunks.append(current)
            current, size = [], 0
        current.append((index, value))
        size += len(value) + 12
    if current:
        chunks.append(current)
    translated = {}
    if code == "ko":
        # This locale strips numeric batch markers. Translate independent messages directly.
        def single(entry):
            index, (_, value) = entry
            query = urllib.parse.urlencode({"client": "gtx", "sl": "en", "tl": target,
                                            "dt": "t", "q": value})
            for attempt in range(3):
                try:
                    with urllib.request.urlopen("https://translate.googleapis.com/translate_a/single?" + query,
                                                timeout=30) as response:
                        data = json.load(response)
                    return index, unicodedata.normalize("NFKC", "".join(p[0] for p in data[0] if p[0]))
                except Exception:
                    if attempt == 2:
                        raise
                    time.sleep(1)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            translated.update(pool.map(single, enumerate(entries)))
    else:
        for chunk in chunks:
            print(f"{code}: batch {chunk[0][0]}..{chunk[-1][0]}", flush=True)
            translated.update(fetch(target, chunk))
    result = {}
    for index, (key, value) in enumerate(entries):
        output = translated[index]
        # Keep intentional concatenation spaces and immutable named parameters.
        if value.startswith(" "):
            output = " " + output.lstrip()
        if value.endswith(" "):
            output = output.rstrip() + " "
        for match in re.findall(r"\{p\d+\}", value):
            number = re.search(r"\d+", match)[0]
            output = re.sub(r"\{\s*[pP]\s*" + number + r"\s*\}", match, output)
        if set(re.findall(r"\{p\d+\}", value)) != set(re.findall(r"\{p\d+\}", output)):
            raise ValueError(f"{code}: placeholder mismatch in entry {index}")
        output.format(**{key: "value" for key in re.findall(r"\{(p\d+)\}", value)})
        result[key] = output
    keys = ["Меню", "Язык", "Как в системе", "Запустить игру", "Моды", "Библиотеки", "Порядок загрузки"]
    result.update(zip(keys, LABELS[code], strict=True))
    result["Моды · {p0}"] = LABELS[code][4] + " · {p0}"
    result["Библиотеки · {p0}"] = LABELS[code][5] + " · {p0}"
    cache.parent.mkdir(exist_ok=True)
    cache.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return code, result


if __name__ == "__main__":
    catalogs = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as workers:
        jobs = [workers.submit(build, code, target) for code, target in LANGUAGES.items()]
        for job in concurrent.futures.as_completed(jobs):
            code, data = job.result()
            catalogs[code] = data
            print(f"{code}: {len(data)} validated entries", flush=True)
    header = '"""Offline language pack generated from project-owned UI messages; primary labels reviewed."""\n\n# ruff: noqa: E501\n\n'
    terminology = {"zh": {"图书馆": "库"}, "zh-TW": {"圖書館": "程式庫"},
                   "ja": {"図書館": "ライブラリ"}, "ko": {"도서관": "라이브러리"}}
    for code, replacements in terminology.items():
        if code in catalogs:
            for key, value in catalogs[code].items():
                for source, target in replacements.items():
                    value = value.replace(source, target)
                catalogs[code][key] = value
    (ROOT / "cc2_mce/language_packs.py").write_text(header + "PACKS: dict[str, dict[str, str]] = "
        + json.dumps(dict(sorted(catalogs.items())), ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
