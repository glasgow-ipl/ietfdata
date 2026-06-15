# Copyright (C) 2019-2026 University of Glasgow
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions 
# are met:
# 
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

ARCHIVE := archive/rfc-index.xml \
           archive/ietfdata-dt.sqlite \
           archive/ietfdata-ma.sqlite

DATA := data/participants.json  \
        data/organisations.json \
        data/affiliations.json

# =============================================================================
# Rules to run tests.

test: typecheck
	@echo "*** Testing against live datatracker"
	python3 -m unittest discover -s tests/ -v

test-archive: typecheck $(ARCHIVE)
	@echo "*** Testing against archived datatracker"
	DT_TEST_ARCHIVE=1 python3 -m unittest discover -s tests/ -v

typecheck:
	mypy ietfdata/*.py ietfdata/tools/*.py
	mypy tests/*.py

# =============================================================================
# Rules to fetch an archive of raw data from the IETF.

archive:
	mkdir $@

archive/rfc-index.xml: | archive
	curl -s -o $@ https://www.rfc-editor.org/rfc-index.xml

archive/ietfdata-dt.sqlite: | archive
	python3 -m ietfdata.tools.download_dt $@

archive/ietfdata-ma.sqlite: | archive
	python3 -m ietfdata.tools.download_ma $@

# =============================================================================
# Rules to update the data derived from the archive.

data:
	mkdir $@

data/participants.json: archive/ietfdata-dt.sqlite archive/ietfdata-ma.sqlite | data
	python3 -m ietfdata.tools.participants  $^ $@

data/organisations.json: archive/ietfdata-dt.sqlite archive/rfc-index.xml | data
	python3 -m ietfdata.tools.organisations $^ $@

data/affiliations.json: archive/ietfdata-dt.sqlite archive/rfc-index.xml data/participants.json data/organisations.json | data
	python3 -m ietfdata.tools.affiliations  $^ $@

# Can this rule and ietfdata/tools/participants_affiliations.py be removed?
data/affiliations2.json: archive/ietfdata-dt.sqlite archive/rfc-index.xml data/participants.json data/organisations.json | data
	python3 -m ietfdata.tools.participants_affiliations $^ $@

# =================================================================================================
# Rules to clean-up:

clean:
	rm -f $(DATA)
	rm -f data/affiliations2.json

deep-clean: clean
	rm -f $(ARCHIVE)

# =================================================================================================
# Targets that don't represent files:

.PHONY: test test-archive typecheck clean deep-clean

# =================================================================================================
# Configuration for make:

.DELETE_ON_ERROR:

.NOTINTERMEDIATE:

MAKEFLAGS += --output-sync --warn-undefined-variables --no-builtin-rules --no-builtin-variables

# =================================================================================================
# vim: set ts=2 sw=2 tw=0 ai:
