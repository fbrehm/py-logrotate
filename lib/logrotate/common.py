#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank@brehm-online.com
@license: GPL3
@copyright: © 2010 - 2016 by Frank Brehm, Berlin
@summary: Module for common used functions
"""

# Standard modules
import re
import os
import sys
import locale
import logging
import gettext
import csv
import pprint
import email.utils

# Third party modules
import six

# Own modules

basedir = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..'))
locale_dir = os.path.join(basedir, 'po')
if not os.path.isdir(locale_dir):
    locale_dir = None

translator = gettext.translation('plogrotate', locale_dir, fallback=True)

__version__ = '0.3.1'

RE_WS = re.compile(r'\s+')
RE_WS_ONLY = re.compile(r'^\s*$')

RE_BS_SQ = re.compile(r"\\'")
RE_SINGLE_QUOTED = re.compile(r"^'((?:\\'|[^'])*)'")

RE_BS_DQ = re.compile(r'\\"')
RE_DOUBLE_QUOTED = re.compile(r'^"((?:\\"|[^"])*)"')

RE_UNQUOTED = re.compile(r'^((?:[^\s\'"]+|\\\'|\\")+)')
RE_UNBALANCED_QUOTE = re.compile(r'^(?P<chunk>(?P<quote>[\'"]).*)\s*')

RE_EMAIL = re.compile(
    r'^[a-z0-9._%-+]+@[a-z0-9._%-]+\.[a-z]{2,12}$',
    re.IGNORECASE)

RE_YES = re.compile(r'^\s*(?:y(?:es)?|true|on)\s*$', re.IGNORECASE)
RE_NO = re.compile(r'^\s*(?:no?|false|off)\s*$', re.IGNORECASE)


# =============================================================================
def logrotate_gettext(message):
    if six.PY3:
        return to_str_or_bust(translator.gettext(message))
    else:
        return to_str_or_bust(translator.lgettext(message))


# =============================================================================
def logrotate_ngettext(singular, plural, n):
    if six.PY3:
        return to_str_or_bust(translator.ngettext(singular, plural, n))
    else:
        return to_str_or_bust(translator.lngettext(singular, plural, n))


_ = logrotate_gettext
__ = logrotate_ngettext

logger = logging.getLogger(__name__)
locale_dir = None


# =============================================================================
class UnbalancedQuotesError(Exception):
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
            msg = "Unbalanced quotes in %r." % (self.text)
        else:
            msg = "Unbalanced quote %r in %r." % (self.quote_char, self.text)
        return msg


# =============================================================================
def pp(value):
    """
    Returns a pretty print string of the given value.

    @return: pretty print string
    @rtype: str
    """

    pretty_printer = pprint.PrettyPrinter(indent=4)
    return pretty_printer.pformat(value)


# =============================================================================
def split_parts(text, keep_quotes=False, raise_on_unbalanced=True):
    """
    Split the given text in chunks by whitespaces or
    single or double quoted strings.

    @param text: the text to split in chunks
    @type text: str
    @param keep_quotes: keep quotes of quoted chunks
    @type keep_quotes: bool
    @param raise_on_unbalanced: raise an exception on unbalanced quotes
    @type raise_on_unbalanced: bool

    @return: list of chunks
    @rtype: list
    """

    chunks = []
    if text is None:
        return chunks

    txt = str(text)
    last_chunk = ''

    # Big loop to split the text - until it is empty
    while txt != '':

        # add chunk, if there is a chunk left and a whitspace
        # at the begin of the line
        match = RE_WS.search(txt)
        if (last_chunk != '') and match:
            chunks.append(last_chunk)
            last_chunk = ''

        # clean the line
        txt = txt.strip()
        if txt == '':
            break

        # search for a single quoted string at the begin of the line
        match = RE_SINGLE_QUOTED.search(txt)
        if match:
            chunk = match.group(1)
            chunk = RE_BS_SQ.sub("'", chunk)
            if keep_quotes:
                chunk = "'" + chunk + "'"
            last_chunk += chunk
            txt = RE_SINGLE_QUOTED.sub("", txt)
            continue

        # search for a double quoted string at the begin of the line
        match = RE_DOUBLE_QUOTED.search(txt)
        if match:
            chunk = match.group(1)
            chunk = RE_BS_DQ.sub('"', chunk)
            if keep_quotes:
                chunk = '"' + chunk + '"'
            last_chunk += chunk
            txt = RE_DOUBLE_QUOTED.sub("", txt)
            continue

        # search for unquoted, whitespace delimited text
        # at the begin of the line
        match = RE_UNQUOTED.search(txt)
        if match:
            last_chunk += match.group(1)
            txt = RE_UNQUOTED.sub("", txt)
            continue

        # Only whitespaces left
        if RE_WS_ONLY.search(txt):
            break

        # Check for unbalanced quotes
        match = RE_UNBALANCED_QUOTE.search(txt)
        if match:
            chunk = match.group('chunk')
            quote_char = match.group('quote')
            if raise_on_unbalanced:
                raise UnbalancedQuotesError(text, quote_char)
            last_chunk += chunk
            txt = RE_UNBALANCED_QUOTE.sub("", txt)
            continue

        # Here we should not come to ...
        msg = "Broken split of %r: %r left." % (text, txt)
        raise Exception(msg)

    if last_chunk != '':
        chunks.append(last_chunk)

    return chunks


# =============================================================================
def email_valid(address):
    """
    Simple Check for E-Mail addresses

    @param address: the mail address to check
    @type address: str

    @return: Validity of the given mil address
    @rtype: bool
    """

    if address is None:
        return False

    adr = str(address)
    if adr is None or adr == '':
        return False

    if RE_EMAIL.search(adr):
        return True
    return False


# =============================================================================
def human2bytes(value, si_conform=True, use_locale_radix=False, as_float=False, verbose=0):
    """
    Converts the given human readable byte value (e.g. 5MB, 8.4GiB etc.)
    with a suffix into an integer/long value (without a suffix).
    It raises a ValueError on invalid values.

    Available prefixes are:
        - kB (1000), KB (1024), KiB (1024)
        - MB (1000*1000), MiB (1024*1024)
        - GB (1000³), GiB (1024³)
        - TB (1000^4), TiB (1024^4)
        - PB (1000^5), PiB (1024^5)
        - EB (1000^6), EiB (1024^6)
        - ZB (1000^7), ZiB (1024^7)

    @param value: the value to convert
    @type value: str
    @param si_conform: use factor 1000 instead of 1024 for kB a.s.o.
    @type si_conform: bool
    @param use_locale_radix: use the locale version of radix instead of the english decimal dot.
    @type use_locale_radix: bool
    @param verbose: level of verbosity
    @type verbose: int

    @return: amount of bytes
    @rtype: int (or long in Python2)
    """

    if value is None:
        msg = "Given value is None."
        raise ValueError(msg)

    radix = '.'
    thousep = ','
    if use_locale_radix:
        radix = locale.nl_langinfo(locale.RADIXCHAR)
        thousep = locale.nl_langinfo(locale.THOUSEP)
    radix = re.escape(radix)
    thousep = re.escape(thousep)
    if verbose > 4:
        logger.debug(_("Using radix %(radix)r, thousend separator %(sep)r") % {
            'radix': radix, 'sep': thousep})

    value_raw = ''
    value_pre = value
    suffix = None

    if thousep:
        value_pre = re.sub(thousep, '', value)
        if verbose > 3:
            logger.debug(_("Value without thousend separators: %r."), value_pre)

    pattern = r'^\s*\+?(\d+(?:' + radix + r'\d*)?)\s*(\S+)?'
    match = re.search(pattern, value_pre)
    if match is not None:
        value_raw = match.group(1)
        suffix = match.group(2)
    else:
        msg = _("Could not determine bytes in %r.") % (value)
        raise ValueError(msg)

    if use_locale_radix:
        value_raw = re.sub(radix, '.', value_raw, 1)
    value_float = float(value_raw)
    value_long = 0
    if six.PY2:
        value_long = long(value_float)
    else:
        value_long = int(value_float)
    if suffix is None:
        suffix = ''
    if verbose > 4:
        logger.debug(
            "Value float: %r, Value long: %r, suffix: %r",
            value_float, value_long, suffix)

    factor_bin = 1024
    factor_si = 1000
    factor = 1
    if six.PY2:
        factor_bin = long(1024)
        factor_si = long(1000)
        factor = long(1)
    if not si_conform:
        factor_si = factor_bin

    if re.search(r'^\s*(?:b(?:yte)?)?\s*$', suffix, re.IGNORECASE):
        factor = 1
        if six.PY2:
            factor = long(1)
    elif re.search(r'^\s*k(?:[bB](?:[Yy][Tt][Ee])?)?\s*$', suffix):
        factor = factor_si
    elif re.search(r'^\s*Ki?(?:[bB](?:[Yy][Tt][Ee])?)?\s*$', suffix):
        factor = factor_bin
    elif re.search(r'^\s*M(?:B(?:yte)?)?\s*$', suffix, re.IGNORECASE):
        factor = factor_si ** 2
    elif re.search(r'^\s*MiB(?:yte)?\s*$', suffix, re.IGNORECASE):
        factor = factor_bin ** 2
    elif re.search(r'^\s*G(?:B(?:yte)?)?\s*$', suffix, re.IGNORECASE):
        factor = factor_si ** 3
    elif re.search(r'^\s*GiB(?:yte)?\s*$', suffix, re.IGNORECASE):
        factor = factor_bin ** 3
    elif re.search(r'^\s*T(?:B(?:yte)?)?\s*$', suffix, re.IGNORECASE):
        factor = factor_si ** 4
    elif re.search(r'^\s*TiB(?:yte)?\s*$', suffix, re.IGNORECASE):
        factor = factor_bin ** 4
    elif re.search(r'^\s*P(?:B(?:yte)?)?\s*$', suffix, re.IGNORECASE):
        factor = factor_si ** 5
    elif re.search(r'^\s*PiB(?:yte)?\s*$', suffix, re.IGNORECASE):
        factor = factor_bin ** 5
    elif re.search(r'^\s*E(?:B(?:yte)?)?\s*$', suffix, re.IGNORECASE):
        factor = factor_si ** 6
    elif re.search(r'^\s*EiB(?:yte)?\s*$', suffix, re.IGNORECASE):
        factor = factor_bin ** 6
    elif re.search(r'^\s*Z(?:B(?:yte)?)?\s*$', suffix, re.IGNORECASE):
        factor = factor_si ** 7
    elif re.search(r'^\s*ZiB(?:yte)?\s*$', suffix, re.IGNORECASE):
        factor = factor_bin ** 7
    else:
        msg = _("Couldn't detect suffix %r.") % (suffix)
        raise ValueError(msg)

    if verbose > 4:
        msg = _("Found factor %d.") % (factor)
        logger.debug(msg)

    fbytes = float(factor) * value_float
    if as_float:
        return fbytes
    if six.PY2:
        lbytes = long(fbytes)
    else:
        lbytes = int(fbytes)

    return lbytes


# =============================================================================
def period2days(period, use_locale_radix=False, verbose=0):
    """
    Converts the given string of the form »5d 8h« in an amount of days.
    It raises a ValueError on invalid values.

    Special values of period:
        - now (returns 0)
        - never (returns float('inf'))

    Valid units for periods are:
        - »h[ours]«
        - »d[ays]«   - default, if bare numbers are given
        - »w[eeks]«  - == 7 days
        - »m[onths]« - == 30 days
        - »y[ears]«  - == 365 days

    @param period: the period to convert
    @type period: str
    @param use_locale_radix: use the locale version of radix instead of the english decimal dot.
    @type use_locale_radix: bool
    @param verbose: level of verbosity
    @type verbose: int

    @return: amount of days
    @rtype: float
    """

    if period is None:
        raise ValueError(_("Given period is None."))

    value = str(period).strip().lower()
    if period == '':
        raise ValueError(_("Given period was empty."))

    if verbose > 3:
        logger.debug(_("Called with %r."), period)

    if period == 'now':
        return float(0)

    # never - returns a positive infinite value
    if period == 'never':
        return float('inf')

    days = float(0)
    radix = '.'
    if use_locale_radix:
        radix = locale.RADIXCHAR
    radix = re.escape(radix)
    if verbose > 3:
        logger.debug(_("Using radix %r ..."), radix)

    # Search for hours in value
    pattern = r'(\d+(?:' + radix + r'\d*)?)\s*h(?:ours?)?'
    if verbose > 4:
        logger.debug(_("Pattern %r."), pattern)
    match = re.search(pattern, value, re.IGNORECASE)
    if match:
        hours_str = match.group(1)
        if use_locale_radix:
            hours_str = re.sub(radix, '.', hours_str, 1)
        hours = float(hours_str)
        days += hours / 24
        if verbose > 3:
            logger.debug(_("Found %.2f hours."), hours)
        value = re.sub(pattern, '', value, re.IGNORECASE)
    if verbose > 4:
        logger.debug(_("Rest after hours: %r."), value)

    # Search for weeks in value
    pattern = r'(\d+(?:' + radix + r'\d*)?)\s*w(?:eeks?)?'
    if verbose > 4:
        logger.debug(_("Pattern %r."), pattern)
    match = re.search(pattern, value, re.IGNORECASE)
    if match:
        weeks_str = match.group(1)
        if use_locale_radix:
            weeks_str = re.sub(radix, '.', weeks_str, 1)
        weeks = float(weeks_str)
        days += weeks * 7
        if verbose > 3:
            logger.debug(_("Found %f weeks."), weeks)
        value = re.sub(pattern, '', value, re.IGNORECASE)
    if verbose > 4:
        logger.debug(_("Rest after weeks: %r."), value)

    # Search for months in value
    pattern = r'(\d+(?:' + radix + r'\d*)?)\s*m(?:onths?)?'
    if verbose > 4:
        logger.debug(_("Pattern %r."), pattern)
    match = re.search(pattern, value, re.IGNORECASE)
    if match:
        months_str = match.group(1)
        if use_locale_radix:
            months_str = re.sub(radix, '.', months_str, 1)
        months = float(months_str)
        days += months * 30
        if verbose > 3:
            logger.debug(_("Found %f months."), months)
        value = re.sub(pattern, '', value, re.IGNORECASE)
    if verbose > 4:
        logger.debug(_("Rest after months: %r."), value)

    # Search for years in value
    pattern = r'(\d+(?:' + radix + r'\d*)?)\s*y(?:ears?)?'
    if verbose > 4:
        logger.debug(_("Pattern %r."), pattern)
    match = re.search(pattern, value, re.IGNORECASE)
    if match:
        years_str = match.group(1)
        if use_locale_radix:
            years_str = re.sub(radix, '.', years_str, 1)
        years = float(years_str)
        days += years * 365
        if verbose > 3:
            logger.debug(_("Found %f years."), years)
        value = re.sub(pattern, '', value, re.IGNORECASE)
    if verbose > 4:
        logger.debug(_("Rest after years: %r."), value)

    # At last search for days in value
    pattern = r'(\d+(?:' + radix + r'\d*)?)\s*(?:d(?:ays?)?)?'
    if verbose > 4:
        logger.debug(_("Pattern %r."), pattern)
    match = re.search(pattern, value, re.IGNORECASE)
    if match:
        days_str = match.group(1)
        if use_locale_radix:
            days_str = re.sub(radix, '.', days_str, 1)
        days_float = float(days_str)
        days += days_float
        if verbose > 3:
            logger.debug(_("Found %f days."), days_float)
        value = re.sub(pattern, '', value, re.IGNORECASE)
    if verbose > 4:
        logger.debug(_("Rest after days: %r."), value)

    # warn, if there is a rest
    if not RE_WS_ONLY.search(value):
        logger.warning(_("Invalid content for a period: %r."), value)

    if verbose > 3:
        msg = _("Total %f days found.") % (days)
        logger.debug(_("Total %f days found."), days)

    return days


# =============================================================================
def get_address_list(address_str, verbose = 0):
    '''
    Retrieves all mail addresses from address_str and give them back
    as a list of tuples.

    @param address_str: the string with all mail addresses as a comma
                        separated list
    @type address_str:  str
    @param verbose:     level of verbosity
    @type verbose:      int

    @return: list of tuples in the form of the return value
             of email.utils.parseaddr()
    @rtype:  list

    '''

    addr_list = []
    addresses = []

    for row in csv.reader([address_str],
                          doublequote=False,
                          skipinitialspace=True):
        for address in row:
            addr_list.append(address)

    if verbose > 3:
        logger.debug(
            __(
                "Found address entry:",
                "Found address entries:", len(addr_list)
            ) + "\n" + pp(addr_list))

    for address in addr_list:
        address = re.sub(r',', ' ', address)
        address = re.sub(r'\s+', ' ', address)
        pair = email.utils.parseaddr(address)
        if verbose > 3:
            logger.debug(_("Got mail address pair:") + "\n" + pp(pair))
        if not email_valid(pair[1]):
            logger.warning(_("Found invalid mail address %r."), address)
            continue
        addresses.append(pair)

    return addresses


# =============================================================================
def to_bool(value):
    """
    Converter from string to boolean values (e.g. from configurations)
    """

    if not value:
        return False
    if isinstance(value, bool):
        return value

    try:
        v_int = int(value)
    except ValueError:
        pass
    except TypeError:
        pass
    else:
        if v_int == 0:
            return False
        else:
            return True

    v_str = to_str_or_bust(value, force=True)

    if RE_YES.search(v_str):
        return True

    if RE_NO.search(v_str):
        return False

    return bool(value)

# =============================================================================
def to_unicode_or_bust(obj, encoding='utf-8', force=False):
    """
    Transforms a string, which is not a unicode string, into a unicode string.
    All other objects are left untouched.

    @param obj: the object to transform
    @type obj:  object
    @param encoding: the encoding to use to decode the object,
    @type encoding:  str

    @return: the maybe decoded object
    @rtype:  object

    """

    do_decode = False
    if six.PY2:
        if isinstance(obj, str):
            do_decode = True
        elif force:
            return unicode(obj)
    else:
        if isinstance(obj, bytes):
            do_decode = True
        elif force:
            return str(obj)

    if do_decode:
        obj = obj.decode(encoding)

    return obj


# =============================================================================
def encode_or_bust(obj, encoding='utf-8', force=False):
    """
    Encodes the given unicode object into the given encoding.
    In Python 3 a bytes object is returend in this case.

    @param obj: the object to encode
    @type obj:  object
    @param encoding: the encoding to use to encode the object,
    @type encoding:  str

    @return: the maybe encoded object
    @rtype:  object

    """

    do_encode = False
    if six.PY2:
        if isinstance(obj, unicode):
            do_encode = True
        elif force:
            return str(obj)
    else:
        if isinstance(obj, str):
            do_encode = True
        elif force:
            return bytes(obj)

    if do_encode:
        obj = obj.encode(encoding)

    return obj


# =============================================================================
def to_utf8_or_bust(obj, force=False):
    """
    Transforms a string, what is a unicode string, into a utf-8 encoded string.
    All other objects are left untouched.
    In Python 3 a bytes object is returend in this case.

    @param obj: the object to transform
    @type obj:  object

    @return: the maybe encoded object
    @rtype:  object

    """

    return encode_or_bust(obj, 'utf-8', force=force)


# =============================================================================
def to_bytes(obj, encoding='utf-8', force=False):
    "Wrapper for encode_or_bust()"

    return encode_or_bust(obj, encoding, force=force)


# =============================================================================
def to_str_or_bust(obj, encoding='utf-8', force=False):
    """
    Transformes the given string-like object into the str-type according
    to the current Python version.
    """

    if six.PY2:
        return encode_or_bust(obj, encoding, force=force)
    else:
        return to_unicode_or_bust(obj, encoding, force=force)


# =============================================================================
def terminal_can_colors(verbose=0):
    """
    Method to detect, whether the current terminal (stdout and stderr)
    is able to perform ANSI color sequences.

    @return: both stdout and stderr can perform ANSI color sequences
    @rtype: bool

    """

    cur_term = ''
    if 'TERM' in os.environ:
        cur_term = os.environ['TERM'].lower().strip()

    colored_term_list = (
        r'ansi',
        r'linux.*',
        r'screen.*',
        r'[xeak]term.*',
        r'gnome.*',
        r'rxvt.*',
        r'interix',
    )
    term_pattern = r'^(?:' + r'|'.join(colored_term_list) + r')$'
    re_term = re.compile(term_pattern)

    ansi_term = False
    env_term_has_colors = False

    if cur_term:
        if cur_term == 'ansi':
            env_term_has_colors = True
            ansi_term = True
        elif re_term.search(cur_term):
            env_term_has_colors = True
    if verbose:
        sys.stderr.write(
            "ansi_term: %r, env_term_has_colors: %r\n" % (
                ansi_term, env_term_has_colors))

    has_colors = False
    if env_term_has_colors:
        has_colors = True
    for handle in [sys.stdout, sys.stderr]:
        if (hasattr(handle, "isatty") and handle.isatty()):
            if debug:
                sys.stderr.write("%s is a tty.\n" % (handle.name))
            if (platform.system() == 'Windows' and not ansi_term):
                if debug:
                    sys.stderr.write("platform is Windows and not ansi_term.\n")
                has_colors = False
        else:
            if debug:
                sys.stderr.write("%s is not a tty.\n" % (handle.name))
            if ansi_term:
                pass
            else:
                has_colors = False

    return has_colors


# =============================================================================

if __name__ == "__main__":
    pass

# =============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
