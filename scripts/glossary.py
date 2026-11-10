"""English reading aids for Homer: a dictionary form and gloss for every word.

Dictionary forms (lemmas) come from the Perseus Ancient Greek Dependency
Treebank, which annotates every word of the same Perseus editions this
instance shows, line by line. Glosses are the Logeion/Perseus short
definitions. Words are matched to the treebank within each line; a word the
treebank spells differently takes the lemma its written form has elsewhere.
"""
import difflib
import hashlib
import re
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TREEBANK_COMMIT = "bf4334f0af5e13d16b04c1cccd6237e683ac6f5f"
TREEBANK_BASE = f"https://raw.githubusercontent.com/PerseusDL/treebank_data/{TREEBANK_COMMIT}/v2.1/Greek/texts/"
TREEBANKS = {
    # work abbreviation as in canonical ids: (file, sha256)
    "Il": ("tlg0012.tlg001.perseus-grc1.tb.xml", "1a7cacbc9460a7acce4a6c7004007619dd8acf1f6e210b3d9f8a3d3e2518c8d9"),
    "Od": ("tlg0012.tlg002.perseus-grc1.tb.xml", "e936cc7d0bb3fe61cd0ca83b047e745b495668d12fefe7d4e434d3818febd31d"),
}
SHORTDEFS_COMMIT = "53d50e3f304cf78dc1d5ef890e4fa50d58d3d747"
SHORTDEFS_URL = f"https://raw.githubusercontent.com/helmadik/shortdefs/{SHORTDEFS_COMMIT}/shortdefsGreekEnglishLogeion"
SHORTDEFS_FILE = "shortdefsGreekEnglishLogeion.txt"
SHORTDEFS_SHA256 = "0f4fb04dd83f98d05e0cc2830a6d15aaa9989a7c9436a08746e3f8547198939e"
POS_LABELS = {
    "n": "noun", "v": "verb", "a": "adjective", "d": "adverb", "l": "article", "g": "particle",
    "c": "conjunction", "r": "preposition", "p": "pronoun", "m": "numeral", "i": "interjection",
}
ELISION_RE = re.compile("[ʼ'᾽’᾿]")
# Words too common in glosses to say what a lemma means. They are indexed
# only for lemmas whose glosses contain nothing else.
STOP_WORDS = frozenset("""
a an the and or of to in on for with by from at as is are was were be been it its he she they them
their his her you your we our us i my me him who whom which that this those these then so but not
no will would shall should may might can could do does did have has had o if when what there than
am one esp etc
""".split())


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def match_key(word):
    """Spelling for matching only: case, elision marks, and Unicode form.
    The treebank marks elision with a combining comma after the last letter,
    which composes with a final vowel into what looks like a breathing."""
    text = unicodedata.normalize("NFD", ELISION_RE.sub("", word).lower())
    if text.endswith("\u0313"):
        # A final comma is an elision mark unless it is the word's own smooth
        # breathing, as in οὐ: a word that begins with a vowel and has no
        # breathing before its last letter.
        body = text[:-1]
        starts_with_vowel = body[:1] in "αεηιουω"
        if not starts_with_vowel or "\u0313" in body or "\u0314" in body:
            text = body
    return unicodedata.normalize("NFC", text)


def acute(word):
    """A word as a dictionary would head it: final grave accent as acute."""
    return unicodedata.normalize("NFC", unicodedata.normalize("NFD", word).replace("\u0300", "\u0301"))


def load_shortdefs(path):
    if sha256(path) != SHORTDEFS_SHA256:
        raise ValueError(f"Source checksum mismatch: {path}")
    defs = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if "\t" in line:
            lemma, gloss = line.split("\t", 1)
            defs.setdefault(unicodedata.normalize("NFC", lemma.strip()), gloss.strip())
    return defs


EXTRACT_FILE = "lemmas.tsv"
EXTRACT_SHA256 = "46ad3a9fccb9ae00dfb535b70c88f308d69ed57aa4e5b120ad915422c06bb854"


def extract_treebank(raw_dir, out_path):
    """Reduce the pinned treebank XML (36 MB) to the four fields used here:
    work, book.line, word form, lemma, part of speech. Run by
    scripts/fetch_treebank.py; the extract is what the repository keeps."""
    rows = []
    for work, (name, digest) in TREEBANKS.items():
        path = Path(raw_dir) / name
        if sha256(path) != digest:
            raise ValueError(f"Source checksum mismatch: {path}")
        for _event, element in ET.iterparse(path):
            if element.tag != "word":
                continue
            cite = element.get("cite", "")
            form = element.get("form", "")
            lemma = element.get("lemma", "")
            postag = element.get("postag", "") or "-"
            if cite and lemma and postag[0] != "u" and any(c.isalpha() for c in form):
                rows.append("\t".join([work, cite.rsplit(":", 1)[-1], form, lemma, postag[0]]))
            element.clear()
    Path(out_path).write_text("\n".join(rows) + "\n", encoding="utf-8")
    return len(rows)


def load_treebank(path):
    """Words by work and `book.line`: [(match key, lemma, part of speech), ...]."""
    if sha256(path) != EXTRACT_SHA256:
        raise ValueError(f"Source checksum mismatch: {path}")
    works = defaultdict(lambda: defaultdict(list))
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        work, reference, form, lemma, pos = line.split("\t")
        works[work][reference].append((match_key(form), unicodedata.normalize("NFC", lemma), pos))
    return works


def annotate(lines, treebank_dir, tokenize, shortdefs=()):
    """One (lemma, pos) or None per displayed word, by canonical id."""
    notes = {}
    stats = Counter()
    treebanks = load_treebank(Path(treebank_dir) / EXTRACT_FILE)
    for row in lines:
        work, reference = row["canonical_id"].split(".", 1)
        tokens = tokenize(row["text"])
        words = treebanks[work].get(reference, [])
        keys = [match_key(t) for t in tokens]
        out = [None] * len(tokens)
        if [w[0] for w in words] == keys:
            out = [(lemma, pos) for _, lemma, pos in words]
            stats["lines_identical"] += 1
        elif words:
            stats["lines_matched_word_by_word"] += 1
            matcher = difflib.SequenceMatcher(a=[w[0] for w in words], b=keys, autojunk=False)
            for tag, a1, a2, b1, b2 in matcher.get_opcodes():
                if tag == "equal":
                    for offset in range(a2 - a1):
                        _, lemma, pos = words[a1 + offset]
                        out[b1 + offset] = (lemma, pos)
                    continue
                # The treebank writes some compounds (οὐδέ, μήτε ...) as two
                # words. The written word is then its own dictionary form if
                # the lexicon has it, and otherwise belongs to its first part.
                cursor = a1
                for b in range(b1, b2):
                    for a in range(cursor, a2 - 1):
                        if words[a][0] + words[a + 1][0] == keys[b]:
                            headword = acute(keys[b])
                            out[b] = (headword, "c") if headword in shortdefs else (words[a][1], words[a][2])
                            stats["words_joined_from_two"] += 1
                            cursor = a + 2
                            break
        else:
            stats["lines_without_treebank"] += 1
        notes[row["canonical_id"]] = out
        stats["words"] += len(tokens)
    by_form = defaultdict(Counter)
    for row in lines:
        for token, note in zip(tokenize(row["text"]), notes[row["canonical_id"]]):
            if note:
                by_form[match_key(token)][note] += 1
    for row in lines:
        out = notes[row["canonical_id"]]
        for i, token in enumerate(tokenize(row["text"])):
            if out[i] is None:
                known = by_form[match_key(token)]
                if known:
                    out[i] = known.most_common(1)[0][0]
                    stats["words_lemma_by_form"] += 1
                else:
                    stats["words_without_lemma"] += 1
    return notes, stats


def gloss_words(gloss):
    plain = re.sub(r"\([^)]*\)", " ", gloss)
    words = [w for w in re.findall(r"[a-z]+(?:'[a-z]+)?", plain.lower()) if w not in STOP_WORDS]
    return words or re.findall(r"[a-z]+(?:'[a-z]+)?", gloss.lower())


def word_index(gloss, count, limit=14):
    """English words of a gloss weighted by the lemma's frequency; words of
    the first sense count in full, later senses half."""
    weights = {}
    for position, sense in enumerate(re.split(r"[,;]", gloss)):
        for word in gloss_words(sense):
            weight = max(1, count if position == 0 else count // 2)
            weights[word] = max(weights.get(word, 0), weight)
    return [[w, c] for w, c in sorted(weights.items(), key=lambda wc: (-wc[1], wc[0]))[:limit]]


# Frequent Homeric headwords the definitions list lacks or files under
# another form. These few glosses are supplied by this instance.
SUPPLIED_GLOSSES = {
    "ἕ": "him, her, it (third-person pronoun)",
    "πέρ": "very, however much; although",
    "πού": "somewhere; I suppose",
    "προσεῖπον": "to speak to, address",
    "ἠέλιος": "the sun",
    "μίγνυμι": "to mix, mingle",
    "Ποσειδεών": "Poseidon",
    "κεῖνος": "that one, he",
    "ἐπήν": "when, whenever",
    "ζώω": "to live",
    "τί": "what? why?",
    "φίλτατος": "dearest",
    "πατρώιος": "of one's father, ancestral",
    "πυκινός": "close, thick; shrewd",
    "σάφα": "clearly, for certain",
    "εἷος": "while, until",
}


def bare(word):
    """Letters only: no accents, breathings, or iota subscript."""
    return "".join(c for c in unicodedata.normalize("NFD", word.lower()) if not unicodedata.combining(c))


def gloss_for(lemma, shortdefs, by_bare_letters):
    """Treebank lemmas may carry a homonym number the definitions lack, and
    the two sources accent some headwords differently (πέρ and περ, θνήσκω
    and θνῄσκω). An exact headword wins; otherwise the letters decide."""
    plain = re.sub(r"\d+$", "", lemma)
    if plain in SUPPLIED_GLOSSES:
        return SUPPLIED_GLOSSES[plain]
    for candidate in (lemma, plain, lemma.lower(), plain.lower()):
        if candidate in shortdefs:
            return shortdefs[candidate]
    # Very short words differ only by their accents; do not guess those.
    letters = bare(plain)
    return by_bare_letters.get(letters, "") if len(letters) >= 4 else ""


def build_glossary(lines, source_dir, tokenize):
    shortdefs = load_shortdefs(Path(source_dir) / "lexicon" / SHORTDEFS_FILE)
    by_bare_letters = {}
    for headword, gloss in shortdefs.items():
        by_bare_letters.setdefault(bare(headword), gloss)
    notes, stats = annotate(lines, Path(source_dir) / "treebank", tokenize, shortdefs)
    form_total = Counter()
    form_lemmas = defaultdict(Counter)
    lemma_forms = defaultdict(Counter)
    lemma_pos = defaultdict(Counter)
    for row in lines:
        for token, note in zip(tokenize(row["text"]), notes[row["canonical_id"]]):
            form_total[token] += 1
            if note:
                lemma, pos = note
                form_lemmas[token][lemma] += 1
                lemma_forms[lemma][token] += 1
                lemma_pos[lemma][pos] += 1
    ordered = sorted(lemma_forms, key=lambda k: (-sum(lemma_forms[k].values()), k))
    index = {lemma: i for i, lemma in enumerate(ordered)}
    lemmas = []
    for lemma in ordered:
        count = sum(lemma_forms[lemma].values())
        gloss = gloss_for(lemma, shortdefs, by_bare_letters)
        if not gloss:
            stats["lemmas_without_gloss"] += 1
            stats["words_of_lemmas_without_gloss"] += count
        lemmas.append({
            "lemma": re.sub(r"\d+$", "", lemma),
            "pos": POS_LABELS.get(lemma_pos[lemma].most_common(1)[0][0], "word"),
            "n": count,
            "def": gloss,
            "en": [],
            "w": word_index(gloss, count) if gloss else [],
            "forms": [[f, c] for f, c in sorted(lemma_forms[lemma].items(), key=lambda fc: (-fc[1], fc[0]))],
        })
    forms = {}
    for form in sorted(form_total):
        related = [index[k] for k, _ in form_lemmas[form].most_common(3)]
        glosses = []
        for i in related[:2]:
            if lemmas[i]["def"] and lemmas[i]["def"] not in glosses:
                glosses.append(lemmas[i]["def"])
        forms[form] = [form_total[form], glosses, related]
    stats["lemmas"] = len(lemmas)
    stats["forms"] = len(forms)
    stats["forms_without_gloss"] = sum(1 for entry in forms.values() if not entry[1])
    return {"forms": forms, "lemmas": lemmas}, stats
