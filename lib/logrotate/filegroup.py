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
import copy
import glob
import pwd
import grp
import datetime

from collections import MutableSequence

from enum import Enum, unique

from pathlib import Path

HAS_LZMA = False
try:
    import lzma                                             # noqa
    HAS_LZMA = True
except ImportError:
    pass

# Third party modules
from six.moves import shlex_quote

from babel.dates import format_timedelta

# Own modules
from fb_tools.common import pp, to_str, is_sequence, bytes2human

from fb_tools.obj import FbBaseObject

from .errors import LogrotateObjectError
from .errors import LogrotateCfgNonFatalError

from .translate import XLATOR, format_list

from .common import human2bytes, period2days

from .status import StatusFileEntry

__version__ = '0.9.4'

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
    renamecopy = 4

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
@unique
class RotationInterval(Enum):
    year = 1
    month = 2
    week = 3
    day = 4
    hour = 5

    # -------------------------------------------------------------------------
    def __str__(self):
        return self.name

    # -------------------------------------------------------------------------
    @classmethod
    def default(cls):
        return cls.week

    # -------------------------------------------------------------------------
    @classmethod
    def from_str(cls, value):
        v = str(to_str(value)).strip().lower()
        for method in cls:
            if method.name == v:
                return method
        msg = _("Invalid rotation interval {!r} given.").format(value)
        raise ValueError(msg)


# =============================================================================
class LogFileGroup(FbBaseObject, MutableSequence):
    """
    Class for encapsulating a group of logfiles, which are rotatet together
    with the same rules
    """

    status_file = None

    re_empty = re.compile(r'^\s*$')

    ext_compress_extensions = {
        re.compile(r'(^|/)zip$', re.IGNORECASE): '.zip',
        re.compile(r'(^|/)gzip$', re.IGNORECASE): '.gz',
        re.compile(r'(^|/)bzip2$', re.IGNORECASE): '.bz2',
        re.compile(r'(^|/)xz$', re.IGNORECASE): '.xz',
        re.compile(r'(^|/)lzma$', re.IGNORECASE): '.lzma',
    }

    re_wrong_pc_placeholder = re.compile(r'%[^%YmdHMSVs]')
    valid_pc_placeholders = ('%%', '%Y', '%m', '%d', '%H', '%M', '%S', '%V', '%s')

    msg_pointless = _("Pointless option(s) for directive {d!r} in {lf!r}:{lnr}: {line}")

    default_dateext_daily = '-%Y-%m-%d'
    default_dateext_hourly = '-%Y-%m-%d-%H'

    unary_directives = {
        'compress': {
            'property': 'compress', 'value': True},
        'copy': {
            'property': 'rotate_method', 'value': 'copy'},
        'copytruncate': {
            'property': 'rotate_method', 'value': 'copytruncate'},
        'daily': {
            'property': 'rotation_interval', 'value': RotationInterval.day},
        'dateext': {
            'property': 'dateext', 'value': True},
        'datehourago': {
            'property': 'datehourago', 'value': True},
        'dateyesterday': {
            'property': 'dateyesterday', 'value': True},
        'hourly': {
            'property': 'rotation_interval', 'value': RotationInterval.hour},
        'ifempty': {
            'property': 'if_empty', 'value': True},
        'missingok': {
            'property': 'missing_ok', 'value': True},
        'monthly': {
            'property': 'rotation_interval', 'value': RotationInterval.month},
        'nocompress': {
            'property': 'compress', 'value': False},
        'nocopy': {
            'property': 'rotate_method', 'value': 'create'},
        'nocreate': {
            'property': 'rotate_method', 'value': 'copy'},
        'nocreateolddir': {
            'property': 'createolddir', 'value': False},
        'nodateext': {
            'property': 'dateext', 'value': False},
        'nodelaycompress': {
            'property': 'delaycompress', 'value': None},
        'nomissingok': {
            'property': 'missing_ok', 'value': False},
        'noolddir': {
            'property': 'olddir', 'value': None},
        'nosharedscripts': {
            'property': 'sharedscripts', 'value': False},
        'noshred': {
            'property': 'shred', 'value': False},
        'notifempty': {
            'property': 'if_empty', 'value': False},
        'renamecopy': {
            'property': 'rotate_method', 'value': 'renamecopy'},
        'sharedscripts': {
            'property': 'sharedscripts', 'value': True},
        'shred': {
            'property': 'shred', 'value': True},
        'weekly': {
            'property': 'rotation_interval', 'value': RotationInterval.week},
        'yearly': {
            'property': 'rotation_interval', 'value': RotationInterval.year},
    }

    integer_directives = {
        'delaycompress': {
            'property': 'delaycompress', 'default': 1},
        'maxage': {
            'property': 'maxage', 'default': None},
        'maxsize': {
            'property': 'maxsize', 'default': None},
        'minage': {
            'property': 'minage', 'default': None},
        'minsize': {
            'property': 'minsize', 'default': None},
        'rotate': {
            'property': 'rotate', 'default': None},
        'shredcycles': {
            'property': 'shredcycles', 'default': None},
        'size': {
            'property': 'size', 'default': None},
        'start': {
            'property': 'start', 'default': None},
    }

    string_directives = {
        'addextension': {'min': 1, 'max': 1},
        'compresscmd': {'min': 1, 'max': 1},
        'compressext': {'min': 1, 'max': 1},
        'compressoptions': {'min': 0, 'max': None},
        'create': {'min': 0, 'max': 3},
        'createolddir': {'min': 3, 'max': 3},
        'dateformat': {'min': 1, 'max': 1},
        'extension': {'min': 1, 'max': 1},
        'olddir': {'min': 1, 'max': 1},
    }

    unsupported_directives = (
        'error', 'mail', 'mailfirst', 'maillast', 'nomail', 'su', 'uncompresscmd')

    min_last_rotation_date = {}

    # -------------------------------------------------------------------------
    def __new__(cls, *args, **kwargs):

        cls.init_last_rotation_date()

        return super().__new__(cls)

    # -------------------------------------------------------------------------
    @classmethod
    def init_last_rotation_date(cls):

        if cls.min_last_rotation_date.keys():
            return

        tz = StatusFileEntry.local_timezone
        dt_now = datetime.datetime.now(tz)

        dt_year = datetime.datetime(
            dt_now.year - 1, dt_now.month, dt_now.day, hour=dt_now.hour,
            minute=dt_now.minute, second=dt_now.second, tzinfo=tz)
        cls.min_last_rotation_date['year'] = dt_year

        if dt_now.month <= 1:
            dt_month = dt_year = datetime.datetime(
                dt_now.year - 1, 12, dt_now.day, hour=dt_now.hour,
                minute=dt_now.minute, second=dt_now.second, tzinfo=tz)
        else:
            dt_month = dt_year = datetime.datetime(
                dt_now.year, dt_now.month - 1, dt_now.day, hour=dt_now.hour,
                minute=dt_now.minute, second=dt_now.second, tzinfo=tz)
        cls.min_last_rotation_date['month'] = dt_month

        cls.min_last_rotation_date['week'] = dt_now - datetime.timedelta(weeks=1)
        cls.min_last_rotation_date['day'] = dt_now - datetime.timedelta(days=1)
        cls.min_last_rotation_date['hour'] = dt_now - datetime.timedelta(hours=1)

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
        self._files = []

        self.last_rotation = {}

        self._compress = bool(compress)
        self._compresscmd = None
        self._compressext = None
        self._compressoptions = None
        self._delaycompress = None

        self._if_empty = True
        self._missing_ok = False

        self._sharedscripts = False
        self.scripts = {}

        self._start = 0
        self._dateext = False
        self._dateformat = None
        self._dateyesterday = False
        self._datehourago = False
        self._addextension = None
        self._extension = None

        self.applied_directives = {}

        self._rotate = 0
        self._rotate_method = RotateMethod.default()
        self._rotation_interval = RotationInterval.default()
        self._minage = None
        self._maxage = None
        self._minsize = None
        self._maxsize = None
        self._size = None
        self._shred = False
        self._shredcycles = None

        self._create_mode = None
        self._create_owner = None
        self._create_group = None

        self._olddir = None
        self._createolddir = False
        self._olddir_mode = None
        self._olddir_owner = None
        self._olddir_group = None

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
    def sharedscripts(self):
        "Don't complain, if no files were found for the given file pattern."
        return self._sharedscripts

    @sharedscripts.setter
    def sharedscripts(self, value):
        self._sharedscripts = bool(value)

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
                for re_ext in self.ext_compress_extensions:
                    if re_ext.search(self.compresscmd):
                        return self.ext_compress_extensions[re_ext]
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
        v = int(value)
        if v < 0:
            msg = _("A negative value for {!r} is not allowed.").format('delaycompress')
            raise ValueError(msg)
        self._delaycompress = v

    # ------------------------------------------------------------
    @property
    def rotate(self):
        """
        Defines, how many rotated files should be held before they are removed.
        """
        return self._rotate

    @rotate.setter
    def rotate(self, value):
        v = int(value)
        if v < 0:
            msg = _("A negative number for {!r} is not allowed.").format('rotate')
            raise ValueError(msg)
        self._rotate = v

    # ------------------------------------------------------------
    @property
    def maxage(self):
        """
        Remove rotated logs older than this number of days.
        """
        return self._maxage

    @maxage.setter
    def maxage(self, value):
        if value is None:
            self._maxage = None
            return
        v = period2days(value)
        if v < 0:
            msg = _("A negative number for {!r} is not allowed.").format('maxage')
            raise ValueError(msg)
        self._maxage = v

    # ------------------------------------------------------------
    @property
    def minage(self):
        """
        Do not rotate logs which are less than this number of days old.
        """
        return self._minage

    @minage.setter
    def minage(self, value):
        if value is None:
            self._minage = None
            return
        v = period2days(value)
        if v < 0:
            msg = _("A negative number for {!r} is not allowed.").format('minage')
            raise ValueError(msg)
        self._minage = v

    # ------------------------------------------------------------
    @property
    def maxsize(self):
        """
        Log files are rotated when they grow bigger than size bytes even
        before the additionally specified time interval.
        """
        return self._maxsize

    @maxsize.setter
    def maxsize(self, value):
        if value is None:
            self._maxsize = None
            return
        v = human2bytes(value)
        if v < 0:
            msg = _("A negative number for {!r} is not allowed.").format('maxsize')
            raise ValueError(msg)
        self._maxsize = v

    # ------------------------------------------------------------
    @property
    def minsize(self):
        """
        Log files are rotated when they grow bigger than size bytes, but not before
        the additionally specified time interval.
        """
        return self._minsize

    @minsize.setter
    def minsize(self, value):
        if value is None:
            self._minsize = None
            return
        v = human2bytes(value)
        if v < 0:
            msg = _("A negative number for {!r} is not allowed.").format('minsize')
            raise ValueError(msg)
        self._minsize = v

    # ------------------------------------------------------------
    @property
    def size(self):
        """
        Log files are rotated if they grow bigger than size bytes independent
        of the specified time interval.
        """
        return self._size

    @size.setter
    def size(self, value):
        if value is None:
            self._size = None
            return
        v = human2bytes(value)
        if v < 0:
            msg = _("A negative number for {!r} is not allowed.").format('size')
            raise ValueError(msg)
        self._size = v

    # ------------------------------------------------------------
    @property
    def shred(self):
        "Delete log files using shred -u instead of unlink()."
        return self._shred

    @shred.setter
    def shred(self, value):
        self._shred = bool(value)

    # ------------------------------------------------------------
    @property
    def shredcycles(self):
        """
        Defines, how many rotated files should be held before they are removed.
        """
        return self._shredcycles

    @shredcycles.setter
    def shredcycles(self, value):
        if value is None:
            self._shredcycles = None
            return
        v = int(value)
        if v < 0:
            msg = _("A negative number for {!r} is not allowed.").format('shredcycles')
            raise ValueError(msg)
        self._shredcycles = v

    # ------------------------------------------------------------
    @property
    def start(self):
        """
        The number to use as the base for rotation, if no date extension is used.
        """
        return self._start

    @start.setter
    def start(self, value):
        v = int(value)
        if v < 0:
            msg = _("A negative number for {!r} is not allowed.").format('start')
            raise ValueError(msg)
        self._start = v

    # ------------------------------------------------------------
    @property
    def dateext(self):
        """Archive old versions of log files adding a date extension
            instead of simply adding a number."""
        return self._dateext

    @dateext.setter
    def dateext(self, value):
        self._dateext = bool(value)

    # ------------------------------------------------------------
    @property
    def dateformat(self):
        """The extension for dateext using the notation similar to strftime(3) function."""
        if self._dateformat is None:
            if self.dateext:
                if self.rotation_interval == 'hour':
                    return self.default_dateext_hourly
                else:
                    return self.default_dateext_daily
            return None
        return self._dateformat

    @dateformat.setter
    def dateformat(self, value):
        if value is None:
            self._dateformat = None
            return
        v = str(value).strip()
        if self.re_wrong_pc_placeholder.search(v):
            msg = _("Found wrong {f} specifier, the only allowed specifiers are {li}.").format(
                f='strftime()', li=format_list(self.valid_pc_placeholders))
            raise ValueError(msg)
        self._dateformat = v

    # ------------------------------------------------------------
    @property
    def dateyesterday(self):
        """Use yesterday's instead of today's date to create the dateext extension."""
        return self._dateyesterday

    @dateyesterday.setter
    def dateyesterday(self, value):
        self._dateyesterday = bool(value)

    # ------------------------------------------------------------
    @property
    def datehourago(self):
        """Use hour ago instead of current date to create the dateext extension."""
        return self._datehourago

    @datehourago.setter
    def datehourago(self, value):
        self._datehourago = bool(value)

    # ------------------------------------------------------------
    @property
    def addextension(self):
        "Log files will get the given extension as their filal extension after rotation."
        return self._addextension

    @addextension.setter
    def addextension(self, value):
        if value is None:
            self._addextension = None
            return
        v = str(value).strip()
        if v == '':
            self._addextension = None
            return
        self._addextension = v

    # ------------------------------------------------------------
    @property
    def extension(self):
        "Log files can keep given extension after rotation."
        return self._extension

    @extension.setter
    def extension(self, value):
        if value is None:
            self._extension = None
            return
        v = str(value).strip()
        if v == '':
            self._extension = None
            return
        self._extension = v

    # ------------------------------------------------------------
    @property
    def rotate_method(self):
        """The method, which is used for rotating the current logfiles."""
        return self._rotate_method.name

    @rotate_method.setter
    def rotate_method(self, value):
        if isinstance(value, RotateMethod):
            self._rotate_method = value
        elif value is None:
            self._rotate_method = RotateMethod.default()
        else:
            self._rotate_method = RotateMethod.from_str(value)
        if self._rotate_method != RotateMethod.create:
            self.create_mode = None
            self.create_owner = None
            self.create_group = None

    # ------------------------------------------------------------
    @property
    def create_mode(self):
        """The file mode of the newly created logfile (if directive 'create' was given).
            If None, the file mode of the rotated file will be used."""
        return self._create_mode

    @create_mode.setter
    def create_mode(self, value):
        if value is None:
            self._create_mode = None
            return
        if isinstance(value, int):
            self._create_mode = value
        else:
            v = int(value, 8)
            self._create_mode = v

    # ------------------------------------------------------------
    @property
    def create_owner(self):
        """The UID of the owner of the newly created logfile (if directive 'create' was given).
            If None, the file owner of the rotated file will be used."""
        return self._create_owner

    @property
    def create_owner_name(self):
        """The name of the owner of the newly created logfile (if directive 'create' was given).
            If None, the file owner of the rotated file will be used."""
        if self._create_owner is None:
            return None
        try:
            owner = pwd.getpwuid(self._create_owner).pw_name
            return owner
        except KeyError:
            pass
        return self._create_owner

    @create_owner.setter
    def create_owner(self, value):
        if value is None:
            self._create_owner = None
            return
        try:
            v = int(value)
            self._create_owner = v
            return
        except ValueError:
            pass
        v = pwd.getpwnam(value).pw_uid
        self._create_owner = v

    # ------------------------------------------------------------
    @property
    def create_group(self):
        """The GID of the owning group of the newly created logfile
            (if directive 'create' was given).
            If None, the file owning of the rotated file will be used."""
        return self._create_group

    @property
    def create_group_name(self):
        """The name of the owning of the newly created logfile
            (if directive 'create' was given).
            If None, the file owning of the rotated file will be used."""
        if self._create_group is None:
            return None
        try:
            group = grp.getgrgid(self._create_group).gr_name
            return group
        except KeyError:
            pass
        return self._create_group

    @create_group.setter
    def create_group(self, value):
        if value is None:
            self._create_group = None
            return
        try:
            v = int(value)
            self._create_group = v
            return
        except ValueError:
            pass
        v = grp.getgrnam(value).gr_gid
        self._create_group = v

    # ------------------------------------------------------------
    @property
    def rotation_interval(self):
        """The method, which is used for rotating the current logfiles."""
        return self._rotation_interval.name

    @rotation_interval.setter
    def rotation_interval(self, value):
        if isinstance(value, RotationInterval):
            self._rotation_interval = value
            return
        if value is None:
            self._rotation_interval = RotationInterval.default()
        self._rotation_interval = RotationInterval.from_str(value)

    # ------------------------------------------------------------
    @property
    def olddir(self):
        """Directory, where rotated log are moved after rotation."""
        return self._olddir

    @olddir.setter
    def olddir(self, value):
        if value is None:
            self._olddir = None
            self._createolddir = False
            self._olddir_mode = None
            self._olddir_owner = None
            self._olddir_group = None
            return
        path = Path(value)
        if self.verbose > 2:
            LOG.debug(_("New {what} path: {p!r}.").format(what='olddir', p=str(path)))
        if self.re_wrong_pc_placeholder.search(str(path)):
            msg = _("Found wrong {f} specifier, the only allowed specifiers are {li}.").format(
                f='strftime()', li=format_list(self.valid_pc_placeholders))
            raise ValueError(msg)
        self._olddir = Path(value)

    # ------------------------------------------------------------
    @property
    def createolddir(self):
        "Should a not existing olddir be created?"
        return self._createolddir

    @createolddir.setter
    def createolddir(self, value):
        self._createolddir = bool(value)
        if not self._createolddir:
            self._olddir_mode = None
            self._olddir_owner = None
            self._olddir_group = None

    # ------------------------------------------------------------
    @property
    def olddir_mode(self):
        """
        The directory mode of the newly created olddir (if directive 'createolddir' was given).
        """
        return self._olddir_mode

    @olddir_mode.setter
    def olddir_mode(self, value):
        if value is None:
            self._olddir_mode = None
            return
        if isinstance(value, int):
            self._olddir_mode = value
        else:
            v = int(value, 8)
            self._olddir_mode = v

    # ------------------------------------------------------------
    @property
    def olddir_owner(self):
        """
        The UID of the owner of the newly created olddir (if directive 'createolddir' was given).
        """
        return self._olddir_owner

    @property
    def olddir_owner_name(self):
        """
        The name of the owner of the newly created olddir (if directive 'createolddir' was given).
        """
        if self._olddir_owner is None:
            return None
        try:
            owner = pwd.getpwuid(self._olddir_owner).pw_name
            return owner
        except KeyError:
            pass
        return self._olddir_owner

    @olddir_owner.setter
    def olddir_owner(self, value):
        if value is None:
            self._olddir_owner = None
            return
        try:
            v = int(value)
            self._olddir_owner = v
            return
        except ValueError:
            pass
        v = pwd.getpwnam(value).pw_uid
        self._olddir_owner = v

    # ------------------------------------------------------------
    @property
    def olddir_group(self):
        """The GID of the owning group of the newly created olddir
            (if directive 'createolddir' was given)."""
        return self._olddir_group

    @property
    def olddir_group_name(self):
        """The name of the owning of the newly created olddir
            (if directive 'createolddir' was given)."""
        if self._olddir_group is None:
            return None
        try:
            group = grp.getgrgid(self._olddir_group).gr_name
            return group
        except KeyError:
            pass
        return self._olddir_group

    @olddir_group.setter
    def olddir_group(self, value):
        if value is None:
            self._olddir_group = None
            return
        try:
            v = int(value)
            self._olddir_group = v
            return
        except ValueError:
            pass
        v = grp.getgrnam(value).gr_gid
        self._olddir_group = v

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
        res['sharedscripts'] = self.sharedscripts

        res['rotate'] = self.rotate
        res['start'] = self.start
        res['dateext'] = self.dateext
        res['dateformat'] = self.dateformat
        res['dateyesterday'] = self.dateyesterday
        res['datehourago'] = self.datehourago
        res['addextension'] = self.addextension
        res['extension'] = self.extension
        res['maxage'] = self.maxage
        res['minage'] = self.minage
        res['maxsize'] = self.maxsize
        res['minsize'] = self.minsize
        res['size'] = self.size

        res['rotate_method'] = self.rotate_method
        res['rotation_interval'] = self.rotation_interval

        res['create_mode'] = None
        if self.create_mode is not None:
            res['create_mode'] = '{:04o}'.format(self.create_mode)
        res['create_owner'] = self.create_owner
        res['create_owner_name'] = self.create_owner_name
        res['create_group'] = self.create_group
        res['create_group_name'] = self.create_group_name
        res['shred'] = self.shred
        res['shredcycles'] = self.shredcycles

        res['olddir'] = self.olddir
        res['createolddir'] = self.createolddir
        res['olddir_mode'] = None
        if self.olddir_mode is not None:
            res['olddir_mode'] = '{:04o}'.format(self.olddir_mode)
        res['olddir_owner'] = self.olddir_owner
        res['olddir_owner_name'] = self.olddir_owner_name
        res['olddir_group'] = self.olddir_group
        res['olddir_group_name'] = self.olddir_group_name

        res['patterns'] = copy.copy(self.patterns)
        res['files'] = copy.copy(self._files)

        res['min_last_rotation_date'] = self.min_last_rotation_date

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

        try:
            ix = self._files.index(key)
            del self._files[ix]
        except ValueError:
            LOG.warning(_("Logfile {!r} already removed in logfile group.").format(str(key)))

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
        new_group.sharedscripts = self.sharedscripts

        new_group.rotate = self.rotate
        new_group.start = self.start
        new_group.dateext = self.dateext
        new_group.dateformat = self.dateformat
        new_group.dateyesterday = self.dateyesterday
        new_group.datehourago = self.datehourago
        new_group.addextension = self.addextension
        new_group.extension = self.extension
        new_group.maxage = self.maxage
        new_group.minage = self.minage
        new_group.maxsize = self.maxsize
        new_group.minsize = self.minsize
        new_group.size = self.size

        new_group.rotation_interval = self.rotation_interval
        new_group.create_mode = self.create_mode
        new_group.create_owner = self.create_owner
        new_group.create_group = self.create_group
        new_group.shred = self.shred
        new_group.shredcycles = self.shredcycles

        new_group.olddir = self.olddir
        new_group.createolddir = self.createolddir
        new_group.olddir_mode = self.olddir_mode
        new_group.olddir_owner = self.olddir_owner
        new_group.olddir_group = self.olddir_group

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

        if path not in self.patterns:
            self.patterns.append(path)

    # -------------------------------------------------------------------------
    def resolve_patterns(self, nr=None):

        if self.verbose > 1:
            if nr is None:
                msg = _("Resolving globbing pattern in file group.")
            else:
                msg = _("Resolving globbing pattern in file group number {}.").format(nr)
            LOG.debug(msg)
        self.clear()

        for pattern in self.patterns:

            files = glob.glob(str(pattern))
            if not files:
                msg = _(
                    "Did not found a file for pattern {p!r} defined in {cf!r} line {lnr}."
                    ).format(p=str(pattern), cf=str(self.config_file), lnr=self.line_nr)
                if self.missing_ok:
                    if self.verbose > 1:
                        LOG.debug(msg)
                else:
                    LOG.error(msg)
                continue

            for lfile in files:
                path = Path(lfile).resolve()
                if path in self:
                    LOG.error(_("Multiple definition of logfile {f!r} in {cf!r}.").format(
                        f=str(path), c=str(self.config_file)))
                    continue
                self.append(path)

        if self.verbose > 2:
            LOG.debug(_("Resolved logfiles in file group:") + '\n' + pp(sorted(list(self))))

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
        if directive in self.unsupported_directives:
            LOG.info(_(
                "Unsupported directive {d!r} found in {lf!r}:{lnr}.").format(
                d=directive, lf=str(cfg_file), lnr=linenr))
            return True

        if directive in self.unary_directives:
            return self.apply_unary_directive(line, line_parts, cfg_file, linenr)
        if directive in self.integer_directives:
            return self.apply_integer_directive(line, line_parts, cfg_file, linenr)
        if directive in self.string_directives:
            return self.apply_string_directives(line, line_parts, cfg_file, linenr)

        return False

    # -------------------------------------------------------------------------
    def apply_unary_directive(self, line, line_parts, cfg_file, linenr):

        directive = line_parts[0].lower()

        prop = self.unary_directives[directive]['property']
        val = self.unary_directives[directive]['value']

        if len(line_parts) > 1:
            LOG.error(self.msg_pointless.format(
                d=directive, lf=str(cfg_file), lnr=linenr, line=line))
            return False

        if not self.is_default:
            if prop in self.applied_directives:
                args = {
                    'lf': str(cfg_file), 'lnr': linenr, 'd': directive,
                    'ex': self.applied_directives[prop][0],
                    'of': str(self.applied_directives[prop][1]),
                    'ol': self.applied_directives[prop][2]}
                LOG.error(_(
                    "Error in {lf!r}:{lnr}: directive {d!r} was already set as {ex!r} in "
                    "{of!r}:{ol}.").format(**args))
                return False

        if self.verbose > 2:
            if self.is_default:
                LOG.debug(_(
                    "Setting default file group property {p!r} to {v!r}.").format(p=prop, v=val))
            else:
                LOG.debug(_(
                    "Setting file group property {p!r} to {v!r}.").format(p=prop, v=val))
        if not self.is_default:
            self.applied_directives[prop] = (directive, cfg_file, linenr)
        setattr(self, prop, val)

        return True

    # -------------------------------------------------------------------------
    def apply_integer_directive(self, line, line_parts, cfg_file, linenr):

        directive = line_parts[0].lower()

        prop = self.integer_directives[directive]['property']

        val = None
        default = None
        if 'default' in self.integer_directives[directive]:
            default = self.integer_directives[directive]['default']

        if len(line_parts) < 2:
            if default is None:
                LOG.error(_(
                    "Necessary integer value for directive {d!r} in {lf!r}:{lnr} not given: "
                    "{line}").format(d=directive, lf=str(cfg_file), lnr=linenr, line=line))
                return False
            else:
                val = default
        else:
            val = line_parts[1]

        if len(line_parts) > 2:
            LOG.error(self.msg_pointless.format(
                d=directive, lf=str(cfg_file), lnr=linenr, line=line))
            return False

        if not self.is_default:
            if prop in self.applied_directives:
                args = {
                    'lf': str(cfg_file), 'lnr': linenr, 'd': directive,
                    'ex': self.applied_directives[prop][0],
                    'of': str(self.applied_directives[prop][1]),
                    'ol': self.applied_directives[prop][2]}
                LOG.error(_(
                    "Error in {lf!r}:{lnr}: directive {d!r} was already set as {ex!r} in "
                    "{of!r}:{ol}.").format(**args))
                return False

        if self.verbose > 2:
            if self.is_default:
                LOG.debug(_(
                    "Setting default file group property {p!r} to {v!r}.").format(p=prop, v=val))
            else:
                LOG.debug(_(
                    "Setting file group property {p!r} to {v!r}.").format(p=prop, v=val))
        if not self.is_default:
            self.applied_directives[prop] = (directive, cfg_file, linenr)
        try:
            setattr(self, prop, val)
        except Exception as e:
            msg = _(
                "Invalid value {v!r} for directive {d!r} in {lf!r}:{lnr}: {e}").format(
                v=line_parts[1], d=directive, lf=str(cfg_file), lnr=linenr, e=e)
            LOG.error(msg)
            return False

        return True

    # -------------------------------------------------------------------------
    def apply_string_directives(self, line, line_parts, cfg_file, linenr):

        directive = line_parts[0].lower()
        options = line_parts[1:]
        min_opts = self.string_directives[directive].get('min', 1)
        max_opts = self.string_directives[directive].get('max', None)

        if max_opts and min_opts == max_opts:
            if len(options) != max_opts:
                msg = ngettext(
                    "Directive {d!r} needs exactly one option "
                    "({g} given in {lf!r}:{lnr}): {line}",
                    "Directive {d!r} needs exactly {nr} options "
                    "({g} given in {lf!r}:{lnr}): {line}", max_opts).format(
                    d=directive, nr=max_opts, g=len(options),
                    lf=str(cfg_file), lnr=linenr)
                LOG.error(msg)
                return False

        if len(options) < min_opts:
            msg = ngettext(
                "Directive {d!r} needs at least one option ({g} given in {lf!r}:{lnr}): {line}",
                "Directive {d!r} needs at least {nr} options ({g} given in {lf!r}:{lnr}): {line}",
                min_opts).format(
                d=directive, nr=min_opts, g=len(options), lf=str(cfg_file), lnr=linenr)
            LOG.error(msg)
            return False
        if max_opts and len(options) > max_opts:
            msg = ngettext(
                "Directive {d!r} needs at most one option ({g} given in {lf!r}:{lnr}): {line}",
                "Directive {d!r} needs at most {nr} options ({g} given in {lf!r}:{lnr}): {line}",
                max_opts).format(
                d=directive, nr=max_opts, g=len(options), lf=str(cfg_file), lnr=linenr)
            LOG.error(msg)
            return False

        val = None
        prop = directive
        if directive in (
                'compresscmd', 'compressext', 'addextension', 'extension',
                'olddir', 'dateformat'):
            val = options[0]
        elif directive in ('compressoptions', 'create', 'createolddir'):
            if len(options):
                val = options
            if directive == 'create':
                prop = 'rotate_method'
        else:
            raise RuntimeError(_("There is something failing ..."))

        if not self.is_default:
            if prop in self.applied_directives:
                args = {
                    'lf': str(cfg_file), 'lnr': linenr, 'd': directive,
                    'ex': self.applied_directives[prop][0],
                    'of': str(self.applied_directives[prop][1]),
                    'ol': self.applied_directives[prop][2]}
                LOG.error(_(
                    "Error in {lf!r}:{lnr}: directive {d!r} was already set as {ex!r} in "
                    "{of!r}:{ol}.").format(**args))
                return False

        if self.verbose > 2:
            if self.is_default:
                LOG.debug(_(
                    "Setting default file group property {p!r} to {v!r}.").format(p=prop, v=val))
            else:
                LOG.debug(_(
                    "Setting file group property {p!r} to {v!r}.").format(p=prop, v=val))
        try:
            if directive == 'create':
                self._set_create_options(val)
            elif directive == 'createolddir':
                self.createolddir = True
                self.olddir_mode = val[0]
                self.olddir_owner = val[1]
                self.olddir_group = val[2]
            else:
                setattr(self, prop, val)
        except Exception as e:
            msg = _(
                "Invalid value {v!r} for directive {d!r} in {lf!r}:{lnr}: {c} - {e}").format(
                v=val, d=prop, lf=str(cfg_file), lnr=linenr,
                c=e.__class__.__name__, e=e)
            if self.verbose > 3:
                self.handle_error(msg, do_traceback=True)
            else:
                LOG.error(msg)
            return False

        if not self.is_default:
            self.applied_directives[prop] = (directive, cfg_file, linenr)

        return True

    # -------------------------------------------------------------------------
    def _set_create_options(self, options):

        if self.verbose > 2:
            LOG.debug(_(
                "Setting rotation method to {m!r} and the create options to {o!r}.").format(
                m='create', o=options))

        self.rotate_method = RotateMethod.create

        if options is None:
            self.create_mode = None
            self.create_owner = None
            self.create_group = None
            return

        if len(options) == 1:
            self.create_mode = None
            self.create_owner = options[0]
            self.create_group = None
            return

        if len(options) == 2:
            self.create_mode = None
            self.create_owner = options[0]
            self.create_group = options[1]
            return

        self.create_mode = options[0]
        self.create_owner = options[1]
        self.create_group = options[2]

    # -------------------------------------------------------------------------
    def check_for_rotation(self, logfile):

        LOG.debug(_("Checking file {!r} for the need of rotation.").format(str(logfile)))
        if not logfile.exists():
            msg = _("File {!r} does not exists.").format(str(logfile))
            raise LogFileGroupError(msg)
        if not logfile.is_file():
            msg = _("File {!r} is not a regular file.").format(str(logfile))
            LOG.error(msg)
            return False

        fstat = logfile.stat()
        file_size = fstat.st_size
        if not self.if_empty and not file_size:
            LOG.debug(_("File {!r} is empty and that's why it should not be rotated.").format(
                str(logfile)))
            return False
        fs_str = bytes2human(file_size, precision=1)
        if self.verbose > 1:
            LOG.debug(_("File {lf!r} has a size of {sz}.").format(lf=str(logfile), sz=fs_str))

        diff_last_rotated = None
        dt_mtime = datetime.datetime.fromtimestamp(fstat.st_mtime, StatusFileEntry.local_timezone)
        now = datetime.datetime.now(StatusFileEntry.local_timezone)
        if logfile in self.last_rotation:
            diff_last_rotated = now - self.last_rotation[logfile]
            diff_last_rotated_float = float(diff_last_rotated.days) + (
                float(diff_last_rotated.seconds) / 24 / 60 / 60)
            if self.verbose > 1:
                LOG.debug(_("Last rotation of was {days:0.1f} days ago.").format(
                    days=diff_last_rotated_float))
        elif self.verbose > 1:
            LOG.debug(_("File was obviously not rotated."))

        file_age = now - dt_mtime
        file_age_float = float(file_age.days) + (float(file_age.seconds) / 24 / 60 / 60)
        if self.verbose > 1:
            LOG.debug(_("File {lf!r} is {days:0.1f} days old.").format(
                lf=str(logfile), days=file_age_float))
        if self.minage is not None:
            if file_age.days < self.minage:
                msg = ngettext(
                    "File {lf!r} is less than one day old, not rotating.",
                    "File {lf!r} is less than {days} days old, not rotating.",
                    self.minage).format(lf=str(logfile), days=self.minage)
                LOG.debug(msg)
                return False

        if self.size is not None:
            msize_str = bytes2human(self.size, precision=1)
            if file_size >= self.size:
                LOG.debug(_("File {lf!r} is bigger than or equal to size {sz}, rotating.").format(
                    lf=str(logfile), sz=msize_str))
                return True
            else:
                LOG.debug(_("File {lf!r} is less than a size of {sz}, not rotating.".format(
                    lf=str(logfile), sz=msize_str)))
                return False

        if self.maxsize is not None:
            msize_str = bytes2human(self.maxsize, precision=1)
            if file_size >= self.maxsize:
                LOG.debug(_(
                    "File {lf!r} is bigger than or equal to maximum size {sz},"
                    " rotating.").format(lf=str(logfile), sz=msize_str))
                return True

        min_rotation_date = self.min_last_rotation_date[str(self.rotation_interval)]
        if self.verbose > 1:
            LOG.debug(_("Minimum last rotation date of file {lf!r}: {dt}").format(
                lf=str(logfile), dt=min_rotation_date.isoformat(' ')))
        if logfile in self.last_rotation:
            if self.last_rotation[logfile] <= min_rotation_date:
                LOG.debug(_("Last rotation was long enough ago."))
                if self.minsize is None:
                    return True
            else:
                LOG.debug(_("Last rotation was not long enough ago."))
                return False

        if self.minsize is not None:
            msize_str = bytes2human(self.minsize, precision=1)
            if file_size < self.minsize:
                LOG.debug(_(
                    "File {lf!r} is less than the minimum size of {sz}, not rotating.".format(
                    lf=str(logfile), sz=msize_str)))
                return False
            LOG.debug(_(
                "File {lf!r} is bigger than or equal to minimum size {sz}, rotating.").format(
                lf=str(logfile), sz=msize_str))
            return True

        LOG.debug(_("File {lf!r} should not be rotated from some unknown reason.").format(
            lf=str(logfile)))
        return False


# ========================================================================
if __name__ == "__main__":
    pass

# ========================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
