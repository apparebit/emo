#!/bin/bash

if [[ -z ${NOCOLOR} ]] && [ -t 2 ]; then
    STUFF="\e[1m"
    ERROR="\e[1;31m"
    WARN="\e[1;38;5;208m"
    INFO="\e[1;34m"
    RESET="\e[0m"
else
    STUFF=""
    ERROR=""
    WARN=""
    INFO=""
    RESET=""
fi

log() {
    eval "STYLE=\"\${$1}\""
    printf "${STYLE}$1 $2 ${RESET}\n" >&2
}

nope() {
    log ERROR "$@"
    exit 1
}

if [[ -z ${BASH} ]]; then
    log ERROR "It looks like you source'd this script; please run it instead"
    log STUFF '$ chmod +x build.sh'
    log STUFF '$ ./build.sh'
    return 1
fi

test() {
    pdflatex -jobname=pdftex-canary canary   || nope "pdflatex failed"
    xelatex -jobname=xetex-canary canary     || nope "xelatex failed"
    lualatex -jobname=luatex-canary canary   || nope "lualatex failed"
    pdfunite pdftex-canary.pdf xetex-canary.pdf luatex-canary.pdf canary.pdf
    log INFO 'Be sure to inspect "canary.pdf"!'
}

html() {
    # LaTeXML: --includestyles handles emo-supprt package
    latexmlc --includestyles --dest=demo-latexml.html demo.tex  || nope "LaTeXML failed"

    # Remove run date comment and footer. The latter is just plain tacky.
    sed -i '' '/^<!--Generated on /d' ./demo-latexml.html
    sed -i '' '/^<footer class="ltx_page_footer">/{N;N;d;}' ./demo-latexml.html

    # TeX4ht: -l is necessary for selecting LuaTeX engine
    make4ht -l -j demo-tex4ht demo.tex  || nope "TeX4ht failed"
    log INFO 'Be sure to inspect "demo.html"!'
}

docs() {
    lualatex emo.dtx
    makeindex -s gind.ist -o emo.ind emo.idx
    makeindex -s gglo.ist -o emo.gls emo.glo
    lualatex emo.dtx
    lualatex emo.dtx
}

target=${1:-all}
case $target in
    test )  test ;;
    html )  html ;;
    docs )  docs ;;
    all  )
        test
        html
        docs
        ;;
    *       )
        log ERROR "Unknown command \'${target}\'!"
        log ERROR "Use \'test\', \'html\', \'docs\', or \'all\'."
        log ERROR "Or just omit the argument."
        exit 1
        ;;
esac
