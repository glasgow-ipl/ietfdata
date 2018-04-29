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
# It's possible to do time range queries on a lot of these values, for example:
#   https://datatracker.ietf.org/api/v1/person/person/?time__gt=2018-03-27T14:07:36
#
# Information about working groups:
#   https://datatracker.ietf.org/api/v1/group/group/                               - list of groups
#   https://datatracker.ietf.org/api/v1/group/group/2161/                          - info about group 2161
#   https://datatracker.ietf.org/api/v1/group/grouphistory/?group=2161             - history
#   https://datatracker.ietf.org/api/v1/group/groupurl/?group=2161                 - URLs
#   https://datatracker.ietf.org/api/v1/group/groupevent/?group=2161               - events
#   https://datatracker.ietf.org/api/v1/group/groupmilestone/?group=2161           - Current milestones
#   https://datatracker.ietf.org/api/v1/group/groupmilestonehistory/?group=2161    - Previous milestones
#   https://datatracker.ietf.org/api/v1/group/milestonegroupevent/?group=2161      - changed milestones
#   https://datatracker.ietf.org/api/v1/group/role/?group=2161                     - The current WG chairs and ADs of a group
#   https://datatracker.ietf.org/api/v1/group/role/?person=20209                   - Groups a person is currently involved with
#   https://datatracker.ietf.org/api/v1/group/role/?email=csp@csperkins.org        - Groups a person is currently involved with
#   https://datatracker.ietf.org/api/v1/group/rolehistory/?group=2161              - The previous WG chairs and ADs of a group
#   https://datatracker.ietf.org/api/v1/group/rolehistory/?person=20209            - Groups a person was previously involved with
#   https://datatracker.ietf.org/api/v1/group/rolehistory/?email=csp@csperkins.org - Groups a person was previously involved with
#   https://datatracker.ietf.org/api/v1/group/changestategroupevent/?group=2161    - Group state changes
#   https://datatracker.ietf.org/api/v1/group/groupstatetransitions                - ???
#
# Information about documents:
#   https://datatracker.ietf.org/api/v1/doc/document/                              - list of documents
#   https://datatracker.ietf.org/api/v1/doc/document/?name=...                     - info about document ...
#   https://datatracker.ietf.org/api/v1/doc/docevent/                              - list of document events
#   https://datatracker.ietf.org/api/v1/doc/docevent/?doc=...                      - events for a document
#   https://datatracker.ietf.org/api/v1/doc/docevent/?by=...                       - events by a person (as /api/v1/person/person)
#   https://datatracker.ietf.org/api/v1/doc/docevent/?time=...                     - events by time
#   https://datatracker.ietf.org/api/v1/doc/statedocevent/                         - subset of /api/v1/doc/docevent/; same parameters
#   https://datatracker.ietf.org/api/v1/doc/ballotdocevent/                        -               "                "
#   https://datatracker.ietf.org/api/v1/doc/newrevisiondocevent/                   -               "                "
#   https://datatracker.ietf.org/api/v1/doc/submissiondocevent/                    -               "                "
#   https://datatracker.ietf.org/api/v1/doc/writeupdocevent/                       -               "                "
#   https://datatracker.ietf.org/api/v1/doc/consensusdocevent/                     -               "                "
#   https://datatracker.ietf.org/api/v1/doc/ballotpositiondocevent/                -               "                "
#   https://datatracker.ietf.org/api/v1/doc/reviewrequestdocevent/                 -               "                "
#   https://datatracker.ietf.org/api/v1/doc/lastcalldocevent/                      -               "                "
#   https://datatracker.ietf.org/api/v1/doc/telechatdocevent/                      -               "                "
#   https://datatracker.ietf.org/api/v1/doc/documentauthor/?document=...           - authors of a document
#   https://datatracker.ietf.org/api/v1/doc/documentauthor/?person=...             - documents by person (as /api/v1/person/person)
#   https://datatracker.ietf.org/api/v1/doc/documentauthor/?email=...              - documents by person with particular email
#   https://datatracker.ietf.org/api/v1/doc/relateddocument/?source=...            - documents that source draft relates to (references, replaces, etc)
#   https://datatracker.ietf.org/api/v1/doc/relateddocument/?target=...            - documents that relate to target draft
#   https://datatracker.ietf.org/api/v1/doc/docalias/rfcXXXX/                      - draft that became the given RFC
#   https://datatracker.ietf.org/api/v1/doc/docalias/bcpXXXX/                      - draft that became the given BCP
#   https://datatracker.ietf.org/api/v1/doc/docalias/stdXXXX/                      - RFC that is the given STD
#   https://datatracker.ietf.org/api/v1/doc/state/                                 - Types of state a document can be in
#   https://datatracker.ietf.org/api/v1/doc/ballottype/                            - Types of ballot that can be issued on a document
#
#   https://datatracker.ietf.org/api/v1/doc/relateddochistory/
#   https://datatracker.ietf.org/api/v1/doc/dochistoryauthor/
#   https://datatracker.ietf.org/api/v1/doc/initialreviewdocevent/
#   https://datatracker.ietf.org/api/v1/doc/deletedevent/
#   https://datatracker.ietf.org/api/v1/doc/addedmessageevent/
#   https://datatracker.ietf.org/api/v1/doc/documenturl/
#   https://datatracker.ietf.org/api/v1/doc/docreminder/
#   https://datatracker.ietf.org/api/v1/doc/statetype/
#   https://datatracker.ietf.org/api/v1/doc/editedauthorsdocevent/
#   https://datatracker.ietf.org/api/v1/doc/dochistory/
#
#
# Information about meetings:
#   https://datatracker.ietf.org/api/v1/meeting/meeting/                        - list of meetings
#   https://datatracker.ietf.org/api/v1/meeting/meeting/747/                    - information about meeting number 747
#   https://datatracker.ietf.org/api/v1/meeting/session/                        - list of all sessions in meetings
#   https://datatracker.ietf.org/api/v1/meeting/session/25886/                  - a session in a meeting
#   https://datatracker.ietf.org/api/v1/meeting/session/?meeting=747            - sessions in meeting number 747
#   https://datatracker.ietf.org/api/v1/meeting/session/?meeting=747&group=2161 - sessions in meeting number 747 for group 2161
#   https://datatracker.ietf.org/api/v1/meeting/schedtimesessassignment/59003/  - a schededuled session within a meeting
#   https://datatracker.ietf.org/api/v1/meeting/timeslot/9480/                  - a time slot within a meeting (time, duration, location)
#   https://datatracker.ietf.org/api/v1/meeting/schedule/791/                   - a draft of the meeting agenda
#   https://datatracker.ietf.org/api/v1/meeting/room/537/                       - a room at a meeting
#   https://datatracker.ietf.org/api/v1/meeting/floorplan/14/                   - floor plan for a meeting venue
#   ...
#
# See also:
#   https://datatracker.ietf.org/api/
#   https://trac.tools.ietf.org/tools/ietfdb/wiki/DatabaseSchemaDescription
#   https://trac.tools.ietf.org/tools/ietfdb/wiki/DatatrackerDrafts
#   RFC 6174 "Definition of IETF Working Group Document States"
#   RFC 6175 "Requirements to Extend the Datatracker for IETF Working Group Chairs and Authors"
#   RFC 6292 "Requirements for a Working Group Charter Tool"
#   RFC 6293 "Requirements for Internet-Draft Tracking by the IETF Community in the Datatracker"
#   RFC 6322 "Datatracker States and Annotations for the IAB, IRTF, and Independent Submission Streams"
#   RFC 6359 "Datatracker Extensions to Include IANA and RFC Editor Processing Information"
#   RFC 7760 "Statement of Work for Extensions to the IETF Datatracker for Author Statistics"

from pathlib     import Path

import datetime
import glob
import json
import requests

# =============================================================================
# Class to query the IETF Datatracker:

class DataTracker:
    def __init__(self):
        self.session    = requests.Session()
        self.base_url   = "https://datatracker.ietf.org"
        self._people    = {}
        self._documents = {}

    def person(self, person_id): 
        """
        Returns a JSON object representing the person, for example:
            {
                'address': 'School of Computing Science\r\nUniversity of Glasgow\r\nGlasgow G12 8QQ\r\nUnited Kingdom', 
                'affiliation': 'University of Glasgow', 
                'ascii': 'Colin Perkins', 
                'ascii_short': '', 
                'biography': '', 
                'id': 20209, 
                'name': 'Colin Perkins', 
                'photo': None, 
                'photo_thumb': None, 
                'resource_uri': '/api/v1/person/person/20209/', 
                'time': '2012-02-26T00:03:54', 
                'user': ''
            }
        """
        if person_id not in self._people:
            api_url  = "/api/v1/person/person/" + person_id
            response = self.session.get(self.base_url + api_url, verify=True)
            if response.status_code == 200:
                self._people[person_id] = response.json()
            else:
                raise Exception("No such person")
        return self._people[person_id]

    def person_from_email(self, person_email):
        """
        Returns the same JSON object as the person() method, but looked up by
        email address rather than ID number.
        """
        api_url   = "/api/v1/person/email/" + person_email + "/"
        response  = self.session.get(self.base_url + api_url, verify=True)
        if response.status_code == 200:
            person_id = response.json()['person'].replace("/api/v1/person/person/", "").rstrip('/')
            return self.person(person_id)
        else:
            raise Exception("No such person")

    def people(self, since="1970-01-01T00:00:00", until="2038-01-19T03:14:07"):
        """
        Returns a list JSON objects representing all people recorded in the 
        datatracker. As of 29 April 2018, that list contained 21500 entries. 
        The since and until parameters can be used to contrain the output to 
        only those entries added/modified in a particular time range.
        """
        people  = []
        api_url = "/api/v1/person/person/?time__gt=" + since + "&time__lt=" + until
        while api_url != None:
            r = self.session.get(self.base_url + api_url, verify=True)
            meta = r.json()['meta']
            objs = r.json()['objects']
            api_url = meta['next']
            for obj in objs:
                self._people[obj['id']] = obj
                people.append(obj)
        return people

    def documents(self, since="1970-01-01T00:00:00", until="2038-01-19T03:14:07", doctype="draft"):
        """
        Returns a list JSON objects representing all documents recorded in the 
        datatracker. As of 29 April 2018, that list contained 84000 entries. 
        The since and until parameters can be used to contrain the output to 
        only those entries added/modified in a particular time range. The 
        doctype parameter is one of:
             "agenda"     - Agenda
             "bluesheets" - Bluesheets
             "charter"    - Charter
             "conflrev"   - Conflict Review
             "draft"      - Draft
             "liaison"    - Liaison
             "liai-att"   - Liaison Attachment
             "minutes"    - Minutes
             "recording"  - Recording
             "review"     - Review
             "shepwrit"   - Shepherd's writeup
             "slides"     - Slides
             "statchg"    - Status Change
        and constrains the type of document returned. The JSON objects returned
        are the same format as those returned by the document() method.
        """
        documents = []
        api_url   = "/api/v1/doc/document/?time__gt=" + since + "&time__lt=" + until + "&type=" + doctype
        while api_url != None:
            r = self.session.get(self.base_url + api_url, verify=True)
            meta = r.json()['meta']
            objs = r.json()['objects']
            api_url = meta['next']
            for obj in objs:
                self._documents[obj['name']] = obj
                documents.append(obj)
        return documents

    def document(self, name):
        """
        Returns a JSON object representing a document identified by name, for example:
            {
               "states" : [
                  "/api/v1/doc/state/1/",
                  "/api/v1/doc/state/38/"
               ],
               "rev" : "11",
               "name" : "draft-ietf-quic-transport",
               "intended_std_level" : "/api/v1/name/intendedstdlevelname/ps/",
               "std_level" : null,
               "pages" : 105,
               "abstract" : "   This document defines the core of the QUIC transport protocol.  This\n   document describes connection establishment, packet format,\n   multiplexing and reliability.  Accompanying documents describe the\n   cryptographic handshake and loss detection.\n",
               "type" : "/api/v1/name/doctypename/draft/",
               "rfc" : null,
               "group" : "/api/v1/group/group/2161/",
               "external_url" : "",
               "resource_uri" : "/api/v1/doc/document/draft-ietf-quic-transport/",
               "tags" : [],
               "shepherd" : null,
               "order" : 1,
               "stream" : "/api/v1/name/streamname/ietf/",
               "expires" : "2018-10-19T16:10:12",
               "ad" : null,
               "notify" : "",
               "title" : "QUIC: A UDP-Based Multiplexed and Secure Transport",
               "words" : 24198,
               "internal_comments" : "",
               "submissions" : [
                  "/api/v1/submit/submission/82995/",
                  "/api/v1/submit/submission/83773/",
                  "/api/v1/submit/submission/85557/",
                  "/api/v1/submit/submission/86717/",
                  "/api/v1/submit/submission/87084/",
                  "/api/v1/submit/submission/88860/",
                  "/api/v1/submit/submission/89569/",
                  "/api/v1/submit/submission/89982/",
                  "/api/v1/submit/submission/91554/",
                  "/api/v1/submit/submission/92517/",
                  "/api/v1/submit/submission/93617/",
                  "/api/v1/submit/submission/94830/"
               ],
               "time" : "2018-04-17T16:10:12",
               "note" : ""
            }
        """
        if name not in self._documents:
            api_url  = "/api/v1/doc/document/" + name + "/"
            response = self.session.get(self.base_url + api_url, verify=True)
            if response.status_code == 200:
                self._documents[name] = response.json()
            else:
                raise Exception("No such document")
        return self._documents[name]

# =============================================================================
