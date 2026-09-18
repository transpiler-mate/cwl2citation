# Reference

The plugin consumes Transpiler-Mate's validated `SoftwareApplication` metadata, including its required title, description, software version, authors, and publisher. It does not execute the workflow.

| Source | Citation mapping |
| --- | --- |
| `name`, `description` | Title and abstract (where supported) |
| `softwareVersion` | CFF/CSL version, RIS edition, BibTeX software-version note |
| `author` (Person or AuthorRole) | Ordered citation authors; AuthorRole unwraps its Person |
| Author `identifier` | Checksum-validated ORCID in CFF |
| Author `affiliation` | CFF affiliation |
| `publisher.name` | CSL publisher, RIS publisher, BibTeX publisher |
| Software `identifier` | DOI when recognizable; overridden by `--doi` |
| `keywords` | CFF keywords, CSL keyword string, RIS keywords |
| `license` | CFF SPDX identifier(s), if recognized by the CFF schema |
| `--released` | CFF date-released, CSL issued, BibTeX year, RIS date/year |
| `--code-repository` | CFF repository-code; fallback landing URL |
| `--url` | Citation landing URL; otherwise DOI URL, then repository |

Contributors are not automatically promoted to citation authors. Non-DOI identifiers are not converted into DOIs. `dateCreated` is never inferred to be a release date. Unsupported license values are omitted with a warning. ORCID and affiliations are retained in CFF; they are not carried into the other exports. Styled text includes whichever fields the selected style renders.

CFF uses version 1.2.0; CSL-JSON is validated against the CSL 1.0.2 data schema. BibTeX uses portable `@misc`, escaped LaTeX strings, and a software-version note. RIS uses `TY  - COMP`. All files are UTF-8. CSL-JSON is an array of one record.

See the [CLI options](../how-to/use-cli.md) and [Python API](api.md).
