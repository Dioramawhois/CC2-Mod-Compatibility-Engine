"""Offline multilingual UI with system-language detection and named messages."""

from __future__ import annotations

import locale
import os
import re
import sys

from cc2_mce.language_packs import PACKS
from cc2_mce.translations import EN

LANGUAGES = {
    "en": "English",
    "ru": "Русский",
    "de": "Deutsch",
    "fr": "Français",
    "es": "Español",
    "pt": "Português (Brasil)",
    "it": "Italiano",
    "pl": "Polski",
    "tr": "Türkçe",
    "uk": "Українська",
    "zh": "简体中文",
    "zh-TW": "繁體中文",
    "ja": "日本語",
    "ko": "한국어",
}


def language_for_locale(value: str | None) -> str:
    normalized = (value or "").lower().replace("-", "_")
    if normalized.startswith("zh"):
        return (
            "zh-TW"
            if any(part in normalized for part in ("_tw", "_hk", "_mo", "hant", "cht"))
            else "zh"
        )
    language = normalized.split("_")[0].split(".")[0]
    return language if language in LANGUAGES else "en"


def system_language() -> str:
    if sys.platform == "win32":
        try:
            import ctypes

            language_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            return language_for_locale(locale.windows_locale.get(language_id))
        except (AttributeError, OSError):
            pass
    for name in ("LC_ALL", "LC_MESSAGES", "LANG"):
        if os.environ.get(name):
            return language_for_locale(os.environ[name])
    return language_for_locale(locale.getlocale()[0])


class Translator:
    def __init__(self, choice: str = "system") -> None:
        self.language = system_language() if choice == "system" else choice
        self.catalog = {**EN, **PACKS.get(self.language, {})}
        self._patterns: list[tuple[re.Pattern[str], str, list[str]]] = []
        for original, translated in self.catalog.items():
            keys = re.findall(r"\{(p[0-9]+)\}", original)
            if keys:
                pattern = re.escape(original)
                for key in keys:
                    pattern = pattern.replace(re.escape("{" + key + "}"), "(.+?)", 1)
                self._patterns.append((re.compile(pattern), translated, keys))

    def __call__(self, message: str, **values: object) -> str:
        if self.language == "ru":
            return message.format(**values) if values else message
        translated = self.catalog.get(message)
        if translated is not None:
            return translated.format(**values) if values else translated
        if not values:
            for pattern, template, keys in self._patterns:
                match = pattern.fullmatch(message)
                if match:
                    return template.format(**dict(zip(keys, match.groups(), strict=True)))
        return message.format(**values) if values else message
