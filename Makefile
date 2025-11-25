# Copyright (C) 2019-2025 University of Glasgow
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

DATA = data/ietfdata-dt.sqlite \
       data/ietfdata-ma.sqlite \
       data/participants.json  \
       data/organisations.json \
       data/affiliations.json


test: typecheck runtests

test-all: $(DATA) test

typecheck:
	mypy ietfdata/*.py ietfdata/tools/*.py
	mypy tests/*.py

runtests:
	@python3 -m unittest discover -s tests/ -v

data:
	mkdir $@

data/ietfdata-ma.sqlite: | data
	@python3 -m ietfdata.tools.download_ma $@

data/ietfdata-dt.sqlite: | data
	@python3 -m ietfdata.tools.download_dt $@

data/participants.json: data/ietfdata-dt.sqlite data/ietfdata-ma.sqlite
	@python3 -m ietfdata.tools.participants  $^ $@

data/organisations.json: data/ietfdata-dt.sqlite
	@python3 -m ietfdata.tools.organisations $^ $@

data/affiliations.json: data/ietfdata-dt.sqlite data/participants.json data/organisations.json
	@python3 -m ietfdata.tools.affiliations $^ $@

# Can this rule and ietfdata/tools/participants_affiliations.py be removed?
data/affiliations2.json: data/ietfdata-dt.sqlite data/participants.json data/organisations.json
	@python3 -m ietfdata.tools.participants_affiliations $^ $@

# =================================================================================================
# Rules to clean-up:

clean:
	rm -f $(DATA)
	rm -f data/affiliations2.json

# =================================================================================================
# Targets that don't represent files:

.PHONY: test test-all typecheck runtests clean

# =================================================================================================
# Configuration for make:

.DELETE_ON_ERROR:

.NOTINTERMEDIATE:

MAKEFLAGS += --output-sync --warn-undefined-variables --no-builtin-rules --no-builtin-variables

# =================================================================================================
# vim: set ts=2 sw=2 tw=0 ai:
