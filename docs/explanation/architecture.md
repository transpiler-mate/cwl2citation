# Architecture

The plugin follows the Transpiler-Mate project template: a Pydantic options model, decorated plugin function, and package entry point. Transpiler-Mate loads CWL and validates its document-level metadata. A requested fragment is resolved before citation generation.

`model.py` creates one `CitationRecord`, preserving author order and validating DOI syntax, ORCID checksums, and explicit publication metadata. Whitespace is normalized so metadata cannot introduce additional RIS records.

`exporters.py` renders each selected format. ruamel.yaml writes CFF, bibtexparser writes escaped BibTeX, rispy writes RIS, and the standard JSON serializer writes CSL-JSON. citeproc-py renders the same CSL record with a packaged or local style. Pinned upstream schemas validate CFF and CSL data without network access.

All selected files are rendered before creating the output directory. Exclusive file creation prevents overwriting existing exports. On a write failure, files created by the invocation are removed. Existing unrelated files are preserved.

This is a software citation tool. It neither runs CWL nor creates execution provenance, retrieves Zenodo records, mints DOIs, or generates every repository metadata export. Optional DOI and publication date fields let the author cite a published release accurately. Style rendering depends on citeproc-py's supported CSL features and may differ from other processors.
