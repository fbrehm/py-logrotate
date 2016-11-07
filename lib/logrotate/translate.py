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

# Standard modules
import os
import sys
import logging
import gettext

# Third party modules
import six

# Own modules
basedir = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..'))
libdir = os.path.join(basedir, 'lib')

if __name__ == "__main__":
    sys.path.insert(0, libdir)

from logrotate.common import to_str_or_bust as to_str

locale_dir = os.path.join(basedir, 'po')
if not os.path.isdir(locale_dir):
    locale_dir = None

DOMAIN = 'plogrotate'
mo_file = gettext.find(DOMAIN, locale_dir, all=True)

log = logging.getLogger(__name__)

translator = gettext.translation(DOMAIN, locale_dir, fallback=True)
"""
The main gettext-translator object, which can be imported
from other modules.
"""

gettext.install(DOMAIN, locale_dir)

# =============================================================================
def logrotate_gettext(message):
    if six.PY3:
        return to_str(translator.gettext(message))
    else:
        return to_str(translator.lgettext(message))


# =============================================================================
def logrotate_ngettext(singular, plural, n):
    if six.PY3:
        return to_str(translator.ngettext(singular, plural, n))
    else:
        return to_str(translator.lngettext(singular, plural, n))

__ = logrotate_ngettext

# =============================================================================

if __name__ == "__main__":

    print(_("Basedir: %r") % (basedir))
    print(_("Locales Dir: %r") % (locale_dir))
    print(_("Domain: %r") % (DOMAIN))
    print(__("Found .mo-file: %r", "Found .mo-files: %r", len(mo_file)) % (mo_file))

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4

