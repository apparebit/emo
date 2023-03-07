#!/usr/bin/env python3

# Not quite ready for primetime. But the idea is to generate the emo@emoji@
# table automatically at scale.

from collections.abc import Mapping
from dataclasses import dataclass
from functools import total_ordering
import json
from pathlib import Path
import re
import shutil
import subprocess
from types import MappingProxyType
from typing import Any, Iterator


# ======================================================================================
# Emoji Name, Codepoints, and Display


_PUNCTUATION = re.compile(r"""[:'"!()]""")
_SEPARATORS = re.compile(r'[ _\-]+')

def _to_codepoint(cp: int | str) -> int:
    """Coerce the argument to a Unicode codepoint."""
    if isinstance(cp, int):
        return cp
    if cp.startswith(('0x', 'U+')):
        cp = cp[2:]
    return int(cp, base=16)


_REGIONAL_INDICATOR_A = 0x1f1e6
_REGIONAL_INDICATOR_Z = 0x1f1ff
_LETTER_CAPITAL_A = ord('A')

def _is_regional_indicator(cp: int) -> bool:
    """Determine whether the codepoint is a regional indicator."""
    return _REGIONAL_INDICATOR_A <= cp <= _REGIONAL_INDICATOR_Z

def _regional_indicator_to_letter(cp: int) -> str:
    """Convert a regional indicator to the corresponding uppercase letter."""
    return chr(cp - _REGIONAL_INDICATOR_A + _LETTER_CAPITAL_A)


# --------------------------------------------------------------------------------------

# Codepoints other than the fully qualified ones used by Noto emoji
_REMAP = {
    (0x1F3F3, 0xFE0F, 0x200D, 0x1F308): (0x1F3F3, 0x200D, 0x1F308)
}


@total_ordering
class Emoji:
    """
    An emoji. This class combines name and Unicode codepoint sequence, while
    also supporting easy conversion to various output formats based on either.
    """

    def __init__(self, name: str, value: str | Iterator[int|str]) -> None:
        """
        Create a new emoji with the given name and value. The value may be the
        emoji as a string or an iterator over the Unicode codepoints. Each
        codepoint may either be an integer or its hexadecimal string
        representation. The `0x` and `U+` prefixes are ignored.
        """
        self._name = _SEPARATORS.sub('-', _PUNCTUATION.sub('', name))
        if isinstance(value, str):
            self._codepoints = tuple(ord(c) for c in value)
            self._display = value
        else:
            self._codepoints = tuple(_to_codepoint(c) for c in value)
            self._display = ''.join(map(lambda cp: chr(cp), self._codepoints))

    @property
    def name(self) -> str:
        """The name."""
        return self._name

    @property
    def codepoints(self) -> tuple[int]:
        """The Unicode codepoints."""
        return self._codepoints

    def __str__(self) -> str:
        """The emoji itself."""
        return self._display

    def __hash__(self) -> int:
        return hash(self._codepoints)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Emoji):
            return self._codepoints == other._codepoints
        return NotImplemented

    def __lt__(self, other: object) -> bool:
        if isinstance(other, Emoji):
            return self._codepoints < other._codepoints
        return NotImplemented

    def __repr__(self) -> str:
        return f'Emoji("{self._name}", "{self._display}")'

    @property
    def has_compound_name(self) -> bool:
        """Flag for the name containing more than one word."""
        return '-' in self._name

    @property
    def is_regional_flag(self) -> bool:
        """Flag for the emoji representing a regional flag."""
        return (
            len(self._codepoints) == 2 and
            all(_is_regional_indicator(cp) for cp in self._codepoints)
        )

    @property
    def unicode(self) -> str:
        """The codepoints in Unicode `U+` notation."""
        return ' '.join(f'U+{cp:04X}' for cp in self._codepoints)

    @property
    def latex_chars(self) -> str:
        """The codepoints in LaTeX `\char"` notation."""
        return  ''.join(f'\char"{cp:04X}' for cp in self._codepoints)

    @property
    def svg_file(self) -> str:
        """The SVG file within the Noto color emoji repository."""
        # Emoji for national flags leverage the country's ISO 3166-1 alpha-2 code.
        if self.is_regional_flag:
            return ''.join(
                _regional_indicator_to_letter(cp) for cp in self._codepoints
            ) + '.svg'

        codepoints = _REMAP.get(self._codepoints, self._codepoints)
        codepoints = '_'.join(f'{cp:04x}' for cp in codepoints)
        return f'emoji_u{codepoints}.svg'

    @property
    def svg_path(self) -> str:
        """The path to the SVG file within the Noto color emoji repository."""
        if self.is_regional_flag:
            return f'third_party/regional-flags/svg/{self.svg_file}'
        return f'svg/{self.svg_file}'

    @property
    def latex_table_entry(self) -> str:
        """The table entry."""
        prefix = (
            f'\expandafter\def\csname emo@emoji@{self._name}\endcsname'
            if self.has_compound_name else f'\def\emo@emoji@{self._name}'
        )
        return f'{prefix}{{{str(self)}}}'


# ======================================================================================
# All Emoji

#        Smileys & Emotion, People & Body, Component, Animals & Nature, Food & Drink,
#   Travel & Places, Activities, Objects, Symbols, Flags.


SHORT_GROUPS = {
    'animals': 'animals & nature',
    'body': 'people & body',
    'drink': 'food & drink',
    'food': 'food & drink',
    'nature': 'animals & nature',
    'people': 'people & body',
    'places': 'travel & places',
    'smileys': 'smileys & emotion',
    'travel': 'travel & places',
}


@dataclass(frozen=True)
class _Group:
    name: str

@dataclass(frozen=True)
class _Subgroup:
    name: str

_EMOJI_TEST_GROUP = '# group: '
_EMOJI_TEST_SUBGROUP = '# subgroup: '
_EMOJI_TEST_LINE = re.compile(r"""
    ^
    (?P<codepoints>[0-9A-F][0-9A-F ]+[0-9A-F])
    [ ]+ [;] [ ]
    (?P<status>component|fully-qualified|minimally-qualified|unqualified)
    [ ]+ [#] [ ]
    (?P<display>[^ ]+)
    [ ]
    [E][0-9.]+
    [ ]
    (?P<name>.+)
    $
""", re.X)

def _parse_line(line: str) -> Emoji | _Group | _Subgroup | None:
    line = line.strip()
    if line.startswith(_EMOJI_TEST_GROUP):
        return _Group(line[len(_EMOJI_TEST_GROUP):])
    elif line.startswith(_EMOJI_TEST_SUBGROUP):
        return _Subgroup(line[len(_EMOJI_TEST_SUBGROUP):])
    elif line == "" or line[0] == '#':
        return None

    match = _EMOJI_TEST_LINE.match(line)
    if match.group('status') != 'fully-qualified':
        return None
    return Emoji(match.group('name').lower(), match.group('codepoints').split())

class Registry:
    def __init__(self, path: str | Path) -> None:
        self._by_name: dict[str, Emoji] = {}
        self._groups: dict[str, dict[str, tuple[Emoji]]] = {}

        group: dict[str, list[Emoji]] | None = None
        subgroup_name: str | None = None
        subgroup: list[Emoji] | None = None

        with open(path, mode='r', encoding='utf8') as file:
            while (line := file.readline()) != '':
                item = _parse_line(line[:-1])
                if item is None:
                    continue

                name = item.name.lower()
                if isinstance(item, _Group):
                    if subgroup_name is not None:
                        group[subgroup_name] = tuple(subgroup)
                    group = self._groups.setdefault(name, {})
                    subgroup_name = None
                    subgroup = None
                    continue
                if isinstance(item, _Subgroup):
                    if group is None:
                        raise ValueError(
                            f'Subgroup {item.name} listed '
                            f'without leading `# group:` in "{path}"'
                        )
                    if subgroup_name is not None:
                        group[subgroup_name] = tuple(subgroup)
                    subgroup_name = name
                    subgroup = list(group[name]) if name in group else []
                    continue

                if subgroup is None:
                    raise ValueError(
                        f'Emoji {str(item)} ({item.unicode}) listed '
                        f'without leading `# subgroup:` in "{path}"'
                    )
                if name in self._by_name:
                    other = self._by_name[name]
                    raise ValueError(
                        f'Emoji {str(item)} ({item.unicode}) and {str(other)} '
                        f'({other.unicode}) are both named "{item.name}" '
                        f'in listing "{path}"'
                    )
                self._by_name[name] = item
                subgroup.append(item)

    def groups(self) -> set[str]:
        """
        Smileys & Emotion, People & Body, Component, Animals & Nature, Food & Drink,
        Travel & Places, Activities, Objects, Symbols, Flags.
        """
        return self._groups.keys()

    def subgroups(self, group: str) -> set[str]:
        return self._groups[group.lower()].keys()

    def subgroup(self, group: str, subgroup: str) -> tuple[Emoji]:
        return self._groups[group.lower()][subgroup.lower()]

    def emoji(self) -> frozenset[Emoji]:
        return self._by_name.values()

    def select(self, groupings: list[str | tuple[str] | tuple[str,str]]) -> set[Emoji]:
        selected_emoji: set[Emoji] = set()

        for grouping in groupings:
            if isinstance(grouping, str):
                grouping = (grouping,)
            if len(grouping) == 1:
                group = self._groups[grouping[0].lower()]
                for subgroup in group.values():
                    selected_emoji.add(subgroup)
                continue
            selected_emoji.add(
                self.subgroup(
                    grouping[0].lower(),
                    grouping[1].lower()
                )
            )

        return selected_emoji

# ======================================================================================
# SVG to PDF Conversion

def _remove_page_group_object(document: dict) -> dict | None:
    """Remove the /Page /Group object from the document in qpdf's JSON format."""

    objects = document['qpdf'][1]

    def resolve(ref: str) -> Any:
        key = ref if ref == 'trailer' else f'obj:{ref}'
        if key not in objects:
            raise KeyError(ref)
        return objects[key]

    def resolve_value(ref, type=None) -> Any:
        o = resolve(ref)
        if 'value' not in o:
            raise ValueError(f'{ref} does not reference object')
        v = o['value']
        if type is not None and v.get('/Type') != type:
            raise ValueError(
                f'{ref} references object of type {v["/Type"]} not {type}'
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

def _remove_page_group(path: Path) -> bool:
    """Remove the /Page /Group object from the file in qpdf's JSON format."""
    with open(path, mode='r', encoding='utf8') as file:
        document = json.load(file)

    document = _remove_page_group_object(document)
    if document is None:
        return False

    tmp = path.with_suffix('.patched.json')
    with open(tmp, mode='w', encoding='utf8') as file:
        json.dump(document, file)
    tmp.replace(path)
    return True

def _fix_pdf(qpdf: str, path: Path) -> None:
    """Prepare the PDF file for inclusion with pdflatex."""
    json_path = path.with_suffix('.json')
    subprocess.run([qpdf, str(path), '--json-output', str(json_path)], check=True)
    changed = _remove_page_group(json_path)
    if not changed:
        return

    tmp = path.with_suffix('.patched.pdf')
    subprocess.run([qpdf, str(json_path), '--json-input', str(tmp)], check=True)
    tmp.replace(path)

def _convert_svg_to_pdf(rsvg_convert: str, source: Path, target: Path) -> None:
    """Convert the source SVG to the target PDF."""
    subprocess.run([rsvg_convert, str(source), '-f', 'Pdf', '-o', str(target)], check=True)

def _which(tool: str) -> str:
    """
    Determine the absolute path to given command line tool, raising a file not
    found error if it cannot be found in the current path.
    """
    path = shutil.which(tool)
    if path is None:
        raise FileNotFoundError(tool)
    return path

@dataclass(frozen=True)
class Converter:
    """
    A converter encapsulates the state that remains constant from emoji to
    emoji, namely the path to the qpdf and rsvg_convert command line tools as
    well as the source and target directories. Note that the source directory is
    the *root directory* of the Noto color emoji sources.
    """
    qpdf: str
    rsvg_convert: str
    source_dir: Path
    target_dir: Path

    @classmethod
    def create(
        cls,
        source_dir: Path | str,
        target_dir: Path | str | None = None
    ) -> 'Converter':
        return cls(
            qpdf = _which('qpdf'),
            rsvg_convert = _which('rsvg-convert'),
            source_dir = Path(source_dir),
            target_dir = Path.cwd() if target_dir is None else Path(target_dir),
        )

    def __call__(self, emoji: 'Emoji') -> Path:
        source = self.source_dir / emoji.svg_path
        target = self.target_dir / f'{emoji.name}.pdf'
        if not target.exists():
            _convert_svg_to_pdf(self.rsvg_convert, source, target)
            _fix_pdf(self.qpdf, target)
        return target


emoji, groups = parse('./scripts/emoji-test.txt')
print(len(emoji), 'emoji')

names = set()
for e in emoji:
    if e.name in names:
        print('duplicate name', e.name)
    names.add(e.name)

# emoji, groups = parse('./scripts/emoji-test.txt')
# for group, subgroups in groups.items():
#     print(f'{group}')
#     print(len(group) * '=')

#     for subgroup, emoji in subgroups.items():
#         print(f'{subgroup:20s}: {"".join(map(str, emoji))}')

#     print()





lgbt = Emoji('lgbt flag', '🏳️‍🌈')
converter = Converter.create('/Users/rgrimm/Downloads/noto-emoji-2.038')
print(converter)
#print(converter(lgbt))


# island = Emoji('desert island', '🏝️')
# parrot = Emoji('parrot', '🦜')
# print(f'{str(island)}\x1b[5G{island.name}\x1b[30G({island.unicode})')
# print(f'{str(parrot)}\x1b[5G{parrot.name}\x1b[30G({parrot.unicode})')
print('Et voilà!')
