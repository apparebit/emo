#!/bin/bash

if [[ -z ${NOCOLOR} ]] && [ -t 2 ]; then
    EXTRA="\e[1m"
    ERROR="\e[1;31m"
    WARN="\e[1;38;5;208m"
    INFO="\e[1;34m"
    RESET="\e[0m"
else
    EXTRA=""
    ERROR=""
    WARN=""
    INFO=""
    RESET=""
fi

log() {
    eval "STYLE=\"\${$1}\""
    printf "${STYLE}$1 $2 ${RESET}\n" >&2
}

log_help() {
    log EXTRA "Invoke as \'./build.sh [<cmd>]\' with <cmd> one of these:"
    log EXTRA "    test    -- run emo's cross-engine tests"
    log EXTRA "    html    -- run emo's HTML conversions"
    log EXTRA "    docs    -- build emo's documentation on pdfTeX"
    log EXTRA "    all     -- execute test, html, and docs in that order (default)"
    log EXTRA "    luadocs -- build emo's documentation on LuaTeX"
    log EXTRA "    luaall  -- execute test, html, and luadocs in that order"
}

if [[ -z ${BASH} ]]; then
    log ERROR "It looks like you source'd this script; please run it instead"
    log EXTRA '$ chmod +x build.sh'
    log EXTRA '$ ./build.sh'
    return 1
fi

test-with-engine() {
    log INFO "Test with $1"
    "$1" -jobname=$1-canary -interaction=batchmode canary
    if [ $? -ne 0 ]; then
        log ERROR "$1 failed to compile 'canary.tex'"
        exit 1
    fi
}

test() {
    test-with-engine pdflatex
    test-with-engine xelatex
    test-with-engine lualatex
    pdfunite pdflatex-canary.pdf xelatex-canary.pdf lualatex-canary.pdf canary.pdf
    log INFO 'Be sure to inspect "canary.pdf"!'
}

html() {
    log INFO "Convert to HTML with LaTeXML"
    # LaTeXML: --includestyles handles emo-supprt package
    latexmlc --includestyles --dest=demo-latexml.html demo.tex
    if [ $? -ne 0 ]; then
        log ERROR "latexml failed to convert 'demo.tex' to HTML"
        exit 1
    fi

    # Remove run date comment and footer. The latter is just plain tacky.
    sed -i '' '/^<!--Generated on /d' ./demo-latexml.html
    sed -i '' '/^<footer class="ltx_page_footer">/{N;N;d;}' ./demo-latexml.html

    log INFO "Convert to HTML with TeX4ht"
    # TeX4ht: -l is necessary for selecting LuaTeX engine
    make4ht -l -j demo-tex4ht demo.tex
    if [ $? -ne 0 ]; then
        log ERROR "tex4ht failed to convert 'demo.tex' to HTML"
        exit 1
    fi

    log INFO 'Be sure to inspect "demo.html"!'
}

build-docs() {
    log INFO "Build documentation with $1"
    $1 -interaction=batchmode emo.dtx
    #if [ $? -ne 0 ]; then
    #    log ERROR "$1 failed to compile 'emo.dtx'"
    #    exit 1
    #fi
}

docs() {
    build-docs "$1"
    log INFO "Make indices"
    makeindex -s gind.ist -o emo.ind emo.idx
    makeindex -s gglo.ist -o emo.gls emo.glo
    build-docs "$1"
    build-docs "$1"
}

target=${1:-all}
case $target in
    test    )  test ;;
    html    )  html ;;
    docs    )  docs pdflatex ;;
    luadocs )  docs lualatex ;;
    all  )
        test
        html
        docs pdflatex
        ;;
    luaall  )
        test
        html
        docs lualatex
        ;;
    *       )
        log ERROR "Unknown command \'${target}\'!"
        log_help
        exit 1
        ;;
esac
