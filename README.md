# Homer Contabulate

Static single-page contabulate search for Homer in Ancient Greek, covering both the *Iliad* and the *Odyssey*.

The app is fully deployable from `docs/` to GitHub Pages. There is no backend and no frontend build step: the site is plain HTML, CSS, JavaScript, and prebuilt JSON data files.

## Source Texts

The Greek source texts in `source_text/` come from the Perseus Digital Library TEI XML editions:

- `source_text/iliad.xml`
- `source_text/odyssey.xml`

Perseus Digital Library: <https://www.perseus.tufts.edu/hopper/>

## English lookup and glosses

For readers without Greek, a lookup box above the term field finds Greek words by English meaning and inserts them as search terms; the word views add English and Dictionary form columns.

- Dictionary forms come from the Perseus Ancient Greek Dependency Treebank 2.1 (CC BY-SA 3.0), which annotates every word of these same Perseus editions. The treebank XML is 36 MB, so the repository keeps the extract `source_text/treebank/lemmas.tsv`; `python3 scripts/fetch_treebank.py` reproduces it from the pinned commit.
- Glosses are the Logeion/Perseus short definitions in `source_text/lexicon` (`helmadik/shortdefs`, pinned; the repository asks for credit to Perseus and Logeion and states no formal license). Sixteen frequent Homeric headwords the list lacks are glossed in `scripts/glossary.py`.
- `scripts/glossary.py` writes `docs/data/glossary.json` during `scripts/build_data.py`. It is display-only: nothing in it is searched or counted, and the page works without it.
- `docs/js/glossary.js` is shared verbatim with the other non-English Contabulate instances.

## Build

Rebuild the static JSON data:

```bash
python3 scripts/build_data.py
```

This writes:

- `docs/data/plays.json`
- `docs/data/characters.json`
- `docs/data/chunks.json`
- `docs/data/tokens.json`
- `docs/data/tokens2.json`
- `docs/data/tokens3.json`
- `docs/data/tokens_char.json`
- `docs/data/tokens_char2.json`
- `docs/data/tokens_char3.json`
- `docs/data/character_name_filter_config.json`
- `docs/lines/all_lines.json`

The internal data model follows the reference contabulate app contract:

- `plays` = works (`Iliad`, `Odyssey`)
- `characters` = books (`Ῥαψῳδία α` through `Ῥαψῳδία ω`)
- `chunks` = line-level contexts

## Local Preview

Serve the static site locally:

```bash
python3 -m http.server 4173
```

Then open:

```text
http://127.0.0.1:4173/docs/
```

## Tests

Python structure checks:

```bash
python3 -m pytest tests/test_build_output.py
```

Playwright smoke test:

```bash
npx playwright test
```

## Deployment

Publish the contents of `docs/` to GitHub Pages. The custom domain is configured through:

- `docs/CNAME`

with:

```text
homer.contabulate.org
```
