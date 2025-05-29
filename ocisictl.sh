#!/bin/bash

command -v pdm 2>&1 >/dev/null
has_pdm=$?
if [[ $has_pdm != 0 ]]
then
    echo "$0 requires pdm to be installed and available on PATH."
fi

pdm py find 3.14.b 2>&1 >/dev/null
has_py=$?
if [[ $has_py != 0 ]]
then
    echo "$0 requires python 3.14 beta to be installed and available on PATH."
fi

command -v uv 2>&1 >/dev/null
has_uv=$?
if [[ $has_uv != 0 ]]
then
    echo "$0 requires uv to be installed and available on PATH. It is available via: brew install uv"
fi

if [[ $has_pdm != 0 || $has_py != 0 || $has_uv != 0 ]]
then
    exit 2
fi

if [ ! -d .venv ]
then
    pdm create
fi

pdm start $@
