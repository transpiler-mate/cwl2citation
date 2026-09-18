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

"""Generate selected citation formats through Transpiler-Mate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field
from transpiler_mate.api import (
    PluginError,
    PluginExecutionError,
    PluginFailureError,
    transpiler_plugin,
)

from . import exporters
from .model import from_metadata

if TYPE_CHECKING:
    from transpiler_mate.api import TranspilerContext


CitationFormat = Literal["cff", "bibtex", "ris", "csl-json", "text"]
ALL_FORMATS: list[CitationFormat] = ["cff", "bibtex", "ris", "csl-json", "text"]


class CWL2CitationOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    output: Path = Field(default=Path("citations"), description="Output directory")
    format: list[CitationFormat] = Field(
        default_factory=lambda: ALL_FORMATS.copy(),
        description="Output format (repeatable; default: all five)",
    )
    style: str = Field(
        default="apa",
        description="Packaged CSL style name or local .csl file; text only",
    )
    locale: str = Field(default="en-US", description="CSL locale; text only")
    doi: str | None = Field(
        default=None, description="Explicit software DOI, overriding metadata"
    )
    released: str | None = Field(
        default=None,
        description="Release/publication date YYYY-MM-DD; never inferred from dateCreated",
    )
    code_repository: str | None = Field(
        default=None, description="Source repository HTTP(S) URL"
    )
    url: str | None = Field(
        default=None, description="Software landing-page HTTP(S) URL"
    )


FILENAMES = {
    "cff": "CITATION.cff",
    "bibtex": "citation.bib",
    "ris": "citation.ris",
    "csl-json": "citation.csl.json",
    "text": "citation.txt",
}


@transpiler_plugin(
    name="cwl2citation",
    description="Export CFF, BibTeX, RIS, CSL-JSON, and styled software citations.",
    options_model=CWL2CitationOptions,
)
def cwl2citation(context: TranspilerContext, options: CWL2CitationOptions) -> None:
    try:
        if context.process_id:
            _ = (
                context.resolved_process
            )  # Validate the requested fragment; metadata is document-level.
        if not options.format:
            raise PluginFailureError("Select at least one citation format")
        formats = list(dict.fromkeys(options.format))
        for kind in formats:
            target = options.output / FILENAMES[kind]
            if target.exists() or target.is_symlink():
                raise PluginFailureError(f"Output already exists: {target}")
        record = from_metadata(
            context.metadata,
            doi=options.doi,
            released=options.released,
            url=options.url,
            repository=options.code_repository,
        )
        renderers = {
            "cff": lambda: exporters.cff(record),
            "bibtex": lambda: exporters.bibtex(record),
            "ris": lambda: exporters.ris(record),
            "csl-json": lambda: (
                json.dumps([exporters.csl(record)], ensure_ascii=False, indent=2) + "\n"
            ),
            "text": lambda: exporters.text(record, options.style, options.locale),
        }
        rendered = {FILENAMES[kind]: renderers[kind]() for kind in formats}
        options.output.mkdir(parents=True, exist_ok=True)
        written: list[Path] = []
        try:
            for name, content in rendered.items():
                target = options.output / name
                with target.open("x", encoding="utf-8") as stream:
                    written.append(target)
                    stream.write(content)
        except Exception:
            for target in written:
                target.unlink()
            raise
    except PluginError:
        raise
    except Exception as exc:
        raise PluginExecutionError(f"Unable to generate citations: {exc}") from exc
