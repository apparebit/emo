#!/usr/bin/env python3

# Not quite ready for primetime. But the idea is to generate the emo@emoji@
# table automatically at scale.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, Iterator, Iterable, TypeAlias


# --------------------------------------------------------------------------------------
# Emoji Names

PUNCTUATION = re.compile(r"""[:'"!()]""")
SEPARATORS = re.compile(r'[ _\-]+')

RENAMING = {
    'european-union': 'eu',
}

def to_name(value: str) -> str:
    """Turn the given string as an emoji name."""
    return SEPARATORS.sub('-', PUNCTUATION.sub('', value.lower()))


# --------------------------------------------------------------------------------------
# Emoji Codepoints

RECODING = {
    (0x1F3F3, 0xFE0F, 0x200D, 0x1F308): (0x1F3F3, 0x200D, 0x1F308)
}

def to_codepoint(cp: int | str) -> int:
    if isinstance(cp, int):
        return cp
    if cp.startswith(('0x', 'U+')):
        cp = cp[2:]
    return int(cp, base=16)

def to_codepoints(value: str | Iterator[int|str]) -> Sequence[int]:
    if isinstance(value, str):
        return tuple(ord(c) for c in value)
    return tuple(to_codepoint(cp) for cp in value)

REGIONAL_INDICATOR_A = 0x1f1e6
REGIONAL_INDICATOR_Z = 0x1f1ff
LETTER_CAPITAL_A = ord('A')

def is_regional_indicator(cp: int) -> bool:
    return REGIONAL_INDICATOR_A <= cp <= REGIONAL_INDICATOR_Z

def regional_indicator_to_letter(cp: int) -> str:
    return chr(cp - REGIONAL_INDICATOR_A + LETTER_CAPITAL_A)


# --------------------------------------------------------------------------------------
# Emoji Descriptor

@dataclass(slots=True, frozen=True, order=True)
class Emoji:
    """Representation of an emoji."""
    name: str = field(compare=False)
    codepoints: tuple[int,...]
    display: str = field(init=False, compare=False)

    def __post_init__(self) -> None:
        display = ''.join(map(lambda cp: chr(cp), self.codepoints))
        object.__setattr__(self, 'display', display)

    @classmethod
    def of(cls, name: str, value: str | Iterable[int|str]) -> 'Emoji':
        return Emoji(to_name(name), to_codepoints(value))

    @property
    def normal_name(self) -> str:
        return RENAMING.get(self.name, self.name)

    @property
    def normal_codepoints(self) -> tuple[int]:
        return RECODING.get(self.codepoints, self.codepoints)

    def __str__(self) -> str:
        return self.display

    def __repr__(self) -> str:
        return f'Emoji.of("{self.name}", "{self.display}")'

    @property
    def has_compound_name(self) -> bool:
        return '-' in self.name

    @property
    def is_regional_flag(self) -> bool:
        return (
            len(self.codepoints) == 2 and
            all(is_regional_indicator(cp) for cp in self.codepoints)
        )

    @property
    def unicode(self) -> str:
        return ' '.join(f'U+{cp:04X}' for cp in self.codepoints)

    @property
    def latex_chars(self) -> str:
        return  ''.join(f'\char"{cp:04X}' for cp in self.codepoints)

    @property
    def svg_file(self) -> str:
        # Emoji for national flags leverage the country's ISO 3166-1 alpha-2 code.
        if self.is_regional_flag:
            return ''.join(
                regional_indicator_to_letter(cp) for cp in self.codepoints
            ) + '.svg'

        codepoints = '_'.join(f'{cp:04x}' for cp in self.normal_codepoints)
        return f'emoji_u{codepoints}.svg'

    @property
    def svg_path(self) -> str:
        if self.is_regional_flag:
            return f'third_party/regional-flags/svg/{self.svg_file}'
        return f'svg/{self.svg_file}'

    @property
    def latex_table_entry(self) -> str:
        if self.has_compound_name:
            prefix = f'\expandafter\def\csname emo@emoji@{self.normal_name}\endcsname'
        else:
            prefix = f'\def\emo@emoji@{self.normal_name}'

        return f'{prefix}{{{str(self)}}}'


# --------------------------------------------------------------------------------------
# Parser for Unicode's 'emoji-test.txt' File

SubgroupTable: TypeAlias = dict[str, Sequence[Emoji]]
GroupTable: TypeAlias = dict[str, SubgroupTable]
NameTable: TypeAlias = dict[str, Emoji]
CodepointTable: TypeAlias = dict[Sequence[int], Emoji]

class RegistryParser:
    def __init__(self, path: str | Path) -> None:
        self._path: str | Path = path
        self._lineno = 0
        self._by_name: NameTable = {}
        self._by_codepoints: CodepointTable = {}
        self._all_groups: GroupTable = {}
        self._group: SubgroupTable | None = None
        self._subgroup_name: str | None = None
        self._subgroup: list[Emoji] | None = None

    def error(self, msg: str) -> None:
        raise ValueError(f'{self._path}:{self._lineno}: {msg}')

    GROUP_PREFIX = '# group: '
    SUBGROUP_PREFIX = '# subgroup: '
    EMOJI_DECLARATION = re.compile(r"""
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

    def parse_line(self, line: str) -> Emoji | tuple[str, str] | None:
        line = line.strip()
        if line.startswith(self.GROUP_PREFIX):
            return 'group', line[len(self.GROUP_PREFIX):]
        if line.startswith(self.SUBGROUP_PREFIX):
            return 'subgroup', line[len(self.SUBGROUP_PREFIX):]
        if line == '' or line[0] == '#':
            return None

        match = self.EMOJI_DECLARATION.match(line)
        if match is None:
            self.error('neither empty, comment, or emoji')
        if match.group('status') != 'fully-qualified':
            return None
        return Emoji.of(match.group('name'), match.group('codepoints').split())

    def enter_group(self, name: str) -> None:
        assert self._subgroup_name is None
        self._group = self._all_groups.setdefault(name, {})

    def enter_subgroup(self, name: str) -> None:
        assert self._subgroup_name is None
        if self._group is None:
            self.error('subgroup without prior group declaration')
        self._subgroup_name = name
        self._subgroup = list(self._group[name]) if name in self._group else []

    def maybe_exit_subgroup(self) -> None:
        if self._subgroup_name is not None:
            self._group[self._subgroup_name] = tuple(self._subgroup)
            self._subgroup_name = None
            self._subgroup = None

    def add_emoji(self, emoji: Emoji) -> None:
        if self._subgroup_name is None:
            self.error('emoji without prior group and subgroup declaration')
        if emoji.name in self._by_name:
            self.error(f'duplicate declaration of emoji named "{emoji.name}"')
        if emoji.codepoints in self._by_codepoints:
            self.error(f'duplicate declaration of emoji {emoji.unicode}')

        self._by_name[emoji.name] = emoji
        self._by_codepoints[emoji.codepoints] = emoji
        self._subgroup.append(emoji)

    def run(self) -> tuple[NameTable, CodepointTable, GroupTable]:
        assert self._lineno == 0

        with open(self._path, mode='r', encoding='utf8') as file:
            while (line := file.readline()) != '':
                self._lineno += 1
                item = self.parse_line(line[:-1])
                if item is None:
                    continue
                if isinstance(item, Emoji):
                    self.add_emoji(item)
                    continue

                self.maybe_exit_subgroup()
                grouping, name = item
                if grouping == 'group':
                    self.enter_group(name)
                else:
                    self.enter_subgroup(name)

            self.maybe_exit_subgroup()

        return self._by_name, self._by_codepoints, self._all_groups


# --------------------------------------------------------------------------------------
# SVG to PDF Conversion

def remove_page_group_object(document: dict) -> dict | None:
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

def remove_page_group(path: Path) -> bool:
    with open(path, mode='r', encoding='utf8') as file:
        document = json.load(file)

    document = remove_page_group_object(document)
    if document is None:
        return False

    tmp = path.with_suffix('.patched.json')
    with open(tmp, mode='w', encoding='utf8') as file:
        json.dump(document, file)
    tmp.replace(path)
    return True

def fix_pdf(qpdf: str, path: Path) -> None:
    json_path = path.with_suffix('.json')
    subprocess.run([qpdf, str(path), '--json-output', str(json_path)], check=True)
    changed = remove_page_group(json_path)
    if not changed:
        return

    tmp = path.with_suffix('.patched.pdf')
    subprocess.run([qpdf, str(json_path), '--json-input', str(tmp)], check=True)
    tmp.replace(path)

def convert_svg_to_pdf(rsvg_convert: str, source: Path, target: Path) -> None:
    subprocess.run([rsvg_convert, str(source), '-f', 'Pdf', '-o', str(target)], check=True)

def which(tool: str) -> str:
    path = shutil.which(tool)
    if path is None:
        raise FileNotFoundError(tool)
    return path

@dataclass(frozen=True)
class Converter:
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
            qpdf = which('qpdf'),
            rsvg_convert = which('rsvg-convert'),
            source_dir = Path(source_dir),
            target_dir = Path.cwd() if target_dir is None else Path(target_dir),
        )

    def __call__(self, emoji: 'Emoji') -> Path:
        source = self.source_dir / emoji.svg_path
        target = self.target_dir / f'{emoji.name}.pdf'
        if not target.exists():
            convert_svg_to_pdf(self.rsvg_convert, source, target)
            fix_pdf(self.qpdf, target)
        return target


# --------------------------------------------------------------------------------------

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

class Registry:
    def __init__(self, path: str | Path) -> None:
        pass

    def groups(self) -> set[str]:
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


# --------------------------------------------------------------------------------------

by_name, by_codepoints, by_groups = RegistryParser('./scripts/emoji-test.txt').run()
print(len(by_name), 'emoji')

# emoji, groups = parse('./scripts/emoji-test.txt')
# for group, subgroups in groups.items():
#     print(f'{group}')
#     print(len(group) * '=')

#     for subgroup, emoji in subgroups.items():
#         print(f'{subgroup:20s}: {"".join(map(str, emoji))}')

#     print()


lgbt = Emoji.of('rainbow flag', '🏳️‍🌈')
#converter = Converter.create('/Users/rgrimm/Downloads/noto-emoji-2.038')
#print(converter)
#print(converter(lgbt))


# island = Emoji('desert island', '🏝️')
# parrot = Emoji('parrot', '🦜')
# print(f'{str(island)}\x1b[5G{island.name}\x1b[30G({island.unicode})')
# print(f'{str(parrot)}\x1b[5G{parrot.name}\x1b[30G({parrot.unicode})')
print('Et voilà!')
