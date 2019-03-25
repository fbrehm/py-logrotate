#!/bin/bash

set -e
set -u

base_dir=$( dirname $0 )
cd ${base_dir}

output_dir="po"
domain='plogrotate'
pot_file="${output_dir}/${domain}.pot"
pkg_version="0.8.0"
po_with=99
my_address="${DEBEMAIL:-frank.brehm@pixelpark.com}"

used_locales="de_DE"

pkg_version=$( cat lib/webhooks/__init__.py | \
                    grep '^[ 	]*__version__' | \
                    sed -e 's/[ 	]*//g' | \
                    awk -F= '{print $2}' | \
                    sed -e "s/^'//" -e "s/'\$//" )

mkdir -pv "${output_dir}"

pybabel extract bin/* lib \
        --output "${pot_file}" \
        -F babel.cfg \
        --width ${po_with} \
        --sort-by-file \
        --msgid-bugs-address="${my_address}" \
        --copyright-holder "Frank Brehm, Berlin" \
        --project "${domain}" \
        --version "${pkg_version}"

sed -i -e "s/FIRST AUTHOR/Frank Brehm/g" -e "s/<EMAIL@ADDRESS>/<${my_address}>/g" "${pot_file}"

for l in ${used_locales} ; do

    po_file="${output_dir}/${l}/LC_MESSAGES/${domain}.po"
    if [[ -f "${po_file}" ]] ; then

        pybabel update --domain "${domain}" \
                --input-file "${pot_file}" \
                --output-dir "${output_dir}" \
                --locale "${l}" \
                --width ${po_with} \
                --ignore-obsolete \
                --update-header-comment \
                --previous

    else

        pybabel init --domain "${domain}" \
                --input-file "${pot_file}" \
                --output-dir "${output_dir}" \
                --locale "${l}" \
                --width ${po_with}

    fi

done


# vim: ts=4 et
