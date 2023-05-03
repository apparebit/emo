%%
%% This is file `emo-test.cls',
%% generated with the docstrip utility.
%%
%% The original source files were:
%%
%% emo.dtx  (with options: `testing')
%% 
%% emo•ji for all (LaTeX engines)
%% (C) Copyright 2023 by Robert Grimm
%% Released under LPPL v1.3c or later
%% <https://github.com/apparebit/emo>
%% 
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{emo-test}[2023/05/01 v0.5 Testing emo]
\newif\ifemo@verbose@canary\emo@verbose@canaryfalse
\DeclareOption{verbose}{\emo@verbose@canarytrue}
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{standalone}}
\ProcessOptions\relax
\LoadClass[border=10pt, varwidth=6in]{standalone}
\RequirePackage[extra]{emo}
\RequirePackage{iftex}
\RequirePackage{xcolor}
\iftutex
\RequirePackage{fontspec}
\RequirePackage{libertinus}
\setmonofont{inconsolata}
\else
\RequirePackage{libertinus}
\RequirePackage{inconsolata}
\fi
\ifxetex
\def\enginename{XeTeX}
\else
\ifluatex
\def\enginename{LuaTeX}
\else
\ifpdftex
\def\enginename{pdfTeX}
\else
\def\enginename{unknown engine}
\fi
\fi
\fi
\definecolor{emo@canary@frameinner}{HTML}{636366}
\definecolor{emo@canary@frameouter}{HTML}{48484A}
\definecolor{emo@canary@background}{HTML}{E5E5EA}
\setlength{\fboxrule}{0.5pt}
\setlength{\fboxsep}{0pt}
\newcommand\emo@nobox[1]{#1}
\newcommand\emo@wordbox[1]{%
    \fcolorbox{emo@canary@frameinner}{white}{#1}}
\newcommand\emo@linebox[1]{%
    \fcolorbox{emo@canary@frameouter}{emo@canary@background}{#1}}
\def\@sampletext#1{%
    \emo@linebox{%
        #1{It's} #1{\lingchi}:
        #1{Please}, #1{\YHWH}, #1{have} #1{mercy}
        #1{\emo{pleading-face}}!%
    }%
    \vspace{1ex}%
}
\newcommand*\sampletext{%
    \@ifstar{\@sampletext{\emo@wordbox}}{\@sampletext{\emo@nobox}}%
}
\newsavebox{\emo@canary@actual}
\newsavebox{\emo@canary@expected}
\newcommand\checkwidth[5]{%
    \sbox\emo@canary@actual{#2.}%
    \ifemo@use@font%
        \sbox\emo@canary@expected{%
            \begingroup\csname emo@font@#3\endcsname #4\endgroup.}%
    \else%
    \ifemo@use@unicode%
        \sbox\emo@canary@expected{\begingroup #4\endgroup.}%
    \else%
        \sbox\emo@canary@expected{%
            \raisebox{-0.2ex}{%
                \includegraphics[height=1em]{emo-graphics/emo-#5}}.}%
    \fi%
    \fi%
    \ifemo@verbose@canary%
        \fbox{\usebox{\emo@canary@actual}}\space%
        \fbox{\usebox{\emo@canary@expected}}\space%
    \fi%
    \def\macroname{\texttt{\char`\\#1}}%
    \ifdim\wd\emo@canary@actual=\wd\emo@canary@expected%
        \mbox{\macroname{} \emo{check-mark-button}}%
    \else%
        \edef\emo@actual{\the\wd\emo@canary@actual}%
        \edef\emo@expected{\the\wd\emo@canary@expected}%
        \mbox{\macroname{} \emo{cross-mark} \emo@actual{} \emo@expected}%
    \fi%
}
\setlength\parindent{0pt}
\setlength{\parskip}{1ex}
\endinput
%%
%% End of file `emo-test.cls'.