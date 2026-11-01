# Copyright (C) 2025 University of Glasgow
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

from datetime              import date, datetime, timedelta, timezone
from ietfdata.datatracker  import *
from ietfdata.mailarchive3 import *

dt = DataTracker(DTBackendArchive("archive/ietf-dt.sqlite"))
ma = MailArchive("archive/ietf-ma.sqlite")

mt = dt.meeting_type_from_slug("ietf")

prev_meeting_end = "1970-01-01T00:00:00+00:00"

for meeting in sorted(dt.meetings(meeting_type = mt), key=lambda meeting: int(meeting.number)):
    if meeting.status() != MeetingStatus.COMPLETED:
        continue

    meeting_start = meeting.date.strftime("%Y-%m-%dT00:00:00+00:00")
    meeting_end   = (meeting.date + timedelta(days = meeting.days)).strftime("%Y-%m-%dT00:00:00+00:00")

    print(f"IETF {meeting.number}, {meeting.city}")
    for msg in ma.messages(sent_after = prev_meeting_end, sent_before = meeting_end):
        print(f"    {msg.mailing_list().name():10} {msg.uid():5} ", end="", flush=True)
        print(f"{msg.from_()}")


    prev_meeting_end = meeting_end

