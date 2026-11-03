# Copyright (C) 2026 University of Glasgow
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

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ietfdata.datatracker import *

if len(sys.argv) != 3:
    print("Usage: python rfcs_per_year.py archive/ietf-dt.sqlite data/rfcs-per-year.csv")
    sys.exit(1)

dt = DataTracker(DTBackendArchive(sys.argv[1]))

rfcs_per_year = {}

for rfc in dt.documents(doctype = dt.document_type_from_slug("rfc")):
    print(f"\r{rfc.name.upper():8}", end="")
    for event in dt.document_events(doc = rfc, event_type = "published_rfc"):
        year = event.time.year
        if year not in rfcs_per_year:
            rfcs_per_year[year]  = 1
        else:
            rfcs_per_year[year] += 1

print("\r        \r", end="")

with open(sys.argv[2], "w") as outf:
    for year in sorted(rfcs_per_year.keys()):
        print(f"{year},{rfcs_per_year[year]}", file=outf)
