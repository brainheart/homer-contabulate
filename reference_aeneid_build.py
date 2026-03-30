#!/usr/bin/env python3
"""Build static data files for the Aeneid contabulate app.

Source: PerseusDL TEI XML (phi0690.phi003.perseus-lat2.xml)
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source_text" / "phi0690.phi003.perseus-lat2.xml"
DATA_DIR = ROOT / "docs" / "data"
LINES_DIR = ROOT / "docs" / "lines"

TEI_NS = "http://www.tei-c.org/ns/1.0"
TOKEN_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]+", re.UNICODE)

BOOK_TITLES = {
    "1": "Liber I",
    "2": "Liber II",
    "3": "Liber III",
    "4": "Liber IV",
    "5": "Liber V",
    "6": "Liber VI",
    "7": "Liber VII",
    "8": "Liber VIII",
    "9": "Liber IX",
    "10": "Liber X",
    "11": "Liber XI",
    "12": "Liber XII",
}


def tokenize(text):
    return TOKEN_RE.findall((text or "").lower())


def ngrams(tokens, n):
    return [" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, separators=(",", ":"), ensure_ascii=False)


def build():
    tree = ET.parse(SOURCE)
    root = tree.getroot()

    # Find the body/div containing book divs
    body = root.find(f".//{{{TEI_NS}}}body")
    if body is None:
        print("ERROR: no <body> found", file=sys.stderr)
        sys.exit(1)

    # Find all book-level divs
    book_divs = []
    for div in body.iter(f"{{{TEI_NS}}}div"):
        subtype = div.attrib.get("subtype", "")
        typ = div.attrib.get("type", "")
        n = div.attrib.get("n", "")
        if (subtype == "book" or typ == "textpart") and n.isdigit():
            book_divs.append(div)

    if not book_divs:
        print("ERROR: no book divs found", file=sys.stderr)
        sys.exit(1)

    plays = []
    chunks = []
    all_lines = []
    tokens1 = defaultdict(list)
    tokens2 = defaultdict(list)
    tokens3 = defaultdict(list)

    chunk_id = 0

    for book_div in book_divs:
        book_n = book_div.attrib.get("n", "0")
        book_id = int(book_n)
        book_title = BOOK_TITLES.get(book_n, f"Liber {book_n}")
        book_abbr = f"Aen.{book_n}"

        book_total_words = 0
        book_total_lines = 0
        book_unique_words = set()

        # Collect all <l> elements in this book
        for l_elem in book_div.iter(f"{{{TEI_NS}}}l"):
            line_n_raw = l_elem.attrib.get("n", "")
            if not line_n_raw:
                continue
            try:
                line_n = int(line_n_raw)
            except ValueError:
                continue

            # Get full text content of the line element
            text = "".join(l_elem.itertext()).strip()
            if not text:
                continue

            chunk_id += 1
            toks = tokenize(text)
            total_words = len(toks)
            unique_words = len(set(toks))

            book_total_words += total_words
            book_total_lines += 1
            book_unique_words.update(toks)

            canonical_id = f"Aen.{book_n}.{line_n}"
            location = f"{int(book_n):02d}.Aen.{int(book_n):03d}.{int(line_n):04d}"

            chunk = {
                "scene_id": chunk_id,
                "canonical_id": canonical_id,
                "location": location,
                "play_id": book_id,
                "play_title": book_title,
                "play_abbr": book_abbr,
                "genre": "Epic",
                "act": 1,
                "scene": line_n,
                "heading": f"{book_title}, {line_n}",
                "total_words": total_words,
                "unique_words": unique_words,
                "num_speeches": 0,
                "num_lines": 1,
                "characters_present_count": 0,
            }
            chunks.append(chunk)

            all_lines.append({
                "play_id": book_id,
                "canonical_id": canonical_id,
                "location": location,
                "act": 1,
                "scene": line_n,
                "line_num": chunk_id,
                "text": text,
            })

            # Build token indices
            for tok in toks:
                tokens1[tok].append([chunk_id, toks.count(tok)])
            for bg in ngrams(toks, 2):
                tokens2[bg].append([chunk_id, 1])
            for tg in ngrams(toks, 3):
                tokens3[tg].append([chunk_id, 1])

        play = {
            "play_id": book_id,
            "location": f"{int(book_n):02d}.Aen",
            "title": book_title,
            "abbr": book_abbr,
            "genre": "Epic",
            "first_performance_year": None,
            "num_acts": 1,
            "num_scenes": book_total_lines,
            "num_speeches": 0,
            "total_words": book_total_words,
            "total_lines": book_total_lines,
        }
        plays.append(play)

    # Deduplicate token postings (same chunk_id can appear multiple times)
    def dedup_postings(tok_dict):
        result = {}
        for term, postings in tok_dict.items():
            merged = {}
            for cid, count in postings:
                merged[cid] = merged.get(cid, 0) + count
            result[term] = [[cid, cnt] for cid, cnt in sorted(merged.items())]
        return result

    tokens1 = dedup_postings(tokens1)
    tokens2 = dedup_postings(tokens2)
    tokens3 = dedup_postings(tokens3)

    # Write outputs
    write_json(DATA_DIR / "plays.json", plays)
    write_json(DATA_DIR / "chunks.json", chunks)
    write_json(DATA_DIR / "tokens.json", tokens1)
    write_json(DATA_DIR / "tokens2.json", tokens2)
    write_json(DATA_DIR / "tokens3.json", tokens3)
    write_json(LINES_DIR / "all_lines.json", all_lines)

    # Empty placeholders the frontend may expect
    write_json(DATA_DIR / "characters.json", [])
    write_json(DATA_DIR / "character_name_filter_config.json", {})
    write_json(DATA_DIR / "tokens_char.json", {})
    write_json(DATA_DIR / "tokens_char2.json", {})
    write_json(DATA_DIR / "tokens_char3.json", {})

    print(f"Built {len(plays)} books, {len(chunks)} lines, "
          f"{len(tokens1)} unigrams, {len(tokens2)} bigrams, {len(tokens3)} trigrams.")


if __name__ == "__main__":
    build()
