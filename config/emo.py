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
from datetime import datetime
from enum import Enum
from itertools import chain
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from textwrap import dedent
from typing import (
    Any, Dict, Iterable, KeysView, List, Mapping,
    NoReturn, Optional, Set, TextIO, Tuple, Union
)
from urllib.request import urlopen

# --------------------------------------------------------------------------------------
# Provide a simple console logger

class Logger:
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

logger = Logger()

# --------------------------------------------------------------------------------------
# Inline style sheets

STYLE_LINK = re.compile(
    r"""
    <link[ ]+
    (rel=["']stylesheet["'][ ]+)?
    href=["'](?P<sheet>[^"']+)["'][ ]+
    (rel=["']stylesheet["'][ ]+)?
    type=["']text/css["']
    >
    """,
    re.VERBOSE
)

def inline_style_sheets(markup: Path) -> None:
    logger.info(f'Inlining style sheets for "{markup}"')
    with open(markup, mode='r', encoding='utf8') as file:
        content = file.read()

    style_sheets = []
    fragments = []

    last_index = 0
    for link in STYLE_LINK.finditer(content):
        fragments.append(content[last_index:link.start()])

        style_sheet = link.group('sheet')
        style_sheets.append(style_sheet)

        logger.info(f'Loading style sheet "{style_sheet}"')
        with open(style_sheet, mode='r', encoding='utf8') as file:
            css = file.read()
        if not css.startswith('\n'):
            css = f'\n{css}'

        fragments.append(f'<style>{css}</style>')
        last_index = link.end()

    fragments.append(content[last_index:])

    # Write result and clean up.
    tmp_file = markup.with_suffix('.tmp.html')
    logger.info(f'Writing self-contained "{tmp_file}"')
    with open(tmp_file, mode='w', encoding='utf8') as file:
        for fragment in fragments:
            file.write(fragment)

    tmp_file.replace(markup)

# --------------------------------------------------------------------------------------
# Build an archive for release

EMO_FILES = (
    'emo.def',
    'emo.dtx',
    'emo.pdf',
    'emo-lingchi.ttf',
    'README.md',
    'config/emo.py',
    'config/emoji-test.txt'
)

EMO_GRAPHICS = 'emo-graphics'

EMO_METADATA = re.compile(
    r"""
    ^[ ]{4}\[
        (?P<date>\d{4}/\d{1,2}/\d{1,2})
        [ ]
        v(?P<version>\d+\.\d+)
        [ ]
        (?P<info>[^\]]+)
    \]
    """,
    re.VERBOSE | re.MULTILINE
)

def make_release() -> None:
    # Determine repository root.
    source = Path(__file__).parent.parent

    # Determine package metadata.
    metadata = EMO_METADATA.search((source / 'emo.dtx').read_text(encoding='utf8'))
    if metadata is None:
        raise ValueError(f'Package metadata missing from "{source / "emo.dtx"}"')

    version = metadata.group('version')
    logger.info(f'Preparing release {version} for "{source}"')

    # Make sure no archive exists.
    archive = source / f'emo-{version}.zip'
    if archive.exists():
        raise ValueError(
            f'Archive file "{archive}" already exists, please move out of way.'
        )

    # Set up staging directory.
    staging = source / 'emo'
    if staging.exists():
        raise ValueError(
            f'Staging directory "{staging}" already exists, please move out of way.'
        )
    logger.info(f'Creating staging directory "{staging}"')
    staging.mkdir()

    # Process all files belonging into release.
    for path in chain(map(Path, EMO_FILES), source.glob('emo-graphics/emo-*.pdf')):
        path = source / path

        # To stage a file in the repository root, just copy it.
        if path.parent == source:
            logger.info(f'Staging "{path.name}"')
            shutil.copy(path, staging)
            continue

        # To stage a file in a subdirectory, get relative path and, if necessary,
        # recreate path in staging area. Then copy into that subdirectory.
        nested_staging = staging / path.parent.relative_to(source)
        if not nested_staging.exists():
            logger.info(f'Creating nested staging directory "{nested_staging}"')
            nested_staging.mkdir(parents=True)

        logger.info(f'Staging "{path.relative_to(source)}"')
        shutil.copy(path, nested_staging)

    # Create archive.
    shutil.make_archive(
        str(archive.with_suffix('')),
        'zip',
        root_dir=staging.parent,
        base_dir=staging.name,
    )

# --------------------------------------------------------------------------------------
# Normalize emoji names

PUNCTUATION = re.compile(r"""["'’“”&!(),.:]""")
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

# The sets of hair and skin modifiers.
HAIR_MODIFIERS = {
    'red-hair',
    'curly-hair',
    'white-hair',
    'bald',
}

SKIN_MODIFIERS = {
    'darkest',
    'darker',
    'medium',
    'lighter',
    'lightest',
}

# Regex for names of emoji with explicit gender, hair, or skin tone.
GENDER_HAIR_SKIN = re.compile(rf"""
    (\A|[^a-z])
    (
        {"|".join(HAIR_MODIFIERS)}
        | {"|".join(SKIN_MODIFIERS)}
        | man | men
        | woman | women
    )
    (\Z|[^a-z])
""", re.VERBOSE)

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
# Handle emoji codepoints

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
# Normalize emoji group and subgroup names

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
# Define emoji status

class Status(str, Enum):
    COMPONENT = 'component'
    FULLY_QUALIFIED = 'fully-qualified'
    MINIMALLY_QUALIFIED = 'minimally-qualified'
    UNQUALIFIED = 'unqualified'


# --------------------------------------------------------------------------------------
# Define LaTeX commands for emoji table

class LatexCommand:
    @staticmethod
    def ifextra() -> str:
        return '\\ifEmojiExtra'

    @staticmethod
    def begin_group(group: str) -> str:
        return f'\\EmojiBeginGroup{{{group}}}'

    @staticmethod
    def begin_subgroup(group: str, subgroup: str) -> str:
        return f'\\EmojiBeginSubgroup{{{group}}}{{{subgroup}}}'

    @staticmethod
    def define(name: str, codepoints: str) -> str:
        return f'\\DefineEmoji{{{name}}}{{{codepoints}}}'

    @staticmethod
    def end_subgroup(group: str, subgroup: str) -> str:
        return f'\\EmojiEndSubgroup{{{group}}}{{{subgroup}}}'

    @staticmethod
    def end_group(group: str) -> str:
        return f'\\EmojiEndGroup{{{group}}}'

# --------------------------------------------------------------------------------------
# Define emoji descriptor

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
    def is_diverse(self) -> bool:
        return GENDER_HAIR_SKIN.search(self.name) is not None

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
    def pdf_file(self) -> str:
        return f'emo-{self.name}.pdf'

    @property
    def latex_table_entry(self) -> str:
        # The Unicode codepoints of the keycap emoji for hash #, star *, and
        # the digits 0 through 9 start with the plain ASCII codepoint followed
        # by the U+FE0F U+20E3 emoji modifiers. Since TeX is not aware of emoji
        # modifiers, the hash # for keycap-hash trips it up. In that one case,
        # we use \char instead.
        return LatexCommand.define(
            self.name,
            self.latex_chars if self.name == 'keycap-hash' else str(self)
        )


# --------------------------------------------------------------------------------------
# Parse Unicode TR-51's `emoji-test.txt`

NameTable = Mapping[str, Emoji]
CodepointSet = Set[Tuple[int, ...]]
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
# Maintain emoji registry

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

    def non_diverse_people(self) -> List[Emoji]:
        """
        Return a list of emoji from the People & Body group that do not specify
        the gender, hair, or skin tone.
        """
        all_emoji: List[Emoji] = list()

        for subgroup in self.subgroup_names('people-and-body'):
            for emoji in self.subgroup('people-and-body', subgroup):
                if not emoji.is_diverse:
                    all_emoji.append(emoji)

        return all_emoji

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

            # 'NONDIVERSE' -- people & body without gender, hair, or skin color
            if selector == 'NONDIVERSE':
                selection.extend(self.non_diverse_people())
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

    def _is_subgroup_included(
        self, group: str, subgroup: str, selection: CodepointSet
    ) -> bool:
        """
        Determine whether any of the emoji in the named subgroup is part of the
        selection.
        """
        for emoji in self.subgroup(group, subgroup):
            if emoji.codepoints in selection:
                return True
        return False

    def _subgroup_inclusions(
            self, group: str, selection: CodepointSet
        ) -> Dict[str, bool]:
        """
        Compute the map from subgroup names to flag for whether a subgroup emoji
        is part of the selection.
        """
        return {
            subgroup: self._is_subgroup_included(group, subgroup, selection)
            for subgroup in self.subgroup_names(group)
        }

    def write_latex_table(
        self, emoji_selection: Set[Emoji], options: Any
    ) -> List[Emoji]:
        """
        Write the emoji table for the given collection of emoji while preserving
        Unicode display order and grouping.
        """
        codepoint_selection = { emoji.codepoints for emoji in emoji_selection }
        all_emoji: List[Emoji] = list()

        tmp_table = (
            os.devnull if options.dry_run
            else options.latex_table.with_suffix('.latest.def')
        )
        with open(tmp_table, mode='w', encoding='utf8') as file:
            def write(text: str) -> None:
                if not options.dry_run:
                    file.write(text)

            today = datetime.today().strftime('%Y-%m-%d')
            write(f'\\ProvidesFile{{emo.def}}[{today} v1.0 emo•ji table]\n')

            for group in self.group_names():
                include = self._subgroup_inclusions(group, codepoint_selection)
                if not any(include.values()):
                    continue

                write('\n\n')
                write(LatexCommand.begin_group(group))
                write('\n')
                is_first = True

                for subgroup in self.subgroup_names(group):
                    if not include[subgroup]:
                        continue

                    if is_first:
                        is_first = False
                    else:
                        write('\n')

                    write(LatexCommand.begin_subgroup(group, subgroup))
                    write('\n')
                    for emoji in self.subgroup(group, subgroup):
                        if not emoji.codepoints in codepoint_selection:
                            continue

                        all_emoji.append(emoji)
                        write(emoji.latex_table_entry)
                        write('\n')

                    write(LatexCommand.end_subgroup(group, subgroup))
                    write('\n')

                write(LatexCommand.end_group(group))
                write('\n')

            write(
                dedent(f"""
                    {LatexCommand.ifextra()}
                    {LatexCommand.begin_group('extra')}
                    {LatexCommand.begin_subgroup('extra', 'extra')}
                    {LatexCommand.define('lingchi', '凌遲')}
                    {LatexCommand.define('YHWH', 'יהוה')}
                    {LatexCommand.end_subgroup('extra', 'extra')}
                    {LatexCommand.end_group('extra')}
                    \\fi
                """)
            )

        if not options.dry_run:
            tmp_table.replace(options.latex_table)
        return all_emoji

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
# Download Noto emoji sources

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
            logger.info(f'Seemingly valid Noto emoji sources at "{noto_path}"')
        return

    noto_zip = noto_path.with_name('noto-emoji.zip')
    if not noto_zip.exists():
        if verbose:
            logger.info(f'Downloading Noto emoji sources from "{NOTO_REPOSITORY}"')
        with urlopen(NOTO_REPOSITORY) as response, open(noto_zip, mode='wb') as file:
            shutil.copyfileobj(response, file)

    # With archive representing main branch, it is unpacked into
    # noto-emoji-main. We fix that after unpacking.
    if verbose:
        logger.info(f'Unpacking Noto emoji sources into "{noto_path}"')
    shutil.unpack_archive(noto_zip, noto_path.parent, 'zip')
    noto_path.with_name('noto-emoji-main').rename(noto_path)


# --------------------------------------------------------------------------------------
# Convert SVG to PDF

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
        target = self.target_dir / emoji.pdf_file
        if not target.exists():
            if verbose:
                logger.info(f'Converting "{source}" to "{target}"')
            convert_svg_to_pdf(self.rsvg_convert, source, target)
            if verbose:
                logger.info(f'Fixing /Page /Group in "{target}"')
            fix_pdf(self.qpdf, target)
        return target


# --------------------------------------------------------------------------------------
# Provide tool help and command line options

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

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '--show-group-names',
        action='store_true',
        help='show supported group, subgroup names and exit',
    )
    group.add_argument(
        '--show-emoji-names',
        action='store_true',
        help='show supported emoji names and exit',
    )
    group.add_argument(
        '--show-special-names',
        action='store_true',
        help='show map from (simplified) Unicode names to emoji names and exit'
    )
    group.add_argument(
        '--show-names',
        action='store_true',
        help='show group, emoji, as well as special names and exit'
    )
    group.add_argument(
        '-r', '--make-release',
        action='store_true',
        help='make a release and exit',
    )

    parser.add_argument(
        'selectors',
        nargs='*',
        help='names of emoji groups or emoji',
    )
    return parser

# --------------------------------------------------------------------------------------
# Show group, emoji, and special names

def show_names(registry: Registry, options: Any) -> bool:
    showed_something = False

    if options.show_group_names or options.show_names:
        logger.header('Supported groups and subgroups:')
        for group in registry.group_names():
            for subgroup in registry.subgroup_names(group):
                logger.detail(f'{group}::{subgroup}')
        showed_something = True
    if options.show_emoji_names or options.show_names:
        logger.header('Supported emoji names:')
        names = list(registry.emoji_names())
        names.sort()
        for name in names:
            logger.detail(f'{name}')
        showed_something = True
    if options.show_special_names or options.show_names:
        logger.header('Map from (simplified) Unicode to (special) emoji names:')
        for unicode, selector in RENAMING.items():
            logger.detail(f'{unicode:40s} ▶ {selector}')
        showed_something = True
    return showed_something

# --------------------------------------------------------------------------------------
# Create emoji inventory

SPECIAL_FILES = ('emo-lingchi.pdf', 'emo-YHWH.pdf')

def create_inventory(registry: Registry, options: Any) -> List[Emoji]:
    specials = list(SPECIAL_FILES)
    inventory: List[Emoji] = []

    if options.graphics.exists() and options.graphics.is_dir():
        for entry in options.graphics.iterdir():
            if not entry.is_file() or not entry.match('emo-*.pdf'):
                continue

            if entry.name in SPECIAL_FILES:
                specials.remove(entry.name)
                continue

            emoji = registry.lookup(entry.stem[4:])
            if emoji is not None:
                inventory.append(emoji)
            elif options.verbose:
                logger.warning(f'"{entry.name}" does not depict an emoji')

    if len(specials) == 1:
        raise FileNotFoundError(f'PDF graphic "emo-graphics/{specials[0]}" is missing!')
    elif len(specials) == 2:
        raise FileNotFoundError(
            f'PDF graphics "{specials[0]}" and "{specials[1]}" '
            'in "emo-graphics" are missing!'
        )

    return inventory

# --------------------------------------------------------------------------------------
# Run this script

def main() -> None:
    try:
        # Parse command line options.
        options = create_parser().parse_args()

        # Create release.
        if options.make_release and options.dry_run:
            raise ValueError('Unable to dry run selected build function')
        elif options.make_release:
            make_release()
            return

        # Populate registry, maybe list names.
        registry = Registry.from_file(options.registry)
        if show_names(registry, options):
            return

        # Determine requested emoji.
        requested_emoji = registry.select(*options.selectors)

        # Ensure directory for PDF graphics exists and create converter.
        if not options.dry_run:
            options.graphics.mkdir(parents=True, exist_ok=True)
        convert = Converter.create(options.noto_emoji, options.graphics)

        # Create inventory of existing emoji.
        existing_emoji = create_inventory(registry, options)

        # Download Noto emoji sources if they haven't been before.
        if not options.dry_run:
            ensure_local_noto_emoji(options.noto_emoji, options.verbose)

        # Convert requested emoji, which does not recreate existing emoji.
        if not options.dry_run:
            for emoji in requested_emoji:
                convert(emoji, options.verbose)

        # Write emoji table with all emoji in Unicode display order.
        all_emoji = registry.write_latex_table(
            set(requested_emoji) | set(existing_emoji), options
        )

        if options.verbose:
            logger.info('Supported emoji: ' + ' '.join(e.display for e in all_emoji))

    except Exception as x:
        logger.error(str(x))


if __name__ == '__main__':
    main()
