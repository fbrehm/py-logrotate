#!/usr/bin/env python
# -*- coding: utf-8 -*-

# $Id$
# $URL$

'''
@author: Frank Brehm
@contact: frank@brehm-online.com
@license: GPL3
@copyright: (c) 2010-2011 by Frank Brehm, Berlin
@version: 0.6.0
@summary: rotates and compress system logs
'''

import re
import sys
import pprint
import gettext
import os
import os.path
from datetime import datetime

from LogRotate.Getopts import LogrotateOptParser
from LogRotate.Getopts import LogrotateOptParserError

from LogRotate.Handler import LogrotateHandler
from LogRotate.Handler import LogrotateHandlerError

import LogRotate.Common

revision = '$Revision$'
revision = re.sub( r'\$', '', revision )
revision = re.sub( r'Revision: ', r'r', revision )

__author__    = 'Frank Brehm'
__copyright__ = '(C) 2011 by Frank Brehm, Berlin'
__contact__    = 'frank@brehm-online.com'
__version__    = '0.6.0 ' + revision
__license__    = 'GPL3'


#-----------------------------------------------------------------
def main():

    # unbuffered output to stdout
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

    basedir = os.path.realpath(os.path.dirname(sys.argv[0]))
    #print "Basedir: %s" % ( basedir )
    local_dir = os.path.join(basedir, 'po')
    if not os.path.isdir(local_dir):
        local_dir = None
    #print "Locale-Dir: %s" % ( local_dir )

    LogRotate.Common.locale_dir = local_dir

    t = gettext.translation('pylogrotate', local_dir, fallback=True)
    _ = t.lgettext
    __ = t.lngettext

    cur_proc = sys.argv[0]

    opt_parser = LogrotateOptParser(
        prog      = "logrotate",
        version   = __version__,
        local_dir = local_dir,
    )
    pp = pprint.PrettyPrinter(indent=4)
    try:
        opt_parser.getOpts()
    except LogrotateOptParserError, e:
        sys.stderr.write(str(e) + "\n\n")
        opt_parser.parser.print_help(sys.stderr)
        sys.exit(1)

    if opt_parser.options.verbose > 6:
        print _("Options") + ": " + pp.pformat(opt_parser.options)
        print _("Arguments") + ": " + pp.pformat(opt_parser.args)

    testmode = False
    if opt_parser.options.test or opt_parser.options.configcheck:
        testmode = True

    verbose_level = opt_parser.options.verbose

    if opt_parser.options.debug:
        testmode = True
        if verbose_level < 1:
            verbose_level = 1

    if not testmode:
        print "\n" + ('#' * 79)
        print ( _("[%(date)s]: %(prog)s is starting logrotation.") 
              % {'prog': cur_proc, 'date': datetime.now().isoformat(' '), }
              ) + "\n"

    sep_line = '=' * 79

    if testmode:
        print _("Test mode is ON.")
    if verbose_level > 0:
        print (_("Verbose mode is ON on level: %d") % (verbose_level))
    if opt_parser.options.force:
        print _("Force mode is ON.")
    if opt_parser.options.configcheck:
        print _("Configuration check only.")

    if not opt_parser.options.configcheck:
        print ""
        if verbose_level > 0:
            print sep_line + "\n"
        print _("Stage 1: reading configuration") + "\n"

    lr_handler = None
    try:
        lr_handler = LogrotateHandler(
            opt_parser.args[0],
            test         = testmode,
            verbose      = verbose_level,
            force        = opt_parser.options.force,
            config_check = opt_parser.options.configcheck,
            state_file   = opt_parser.options.statefile,
            pid_file     = opt_parser.options.pidfile,
            mail_cmd     = opt_parser.options.mailcmd,
            local_dir    = local_dir,
            version      = __version__,
        )
    except LogrotateHandlerError, e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(9)

    if opt_parser.options.verbose > 2:
        print _("Handler object structure") + ':\n' + str(lr_handler)

    if opt_parser.options.configcheck:
        sys.exit(0)

    print ""
    if verbose_level > 0:
        print sep_line + "\n"
    print _("Stage 2: underlying log rotation") + "\n"
    lr_handler.rotate()

    print ""
    if verbose_level > 0:
        print sep_line + "\n"
    print _("Stage 3: sending logfiles per mail") + "\n"
    lr_handler.send_logfiles()

    print ""
    if verbose_level > 0:
        print sep_line + "\n"
    print _("Stage 4: deleting of old logfiles") + "\n"
    lr_handler.delete_oldfiles()

    print ""
    if verbose_level > 0:
        print sep_line + "\n"
    print _("Stage 5: compression of old log files") + "\n"
    lr_handler.compress()

    lr_handler = None

    if not testmode:
        print ""
        print ( _("[%(date)s]: %(prog)s ended logrotation.") 
              % {'prog': cur_proc, 'date': datetime.now().isoformat(' '), }
              ) + "\n"

    sys.exit(0)

#========================================================================

if __name__ == "__main__":
    main()


#========================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
