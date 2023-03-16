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

To **extract files** embedded in [emo.dtx](emo.dtx) and also rebuild the
[documentation](emo.pdf), run `pdflatex emo.dtx`.

To **configure the emoji**, run `python3 config/emo.py` with appropriate
arguments. The [package documentation](emo.pdf) explains the configuration tool
in detail, but you may find the `-h` for help option sufficient to get started.

To **install this package**, place `emo.def`, `emo.sty`,
`NotoSerifTC-Regular.otf`, and the contents of the `emo-graphics` directory
somewhere where LaTeX can find them. In a pinch, your project directory will do
just fine.

## Supported Emoji

By default, emo supports only a few emoji:

1️⃣ ☣️ ⚖️ ✔️ 🇪🇺 🌁 🌍 🏛️ 🏝️ 🏟️ 🏳️‍🌈 🏷️ 👁️ 👥 💱 💾 📐 📟 🔍 🕵️ 🗑️ 😡 🛑 🤖 🤝 🦜 🧑‍⚖️ 🧻 🧾

Their names are keycap-one, biohazard, balance-scale, check-mark, eu, foggy,
globe-africa-europe, classical-building, desert-island, stadium, rainbow-flag,
label, eye, busts, currency-exchange, floppy-disk, triangular-ruler, pager,
loupe-left, detective, wastebasket, enraged-face, stop-sign, robot, handshake,
parrot, judge, roll-of-paper, and receipt.

The [package's documentation](emo.pdf) explains the underlying naming scheme and
also how to reconfigure which emoji are supported. The [emo.py](config/emo.py)
script takes care of the heavy lifting during reconfiguration, converting SVG
into PDF files and generating an updated `emo.def` file.

## Licensing

This package's LaTeX code is © Copyright 2023 by Robert Grimm and has been
released under the [LPPL v1.3c](https://www.latex-project.org/lppl/lppl-1-3c/)
or later. The Noto fonts distributed with the package are subject to the [SIL
Open Font License v1.1](https://scripts.sil.org/ofl), while the PDF files in the
`emo-graphics` directory are distributed under the [Apache 2.0
license](https://www.apache.org/licenses/LICENSE-2.0), just like the [original
SVG files](https://github.com/googlefonts/noto-emoji).

