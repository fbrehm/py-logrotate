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

# Standard modules
import re
import logging
import pprint
import gettext
import os
import os.path
import sys
import pwd
import socket
import csv

from datetime import datetime
from subprocess import Popen, PIPE

import mimetypes
import email.utils
from email import encoders
from email.message import Message
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.nonmultipart import MIMENonMultipart
from email.mime.text import MIMEText

from quopri import encodestring as _encodestring

# Third party modules

# Own modules
try:
    import LogRotate.Common
except ImportError:
    sys.path.append(os.path.abspath(os.path.join(sys.path[0], '..')))
    import LogRotate.Common

from LogRotate.Common import email_valid

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
                        mailer_version = None,
    ):
        '''
        Constructor.

        @param local_dir:      The directory, where the i18n-files (*.mo)
                               are located. If None, then system default
                               (/usr/share/locale) is used.
        @type local_dir:       str or None
        @param verbose:        verbosity (debug) level
        @type verbose:         int
        @param test_mode:      test mode - no write actions are made
        @type test_mode:       bool
        @param mailer_version: version of the X-Mailer tag in the mail header
        @type mailer_version:  str

        @return: None
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

        self._use_smtp = False
        '''
        @ivar: flag, whether SMTP should used
        @type: bool
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

        self._smtp_host = 'localhost'
        '''
        @ivar: the hostname to use for SMTP (smarthost), if no
               sendmail binary was found
        @type: str
        '''

        self._smtp_port = 25
        '''
        @ivar: the port to use for SMTP to the smarthost
        @type: int
        '''

        self._smtp_tls  = False
        '''
        @ivar: use TLS for sending via SMTP to smarthost
        @type: bool
        '''

        self.smtp_user = None
        '''
        @ivar: Authentication username for SMTP
        @type: str or None
        '''

        self.smtp_passwd = None
        '''
        @ivar: Authentication password for SMTP
        @type: str or None
        '''

        self.mailer_version = __version__
        '''
        @ivar: version of the X-Mailer tag in the mail header
        @type: str
        '''
        if mailer_version is not None:
            self.mailer_version = mailer_version

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

    from_address = property(
            _get_from_address,
            _set_from_address,
            _del_from_address,
            "The mail address of the sender"
    )

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
            msg = (_("Only absolute path allowed for a " +
                     "sendmail command: '%s'.") % (value))
            self.logger.warning(msg)
            return

    def _del_sendmail(self):
        '''
        Deleter method for property 'from_address'
        '''
        self._sendmail = None

    sendmail = property(
            _get_sendmail,
            _set_sendmail,
            _del_sendmail,
            "The sendmail executable for sending mails local"
    )

    #------------------------------------------------------------
    # Property 'smtp_host'
    def _get_smtp_host(self):
        '''
        Getter method for property 'smtp_host'
        '''
        return self._smtp_host

    def _set_smtp_host(self, value):
        '''
        Setter method for property 'smtp_host'
        '''
        _ = self.t.lgettext
        if value:
            self._smtp_host = value
            self.use_smtp = True

    smtp_host = property(
            _get_smtp_host,
            _set_smtp_host,
            None,
            "The hostname to use for sending mails via SMTP (smarthost)"
    )

    #------------------------------------------------------------
    # Property 'smtp_port'
    def _get_smtp_port(self):
        '''
        Getter method for property 'smtp_port'
        '''
        return self._smtp_port

    def _set_smtp_port(self, value):
        '''
        Setter method for property 'smtp_port'
        '''
        _ = self.t.lgettext
        if value:
            port = 25
            try:
                port = int(value)
            except ValueError, e:
                return
            if port < 1 or port >= 2**15:
                return
            self._smtp_port = port

    smtp_port = property(
            _get_smtp_port,
            _set_smtp_port,
            None,
            "The port to use for sending mails via SMTP"
    )

    #------------------------------------------------------------
    # Property 'smtp_tls'
    def _get_smtp_tls(self):
        '''
        Getter method for property 'smtp_tls'
        '''
        return self._smtp_tls

    def _set_smtp_tls(self, value):
        '''
        Setter method for property 'smtp_tls'
        '''
        self._smtp_tls = bool(value)

    smtp_tls = property(
            _get_smtp_tls,
            _set_smtp_tls,
            None,
            "Use TLS for sending mails via SMTP (smarthost)"
    )

    #------------------------------------------------------------
    # Property 'use_smtp'
    def _get_use_smtp(self):
        '''
        Getter method for property 'use_smtp'
        '''
        return self._use_smtp

    def _set_use_smtp(self, value):
        '''
        Setter method for property 'use_smtp'
        '''
        self._use_smtp = bool(value)

    use_smtp = property(
            _get_use_smtp,
            _set_use_smtp,
            None,
            "Use SMTP for sending mails instead of using sendmail"
    )

    #------------------------------------------------------------
    # Other Methods

    #-------------------------------------------------------
    def __del__(self):
        '''
        Destructor.
        '''

        _ = self.t.lgettext
        if self.verbose > 2:
            msg = _("Mailer object will destroyed.")
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
        res['t']              = self.t
        res['verbose']        = self.verbose
        res['test_mode']      = self.test_mode
        res['logger']         = self.logger
        res['sendmail']       = self.sendmail
        res['from']           = self.from_address
        res['smtp_host']      = self.smtp_host
        res['smtp_port']      = self.smtp_port
        res['smtp_tls']       = self.smtp_tls
        res['smtp_user']      = self.smtp_user
        res['smtp_passwd']    = self.smtp_passwd
        res['mailer_version'] = self.mailer_version
        res['use_smtp']       = self.use_smtp

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

        if not self.sendmail:
            self.use_smtp = True

        return

    #-------------------------------------------------------
    def send_file(
            self,
            filename,
            addresses,
            original=None,
            mime_type='text/plain',
            rotate_date=None,
            charset=None
            ):
        '''
        Mails the file with the given file name as an attachement
        to the given recipient(s).

        Raises a LogRotateMailerError on harder errors.

        @param filename:  The file name of the file to send (the existing,
                          rotated and maybe compressed logfile).
        @type filename:   str
        @param addresses: A list of tuples of a pair in the form
                          of the return value of email.utils.parseaddr()
        @type addresses:  list
        @param original:  The file name of the original (unrotated) logfile for
                          informational purposes.
                          If not given, filename is used instead.
        @type original:   str or None
        @param mime_type: MIME type (content type) of the original logfile,
                          defaults to 'text/plain'
        @type mime_type:  str
        @param rotate_date: datetime object of rotation, defaults to now()
        @type rotate_date:  datetime or None
        @param charset: character set of (uncompreesed) logfile, if the
                        mime_type is 'text/plain', defaults to 'utf-8'
        @type charset:  str or None

        @return: success of sending
        @rtype:  bool
        '''

        _ = self.t.lgettext

        if not os.path.exists(filename):
            msg = _("File '%s' doesn't exists.") % (filename)
            self.logger.error(msg)
            return False

        if not os.path.isfile(filename):
            msg = _("File '%s' is not a regular file.") % (filename)
            self.logger.warning(msg)
            return False

        basename = os.path.basename(filename)
        if not original:
            original = os.path.abspath(filename)

        if not rotate_date:
            rotate_date = datetime.now()

        msg = (_("Sending mail with attached file '%(file)s' to: %(rcpt)s")
                % {'file': basename,
                   'rcpt': ', '.join(
                                map(lambda x: ('"' +
                                                email.utils.formataddr(x) +
                                                '"'),
                                    addresses
                                )
                            )
                  })
        self.logger.debug(msg)

        mail_container = MIMEMultipart()
        mail_container['Subject'] = ( "Rotated logfile '%s'" % (filename) )
        mail_container['X-Mailer'] = ( "pylogrotate version %s"
                        % (self.mailer_version) )
        mail_container['From'] = self.from_address
        mail_container['To'] = ', '.join(
            map(lambda x: email.utils.formataddr(x), addresses)
        )
        mail_container.preamble = (
            'You will not see this in a MIME-aware mail reader.\n'
        )

        # Generate Text of the first part of mail body
        mailtext = "Rotated Logfile:\n\n"
        mailtext += "\t - " + filename + "\n"
        mailtext += "\t   (" + original + ")\n"
        mailtext += "\n"
        mailtext += "Date of rotation: " + rotate_date.isoformat(' ')
        mailtext += "\n"
        mailtext = _encodestring(mailtext, quotetabs=False)
        mail_part = MIMENonMultipart(
                'text',
                'plain',
                charset=sys.getdefaultencoding()
        )
        mail_part.set_payload(mailtext)
        mail_part['Content-Transfer-Encoding'] = 'quoted-printable'
        mail_container.attach(mail_part)

        ctype, encoding = mimetypes.guess_type(filename)
        if self.verbose > 3:
            msg = (_("Guessed content-type: '%(ctype)s' " +
                     "and encoding '%(encoding)s'.")
                    % {'ctype': ctype, 'encoding': encoding })
            self.logger.debug(msg)

        if encoding:
            if encoding == 'gzip':
                ctype = 'application/x-gzip'
            elif encoding == 'bzip2':
                ctype = 'application/x-bzip2'
            else:
                ctype = 'application/octet-stream'

        if not ctype:
            ctype = mime_type

        maintype, subtype = ctype.split('/', 1)
        fp = open(filename, 'rb')
        mail_part = MIMEBase(maintype, subtype)
        mail_part.set_payload(fp.read())
        fp.close()
        if maintype == 'text':
            msgtext = mail_part.get_payload()
            msgtext =  _encodestring(msgtext, quotetabs=False)
            mail_part.set_payload(msgtext)
            mail_part['Content-Transfer-Encoding'] = 'quoted-printable'
        else:
            encoders.encode_base64(mail_part)
        mail_part.add_header(
                'Content-Disposition',
                'attachment',
                filename=basename
        )
        mail_container.attach(mail_part)

        composed = mail_container.as_string()
        if self.verbose > 4:
            msg = _("Generated E-mail:") + "\n" + composed
            self.logger.debug(msg)

        if (not self.use_smtp) and self.sendmail:
            return self._send_per_sendmail(composed)
        else:
            msg = _("Sending mails via SMTP currently not possible.")
            self.logger.info(msg)
            return False

        return True

    #-------------------------------------------------------
    def _send_per_sendmail(self, mail):
        '''
        Sending the given mail per sendmail executable.

        Raises a LogRotateMailerError on harder errors.

        @param mail: the complete mail (header and body) as a string
        @type mail:  str

        @return: success of sending
        @rtype:  bool
        '''

        _ = self.t.lgettext

        if not self.sendmail:
            msg = _("There is no sendmail executable available.")
            raise LogRotateMailerError(msg)
            return False

        args = []
        args.append(self.sendmail)
        args.append('-t')

        msg = (_("Executing command: '%s'.") % (self.sendmail + " -t"))
        self.logger.debug(msg)

        if self.test_mode:
            return True

        try:
            sm = Popen(args, stdin=PIPE, stdout=PIPE,
                       stderr=PIPE, close_fds=False)
            stdout_data = None
            stderr_data = None
            (stdout_data, stderr_data) = sm.communicate(mail)
            returncode = sm.wait()

            if self.verbose > 1:
                msg = _("Got returncode: '%s'.") % (returncode)
                self.logger.debug(msg)

                msg = ''
                if stdout_data:
                    msg = _("Output on STDOUT: '%s'.") % (stdout_data)
                else:
                    msg = _("No output on %s.") % ('STDOUT')
                self.logger.debug(msg)

            if stderr_data:
                msg = ((_("Error message of '%s':") % (self.sendmail)) +
                        "\n" + stderr_data)
                self.logger.warning(msg)
            else:
                if self.verbose > 1:
                    msg = _("No output on %s.") % ('STDERR')
                    self.logger.debug(msg)

            if returncode < 0:
                msg = _("Child was terminated by signal %d.") % (-returncode)
                self.logger.error(msg)
                return False

            if returncode != 0:
                return False

            return True

        except OSError, e:
            msg = _("Execution failed: %s") % (str(e))
            self.logger.error(msg)
            return False

        return False

#========================================================================

if __name__ == "__main__":
    pass


#========================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
