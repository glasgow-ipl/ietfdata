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

from pathlib              import Path
from ietfdata.datatracker import *

# =============================================================================
# Example: print information about a person

dt = DataTracker(cache_dir=Path("cache"))

p = dt.person_from_email("csp@csperkins.org")
print("Name: {}".format(p.name))
print("Biography: {}".format(p.biography))

for alias in dt.person_aliases(p):
    print("Known as: {}".format(alias.name))

for email in dt.email_for_person(p):
    if email.primary:
        primary = "(primary)"
    else:
        primary = ""
    print("Email: {} {}".format(email.address, primary))

    for subscriptions in dt.mailing_list_subscriptions(email.address):
        for mailing_list_uri in subscriptions.lists:
            mailing_list = dt.mailing_list(mailing_list_uri)
            print("  Subscribed to mailing list {}".format(mailing_list.name))

for d in dt.documents_authored_by_person(p):
    doc = dt.document(d.document)
    print("Document: {}".format(doc.title))
    print("  {}".format(doc.name))
    print("  Affiliation: {}".format(d.affiliation))
    print("  Country: {}".format(d.country))


# =============================================================================
