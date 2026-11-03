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

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime             import timedelta
from ietfdata.datatracker import *

if len(sys.argv) != 3:
    print("Usage: python ietf_meetings.py archive/ietf_dt.sqlite data/ietf_meetings.json")
    sys.exit(1)

dt = DataTracker(DTBackendArchive(sys.argv[1]))

meetings = []

for meeting in dt.meetings(meeting_type = dt.meeting_type_from_slug("ietf")):
    #print(meeting)
    start_date = meeting.date
    end_date   = meeting.date + timedelta(days = meeting.days-1)
    meetings.append({"number"     : meeting.number,
                     "city"       : meeting.city,
                     "country"    : meeting.country,
                     "attendees"  : meeting.attendees,
                     "start_date" : start_date.strftime("%Y-%m-%d"),
                     "end_date"   : end_date.strftime("%Y-%m-%d")})

with open(sys.argv[2], "w") as outf:
    json.dump(meetings, fp = outf, indent = 3)

