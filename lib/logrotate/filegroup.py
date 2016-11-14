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

__version__ = '0.1.4'

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

    status_file = None

    #-------------------------------------------------------
    def __init__(
        self, config_file=None, line_nr=None, simulate=False, patterns=None,
            appname=None, verbose=0, base_dir=None):
        """Constructor."""

        self._config_file = None
        self._line_nr = None
        self._simulate = bool(simulate)

        self.patterns = []
        sel._files =[]

        super(LogFileGroup, self).__init__(
            appname=appname, verbose=verbose, version=__version__, base_dir=base_dir)

        self.config_file = config_file
        self.line_nr = line_nr

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

    @config_file.setter
    def config_file(self, value):
        self._config_file = to_str(value)

    #------------------------------------------------------------
    @property
    def line_nr(self):
        """
        The number of the beginning line of the definition in the configuration file,
        where this file group is defined.
        """
        return self._line_nr

    @line_nr.setter
    def line_nr(self, value):
        if value is None:
            self._line_nr = None
            return
        self._line_nr = int(value)

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
        res['status_file'] = None
        if self.status_file:
            res['status_file'] = self.status_file.as_dict()

        res['patterns'] = copy.copy(self.patterns)
        res['files'] = copy.copy(self._files)

        return res

    # -------------------------------------------------------------------------
    def __len__(self):
        return len(self._files)

    # -------------------------------------------------------------------------
    def __getitem__(self, key):
        return self._files[key]

    # -------------------------------------------------------------------------
    def __setitem__(self, key, value):

        if value is None:
            v = None
        else:
            v = to_str(value, force=True)
        self._files[key] = v

    # -------------------------------------------------------------------------
    def __delitem__(self, key):

        del self._files[key]

    # -------------------------------------------------------------------------
    def __repr__(self):
        """Typecasting into a string for reproduction."""

        out = "<%s(" % (self.__class__.__name__)

        fields = []
        fields.append("config_file=%r" % (self.config_file))
        fields.append("line_nr=%r" % (self.line_nr))
        fields.append("patterns=%r" % (copy.copy(self.patterns)))
        fields.append("simulate=%r" % (self.simulate))
        fields.append("appname=%r" % (self.appname))
        fields.append("verbose=%r" % (self.verbose))
        fields.append("version=%r" % (self.version))
        fields.append("base_dir=%r" % (self.base_dir))

        out += ", ".join(fields) + ")>"
        return out

    # -------------------------------------------------------------------------
    def index(self, value, *args):

        if len(args) > 2:
            msg = "Call of index() with a wrong number (%d) of arguments." % (len(args))
            raise AttributeError(msg)

        if value is None:
            v = None
        else:
            v = to_str(value, force=True)

        i = 0
        j = None
        if len(args) >= 1:
            i = int(args[0])
        if len(args) >= 2:
            j = int(args[1])
        found = False
        idx = i
        if len(self._files) and i < len(self._files):
            for f in self._files[i:]:
                if f == v:
                    found = True
                    break
                idx += 1
                if j is not None and idx >= j:
                    break

        if not found:
            msg = "File %r not found in file list." % (str(v))
            raise ValueError(msg)
        return idx

    # -------------------------------------------------------------------------
    def __contains__(self, cmd):
        try:
            self.index(cmd)
        except ValueError:
            return False

        return True

    # -------------------------------------------------------------------------
    def insert(self, i, cmd):
        if value is None:
            v = None
        else:
            v = to_str(value, force=True)
        self._files.insert(i, v)

    # -------------------------------------------------------------------------
    def append(self, cmd):
        if value is None:
            v = None
        else:
            v = to_str(value, force=True)
        self._files.append(v)

    # -------------------------------------------------------------------------
    def add_pattern(self, pattern):
        "Extending list self.patterns by a new file globbing pattern."

        if not pattern or not isinstance(to_str(pattern), str):
            msg = "Invalid file globbing pattern %r." % (pattern)
            raise ValueError(msg)

        pat = to_str(pattern)
        if pat in self.patterns:
            LOG.warn(
                _("Pattern %r is already a member of the file globbing pattern list."),
                pattern)
            return
        self.patterns.append(pat)


#========================================================================

if __name__ == "__main__":
    pass

#========================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
