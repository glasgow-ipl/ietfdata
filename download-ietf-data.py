#!/usr/bin/env python3
#
# Copyright (C) 2017-2018 University of Glasgow
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

from pathlib     import Path
from rfcindex    import RFCIndex
from rfc         import RFC
from datatracker import DataTracker

import datetime
import requests
import time
import json
import sys

# =================================================================================================
# Create data directories:

for d in ["data", "data/rfc", "data/people", "data/docs"]:
    if not Path(d).is_dir():
        print("[mkdir]", d)
        Path(d).mkdir(exist_ok=True)

# =================================================================================================
# Functions to manage the last fetch times:

y    = datetime.datetime.now().year
m    = datetime.datetime.now().month
d    = datetime.datetime.now().day
hour = datetime.datetime.now().hour
mins = datetime.datetime.now().minute
secs = datetime.datetime.now().second
time_curr  = "{:04d}-{:02}-{:02d}T{:02}:{:02}:{:02}".format(y, m, d, hour, mins, secs)

def set_last_fetch(filename, last_fetch):
    with open(filename, "w") as outf:
        outf.write(last_fetch)

def get_last_fetch(filename):
    try:
        inf = open(filename, "r")
        last_fetch = inf.read()
        inf.close()
    except OSError:
        last_fetch = "1970-01-01T00:00:00"
    return last_fetch

# =================================================================================================
# Fetch the RFC data:

# Fetch rfc-index.xml if it doesn't exist or is more than 24 hours old:
index_path = Path("data/rfc-index.xml")
if not index_path.exists() or ((time.time() - index_path.stat().st_mtime) > 86400):
    print("[fetch]", index_path)
    response = requests.get("https://www.rfc-editor.org/rfc-index.xml")
    with open(index_path, "w") as f:
        f.write(response.text)

# Parse rfc-index.xml:
print("[parse]", index_path)
index = RFCIndex(index_path)

# Parse and fetch RFCs:
for rfcnum in index.rfc.values():
    rfc = RFC(rfcnum)

# =================================================================================================
# Query the datatracker

requests    = requests.Session()
datatracker = DataTracker()

# Fetch the people:
time_prev = get_last_fetch("data/people/.last_fetched")
for person in datatracker.people(time_prev, time_curr):
    filename = "data/people/" + str(person["id"])
    with open(filename, "w") as f:
        json.dump(person, f)
        print("[fetch] person {:6d}: {}".format(person["id"], person["name"]))
    set_last_fetch("data/people/.last_fetched", time_curr)

# Fetch the documents:
for dt in ["agenda"]:
    # "bluesheets", "charter", "conflrev", "draft", "liaison", "liai-att", 
    # "minutes", "recording", "review", "shepwrit", "slides", "statchg"
    d = "data/docs/" + dt
    if not Path(d).is_dir():
        print("[mkdir]", d)
        Path(d).mkdir(exist_ok=True)

    time_prev = get_last_fetch(d + "/.last_fetched")
    for doc in datatracker.documents(since=time_prev, until=time_curr, doctype=dt):
        metadata_file = d + "/" + doc["name"] + ".json"
        contents_file = d + "/" + doc["name"]
        with open(metadata_file, "w") as f:
            print("[fetch] {}: {}".format(dt, doc["name"]))
            json.dump(doc, f)
        with open(contents_file, "wb") as f:
            print("[fetch] {}: {}".format(dt, doc["external_url"]))
            response = requests.get(doc["external_url"], verify=True)
            if response.status_code == 200:
                f.write(response.content)
            else:
                print("[*****] error", response.status_code)
        set_last_fetch(d + "/.last_fetched", time_curr)

# =================================================================================================
