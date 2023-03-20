#!/usr/bin/env python3

# Check Python version.
import sys
if sys.version_info < (3,7):
    print('While emo.py avoids recent Python features to maximize compatibility,')
    print('it does require 3.7 or later. Please upgrade your Python.')
    sys.exit(1)

# -------------------------------------------------------------------------
# (C) Copyright 2023 by Robert Grimm, released under the Apache 2.0 license
# -------------------------------------------------------------------------

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
import re
import shutil
import subprocess
from typing import (
    Any, Dict, Iterable, KeysView, List, Mapping,
    NoReturn, Optional, TextIO, Tuple, Union
)
from urllib.request import urlopen

# --------------------------------------------------------------------------------------

class Log:
    def __init__(self, out: TextIO = sys.stderr) -> None:
        self._out = out
        self._first_header = True

    def sgr(self, open: str, text: str, close: str) -> str:
        if self._out.isatty():
            return f'\x1b[{open}m{text}\x1b[{close}m'
        return text

    def pln(self, text: str = '') -> None:
        print(text, file=self._out)

    def header(self, text: str) -> None:
        if self._first_header:
            self._first_header = False
        else:
            self.pln()
        self.pln(self.sgr('1', text, '0'))

    def detail(self, text: str) -> None:
        self.pln(f'    {text}')

    def error(self, text: str) -> None:
        self.pln(self.sgr('1;31', f'ERROR: {text}', '0;39'))

    def warning(self, text: str) -> None:
        self.pln(self.sgr('1;38;5;208', f'WARNING: {text}', '0;39'))

    def info(self, text: str) -> None:
        self.pln(self.sgr('1;34', f'INFO: {text}', '0;39'))

log = Log()

# --------------------------------------------------------------------------------------
# Emoji Names

PUNCTUATION = re.compile(r"""["'’“”&!(),:]""")
SEPARATORS = re.compile(r'[ _\-]+')

# The list of name overrides.
RENAMING = {
    'a-button-blood-type': 'a-button',
    'ab-button-blood-type': 'ab-button',
    'b-button-blood-type': 'b-button',
    'o-button-blood-type': 'o-button',
    'bust-in-silhouette': 'bust',
    'busts-in-silhouette': 'busts',
    'flag-european-union': 'eu',
    'globe-showing-americas': 'globe-americas',
    'globe-showing-asia-australia': 'globe-asia-australia',
    'globe-showing-europe-africa': 'globe-africa-europe',
    'hear-no-evil-monkey': 'hear-no-evil',
    'index-pointing-at-the-viewer': 'index-pointing-at-viewer',
    'index-pointing-at-the-viewer-darkest': 'index-pointing-at-viewer-darkest',
    'index-pointing-at-the-viewer-darker': 'index-pointing-at-viewer-darker',
    'index-pointing-at-the-viewer-medium': 'index-pointing-at-viewer-medium',
    'index-pointing-at-the-viewer-lighter': 'index-pointing-at-viewer-lighter',
    'index-pointing-at-the-viewer-lightest': 'index-pointing-at-viewer-lightest',
    'keycap-*': 'keycap-star',
    'keycap-#': 'keycap-hash',
    'keycap-0': 'keycap-zero',
    'keycap-1': 'keycap-one',
    'keycap-2': 'keycap-two',
    'keycap-3': 'keycap-three',
    'keycap-4': 'keycap-four',
    'keycap-5': 'keycap-five',
    'keycap-6': 'keycap-six',
    'keycap-7': 'keycap-seven',
    'keycap-8': 'keycap-eight',
    'keycap-9': 'keycap-nine',
    'keycap-10': 'keycap-ten',
    'magnifying-glass-tilted-left': 'loupe-left',
    'magnifying-glass-tilted-right': 'loupe-right',
    'palm-down-hand': 'palm-down',
    'palm-down-hand-darkest': 'palm-down-darkest',
    'palm-down-hand-darker': 'palm-down-darker',
    'palm-down-hand-medium': 'palm-down-medium',
    'palm-down-hand-lighter': 'palm-down-lighter',
    'palm-down-hand-lightest': 'palm-down-lightest',
    'palm-up-hand': 'palm-up',
    'palm-up-hand-darkest': 'palm-up-darkest',
    'palm-up-hand-darker': 'palm-up-darker',
    'palm-up-hand-medium': 'palm-up-medium',
    'palm-up-hand-lighter': 'palm-up-lighter',
    'palm-up-hand-lightest': 'palm-up-lightest',
    'rolling-on-the-floor-laughing': 'rofl',
    'see-no-evil-monkey': 'see-no-evil',
    'speak-no-evil-monkey': 'speak-no-evil',
}

def to_name(value: str) -> str:
    """Turn the given string as an emoji name."""
    name = value.lower()
    name = PUNCTUATION.sub('', name)
    name = SEPARATORS.sub('-', name)

    # Use simpler skin tone indicators. Do not reorder.
    name = name.replace('medium-dark-skin-tone', 'darker')
    name = name.replace('medium-light-skin-tone', 'lighter')
    name = name.replace('medium-skin-tone', 'medium')
    name = name.replace('dark-skin-tone', 'darkest')
    name = name.replace('light-skin-tone', 'lightest')

    return RENAMING.get(name, name)


# --------------------------------------------------------------------------------------
# Emoji Codepoints

def to_codepoint(cp: Union[int, str]) -> int:
    if isinstance(cp, int):
        return cp
    if cp.startswith(('0x', 'U+')):
        cp = cp[2:]
    return int(cp, base=16)

def to_codepoints(value: Union[str, Iterable[Union[int,str]]]) -> Tuple[int, ...]:
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
# Emoji Groups

AMPERSAND = re.compile('[ ]*&[ ]*')

SHORT_GROUPS = {
    'animals': 'animals-and-nature',
    'body': 'people-and-body',
    'drink': 'food-and-drink',
    'emotion': 'smileys-and-emotion',
    'food': 'food-and-drink',
    'nature': 'animals-and-nature',
    'people': 'people-and-body',
    'places': 'travel-and-places',
    'smileys': 'smileys-and-emotion',
    'travel': 'travel-and-places',
}

def to_group(group: str) -> str:
    group = group.lower()
    group = SHORT_GROUPS.get(group, group)
    return AMPERSAND.sub('-and-', group)

def to_subgroup(subgroup: str) -> str:
    subgroup = subgroup.lower()
    return AMPERSAND.sub('-and-', subgroup)

def to_group_subgroup(group: str, subgroup: str) -> Tuple[str, str]:
    return to_group(group), to_subgroup(subgroup)

def is_subgroup_selector(identifier: str) -> bool:
    return '::' in identifier

def split_subgroup_selector(identifier: str) -> List[str]:
    return identifier.lower().split('::')


# --------------------------------------------------------------------------------------
# Emoji Status

class Status(str, Enum):
    COMPONENT = 'component'
    FULLY_QUALIFIED = 'fully-qualified'
    MINIMALLY_QUALIFIED = 'minimally-qualified'
    UNQUALIFIED = 'unqualified'


# --------------------------------------------------------------------------------------
# Emoji Descriptor

@dataclass(frozen=True, order=True)
class Emoji:
    """Representation of an emoji. The status is optional to allow for quick hacks."""
    name: str = field(compare=False)
    codepoints: Tuple[int,...]
    display: str = field(init=False, compare=False)
    status: Optional[Status] = field(default=None, compare=False)
    version: Optional[float] = field(default=None, compare=False)

    def __post_init__(self) -> None:
        display = ''.join(map(lambda cp: chr(cp), self.codepoints))
        object.__setattr__(self, 'display', display)

    @classmethod
    def of(
        cls,
        name: str,
        value: Union[str, Iterable[Union[int,str]]],
        status: Union[str, Status, None] = None,
        version: Union[str, float, None] = None,
    ) -> 'Emoji':
        if status is not None and not isinstance(status, Status):
            status = Status(status)
        if isinstance(version, str):
            version = float(version)
        return Emoji(to_name(name), to_codepoints(value), status, version)

    def __str__(self) -> str:
        return self.display

    def __repr__(self) -> str:
        if self.status is None:
            return f'Emoji.of("{self.name}", "{self.display}")'
        else:
            return f'Emoji.of("{self.name}", "{self.display}", "{self.status.value}")'

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
    def is_component(self) -> bool:
        return self.status is Status.COMPONENT

    @property
    def is_fully_qualified(self) -> bool:
        return self.status is Status.FULLY_QUALIFIED

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

        # Skip Emoji presentation selector.
        codepoints = '_'.join(f'{cp:04x}' for cp in self.codepoints if cp != 0xFE0F)
        return f'emoji_u{codepoints}.svg'

    @property
    def svg_path(self) -> str:
        if self.is_regional_flag:
            return f'third_party/regional-flags/svg/{self.svg_file}'
        return f'svg/{self.svg_file}'

    @property
    def latex_table_entry(self) -> str:
        if self.has_compound_name:
            prefix = f'\expandafter\def\csname emo@emoji@{self.name}\endcsname'
        else:
            prefix = f'\def\emo@emoji@{self.name}'

        return f'{prefix}{{{str(self)}}}'


# --------------------------------------------------------------------------------------
# Parser for Unicode TR-51's 'emoji-test.txt' File

NameTable = Mapping[str, Emoji]
CodepointTable = Mapping[Tuple[int, ...], Emoji]
SubgroupTable = Mapping[str, Tuple[Emoji, ...]]
GroupTable = Mapping[str, SubgroupTable]

class RegistryParser:
    """
    Parser for the
    `[emoji-test.txt](https://www.unicode.org/Public/emoji/latest/emoji-test.txt)`
    file accompanying [Unicode TR-51](https://www.unicode.org/reports/tr51/). It
    is the most complete listing of Unicode emoji sequences and names and
    conveniently also organizes them into meaningful groups and subgroups. The
    `run()` method returns two tables:

      1. The identifier table maps emoji names, emoji (fully qualified and
         otherwise), and Unicode code sequences (fully qualified and otherwise)
         to Emoji instances (fully qualified only).
      2. The group table maps group names to subgroup names to sequences of
         Emoji instances. For group "component," those emoji have component
         status. For all other groups, they are fully qualified.
    """

    def __init__(self, path: Union[str, Path]) -> None:
        self._path: Union[str, Path] = path
        self._lineno = 0
        self._name_table: Dict[str, Emoji] = {}
        self._codepoint_table: Dict[Tuple[int, ...], Emoji] = {}
        self._group_table: Dict[str, Dict[str, Tuple[Emoji, ...]]] = {}
        self._group_name: Optional[str] = None
        self._group: Optional[Dict[str, Tuple[Emoji, ...]]] = None
        self._subgroup_name: Optional[str] = None
        self._subgroup: Optional[List[Emoji]] = None

    def error(self, msg: str) -> NoReturn:
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
        [E](?P<version>[0-9.]+)
        [ ]
        (?P<name>.+)
        $
    """, re.X)

    def parse_line(self, line: str) -> Union[Emoji, Tuple[str, str], None]:
        line = line.strip()
        # Group and subgroup are specified in comments.
        if line.startswith(self.GROUP_PREFIX):
            return 'group', to_group(line[len(self.GROUP_PREFIX):])
        if line.startswith(self.SUBGROUP_PREFIX):
            return 'subgroup', to_subgroup(line[len(self.SUBGROUP_PREFIX):])
        if line == '' or line[0] == '#':
            return None

        match = self.EMOJI_DECLARATION.match(line)
        if match is None:
            self.error('neither empty, comment, or emoji')
        return Emoji.of(
            match.group('name'),
            match.group('codepoints').split(),
            match.group('status'),
            match.group('version')
        )

    def enter_group(self, name: str) -> None:
        assert self._subgroup_name is None
        self._group_name = name
        self._group = self._group_table.setdefault(name, {})

    def enter_subgroup(self, name: str) -> None:
        assert self._subgroup_name is None
        if self._group is None:
            self.error('subgroup without prior group declaration')
        self._subgroup_name = name
        self._subgroup = list(self._group[name]) if name in self._group else []

    def maybe_exit_subgroup(self) -> None:
        if self._subgroup_name is not None:
            assert self._group is not None
            assert self._subgroup is not None
            self._group[self._subgroup_name] = tuple(self._subgroup)
            self._subgroup_name = None
            self._subgroup = None

    def add_emoji(self, emoji: Emoji) -> None:
        # There must be a group and subgroup.
        if self._subgroup_name is None:
            self.error('emoji without prior group and subgroup declaration')
        # Only register emoji with new codepoints.
        if emoji.codepoints in self._codepoint_table:
            self.error(
                f'duplicate emoji by codepoints {emoji.display} ({emoji.unicode})'
            )
        # Only register component and fully qualified emoji with new names.
        if emoji.is_component and emoji.name in self._name_table:
            self.error(
                'duplicate declaration of component '
                f'emoji by name {emoji.display} ({emoji.unicode})'
            )
        if emoji.is_fully_qualified and emoji.name in self._name_table:
            self.error(
                'duplicate declaration of fully qualified '
                f'emoji by name {emoji.display} ({emoji.unicode})'
            )
        # Only the component group contains only component emoji.
        if self._group_name == 'component' and not emoji.is_component:
            self.error(
                'component group with non-component '
                f'emoji {emoji.display} ({emoji.unicode})'
            )
        if emoji.is_component and self._group_name != 'component':
            self.error(
                f'component emoji {emoji.display} ({emoji.unicode}) '
                'outside component group'
            )

        # Record all emoji by codepoints.
        self._codepoint_table[emoji.codepoints] = emoji

        # Record component and fully qualified emoji also by name and group/subgroup.
        if emoji.is_component or emoji.is_fully_qualified:
            self._name_table[emoji.name] = emoji
            assert self._subgroup is not None
            self._subgroup.append(emoji)

    def run(self) -> Tuple[NameTable, CodepointTable, GroupTable]:
        assert self._lineno == 0

        with open(self._path, mode='r', encoding='utf8') as file:
            while True:
                line = file.readline()
                if line == '':
                    break
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

        # Patch non-component identifiers to point to fully qualified emoji descriptors.
        for identifier, emoji in self._codepoint_table.items():
            if emoji.is_component or emoji.is_fully_qualified:
                continue
            fully_qualified_emoji = self._name_table.get(emoji.name)
            if fully_qualified_emoji is None:
                self.error(
                    f'no fully qualified emoji for {emoji.display} ({emoji.unicode})'
                )
            self._codepoint_table[identifier] = fully_qualified_emoji

        return self._name_table, self._codepoint_table, self._group_table


# --------------------------------------------------------------------------------------
# Emoji Registry

class Registry:
    def __init__(
        self,
        name_table: NameTable,
        codepoint_table: CodepointTable,
        group_table: GroupTable
    ) -> None:
        """Create a new emoji registry. Use `from_file()` instead."""
        self._name_table = name_table
        self._codepoint_table = codepoint_table
        self._group_table = group_table

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> 'Registry':
        """Instantiate a new registry instance from the given file."""
        return Registry(*RegistryParser(path).run())

    def emoji_names(self) -> KeysView[str]:
        """Get the names of all registered emoji."""
        return self._name_table.keys()

    def lookup(self, identifier: Union[str, Tuple[int, ...]]) -> Optional[Emoji]:
        """Look up an emoji by name or codepoints."""
        if isinstance(identifier, str):
            return self._name_table.get(identifier.lower())
        return self._codepoint_table.get(identifier)

    def is_group(self, group: str) -> bool:
        """Determine if the group name is valid."""
        return group in self._group_table

    def is_subgroup(self, group: str, subgroup: str) -> bool:
        """Determine if the subgroup name is valid. The group name must be valid."""
        return subgroup in self._group_table[group]

    def group_names(self) -> KeysView[str]:
        """Get the names of all groups."""
        return self._group_table.keys()

    def subgroup_names(self, group: str) -> KeysView[str]:
        """Get the names of all subgroups."""
        return self._group_table[group].keys()

    def subgroup(self, group: str, subgroup: str) -> Tuple[Emoji, ...]:
        """Get the subgroup of the group."""
        return self._group_table[group][subgroup]

    def subgroup_from_selector(self, selector: str) -> Tuple[Emoji, ...]:
        """Get the subgroup for the given `group::subgroup` selector."""
        names = split_subgroup_selector(selector)
        if len(names) != 2:
            raise KeyError(f'selector "{selector}" does not combine two names')
        group, subgroup = to_group_subgroup(*names)
        if not self.is_group(group):
            raise KeyError(f'selector "{selector}" names non-existent group')
        if not self.is_subgroup(group, subgroup):
            raise KeyError(f'selector "{selector}" names non-existent subgroup')
        return self.subgroup(group, subgroup)

    def select(self, *selectors: str) -> List[Emoji]:
        """Get the emoji matching the given selectors."""
        selection: List[Emoji] = list()

        for selector in selectors:
            # 'ALL' -- all emoji
            if selector == 'ALL':
                for group in self.group_names():
                    for subgroup in self.subgroup_names(group):
                        selection.extend(self.subgroup(group, subgroup))
                continue

            # group::subgroup -- all emoji in the subgroup
            if is_subgroup_selector(selector):
                selection.extend(self.subgroup_from_selector(selector))
                continue

            # name -- all emoji in the group, if it exists
            group = to_group(selector)
            if self.is_group(group):
                for subgroup in self.subgroup_names(group):
                    selection.extend(self.subgroup(group, subgroup))
                continue

            # name -- the named emoji, if it exists
            name = selector.lower()
            if name in self._name_table:
                selection.append(self._name_table[name])
                continue

            raise KeyError(f'selector "{selector}" names neither emoji nor group')

        return selection

    def dump(self, file: Optional[TextIO] = None) -> None:
        """Dump the registry contents by groups and subgroups."""
        if file is None:
            file = sys.stdout

        for group in self.group_names():
            for subgroup in self.subgroup_names(group):
                file.write(group)
                file.write('∷')
                file.write(subgroup)
                file.write(' ≡ ')
                file.write(''.join(e.display for e in self.subgroup(group, subgroup)))
                file.write('\n')


# --------------------------------------------------------------------------------------
# Noto Emoji Sources

NOTO_REPOSITORY = 'https://github.com/googlefonts/noto-emoji/archive/refs/heads/main.zip'

def is_valid_noto_emoji(noto_path: Path) -> bool:
    if not noto_path.exists():
        return False
    if not noto_path.is_dir():
        raise ValueError(
            f'The Noto emoji path "{noto_path}" is not even a directory. '
            'Please move file out of the way or change path with --noto-emoji.'
        )

    entries = set(entry.name for entry in noto_path.iterdir())
    if (
        'colrv1' in entries
        and 'svg' in entries
        and 'third_party' in entries
        and  'emoji_aliases.txt' in entries
    ):
        return True

    raise ValueError(
        f'The Noto emoji path "{noto_path}" points to a directory without '
        'expected contents. Please move directory out of the way or change '
        'path with --noto-emoji'
    )

def ensure_local_noto_emoji(noto_path: Path, verbose: bool = False) -> None:
    if is_valid_noto_emoji(noto_path):
        if verbose:
            log.info(f'Seemingly valid Noto emoji sources at "{noto_path}"')
        return

    noto_zip = noto_path.with_name('noto-emoji.zip')
    if not noto_zip.exists():
        if verbose:
            log.info(f'Downloading Noto emoji sources from "{NOTO_REPOSITORY}"')
        with urlopen(NOTO_REPOSITORY) as response, open(noto_zip, mode='wb') as file:
            shutil.copyfileobj(response, file)

    # With archive representing main branch, it is unpacked into
    # noto-emoji-main. We fix that after unpacking.
    if verbose:
        log.info(f'Unpacking Noto emoji sources into "{noto_path}"')
    shutil.unpack_archive(noto_zip, noto_path.parent, 'zip')
    noto_path.with_name('noto-emoji-main').rename(noto_path)


# --------------------------------------------------------------------------------------
# SVG to PDF Conversion

def remove_page_group_object(document: dict) -> Optional[dict]:
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
    json_path.unlink()
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
        source_dir: Union[Path, str],
        target_dir: Union[Path, str],
    ) -> 'Converter':
        return cls(
            qpdf = which('qpdf'),
            rsvg_convert = which('rsvg-convert'),
            source_dir = Path(source_dir),
            target_dir = Path(target_dir),
        )

    def __call__(self, emoji: 'Emoji', verbose: bool = False) -> Path:
        source = self.source_dir / emoji.svg_path
        target = self.target_dir / f'{emoji.name}.pdf'
        if not target.exists():
            if verbose:
                log.info(f'Converting "{source}" to "{target}"')
            convert_svg_to_pdf(self.rsvg_convert, source, target)
            if verbose:
                log.info(f'Fixing /Page /Group in "{target}"')
            fix_pdf(self.qpdf, target)
        return target


# --------------------------------------------------------------------------------------

DESCRIPTION = """
Generate emoji table and PDF files for the given selectors. A selector may be a
group name, a group and subgroup name with a double colon and no spaces between
them, an emoji name, or `ALL` for all emoji. With some exceptions, an emoji's
name is the emoji's Unicode name with punctuation stripped, spaces replaced by
dashes, and skin tone modifiers simplified to `darkest`, `darker`, `medium`,
`lighter`, and `lightest` (instead of `dark-skin-tone`, `medium-dark-skin-tone`,
`medium-skin-tone`, `medium-light-skin-tone`, and `light-skin-tone`). If
suitably named PDF files exist in the graphics directory, they are not recreated
but included in the emoji table.
"""

def resolved_path(path: str) -> Path:
    return Path(path).resolve()


def create_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=DESCRIPTION,
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        '--show-group-names',
        action='store_true',
        help='show supported group, subgroup names and exit',
    )
    parser.add_argument(
        '--show-emoji-names',
        action='store_true',
        help='show supported emoji names and exit',
    )
    parser.add_argument(
        '--show-special-names',
        action='store_true',
        help='show map from (simplified) Unicode names to emoji names and exit'
    )
    parser.add_argument(
        '--show-names',
        action='store_true',
        help='show group, emoji, as well as special names and exit'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='do not write to file system'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='enable verbose mode'
    )
    parser.add_argument(
        '--registry',
        type=resolved_path,
        default='config/emoji-test.txt',
        metavar='PATH',
        help='use path for file with Unicode emoji sequences',
    )
    parser.add_argument(
        '--noto-emoji',
        type=resolved_path,
        default='noto-emoji',
        metavar='PATH',
        help='use path for directory with Noto color emoji sources',
    )
    parser.add_argument(
        '--graphics',
        type=resolved_path,
        default='emo-graphics',
        metavar='PATH',
        help='use path for directory with generated PDF graphics',
    )
    parser.add_argument(
        '--latex-table',
        type=resolved_path,
        default='emo.def',
        metavar='PATH',
        help='use path for file with LaTeX emoji table',
    )
    parser.add_argument(
        'selectors',
        nargs='*',
        help='names of emoji groups or emoji',
    )
    return parser

def show_names(registry: Registry, options: Any) -> bool:
    showed_something = False

    if options.show_group_names or options.show_names:
        log.header('Supported groups and subgroups:')
        for group in registry.group_names():
            for subgroup in registry.subgroup_names(group):
                log.detail(f'{group}::{subgroup}')
        showed_something = True
    if options.show_emoji_names or options.show_names:
        log.header('Supported emoji names:')
        names = list(registry.emoji_names())
        names.sort()
        for name in names:
            log.detail(f'{name}')
        showed_something = True
    if options.show_special_names or options.show_names:
        log.header('Map from (simplified) Unicode to (special) emoji names:')
        for unicode, selector in RENAMING.items():
            log.detail(f'{unicode:40s} ▶ {selector}')
        showed_something = True
    return showed_something


SPECIAL_FILES = ('lingchi.pdf', 'YHWH.pdf')

def create_inventory(registry: Registry, options: Any) -> List[Emoji]:
    inventory: List[Emoji] = []

    if options.graphics.exists() and options.graphics.is_dir():
        for entry in options.graphics.iterdir():
            if (
                not entry.is_file() or
                entry.suffix != '.pdf' or
                entry.name in SPECIAL_FILES
            ):
                continue

            emoji = registry.lookup(entry.stem)
            if emoji is not None:
                inventory.append(emoji)
            elif options.verbose:
                log.warning(f'"{entry.name}" is not an emoji')

    return inventory


def write_emoji_table(
    requested_emoji: List[Emoji], existing_emoji: List[Emoji], options: Any
) -> List[Emoji]:
    all_emoji = list(set(requested_emoji) | set(existing_emoji))
    all_emoji.sort()

    tmp_table = options.latex_table.with_suffix('.latest.def')
    if not options.dry_run:
        with open(tmp_table, mode='w', encoding='utf8') as file:
            for emoji in all_emoji:
                file.write(emoji.latex_table_entry)
                file.write('\n')
        tmp_table.replace(options.latex_table)

    return all_emoji


def main() -> None:
    options = create_parser().parse_args()
    registry = Registry.from_file(options.registry)
    if show_names(registry, options):
        return

    try:
        # Determine requested emoji.
        requested_emoji = registry.select(*options.selectors)

        # Ensure directory for PDF graphics exists and create converter.
        if not options.dry_run:
            options.graphics.mkdir(parents=True, exist_ok=True)
        convert = Converter.create(options.noto_emoji, options.graphics)

        # Create inventory of existing emoji.
        existing_emoji = create_inventory(registry, options)

        # Noto emoji.
        if not options.dry_run:
            ensure_local_noto_emoji(options.noto_emoji, options.verbose)

        # Convert requested emoji, which does not recreate existing emoji.
        if not options.dry_run:
            for emoji in requested_emoji:
                convert(emoji, options.verbose)

        # Write the emoji table for all emoji.
        all_emoji = write_emoji_table(requested_emoji, existing_emoji, options)

        if options.verbose:
            log.info('Supported emoji: ' + ' '.join(e.display for e in all_emoji))

    except Exception as x:
        log.error(str(x))


if __name__ == '__main__':
    main()
