# CWL 2 Citation

[![PyPI - Version](https://img.shields.io/pypi/v/cwl2citation.svg)](https://pypi.org/project/cwl2citation)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/cwl2citation.svg)](https://pypi.org/project/cwl2citation)
[![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/transpiler-mate/cwl2citation/package.yaml?branch=develop&event=push&label=build&logo=githubactions)](https://github.com/transpiler-mate/cwl2citation/actions/workflows/package.yaml?query=branch%3Adevelop)
[![Code coverage](https://img.shields.io/codecov/c/github/transpiler-mate/cwl2citation/develop?logo=codecov)](https://app.codecov.io/gh/transpiler-mate/cwl2citation/tree/develop)

Generate a citation experience for CWL software with a Transpiler-Mate plugin: **CFF, BibTeX, RIS, CSL-JSON, and styled text** from the same metadata.

Bootstrapped from [transpiler-mate-plugin-project-template](https://github.com/transpiler-mate/transpiler-mate-plugin-project-template).

## Install

From this checkout (Python 3.10+):

```sh
pip install transpiler-mate-runtime .
```

## Generate citations

```sh
transpiler-mate cwl2citation --output citations workflow.cwl#main
```

| File | Purpose |
| --- | --- |
| `CITATION.cff` | Software citation metadata for GitHub and CFF consumers |
| `citation.bib` | BibTeX `@misc` entry, including software version |
| `citation.ris` | RIS `COMP` entry for reference managers |
| `citation.csl.json` | CSL-JSON array containing one software record |
| `citation.txt` | Plain-text bibliography entry, APA by default |

Select formats and a citation style:

```sh
transpiler-mate cwl2citation --format bibtex --format text --style ieee \
  --released 2026-09-18 --output citations-ieee workflow.cwl#main
```

`--doi`, `--url`, and `--code-repository` provide optional publication metadata. `--style` accepts a packaged CSL style name or local independent CSL file; `--locale` defaults to `en-US`. Existing output files are never overwritten.

Citations use document-level Schema.org metadata parsed by Transpiler-Mate. A fragment validates the selected process; it does not create separate step-level citation metadata. Authors retain their order. Missing DOI and publication dates remain absent: `dateCreated` is not a release date. A DOI is read from the software identifier when present or supplied through `--doi`; the plugin does not mint or resolve DOIs.

CFF and CSL-JSON are schema-validated. Styled output uses citeproc-py and packaged CSL styles, so exact formatting depends on the style and processor support. These exports cite the workflow software; they do not reproduce every Zenodo record metadata export or publish to Zenodo.

See [CLI documentation](docs/how-to/use-cli.md), [metadata mapping](docs/reference/index.md), and [third-party notices](THIRD_PARTY.md).

## Development

```sh
pip install -e '.[test]'
pytest
hatch run dev:typecheck
hatch run dev:ruff check src tests
hatch run dev:ruff format --check src tests
hatch run dev:security
pip install -r requirements-docs.txt
mkdocs build --strict
```


## License

[![Apache License, Version 2.0](https://img.shields.io/badge/license-Apache%20License%202.0-blue)](https://www.apache.org/licenses/LICENSE-2.0) for project code; bundled schemas retain their upstream licenses.
