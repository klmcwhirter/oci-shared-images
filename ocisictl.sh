#!/bin/bash

command -v uv 2>&1 >/dev/null
has_uv=$?
if [[ $has_uv != 0 ]]
then
    echo "$0 requires uv to be installed and available on PATH. It is available via: brew install uv"
fi

uv python find 3.14 2>&1 >/dev/null
has_py=$?
if [[ $has_py != 0 ]]
then
    echo "$0 requires python 3.14 to be installed and available on PATH."
fi

command -v uvextras 2>&1 >/dev/null
has_uvextras=$?
if [[ $has_uvextras != 0 ]]
then
    echo "$0 requires uvextras to be installed and available on PATH."
fi

if [[ $has_uvextras != 0 || $has_py != 0 || $has_uv != 0 ]]
then
    exit 2
fi

if [ ! -d .venv ]
then
    uvextras run create
fi

uvextras run start -- "$@"
