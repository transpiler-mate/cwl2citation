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

"""CFF, BibTeX, RIS, CSL-JSON, and CSL-rendered text exporters."""

from __future__ import annotations

import json
from importlib.resources import files
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import rispy
from bibtexparser.entrypoint import write_string
from bibtexparser.library import Library
from bibtexparser.model import Entry, Field
from citeproc import (
    Citation,
    CitationItem,
    CitationStylesBibliography,
    CitationStylesStyle,
    formatter,
)
from citeproc.frontend import CitationStylesLocale
from citeproc.source.json import CiteProcJSON
from citeproc_styles import get_style_filepath
from jsonschema import Draft7Validator, FormatChecker
from loguru import logger
from pylatexenc.latexencode import unicode_to_latex
from ruamel.yaml import YAML
from transpiler_mate.api import PluginFailureError

if TYPE_CHECKING:
    from .model import CitationRecord


def schema(name: str) -> dict[str, Any]:
    return cast(
        "dict[str, Any]",
        json.loads(
            files("cwl2citation")
            .joinpath("schemas")
            .joinpath(name)
            .read_text(encoding="utf-8")
        ),
    )


def validate(data: Any, name: str) -> None:
    Draft7Validator(schema(name), format_checker=FormatChecker()).validate(data)


def cff(record: CitationRecord) -> str:
    data: dict[str, Any] = {
        "cff-version": "1.2.0",
        "type": "software",
        "message": "If you use this software, please cite it using these metadata.",
        "title": record.title,
        "abstract": record.abstract,
        "version": record.version,
        "authors": [],
    }
    for author in record.authors:
        person = {"given-names": author.given, "family-names": author.family}
        if author.orcid:
            person["orcid"] = author.orcid
        if author.affiliation:
            person["affiliation"] = author.affiliation
        data["authors"].append(person)
    optional = {
        "doi": record.doi,
        "url": record.url,
        "repository-code": record.repository,
        "date-released": record.released.isoformat() if record.released else None,
        "keywords": record.keywords or None,
    }
    data.update({key: value for key, value in optional.items() if value is not None})
    supported = set(schema("cff-1.2.0.json")["definitions"]["license-enum"]["enum"])
    licenses = [
        value.removeprefix("https://spdx.org/licenses/").removesuffix(".html")
        for value in record.licenses
    ]
    if licenses and all(value in supported for value in licenses):
        data["license"] = licenses[0] if len(licenses) == 1 else licenses
    elif licenses:
        logger.warning(
            "CFF omits license values that are not recognized SPDX identifiers: {}",
            record.licenses,
        )
    validate(data, "cff-1.2.0.json")
    stream = StringIO()
    YAML().dump(data, stream)
    return stream.getvalue()


def csl(record: CitationRecord) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": record.key,
        "type": "software",
        "title": record.title,
        "abstract": record.abstract,
        "version": record.version,
        "author": [
            {"given": author.given, "family": author.family}
            for author in record.authors
        ],
        "publisher": record.publisher,
    }
    for key, value in {
        "DOI": record.doi,
        "URL": record.url,
        "keyword": "; ".join(record.keywords) or None,
    }.items():
        if value:
            data[key] = value
    if record.released:
        data["issued"] = {
            "date-parts": [
                [record.released.year, record.released.month, record.released.day]
            ]
        }
    validate([data], "csl-data.json")
    return data


def bibtex(record: CitationRecord) -> str:
    def latex(value: str) -> str:
        return str(unicode_to_latex(value))

    fields = {
        "title": "{" + latex(record.title) + "}",
        "author": " and ".join(
            "{" + latex(author.family) + "}, {" + latex(author.given) + "}"
            for author in record.authors
        ),
        "publisher": latex(record.publisher),
        "note": latex(f"Computer software, version {record.version}"),
    }
    if record.released:
        fields["year"] = str(record.released.year)
    for key, value in {"doi": record.doi, "url": record.url}.items():
        if value:
            fields[key] = latex(value)
    return str(
        write_string(
            Library(
                [
                    Entry(
                        "misc",
                        record.key,
                        [Field(key, value) for key, value in fields.items()],
                    )
                ]
            )
        )
    )


class CitationRisWriter(rispy.RisWriter):  # type: ignore[misc]
    def set_header(self, count: int) -> str:
        return ""


def ris(record: CitationRecord) -> str:
    entry: dict[str, Any] = {
        "type_of_reference": "COMP",
        "title": record.title,
        "authors": [f"{author.family}, {author.given}" for author in record.authors],
        "abstract": record.abstract,
        "publisher": record.publisher,
        "edition": record.version,
    }
    if record.keywords:
        entry["keywords"] = record.keywords
    if record.doi:
        entry["doi"] = record.doi
    if record.url:
        entry["urls"] = [record.url]
    if record.released:
        entry.update(
            year=str(record.released.year), date=record.released.strftime("%Y/%m/%d")
        )
    return str(rispy.dumps([entry], implementation=CitationRisWriter))


def text(record: CitationRecord, style: str, locale: str) -> str:
    candidate = Path(style)
    if candidate.is_file():
        style_path = str(candidate)
    else:
        if "/" in style or "\\" in style or style.endswith(".csl"):
            raise PluginFailureError(f"CSL style file does not exist: {style}")
        style_path = str(get_style_filepath(style))
    CitationStylesLocale(locale)
    processor = CitationStylesStyle(style_path, locale=locale, validate=True)
    processor.schema.assertValid(processor.xml)
    if not processor.has_bibliography():
        raise PluginFailureError(
            f"CSL style {style} has no bibliography; use an independent bibliography style"
        )
    bibliography = CitationStylesBibliography(
        processor, CiteProcJSON([csl(record)]), formatter.plain
    )
    bibliography.register(Citation([CitationItem(record.key)]))
    result = "\n".join(str(item) for item in bibliography.bibliography())
    if not result.strip():
        raise PluginFailureError(f"CSL style {style} produced no bibliography entry")
    return result + "\n"
