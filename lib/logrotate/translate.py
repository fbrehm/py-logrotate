#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank@brehm-online.com
@license: GPL3
@copyright: © 2010 - 2016 by Frank Brehm, Berlin
@summary: The module for i18n.
          It provides translation object, usable from all other
          modules in this package.
"""
from __future__ import absolute_import, print_function

# Standard modules
import os
import sys
import logging
import gettext

from pathlib import Path

from distutils.version import LooseVersion

# Third party modules
import six

import babel
from babel.support import Translations

# Own modules
DOMAIN = 'plogrotate'

LOG = logging.getLogger(__name__)

__version__ = '1.0.1'

__me__ = Path(__file__).resolve()
__module_dir__ = __me__.parent
__lib_dir__ = __module_dir__.parent
__base_dir__ = __lib_dir__.parent
LOCALE_DIR = __base_dir__.joinpath('po')
if not LOCALE_DIR.is_dir():
    LOCALE_DIR = __module_dir__.joinpath('po')
    if not LOCALE_DIR.is_dir():
        LOCALE_DIR = None

DEFAULT_LOCALE_DEF = 'en_US'
DEFAULT_LOCALE = babel.core.default_locale()
if not DEFAULT_LOCALE:
    DEFAULT_LOCALE = DEFAULT_LOCALE_DEF

__mo_file__ = gettext.find(DOMAIN, str(LOCALE_DIR))
if __mo_file__:
    try:
        with open(__mo_file__, 'rb') as F:
            XLATOR = Translations(F, DOMAIN)
    except IOError:
        XLATOR = gettext.NullTranslations()
else:
    XLATOR = gettext.NullTranslations()

CUR_BABEL_VERSION = LooseVersion(babel.__version__)
NEWER_BABEL_VERSION = LooseVersion('2.6.0')

SUPPORTED_LANGS = (
    'de_DE',
    'en_US'
)

_ = XLATOR.gettext

# =============================================================================

if __name__ == "__main__":

    print(_("Module directory: {!r}").format(__module_dir__))
    print(_("Base directory: {!r}").format(__base_dir__))
    print(_("Locale directory: {!r}").format(LOCALE_DIR))
    print(_("Locale domain: {!r}").format(DOMAIN))
    print(_("Found .mo-file: {!r}").format(__mo_file__))


# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
