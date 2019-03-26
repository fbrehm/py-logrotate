#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank@brehm-online.com
@license: GPL3
@copyright: © 2010 - 2016 by Frank Brehm, Berlin
@summary: module for operations with the logrotate state file
"""

# Standard modules
import re
import sys
import os
import logging
import shlex
import collections
import stat

from datetime import tzinfo, timedelta, datetime, date, time

from pathlib import Path

# Third party modules
import pytz
import six

from six.moves import shlex_quote

# Own modules
from fb_tools.common import pp, to_str

from fb_tools.obj import FbBaseObjectError, FbBaseObject

from .translate import XLATOR

from .common import split_parts

__version__ = '0.4.2'

_ = XLATOR.gettext
ngettext = XLATOR.ngettext

LOG = logging.getLogger(__name__)
DEFAULT_PERMISSIONS = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
ENCODING = "utf-8"

UTC = pytz.utc


# =============================================================================
class LogrotateStatusFileError(FbBaseObjectError):
    """
    Base class for exceptions in this module.
    """
    pass


# =============================================================================
class LogrotateStatusEntryError(FbBaseObjectError):
    "Exception class for errors with status file entries."
    pass


# =============================================================================
class StatusEntryValueError(LogrotateStatusEntryError, ValueError):
    "Exception class for wrong values on status file entries."
    pass


# =============================================================================
class StatusFileEntry(FbBaseObject):
    """
    Class for a single status file entry.
    """

    pat_ts_date = r'(?P<year>\d+)[-_](?P<month>\d+)[-_](?P<day>\d+)'
    pat_ts_time = r'(?P<hour>\d+)[-_:](?P<min>\d+)[-_:](?P<sec>\d+)'
    pat_ts_v2 = r'^\s*' + pat_ts_date + r'\s*$'
    pat_ts_v3 = r'^\s*' + pat_ts_date + r'[-_\s]+' + pat_ts_time + r'\s*$'
    quotes = '"' + "'"
    pat_quotes = r'^(?P<quote>[' + quotes + r']).*?(?P=quote)$'
    re_quoted = re.compile(pat_quotes)
    re_ts_v2 = re.compile(pat_ts_v2)
    re_ts_v3 = re.compile(pat_ts_v3)

    # -----------------------------------------------------------------------
    def __init__(self, filename=None, ts=None, appname=None, verbose=0, base_dir=None):

        self._filename = None
        self._ts = None

        super(StatusFileEntry, self).__init__(
            appname=appname, verbose=verbose, version=__version__, base_dir=base_dir)

        self.filename = filename
        self.ts = ts

    # -----------------------------------------------------------------------
    @property
    def filename(self):
        "The file name of this entry."
        return self._filename

    @filename.setter
    def filename(self, value):
        if value is None:
            self._filename = None
            return
        self._filename = Path(to_str(value))

    # -----------------------------------------------------------------------
    @property
    def quoted_filename(self):
        "The filename in a shell-escaped version."
        if self.filename is None:
            return None
        ret = shlex_quote(str(self.filename))
        if not self.re_quoted.search(ret):
            ret = '"' + ret + '"'
        return ret

    # -----------------------------------------------------------------------
    @property
    def ts(self):
        "The timestamp of the last rotation of this file."
        return self._ts

    @ts.setter
    def ts(self, value):
        if value is None:
            self._ts = None
            return
        self._ts = self.to_timestamp(value)

    # -------------------------------------------------------------------------
    @classmethod
    def to_timestamp(cls, value):
        """Tries to cast the given value into a datetime object somehow."""

        if value is None:
            return datetime.utcnow()

        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime(value.year, value.month, value.day, tzinfo=UTC)

        v_str = str(to_str(value))

        match = cls.re_ts_v3.search(v_str)
        if match:
            return datetime(
                year=int(match.group('year')), month=int(match.group('month')),
                day=int(match.group('day')), hour=int(match.group('hour')),
                minute=int(match.group('min')), second=int(match.group('sec')),
                tzinfo=UTC)

        match = cls.re_ts_v2.search(v_str)
        if match:
            return datetime(
                year=int(match.group('year')), month=int(match.group('month')),
                day=int(match.group('day')), tzinfo=UTC)

        msg = _("Could not evaluate {!r} as a datetime object.").format(value)
        raise StatusEntryValueError(msg)

    # -------------------------------------------------------------------------
    def as_dict(self, short=True):
        """
        Transforms the elements of the object into a dict

        @return: structure as dict
        @rtype:  dict
        """

        res = super(StatusFileEntry, self).as_dict(short=short)

        res['filename'] = self.filename
        res['quoted_filename'] = self.quoted_filename
        res['ts'] = self.ts
        if self.verbose > 2:
            res['line'] = str(self)
        if self.verbose > 3:
            res['pat_ts_v2'] = self.pat_ts_v2
            res['pat_ts_v3'] = self.pat_ts_v3
            res['pat_quotes'] = self.pat_quotes
            res['quotes'] = self.quotes

        return res

    # -----------------------------------------------------------------------
    @classmethod
    def from_line(cls, line, appname=None, verbose=0, base_dir=None):

        entry = cls(appname=appname, verbose=verbose, base_dir=base_dir)
        #fields = split_parts(line.strip())
        fields = shlex.split(line, comments=False, posix=True)

        if len(fields) > 0:
            entry.filename = fields[0]
        if len(fields) > 1:
            entry.ts = fields[1]

        return entry

    # -------------------------------------------------------------------------
    def __repr__(self):
        """Typecasting into a string for reproduction."""

        out = "<%s(" % (self.__class__.__name__)

        fields = []
        fields.append("filename=%r" % (self.filename))
        fields.append("ts=%r" % (self.ts))
        fields.append("appname=%r" % (self.appname))
        fields.append("verbose=%r" % (self.verbose))
        fields.append("version=%r" % (self.version))
        fields.append("base_dir=%r" % (self.base_dir))

        out += ", ".join(fields) + ")>"
        return out

    # -------------------------------------------------------------------------
    def get_line(self, min_len_filename=0):

        fn_out = '~'
        if self.filename:
            fn_out = self.quoted_filename
        ts_out = '~'
        if self.ts:
            ts_out = self.ts.strftime('%Y-%m-%d_%H:%M:%S')

        return '%-*s %s' % (min_len_filename, fn_out, ts_out)

    # -------------------------------------------------------------------------
    def __str__(self):
        return self.get_line()

    # -------------------------------------------------------------------------
    def __eq__(self, other):

        if not isinstance(other, StatusFileEntry):
            return NotImplemented

        if self.filename == other.filename:
            return True
        return False

    # -------------------------------------------------------------------------
    def __ne__(self, other):

        if not isinstance(other, StatusFileEntry):
            return NotImplemented
        if self == other:
            return False
        return True

    # -------------------------------------------------------------------------
    def __lt__(self, other):

        if not isinstance(other, StatusFileEntry):
            return NotImplemented

        if self.filename is None:
            if other.filename is None:
                return False
            else:
                return True
        elif other.filename is None:
            return False

        if str(self.filename).lower() != str(other.filename).lower():
            return str(self.filename).lower() < str(other.filename).lower()

        return str(self.filename) < str(other.filename)

    # -------------------------------------------------------------------------
    def __gt__(self, other):

        if not isinstance(other, StatusFileEntry):
            return NotImplemented

        if self < other:
            return False
        return True

    # -------------------------------------------------------------------------
    def __copy__(self):
        "Implementing a wrapper for copy.copy()."

        if self.verbose > 3:
            LOG.debug("Copying status file entry for %r ...", self.filename)

        entry = StatusFileEntry(
            filename=self.filename, ts=self.ts,
            appname=self.appname, verbose=self.verbose, base_dir=self.base_dir)

        entry._version = self.version
        return entry


# =============================================================================
class StatusFile(FbBaseObject, collections.MutableMapping):
    """Class for operations with the logrotate state file"""

    open_args = {}
    if six.PY3:
        open_args = {
            'encoding': ENCODING,
            'errors': 'surrogateescape'
        }

    re_first_line = re.compile(
        r'^logrotate\s+state\s+-+\s+version\s+(\d+)$',
        re.IGNORECASE)

    # -----------------------------------------------------------------------
    def __init__(
        self, filename, simulate=False, auto_read=True, permissions=DEFAULT_PERMISSIONS,
            appname=None, verbose=0, version=__version__, base_dir=None):
        """
        Constructor.

        @param file_name: the file name of the status file
        @type file_name: str
        @param simulate: test mode - no write actions are made
        @type simulate: bool
        """

        self.filename = Path(filename)
        self._simulate = bool(simulate)
        self._was_read = False
        self._has_changed = False
        self.permissions = permissions

        self._entries = []

        super(StatusFile, self).__init__(
            appname=appname, verbose=verbose, version=__version__, base_dir=base_dir)

        if auto_read and os.path.exists(self.filename):
            if self.verbose > 2:
                LOG.debug(_("Auto reading on init ..."))
            self.read()
        else:
            if self.verbose > 2:
                LOG.debug(_("No auto reading on init ..."))

    # -----------------------------------------------------------
    @property
    def was_read(self):
        """Flag, that the current config file was read."""
        return self._was_read

    # -----------------------------------------------------------
    @property
    def has_changed(self):
        """Flag, that something has changed, which must be written."""
        return self._has_changed

    # -----------------------------------------------------------
    @property
    def simulate(self):
        """Simulation mode."""
        return self._simulate

    @simulate.setter
    def simulate(self, value):
        self._simulate = bool(value)

    # -----------------------------------------------------------------------
    def as_dict(self):
        """
        Transforms the elements of the object into a dict

        @return: structure as dict
        @rtype:  dict
        """

        res = super(StatusFile, self).as_dict()

        res['simulate'] = self.simulate
        res['was_read'] = self.was_read
        res['has_changed'] = self.has_changed
        res['open_args'] = self.open_args
        res['permissions'] = "%04o" % (self.permissions)

        res['entries'] = []
        for entry in self._entries:
            res['entries'].append(entry.as_dict())

        return res

    # -----------------------------------------------------------------------
    def __del__(self):
        """
        Destructor.
        Enforce saving of status file, if something has changed.
        """

        LOG.debug(_("Status file object will destroyed."))

        # if self.has_changed:
        #     self.write()

    # -----------------------------------------------------------------------
    def __getitem__(self, filename):

        fpath = Path(filename)
        for entry in self._entries:
            if entry.filename == fpath:
                return entry
        raise KeyError(filename)

    # -----------------------------------------------------------------------
    def __setitem__(self, filename, entry):

        if not isinstance(entry, StatusFileEntry):
            msg = _("Only {e} objects can be added to a {c} object (given {f} object).").format(
                e='StatusFileEntry', c=self.__class__.__name__, f=entry.__class__.__name__)
            raise ValueError(msg)

        fpath = Path(filename)

        if fpath != entry.filename:
            msg = _(
                "Filename {f1!r} in given {o} object "
                "does not match given filename {f2!r}.").format(
                f1=str(entry.filename), o=entry.__class__.__name__, f2=str(fpath))
            raise ValueError(msg)

        found = False
        for i in range(len(self._entries)):
            if self._entries[i].filename == fpath:
                if self._entries[i].ts != entry.ts:
                    self._entries[i] = entry
                    self._has_changed = True
                found = True
                break
        if not found:
            self._entries.append(entry)
            self._has_changed = True

    # -----------------------------------------------------------------------
    def __contains__(self, filename):

        fpath = Path(filename)
        for entry in self._entries:
            if entry.filename == fpath:
                return True
        return False

    # -----------------------------------------------------------------------
    def __delitem__(self, filename):

        fpath = Path(filename)
        for i in range(len(self._entries)):
            entry = self._entries[i]
            if entry.filename == fpath:
                self._entries.pop(i)
                self._has_changed = True
                break

    # -----------------------------------------------------------------------
    def __iter__(self):
        for entry in self._entries:
            yield entry.filename

    # -----------------------------------------------------------------------
    def __len__(self):
        return len(self._entries)

    # -----------------------------------------------------------------------
    def get_permissions(self):
        """Retrieving the current file permissions and store them
            in self.permissions."""

        orig_mode = self.filename.stat().st_mode
        orig_perms = stat.S_IMODE(orig_mode)
        LOG.debug(
            _("Original permissions of {fn!r}: {perm:04o}").format(
                fn=str(self.filename), perm=orig_perms))
        self.permissions = orig_perms

    # -----------------------------------------------------------------------
    def read(self):
        """Reads the status file and put the results in self._entries."""

        self._entries = list()

        if not self.filename.exists():
            msg = _("File does not exists")
            raise IOError(errno.ENOENT, msg, str(self.filename))

        if not self.filename.is_file():
            msg = _("Path is not a regular file")
            raise IOError(errno.ENOENT, msg, str(self.filename))

        if not os.access(str(self.filename), os.R_OK):
            msg = _("No read permissions")
            raise IOError(errno.EACCES, msg, str(self.filename))

        LOG.debug(_("Trying to read {!r} ...").format(str(self.filename)))
        with self.filename.open('r', **self.open_args) as fh:
            i = 0
            for line in fh.readlines():
                i += 1
                match = self.re_first_line.search(line)
                if match:
                    LOG.debug(
                        _("Idendified version of status file: {}").format(int(match.group(1))))
                    continue
                try:
                    entry = StatusFileEntry.from_line(
                        line, appname=self.appname, verbose=self.verbose,
                        base_dir=self.base_dir)
                    self._entries.append(entry)
                except ValueError as e:
                    LOG.error(_(
                        "Could not evaluate line {file!r}:{lnr} {line!r}: {e}").format(
                            file=str(self.filename), lnr=i, line=line, e=e))
                    continue

        self.get_permissions()
        self._was_read = True

    # -----------------------------------------------------------------------
    def write(self):
        """Writes the states into the status file."""

        max_len_filename = 1
        for entry in self._entries:
            new_len = len(entry.quoted_filename)
            if new_len > max_len_filename:
                max_len_filename = new_len

        first_line = 'Logrotate State -- Version 3'

        if self.simulate:
            LOG.info(_("Simulating writing {!r} ...").format(str(self.filename)))
            if self.verbose > 2:
                LOG.debug(_("Writing line {!r}.").format(first_line))
                for entry in sorted(self._entries):
                    line = entry.get_line(max_len_filename)
                    LOG.debug(_("Writing line {!r}.").format(line))
            self._has_changed = False
            return

        LOG.info(_("Trying to write {!r} ...").format(str(self.filename)))

        with self.filename.open('w', 1, **self.open_args) as fh:
            if self.verbose > 2:
                LOG.debug(_("Writing line {!r}.").format(first_line))
            fh.write('%s\n' % (first_line))
            for entry in sorted(self._entries):
                line = entry.get_line(max_len_filename)
                if self.verbose > 2:
                    LOG.debug(_("Writing line {!r}.").format(line))
                fh.write('%s\n' % (line))

        self.ensure_permissions()
        self._has_changed = False

    # -----------------------------------------------------------------------
    def ensure_permissions(self, permissions=None):

        if not self.filename.exists():
            msg = _("File does not exists")
            raise IOError(errno.ENOENT, msg, str(self.filename))

        if permissions is None:
            permissions = self.permissions

        LOG.debug(_("Ensuring permissions of {!r} ...").format(str(self.filename)))
        operms = self.filename.stat().st_mode
        operms = stat.S_IMODE(operms)
        LOG.debug(_(
            "Current permissions of {fn!r}: {cur:04o}, expected: {exp:04o}.").format(
                fn=str(self.filename), cur=operms, exp=permissions))
        if operms != permissions:
            LOG.info(_(
                "Setting permissions of {fn!r} to {perm:04o}.").format(
                fn=str(self.filename), perm=permissions))
            if not self.simulate:
                os.chmod(self.filename, permissions)

    # -----------------------------------------------------------------------
    def __str__(self):
        '''
        Typecasting function for translating object structure
        into a string

        @return: structure as string
        @rtype:  str
        '''

        return pp(self.as_dict())

    # -----------------------------------------------------------------------
    def set_entry(self, filename, timestamp=None):
        """
        Setting the rotation timestamp of the given filename. If no timestamp
        was given, the current timestamp will be used.
        """

        ts = StatusFileEntry.to_timestamp(timestamp)
        entry = StatusFileEntry(
            filename=filename, ts=ts,
            appname=self.appname, verbose=self.verbose, base_dir=self.base_dir)
        fname = entry.filename
        self[fname] = entry

    # -----------------------------------------------------------------------
    def check_permissions(self):
        '''
        Checks the permissions of the state file and/or his parent directory.
        Throws a LogrotateStatusFileError on a error.

        @return: success of check
        @rtype: bool
        '''

        msg = _("Checking permissions of status file {!r} ...").format(str(self.filename))
        LOG.debug(msg)

        if self.filename.exists():
            # Check for write access to the status file
            if os.access(str(self.filename), os.W_OK):
                msg = _("Access to status file {!r} is OK.").format(str(self.filename))
                LOG.debug(msg)
                return True
            else:
                msg = _("No write access to status file {!r}.").format(str(self.filename))
                if self.simulate:
                    LOG.error(msg)
                else:
                    raise LogrotateStatusFileError(msg)
                return False

        parent_dir = self.filename.parent
        msg = _("Checking permissions of parent directory {!r} ...").format(str(parent_dir))
        LOG.debug(msg)

        # Check for existence of parent dir
        if not parent_dir.exists():
            msg = _("Directory {!r} doesn't exists.").format(str(parent_dir))
            if self.simulate:
                LOG.error(msg)
            else:
                raise LogrotateStatusFileError(msg)
            return False

        # Check whether parent dir is a directory
        if not parent_dir.is_dir():
            msg = _("Parent directory {d!r} of status file {f!r} is not a directory.").format(
                d=str(parent_dir), f=str(self.filename))
            if self.simulate:
                LOG.error(msg)
            else:
                raise LogrotateStatusFileError(msg)
            return False

        # Check for write access to parent dir
        if not os.access(parent_dir, os.W_OK):
            msg = _("No write access to parent directory {d!r} of status file {f!r}.").format(
                d=str(parent_dir), f=str(self.filename))
            if self.simulate:
                LOG.error(msg)
            else:
                raise LogrotateStatusFileError(msg)
            return False

        msg = _("Permissions to parent directory {!r} are OK.").format(str(parent_dir))
        LOG.debug(msg)
        return True

# =============================================================================

if __name__ == "__main__":
    pass

# =============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
