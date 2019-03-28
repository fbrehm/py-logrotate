#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank@brehm-online.com
@license: GPL3
@copyright: © 2010 - 2016 by Frank Brehm, Berlin
@summary: module for a logfile goup object
"""
from __future__ import absolute_import

# Standard modules
import re
import logging
import subprocess
import pprint
import gettext
import copy
import glob

from collections import MutableSequence

from enum import Enum, unique

from pathlib import Path

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
from fb_tools.common import pp, human2mbytes, to_str, is_sequence

from fb_tools.obj import FbBaseObject

from .errors import LogrotateObjectError
from .errors import LogrotateCfgFatalError, LogrotateCfgNonFatalError

from .translate import XLATOR

from .common import split_parts

__version__ = '0.6.3'

_ = XLATOR.gettext
ngettext = XLATOR.ngettext

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
class LogFileGroupError(LogrotateObjectError):
    "Base class for exceptions in this module."
    pass


# =============================================================================
@unique
class RotateMethod(Enum):
    create = 1
    copytruncate = 2
    copy = 3

    # -------------------------------------------------------------------------
    def __str__(self):
        return self.name

    # -------------------------------------------------------------------------
    @classmethod
    def default(cls):
        return cls.create

    # -------------------------------------------------------------------------
    @classmethod
    def from_str(cls, value):
        v = str(to_str(value)).strip().lower()
        for method in cls:
            if method.name == v:
                return method
        msg = _("Invalid rotation method {!r} given.").format(value)
        raise ValueError(msg)


# =============================================================================
class LogFileGroup(FbBaseObject, MutableSequence):
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

    msg_pointless = _("Pointless option(s) for directive {d!r} in {lf!r}:{lnr}: {line}")

    unary_directives = {
        'compress': {
            'property': 'compress', 'value': True, 'exclude': ['nocompress']},
        'nocompress': {
            'property': 'compress', 'value': False, 'exclude': ['compress']},
        'copy': {
            'property': 'rotate_method', 'value': 'copy', 'exclude': ['copytruncate', 'create']},
        'copytruncate': {
            'property': 'rotate_method', 'value': 'copytruncate', 'exclude': ['copy', 'create']},
        'ifempty': {
            'property': 'if_empty', 'value': True, 'exclude': ['notifempty']},
        'notifempty': {
            'property': 'if_empty', 'value': False, 'exclude': ['ifempty']},
        'missingok': {
            'property': 'missing_ok', 'value': True, 'exclude': ['nomissingok']},
        'nomissingok': {
            'property': 'missing_ok', 'value': False, 'exclude': ['missingok']},
    }

    # -------------------------------------------------------------------------
    def __init__(
        self, config_file=None, line_nr=None, simulate=False, patterns=None,
            compress=False, compresscmd='internal_gzip', compressext=None,
            compressoptions=None, delaycompress=None, rotate_method=None,
            is_default=False, appname=None, verbose=0, base_dir=None):
        """Constructor."""

        self._config_file = None
        self._line_nr = None
        self._simulate = bool(simulate)

        self._is_default = False
        self._definition_started = False

        self.patterns = []
        self._files =[]

        self._compress = bool(compress)
        self._compresscmd = None
        self._compressext = None
        self._compressoptions = None
        self._delaycompress = None

        self._if_empty = True
        self._missing_ok = False

        self.applied_directives = {}

        self._rotate_method = RotateMethod.default()

        super(LogFileGroup, self).__init__(
            appname=appname, verbose=verbose, version=__version__, base_dir=base_dir)

        self.is_default = is_default
        self.config_file = config_file
        self.line_nr = line_nr

        if patterns:
            self.add_patterns(patterns)

        self.compresscmd = compresscmd
        self.compressext = compressext
        self.compressoptions = compressoptions
        self.delaycompress = delaycompress

        if rotate_method is not None:
            self.rotate_method = rotate_method

    # ------------------------------------------------------------
    @property
    def config_file(self):
        "Filename of the configuration file, where this file group is defined."
        return self._config_file

    @config_file.setter
    def config_file(self, value):
        if value is None:
            self._config_file = None
            return
        self._config_file = Path(value)

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
    def is_default(self):
        "Flag, that this file group is the default file group of the config reader."
        return self._is_default

    @is_default.setter
    def is_default(self, value):
        self._is_default = bool(value)

    # ------------------------------------------------------------
    @property
    def definition_started(self):
        "Flag, that the definition of the file group was started inside the configuration."
        if self.is_default:
            return True
        return self._definition_started

    @definition_started.setter
    def definition_started(self, value):
        self._definition_started = bool(value)

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
    def if_empty(self):
        "Should empty logfiles be rotated?"
        return self._if_empty

    @if_empty.setter
    def if_empty(self, value):
        self._if_empty = bool(value)

    # ------------------------------------------------------------
    @property
    def missing_ok(self):
        "Don't complain, if no files were found for the given file pattern."
        return self._missing_ok

    @missing_ok.setter
    def missing_ok(self, value):
        self._missing_ok = bool(value)

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
        v = str(to_str(value))
        if self.re_empty.search(v):
            self._compresscmd = 'internal_gzip'
            return
        if v.lower().startswith('internal_'):
            if v.lower() not in INTERNAL_COMPRESSORS:
                msg = _("Invalid internal compressor {!r} given.").format(value)
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
        v = str(to_str(value))
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
        if is_sequence(value):
            self._compressoptions = copy.copy(value)
            return
        self._compressoptions = shlex_quote(str(to_str(value)))

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

    # ------------------------------------------------------------
    @property
    def rotate_method(self):
        """The method, which is used for rotating the current logfiles."""
        return self._rotate_method.name

    @rotate_method.setter
    def rotate_method(self, value):
        if isinstance(value, RotateMethod):
            self._rotate_method = value
            return
        if value is None:
            self._rotate_method = RotateMethod.default()
        self._rotate_method = RotateMethod.from_str(value)

    # -------------------------------------------------------------------------
    def as_dict(self, short=True):
        '''
        Transforms the elements of the object into a dict

        @return: structure as dict
        @rtype:  dict
        '''

        res = super(LogFileGroup, self).as_dict(short=short)

        res['config_file'] = self.config_file
        res['line_nr'] = self.line_nr
        res['simulate'] = self.simulate
        res['is_default'] = self.is_default
        res['definition_started'] = self.definition_started
        res['status_file'] = None
        if self.status_file:
            res['status_file'] = self.status_file.as_dict(short=short)

        res['compress'] = self.compress
        res['compresscmd'] = self.compresscmd
        res['compressext'] = self.compressext
        res['compressoptions'] = self.compressoptions
        res['delaycompress'] = self.delaycompress

        res['if_empty'] = self.if_empty
        res['missing_ok'] = self.missing_ok

        res['rotate_method'] = self.rotate_method

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
            v = Path(to_str(value))
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
        fields.append("is_default=%r" % (self.is_default))
        fields.append("line_nr=%r" % (self.line_nr))
        fields.append("patterns=%r" % (copy.copy(self.patterns)))
        fields.append("simulate=%r" % (self.simulate))
        fields.append("rotate_method=%r" % (self.rotate_method))
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
            patterns=self.patterns, rotate_method=self.rotate_method,
            appname=self.appname, verbose=self.verbose, base_dir=self.base_dir,
            is_default=self.is_default,
        )

        new_group.compress = self.compress
        new_group.compresscmd = self.compresscmd
        new_group.compressext = self._compressext
        new_group.compressoptions = copy.copy(self.compressoptions)
        new_group.delaycompress = self.delaycompress
        new_group.definition_started = self.definition_started
        new_group.applied_directives = {}

        new_group.if_empty = self.if_empty
        new_group.missing_ok = self.missing_ok

        for fname in self:
            new_group.append(fname)

        return new_group

    # -------------------------------------------------------------------------
    def spawn_new(self):
        """Creates a new file group as a copy of the current file group.
            If current group is not a default group, a LogFileGroupError is raised.
        """

        if not self.is_default:
            msg = _("Method {} may only be used on a default file group.").format(
                'spawn_new()')
            raise LogFileGroupError(msg)

        if self.verbose > 2:
            LOG.debug(_("Spawning a new file group from a default file group."))

        new_group = copy.copy(self)
        new_group.is_default = False
        new_group.definition_started = False

        return new_group

    # -------------------------------------------------------------------------
    def index(self, value, *args):

        if len(args) > 2:
            msg = _("Call of {what} with a wrong number ({nr}) of arguments.").format(
                what='index()', nr=len(args))
            raise AttributeError(msg)

        if value is None:
            v = None
        else:
            v = Path(to_str(value))

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
            msg = _("File {!r} not found in file list.").format(str(v))
            raise ValueError(msg)
        return idx

    # -------------------------------------------------------------------------
    def __contains__(self, filename):
        try:
            self.index(filename)
        except ValueError:
            return False

        return True

    # -------------------------------------------------------------------------
    def insert(self, i, filename):
        if filename is None:
            v = None
        else:
            v = Path(to_str(filename))
        self._files.insert(i, v)

    # -------------------------------------------------------------------------
    def append(self, filename):
        if filename is None:
            v = None
        else:
            v = Path(to_str(filename))
        self._files.append(v)

    # -------------------------------------------------------------------------
    def clear(self):
        self._files = []

    # -------------------------------------------------------------------------
    def add_patterns(self, patterns):
        "Extending list self.patterns by a new file globbing pattern."

        if is_sequence(patterns):
            for pattern in patterns:
                self.add_pattern(pattern)
        else:
            self.add_pattern(patterns)

    # -------------------------------------------------------------------------
    def add_pattern(self, pattern):

        try:
            path = Path(pattern)
        except TypeError as e:
            msg = _("Could not add file pattern {p!r}: {e}").format(
                p=pattern, e=e)
            raise LogrotateCfgNonFatalError(msg)

        if not path.is_absolute():
            msg = _("A logfile pattern must be an absolute path: {!r}").format(str(path))
            raise LogrotateCfgNonFatalError(msg)

        self.patterns.append(path)

    # -------------------------------------------------------------------------
    @classmethod
    def add_taboo_pattern(cls, pattern, pattern_type='file'):
        """
        Adding a new entry to the list of compiled taboo patterns.
        """

        if not pattern or not isinstance(to_str(pattern), str):
            msg = _("Invalid taboo pattern {!r} given.").format(pattern)
            raise ValueError(msg)

        ptype = pattern_type.strip().lower()
        if ptype not in cls.toboo_pattern_types:
            msg = _("Invalid taboo pattern type {!r} given.").format(pattern_type)
            raise ValueError(msg)

        pat = cls.toboo_pattern_types[ptype] % (pattern)
        re_taboo = None
        try:
            re_taboo = re.compile(pat, re.IGNORECASE)
        except Exception as e:
            msg = _("Got a {c} error on adding taboo pattern {p!r}: {e}.").format(
                c=e.__class__.__name__, p=pattern, e=e)
            return ValueError(msg)

        found = False
        for re_t in cls.taboo_patterns:
            if pat == re_t.pattern:
                LOG.debug(_(
                    "Taboo pattern {!r} already exists in the list of taboo patterns.").format(
                    pat))
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

    # -------------------------------------------------------------------------
    def resolve_patterns(self):

        if self.verbose > 1:
            LOG.debug(_("Resolving globbing pattern in file group."))
        self.clear()

        for pattern in self.patterns:

            files = glob.glob(str(pattern))
            if not files:
                if self.verbose > 2:
                    LOG.debug(_("Did not found a file for pattern {!r}.").format(pattern))
                continue

            for lfile in files:
                path = Path(lfile).resolve()
                if path in self:
                    LOG.error(_("Multiple definition of logfile {f!r} in {cf!r}.").format(
                        f=str(path), c=str(self.config_file)))
                    continue
                self.append(path)

    # -------------------------------------------------------------------------
    def apply_directive(self, line, line_parts, cfg_file, linenr):

        if self.verbose > 2:
            msg = ''
            if self.is_default:
                msg = _("Trying to apply option line {!r} to a default file group.")
            else:
                msg = _("Trying to apply option line {!r} to a file group.")
            LOG.debug(msg.format(line))

        directive = line_parts[0].lower()
        if directive in self.unary_directives:
            return self.apply_unary_directive(line, line_parts, cfg_file, linenr)

        return False

    # -------------------------------------------------------------------------
    def apply_unary_directive(self, line, line_parts, cfg_file, linenr):

        directive = line_parts[0].lower()

        if self.verbose > 3:
            LOG.debug(_("Already applied directives:") + '\n' + pp(self.applied_directives))

        prop = self.unary_directives[directive]['property']
        val = self.unary_directives[directive]['value']
        excludes = [directive]
        if self.unary_directives[directive]['exclude']:
            for excl in self.unary_directives[directive]['exclude']:
                excludes.append(excl)

        if len(line_parts) > 1:
            LOG.error(self.msg_pointless.format(
                d=directive, lf=str(cfg_file), lnr=linenr, line=line))
            return False

        for exclude in excludes:
            if exclude in self.applied_directives:
                args = {
                    'lf': str(cfg_file), 'lnr': linenr, 'd': directive,
                    'ex': exclude, 'of': str(self.applied_directives[exclude][0]),
                    'ol': self.applied_directives[exclude][1], 'line': line}
                LOG.error(_(
                    "Error in {lf!r}:{lnr}: directive {d!r} was already set as {ex!r} in "
                    "{of!r}:{ol}: {line}").format(**args))
                return False
        if self.verbose > 2:
            if self.is_default:
                LOG.debug(_(
                    "Setting default file group property {p!r} to {v!r}.").format(p=prop, v=val))
            else:
                LOG.debug(_(
                    "Setting file group property {p!r} to {v!r}.").format(p=prop, v=val))
        self.applied_directives[directive] = (cfg_file, linenr)
        setattr(self, prop, val)

        return True

# ========================================================================

if __name__ == "__main__":
    pass

# ========================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
