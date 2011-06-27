#!/usr/bin/env python
# -*- coding: utf-8 -*-

# $Id$
# $URL$

'''
@author: Frank Brehm
@contact: frank@brehm-online.com
@license: GPL3
@copyright: (c) 2010-2011 by Frank Brehm, Berlin
@version: 0.0.2
@summary: module for operations with the logrotate state file
'''

import re
import sys
import os
import os.path
import gettext
import logging
import pprint

from datetime import tzinfo, timedelta, datetime, date, time

from LogRotateCommon import split_parts 

revision = '$Revision$'
revision = re.sub( r'\$', '', revision )
revision = re.sub( r'Revision: ', r'r', revision )
revision = re.sub( r'\s*$', '', revision )

__author__    = 'Frank Brehm'
__copyright__ = '(C) 2011 by Frank Brehm, Berlin'
__contact__    = 'frank@brehm-online.com'
__version__    = '0.1.0 ' + revision
__license__    = 'GPL3'

#========================================================================

class LogrotateStatusFileError(Exception):
    '''
    Base class for exceptions in this module.
    '''

#========================================================================

ZERO = timedelta(0)

class UTC(tzinfo):
    """UTC"""

    def utcoffset(self, dt):
        return ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return ZERO

utc = UTC()


#========================================================================

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
                        logger     = None,
    ):
        '''
        Constructor.

        @param file_name: the file name of the status file
        @type file_name:  str
        @param verbose:   verbosity (debug) level
        @type verbose:    int
        @param test_mode: test mode - no write actions are made
        @type test_mode:  bool
        @param logger:    logger object to use for logging a.s.o.
        @type logger:     logging.getLogger or None
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
            'LogRotateStatusFile',
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

        self.logger = logger.getChild('status_file')
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

        if not logger:

            #################################################
            # Create a logger object, if necessary
            self.logger = logging.getLogger('logrotate_state_file')

            self.logger.setLevel(logging.DEBUG)

            pp = pprint.PrettyPrinter(indent=4)
            # create console handler and set level to debug
            ch = logging.StreamHandler()
            #ch.setLevel(logging.DEBUG)
            if verbose:
                ch.setLevel(logging.DEBUG)
            else:
                ch.setLevel(logging.INFO)

            # create formatter
            formatter = logging.Formatter(
                '[%(asctime)s]: %(name)s %(levelname)-8s - %(message)s'
            )

            # add formatter to ch
            ch.setFormatter(formatter)

            # add ch to logger
            self.logger.addHandler(ch)

        # Initial read and check for permissions
        self._read(must_exists = False)
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
        If this logfile is not found in the state file, datetime.min() is given back.

        @param logfile: the logfile to query
        @type logfile:  str

        @return: date of last rotation of this logfile
        @rtype:  datetime
        '''

        if not self.was_read:
            self._read(must_exists = False)

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
        msg = _("Setting rotation date of '%(file)s' to '%(date)s' ...") \
                % {'file': logfile, 'date': date_utc.isoformat(' ') }
        self.logger.debug(msg)

        #self._read(must_exists = False)
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

            msg = _("Open status file '%s' for writing ...") % (self.file_name)
            self.logger.debug(msg)

            # open status file for writing
            if not self.test_mode:
                try:
                    fd = open(self.file_name, 'w')
                except IOError, e:
                    msg = _("Could not open status file '%s' for write: ") % (self.file_name) + str(e)
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
            for logfile in sorted(self.file_state.keys(), lambda x,y: cmp(x.lower(), y.lower())):
                rotate_date = self.file_state[logfile]
                date_str = "%d-%d-%d" % (rotate_date.year, rotate_date.month, rotate_date.day)
                if self.status_version == 3:
                    date_str = ( "%d-%02d-%02d_%02d:%02d:%02d" %
                                (rotate_date.year, rotate_date.month, rotate_date.day,
                                 rotate_date.hour, rotate_date.minute, rotate_date.second))
                line = '%-*s %s' % (max_length, ('"' + logfile + '"'), date_str)
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

        pp = pprint.PrettyPrinter(indent=4)
        return pp.pformat(self.as_dict())

    #------------------------------------------------------------
    def _check_permissions(self):
        '''
        Checks the permissions of the state file and/or his parent directory.
        Throws a LogrotateStatusFileError on a error.

        @return:    success of check
        @rtype:     bool
        '''

        _ = self.t.lgettext
        msg = _("Checking permissions of status file '%s' ...") % (self.file_name)
        self.logger.debug(msg)

        if os.path.exists(self.file_name):
            # Check for write access to the status file
            if os.access(self.file_name, os.W_OK):
                msg = _("Access to status file '%s' is OK.") % (self.file_name)
                self.logger.debug(msg)
                return True
            else:
                msg = _("No write access to status file '%s'.") % (self.file_name)
                if self.test_mode:
                    self.logger.error(msg)
                else:
                    raise LogrotateStatusFileError(msg)
                return False

        parent_dir = os.path.dirname(self.file_name)
        msg = _("Checking permissions of parent directory '%s' ...") % (parent_dir)
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
            msg = _("Parent directory '%(dir)s' of status file '%(file)s' is not a directory.") \
                    % {'dir': parent_dir, 'file': self.file_name }
            if self.test_mode:
                self.logger.error(msg)
            else:
                raise LogrotateStatusFileError(msg)
            return False

        # Check for write access to parent dir
        if not os.access(parent_dir, os.W_OK):
            msg = _("No write access to parent directory '%(dir)s' of status file '%(file)s'.") \
                    % {'dir': parent_dir, 'file': self.file_name }
            if self.test_mode:
                self.logger.error(msg)
            else:
                raise LogrotateStatusFileError(msg)
            return False

        msg = _("Permissions to parent directory '%s' are OK.") % (parent_dir)
        self.logger.debug(msg)
        return True

    #-------------------------------------------------------
    def _read(self, must_exists = True):
        '''
        Reads the status file and put the results in the dict self.file_state.
        Puts back the absolute path of the status file in self.file_name on success.

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
                msg = _("Absolute path of status file is now '%s'.") % (self.file_name)
                self.logger.debug(msg)

        # Checks, that the status file is a regular file
        if not os.path.isfile(self.file_name):
            msg = _("Status file '%s' is not a regular file.") % (self.file_name)
            raise LogrotateStatusFileError(msg)
            return False

        msg = _("Reading status file '%s' ...") % (self.file_name)
        self.logger.debug(msg)

        fd = None
        try:
            fd = open(self.file_name, 'Ur')
        except IOError, e:
            msg = _("Could not read status file '%s': ") % (self.file_name) + str(e)
            raise LogrotateStatusFileError(msg)
        self.fd = fd

        try:
            # Reading the lines of the status file
            i = 0
            for line in fd:
                i += 1
                line = line.strip()
                if self.verbose > 4:
                    msg = _("Performing status file line '%(line)s' (file: '%(file)s', row: %(row)d)") \
                            % {'line': line, 'file': self.file_name, 'row': i, }
                    self.logger.debug(msg)

                # check for file heading
                if i == 1:
                    match = re.search(r'^logrotate\s+state\s+-+\s+version\s+([23])$', line, re.IGNORECASE)
                    if match:
                        # Correct file header
                        self.status_version = int(match.group(1))
                        if self.verbose > 1:
                            msg = _("Idendified version of status file: %d") % (self.status_version)
                            self.logger.debug(msg)
                        continue
                    else:
                        # Wrong header
                        msg = _("Incompatible version of status file '%(file)s': %(header)s") \
                                % { 'file': self.file_name, 'header': line }
                        fd.close()
                        raise LogrotateStatusFileError(msg)

                if line == '':
                    continue

                parts = split_parts(line)
                logfile = parts[0]
                rdate   = parts[1]
                if self.verbose > 2:
                    msg = _("Found logfile '%(file)s' with rotation date '%(date)s'.") \
                            % { 'file': logfile, 'date': rdate }
                    self.logger.debug(msg)

                if logfile and rdate:
                    match = re.search(r'\s*(\d+)[_\-](\d+)[_\-](\d+)(?:[\s\-_]+(\d+)[_\-:](\d+)[_\-:](\d+))?', rdate)
                    if not match:
                        msg = _("Could not determine date format: '%(date)s' (file: '%(file)s', row: %(row)d)") \
                                % {'date': rdate, 'file': logfile, 'row': i, }
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
                        dt = datetime(d['Y'], d['m'], d['d'], d['H'], d['M'], d['S'], tzinfo = utc)
                    except ValueError, e:
                        msg = _("Invalid date: '%(date)s' (file: '%(file)s', row: %(row)d)") \
                                % {'date': rdate, 'file': logfile, 'row': i, }
                        self.logger.warning(msg)
                        continue

                    self.file_state[logfile] = dt

                else:

                    msg = _("Neither a logfile nor a date found in line '%(line)s' (file: '%(file)s', row: %(row)d)") \
                            % {'line': line, 'file': logfile, 'row': i, }
                    self.logger.warning(msg)

        finally:
            fd.close

        self.fd = None
        self.was_read = True

        return True

#========================================================================

if __name__ == "__main__":
    pass


#========================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
