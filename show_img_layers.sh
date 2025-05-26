#!/bin/bash
#*----------------------------------------------------------------------------*
#* NAME: show_img_layers.sh
#*
#* DESCRIPTION:
#* Showe layers for defined images
#*----------------------------------------------------------------------------*

CONFIG=${1:-ocisictl.yaml}

if $(which yq >/dev/null 2>&1)
then
    true
else
    echo "$0 depends on yq - not found in path"
    exit 2
fi

#*----------------------------------------------------------------------------*
function _logbar
{
    declare -r bar='#* ----------------------------------------------------------------------'

    echo $bar
    echo $*
    echo $bar
}
#*----------------------------------------------------------------------------*
function config_imgs_managers
{
    yq '.[].manager' ${CONFIG} | sort -u | sed '/null/d'
}
#*----------------------------------------------------------------------------*
function show_imgs_layers
{
    local manager

    for manager in $(config_imgs_managers)
    do
        local imgs
        if [ "${manager}" = "docker" ]
        then
            imgs=$(${manager} image ls --format json | yq -p=j 'select(.Repository != "<none>") | (.Repository + ":" + .Tag)' | sed '/---/d' | sort)
        elif [ "${manager}" = "podman" ]
        then
            imgs=$(${manager} image ls --format json | yq -p=j '.[] | select(.Names != null) | .Names[0]' | sed '/---/d' | sort)
        else
            continue
        fi

        local img
        for img in ${imgs}
        do
            _logbar ${manager} - ${img}
            ${manager} inspect --format json ${img} | yq -P .[0].RootFS.Layers
        done
    done
}
#*----------------------------------------------------------------------------*

show_imgs_layers

#*----------------------------------------------------------------------------*
