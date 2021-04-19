# Copyright (C) 2020 University of Glasgow
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

from pathlib                  import Path
from ietfdata.datatracker     import *
from ietfdata.datatracker_ext import *


dt = DataTrackerExt()

# Find the mailing lists:
lists = {}
for ml in dt.mailing_lists():
    key = ml.name.lower()
    lists[key] = ml


# Find the subscribers to ietf@ietf.org:

subscribed : Dict[str, List[str]] = {}

subscribed_wg : List[str] = []

def record_subscriptions(ml: MailingList):
    print(F"Record subscriptions: {ml.name} ", end="", flush=True)
    subscribed[ml.name] = []
    for x in dt.mailing_list_subscriptions(mailing_list=ml):
        subscribed[ml.name].append(x.email)
    print(F"({len(subscribed[ml.name])})")

record_subscriptions(lists["ietf"])


# Find the subscribers to lists for active working groups:

for group in dt.active_working_groups():
    addr, domain = group.list_email.split("@")
    if domain == "ietf.org":
        record_subscriptions(lists[addr])

        for subscriber in subscribed[lists[addr].name]:
            if subscriber not in subscribed_wg:
                subscribed_wg.append(subscriber)
    else:
        print(F"{group.acronym} uses non-IETF mailing list: {group.list_email}")


# Compare subscriber lists:

ietf_and_wg = set()
ietf_not_wg = set()

for s in subscribed["ietf"]:
    if s in subscribed_wg:
        ietf_and_wg.add(s)
    else:
        ietf_not_wg.add(s)

print(F"Number of unique WG list subscribers: {len(subscribed_wg)}")
print(F"Subscribed to ietf@ietf.org and some WG: {len(ietf_and_wg)}")
print(F"Subscribed to ietf@ietf.org but no WGs: {len(ietf_not_wg)}")
