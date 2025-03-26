# Copyright (C) 2024 University of Glasgow
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

from datetime                 import timedelta
from pathlib                  import Path
from ietfdata.datatracker     import *
from ietfdata.datatracker_ext import *
from ietfdata.rfcindex        import *
from dateutil.parser          import *

def month_num(month):
    if month == "January":
        return "01"
    elif month == "February":
        return "02"
    elif month == "March":
        return "03"
    elif month == "April":
        return "04"
    elif month == "May":
        return "05"
    elif month == "June":
        return "06"
    elif month == "July":
        return "07"
    elif month == "August":
        return "08"
    elif month == "September":
        return "09"
    elif month == "October":
        return "10"
    elif month == "November":
        return "11"
    elif month == "December":
        return "12"
    else:
        print("huh?")
        sys.exit(1)

ri = RFCIndex()
dt = DataTrackerExt(cache_timeout = timedelta(hours = 12))

print("RFC      Date       DaysBeforeBallot   TotalTimeWithIESG")
for rfc in ri.rfcs(since="2013-01"):
    if rfc.stream != "IETF":
        continue
    draft = dt.document_from_draft(rfc.draft[:-3])
    if draft is None:
        continue

    print(f"{rfc.doc_id}  ", end="")
    print(f"{rfc.year}-{month_num(rfc.month)}            ", end="")

    started_event  = None
    approved_event = None
    ballot_event   = None

    for event in dt.document_events(doc = draft, event_type = "started_iesg_process"):
        if started_event is None:
            started_event = event
    for event in dt.document_events(doc = draft, event_type = "created_ballot"):
        if ballot_event is None:
            ballot_event = event
    for event in dt.document_events(doc = draft, event_type = "iesg_approved"):
        if approved_event is None:
            approved_event = event

    if started_event == None or approved_event == None or ballot_event == None:
        print(f"{rfc.doc_id} missing data")
        print(f"started:  {started_event}")
        print(f"ballot:   {ballot_event}")
        print(f"approved: {approved_event}")
    else:
        ballot_time = ballot_event.time - started_event.time
        total_time  = approved_event.time - started_event.time
        print(f"{timedelta(seconds = ballot_time.total_seconds()).days:4}            ", end="")
        print(f"{timedelta(seconds = total_time.total_seconds()).days:4}  ")


