#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank@brehm-online.com
@license: GPL3
@copyright: © 2010 - 2016 by Frank Brehm, Berlin
@summary: Module for BaseObject class
"""

# Standard modules
import re
import os
import sys
import locale
import logging
import gettext
import pprint

# Third party modules
import six

# Own modules
from logrotate.common import logrotate_gettext, logrotate_ngettext

__version__ = '0.1.0'

log = logging.getLogger(__name__)

_ = logrotate_gettext
__ = logrotate_ngettext


# =============================================================================
class BaseObjectError(PbError):
    """
    Base error class useable by all descendand objects.
    """
    pass


# =============================================================================
class BaseObject(object):
    """
    Base class for all objects.
    """

    # -------------------------------------------------------------------------
    def __init__(
        self, appname=None, verbose=0, version=__version__, base_dir=None):
        """
        Initialisation of the base object.

        Raises an exception on a uncoverable error.

        @param appname: name of the current running application
        @type appname: str
        @param verbose: verbose level
        @type verbose: int
        @param version: the version string of the current object or application
        @type version: str
        @param base_dir: the base directory of all operations
        @type base_dir: str

        @return: None
        """

        self._appname = None
        """
        @ivar: name of the current running application
        @type: str
        """
        if appname:
            v = str(appname).strip()
            if v:
                self._appname = v
        if not self._appname:
            self._appname = os.path.basename(sys.argv[0])

        self._version = version
        """
        @ivar: version string of the current object or application
        @type: str
        """

        self._verbose = int(verbose)
        """
        @ivar: verbosity level (0 - 9)
        @type: int
        """
        if self._verbose < 0:
            msg = _("Wrong verbose level %r, must be >= 0") % (verbose)
            raise ValueError(msg)

        self._base_dir = base_dir
        """
        @ivar: base directory used for different purposes, must be an existent
               directory. Defaults to directory of current script daemon.py.
        @type: str
        """
        if base_dir:
            if not os.path.exists(base_dir):
                msg = _("Base directory %r does not exists.") % (base_dir)
                self.handle_error(msg)
                self._base_dir = None
            elif not os.path.isdir(base_dir):
                msg = _("Base directory %r is not a directory.") % (base_dir)
                self.handle_error(msg)
                self._base_dir = None
        if not self._base_dir:
            self._base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

    # -----------------------------------------------------------
    @property
    def appname(self):
        """The name of the current running application."""
        return self._appname

    @appname.setter
    def appname(self, value):
        if value:
            v = str(value).strip()
            if v:
                self._appname = v

    # -----------------------------------------------------------
    @property
    def version(self):
        """The version string of the current object or application."""
        return self._version

    # -----------------------------------------------------------
    @property
    def verbose(self):
        """The verbosity level."""
        return getattr(self, '_verbose', 0)

    @verbose.setter
    def verbose(self, value):
        v = int(value)
        if v >= 0:
            self._verbose = v
        else:
            log.warn(_("Wrong verbose level %r, must be >= 0"), value)

    # -----------------------------------------------------------
    @property
    def base_dir(self):
        """The base directory used for different purposes."""
        return self._base_dir

    @base_dir.setter
    def base_dir(self, value):
        if value.startswith('~'):
            value = os.path.expanduser(value)
        if not os.path.exists(value):
            msg = _("Base directory %r does not exists.") % (value)
            log.error(msg)
        elif not os.path.isdir(value):
            msg = _("Base directory %r is not a directory.") % (value)
            log.error(msg)
        else:
            self._base_dir = value

    # -------------------------------------------------------------------------
    def __repr__(self):
        """Typecasting into a string for reproduction."""

        out = "<%s(" % (self.__class__.__name__)

        fields = []
        fields.append("appname=%r" % (self.appname))
        fields.append("verbose=%r" % (self.verbose))
        fields.append("version=%r" % (self.version))
        fields.append("base_dir=%r" % (self.base_dir))

        out += ", ".join(fields) + ")>"
        return out

    # -------------------------------------------------------------------------
    def as_dict(self):
        """
        Transforms the elements of the object into a dict

        @return: structure as dict
        @rtype:  dict
        """

        res = self.__dict__
        res = {}
        for key in self.__dict__:
            if key.startswith('_') and not key.startswith('__'):
                continue
            val = self.__dict__[key]
            if isinstance(val, BaseObject):
                res[key] = val.as_dict()
            else:
                res[key] = val
        res['__class_name__'] = self.__class__.__name__
        res['appname'] = self.appname
        res['version'] = self.version
        res['verbose'] = self.verbose
        res['base_dir'] = self.base_dir

        return res

# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
