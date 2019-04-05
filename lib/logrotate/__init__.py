#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: (c) 2010 - 2016 by Frank Brehm, Berlin
@summary: All modules for plogrotate
'''

import os

from pathlib import Path

__author__ = 'Frank Brehm <frank@brehm-online.com>'
__copyright__ = '(C) 2010 - 2016 by Frank Brehm, Berlin'
__contact__ = 'frank@brehm-online.com'
__version__ = '0.9.1'
__license__ = 'GPLv3+'


DEFAULT_CONFIG_FILE = Path(os.sep) / 'etc' / 'plogrotate.conf'
DEFAULT_STATUS_FILE = Path(os.sep) / 'var' / 'lib' / 'logrotate' / 'plogrotate.status'
DEFAULT_PID_FILE = Path(os.sep) / 'run' / 'plogrotate.pid'

# =============================================================================

if __name__ == "__main__":

    pass


# vim: fileencoding=utf-8 filetype=python ts=4
