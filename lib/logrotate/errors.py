#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@summary: module for some common used error classes
"""
from __future__ import absolute_import

# Standard modules
import errno
import signal
import os

# Third party modules

# Own modules

from fb_tools.obj import FbBaseObjectError
from fb_tools.errors import FbError, FbHandlerError, FbAppError

from .translate import XLATOR

__version__ = '0.2.0'

_ = XLATOR.gettext
ngettext = XLATOR.ngettext


# =============================================================================
class LogrotateError(FbError):
    """ Base error class for all other self defined exceptions."""

    pass


# =============================================================================
class LogrotateObjectError(FbBaseObjectError, LogrotateError):
    """ Base error class useable by all objects. """

    pass

#========================================================================
class LogrotateConfigurationError(LogrotateObjectError):
    """
    Base class for exceptions on reading and evaluating logrotate configuration.
    """
    pass


# =============================================================================
class LogRotateScriptError(LogrotateObjectError):
    "Base class for exceptions in this module."
    pass


# =============================================================================
class ExecutionError(LogRotateScriptError, FbHandlerError):
    "Error raised, if execution of the script was not successful."
    pass


# =============================================================================
class LogrotateStatusFileError(LogrotateObjectError):
    """
    Base class for exceptions in this module.
    """
    pass


# =============================================================================
class LogrotateStatusEntryError(LogrotateObjectError):
    "Exception class for errors with status file entries."
    pass


# =============================================================================
class StatusEntryValueError(LogrotateStatusEntryError, ValueError):
    "Exception class for wrong values on status file entries."
    pass


# =============================================================================
class UnbalancedQuotesError(LogrotateError):
    """Exception class for unbalanced quotes in a text."""

    # -------------------------------------------------------------------------
    def __init__(self, text, quote_char=None):
        """
        Constructor.

        @param text: the text with the unbalanced quotes
        @type text: str
        @param tries: the quoting character
        @type tries: str

        """

        self.text = str(text)
        self.quote_char = quote_char

    # -----------------------------------------------------
    def __str__(self):

        if self.quote_char is None:
            msg = _("Unbalanced quotes in {!r}.").format(self.text)
        else:
            msg = _("Unbalanced quote {what!r} in {where!r}.").format(
                what=self.quote_char, where=self.text)
        return msg


# ========================================================================

if __name__ == "__main__":
    pass

# ========================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
