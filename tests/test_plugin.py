# Copyright 2026 Transpiler-Mate
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import json
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any

import pytest
import rispy
from bibtexparser.entrypoint import parse_string
from click.testing import CliRunner
from pylatexenc.latex2text import LatexNodes2Text
from ruamel.yaml import YAML
from transpiler_mate.api import AuthorRole, PluginError, PluginFailureError
from transpiler_mate.runtime.cli import main
from transpiler_mate.runtime.context_resolver import DefaultTranspilerContextResolver

from cwl2citation import exporters
from cwl2citation.model import from_metadata, normalize_doi
from cwl2citation.plugin import (
    ALL_FORMATS,
    FILENAMES,
    CWL2CitationOptions,
    cwl2citation,
)

SOURCE = Path(__file__).parent / "fixtures/hello.cwl"


@pytest.fixture
def context() -> Any:
    return DefaultTranspilerContextResolver().resolve(f"{SOURCE}#hello")


def test_all_formats_cli(tmp_path: Path) -> None:
    output = tmp_path / "citations"
    result = CliRunner().invoke(
        main,
        [
            "cwl2citation",
            "--output",
            str(output),
            "--doi",
            "https://doi.org/10.1234/example",
            "--released",
            "2026-09-18",
            "--code-repository",
            "https://github.com/example/hello",
            f"{SOURCE}#hello",
        ],
    )
    assert result.exit_code == 0, result.output
    assert {path.name for path in output.iterdir()} == set(FILENAMES.values())
    cff = YAML(typ="safe").load((output / "CITATION.cff").read_text())
    exporters.validate(cff, "cff-1.2.0.json")
    assert cff["title"] == "Hello"
    assert cff["doi"] == "10.1234/example"
    assert cff["date-released"] == "2026-09-18"
    assert cff["license"] == "Apache-2.0"
    assert cff["repository-code"] == "https://github.com/example/hello"
    csl = json.loads((output / "citation.csl.json").read_text())
    exporters.validate(csl, "csl-data.json")
    assert csl[0]["type"] == "software"
    assert csl[0]["issued"] == {"date-parts": [[2026, 9, 18]]}
    bib = parse_string((output / "citation.bib").read_text())
    assert not bib.failed_blocks
    assert bib.entries[0]["year"] == "2026"
    ris = rispy.loads((output / "citation.ris").read_text())[0]
    assert ris["type_of_reference"] == "COMP"
    assert ris["doi"] == cff["doi"]
    assert ris["authors"] == ["Author, Example"]
    text = (output / "citation.txt").read_text()
    assert (
        "2026" in text
        and "Hello" in text
        and "0.1.0" in text
        and "10.1234/example" in text
    )


def test_select_formats_with_hyphen(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        main,
        [
            "cwl2citation",
            "--format",
            "csl-json",
            "--format",
            "ris",
            "--output",
            str(tmp_path),
            str(SOURCE),
        ],
    )
    assert result.exit_code == 0, result.output
    assert {path.name for path in tmp_path.iterdir()} == {
        "citation.csl.json",
        "citation.ris",
    }


def test_missing_date_and_doi_not_invented(context: Any, tmp_path: Path) -> None:
    cwl2citation.execute(context, CWL2CitationOptions(output=tmp_path))
    cff = YAML(typ="safe").load((tmp_path / "CITATION.cff").read_text())
    assert "date-released" not in cff and "doi" not in cff
    assert "issued" not in json.loads((tmp_path / "citation.csl.json").read_text())[0]
    assert "n.d." in (tmp_path / "citation.txt").read_text()
    assert (
        "year" not in parse_string((tmp_path / "citation.bib").read_text()).entries[0]
    )


@pytest.mark.parametrize("style", ["apa", "ieee", "harvard-cite-them-right"])
def test_real_styles(context: Any, style: str) -> None:
    record = from_metadata(
        context.metadata, doi=None, released="2026-09-18", url=None, repository=None
    )
    rendered = exporters.text(record, style, "en-US")
    assert "Hello" in rendered and "2026" in rendered
    if style == "ieee":
        assert rendered != exporters.text(record, "apa", "en-US")


def test_roles_unicode_and_special_characters(context: Any, tmp_path: Path) -> None:
    person = context.metadata.author.model_copy(
        update={
            "given_name": "Renée",
            "family_name": "Müller",
            "identifier": "https://orcid.org/0000-0002-1825-0097",
        }
    )
    metadata = context.metadata.model_copy(
        update={
            "name": "CWL & 50% {fire}_#1",
            "author": [
                AuthorRole(role_name="Researcher", author=person),
                context.metadata.author,
            ],
            "description": "line one\nER  - injected",
        }
    )
    cwl2citation.execute(
        context.model_copy(update={"metadata": metadata}),
        CWL2CitationOptions(output=tmp_path),
    )
    cff = YAML(typ="safe").load((tmp_path / "CITATION.cff").read_text())
    assert cff["authors"][0]["orcid"] == "https://orcid.org/0000-0002-1825-0097"
    assert cff["authors"][1]["family-names"] == "Author"
    bib = parse_string((tmp_path / "citation.bib").read_text())
    assert not bib.failed_blocks and len(bib.entries) == 1
    decoded = LatexNodes2Text().latex_to_text(bib.entries[0]["title"])
    assert "50%" in decoded and "{fire}" in decoded
    ris = rispy.loads((tmp_path / "citation.ris").read_text())
    assert len(ris) == 1 and ris[0]["authors"][0] == "Müller, Renée"


@pytest.mark.parametrize(
    "options",
    [
        {"style": "nonexistent-style"},
        {"locale": "xx-NOTREAL"},
        {"released": "2026-02-30"},
        {"released": "20260918"},
        {"doi": "garbage"},
        {"url": "file:///tmp/example"},
        {"format": []},
    ],
)
def test_invalid_options_write_nothing(
    context: Any, tmp_path: Path, options: dict[str, Any]
) -> None:
    with pytest.raises(PluginError):
        cwl2citation.execute(context, CWL2CitationOptions(output=tmp_path, **options))
    assert list(tmp_path.iterdir()) == []


def test_existing_file_preserved(context: Any, tmp_path: Path) -> None:
    (tmp_path / "citation.ris").write_text("existing")
    with pytest.raises(PluginFailureError, match="already exists"):
        cwl2citation.execute(context, CWL2CitationOptions(output=tmp_path))
    assert list(tmp_path.iterdir()) == [tmp_path / "citation.ris"]
    assert (tmp_path / "citation.ris").read_text() == "existing"


def test_unused_style_not_loaded(context: Any, tmp_path: Path) -> None:
    cwl2citation.execute(
        context,
        CWL2CitationOptions(output=tmp_path, format=["cff", "cff"], style="missing"),
    )
    assert list(tmp_path.iterdir()) == [tmp_path / "CITATION.cff"]


@pytest.mark.parametrize(
    "identifier",
    ["10.1234/example", "doi:10.1234/example", "https://doi.org/10.1234/example"],
)
def test_doi_forms(identifier: str) -> None:
    assert normalize_doi(identifier) == "10.1234/example"
    assert normalize_doi("https://example.org/software") is None


def test_invalid_orcid(context: Any) -> None:
    person = context.metadata.author.model_copy(
        update={"identifier": "https://orcid.org/0000-0002-1825-0098"}
    )
    with pytest.raises(PluginFailureError, match="ORCID checksum"):
        from_metadata(
            context.metadata.model_copy(update={"author": person}),
            doi=None,
            released=None,
            url=None,
            repository=None,
        )


def test_override_metadata_doi(context: Any) -> None:
    metadata = context.metadata.model_copy(update={"identifier": "10.1234/original"})
    record = from_metadata(
        metadata, doi="10.1234/version", released=None, url=None, repository=None
    )
    assert record.doi == "10.1234/version"
    assert record.url == "https://doi.org/10.1234/version"


def test_default_and_registration() -> None:
    assert CWL2CitationOptions().format == ALL_FORMATS
    assert (
        next(
            iter(entry_points(group="transpiler_mate.plugins", name="cwl2citation"))
        ).load()
        is cwl2citation
    )
