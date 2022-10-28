# Copyright (C) 2022 University of Glasgow
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

import email.header
import email.utils
import os
import re
import string
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dataclasses import dataclass, field
from pathlib              import Path
from ietfdata.datatracker import *
from ietfdata.mailarchive import *

dt      = DataTracker()
archive = MailArchive()
drafts  = {}

for ml_name in ["ietf-announce", "ietf-announce-old", "i-d-announce"]:
    ml = archive.mailing_list(ml_name)
    ml.update()
    for msg in ml.messages():
        if msg.subject is None:
            msg.subject = ""
        if isinstance(msg.subject, list):
            msg.subject = msg.subject[0]
        if isinstance(msg.date, list):
            msg.date = msg.date[0]
        if msg.subject.lower().startswith("i-d action:"):
            if msg.subject.endswith("(resend)"):
                msg.subject = msg.subject[:-9]
            if msg.subject.endswith("(re-send)"):
                msg.subject = msg.subject[:-10]
            if msg.subject.endswith(",.pdf"):
                msg.subject = msg.subject[:-5]
            if msg.subject.endswith(", .pdf"):
                msg.subject = msg.subject[:-6]
            if msg.subject.endswith(",.ps"):
                msg.subject = msg.subject[:-4]
            draft = msg.subject[11:].strip()[:-4]
            date  = msg.date.strftime('%Y-%m-%d')
            print(f"  {date} {draft}")
            assert draft[-3] == "-"
            assert draft[-2].isdigit()
            assert draft[-1].isdigit()
            if draft not in drafts:
                drafts[draft] = date

with open("draft-submission-dates.json", "w") as outf:
    json.dump(drafts, outf, indent=4)


