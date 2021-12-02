# Copyright (C) 2021 University of Glasgow
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

# Find all internet-drafts submitted within a particular date range, and
# print some metadata about the submissions, including links to download
# the drafts in various formats. Note that the `Submission` class contains
# more fields than are printed here.
# 
# The `Submission` objects found in this way are useful to find metadata
# about internet-draft submissions. They can also be used to find URLs
# from which to download drafts, as shown, but if you need to fetch large
# numbers of drafts, it's much faster to rsync the entire draft archive, as
# described at https://www.ietf.org/standards/ids/internet-draft-mirror-sites/

dt = DataTracker()
for submission in dt.submissions(date_since = "2021-11-01", date_until = "2021-11-30"):
    print(f"{submission.name}-{submission.rev}")
    print(f"  submitted: {submission.submission_date}")

    for author in submission.parse_authors():
        print(f"  author: {author['name']}", end="")
        if author['email'] is not None:
            print(f" <{author['email']}>", end="")
        if author['affiliation'] is not None:
            print(f", {author['affiliation']}", end="")
        print("")

    for url in submission.urls():
        print(f"  {url}")

