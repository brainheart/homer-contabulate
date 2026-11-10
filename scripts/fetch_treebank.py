#!/usr/bin/env python3
"""Download the pinned Perseus treebank files and rebuild the lemma extract.

The treebank XML is 36 MB, so the repository keeps only
`source_text/treebank/lemmas.tsv` (work, book.line, form, lemma, part of
speech). This script reproduces that extract from the pinned commit and
prints its SHA-256, which `scripts/glossary.py` checks on every build.
"""
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import glossary

RAW = glossary.ROOT / "source_text" / "treebank" / "raw"


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for name, digest in glossary.TREEBANKS.values():
        path = RAW / name
        if not path.exists() or glossary.sha256(path) != digest:
            print(f"Downloading {name}")
            urllib.request.urlretrieve(glossary.TREEBANK_BASE + name, path)
    out = glossary.ROOT / "source_text" / "treebank" / glossary.EXTRACT_FILE
    rows = glossary.extract_treebank(RAW, out)
    print(f"{rows} words -> {out}\nsha256 {glossary.sha256(out)}")


if __name__ == "__main__":
    main()
