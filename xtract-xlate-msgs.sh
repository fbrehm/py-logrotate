#!/bin/bash

set -e
set -u

output_dir="po"
pot_file="${output_dir}/plogrotate.pot"
domain='plogrotate'
pkg_version="0.7.0"

used_locales="de"

cd $(dirname $0)

if [[ -f debian/changelog ]] ; then
    pkg_version=$( head -n 1 debian/changelog | awk '{print $2}' | sed -e 's/[\(\)]//g' )
fi

pybabel extract --keyword '_' --keyword '__' \
        --output "${pot_file}" \
        --width 99 \
        --sort-by-file \
        --msgid-bugs-address=frank@brehm-online.com \
        --copyright-holder "Frank Brehm" \
        --project "${domain}" \
        --version "${pkg_version}" \
        bin lib

for l in ${used_locales} ; do

    po_file="${output_dir}/${l}/LC_MESSAGES/${domain}.po"
    if [[ -f "${po_file}" ]] ; then

        pybabel update --domain "${domain}" \
                --input-file "${pot_file}" \
                --output-dir "${output_dir}" \
                --locale "${l}" \
                --width 99 \
                --ignore-obsolete --previous

    else

        pybabel init --domain "${domain}" \
                --input-file "${pot_file}" \
                --output-dir "${output_dir}" \
                --locale "${l}" \
                --width 99

    fi

    pybabel compile --domain "${domain}" \
            --directory "${output_dir}" \
            --locale "${l}" \
            --statistics --use-fuzzy

done


# vim: ts=4 et
