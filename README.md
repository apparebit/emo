# Emo: emoji for all (LaTeX engines)

This package defines the `\emo{<emoji-name>}` macro for including color emoji
in a document no matter the input encoding or LaTeX engine. It uses the Noto
color emoji font if the engine supports doing so and falls back onto PDF
graphics otherwise.  🎉

When emo is used with the `extra` option, this package also defines the
`\lingchi` and `\YHWH` macros for 凌遲 and יהוה, respectively. Both macros
preserve a subsequent space as space, no backslash needed. When used with the
`index` option, this package also emits a raw index entry for each use of an
emoji into an `.edx` file.

## Installation

To extract files embedded in [emo.dtx](emo.dtx) and also rebuild the
[documentation](emo.pdf), run `pdflatex emo.dtx`. To install this package, place
`emo.def`, `emo.sty`, `NotoSerifTC-Regular.otf`, and the contents of the
`emo-graphics` directory somewhere where LaTeX can find them. In a pinch, your
project directory will do just fine.

## Supported Emoji

⚖️ ☣️ ✔️ 🏛 🏝 😡 🇪🇺 👁 💾 🌁 🌍 🤝 🧑‍⚖️ 1️⃣ 🏷 🔍 📟 🦜 🏳️‍🌈 🧾 🤖 🏟 🛑 📐 🗑

The above emoji are named balance-scale, biohazard, check-mark,
classical-building, desert-island, enraged-face, eu, eye, floppy-disk, foggy,
globe-africa-europe, handshake, judge, keycap-one, label, loupe-left, pager,
parrot, rainbow-flag, receipt, robot, stadium, stop-sign, triangular-ruler, and
wastebasket. These are the same names as their Unicode names, only interword
spaces have been replaced by dashes.

## Implementation

For each emoji, the implementation requires an entry in the emoji table in
`emo.def` as well as a PDF file with the emoji's likeness. For consistency, emo
uses the same artwork under LuaLaTeX and as fallback. The only difference is
that the fallback version relies on PDF graphics that were previously converted
from tbe SVG source files included with the source code for [Noto's color
emoji](https://github.com/googlefonts/noto-emoji). I manually prepared the
initial set of 25 emoji. Since that's less than 0.1% of all emoji, there
obviously remains a lot of conversion work. But that work also is eminently
automatable and a Python script doing just that is almost done.

The conversion is more involved than just using `rsvg-convert` to turn SVG into
PDF files. As it turns out, PDF files created by that command line tool may
include a `\Page` `\Group` object that confuses `pdflatex`. Hence, the
[conversion script](scripts/emo.py) leverages `qpdf` to automatically remove
these objects again (but only those objects). The conversion script also
leverages the `emoji-text.txt` file from Unicode 15 for identifying and
potentially converting all standardized emoji.

Emo's [package documentation](emo.pdf) includes detailed documentation on the
implementation of this package.

## Licensing

This package's LaTeX code is © Copyright 2023 by Robert Grimm and has been
released under the [LPPL v1.3c](https://www.latex-project.org/lppl/lppl-1-3c/)
or later. The Noto fonts distributed with the package are subject to the [SIL
Open Font License v1.1](https://scripts.sil.org/ofl), while the PDF files in the
`emo-graphics` directory are distributed under the [Apache 2.0
license](https://www.apache.org/licenses/LICENSE-2.0), just like the [original
SVG files](https://github.com/googlefonts/noto-emoji).

