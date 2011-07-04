#
# Makefile for i18n-Objects in PyLogrotate
#
# $Id$
# $URL$
#

.SUFFIXES: .mo .po

MODULE = pylogrotate LogRotateGetopts LogRotateConfig LogRotateStatusFile LogRotateScript LogRotateHandler

all: $(MODULE:=.de.mo)

.po.mo:
	@echo
	@echo "Compiling $*.mo from $*.po ..."
	msgfmt -o $*.mo --check -v $*.po
	@if [ ! -d de_DE/LC_MESSAGES ] ; then mkdir -vp de_DE/LC_MESSAGES; fi
	@TARGET=de_DE/LC_MESSAGES/`echo $* | sed s'/\.de$$//'`.mo; \
		cp -pv $*.mo $$TARGET


