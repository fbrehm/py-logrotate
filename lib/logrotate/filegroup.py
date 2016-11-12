#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank@brehm-online.com
@license: GPL3
@copyright: © 2010 - 2016 by Frank Brehm, Berlin
@summary: module for a logfile goup object
"""

# Standard modules
import re
import logging
import subprocess
import pprint
import gettext
import copy
import glob

from collections import MutableSequence

# Third party modules
import pytz
import six

# Own modules
from logrotate.common import split_parts, pp
from logrotate.common import logrotate_gettext, logrotate_ngettext
from logrotate.common import to_str_or_bust as to_str

from logrotate.base import BaseObjectError, BaseObject

__version__ = '0.1.1'

_ = logrotate_gettext
__ = logrotate_ngettext

LOG = logging.getLogger(__name__)


# =============================================================================
class LogFileGroupError(BaseObjectError):
    "Base class for exceptions in this module."
    pass


# =============================================================================
class LogFileGroup(BaseObject, MutableSequence):
    """
    Class for encapsulating a group of logfiles, which are rotatet together
    with the same rules
    """

    #-------------------------------------------------------
    def __init__(
        self, config_file=None, first_line_nr=None, simulate=False, patterns=None,
            taboo_pattern=None, appname=None, verbose=0, base_dir=None):
        """Constructor."""

        self._config_file = config_file
        self._first_line_nr = None
        if first_line_nr is not None:
            self._first_line_nr = int(first_line_nr)
        self._simulate = bool(simulate)

        self.patterns = []
        self.taboo_patterns = []

        super(LogFileGroup, self).__init__(
            appname=appname, verbose=verbose, version=__version__, base_dir=base_dir)

        if patterns:
            if isinstance(patterns, (list, tuple)):
                for pattern in patterns:
                    self.patterns.append(to_str(pattern, force=True))
            elif isinstance(to_str(patterns), str):
                self.patterns.append(commands)
            else:
                msg = _("Invalide type %(t)r of parameter %(p)p %(c)r.") % {
                    't': patterns.__class__.__name__, 'p': 'patterns', 'c': patterns}
                raise TypeError(msg)



