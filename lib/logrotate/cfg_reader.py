#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank@brehm-online.com
@license: GPL3
@copyright: © 2010 - 2019 by Frank Brehm, Berlin
@summary: module the configuration parsing object for Python logrotating
"""
from __future__ import absolute_import, print_function

# Standard modules
import re
import logging
import subprocess
import pprint
import gettext
import copy

from pathlib import Path

# Third party modules
import six

# Own modules
from fb_tools.common import pp, to_str
from fb_tools.obj import FbBaseObjectError, FbBaseObject
from fb_tools.handling_obj import HandlingObject

from . import DEFAULT_CONFIG_FILE
from .translate import XLATOR
from .errors import LogrotateConfigurationError
from .common import split_parts
from .filegroup import LogFileGroup

__version__ = '0.1.1'

_ = XLATOR.gettext
ngettext = XLATOR.ngettext

LOG = logging.getLogger(__name__)


# =============================================================================
class LogrotateConfigReader(HandlingObject):
    '''Class for reading the configuration for Python logrotating'''

    #-------------------------------------------------------
    def __init__(
        self, config_file=DEFAULT_CONFIG_FILE, name=None, simulate=False, quiet=False,
            force=None, appname=None, verbose=0, base_dir=None):
        """
        Constructor.

        @param name: the name of the script as an identifier
        @type name: str
        @param simulate: test mode - no write actions are made
        @type simulate: bool

        @return: None
        """

        self._config_file = None
        self.default_group = None

        super(LogrotateConfigReader, self).__init__(
            appname=appname, verbose=verbose, version=__version__, base_dir=base_dir,
            simulate=simulate, quiet=quiet, force=force)

        self.config_file = config_file

        self._init_default_group()

        self.initialized = True

    # -----------------------------------------------------------------------
    @property
    def config_file(self):
        "The file name of the config file to evaluate."
        return self._config_file

    @config_file.setter
    def config_file(self, value):
        if value is None:
            msg = _("The filename of the config file may not be None.")
            raise LogrotateConfigurationError(msg)
        self._config_file = Path(value)

    # -----------------------------------------------------------------------
    def _init_default_group(self):

        LOG.debug(_("Initializing default file group ..."))

        self.default_group = LogFileGroup(
            appname=self.appname, verbose=self.verbose, base_dir=self.base_dir,
            simulate=self.simulate, is_default=True,
        )

    # -------------------------------------------------------------------------
    def as_dict(self, short=True):
        """
        Transforms the elements of the object into a dict

        @return: structure as dict
        @rtype:  dict
        """

        res = super(LogrotateConfigReader, self).as_dict(short=short)

        res['config_file'] = self.config_file

        return res


#========================================================================

if __name__ == "__main__":
    pass

#========================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
