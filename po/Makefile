#
# Makefile for i18n-Objects in PyLogrotate
#
# $Id$
# $URL$
#

all: pylogrotate.de.mo LogRotateGetopts.de.mo

pylogrotate.de.mo: pylogrotate.de.po
	@echo
	@echo "Compiling $@ ..."
	msgfmt -o pylogrotate.de.mo --check -v pylogrotate.de.po
	@if [ ! -d de_DE/LC_MESSAGES ] ; then mkdir -vp de_DE/LC_MESSAGES; fi
	@cp -pv pylogrotate.de.mo de_DE/LC_MESSAGES/pylogrotate.mo

LogRotateGetopts.de.mo: LogRotateGetopts.de.po
	@echo
	@echo "Compiling $@ ..."
	msgfmt -o LogRotateGetopts.de.mo --check -v LogRotateGetopts.de.po
	@if [ ! -d de_DE/LC_MESSAGES ] ; then mkdir -vp de_DE/LC_MESSAGES; fi
	@cp -pv LogRotateGetopts.de.mo de_DE/LC_MESSAGES/LogRotateGetopts.mo

