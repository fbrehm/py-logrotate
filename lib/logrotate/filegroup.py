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

HAS_LZMA = False
try:
    import lzma
    HAS_LZMA = True
except ImportError:
    pass

# Third party modules
import pytz
import six

from six.moves import shlex_quote

# Own modules
from logrotate.common import split_parts, pp
from logrotate.common import logrotate_gettext, logrotate_ngettext
from logrotate.common import to_str_or_bust as to_str

from logrotate.base import BaseObjectError, BaseObject

__version__ = '0.2.4'

_ = logrotate_gettext
__ = logrotate_ngettext

LOG = logging.getLogger(__name__)

INTERNAL_COMPRESSORS = {
    'internal_zip': '.zip',
    'internal_gzip': '.gz',
    'internal_bzip2': '.bzip2',
}

if HAS_LZMA:
    INTERNAL_COMPRESSORS['internal_xz'] = '.xz'
    INTERNAL_COMPRESSORS['internal_lzma'] = '.lzma'


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

    toboo_pattern_types = {
        'ext': r'%s$',
        'suffix': r'%s$',
        'file': r'^%s$',
        'prefix': r'^%s',
    }
    taboo_patterns = []

    re_empty = re.compile(r'^\s*$')

    # -------------------------------------------------------
    def __init__(
        self, config_file=None, line_nr=None, simulate=False, patterns=None,
            compress=False, compresscmd='internal_gzip', compressext=None,
            compressoptions=None, delaycompress=None,
            appname=None, verbose=0, base_dir=None):
        """Constructor."""

        self._config_file = None
        self._line_nr = None
        self._simulate = bool(simulate)

        self.patterns = []
        self._files =[]

        self._compress = bool(compress)
        self._compresscmd = None
        self._compressext = None
        self._compressoptions = None
        self._delaycompress = None

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

        self.compresscmd = compresscmd
        self.compressext = compressext
        self.compressoptions = compressoptions
        self.delaycompress = delaycompress

    # ------------------------------------------------------------
    @property
    def config_file(self):
        "Filename of the configuration file, where this file group is defined."
        return self._config_file

    @config_file.setter
    def config_file(self, value):
        self._config_file = to_str(value)

    # ------------------------------------------------------------
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

    # ------------------------------------------------------------
    @property
    def simulate(self):
        "Number of logfiles referencing to this script as a postrotate script."
        return self._simulate

    @simulate.setter
    def simulate(self, value):
        self._simulate = bool(value)

    # ------------------------------------------------------------
    @property
    def compress(self):
        "Should the rotated logfiles compressed after rotation?"
        return self._compress

    @compress.setter
    def compress(self, value):
        self._compress = bool(value)

    # ------------------------------------------------------------
    @property
    def compresscmd(self):
        "The used command to compress rotated files."
        return self._compresscmd

    @compresscmd.setter
    def compresscmd(self, value):
        if value is None:
            self._compresscmd = 'internal_gzip'
            return
        v = to_str(value, force=True)
        if self.re_empty.search(v):
            self._compresscmd = 'internal_gzip'
            return
        if v.lower().startswith('internal_'):
            if v.lower() not in INTERNAL_COMPRESSORS:
                msg = _("Invalid internal compressor %r given.") % (value)
                raise ValueError(msg)
            self._compresscmd = v.lower()
        else:
            self._compresscmd = value

    # ------------------------------------------------------------
    @property
    def compressext(self):
        """
        The file extension, which should get rotated files.

        For internal compressors they are handled automatically. Otherwise
        if not given, '.compressed' is used.
        """
        if self._compressext is None:
            if self.compresscmd.startswith('internal_'):
                return INTERNAL_COMPRESSORS[self.compresscmd]
            else:
                return '.compressed'
        return self._compressext

    @compressext.setter
    def compressext(self, value):
        if value is None:
            self._compressext = None
            return
        v = to_str(value, force=True)
        if self.re_empty.search(v):
            self._compressext = None
        else:
            self._compressext = v

    # ------------------------------------------------------------
    @property
    def compressoptions(self):
        "Optional arguments options given to external compress commands."
        return self._compressoptions

    @compressoptions.setter
    def compressoptions(self, value):
        if value is None:
            self._compressoptions = None
            return
        if isinstance(value, (list, tuple)):
            self._compressoptions = copy.copy(value)
            return
        self._compressoptions = shlex_quote(to_str(value, force=True))

    # ------------------------------------------------------------
    @property
    def delaycompress(self):
        """
        Defines, how many rotated files should not compressed after
        rotation of a logfile.
        """
        return self._delaycompress

    @delaycompress.setter
    def delaycompress(self, value):
        if value is None:
            self._delaycompress = None
            return
        self._delaycompress = int(value)

    # -------------------------------------------------------------------------
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

        res['compress'] = self.compress
        res['compresscmd'] = self.compresscmd
        res['compressext'] = self.compressext
        res['compressoptions'] = self.compressoptions
        res['delaycompress'] = self.delaycompress

        res['patterns'] = copy.copy(self.patterns)
        res['files'] = copy.copy(self._files)

        res['taboo_patterns'] = []
        for re_taboo in self.taboo_patterns:
            res['taboo_patterns'].append(re_taboo.pattern)

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
    def __copy__(self):
        """Wrapper method for copy.copy() to create a complete copy
        of this logfile group."""

        new_group = LogFileGroup(
            config_file=self.config_file, line_nr=self.line_nr, simulate=self.simulate,
            patterns=self.patterns,
            appname=self.appname, verbose=self.verbose, base_dir=self.base_dir,
        )

        new_group.compress = self.compress
        new_group.compresscmd = self.compresscmd
        new_group.compressext = self._compressext
        new_group.compressoptions = copy.copy(self.compressoptions)
        new_group.delaycompress = self.delaycompress

        for fname in self:
            new_group.append(fname)

        return new_group

    # -------------------------------------------------------------------------
    def index(self, value, *args):

        if len(args) > 2:
            msg = _("Call of index() with a wrong number (%d) of arguments.") % (len(args))
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
            msg = _("File %r not found in file list.") % (str(v))
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
            msg = _("Invalid file globbing pattern %r.") % (pattern)
            raise ValueError(msg)

        pat = to_str(pattern)
        if pat in self.patterns:
            LOG.warn(
                _("Pattern %r is already a member of the file globbing pattern list."),
                pattern)
            return
        self.patterns.append(pat)

    # -------------------------------------------------------------------------
    @classmethod
    def add_taboo_pattern(cls, pattern, pattern_type='file'):
        """
        Adding a new entry to the list of compiled taboo patterns.
        """

        if not pattern or not isinstance(to_str(pattern), str):
            msg = _("Invalid taboo pattern %r given.") % (pattern)
            raise ValueError(msg)

        ptype = pattern_type.strip().lower()
        if ptype not in cls.toboo_pattern_types:
            msg = _("Invalid taboo pattern type %r given.") % (pattern_type)
            raise ValueError(msg)

        pat = cls.toboo_pattern_types[ptype] % (pattern)
        re_taboo = None
        try:
            re_taboo = re.compile(pat, re.IGNORECASE)
        except Exception as e:
            msg = _("Got a %(c)s error on adding taboo pattern %(p)r: %(e)s.") % {
                'c': e.__class__.__name__, 'p':  pattern, 'e': e}
            return ValueError(msg)

        found = False
        for re_t in cls.taboo_patterns:
            if pat == re_t.pattern:
                LOG.debug(_(
                    "Taboo pattern %r already exists in the list "
                    "of taboo patterns."), pat)
                found = True
                break

        if not found:
            cls.taboo_patterns.append(re_taboo)

    # -------------------------------------------------------------------------
    @classmethod
    def init_taboo_patterns(cls):
        "Initialize the list of taboo patterns with some default values."

        LOG.debug(_("Initializing the list of taboo patterns with some default values."))

        cls.taboo_patterns = []

        # Standard taboo extensions (suffixes)
        cls.add_taboo_pattern(r'\.rpmnew', 'ext');
        cls.add_taboo_pattern(r'\.rpmorig', 'ext');
        cls.add_taboo_pattern(r'\.rpmsave', 'ext');
        cls.add_taboo_pattern(r',v', 'ext');
        cls.add_taboo_pattern(r'\.swp', 'ext');
        cls.add_taboo_pattern(r'~', 'ext');
        cls.add_taboo_pattern(r'\.bak', 'ext');
        cls.add_taboo_pattern(r'\.old', 'ext');
        cls.add_taboo_pattern(r'\.rej', 'ext');
        cls.add_taboo_pattern(r'\.disabled', 'ext');
        cls.add_taboo_pattern(r'\.dpkg-old', 'ext');
        cls.add_taboo_pattern(r'\.dpkg-dist', 'ext');
        cls.add_taboo_pattern(r'\.dpkg-new', 'ext');
        cls.add_taboo_pattern(r'\.cfsaved', 'ext');
        cls.add_taboo_pattern(r'\.ucf-old', 'ext');
        cls.add_taboo_pattern(r'\.ucf-dist', 'ext');
        cls.add_taboo_pattern(r'\.ucf-new', 'ext');
        cls.add_taboo_pattern(r'\.rhn-cfg-tmp-*', 'ext');

        # Standard taboo prefix
        cls.add_taboo_pattern(r'\.', 'prefix');

        # Standard taboo files
        cls.add_taboo_pattern(r'CVS', 'file');
        cls.add_taboo_pattern(r'RCS', 'file');



# ========================================================================

if __name__ == "__main__":
    pass

# ========================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
