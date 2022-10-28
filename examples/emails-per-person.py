# Copyright (C) 2021-2022 University of Glasgow
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
import textwrap

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pathlib              import Path
from ietfdata.datatracker import *

# =============================================================================
# Find the number of email addresses for each participants in the IETF.

dt = DataTracker()

people = {}

num_people = 0
num_emails = 0
max_emails = 0
max_person = ""

# This iterates over all the people in the datatracker, which will be slow
# if you do not have them all cached locally. The the environment variable
# IETFDATA_LOGLEVEL to INFO before running to see progress.
for person in dt.people():
    num_people += 1
    people[person.id] = []
    print(f"{person.id:8} {person.name}")
    email_for_person = 0
    for email in dt.email_for_person(person):
        email_for_person += 1
        if email_for_person > max_emails:
            max_emails = email_for_person
            max_person = f"{person.name} ({person.id})"
        num_emails += 1
        people[person.id].append(email.address)
        print(f"         {email.address}")

print(f"num_people = {num_people}")
print(f"num_email_addresses = {num_emails}")
print(f"max_email_addresses = {max_emails}    {max_person}")
print(f"average number of email addresses per person = {num_emails / num_people}")
print(f"")
print(f"Num Emails:   Count:")
for i in range(0, max_emails+1):
    count = 0
    for person, emails in people.items():
        if len(emails) == i:
            count += 1
    print(f"  {i:4}        {count}")

