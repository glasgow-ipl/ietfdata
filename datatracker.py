# Copyright (C) 2017 University of Glasgow
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

# The module contains code to interact with the IETF Datatracker
# (https://datatracker.ietf.org/release/about)
#
# The Datatracker API is at https://datatracker.ietf.org/api/v1 and is
# a REST API implemented using Django Tastypie (http://tastypieapi.org)
#
# Information about working groups:
#   https://datatracker.ietf.org/api/v1/group/group/                            - list of groups
#   https://datatracker.ietf.org/api/v1/group/group/?id=2161                    - info about group 2161
#   https://datatracker.ietf.org/api/v1/group/grouphistory/?group=2161          - history
#   https://datatracker.ietf.org/api/v1/group/groupurl/?group=2161              - URLs
#   https://datatracker.ietf.org/api/v1/group/groupevent/?group=2161            - events
#   https://datatracker.ietf.org/api/v1/group/groupmilestone/?group=2161        - milestones
#   https://datatracker.ietf.org/api/v1/group/groupmilestonehistory/?group=2161 - milestones
#   https://datatracker.ietf.org/api/v1/group/milestonegroupevent/?group=2161   - changed milestones
#   https://datatracker.ietf.org/api/v1/group/role/?group=2161                  - WG chairs and ADs
#   https://datatracker.ietf.org/api/v1/group/changestategroupevent/?group=2161 - Group state changes
#   ...not clear what "rolehistory" and "groupstatetransitions" do...
#
# Information about documents:
#   https://datatracker.ietf.org/api/v1/doc/document/                           - list of documents
#   https://datatracker.ietf.org/api/v1/doc/document/?name=...                  - info about document ...
#   ...

from pathlib     import Path

import datetime
import glob
import json
import requests

# =============================================================================
# Helper functions:

def get_last_fetch(filename):
    try:
        inf = open(filename, "r")
        last_fetch = inf.read()
        inf.close()
    except OSError:
        last_fetch = "1970-01-01"
    return last_fetch

def set_last_fetch(filename):
    with open(filename, "w") as outf:
        year  = datetime.datetime.now().year
        month = datetime.datetime.now().month
        day   = datetime.datetime.now().day
        last_fetch = "{:04d}-{:02}-{:02d}".format(year, month, day)
        outf.write(last_fetch)

# =============================================================================
# Classes to represent data stored in the IETF Datatracker:

class Group:
    # See https://datatracker.ietf.org/api/v1/group/group/schema/
    def __init__(self, json):
        self.id             = json['id']
        self.type           = json['type']
        self.name           = json['name']
        self.acronym        = json['acronym']
        self.state          = json['state']
        self.charter        = json['charter']
        self.ad             = json['ad']
        self.list_email     = json['list_email']
        self.list_subscribe = json['list_subscribe']
        self.list_archive   = json['list_archive']
        self.time           = json['time']
        self.description    = json['description']
        self.comments       = json['comments']
        self.resource_uri   = json['resource_uri']
        self.parent         = json['parent']
        self.unused_states  = json['unused_states']
        self.unused_tags    = json['unused_tags']

    def __str__(self):
        return str(self.id) + " " +self.type + " " + self.name

# =============================================================================
# Class to query the IETF Datatracker:

class DataTracker:
    def __init__(self):
        for d in ["data/datatracker", "data/datatracker/groups", "data/datatracker/docs"]:
            if not Path(d).is_dir():
                print("[mkdir]", d)
                Path(d).mkdir(exist_ok=True)
        self.session     = requests.Session()
        self.datatracker = "https://datatracker.ietf.org"

    def groups(self):
        # Update the local cache of group data:
        last_fetch = get_last_fetch("data/datatracker/groups/.last_fetch")
        url  = "/api/v1/group/group/?time__gt=" + last_fetch
        while url != None:
            r = self.session.get(self.datatracker + url, verify=True)
            meta = r.json()['meta']
            objs = r.json()['objects']
            url = meta['next']
            for obj in objs:
                grouptype = obj['type'][obj['type'].rstrip("/").rfind('/'):]
                groupdir  = "data/datatracker/groups" + grouptype
                if not Path(groupdir).is_dir():
                    print("[mkdir]", groupdir)
                    Path(groupdir).mkdir(exist_ok=True)

                f  = groupdir + obj['acronym'] + ".json"
                with open(f, "w") as outf:
                    print("[fetch]", f)
                    json.dump(obj, outf)
        set_last_fetch("data/datatracker/groups/.last_fetch")
        # Read and return the contents of the cache:
        groups = []
        for group in glob.glob("data/datatracker/groups/[0-9]*.json"):
            with open(group) as inf:
                groups.append(Group(json.load(inf)))
        return groups

    def documents(self):
        # Update the local cache of documents:
        last_fetch = get_last_fetch("data/datatracker/docs/.last_fetch")
        url  = "/api/v1/doc/document/?&time__gt=" + last_fetch
        while url != None:
            r = self.session.get(self.datatracker + url, verify=True)
            meta = r.json()['meta']
            docs = r.json()['objects']
            url = meta['next']
            for doc in docs:
                doctype = doc['type'][doc['type'].rstrip("/").rfind('/'):]
                docdir  = "data/datatracker/docs" + doctype
                if not Path(docdir).is_dir():
                    print("[mkdir]", docdir)
                    Path(docdir).mkdir(exist_ok=True)
                name = doc['name'].replace("/", "-").replace(" ", "_")
                with open(docdir + name + ".json", "w") as outf:
                    print("[fetch]", docdir + name + ".json")
                    json.dump(doc, outf)
        set_last_fetch("data/datatracker/docs/.last_fetch")
        # FIXME: finish this...

# =============================================================================
