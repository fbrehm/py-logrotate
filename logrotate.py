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

revision = '$Revision$'
revision = re.sub( r'\$', '', revision )
revision = re.sub( r'Revision: ', r'r', revision )

__author__    = 'Frank Brehm'
__copyright__ = '(C) 2011 by Frank Brehm, Berlin'
__contact__    = 'frank@brehm-online.com'
__version__    = '0.2.0 ' + revision
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

    print _("Options") + ": " + pp.pformat(opt_parser.options)
    print _("Arguments") + ": " + pp.pformat(opt_parser.args)


#========================================================================

if __name__ == "__main__":
    main()


#========================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
