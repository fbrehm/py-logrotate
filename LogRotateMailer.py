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
@summary: module for a logrotate mailer object to send
          rotated logfiles per mail to a reciepient
'''

import re
import logging
import pprint
import gettext
import os
import os.path
import pwd
import socket

import email.utils

from LogRotateCommon import email_valid

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

class LogRotateMailerError(Exception):
    '''
    Base class for exceptions in this module.
    '''

#========================================================================

class LogRotateMailer(object):
    '''
    Class for a mailer object to send
    rotated logfiles per mail to a reciepient

    @author: Frank Brehm
    @contact: frank@brehm-online.com
    '''

    #-------------------------------------------------------
    def __init__( self, local_dir = None,
                        verbose   = 0,
                        test_mode = False,
    ):
        '''
        Constructor.

        @param local_dir: The directory, where the i18n-files (*.mo)
                          are located. If None, then system default
                          (/usr/share/locale) is used.
        @type local_dir:  str or None
        @param verbose:   verbosity (debug) level
        @type verbose:    int
        @param test_mode: test mode - no write actions are made
        @type test_mode:  bool

        @return: None
        '''

        self.t = gettext.translation(
            'LogRotateMailer',
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

        self.test_mode = test_mode
        '''
        @ivar: test mode - no write actions are made
        @type: bool
        '''

        self.logger = logging.getLogger('pylogrotate.mailer')
        '''
        @ivar: logger object
        @type: logging.getLogger
        '''

        self._sendmail = None
        '''
        @ivar: file name of the sendmail executable
               ('/usr/sbin/sendmail' or '/usr/lib/sendmail')
               used for sending the mails.
               if None, the mails will sended via SMTP
        @type: str or None
        '''
        self._init_sendmail()

        self._from_address = ('me', 'info@uhu-banane.de')
        '''
        @ivar: Mailaddress of the sender, tuple with the real name of
               the sender and his mail address as the second value
        @type: tuple
        '''
        self._init_from_address()

    #------------------------------------------------------------
    # Defintion of some properties

    #------------------------------------------------------------
    # Property 'from'
    def _get_from_address(self):
        '''
        Getter method for property 'from_address'
        '''
        return email.utils.formataddr(self._from_address)

    def _set_from_address(self, value):
        '''
        Setter method for property 'from_address'
        '''
        _ = self.t.lgettext
        if value is None:
            msg = _("The 'From' address may not set to None.")
            raise LogRotateMailerError(msg)
        pair = ('', '')
        if isinstance(value, tuple):
            if len(value) < 2:
                pair = email.utils.parseaddr(value[0])
            else:
                pair = (value[0], value[1])
        else:
            pair = email.utils.parseaddr(value)

        if ( (pair[0] is None or pair[0] == '') and
             (pair[1] is None or pair[1] == '') ):
            msg = _("Invalid mail address given: '%s'.") % (str(value))
            raise LogRotateMailerError(msg)

        if not email_valid(pair[1]):
            msg = _("Invalid mail address given: '%s'.") % (str(value))
            raise LogRotateMailerError(msg)

        self._from_address = pair
        if self.verbose > 3:
            addr = email.utils.formataddr(pair)
            msg = _("Set sender mail address to: '%s'.") % (addr)
            self.logger.debug(msg)

    def _del_from_address(self):
        '''
        Deleter method for property 'from_address'
        '''
        self._init_from_address()

    from_address = property(_get_from_address, _set_from_address, _del_from_address, "The mail address of the sender")

    #------------------------------------------------------------
    # Property 'sendmail'
    def _get_sendmail(self):
        '''
        Getter method for property 'sendmail'
        '''
        return self._sendmail

    def _set_sendmail(self, value):
        '''
        Setter method for property 'sendmail'
        '''
        _ = self.t.lgettext
        if value is None or value == '':
            self._sendmail = None
            return

        if os.path.isabs(value):
            if os.path.exists(value):
                cmd = os.path.normpath(value)
                if os.access(cmd, os.X_OK):
                    msg = _("Using '%s' as the sendmail command.") % (cmd)
                    self.logger.debug(msg)
                    self._sendmail = cmd
                    return
                else:
                    msg = _("No execute permissions to '%s'.") % (cmd)
                    self.logger.warning(msg)
                    return
            else:
                msg = _("Sendmail command '%s' not found.") % (value)
                self.logger.warning(msg)
                return
        else:
            msg = _("Only absolute path allowed for a sendmail command: '%s'.") % (value)
            self.logger.warning(msg)
            return

    def _del_sendmail(self):
        '''
        Deleter method for property 'from_address'
        '''
        self._sendmail = None

    sendmail = property(_get_sendmail, _set_sendmail, _del_sendmail, "The sendmail executable for sending mails local")

    #------------------------------------------------------------
    # Other Methods

    #-------------------------------------------------------
    def __del__(self):
        '''
        Destructor.
        '''

        _ = self.t.lgettext
        if self.verbose > 2:
            msg = _("Mailer script object will destroyed.")
            self.logger.debug(msg)

    #------------------------------------------------------------
    def __str__(self):
        '''
        Typecasting function for translating object structure
        into a string

        @return: structure as string
        @rtype:  str
        '''

        pp = pprint.PrettyPrinter(indent=4)
        structure = self.as_dict()
        return pp.pformat(structure)

    #-------------------------------------------------------
    def as_dict(self):
        '''
        Transforms the elements of the object into a dict

        @return: structure as dict
        @rtype:  dict
        '''

        res = {}
        res['t']         = self.t
        res['verbose']   = self.verbose
        res['test_mode'] = self.test_mode
        res['logger']    = self.logger
        res['sendmail']  = self.sendmail
        res['from']      = self.from_address

        return res

    #-------------------------------------------------------
    def _init_from_address(self):
        '''
        Initialises the sender mail address
        '''

        _ = self.t.lgettext

        cur_user = pwd.getpwuid(os.getuid())[0]
        cur_host = socket.getfqdn()
        addr = cur_user + '@' + cur_host

        if self.verbose > 3:
            msg = _("Using <%s> as the sender mail address.") % (addr)
            self.logger.debug(msg)

        self._from_address = (None, addr)

    #-------------------------------------------------------
    def _init_sendmail(self):
        '''
        Initialises the sendmail with 
        '''

        _ = self.t.lgettext

        progs = [
            os.sep + os.path.join('usr', 'sbin', 'sendmail'),
            os.sep + os.path.join('usr', 'lib', 'sendmail'),
        ]

        if self.verbose > 3:
            msg = _("Initial search for the sendmail executable ...")
            self.logger.debug(msg)

        for prog in progs:

            if self.verbose > 3:
                msg = _("Testing for '%s' ...") % (prog)
                self.logger.debug(msg)

            if os.path.exists(prog):
                if os.access(prog, os.X_OK):
                    if self.verbose > 1:
                            msg = _("Using '%s' as the sendmail command.") % (prog)
                            self.logger.debug(msg)
                    self._sendmail = prog
                    break
                else:
                    msg = _("No execute permissions to '%s'.") % (prog)
                    self.logger.warning(msg)

        return

#========================================================================

if __name__ == "__main__":
    pass


#========================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
