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

from datetime import tzinfo, timedelta, datetime, date, time

# Third party modules
import pytz
import six

from six.moves import shlex_quote

# Own modules
from logrotate.common import split_parts, pp
from logrotate.common import logrotate_gettext, logrotate_ngettext
from logrotate.common import to_str_or_bust as as_str

from logrotate.base import BaseObjectError, BaseObject

__version__ = '0.2.2'

_ = logrotate_gettext
__ = logrotate_ngettext

LOG = logging.getLogger(__name__)

utc = pytz.utc


# =============================================================================
class LogrotateStatusFileError(BaseObjectError):
    """
    Base class for exceptions in this module.
    """
    pass


# =============================================================================
class LogrotateStatusEntryError(BaseObjectError):
    "Exception class for errors with status file entries."
    pass


# =============================================================================
class StatusEntryValueError(LogrotateStatusEntryError, ValueError):
    "Exception class for wrong values on status file entries."
    pass


# =============================================================================
class StatusFileEntry(BaseObject):
    """
    Class for a single status file entry.
    """

    pat_ts_date = r'(?P<year>\d+)[-_](?P<month>\d+)[-_](?P<day>\d+)'
    pat_ts_time = r'(?P<hour>\d+)[-_:](?P<min>\d+)[-_:](?P<sec>\d+)'
    pat_ts_v2 = r'^\s*' + pat_ts_date + r'\s*$'
    pat_ts_v3 = r'^\s*' + pat_ts_date + r'[-_\s]+' + pat_ts_time + r'\s*$'
    re_ts_v2 = re.compile(pat_ts_v2)
    re_ts_v3 = re.compile(pat_ts_v3)

    # -----------------------------------------------------------------------
    def __init__( self, filename=None, ts=None, appname=None, verbose=0, base_dir=None):

        self._filename = None
        self._ts = None

        super(ShadowEntry, self).__init__(
            appname=appname, verbose=verbose, version=__version__, base_dir=base_dir)

        self.filename = filename

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
        self._filename = str(value, force=True)

    # -----------------------------------------------------------------------
    @property
    def quoted_filename(self):
        "The filename in a shell-escaped version."
        if self.filename is None:
            return None
        return shlex_quote(self.filename)

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
        if isinstance(value, datetime):
            self._ts = value
            return
        if isinstance(value, date):
            self._ts = datetime(value.year, value.month, value.day, tzinfo=utc)
            return

        v_str = as_str(value, force=True)

        match = self.re_ts_v3.search(v_str)
        if match:
            self._ts = datetime(
                year=int(match.group('year')), month=int(match.group('month')),
                day=int(match.group('day')), hour=int(match.group('hour')),
                minute=int(match.group('min')), second=int(match.group('sec')),
                tzinfo=utc)
            return

        match = self.re_ts_v2.search(v_str)
        if match:
            self._ts = datetime(
                year=int(match.group('year')), month=int(match.group('month')),
                day=int(match.group('day')), tzinfo=utc)
            return

        msg = _("Could not evaluate %r as a dateime object.") % (value)
        raise StatusEntryValueError

    # -------------------------------------------------------------------------
    def as_dict(self):
        """
        Transforms the elements of the object into a dict

        @return: structure as dict
        @rtype:  dict
        """

        res = super(StatusFileEntry, self).as_dict()

        res['filename'] = self.filename
        res['quoted_filename'] = self.quoted_filename
        res['ts'] = self.ts
        res['pat_ts_v2'] = self.pat_ts_v2
        res['pat_ts_v3'] = self.pat_ts_v3

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

        return '%-*s "%s"' % (
            min_len_filename,
            self.quoted_filename,
            self.ts.strftime('%Y-%m-%d %H:%M:%S'))

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

        if self.filename.lower() != other.filename.lower():
            return self.filename.lower() < other.filename.lower()

        return self.filename < other.filename

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
class LogrotateStatusFile(object):
    '''
    Class for operations with the logrotate state file

    @author: Frank Brehm
    @contact: frank@brehm-online.com
    '''

    #-------------------------------------------------------
    def __init__( self, file_name,
                        local_dir  = None,
                        verbose    = 0,
                        test_mode  = False,
    ):
        '''
        Constructor.

        @param file_name: the file name of the status file
        @type file_name:  str
        @param verbose:   verbosity (debug) level
        @type verbose:    int
        @param test_mode: test mode - no write actions are made
        @type test_mode:  bool
        @param local_dir: The directory, where the i18n-files (*.mo)
                          are located. If None, then system default
                          (/usr/share/locale) is used.
        @type local_dir:  str or None

        @return: None
        '''

        self.local_dir = local_dir
        '''
        @ivar: The directory, where the i18n-files (*.mo) are located.
        @type: str or None
        '''

        self.t = gettext.translation(
            'pylogrotate',
            local_dir,
            fallback = True
        )
        '''
        @ivar: a gettext translation object
        @type: gettext.translation
        '''

        _ = self.t.lgettext

        self.verbose = verbose
        '''
        @ivar: verbosity level (0 - 9)
        @type: int
        '''

        self.file_name = file_name
        '''
        @ivar: the initial file name of the status file to use
        @type: str
        '''

        self.file_name_is_absolute = False
        '''
        @ivar: flag, that shows, that the file name is now an absolute path
        @type: bool
        '''

        self.fd = None
        '''
        @ivar: the file object of the opened status file, or None, if not opened
        @type: file or None
        '''

        self.was_read = False
        '''
        @ivar: flag, whether the status file was read
        @type: bool
        '''

        self.status_version = None
        '''
        @ivar: the version of the status file (2 or 3)
        @type: int or None
        '''

        self.test_mode = test_mode
        '''
        @ivar: test mode - no write actions are made
        @type: bool
        '''

        self.has_changed = False
        '''
        @ivar: flag, whether something has changed and needs to be written
        @type: bool
        '''

        self.logger = logging.getLogger('pylogrotate.status_file')
        '''
        @ivar: logger object
        @type: logging.getLogger
        '''

        self.file_state = {}
        '''
        @ivar: the last rotation date of every particular log file
               keys are the asolute filenames (without globbing)
               and the values are datetime objects of the last rotation
               referencing to UTC
               If no rotation was made, value is datetime.min().
        @type: dict
        '''

        # Initial read and check for permissions
        self.read(must_exists = False)
        self._check_permissions()

    #-------------------------------------------------------
    def __del__(self):
        '''
        Destructor.
        Enforce saving of status file, if something has changed.
        '''

        _ = self.t.lgettext
        msg = _("Status file object will destroyed.")
        self.logger.debug(msg)

        if self.has_changed:
            self.write()

    #-------------------------------------------------------
    def as_dict(self):
        '''
        Transforms the elements of the object into a dict

        @return: structure as dict
        @rtype:  dict
        '''

        res = {}
        res['local_dir']             = self.local_dir
        res['t']                     = self.t
        res['verbose']               = self.verbose
        res['file_name']             = self.file_name
        res['file_name_is_absolute'] = self.file_name_is_absolute
        res['fd']                    = self.fd
        res['status_version']        = self.status_version
        res['test_mode']             = self.test_mode
        res['logger']                = self.logger
        res['file_state']            = self.file_state
        res['was_read']              = self.was_read
        res['has_changed']           = self.has_changed

        return res

    #------------------------------------------------------------
    def get_rotation_date(self, logfile):
        '''
        Gives back the date of the last rotation of a particular logfile.
        If this logfile is not found in the state file,
        datetime.min() is given back.

        @param logfile: the logfile to query
        @type logfile:  str

        @return: date of last rotation of this logfile
        @rtype:  datetime
        '''

        if not self.was_read:
            self.read(must_exists = False)

        rotate_date = datetime.min.replace(tzinfo=utc)
        if logfile in self.file_state:
            rotate_date = self.file_state[logfile]

        return rotate_date

    #------------------------------------------------------------
    def set_rotation_date(self, logfile, rotate_date = None):
        '''
        Sets the rotation date of the given logfile.
        If the rotation date is not given, datetime.utcnow() is used.

        @param logfile:     the logfile to set
        @type logfile:      str
        @param rotate_date: the rotation date of this logfile
        @type rotate_date:  datetime or None

        @return: date of rotation of this logfile (relative to UTC)
        @rtype:  datetime
        '''

        date_utc = datetime.utcnow()
        if rotate_date:
            date_utc = rotate_date.astimezone(utc)

        _ = self.t.lgettext
        msg = (_("Setting rotation date of '%(file)s' to '%(date)s' ...") %
                {'file': logfile, 'date': date_utc.isoformat(' ') })
        self.logger.debug(msg)

        #self.read(must_exists = False)
        self.file_state[logfile] = date_utc
        self.has_changed = True

        #self.write()

        return date_utc

    #------------------------------------------------------------
    def write(self):
        '''
        Writes the content of self.file_state in the state file.

        @return:    success of writing
        @rtype:     bool
        '''

        _ = self.t.lgettext

        # setting a failing version of the status file
        if not self.status_version:
            self.status_version = 3

        max_length = 1

        # Retrieving the maximum length of the logfiles for version 3
        if self.status_version == 3:
            for logfile in self.file_state:
                if len(logfile) > max_length:
                    max_length = len(logfile)
            max_length += 2

        fd = None
        # Big try block for ensure closing open status file
        try:

            msg = (_("Open status file '%s' for writing ...") %
                    (self.file_name))
            self.logger.debug(msg)

            # open status file for writing
            if not self.test_mode:
                try:
                    fd = open(self.file_name, 'w')
                except IOError, e:
                    msg = (_("Could not open status file '%s' for write: ") %
                            (self.file_name) + str(e))
                    raise LogrotateStatusFileError(msg)

            # write logrotate version line
            line = 'Logrotate State -- Version 3'
            if self.status_version == 2:
                line = 'logrotate state -- version 2'
            if self.verbose > 2:
                msg = _("Writing version line '%s'.") % (line)
                self.logger.debug(msg)
            line += '\n'
            if fd:
                fd.write(line)

            # iterate over logfiles in self.file_state
            for logfile in sorted(
                    self.file_state.keys(),
                    lambda x,y: cmp(x.lower(), y.lower())):
                rotate_date = self.file_state[logfile]
                date_str = ( "%d-%d-%d" 
                    % (rotate_date.year, rotate_date.month, rotate_date.day))
                if self.status_version == 3:
                    date_str = (
                        "%d-%02d-%02d_%02d:%02d:%02d" % (
                            rotate_date.year,
                            rotate_date.month,
                            rotate_date.day,
                            rotate_date.hour,
                            rotate_date.minute,
                            rotate_date.second))
                line = ('%-*s %s'
                        % (max_length, ('"' + logfile + '"'), date_str))
                if self.verbose > 2:
                    msg = _("Writing line '%s'.") % (line)
                    self.logger.debug(msg)
                if fd:
                    fd.write(line + "\n")

        finally:
            if fd:
                fd.close()
                fd = None

        self.has_changed = False
        return True

    #------------------------------------------------------------
    def __str__(self):
        '''
        Typecasting function for translating object structure
        into a string

        @return: structure as string
        @rtype:  str
        '''

        return pp(self.as_dict())

    #------------------------------------------------------------
    def _check_permissions(self):
        '''
        Checks the permissions of the state file and/or his parent directory.
        Throws a LogrotateStatusFileError on a error.

        @return:    success of check
        @rtype:     bool
        '''

        _ = self.t.lgettext
        msg = (_("Checking permissions of status file '%s' ...")
                % (self.file_name))
        self.logger.debug(msg)

        if os.path.exists(self.file_name):
            # Check for write access to the status file
            if os.access(self.file_name, os.W_OK):
                msg = _("Access to status file '%s' is OK.") % (self.file_name)
                self.logger.debug(msg)
                return True
            else:
                msg = (_("No write access to status file '%s'.")
                        % (self.file_name))
                if self.test_mode:
                    self.logger.error(msg)
                else:
                    raise LogrotateStatusFileError(msg)
                return False

        parent_dir = os.path.dirname(self.file_name)
        msg = (_("Checking permissions of parent directory '%s' ...")
                % (parent_dir))
        self.logger.debug(msg)

        # Check for existence of parent dir
        if not os.path.exists(parent_dir):
            msg = _("Directory '%s' doesn't exists.") % (parent_dir)
            if self.test_mode:
                self.logger.error(msg)
            else:
                raise LogrotateStatusFileError(msg)
            return False

        # Check whether parent dir is a directory
        if not os.path.isdir(parent_dir):
            msg = (_("Parent directory '%(dir)s' of status file '%(file)s' "
                     + "is not a directory.") 
                    % {'dir': parent_dir, 'file': self.file_name })
            if self.test_mode:
                self.logger.error(msg)
            else:
                raise LogrotateStatusFileError(msg)
            return False

        # Check for write access to parent dir
        if not os.access(parent_dir, os.W_OK):
            msg = (_("No write access to parent directory '%(dir)s' "
                     + "of status file '%(file)s'.")
                    % {'dir': parent_dir, 'file': self.file_name })
            if self.test_mode:
                self.logger.error(msg)
            else:
                raise LogrotateStatusFileError(msg)
            return False

        msg = _("Permissions to parent directory '%s' are OK.") % (parent_dir)
        self.logger.debug(msg)
        return True

    #-------------------------------------------------------
    def read(self, must_exists = True):
        '''
        Reads the status file and put the results in the dict self.file_state.
        Puts back the absolute path of the status file
        in self.file_name on success.

        Throws a LogrotateStatusFileError on a error.

        @param must_exists: throws an exception, if true and the status file
                            doesn't exists
        @type must_exists:  bool

        @return:    success of reading
        @rtype:     bool
        '''

        self.file_state = {}
        _ = self.t.lgettext

        # Check for existence of status file
        if not os.path.exists(self.file_name):
            msg = _("Status file '%s' doesn't exists.") % (self.file_name)
            if must_exists:
                raise LogrotateStatusFileError(msg)
            else:
                self.logger.info(msg)
            return False

        # makes the name of the status file an absolute path
        if not self.file_name_is_absolute:
            self.file_name = os.path.abspath(self.file_name)
            self.file_name_is_absolute = True
            if self.verbose > 2:
                msg = (_("Absolute path of status file is now '%s'.")
                        % (self.file_name))
                self.logger.debug(msg)

        # Checks, that the status file is a regular file
        if not os.path.isfile(self.file_name):
            msg = (_("Status file '%s' is not a regular file.")
                    % (self.file_name))
            raise LogrotateStatusFileError(msg)
            return False

        msg = _("Reading status file '%s' ...") % (self.file_name)
        self.logger.debug(msg)

        fd = None
        try:
            fd = open(self.file_name, 'Ur')
        except IOError, e:
            msg = (_("Could not read status file '%s': ")
                    % (self.file_name)) + str(e)
            raise LogrotateStatusFileError(msg)
        self.fd = fd

        try:
            # Reading the lines of the status file
            i = 0
            for line in fd:
                i += 1
                line = line.strip()
                if self.verbose > 4:
                    msg = _("Performing status file line '%s'.") % (line)
                    msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                        % {'file': self.file_name, 'lnr': i})
                    self.logger.debug(msg)

                # check for file heading
                if i == 1:
                    match = re.search(
                        r'^logrotate\s+state\s+-+\s+version\s+([23])$',
                        line, re.IGNORECASE
                    )
                    if match:
                        # Correct file header
                        self.status_version = int(match.group(1))
                        if self.verbose > 1:
                            msg = (_("Idendified version of status file: %d")
                                    % (self.status_version))
                            self.logger.debug(msg)
                        continue
                    else:
                        # Wrong header
                        msg = (_("Incompatible version of status file "
                                 + "'%(file)s': %(header)s")
                                % { 'file': self.file_name, 'header': line })
                        fd.close()
                        raise LogrotateStatusFileError(msg)

                if line == '':
                    continue

                parts = split_parts(line)
                logfile = parts[0]
                rdate   = parts[1]
                if self.verbose > 2:
                    msg = (_("Found logfile '%(file)s' with rotation "
                             + "date '%(date)s'.")
                            % { 'file': logfile, 'date': rdate })
                    self.logger.debug(msg)

                if logfile and rdate:
                    pat = (r'\s*(\d+)[_\-](\d+)[_\-](\d+)' +
                           r'(?:[\s\-_]+(\d+)[_\-:](\d+)[_\-:](\d+))?')
                    match = re.search(pat, rdate)
                    if not match:
                        msg = (_("Could not determine date format: '%s'.")
                                % (rdate))
                        msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                            % {'file': logfile, 'lnr': i})
                        self.logger.warning(msg)
                        continue
                    d = {
                        'Y': int(match.group(1)),
                        'm': int(match.group(2)),
                        'd': int(match.group(3)),
                        'H': 0,
                        'M': 0,
                        'S': 0,
                    }
                    if match.group(4) is not None:
                        d['H'] = int(match.group(4))
                    if match.group(5) is not None:
                        d['M'] = int(match.group(5))
                    if match.group(6) is not None:
                        d['S'] = int(match.group(6))

                    dt = None
                    try:
                        dt = datetime(d['Y'], d['m'], d['d'],
                                      d['H'], d['M'], d['S'],
                                      tzinfo = utc)
                    except ValueError, e:
                        msg = _("Invalid date: '%s'.") % (rdate)
                        msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                        % {'file': logfile, 'lnr': i})
                        self.logger.warning(msg)
                        continue

                    self.file_state[logfile] = dt

                else:

                    msg = (_("Neither a logfile nor a date found " +
                             "in line '%s'.") % (line))
                    msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                        % {'file': logfile, 'lnr': i})
                    self.logger.warning(msg)

        finally:
            fd.close

        self.fd = None
        self.was_read = True

        return True

# =============================================================================

if __name__ == "__main__":
    pass


# =============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
