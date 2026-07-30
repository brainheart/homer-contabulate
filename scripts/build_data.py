#!/usr/bin/env python3
"""Build static data files for the Homer contabulate app."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "docs" / "data"
LINES_DIR = ROOT / "docs" / "lines"
TEI_NS = "http://www.tei-c.org/ns/1.0"
NS = {"tei": TEI_NS}
TOKEN_RE = re.compile(r"[^\W\d_]+(?:[᾽'][^\W\d_]+)?", re.UNICODE)

GREEK_BOOK_LETTERS = [
    "α", "β", "γ", "δ", "ε", "ζ", "η", "θ", "ι", "κ", "λ", "μ",
    "ν", "ξ", "ο", "π", "ρ", "σ", "τ", "υ", "φ", "χ", "ψ", "ω",
]

WORK_SPECS = [
    {
        "title": "Iliad",
        "display_title": "Ἰλιάς",
        "abbr": "Il.",
        "source": ROOT / "source_text" / "iliad.xml",
        "play_id": 1,
        "sort_prefix": "01",
    },
    {
        "title": "Odyssey",
        "display_title": "Ὀδύσσεια",
        "abbr": "Od.",
        "source": ROOT / "source_text" / "odyssey.xml",
        "play_id": 2,
        "sort_prefix": "02",
    },
]


def tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_RE.finditer(text or "")]


def ngrams(tokens: list[str], n: int) -> list[str]:
    return [" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, separators=(",", ":"), ensure_ascii=False)


def dedup_postings(index: dict[str, list[list[int]]]) -> dict[str, list[list[int]]]:
    result: dict[str, list[list[int]]] = {}
    for term, postings in index.items():
        merged: dict[int, int] = {}
        for chunk_id, count in postings:
            merged[chunk_id] = merged.get(chunk_id, 0) + count
        result[term] = [[chunk_id, count] for chunk_id, count in sorted(merged.items())]
    return result


def build_character_indexes(characters: list[dict]) -> tuple[dict, dict, dict]:
    tokens1 = defaultdict(list)
    tokens2 = defaultdict(list)
    tokens3 = defaultdict(list)

    for character in characters:
        character_id = character["character_id"]
        name_tokens = tokenize(f"{character['play_title']} {character['name']}")
        counts1 = Counter(name_tokens)
        counts2 = Counter(ngrams(name_tokens, 2))
        counts3 = Counter(ngrams(name_tokens, 3))

        for term, count in counts1.items():
            tokens1[term].append([character_id, count])
        for term, count in counts2.items():
            tokens2[term].append([character_id, count])
        for term, count in counts3.items():
            tokens3[term].append([character_id, count])

    return dedup_postings(tokens1), dedup_postings(tokens2), dedup_postings(tokens3)


def parse_work(spec: dict, chunk_start: int, character_start: int):
    tree = ET.parse(spec["source"])
    root = tree.getroot()
    body = root.find(".//tei:body", NS)
    if body is None:
        raise ValueError(f"No <body> found in {spec['source']}")

    book_divs = []
    for div in body.findall(".//tei:div", NS):
        n = (div.attrib.get("n") or "").strip()
        if not n.isdigit():
            continue
        subtype = (div.attrib.get("subtype") or "").lower()
        typ = (div.attrib.get("type") or "").lower()
        if subtype == "book" or typ == "textpart":
            book_divs.append(div)

    book_divs.sort(key=lambda div: int(div.attrib["n"]))
    if not book_divs:
        raise ValueError(f"No book divs found in {spec['source']}")

    characters = []
    chunks = []
    lines = []
    tokens1 = defaultdict(list)
    tokens2 = defaultdict(list)
    tokens3 = defaultdict(list)
    act_totals = Counter()
    act_line_totals = Counter()

    chunk_id = chunk_start
    character_id = character_start
    work_total_words = 0
    work_total_lines = 0

    for book_div in book_divs:
        book_n = int(book_div.attrib["n"])
        book_letter = GREEK_BOOK_LETTERS[book_n - 1] if 1 <= book_n <= len(GREEK_BOOK_LETTERS) else str(book_n)
        book_label = f"Ῥαψῳδία {book_letter}"
        character_id += 1
        characters.append({
            "character_id": character_id,
            "play_id": spec["play_id"],
            "play_title": spec["title"],
            "name": book_label,
            "gender": "A",
            "num_speeches": 0,
            "total_words_spoken": 0,
            "book_number": book_n,
        })

        for l_elem in book_div.iterfind(".//tei:l", NS):
            line_n_raw = (l_elem.attrib.get("n") or "").strip()
            if not line_n_raw:
                continue
            try:
                line_n = int(line_n_raw)
            except ValueError:
                continue

            text = " ".join("".join(l_elem.itertext()).split())
            if not text:
                continue

            chunk_id += 1
            toks = tokenize(text)
            total_words = len(toks)
            canonical_id = f"{spec['abbr']}{book_n}.{line_n}"
            location = f"{spec['sort_prefix']}.{spec['abbr'].rstrip('.')}.{book_n:03d}.{line_n:04d}"

            chunks.append({
                "scene_id": chunk_id,
                "canonical_id": canonical_id,
                "location": location,
                "play_id": spec["play_id"],
                "play_title": spec["title"],
                "play_abbr": spec["abbr"],
                "genre": "Epic",
                "act": book_n,
                "act_label": book_label,
                "scene": line_n,
                "heading": f"{spec['title']} {book_label}, {line_n}",
                "total_words": total_words,
                "unique_words": len(set(toks)),
                "num_speeches": 0,
                "num_lines": 1,
                "characters_present_count": 1,
            })
            lines.append({
                "play_id": spec["play_id"],
                "canonical_id": canonical_id,
                "location": location,
                "act": book_n,
                "act_label": book_label,
                "scene": line_n,
                "line_num": chunk_id,
                "text": text,
            })

            counts1 = Counter(toks)
            counts2 = Counter(ngrams(toks, 2))
            counts3 = Counter(ngrams(toks, 3))
            for term, count in counts1.items():
                tokens1[term].append([chunk_id, count])
            for term, count in counts2.items():
                tokens2[term].append([chunk_id, count])
            for term, count in counts3.items():
                tokens3[term].append([chunk_id, count])

            act_totals[book_n] += total_words
            act_line_totals[book_n] += 1
            work_total_words += total_words
            work_total_lines += 1

    play = {
        "play_id": spec["play_id"],
        "location": f"{spec['sort_prefix']}.{spec['abbr'].rstrip('.')}",
        "title": spec["title"],
        "display_title": spec["display_title"],
        "abbr": spec["abbr"],
        "genre": "Epic",
        "first_performance_year": None,
        "num_acts": len(book_divs),
        "num_scenes": work_total_lines,
        "num_speeches": 0,
        "total_words": work_total_words,
        "total_lines": work_total_lines,
    }

    for character in characters:
        book_n = character["book_number"]
        character["total_words_spoken"] = act_totals[book_n]
        character["num_lines"] = act_line_totals[book_n]
        character["act_label"] = character["name"]
        del character["book_number"]

    return {
        "play": play,
        "characters": characters,
        "chunks": chunks,
        "lines": lines,
        "tokens1": tokens1,
        "tokens2": tokens2,
        "tokens3": tokens3,
        "last_chunk_id": chunk_id,
        "last_character_id": character_id,
    }


def build() -> None:
    plays = []
    characters = []
    chunks = []
    all_lines = []
    tokens1 = defaultdict(list)
    tokens2 = defaultdict(list)
    tokens3 = defaultdict(list)

    chunk_id = 0
    character_id = 0
    for spec in WORK_SPECS:
        parsed = parse_work(spec, chunk_id, character_id)
        plays.append(parsed["play"])
        characters.extend(parsed["characters"])
        chunks.extend(parsed["chunks"])
        all_lines.extend(parsed["lines"])
        for term, postings in parsed["tokens1"].items():
            tokens1[term].extend(postings)
        for term, postings in parsed["tokens2"].items():
            tokens2[term].extend(postings)
        for term, postings in parsed["tokens3"].items():
            tokens3[term].extend(postings)
        chunk_id = parsed["last_chunk_id"]
        character_id = parsed["last_character_id"]

    tokens1 = dedup_postings(tokens1)
    tokens2 = dedup_postings(tokens2)
    tokens3 = dedup_postings(tokens3)
    tokens_char, tokens_char2, tokens_char3 = build_character_indexes(characters)

    write_json(DATA_DIR / "plays.json", plays)
    write_json(DATA_DIR / "characters.json", characters)
    write_json(DATA_DIR / "chunks.json", chunks)
    write_json(DATA_DIR / "tokens.json", tokens1)
    write_json(DATA_DIR / "tokens2.json", tokens2)
    write_json(DATA_DIR / "tokens3.json", tokens3)
    write_json(DATA_DIR / "tokens_char.json", tokens_char)
    write_json(DATA_DIR / "tokens_char2.json", tokens_char2)
    write_json(DATA_DIR / "tokens_char3.json", tokens_char3)
    write_json(DATA_DIR / "character_name_filter_config.json", {
        "enabled": False,
        "notes": ["Disabled: this corpus does not yet have a reviewed proper-name list."],
        "global_additions": [], "global_removals": [],
        "play_additions": {}, "play_removals": {},
    })
    write_json(LINES_DIR / "all_lines.json", all_lines)

    print(
        f"Built {len(plays)} works, {len(characters)} books, {len(chunks)} lines, "
        f"{len(tokens1)} unigrams, {len(tokens2)} bigrams, {len(tokens3)} trigrams."
    )


if __name__ == "__main__":
    build()
