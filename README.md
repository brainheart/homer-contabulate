# Homer Contabulate

Static single-page contabulate search for Homer in Ancient Greek, covering both the *Iliad* and the *Odyssey*.

The app is fully deployable from `docs/` to GitHub Pages. There is no backend and no frontend build step: the site is plain HTML, CSS, JavaScript, and prebuilt JSON data files.

## Source Texts

The Greek source texts in `source_text/` come from the Perseus Digital Library TEI XML editions:

- `source_text/iliad.xml`
- `source_text/odyssey.xml`

Perseus Digital Library: <https://www.perseus.tufts.edu/hopper/>

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
