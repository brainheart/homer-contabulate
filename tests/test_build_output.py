from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "docs" / "data"
LINES_PATH = ROOT / "docs" / "lines" / "all_lines.json"


def load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def test_expected_json_files_exist_and_are_non_empty():
    expected = [
        DATA_DIR / "plays.json",
        DATA_DIR / "characters.json",
        DATA_DIR / "chunks.json",
        DATA_DIR / "tokens.json",
        DATA_DIR / "tokens2.json",
        DATA_DIR / "tokens3.json",
        DATA_DIR / "tokens_char.json",
        DATA_DIR / "tokens_char2.json",
        DATA_DIR / "tokens_char3.json",
        DATA_DIR / "character_name_filter_config.json",
        LINES_PATH,
    ]
    for path in expected:
        assert path.exists(), f"Missing build artifact: {path}"
        assert path.stat().st_size > 0, f"Empty build artifact: {path}"


def test_plays_and_books_have_expected_shape():
    plays = load_json(DATA_DIR / "plays.json")
    characters = load_json(DATA_DIR / "characters.json")

    assert [play["title"] for play in plays] == ["Iliad", "Odyssey"]
    assert all(play["num_acts"] == 24 for play in plays)
    assert len(characters) == 48
    assert characters[0]["name"] == "Ῥαψῳδία α"
    assert characters[-1]["name"] == "Ῥαψῳδία ω"


def test_chunks_lines_and_token_indexes_are_consistent():
    chunks = load_json(DATA_DIR / "chunks.json")
    all_lines = load_json(LINES_PATH)
    tokens = load_json(DATA_DIR / "tokens.json")
    tokens2 = load_json(DATA_DIR / "tokens2.json")
    tokens3 = load_json(DATA_DIR / "tokens3.json")

    assert len(chunks) == len(all_lines)
    assert len(chunks) > 27000

    chunk_ids = {chunk["scene_id"] for chunk in chunks}
    line_ids = {line["line_num"] for line in all_lines}
    assert chunk_ids == line_ids

    first_chunk = chunks[0]
    first_line = all_lines[0]
    assert first_chunk["canonical_id"] == "Il.1.1"
    assert first_line["text"].startswith("μῆνιν ἄειδε")
    assert first_chunk["act_label"] == "Ῥαψῳδία α"

    for index in (tokens, tokens2, tokens3):
        sample_postings = next(iter(index.values()))
        assert sample_postings
        assert sample_postings[0][0] in chunk_ids
        assert sample_postings[0][1] > 0


def test_expected_homeric_terms_exist():
    tokens = load_json(DATA_DIR / "tokens.json")
    tokens2 = load_json(DATA_DIR / "tokens2.json")

    assert "μῆνιν" in tokens
    assert "ἄνδρα" in tokens
    assert "μῆνιν ἄειδε" in tokens2
