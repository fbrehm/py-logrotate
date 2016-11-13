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

__version__ = '0.1.2'

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
        self, config_file=None, line_nr=None, simulate=False, patterns=None,
            appname=None, verbose=0, base_dir=None):
        """Constructor."""

        self._config_file = config_file
        self._line_nr = None
        if line_nr is not None:
            self._line_nr = int(line_nr)
        self._simulate = bool(simulate)

        self.patterns = []
        sel._files =[]

        super(LogFileGroup, self).__init__(
            appname=appname, verbose=verbose, version=__version__, base_dir=base_dir)

        if patterns:
            if isinstance(patterns, (list, tuple)):
                for pattern in patterns:
                    self.patterns.append(to_str(pattern, force=True))
            elif isinstance(to_str(patterns), str):
                self.patterns.append(to_str(commands))
            else:
                msg = _("Invalide type %(t)r of parameter %(p)p %(c)r.") % {
                    't': patterns.__class__.__name__, 'p': 'patterns', 'c': patterns}
                raise TypeError(msg)

    #------------------------------------------------------------
    @property
    def config_file(self):
        "Filename of the configuration file, where this file group is defined."
        return self._config_file

    #------------------------------------------------------------
    @property
    def line_nr(self):
        """
        The number of the beginning line of the definition in the configuration file,
        where this file group is defined.
        """
        return self._line_nr

    #------------------------------------------------------------
    @property
    def simulate(self):
        "Number of logfiles referencing to this script as a postrotate script."
        return self._simulate

    @simulate.setter
    def simulate(self, value):
        self._simulate = bool(value)

    #-------------------------------------------------------
    def as_dict(self):
        '''
        Transforms the elements of the object into a dict

        @return: structure as dict
        @rtype:  dict
        '''

        res = super(LogFileGroup, self).as_dict()

        res['config_file'] = self.config_file
        res['line_nr'] = self.line_nr
        res['simulate'] = self.simulate

        res['files'] = copy.copy(self._files)

        return res



#========================================================================

if __name__ == "__main__":
    pass

#========================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
