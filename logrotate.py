#!/usr/bin/env python
# -*- coding: utf-8 -*-

# $Id$
# $URL$

'''
@author: Frank Brehm
@contact: frank@brehm-online.com
@license: GPL3
@copyright: (c) 2010-2011 by Frank Brehm, Berlin
@version: 0.2.0
@summary: rotates and compress system logs
'''

import re
import sys
import pprint
import gettext
import os.path

from LogRotateGetopts import LogrotateOptParser
from LogRotateGetopts import LogrotateOptParserError

from LogRotateHandler import LogrotateHandler
from LogRotateHandler import LogrotateHandlerError

revision = '$Revision$'
revision = re.sub( r'\$', '', revision )
revision = re.sub( r'Revision: ', r'r', revision )

__author__    = 'Frank Brehm'
__copyright__ = '(C) 2011 by Frank Brehm, Berlin'
__contact__    = 'frank@brehm-online.com'
__version__    = '0.2.1 ' + revision
__license__    = 'GPL3'


#-----------------------------------------------------------------
def main():

    basedir = os.path.realpath(os.path.dirname(sys.argv[0]))
    #print "Basedir: %s" % ( basedir )
    local_dir = os.path.join(basedir, 'po')
    if not os.path.isdir(local_dir):
        local_dir = None
    #print "Locale-Dir: %s" % ( local_dir )

    t = gettext.translation('pylogrotate', local_dir, fallback=True)
    _ = t.lgettext
    __ = t.lngettext

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

    if opt_parser.options.verbose > 2:
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

    lr_handler = LogrotateHandler(
        opt_parser.args[0],
        test       = testmode,
        verbose    = verbose_level,
        force      = opt_parser.options.force,
        state_file = opt_parser.options.statefile,
        mail_cmd   = opt_parser.options.mailcmd,
        local_dir  = local_dir,
    )

    if opt_parser.options.verbose > 2:
        print _("Handler object structure") + ': ' + str(lr_handler)

#========================================================================

if __name__ == "__main__":
    main()


#========================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
