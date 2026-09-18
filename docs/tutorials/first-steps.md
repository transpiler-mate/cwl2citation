# Generate your first citations

After [installation](../how-to/install.md), run from the project checkout:

```sh
transpiler-mate cwl2citation --output example-citations tests/fixtures/hello.cwl#hello
```

The directory contains `CITATION.cff`, `citation.bib`, `citation.ris`, `citation.csl.json`, and `citation.txt`.

The fixture has no DOI or release date. APA therefore produces an undated citation rather than inventing publication metadata:

```text
Author, E. (n.d.). Hello (Version 0.1.0) [Computer software]. Example Organization.
```

Try another style in a different directory:

```sh
transpiler-mate cwl2citation --format text --style ieee --released 2026-09-18 \
  --output example-ieee tests/fixtures/hello.cwl#hello
```

Use your real publication date when citing published software.
