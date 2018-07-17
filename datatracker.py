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

# The module contains code to interact with the IETF Datatracker
# (https://datatracker.ietf.org/release/about)
#
# The Datatracker API is at https://datatracker.ietf.org/api/v1 and is
# a REST API implemented using Django Tastypie (http://tastypieapi.org)
#
# It's possible to do time range queries on many of these values, for example:
#   https://datatracker.ietf.org/api/v1/person/person/?time__gt=2018-03-27T14:07:36
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

import datetime
import glob
import json
import requests
import unittest

# =============================================================================
# Class to query the IETF Datatracker:

class DataTracker:
    """
    A class for interacting with the IETF DataTracker.
    """

    def __init__(self):
        self.session      = requests.Session()
        self.base_url     = "https://datatracker.ietf.org"
        self._people      = {}
        self._documents   = {}
        self._states      = {}
        self._submissions = {}

    def __del__(self):
        self.session.close()

    # Datatracker API endpoints returning information about people:
    # * https://datatracker.ietf.org/api/v1/person/person/                          - list of people
    # * https://datatracker.ietf.org/api/v1/person/person/20209/                    - info about person 20209
    # * https://datatracker.ietf.org/api/v1/person/email/csp@csperkins.org/         - map from email address to person
    #   https://datatracker.ietf.org/api/v1/person/personhistory/                   - ???
    #   https://datatracker.ietf.org/api/v1/person/personevent/                     - ???
    #   https://datatracker.ietf.org/api/v1/person/alias/                           - ???

    def person(self, person_id): 
        """
        Returns a JSON dictionary representing the person, for example:
            {
                "time" : "2012-02-26T00:03:54",
                "biography" : "",
                "ascii" : "Colin Perkins",
                "name_from_draft" : "Colin Perkins",
                "photo_thumb" : null,
                "id" : 20209,
                "photo" : null,
                "name" : "Colin Perkins",
                "resource_uri" : "/api/v1/person/person/20209/",
                "user" : "",
                "consent" : null,
                "ascii_short" : ""
            }
        """
        if person_id not in self._people:
            api_url  = "/api/v1/person/person/" + person_id
            response = self.session.get(self.base_url + api_url, verify=True)
            if response.status_code == 200:
                self._people[person_id] = response.json()
            else:
                return None
        return self._people[person_id]

    def person_from_email(self, person_email):
        """
        Returns the same JSON dictionary as the person() method, but found
        by email address rather than ID number.
        """
        api_url   = "/api/v1/person/email/" + person_email + "/"
        response  = self.session.get(self.base_url + api_url, verify=True)
        if response.status_code == 200:
            person_id = response.json()['person'].replace("/api/v1/person/person/", "").rstrip('/')
            return self.person(person_id)
        else:
            return None

    def people(self, since="1970-01-01T00:00:00", until="2038-01-19T03:14:07", name_contains=None):
        """
        A generator that returns JSON objects representing all people recorded
        in the datatracker. As of 29 April 2018, there are approximately 21500
        people recorded. The since and until parameters can be used to contrain
        the output to only entries with timestamps in a particular time range.
        If provided, name_contains filters based on the whether the name field
        contains the specified value.
        """
        api_url = "/api/v1/person/person/?time__gt=" + since + "&time__lt=" + until
        if name_contains != None:
            api_url = api_url + "&name__contains=" + name_contains
        while api_url != None:
            r = self.session.get(self.base_url + api_url, verify=True)
            meta = r.json()['meta']
            objs = r.json()['objects']
            api_url = meta['next']
            for obj in objs:
                self._people[obj['id']] = obj
                yield obj

    # Datatracker API endpoints returning information about documents:
    # * https://datatracker.ietf.org/api/v1/doc/document/                        - list of documents
    # * https://datatracker.ietf.org/api/v1/doc/document/draft-ietf-avt-rtp-new/ - info about document
    #   https://datatracker.ietf.org/api/v1/doc/docevent/                        - list of document events
    #   https://datatracker.ietf.org/api/v1/doc/docevent/?doc=...                - events for a document
    #   https://datatracker.ietf.org/api/v1/doc/docevent/?by=...                 - events by a person (as /api/v1/person/person)
    #   https://datatracker.ietf.org/api/v1/doc/docevent/?time=...               - events by time
    #   https://datatracker.ietf.org/api/v1/doc/statedocevent/                   - subset of /api/v1/doc/docevent/; same parameters
    #   https://datatracker.ietf.org/api/v1/doc/ballotdocevent/                  -               "                "
    #   https://datatracker.ietf.org/api/v1/doc/newrevisiondocevent/             -               "                "
    #   https://datatracker.ietf.org/api/v1/doc/submissiondocevent/              -               "                "
    #   https://datatracker.ietf.org/api/v1/doc/writeupdocevent/                 -               "                "
    #   https://datatracker.ietf.org/api/v1/doc/consensusdocevent/               -               "                "
    #   https://datatracker.ietf.org/api/v1/doc/ballotpositiondocevent/          -               "                "
    #   https://datatracker.ietf.org/api/v1/doc/reviewrequestdocevent/           -               "                "
    #   https://datatracker.ietf.org/api/v1/doc/lastcalldocevent/                -               "                "
    #   https://datatracker.ietf.org/api/v1/doc/telechatdocevent/                -               "                "
    #   https://datatracker.ietf.org/api/v1/doc/documentauthor/?document=...     - authors of a document
    #   https://datatracker.ietf.org/api/v1/doc/documentauthor/?person=...       - documents by person (as /api/v1/person/person)
    #   https://datatracker.ietf.org/api/v1/doc/documentauthor/?email=...        - documents by person with particular email
    #   https://datatracker.ietf.org/api/v1/doc/relateddocument/?source=...      - documents that source draft relates to (references, replaces, etc)
    #   https://datatracker.ietf.org/api/v1/doc/relateddocument/?target=...      - documents that relate to target draft
    # * https://datatracker.ietf.org/api/v1/doc/docalias/rfcXXXX/                - draft that became the given RFC
    #   https://datatracker.ietf.org/api/v1/doc/docalias/bcpXXXX/                - draft that became the given BCP
    #   https://datatracker.ietf.org/api/v1/doc/docalias/stdXXXX/                - RFC that is the given STD
    # * https://datatracker.ietf.org/api/v1/doc/state/                           - Types of state a document can be in
    #   https://datatracker.ietf.org/api/v1/doc/ballottype/                      - Types of ballot that can be issued on a document
    #
    #   https://datatracker.ietf.org/api/v1/doc/relateddochistory/
    #   https://datatracker.ietf.org/api/v1/doc/dochistoryauthor/
    #   https://datatracker.ietf.org/api/v1/doc/initialreviewdocevent/
    #   https://datatracker.ietf.org/api/v1/doc/deletedevent/
    #   https://datatracker.ietf.org/api/v1/doc/addedmessageevent/
    #   https://datatracker.ietf.org/api/v1/doc/documenturl/
    #   https://datatracker.ietf.org/api/v1/doc/docreminder/
    # * https://datatracker.ietf.org/api/v1/doc/statetype/                       - Possible types of state for a document
    #   https://datatracker.ietf.org/api/v1/doc/editedauthorsdocevent/
    #   https://datatracker.ietf.org/api/v1/doc/dochistory/

    def __fix_document(self, document):
        if document['std_level'] != None:
            document['std_level'] = document['std_level'].replace("/api/v1/name/stdlevelname/", "").rstrip('/')
        if document['intended_std_level'] != None:
            document['intended_std_level'] = document['intended_std_level'].replace("/api/v1/name/intendedstdlevelname/", "").rstrip('/')
        if document['group'] != None:
            document['group']  = document['group'].replace("/api/v1/group/group/", "").rstrip('/')
        if document['type'] != None:
            document['type']   = document['type'].replace("/api/v1/name/doctypename/", "").rstrip('/')
        if document['stream'] != None:
            document['stream'] = document['stream'].replace("/api/v1/name/streamname/", "").rstrip('/')
        if document['ad'] != None:
            document['ad'] = document['ad'].replace("/api/v1/person/person/", "").rstrip('/')
        if document['shepherd'] != None:
            document['shepherd'] = document['shepherd'].replace("/api/v1/person/person/", "").rstrip('/')
        document['submissions'] = list(map(lambda s : s.replace("/api/v1/submit/submission/", "").rstrip('/'), document['submissions']))
        document['states']      = list(map(lambda s : s.replace("/api/v1/doc/state/",         "").rstrip('/'), document['states']))
        document['tags']        = list(map(lambda s : s.replace("/api/v1/name/doctagname/",   "").rstrip('/'), document['tags']))
        return document

    def documents(self, since="1970-01-01T00:00:00", until="2038-01-19T03:14:07", doctype="", group=""):
        """
        A generator that returns JSON objects representing all documents
        recorded in the datatracker. As of 29 April 2018, approximately
        84000 documents are recorded. The since and until parameters can
        be used to contrain output to only those entries with timestamps
        in a particular time range. 

        The doctype parameter can be one of:
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
        and will constrain the type of document returned. 

        The group can be a group identifier, as used by the group() method, and
        will constrain the results to documents from the specified group.

        The JSON objects returned are the same format as those returned by the 
        document() method.
        """
        api_url   = "/api/v1/doc/document/?time__gt=" + since + "&time__lt=" + until 
        if doctype != "":
            api_url = api_url + "&type=" + doctype
        if group != "":
            api_url = api_url + "&group=" + group
        print(api_url)
        while api_url != None:
            r = self.session.get(self.base_url + api_url, verify=True)
            meta = r.json()['meta']
            objs = r.json()['objects']
            api_url = meta['next']
            for obj in objs:
                self._documents[obj['name']] = obj
                yield self.__fix_document(obj)

    def document(self, name):
        """
        Returns a JSON object representing a document identified by name, for example:
            {
               "states" : [ '1', '38' ],
               "rev" : "11",
               "name" : "draft-ietf-quic-transport",
               "intended_std_level" : "ps",
               "std_level" : null,
               "pages" : 105,
               "abstract" : "This document defines the core of the QUIC transport protocol...",
               "type" : "draft",
               "rfc" : null,
               "group" : "2161",
               "external_url" : "",
               "resource_uri" : "/api/v1/doc/document/draft-ietf-quic-transport/",
               "tags" : [],
               "shepherd" : null,
               "order" : 1,
               "stream" : "ietf",
               "expires" : "2018-10-19T16:10:12",
               "ad" : null,
               "notify" : "",
               "title" : "QUIC: A UDP-Based Multiplexed and Secure Transport",
               "words" : 24198,
               "internal_comments" : "",
               "submissions" : [
                  '82995', '83773', '85557', '86717', '87084', '88860',
                  '89569', '89982', '91554', '92517', '93617', '94830'
               ],
               "time" : "2018-04-17T16:10:12",
               "note" : ""
            }
        The document_state() method can be used to get additional information on states.
        The group() method can be used to get additional information on the group.
        The submissions() method can be used to get additional information on submissions.
        """
        if name not in self._documents:
            api_url  = "/api/v1/doc/document/" + name + "/"
            response = self.session.get(self.base_url + api_url, verify=True)
            if response.status_code == 200:
                self._documents[name] = self.__fix_document(response.json())
            else:
                return None
        return self._documents[name]

    def document_from_rfc(self, rfc):
        """
        Returns the document that became the specified RFC.
        The rfc parameter is of the form "rfc3550".
        """
        api_url  = "/api/v1/doc/docalias/" + rfc + "/"
        response = self.session.get(self.base_url + api_url, verify=True)
        if response.status_code == 200:
            name = response.json()['document'].replace("/api/v1/doc/document/", "").rstrip('/')
            return self.document(name)
        else:
            return None

    def document_state(self, state):
        """
        Returns a JSON object representing the state of a document, for example:
            {
              'desc': 'The ID has been published as an RFC.', 
              'id': 7, 
              'name': 'RFC Published', 
              'next_states': ['8'], 
              'order': 32, 
              'resource_uri': '/api/v1/doc/state/7/', 
              'slug': 'pub', 
              'type': 'draft-iesg', 
              'used': True
            }
        The state parameter is one of the 'states' from a document object.
        """
        if state not in self._states:
            api_url  = "/api/v1/doc/state/" + state
            response = self.session.get(self.base_url + api_url, verify=True)
            if response.status_code == 200:
                resp = response.json()
                resp['next_states'] = list(map(lambda s : s.replace("/api/v1/doc/state/", "").rstrip('/'), resp['next_states']))
                resp['type']        = resp['type'].replace("/api/v1/doc/statetype/", "").rstrip('/')
                self._states[state] = resp
            else:
                return None
        return self._states[state]

    def document_states(self, statetype=""):
        """
        A generator returning the possible states a document can be in.
        Each element is a state, as returned by document_state(). 
        The statetype parameter allows subsetting of the possible states,
        for example specifying statetype="draft-rfceditor" returns the
        states a document can be in during RFC Editor processing.
        """
        api_url   = "/api/v1/doc/state/"
        if statetype != "":
            api_url = api_url + "?type=" + statetype
        while api_url != None:
            r = self.session.get(self.base_url + api_url, verify=True)
            meta = r.json()['meta']
            objs = r.json()['objects']
            api_url = meta['next']
            for obj in objs:
                obj['next_states'] = list(map(lambda s : s.replace("/api/v1/doc/state/", "").rstrip('/'), obj['next_states']))
                obj['type']        = obj['type'].replace("/api/v1/doc/statetype/", "").rstrip('/')
                self._states[obj['id']] = obj
                yield obj

    def document_state_types(self):
        """
        A generator returning possible state types for a document.
        These are the possible values of the 'type' field in the 
        output of document_state(), or the statetype parameter to
        document_states().
        """
        api_url   = "/api/v1/doc/statetype/"
        while api_url != None:
            r = self.session.get(self.base_url + api_url, verify=True)
            meta = r.json()['meta']
            objs = r.json()['objects']
            api_url = meta['next']
            for obj in objs:
                yield obj['slug']

    def submission(self, submission):
        """
        Returns a JSON object giving information about a document submission.
        """
        if submission not in self._submissions:
            api_url = "/api/v1/submit/submission/" + submission + "/"
            response = self.session.get(self.base_url + api_url, verify=True)
            if response.status_code == 200:
                resp = response.json()
                resp['group'] = resp['group'].replace("/api/v1/group/group/", "").rstrip('/')
                # FIXME: there is more tidying that can be done here
                self._submissions[submission] = resp
            else:
                return None
        return self._submissions[submission]

    # Datatracker API endpoints returning information about working groups:
    #   https://datatracker.ietf.org/api/v1/group/group/                               - list of groups
    #   https://datatracker.ietf.org/api/v1/group/group/2161/                          - info about group 2161
    #   https://datatracker.ietf.org/api/v1/group/grouphistory/?group=2161             - history
    #   https://datatracker.ietf.org/api/v1/group/groupurl/?group=2161                 - URLs
    #   https://datatracker.ietf.org/api/v1/group/groupevent/?group=2161               - events
    #   https://datatracker.ietf.org/api/v1/group/groupmilestone/?group=2161           - Current milestones
    #   https://datatracker.ietf.org/api/v1/group/groupmilestonehistory/?group=2161    - Previous milestones
    #   https://datatracker.ietf.org/api/v1/group/milestonegroupevent/?group=2161      - changed milestones
    #   https://datatracker.ietf.org/api/v1/group/role/?group=2161                     - The current WG chairs and ADs of a group
    #   https://datatracker.ietf.org/api/v1/group/role/?person=20209                   - Groups a person is currently involved with
    #   https://datatracker.ietf.org/api/v1/group/role/?email=csp@csperkins.org        - Groups a person is currently involved with
    #   https://datatracker.ietf.org/api/v1/group/rolehistory/?group=2161              - The previous WG chairs and ADs of a group
    #   https://datatracker.ietf.org/api/v1/group/rolehistory/?person=20209            - Groups person was previously involved with
    #   https://datatracker.ietf.org/api/v1/group/rolehistory/?email=csp@csperkins.org - Groups person was previously involved with
    #   https://datatracker.ietf.org/api/v1/group/changestategroupevent/?group=2161    - Group state changes
    #   https://datatracker.ietf.org/api/v1/group/groupstatetransitions                - ???

    def group(self, group_id):
        # FIXME
        pass

    # Datatracker API endpoints returning information about meetings:
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

# =============================================================================
# Unit tests:

class TestDatatracker(unittest.TestCase):
    def test_person(self):
        dt = DataTracker()
        p1 = dt.person("20209")
        self.assertEqual(p1['ascii'], 'Colin Perkins')
        self.assertEqual(p1['ascii_short'], '')
        self.assertEqual(p1['biography'], '')
        self.assertEqual(p1['consent'], None)
        self.assertEqual(p1['id'], 20209)
        self.assertEqual(p1['name'], 'Colin Perkins')
        self.assertEqual(p1['name_from_draft'], 'Colin Perkins')
        self.assertEqual(p1['photo'], None)
        self.assertEqual(p1['photo_thumb'], None)
        self.assertEqual(p1['resource_uri'], '/api/v1/person/person/20209/')
        self.assertEqual(p1['time'], '2012-02-26T00:03:54')
        self.assertEqual(p1['user'], '')

    def test_person_from_email(self):
        dt = DataTracker()
        p1 = dt.person_from_email("ietf@trammell.ch")
        self.assertEqual(p1['ascii'], 'Brian Trammell')
        self.assertEqual(p1['ascii_short'], '')
        self.assertEqual(p1['biography'], 
                "Brian Trammell is a Senior Researcher at the Networked "
                "Systems and Network Security Groups at the Swiss Federal "
                "Institute of Technology (ETH) Zurich. His primary focus "
                "is on network monitoring and measurement, specifically "
                "on performance measurement, security monitoring, "
                "measurement tools, and privacy issues in measurement and "
                "management. Active in the IETF since 2005, he's co-authored "
                "19 RFCs in various areas. He co-chairs the IP Performance "
                "Meaurement working group and the Path Aware Networking "
                "Research Group. Prior to his work with CSG, he was Engineering "
                "Technical Lead at the CERT Network Situational Awareness "
                "group, and a veteran of a variety of short-lived Internet "
                "start-ups. He earned a BS in Computer Science from Georgia "
                "Tech in 2000.")
        self.assertEqual(p1['consent'], None)
        self.assertEqual(p1['id'], 109354)
        self.assertEqual(p1['name'], 'Brian Trammell')
        self.assertEqual(p1['name_from_draft'], 'Brian Trammell')
        self.assertEqual(p1['photo'], 'https://www.ietf.org/lib/dt/media/photo/Brian_Trammell-2-800px.jpg')
        self.assertEqual(p1['photo_thumb'], 'https://www.ietf.org/lib/dt/media/photo/Brian_Trammell-2-800px_UrxVEEk.jpg')
        self.assertEqual(p1['resource_uri'], '/api/v1/person/person/109354/')
        self.assertEqual(p1['time'], '2012-02-26T00:04:12')
        self.assertEqual(p1['user'], '')

    def test_people(self):
        dt = DataTracker()
        people = list(dt.people(since="2018-04-01T00:00:00", until="2018-04-30T23:59:59"))
        self.assertEqual(people[ 0]['name'], 'Kazumasa Ikuta')
        self.assertEqual(people[ 1]['name'], 'Denaya Dennis')
        self.assertEqual(people[ 2]['name'], 'Michael Slusarz')
        self.assertEqual(people[ 3]['name'], 'Ethan Grossman')
        self.assertEqual(people[ 4]['name'], 'Md. Nasim Parvez')
        self.assertEqual(people[ 5]['name'], 'Kouhei Ueno')
        self.assertEqual(people[ 6]['name'], 'Pw Carey')
        self.assertEqual(people[ 7]['name'], 'Benjamin Phister')
        self.assertEqual(people[ 8]['name'], 'Jean-Emmanuel Rodriguez')
        self.assertEqual(people[ 9]['name'], 'Øyvind Rønningstad')
        self.assertEqual(people[10]['name'], 'Tomonobu Niwa')
        self.assertEqual(people[11]['name'], 'Shuang Zhou')
        self.assertEqual(people[12]['name'], 'Xiangkai Meng')
        self.assertEqual(people[13]['name'], 'Rong Ma')
        self.assertEqual(people[14]['name'], 'Ralf Dorfner')
        self.assertEqual(people[15]['name'], 'Giorgio Campo')
        self.assertEqual(people[16]['name'], 'Scott Arciszewski')
        self.assertEqual(people[17]['name'], 'Steven Haussmann')
        self.assertEqual(people[18]['name'], 'praneet kaur')
        self.assertEqual(people[19]['name'], 'Selu Kauvaka')
        self.assertEqual(people[20]['name'], 'Farha Diba')
        self.assertEqual(people[21]['name'], 'Yang Xia')

    def test_document(self):
        dt = DataTracker()
        d1 = dt.document("draft-ietf-avt-rtp-cnames")
        self.assertEqual(d1['abstract'], 
                "The RTP Control Protocol (RTCP) Canonical Name (CNAME) "
                "is a persistent transport-level identifier for an RTP "
                "endpoint.  While the Synchronization Source (SSRC) "
                "identifier of an RTP endpoint may change if a collision "
                "is detected or when the RTP application is restarted, "
                "its RTCP CNAME is meant to stay unchanged, so that RTP "
                "endpoints can be uniquely identified and associated with "
                "their RTP media streams.  For proper functionality, RTCP "
                "CNAMEs should be unique within the participants of an RTP "
                "session.  However, the existing guidelines for choosing "
                "the RTCP CNAME provided in the RTP standard are insufficient "
                "to achieve this uniqueness.  This memo updates those guidelines "
                "to allow endpoints to choose unique RTCP CNAMEs. [STANDARDS-TRACK]")
        self.assertEqual(d1['ad'], '103961')
        self.assertEqual(d1['expires'], '2011-07-29T13:20:08')
        self.assertEqual(d1['external_url'], '')
        self.assertEqual(d1['group'], '941')
        self.assertEqual(d1['intended_std_level'], 'ps')
        self.assertEqual(d1['internal_comments'], '')
        self.assertEqual(d1['name'], 'draft-ietf-avt-rtp-cnames')
        self.assertEqual(d1['note'], '')
        self.assertEqual(d1['notify'], '')
        self.assertEqual(d1['order'], 1)
        self.assertEqual(d1['pages'], 9)
        self.assertEqual(d1['resource_uri'], '/api/v1/doc/document/draft-ietf-avt-rtp-cnames/')
        self.assertEqual(d1['rev'], '05')
        self.assertEqual(d1['rfc'], '6222')
        self.assertEqual(d1['shepherd'], None)
        self.assertEqual(d1['states'], ['3', '110', '7'])
        self.assertEqual(d1['std_level'], 'ps')
        self.assertEqual(d1['stream'], 'ietf')
        self.assertEqual(d1['submissions'], ['24225', '26079', '28348', '29011', '29371', '29711'])
        self.assertEqual(d1['tags'], ['app-min'])
        self.assertEqual(d1['time'], '2015-10-14T13:52:19')
        self.assertEqual(d1['title'], 'Guidelines for Choosing RTP Control Protocol (RTCP) Canonical Names (CNAMEs)')
        self.assertEqual(d1['type'], 'draft')
        self.assertEqual(d1['words'], 2627)

    def test_documents(self):
        dt = DataTracker()
        documents = list(dt.documents(since="2018-04-27T00:00:00", until="2018-05-31T23:59:59", doctype="draft", group="2161"))
        for doc in documents:
            print(doc['name'])
        self.assertEqual(documents[0]['name'], 'draft-ietf-quic-transport')
        self.assertEqual(documents[1]['name'], 'draft-ietf-quic-recovery')
        self.assertEqual(documents[2]['name'], 'draft-ietf-quic-tls')
        self.assertEqual(documents[3]['name'], 'draft-ietf-quic-http')
        self.assertEqual(documents[4]['name'], 'draft-ietf-quic-qpack')
        self.assertEqual(documents[5]['name'], 'draft-ietf-quic-invariants')
        self.assertEqual(documents[6]['name'], 'draft-ietf-quic-applicability')
        self.assertEqual(documents[7]['name'], 'draft-ietf-quic-manageability')

    def test_document_from_rfc(self):
        dt = DataTracker()
        d  = dt.document_from_rfc("rfc3550")
        self.assertEqual(d['abstract'], 
            "This memorandum describes RTP, the real-time transport protocol.  "
            "RTP provides end-to-end network transport functions suitable for "
            "applications transmitting real-time data, such as audio, video or "
            "simulation data, over multicast or unicast network services.  RTP "
            "does not address resource reservation and does not guarantee "
            "quality-of- service for real-time services.  The data transport is "
            "augmented by a control protocol (RTCP) to allow monitoring of the "
            "data delivery in a manner scalable to large multicast networks, "
            "and to provide minimal control and identification functionality.  "
            "RTP and RTCP are designed to be independent of the underlying "
            "transport and network layers.  The protocol supports the use of "
            "RTP-level translators and mixers.  Most of the text in this memorandum "
            "is identical to RFC 1889 which it obsoletes.  There are no changes in "
            "the packet formats on the wire, only changes to the rules and "
            "algorithms governing how the protocol is used.  The biggest change is "
            "an enhancement to the scalable timer algorithm for calculating when "
            "to send RTCP packets in order to minimize transmission in excess of "
            "the intended rate when many participants join a session simultaneously. "
            "[STANDARDS-TRACK]")
        self.assertEqual(d['ad'], '2515')
        self.assertEqual(d['expires'], '2003-09-08T00:00:12')
        self.assertEqual(d['external_url'], '')
        self.assertEqual(d['group'], '941')
        self.assertEqual(d['intended_std_level'], 'std')
        self.assertEqual(d['internal_comments'], '')
        self.assertEqual(d['name'], 'draft-ietf-avt-rtp-new')
        self.assertEqual(d['note'], '')
        self.assertEqual(d['notify'], 'magnus.westerlund@ericsson.com, csp@csperkins.org')
        self.assertEqual(d['order'], 1)
        self.assertEqual(d['pages'], 104)
        self.assertEqual(d['resource_uri'], '/api/v1/doc/document/draft-ietf-avt-rtp-new/')
        self.assertEqual(d['rev'], '12')
        self.assertEqual(d['rfc'], '3550')
        self.assertEqual(d['shepherd'], None)
        self.assertEqual(d['states'], ['3', '7'])
        self.assertEqual(d['std_level'], 'std')
        self.assertEqual(d['stream'], 'ietf')
        self.assertEqual(d['submissions'], [])
        self.assertEqual(d['tags'], ['app-min', 'errata'])
        self.assertEqual(d['time'], '2015-10-14T13:49:52')
        self.assertEqual(d['title'], 'RTP: A Transport Protocol for Real-Time Applications')
        self.assertEqual(d['type'], 'draft')
        self.assertEqual(d['words'], 34861)

    def test_document_state(self):
        dt = DataTracker()
        s = dt.document_state('7')
        self.assertEqual(s['desc'], 'The ID has been published as an RFC.')
        self.assertEqual(s['id'], 7)
        self.assertEqual(s['name'], 'RFC Published')
        self.assertEqual(s['next_states'], ['8'])
        self.assertEqual(s['order'], 32)
        self.assertEqual(s['resource_uri'], '/api/v1/doc/state/7/')
        self.assertEqual(s['slug'], 'pub')
        self.assertEqual(s['type'], 'draft-iesg')
        self.assertEqual(s['used'], True)

    def test_document_states(self):
        dt = DataTracker()
        states = list(dt.document_states(statetype="draft-rfceditor"))
        self.assertEqual(states[ 0]['name'], 'AUTH')
        self.assertEqual(states[ 1]['name'], 'AUTH48')
        self.assertEqual(states[ 2]['name'], 'EDIT')
        self.assertEqual(states[ 3]['name'], 'IANA')
        self.assertEqual(states[ 4]['name'], 'IESG')
        self.assertEqual(states[ 5]['name'], 'ISR')
        self.assertEqual(states[ 6]['name'], 'ISR-AUTH')
        self.assertEqual(states[ 7]['name'], 'REF')
        self.assertEqual(states[ 8]['name'], 'RFC-EDITOR')
        self.assertEqual(states[ 9]['name'], 'TO')
        self.assertEqual(states[10]['name'], 'MISSREF')
        self.assertEqual(states[11]['name'], 'AUTH48-DONE')
        self.assertEqual(states[12]['name'], 'AUTH48-DONE')
        self.assertEqual(states[13]['name'], 'EDIT')
        self.assertEqual(states[14]['name'], 'IANA')
        self.assertEqual(states[15]['name'], 'IESG')
        self.assertEqual(states[16]['name'], 'ISR-AUTH')
        self.assertEqual(states[17]['name'], 'Pending')

    def test_document_state_types(self):
        dt = DataTracker()
        st = list(dt.document_state_types())
        self.assertEqual(st[ 0], 'draft')
        self.assertEqual(st[ 1], 'draft-iesg')
        self.assertEqual(st[ 2], 'draft-iana')
        self.assertEqual(st[ 3], 'draft-rfceditor')
        self.assertEqual(st[ 4], 'draft-stream-ietf')
        self.assertEqual(st[ 5], 'draft-stream-irtf')
        self.assertEqual(st[ 6], 'draft-stream-ise')
        self.assertEqual(st[ 7], 'draft-stream-iab')
        self.assertEqual(st[ 8], 'slides')
        self.assertEqual(st[ 9], 'minutes')
        self.assertEqual(st[10], 'agenda')
        self.assertEqual(st[11], 'liai-att')
        self.assertEqual(st[12], 'charter')
        self.assertEqual(st[13], 'conflrev')
        self.assertEqual(st[14], 'draft-iana-action')
        self.assertEqual(st[15], 'draft-iana-review')
        self.assertEqual(st[16], 'statchg')
        self.assertEqual(st[17], 'recording')
        self.assertEqual(st[18], 'bluesheets')
        self.assertEqual(st[19], 'reuse_policy')
        self.assertEqual(st[20], 'review')
        self.assertEqual(st[21], 'liaison')
        self.assertEqual(st[22], 'shepwrit')

    def test_submission(self):
        dt = DataTracker()
        sub = dt.submission('24225')
        self.assertEqual(sub['abstract'], 
                "The RTP Control Protocol (RTCP) Canonical Name (CNAME) "
                "is a\npersistent transport-level identifier for an RTP "
                "endpoint.  While the\nSynchronization Source (SSRC) "
                "identifier of an RTP endpoint may\nchange if a collision "
                "is detected, or when the RTP application is\nrestarted, "
                "the CNAME is meant to stay unchanged, so that RTP\nendpoints "
                "can be uniquely identified and associated with their RTP\nmedia "
                "streams.  For proper functionality, CNAMEs should be unique\nwithin "
                "the participants of an RTP session.  However, the existing\nguidelines "
                "for choosing the RTCP CNAME provided in the RTP standard\nare "
                "insufficient to achieve this uniqueness.  This memo updates "
                "these\nguidelines to allow endpoints to choose unique CNAMEs.")
        self.assertEqual(sub['access_key'], '1239ae6d3007119bcf2750bd339c74bf')
        self.assertEqual(sub['auth_key'], '4UWACQOq4MDvQdXVkJwMkQ0Io6ykT0Ox')
        self.assertEqual(sub['authors'], 
                "[{u'email': u'abegen@cisco.com', u'name': u'Ali Begen'}, "
                "{u'email': u'csp@csperkins.org', u'name': u'Colin Perkins'}, "
                "{u'email': u'dwing@cisco.com', u'name': u'Dan Wing'}]")
        self.assertEqual(sub['checks'], ['/api/v1/submit/submissioncheck/22209/'])
        self.assertEqual(sub['document_date'], '2010-06-17')
        self.assertEqual(sub['draft'], '/api/v1/doc/document/draft-ietf-avt-rtp-cnames/')
        self.assertEqual(sub['file_size'], 15711)
        self.assertEqual(sub['file_types'], '.txt')
        self.assertEqual(sub['first_two_pages'], 
                '\n'
                '\n'
                '\n'
                'AVT                                                             A. Begen\n'
                'Internet-Draft                                                     Cisco\n'
                'Updates:  3550 (if approved)                                  C. Perkins\n'
                'Intended status:  Standards Track                  University of Glasgow\n'
                'Expires:  December 19, 2010                                      D. Wing\n'
                '                                                                   Cisco\n'
                '                                                           June 17, 2010\n'
                '\n'
                '\n'
                '  Guidelines for Choosing RTP Control Protocol (RTCP) Canonical Names\n'
                '                                (CNAMEs)\n'
                '                      draft-ietf-avt-rtp-cnames-00\n'
                '\n'
                'Abstract\n'
                '\n'
                '   The RTP Control Protocol (RTCP) Canonical Name (CNAME) is a\n'
                '   persistent transport-level identifier for an RTP endpoint.  While the\n'
                '   Synchronization Source (SSRC) identifier of an RTP endpoint may\n'
                '   change if a collision is detected, or when the RTP application is\n'
                '   restarted, the CNAME is meant to stay unchanged, so that RTP\n'
                '   endpoints can be uniquely identified and associated with their RTP\n'
                '   media streams.  For proper functionality, CNAMEs should be unique\n'
                '   within the participants of an RTP session.  However, the existing\n'
                '   guidelines for choosing the RTCP CNAME provided in the RTP standard\n'
                '   are insufficient to achieve this uniqueness.  This memo updates these\n'
                '   guidelines to allow endpoints to choose unique CNAMEs.\n'
                '\n'
                'Status of this Memo\n'
                '\n'
                '   This Internet-Draft is submitted in full conformance with the\n'
                '   provisions of BCP 78 and BCP 79.\n'
                '\n'
                '   Internet-Drafts are working documents of the Internet Engineering\n'
                '   Task Force (IETF).  Note that other groups may also distribute\n'
                '   working documents as Internet-Drafts.  The list of current Internet-\n'
                '   Drafts is at http://datatracker.ietf.org/drafts/current/.\n'
                '\n'
                '   Internet-Drafts are draft documents valid for a maximum of six months\n'
                '   and may be updated, replaced, or obsoleted by other documents at any\n'
                '   time.  It is inappropriate to use Internet-Drafts as reference\n'
                '   material or to cite them other than as "work in progress."\n'
                '\n   This Internet-Draft will expire on December 19, 2010.\n'
                '\n'
                'Copyright Notice\n'
                '\n'
                '   Copyright (c) 2010 IETF Trust and the persons identified as the\n'
                '   document authors.  All rights reserved.\n'
                '\n'
                '\n'
                '\n'
                'Begen, et al.           Expires December 19, 2010               [page 1]\n'
                '\n'
                'Internet-Draft            Choosing RTCP CNAMEs                 June 2010\n'
                '\n'
                '\n'
                '   This document is subject to BCP 78 and the IETF Trust\'s Legal\n'
                '   Provisions Relating to IETF Documents\n'
                '   (http://trustee.ietf.org/license-info) in effect on the date of\n'
                '   publication of this document.  Please review these documents\n'
                '   carefully, as they describe your rights and restrictions with respect\n'
                '   to this document.  Code Components extracted from this document must\n'
                '   include Simplified BSD License text as described in Section 4.e of\n'
                '   the Trust Legal Provisions and are provided without warranty as\n'
                '   described in the Simplified BSD License.\n'
                '\n'
                '\n'
                'Table of Contents\n'
                '\n'
                '   1.  Introduction  . . . . . . . . . . . . . . . . . . . . . . . . . 3\n'
                '   2.  Requirements Notation . . . . . . . . . . . . . . . . . . . . . 3\n'
                '   3.  Deficiencies with Earlier RTCP CNAME Guidelines . . . . . . . . 3\n'
                '   4.  Choosing an RTCP CNAME  . . . . . . . . . . . . . . . . . . . . 4\n'
                '     4.1.  Persistent vs. Per-Session CNAMEs . . . . . . . . . . . . . 4\n'
                '     4.2.  Guidelines  . . . . . . . . . . . . . . . . . . . . . . . . 5\n'
                '   5.  Security Considerations . . . . . . . . . . . . . . . . . . . . 6\n'
                '   6.  IANA Considerations . . . . . . . . . . . . . . . . . . . . . . 6\n'
                '   7.  Acknowledgments . . . . . . . . . . . . . . . . . . . . . . . . 6\n'
                '   8.  References  . . . . . . . . . . . . . . . . . . . . . . . . . . 6\n'
                '     8.1.  Normative References  . . . . . . . . . . . . . . . . . . . 6\n'
                '     8.2.  Informative References  . . . . . . . . . . . . . . . . . . 7\n'
                '   Authors\' Addresses  . . . . . . . . . . . . . . . . . . . . . . . . 7\n'
                '\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
                'Begen, et al.           Expires December 19, 2010               [page 2]')
        self.assertEqual(sub['group'], '941')
        self.assertEqual(sub['id'], 24225)
        self.assertEqual(sub['name'], 'draft-ietf-avt-rtp-cnames')
        self.assertEqual(sub['note'], '')
        self.assertEqual(sub['pages'], 8)
        self.assertEqual(sub['remote_ip'], '128.107.239.233')
        self.assertEqual(sub['replaces'], '')
        self.assertEqual(sub['resource_uri'], '/api/v1/submit/submission/24225/')
        self.assertEqual(sub['rev'], '00')
        self.assertEqual(sub['state'], '/api/v1/name/draftsubmissionstatename/posted/')
        self.assertEqual(sub['submission_date'], '2010-06-17')
        self.assertEqual(sub['submitter'], 'Ali C. Begen')
        self.assertEqual(sub['title'], 'Guidelines for Choosing RTP Control Protocol (RTCP) Canonical Names (CNAMEs)')
        self.assertEqual(sub['words'], None)

if __name__ == '__main__':
    unittest.main()

# =============================================================================
