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

"""Normalize software metadata once for all citation exporters."""

from __future__ import annotations

import re
from datetime import date
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from loguru import logger
from pydantic import BaseModel, Field
from transpiler_mate.api import AuthorRole, DefinedTerm, PluginFailureError

if TYPE_CHECKING:
    from transpiler_mate.api import SoftwareApplication


class Author(BaseModel):
    given: str = Field(min_length=1)
    family: str = Field(min_length=1)
    orcid: str | None = None
    affiliation: str | None = None


class CitationRecord(BaseModel):
    key: str
    title: str = Field(min_length=1)
    abstract: str
    version: str = Field(min_length=1)
    authors: list[Author] = Field(min_length=1)
    publisher: str
    released: date | None = None
    doi: str | None = None
    url: str | None = None
    repository: str | None = None
    licenses: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


def clean(value: str) -> str:
    """Collapse line breaks to prevent line-oriented export injection."""
    return " ".join(value.split())


def normalize_doi(value: str | None, *, explicit: bool = False) -> str | None:
    if value is None:
        return None
    candidate = re.sub(
        r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", value.strip(), flags=re.I
    )
    if re.fullmatch(r"10\.\d{4,9}/[^\s]+", candidate):
        return candidate
    if explicit or value.lower().startswith(
        ("doi:", "https://doi.org/", "http://doi.org/", "10.")
    ):
        raise PluginFailureError(f"Invalid DOI: {value}")
    return None


def http_url(value: str | None) -> str | None:
    if value is None:
        return None
    parts = urlsplit(value)
    if (
        parts.scheme not in {"http", "https"}
        or not parts.netloc
        or any(c.isspace() for c in value)
    ):
        raise PluginFailureError(f"Expected an HTTP(S) URL: {value}")
    return value


def author_orcid(value: object) -> str | None:
    text = str(value or "")
    identifier = re.sub(r"^https?://orcid\.org/", "", text, flags=re.I)
    if not re.fullmatch(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]", identifier):
        if "orcid.org" in text:
            raise PluginFailureError(f"Invalid ORCID: {text}")
        return None
    digits = identifier.replace("-", "")
    total = 0
    for digit in digits[:-1]:
        total = (total + int(digit)) * 2
    check = (12 - total % 11) % 11
    if digits[-1] != ("X" if check == 10 else str(check)):
        raise PluginFailureError(f"Invalid ORCID checksum: {text}")
    return f"https://orcid.org/{identifier}"


def from_metadata(
    metadata: SoftwareApplication,
    *,
    doi: str | None,
    released: str | None,
    url: str | None,
    repository: str | None,
) -> CitationRecord:
    people = metadata.author if isinstance(metadata.author, list) else [metadata.author]
    authors = []
    for entry in people:
        person = entry.author if isinstance(entry, AuthorRole) else entry
        affiliations = (
            person.affiliation
            if isinstance(person.affiliation, list)
            else [person.affiliation]
        )
        authors.append(
            Author(
                given=clean(person.given_name),
                family=clean(person.family_name),
                orcid=author_orcid(person.identifier),
                affiliation="; ".join(clean(org.name) for org in affiliations),
            )
        )
    identifier = str(metadata.identifier) if metadata.identifier is not None else None
    resolved_doi = (
        normalize_doi(doi, explicit=True)
        if doi is not None
        else normalize_doi(identifier)
    )
    release = date.fromisoformat(released) if released else None
    if released and (not re.fullmatch(r"\d{4}-\d{2}-\d{2}", released)):
        raise PluginFailureError("--released must use YYYY-MM-DD")
    repository = http_url(repository)
    landing = (
        http_url(url)
        if url
        else (f"https://doi.org/{resolved_doi}" if resolved_doi else repository)
    )
    raw_keywords = (
        metadata.keywords
        if isinstance(metadata.keywords, list)
        else [metadata.keywords]
    )
    keywords = [
        clean(str(item.name or item.term_code or ""))
        if isinstance(item, DefinedTerm)
        else clean(str(item))
        for item in raw_keywords
        if item is not None
    ]
    licenses = (
        metadata.license if isinstance(metadata.license, list) else [metadata.license]
    )
    license_values = [
        str(getattr(item, "identifier", None) or getattr(item, "url", None) or item)
        for item in licenses
    ]
    if metadata.contributor:
        logger.info(
            "Citation authors come from author metadata; contributors are not promoted to authors."
        )
    key = (
        re.sub(
            r"[^a-zA-Z0-9_-]+", "-", f"{metadata.name}-{metadata.software_version}"
        ).strip("-")
        or "workflow"
    )
    return CitationRecord(
        key=key,
        title=clean(metadata.name),
        abstract=clean(metadata.description),
        version=clean(metadata.software_version),
        authors=authors,
        publisher=clean(metadata.publisher.name),
        released=release,
        doi=resolved_doi,
        url=landing,
        repository=repository,
        licenses=license_values,
        keywords=[item for item in keywords if item],
    )
