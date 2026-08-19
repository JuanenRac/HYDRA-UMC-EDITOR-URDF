# =============================================================================
# HYDRA-UMC EDITOR-URDF - i18n.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Same 5-language convention (English/Spanish/Italian/French/German) and
# the same plain KEY=Value language/<name>.lng file mechanism every other
# Python project in this ecosystem uses (URTC-FLASHER, URTC-TESTER,
# HYDRA-UMC-SUITE) - this file is a near-verbatim port of HYDRA-UMC-SUITE's
# own i18n.py, per [[No reference -> reuse, don't invent]]: the mechanism
# itself has no project-specific logic, no reason to redesign it here.
#
# Language switch requires an app restart (same as the rest of the
# ecosystem) rather than live-retranslating every already-built widget.
# =============================================================================
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    _base_dir = Path(sys.executable).resolve().parent
else:
    _base_dir = Path(__file__).resolve().parent.parent

LANGUAGE_FOLDER = _base_dir / "language"
CONFIG_FILE_PATH = _base_dir / "hydra_editor_urdf_config.json"
DEFAULT_LANGUAGE = "english"
AVAILABLE_LANGUAGES: list[tuple[str, str]] = [
    ("english", "English"),
    ("spanish", "Español"),
    ("italian", "Italiano"),
    ("french", "Français"),
    ("german", "Deutsch"),
]


def load_config() -> dict:
    if not CONFIG_FILE_PATH.is_file():
        return {}
    try:
        with open(CONFIG_FILE_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}


def save_config(updates: dict) -> bool:
    """Merges updates into the existing config and writes it back
    atomically (temp file + os.replace())."""
    current = load_config()
    current.update(updates)
    tmp_path = CONFIG_FILE_PATH.with_suffix(".json.tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2)
        os.replace(tmp_path, CONFIG_FILE_PATH)
        return True
    except OSError:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        return False


def load_language(name: str) -> dict[str, str]:
    """Reads language/<name>.lng - plain UTF-8 KEY=Value, one per line,
    '#'-prefixed/blank lines ignored, literal \\n unescaped to a real
    newline - same format every other project in this ecosystem reads."""
    path = LANGUAGE_FOLDER / f"{name}.lng"
    result: dict[str, str] = {}
    try:
        with open(path, encoding="utf-8-sig") as f:
            for line in f:
                line = line.rstrip("\n").rstrip("\r")
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _sep, value = line.partition("=")
                result[key.strip()] = value.replace("\\n", "\n")
    except (OSError, UnicodeDecodeError):
        return {}
    return result


_config = load_config()
_current_language = _config.get("language", DEFAULT_LANGUAGE)
_translations = load_language(_current_language)
if not _translations and _current_language != DEFAULT_LANGUAGE:
    _current_language = DEFAULT_LANGUAGE
    _translations = load_language(DEFAULT_LANGUAGE)


def _(key: str, **kwargs) -> str:
    """Looks up key in the currently loaded language file, applying any
    keyword substitutions. Falls back to the key itself (visibly
    un-translated) if missing, rather than raising."""
    text = _translations.get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text


def current_language() -> str:
    return _current_language
