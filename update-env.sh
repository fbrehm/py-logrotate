#!/bin/bash

base_dir=$( dirname $0 )
cd ${base_dir}
base_dir=$( readlink -f . )

if type -t virtualenv >/dev/null ; then
    :
else
    echo "Command 'virtualenv' not found, please install package 'python-virtualenv' or appropriate." >&2
    exit 6
fi

if type -t msgfmt >/dev/null ; then
    :
else
    echo "Command 'msgfmt' not found, please install package 'gettext' or appropriate." >&2
    exit 6
fi

declare -a VALID_PY_VERSIONS=("3.8" "3.7" "3.6" "3.5")

echo "Preparing virtual environment …"
echo
if [[ ! -f venv/bin/activate ]] ; then
    found="n"
    for py_version in "${VALID_PY_VERSIONS[@]}" ; do
        PYTHON="python${py_version}"
        if type -t ${PYTHON} >/dev/null ; then
            found="y"
            echo
            echo "Found ${PYTHON}."
            echo
            virtualenv --python=${PYTHON} venv
            break
        fi
    done
    if [[ "${found}" == "n" ]] ; then
        echo >&2
        echo "Did not found a usable Python version." >&2
        echo "Usable Python versions are: ${VALID_PY_VERSIONS[*]}" >&2
        echo >&2
        exit 5
    fi
fi

. venv/bin/activate || exit 5

echo "---------------------------------------------------"
echo "Upgrading PIP ..."
echo
pip install --upgrade --upgrade-strategy eager pip
echo

echo "---------------------------------------------------"
echo "Upgrading setuptools + wheel + six ..."
echo
pip install --upgrade --upgrade-strategy eager setuptools wheel six
echo

echo "---------------------------------------------------"
echo "Installing and/or upgrading necessary modules ..."
echo
pip install --upgrade --upgrade-strategy eager --requirement requirements.txt
echo
echo "---------------------------------------------------"
echo "Installed modules:"
echo
pip list --format columns

#echo
#echo "---------------------------------------------------"
#echo "Compiling binary language catalogues"
#echo
#./compile-xlate-msgs.sh

echo
echo "-------"
echo "Fertig."
echo

# vim: ts=4
