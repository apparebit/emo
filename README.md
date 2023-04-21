# emo•ji for all (LaTeX engines)

This package defines the `\emo{<emoji-name>}` macro for including color emoji in
a document no matter the LaTeX engine. It uses the Noto color emoji font if the
engine supports doing so and falls back onto PDF graphics otherwise. In either
case, `\emo{desert-island}` results in 🏝 and `\emo{parrot}` results in 🦜. Emo
may come in particularly handy when dealing with academic publishers that
provide only minimal support for non-Latin scripts (cough,
[ACM](https://www.acm.org), cough).

Emo's source repository is <https://github.com/apparebit/emo>. It also is
available [through CTAN](https://ctan.org/pkg/emo). Emo supports conversion to
HTML with [LaTeXML](https://github.com/brucemiller/LaTeXML) or
[TeX4ht](https://tug.org/tex4ht/). When using the latter tool, please be sure to
use |make4ht -l| as invocation.

## Package Options

When emo is used with the `extra` option, this package also defines the
`\lingchi` and `\YHWH` macros for 凌遲 and יהוה, respectively. Both macros
preserve a subsequent space as space, no backslash needed.

When used with the `index` option, this package also emits a raw index entry for
each use of an emoji into an emo index or `.edx` file.

## Installation

To **extract files** embedded in [emo.dtx](emo.dtx), run `pdftex emo.dtx`. Note
that plain old `tex` won't do, since it mangles this README. `pdflatex` works,
but also generates the package documentation. The embedded files are `build.sh`,
`emo.ins`, `emo.sty`, `emo.sty.ltxml`, and `README.md`.

To **build the documentation** embedded in `emo.dtx`, run `source build.sh`. The
shell script invokes `pdflatex emo.dtx` thrice and `makeindex` once each for the
change and the symbol indices, resulting in [emo.pdf](emo.pdf).

To **configure the emoji**, run `python3 config/emo.py` with appropriate
arguments. The [package documentation](emo.pdf) explains the configuration tool
in detail, but you may find the `-h` for help option sufficient to get started.

To **install this package**, place `emo.def`, `emo.sty`, `emo.sty.ltxml`,
`emo-lingchi.ttf`, and the `emo-graphics` directory with the fallback PDF files
somewhere where LaTeX can find them. In a pinch, your project directory will do.

## Supported Emoji

By default, emo supports only a few emoji:

1️⃣ ☣️ ⚖️ ✔️ ➕ 🇪🇺 🉐 🌁 🌍 🏛️ 🏝️ 🏟️ 🏳️‍🌈 🏷️ 👁️ 👥 💥 💱 💾 📈 📐 📟 🔍
🕵️ 🗑️ 😡 🛑 🤖 🤝 🤦 🤯 🦜 🧑‍⚖️ 🧻 🧾

Their names are keycap-one, biohazard, balance-scale, check-mark, plus, eu,
japanese-bargain-button, foggy, globe-africa-europe, classical-building,
desert-island, stadium, rainbow-flag, label, eye, busts, collision,
currency-exchange, floppy-disk, chart-increasing, triangular-ruler, pager,
loupe-left, detective, wastebasket, enraged-face, stop-sign, robot, handshake,
person-facepalming, exploding-head, parrot, judge, roll-of-paper, and receipt.

The [package's documentation](emo.pdf) explains the underlying naming scheme and
also how to reconfigure which emoji are supported. The [emo.py](config/emo.py)
script takes care of the heavy lifting during reconfiguration, converting SVG
into PDF files and generating an updated `emo.def` file.

## Copyright and Licensing

This package combines code written in LaTeX, Python, and Perl with Unicode data
about emoji as well as graphics and fonts derived from Google's Noto fonts. As a
result, a number of different licenses apply, all of which are [OSI
approved](https://opensource.org/licenses/) and non-copyleft:

  * This package's [LaTeX code](emo.dtx) is © Copyright 2023 by Robert Grimm and
    has been released under the [LPPL
    v1.3c](https://www.latex-project.org/lppl/lppl-1-3c/) or later.
  * The [emo.py](config/emo.py) configuration script also is © Copyright 2023 by
    Robert Grimm but has been released under the [Apache 2.0
    license](https://www.apache.org/licenses/LICENSE-2.0).
  * The [emoji-test.txt](config/emoji-test.txt) configuration file is a data
    file from [Unicode TR-51](https://unicode.org/reports/tr51/) and hence
    subject to the [Unicode License](https://www.unicode.org/license.txt).
  * The `emo-lingchi.ttf` font is a two-glyph subset of the serif traditional
    Chinese version of Google's [Noto
    fonts](https://github.com/notofonts/noto-cjk) and hence subject to the [SIL
    Open Font License v1.1](https://scripts.sil.org/ofl).
  * The PDF graphics in the `emo-graphics` directory are derived from the
    sources for [Noto's color emoji](https://github.com/googlefonts/noto-emoji)
    and hence subject to the Apache 2.0 license.

