# =============================================================================
# HYDRA-UMC EDITOR-URDF - tests/test_i18n.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Real unit tests for hydra_editor_urdf/i18n.py's own file-backed
# functions (load_config/save_config/load_language) plus the lookup
# helper _(), exercised against real temp files via monkeypatch on the
# module's own path constants - never the operator's real config/language
# folder next to the actual installed app.
# =============================================================================
from __future__ import annotations

import json

from hydra_editor_urdf import i18n


def test_load_config_missing_file_returns_empty_dict(tmp_path, monkeypatch):
    monkeypatch.setattr(i18n, "CONFIG_FILE_PATH", tmp_path / "config.json")
    assert i18n.load_config() == {}


def test_load_config_reads_real_json(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"language": "spanish"}), encoding="utf-8")
    monkeypatch.setattr(i18n, "CONFIG_FILE_PATH", config_path)
    assert i18n.load_config() == {"language": "spanish"}


def test_load_config_non_dict_json_returns_empty_dict(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    monkeypatch.setattr(i18n, "CONFIG_FILE_PATH", config_path)
    assert i18n.load_config() == {}


def test_load_config_corrupt_json_returns_empty_dict_not_a_crash(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text("{not valid json", encoding="utf-8")
    monkeypatch.setattr(i18n, "CONFIG_FILE_PATH", config_path)
    assert i18n.load_config() == {}


def test_save_config_writes_and_merges(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setattr(i18n, "CONFIG_FILE_PATH", config_path)

    assert i18n.save_config({"language": "german"}) is True
    assert i18n.load_config() == {"language": "german"}

    assert i18n.save_config({"theme": "dark"}) is True
    assert i18n.load_config() == {"language": "german", "theme": "dark"}


def test_save_config_leaves_no_leftover_tmp_file(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setattr(i18n, "CONFIG_FILE_PATH", config_path)
    i18n.save_config({"language": "french"})
    assert list(tmp_path.glob("*.tmp")) == []


def test_load_language_parses_key_value_pairs(tmp_path, monkeypatch):
    lang_dir = tmp_path / "language"
    lang_dir.mkdir()
    (lang_dir / "english.lng").write_text("GREETING=Hello\nFAREWELL=Bye\n", encoding="utf-8")
    monkeypatch.setattr(i18n, "LANGUAGE_FOLDER", lang_dir)
    result = i18n.load_language("english")
    assert result == {"GREETING": "Hello", "FAREWELL": "Bye"}


def test_load_language_skips_comments_and_blank_lines(tmp_path, monkeypatch):
    lang_dir = tmp_path / "language"
    lang_dir.mkdir()
    (lang_dir / "english.lng").write_text("# a comment\n\nKEY=Value\n", encoding="utf-8")
    monkeypatch.setattr(i18n, "LANGUAGE_FOLDER", lang_dir)
    assert i18n.load_language("english") == {"KEY": "Value"}


def test_load_language_unescapes_literal_newlines(tmp_path, monkeypatch):
    lang_dir = tmp_path / "language"
    lang_dir.mkdir()
    (lang_dir / "english.lng").write_text("MULTILINE=line one\\nline two\n", encoding="utf-8")
    monkeypatch.setattr(i18n, "LANGUAGE_FOLDER", lang_dir)
    assert i18n.load_language("english")["MULTILINE"] == "line one\nline two"


def test_load_language_missing_file_returns_empty_dict(tmp_path, monkeypatch):
    monkeypatch.setattr(i18n, "LANGUAGE_FOLDER", tmp_path / "language")
    assert i18n.load_language("does-not-exist") == {}


def test_load_language_handles_utf8_bom(tmp_path, monkeypatch):
    lang_dir = tmp_path / "language"
    lang_dir.mkdir()
    (lang_dir / "english.lng").write_bytes(b"\xef\xbb\xbfKEY=Value\n")
    monkeypatch.setattr(i18n, "LANGUAGE_FOLDER", lang_dir)
    result = i18n.load_language("english")
    assert result == {"KEY": "Value"}
    assert "﻿KEY" not in result


def test_lookup_falls_back_to_the_key_itself_when_missing(monkeypatch):
    monkeypatch.setattr(i18n, "_translations", {"HELLO": "Hola"})
    assert i18n._("HELLO") == "Hola"
    assert i18n._("MISSING_KEY") == "MISSING_KEY"


def test_lookup_applies_keyword_substitution(monkeypatch):
    monkeypatch.setattr(i18n, "_translations", {"GREETING": "Hola, {name}!"})
    assert i18n._("GREETING", name="Juan") == "Hola, Juan!"


def test_lookup_missing_substitution_key_returns_unsubstituted_text(monkeypatch):
    monkeypatch.setattr(i18n, "_translations", {"GREETING": "Hola, {name}!"})
    assert i18n._("GREETING", wrong_kwarg="x") == "Hola, {name}!"


def test_current_language_reflects_module_state(monkeypatch):
    monkeypatch.setattr(i18n, "_current_language", "italian")
    assert i18n.current_language() == "italian"
