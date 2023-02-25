from dataclasses import dataclass
import json
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, Optional

_SEPARATORS = re.compile(r'[ _\-]+')

@dataclass(frozen=True)
class Emoji:
    key: str
    value: str

    @classmethod
    def of(cls, key: str, value: str) -> 'Emoji':
        """
        Create a new emoji with the key and value. If the key contains spaces,
        underscores, or dashes as word separators, it is normalized to use
        exactly one dash for each word separator.
        """
        return Emoji(_SEPARATORS.sub('-', key), value)

    @property
    def dashed(self) -> bool:
        """Determine whether the emoji key contains a dash."""
        return '-' in self.key

    def codepoints(self) -> list[int]:
        """Get the codepoints for this emoji."""
        return [ord(c) for c in self.value]

    def filename(self, extension: str) -> str:
        """Determine a file name for this emoji with the extension."""
        return f'{self.key}.{extension}'

    @property
    def json(self) -> str:
        """A JSON file for this emoji."""
        return self.filename('json')

    @property
    def pdf(self) -> str:
        """A PDF file for this emoji."""
        return self.filename('pdf')

    @property
    def svg(self) -> str:
        """The name of the SVG source file, which uses codepoints."""
        coded = ''.join([f'{c:04x}' for c in self.codepoints()])
        return f'emoji_u{coded}.svg'

    def remove_page_group(self, directory: Path) -> None:
        """
        If the JSON representation for this emoji's PDF graphic contains a page
        group, remove the page group, update the JSON, and return True.
        Otherwise, do not change anything and return False.
        """
        with open(directory / self.json, mode='r', encoding='utf8') as file:
            document = json.load(file)

        document = self.remove_page_group_object(document)
        if not document:
            return False

        with open(directory / self.json, mode='w', encoding='utf8') as file:
            json.dump(document, file)
        return True

    def remove_page_group_object(self, document: dict) -> dict | None:
        objects = document['qpdf'][1]

        def resolve(ref: str) -> Any:
            key = ref if ref == 'trailer' else f'obj:{ref}'
            if key not in objects:
                raise KeyError(ref)
            return objects[key]

        def resolve_value(ref, type=None) -> Any:
            o = resolve(ref)
            if 'value' not in o:
                raise ValueError(f'{ref} does not point to object')
            v = o['value']
            if type is not None and v['/Type'] != type:
                raise ValueError(
                    f'{ref} points to object of type {v["/Type"]} not {type}'
                )
            return v

        trailer = resolve_value('trailer')
        root = resolve_value(trailer['/Root'], '/Catalog')
        pages = resolve_value(root['/Pages'], '/Pages')['/Kids']
        if len(pages) > 1:
            raise ValueError(f'PDF has {len(pages)} pages instead of just one')
        page = resolve_value(pages[0], '/Page')

        if not '/Group' in page:
            return None

        del page['/Group']
        return document

    def generate_pdf(self, input: Path, output: Path) -> None:
        """
        Convert the SVG for this emoji at the given input path into a PDF at the
        given output path. This method not only converts SVG to PDF but also
        fixes the resulting PDF, removing any page group.
        """
        subprocess.run(
            ['rsvg-convert', input / self.svg, '-f', 'pdf', output / self.pdf],
            check=True
        )
        subprocess.run(
            ['qpdf', output / self.pdf, '--json-output', output / self.json],
            check=True
        )
        if self.remove_page_group(output):
            subprocess.run(
                ['qpdf', output / self.json, '--json-input', output / self.pdf],
                check=True
            )

    def to_latex_chars(self) -> str:
        return ''.join([f'\char"{c:04X}' for c in self.codepoints()])

    def to_latex_table_entry(self) -> str:
        coded = self.to_latex_chars()
        if self.dashed:
            return f'\expandafter\def\csname emo@emoji@{self.key}\endcsname{{{coded}}}'
        else:
            return f'\def\emo@emoji@{self.key}{{{coded}}}'


desert_island = Emoji.of('desert island', '🏝️')
parrot = Emoji.of('parrot', '🦜')
print(desert_island.codepoints())
print(desert_island.to_latex_chars())

print(desert_island.to_registry_entry())
print(parrot.to_registry_entry())
