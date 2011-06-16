#
# Makefile for i18n-Objects in PyLogrotate
#
# $Id$
# $URL$
#

all: pylogrotate.de.mo LogRotateGetopts.de.mo LogRotateConfig.de.mo LogRotateStatusFile.de.mo

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

LogRotateConfig.de.mo: LogRotateConfig.de.po
	@echo
	@echo "Compiling $@ ..."
	msgfmt -o LogRotateConfig.de.mo --check -v LogRotateConfig.de.po
	@if [ ! -d de_DE/LC_MESSAGES ] ; then mkdir -vp de_DE/LC_MESSAGES; fi
	@cp -pv LogRotateConfig.de.mo de_DE/LC_MESSAGES/LogRotateConfig.mo

LogRotateStatusFile.de.mo: LogRotateStatusFile.de.po
	@echo
	@echo "Compiling $@ ..."
	msgfmt -o LogRotateStatusFile.de.mo --check -v LogRotateStatusFile.de.po
	@if [ ! -d de_DE/LC_MESSAGES ] ; then mkdir -vp de_DE/LC_MESSAGES; fi
	@cp -pv LogRotateStatusFile.de.mo de_DE/LC_MESSAGES/LogRotateStatusFile.mo

