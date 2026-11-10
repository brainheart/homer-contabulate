"""Sanity checks on the generated Homer build output."""

import json
import unittest
from collections import Counter
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "docs" / "data"
LINES_DIR = Path(__file__).parent.parent / "docs" / "lines"


class TestBuildOutputExists(unittest.TestCase):
    EXPECTED_FILES = [
        "plays.json",
        "chunks.json",
        "characters.json",
        "tokens.json",
        "tokens2.json",
        "tokens3.json",
        "tokens_char.json",
        "tokens_char2.json",
        "tokens_char3.json",
        "character_name_filter_config.json",
    ]

    def test_all_data_files_exist(self):
        for filename in self.EXPECTED_FILES:
            self.assertTrue((DATA_DIR / filename).exists(), f"{filename} must exist")

    def test_no_commentary_data_ships(self):
        self.assertFalse((DATA_DIR / "commentary_interest.json").exists())

    def test_lines_file_exists(self):
        self.assertTrue((LINES_DIR / "all_lines.json").exists(), "all_lines.json must exist")


class TestWorks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.works = json.loads((DATA_DIR / "plays.json").read_text())

    def test_has_2_works(self):
        self.assertEqual(len(self.works), 2)

    def test_work_has_required_fields(self):
        required = {
            "play_id",
            "location",
            "title",
            "abbr",
            "genre",
            "first_performance_year",
            "total_words",
            "total_lines",
            "num_acts",
            "num_scenes",
            "mattr_50",
        }
        for work in self.works:
            self.assertTrue(required.issubset(work.keys()), f"Missing fields for {work.get('title')}")
            self.assertEqual(work["num_scenes"], work["total_lines"])

    def test_genre_counts(self):
        counts = Counter(work["genre"] for work in self.works)
        self.assertEqual(counts['Epic'], 2)

    def test_unique_ids_and_abbreviations(self):
        work_ids = [work["play_id"] for work in self.works]
        abbrs = [work["abbr"] for work in self.works]
        self.assertEqual(len(work_ids), len(set(work_ids)))
        self.assertEqual(len(abbrs), len(set(abbrs)))

    def test_locations_follow_catalog_order(self):
        self.assertEqual(self.works[0]["location"], "01.Il")


class TestParagraphs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paragraphs = json.loads((DATA_DIR / "chunks.json").read_text())
        cls.works = {work["play_id"] for work in json.loads((DATA_DIR / "plays.json").read_text())}

    def test_paragraphs_are_present(self):
        self.assertEqual(len(self.paragraphs), 27794)

    def test_first_paragraph_shape(self):
        first = self.paragraphs[0]
        self.assertEqual(first["canonical_id"], "Il.1.1")
        self.assertEqual(first["location"], "01.Il.001.0001")
        self.assertEqual(first["act"], 1)
        self.assertEqual(first["scene"], 1)

    def test_paragraph_has_required_fields(self):
        required = {"scene_id", "canonical_id", "location", "play_id", "act", "scene", "total_words", "num_lines", "hapax_count"}
        for paragraph in self.paragraphs[:25]:
            self.assertTrue(required.issubset(paragraph.keys()))
            self.assertEqual(paragraph["num_lines"], 1)

    def test_all_paragraphs_reference_valid_works(self):
        for paragraph in self.paragraphs:
            self.assertIn(paragraph["play_id"], self.works)

    def test_unique_scene_ids(self):
        paragraph_ids = [paragraph["scene_id"] for paragraph in self.paragraphs]
        self.assertEqual(len(paragraph_ids), len(set(paragraph_ids)))


class TestTokens(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tokens = json.loads((DATA_DIR / "tokens.json").read_text())

    def test_token_index_size(self):
        self.assertGreater(len(self.tokens), 28000)

    def test_homer_vocabulary_present(self):
        for word in ('καὶ', 'θεὸς', 'μῆνιν', 'ἀθήνη'):
            self.assertIn(word, self.tokens)
        self.assertGreater(len(self.tokens["καὶ"]), 1000)

    def test_posting_format(self):
        sample_key = next(iter(self.tokens))
        postings = self.tokens[sample_key]
        self.assertIsInstance(postings, list)
        self.assertGreater(len(postings), 0)
        for posting in postings[:5]:
            self.assertIsInstance(posting, list)
            self.assertEqual(len(posting), 2)
            self.assertIsInstance(posting[0], int)
            self.assertIsInstance(posting[1], int)


class TestParagraphRows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = json.loads((LINES_DIR / "all_lines.json").read_text())
        cls.paragraphs = json.loads((DATA_DIR / "chunks.json").read_text())

    def test_all_lines_matches_paragraph_count(self):
        self.assertEqual(len(self.rows), len(self.paragraphs))

    def test_rows_align_with_chunks_by_canonical_id(self):
        for row, chunk in zip(self.rows[:100], self.paragraphs[:100]):
            self.assertEqual(row["canonical_id"], chunk["canonical_id"])
        self.assertTrue(self.rows[0]["text"].strip())
        self.assertTrue(self.rows[-1]["text"].strip())


class TestPublishedMetadata(unittest.TestCase):
    def test_hapax_counts_and_instance_json(self):
        chunks = json.loads((DATA_DIR / "chunks.json").read_text())
        self.assertIn("hapax_count", chunks[0])
        self.assertGreater(sum(c["hapax_count"] for c in chunks), 8000)
        instance = json.loads((DATA_DIR.parent / "instance.json").read_text())
        self.assertEqual(instance["id"], "homer")
        self.assertEqual(instance["language"], "Greek")
        self.assertEqual(instance["created"], "2026-03-31")
        self.assertEqual(instance["stats"]["texts"], 2)
        self.assertEqual(instance["stats"]["segments"], 27794)
        self.assertEqual(instance["stats"]["words"], 199084)
        self.assertEqual(instance["stats"]["segment_label"], "lines")
        self.assertEqual(instance["stats"]["commentaries"], 0)
        self.assertEqual(instance["stats"]["comments"], 0)

    def test_characters_hold_per_book_aggregates_not_names(self):
        # characters.json here is repurposed as per-book aggregates
        # (the UI's proper-name toggle stays hidden for this corpus)
        chars = json.loads((DATA_DIR / "characters.json").read_text())
        self.assertEqual(len(chars), 48)
        self.assertTrue(all(c["name"].startswith("Ῥαψῳδία") for c in chars))


class TestGlossary(unittest.TestCase):
    """The English reading aids: treebank lemmas, Logeion glosses."""

    @classmethod
    def setUpClass(cls):
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        import build_data
        import glossary
        cls.module = glossary
        cls.tokenize = staticmethod(build_data.tokenize)
        cls.glossary = json.loads((DATA_DIR / "glossary.json").read_text(encoding="utf-8"))
        cls.tokens = json.loads((DATA_DIR / "tokens.json").read_text(encoding="utf-8"))
        cls.lines = json.loads((LINES_DIR / "all_lines.json").read_text(encoding="utf-8"))
        cls.lemmas = cls.glossary["lemmas"]
        cls.forms = cls.glossary["forms"]
        cls.by_lemma = {e["lemma"]: e for e in reversed(cls.lemmas)}

    def test_sources_are_pinned_and_attributed(self):
        root = Path(__file__).parent.parent / "source_text"
        self.assertEqual(self.module.sha256(root / "treebank" / "lemmas.tsv"), self.module.EXTRACT_SHA256)
        self.assertEqual(len(self.module.load_shortdefs(root / "lexicon" / self.module.SHORTDEFS_FILE)["ἀνήρ"]), len("a man"))
        self.assertEqual(self.glossary["meta"], {"lang": "grc", "dir": "ltr"})
        self.assertIn("Perseus Ancient Greek Dependency Treebank", self.glossary["source"])
        self.assertIn("Logeion", self.glossary["source"])

    def test_words_take_lemmas_from_the_treebank(self):
        root = Path(__file__).parent.parent / "source_text"
        shortdefs = self.module.load_shortdefs(root / "lexicon" / self.module.SHORTDEFS_FILE)
        notes, stats = self.module.annotate(self.lines, root / "treebank", self.tokenize, shortdefs)
        self.assertEqual(stats["words"], 199084)
        self.assertGreater(stats["lines_identical"], 26000)
        self.assertLess(stats["words_without_lemma"], 100)
        self.assertEqual([n[0] for n in notes["Il.1.1"]], ["μῆνις", "ἀείδω", "θεά", "Πηληιάδης", "Ἀχιλλεύς"])
        self.assertEqual([n[0] for n in notes["Od.1.1"]][:3], ["ἀνήρ", "ἐγώ", "ἐνέπω"])
        for row in self.lines:
            self.assertEqual(len(notes[row["canonical_id"]]), len(self.tokenize(row["text"])))

    def test_matching_ignores_elision_marks_but_keeps_breathings(self):
        key = self.module.match_key
        self.assertEqual(key("δ\u0313"), "δ")            # the treebank's elision mark
        self.assertEqual(key("μυρίʼ"), key("μυρί\u0313"))
        self.assertEqual(key("οὐ"), "οὐ")                 # a breathing, not an elision
        self.assertEqual(key("Μῆνιν"), "μῆνιν")
        self.assertEqual(self.module.acute("οὐδὲ"), "οὐδέ")
        self.assertEqual(self.module.bare("θνῄσκω"), "θνησκω")

    def test_forms_cover_the_vocabulary_exactly(self):
        self.assertEqual(set(self.forms), set(self.tokens))
        for form, (count, glosses, related) in self.forms.items():
            self.assertEqual(count, sum(c for _, c in self.tokens[form]), form)
            self.assertTrue(all(0 <= i < len(self.lemmas) for i in related))
        self.assertEqual(self.forms["μῆνιν"][1], ["wrath, anger"])
        self.assertLess(sum(1 for entry in self.forms.values() if not entry[1]), 900)

    def test_lemmas_and_glosses(self):
        self.assertEqual(len(self.lemmas), 8816)
        self.assertEqual([e["n"] for e in self.lemmas], sorted((e["n"] for e in self.lemmas), reverse=True))
        for entry in self.lemmas:
            self.assertEqual(entry["n"], sum(count for _, count in entry["forms"]))
        self.assertEqual(dict(self.by_lemma["μῆνις"]["forms"]), {"μῆνιν": 12, "μῆνις": 3, "μήνιος": 1})
        self.assertEqual(self.by_lemma["μῆνις"]["w"], [["wrath", 16], ["anger", 8]])
        self.assertEqual(self.by_lemma["ναῦς"]["def"], "a ship")
        # A compound the treebank writes as two words is one dictionary form here.
        self.assertEqual(self.by_lemma["οὐδέ"]["n"], 658)
        # Glosses this instance supplies for headwords the list lacks.
        self.assertEqual(self.by_lemma["ἕ"]["def"], "him, her, it (third-person pronoun)")
        unglossed = sum(e["n"] for e in self.lemmas if not e["def"])
        self.assertLess(unglossed / 199084, 0.015)


if __name__ == "__main__":
    unittest.main()
