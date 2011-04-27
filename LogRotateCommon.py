#!/usr/bin/env python
# -*- coding: utf-8 -*-

# $Id$
# $URL$

'''
@author: Frank Brehm
@contact: frank@brehm-online.com
@license: GPL3
@copyright: (c) 2010-2011 by Frank Brehm, Berlin
@version: 0.1.0
@summary: Module for common used functions
'''

import re
import sys

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

def split_parts( text, keep_quotes = False, raise_on_unbalanced = True):
    '''
    Split the given text in chunks by whitespaces or
    single or double quoted strings.
        
    @param text:        the text to split in chunks
    @type text:         str
    @param keep_quotes: keep quotes of quoted chunks
    @type keep_quotes:  bool
    @param raise_on_unbalanced: raise an exception on
                                unbalanced quotes
    @type raise_on_unbalanced:  bool

    @return: list of chunks
    @rtype:  list
    '''

    chunks = []
    if text is None:
        return chunks

    txt = str(text)
    last_chunk = ''

    # Big loop to split the text - until it is empty
    while txt != '':

        # add chunk, if there is a chunk left and a whitspace
        # at the begin of the line
        match = re.search(r"\s+", txt)
        if ( last_chunk != '' ) and match:
            chunks.append(last_chunk)
            last_chunk = ''

        # clean the line
        txt = txt.strip()
        if txt == '':
            break

        # search for a single quoted string at the begin of the line
        match = re.search(r"^'((?:\\'|[^'])*)'", txt)
        if match:
            chunk = match.group(1)
            chunk = re.sub(r"\\'", "'", chunk)
            if keep_quotes:
                chunk = "'" + chunk + "'"
            last_chunk += chunk
            txt = re.sub(r"^'(?:\\'|[^'])*'", "", txt)
            continue

        # search for a double quoted string at the begin of the line
        match = re.search(r'^"((?:\\"|[^"])*)"', txt)
        if match:
            chunk = match.group(1)
            chunk = re.sub(r'\\"', '"', chunk)
            if keep_quotes:
                chunk = '"' + chunk + '"'
            last_chunk += chunk
            txt = re.sub(r'^"(?:\\"|[^"])*"', "", txt)
            continue

        # search for unquoted, whitespace delimited text
        # at the begin of the line
        match = re.search(r'^((?:[^\s\'"]+|\\\'|\\")+)', txt)
        if match:
            last_chunk += match.group(1)
            txt = re.sub(r'^(?:[^\s\'"]+|\\\'|\\")+', "", txt)
            continue

        # Only whitespaces left
        match = re.search(r'^\s*$', txt)
        if match:
            break

        # Check for unbalanced quotes
        match = re.search(r'^([\'"].*)\s*', txt)
        if match:
            chunk = match.group(1)
            if raise_on_unbalanced:
                raise Exception("Unbalanced quotes in »%s«." % ( str(text) ) )
            else:
                last_chunk += chunk
                continue

        # Here we should not come to ...
        raise Exception("Broken split of »%s«: »%s« left" %( str(text), txt))

    if last_chunk != '':
        chunks.append(last_chunk)

    return chunks

#========================================================================

if __name__ == "__main__":
    pass

#========================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
