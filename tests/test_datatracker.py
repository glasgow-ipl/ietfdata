# Copyright (C) 2017-2021 University of Glasgow
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
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT thirdpartyS AND CONTRIBUTORS "AS IS"
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

import unittest
import os
import sys

from datetime      import date, datetime, timedelta, timezone
from pathlib       import Path
from unittest.mock import patch, Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import ietfdata
from ietfdata.datatracker import *


# =================================================================================================================================
# Unit tests:

class TestDatatracker(unittest.TestCase):
    dt : DataTracker

    @classmethod
    def setUpClass(self) -> None:
        self.dt = DataTracker(cache_dir = "cache", cache_timeout = timedelta(minutes = 15))

    # -----------------------------------------------------------------------------------------------------------------------------
    # Tests relating to the datatracker access layer:

    def test__datatracker_get_single(self) -> None:
        json = self.dt._datatracker_get_single(URI(uri="/api/v1/person/email/csp@csperkins.org/"))
        if json is not None:
            self.assertEqual(json["resource_uri"], "/api/v1/person/email/csp@csperkins.org/")
            self.assertEqual(json["address"],      "csp@csperkins.org")
            self.assertEqual(json["person"],       "/api/v1/person/person/20209/")
            self.assertEqual(json["time"],         "1970-01-02T07:59:59Z")
            self.assertEqual(json["primary"],      True)
            self.assertEqual(json["active"],       True)
        else:
            self.fail("Cannot retrieve single JSON item")


    def test__datatracker_get_multi_small(self) -> None:
        url = URI(uri="/api/v1/doc/document/")
        url.params["group"] = 1963
        url.params["type"]  = "draft"
        json = list(self.dt._datatracker_get_multi(url, "id"))
        self.assertEqual(len(json), 2)
        self.assertEqual(json[0][  "id"], 63980)
        self.assertEqual(json[0]["name"], "draft-ietf-netvc-requirements")
        self.assertEqual(json[1][  "id"], 64020)
        self.assertEqual(json[1]["name"], "draft-ietf-netvc-testing")


    def test__datatracker_get_multi_large(self) -> None:
        url = URI(uri="/api/v1/meeting/meeting/")
        url.params["type"]  = "ietf"
        json = list(self.dt._datatracker_get_multi(url, "id"))
        self.assertGreaterEqual(len(json), 111)


    def test__datatracker_get_multi_count(self) -> None:
        count = self.dt._datatracker_get_multi_count(URI(uri="/api/v1/name/stdlevelname/"))
        self.assertEqual(count, 8)


    # -----------------------------------------------------------------------------------------------------------------------------
    # Tests relating to email addresses:

    def test_email(self) -> None:
        e  = self.dt.email(EmailURI(uri="/api/v1/person/email/csp@csperkins.org/"))
        if e is not None:
            self.assertEqual(e.resource_uri, EmailURI(uri="/api/v1/person/email/csp@csperkins.org/"))
            self.assertEqual(e.address,      "csp@csperkins.org")
            self.assertEqual(e.person,       PersonURI(uri="/api/v1/person/person/20209/"))
            self.assertEqual(e.time,         datetime.fromisoformat("1970-01-01T23:59:59-08:00"))
            # self.assertEqual(e.origin,     "author: draft-ietf-mmusic-rfc4566bis")
            self.assertEqual(e.primary,      True)
            self.assertEqual(e.active,       True)
        else:
            self.fail("Cannot find email address")


    def test_email_for_address(self) -> None:
        e  = self.dt.email_for_address("csp@csperkins.org")
        if e is not None:
            self.assertEqual(e.resource_uri, EmailURI(uri="/api/v1/person/email/csp@csperkins.org/"))
            self.assertEqual(e.address,      "csp@csperkins.org")
            self.assertEqual(e.person,       PersonURI(uri="/api/v1/person/person/20209/"))
            self.assertEqual(e.time,         datetime.fromisoformat("1970-01-01T23:59:59-08:00"))
            # self.assertEqual(e.origin,     "author: draft-ietf-mmusic-rfc4566bis")
            self.assertEqual(e.primary,      True)
            self.assertEqual(e.active,       True)
        else:
            self.fail("Cannot find email address")


    def test_email_for_person(self) -> None:
        p  = self.dt.person_from_email("csp@csperkins.org")
        if p is not None:
            es = list(self.dt.email_for_person(p))
            self.assertEqual(len(es), 5)
            self.assertEqual(es[0].address, "c.perkins@cs.ucl.ac.uk")
            self.assertEqual(es[1].address, "colin.perkins@glasgow.ac.uk")
            self.assertEqual(es[2].address, "csp@cperkins.net")
            self.assertEqual(es[3].address, "csp@csperkins.org")
            self.assertEqual(es[4].address, "csp@isi.edu")
        else:
            self.fail("Cannot find person")


    def test_email_history_for_address(self) -> None:
        h  = list(self.dt.email_history_for_address("csp@isi.edu"))
        self.assertEqual(len(h), 6)
        
        self.assertEqual(h[0].history_id, 167444)
        self.assertEqual(h[0].history_type, "~")
        self.assertEqual(h[0].history_change_reason, None)
        self.assertEqual(h[0].origin, "author: draft-ietf-avt-rtptest")
        self.assertEqual(h[0].address, "csp@isi.edu")
        self.assertEqual(h[0].active, False)
        self.assertEqual(h[0].person, PersonURI(uri="/api/v1/person/person/20209/"))
        self.assertEqual(h[0].time, datetime.fromisoformat("2012-02-26T00:46:44-08:00"))
        self.assertEqual(h[0].resource_uri, HistoricalEmailURI(uri="/api/v1/person/historicalemail/167444/"))
        self.assertEqual(h[0].primary, False)
        self.assertEqual(h[0].history_date, datetime.fromisoformat("2022-06-27T12:36:15-07:00"))
        self.assertEqual(h[0].history_user, "")
        
        self.assertEqual(h[1].history_id, 161025)
        self.assertEqual(h[1].history_type, "~")
        self.assertEqual(h[1].history_change_reason, None)
        self.assertEqual(h[1].origin, "author: draft-ietf-avt-rtptest")
        self.assertEqual(h[1].address, "csp@isi.edu")
        self.assertEqual(h[1].active, False)
        self.assertEqual(h[1].person, PersonURI(uri="/api/v1/person/person/20209/"))
        self.assertEqual(h[1].time, datetime.fromisoformat("2012-02-26T00:46:44-08:00"))
        self.assertEqual(h[1].resource_uri, HistoricalEmailURI(uri="/api/v1/person/historicalemail/161025/"))
        self.assertEqual(h[1].primary, False)
        self.assertEqual(h[1].history_date, datetime.fromisoformat("2022-04-19T14:40:37-07:00"))
        self.assertEqual(h[1].history_user, "")
        
        self.assertEqual(h[2].history_id, 128355)
        self.assertEqual(h[2].history_type, "~")
        self.assertEqual(h[2].history_change_reason, None)
        self.assertEqual(h[2].origin, "author: draft-ietf-avt-rtptest")
        self.assertEqual(h[2].address, "csp@isi.edu")
        self.assertEqual(h[2].active, False)
        self.assertEqual(h[2].person, PersonURI(uri="/api/v1/person/person/20209/"))
        self.assertEqual(h[2].time, datetime.fromisoformat("2012-02-26T00:46:44-08:00"))
        self.assertEqual(h[2].resource_uri, HistoricalEmailURI(uri="/api/v1/person/historicalemail/128355/"))
        self.assertEqual(h[2].primary, False)
        self.assertEqual(h[2].history_date, datetime.fromisoformat("2021-05-18T16:32:20-07:00"))
        self.assertEqual(h[2].history_user, "")
        
        self.assertEqual(h[3].history_id, 128350)
        self.assertEqual(h[3].history_change_reason, None)
        self.assertEqual(h[3].history_type, "~")
        self.assertEqual(h[3].origin, "author: draft-ietf-avt-rtptest")
        self.assertEqual(h[3].address, "csp@isi.edu")
        self.assertEqual(h[3].active, False)
        self.assertEqual(h[3].person, PersonURI(uri="/api/v1/person/person/20209/"))
        self.assertEqual(h[3].time, datetime.fromisoformat("2012-02-26T00:46:44-08:00"))
        self.assertEqual(h[3].resource_uri, HistoricalEmailURI(uri="/api/v1/person/historicalemail/128350/"))
        self.assertEqual(h[3].primary, False)
        self.assertEqual(h[3].history_user, "")
        self.assertEqual(h[3].history_date, datetime.fromisoformat("2021-05-18T16:30:53-07:00"))
        
        self.assertEqual(h[4].resource_uri, HistoricalEmailURI(uri="/api/v1/person/historicalemail/71987/"))
        self.assertEqual(h[4].address,      "csp@isi.edu")
        self.assertEqual(h[4].person,       PersonURI(uri="/api/v1/person/person/20209/"))
        self.assertEqual(h[4].origin,       "author: draft-ietf-avt-rtptest")
        self.assertEqual(h[4].time,         datetime.fromisoformat("2012-02-26T00:46:44-08:00"))
        self.assertEqual(h[4].active,       False)
        self.assertEqual(h[4].primary,      False)
        self.assertEqual(h[4].history_id,   71987)
        self.assertEqual(h[4].history_date, datetime.fromisoformat("2019-09-29T14:39:48-07:00"))
        self.assertEqual(h[4].history_type, "~")
        self.assertEqual(h[4].history_user, "")
        self.assertEqual(h[4].history_change_reason, None)
        
        self.assertEqual(h[5].resource_uri, HistoricalEmailURI(uri="/api/v1/person/historicalemail/2090/"))
        self.assertEqual(h[5].address,      "csp@isi.edu")
        self.assertEqual(h[5].person,       PersonURI(uri="/api/v1/person/person/20209/"))
        self.assertEqual(h[5].origin,       "author: draft-ietf-avt-rtptest")
        self.assertEqual(h[5].time,         datetime.fromisoformat("2012-02-26T00:46:44-08:00"))
        self.assertEqual(h[5].active,       False)
        self.assertEqual(h[5].primary,      False)
        self.assertEqual(h[5].history_id,   2090)
        self.assertEqual(h[5].history_date, datetime.fromisoformat("2018-06-19T15:39:40-07:00"))
        self.assertEqual(h[5].history_type, "~")
        self.assertEqual(h[5].history_user, "")
        self.assertEqual(h[5].history_change_reason, None)


    def test_email_history_for_person(self) -> None:
        p  = self.dt.person_from_email("casner@acm.org")
        if p is not None:
            h = list(self.dt.email_history_for_person(p))
            self.assertEqual(len(h), 4)
            self.assertEqual(h[0].address, "casner@acm.org")
            self.assertEqual(h[1].address, "casner@cisco.com")
            self.assertEqual(h[2].address, "casner@packetdesign.com")
            self.assertEqual(h[3].address, "casner@precept.com")
        else:
            self.fail("Cannot find person")


    def test_emails(self) -> None:
        e = list(self.dt.emails(addr_contains="csperkins.org"))
        self.assertEqual(len(e), 1)
        self.assertEqual(e[0].resource_uri, EmailURI(uri="/api/v1/person/email/csp@csperkins.org/"))


    # -----------------------------------------------------------------------------------------------------------------------------
    # Tests relating to people:

    def test_person_from_email(self) -> None:
        p  = self.dt.person_from_email("csp@csperkins.org")
        if p is not None:
            self.assertEqual(p.id,              20209)
            self.assertEqual(p.resource_uri,    PersonURI(uri="/api/v1/person/person/20209/"))
            self.assertEqual(p.name,            "Colin Perkins")
            self.assertEqual(p.name_from_draft, "Colin Perkins")
            self.assertEqual(p.ascii,           "Colin Perkins")
            self.assertEqual(p.ascii_short,     "")
            self.assertEqual(p.plain,           "")
            self.assertEqual(p.user,            "")
            self.assertEqual(p.time,            datetime.fromisoformat("2012-02-26T00:03:54-08:00"))
            self.assertEqual(p.photo,           "https://www.ietf.org/lib/dt/media/photo/csp-square.jpg")
            self.assertEqual(p.photo_thumb,     "https://www.ietf.org/lib/dt/media/photo/csp-square_GDMMZmn.jpg")
            # self.assertEqual(p.biography,     "Colin Perkins is a ...")
        else:
            self.fail("Cannot find person")

    def test_person(self) -> None:
        p  = self.dt.person(PersonURI(uri="/api/v1/person/person/20209/"))
        if p is not None:
            self.assertEqual(p.id,              20209)
            self.assertEqual(p.resource_uri,    PersonURI(uri="/api/v1/person/person/20209/"))
            self.assertEqual(p.name,            "Colin Perkins")
            self.assertEqual(p.name_from_draft, "Colin Perkins")
            self.assertEqual(p.ascii,           "Colin Perkins")
            self.assertEqual(p.ascii_short,     "")
            self.assertEqual(p.plain,           "")
            self.assertEqual(p.user,            "")
            self.assertEqual(p.time,            datetime.fromisoformat("2012-02-26T00:03:54-08:00"))
            self.assertEqual(p.photo,           "https://www.ietf.org/lib/dt/media/photo/csp-square.jpg")
            self.assertEqual(p.photo_thumb,     "https://www.ietf.org/lib/dt/media/photo/csp-square_GDMMZmn.jpg")
            # self.assertEqual(p.biography,     "Colin Perkins is a ...")
        else:
            self.fail("Cannot find person")


    def test_person_history(self) -> None:
        p  = self.dt.person(PersonURI(uri="/api/v1/person/person/20209/"))
        if p is not None:
            h  = list(self.dt.person_history(p))
            self.assertEqual(len(h), 8)
            
            self.assertEqual(h[0].id,              20209)
            self.assertEqual(h[0].resource_uri,    HistoricalPersonURI(uri="/api/v1/person/historicalperson/27668/"))
            self.assertEqual(h[0].name,            "Colin Perkins")
            self.assertEqual(h[0].name_from_draft, "Colin Perkins")
            self.assertEqual(h[0].ascii,           "Colin Perkins")
            self.assertEqual(h[0].ascii_short,     "")
            self.assertEqual(h[0].plain,           "")
            self.assertEqual(h[0].user,            "")
            self.assertEqual(h[0].time,            datetime.fromisoformat("2012-02-26T00:03:54-08:00"))
            self.assertEqual(h[0].photo,           "photo/csp-square.jpg")
            self.assertEqual(h[1].photo_thumb,     "photo/csp-square_GDMMZmn.jpg")
            self.assertEqual(h[0].biography,       "Colin Perkins is an Associate Professor at the University of Glasgow. His research interests are on transport protocols, and network protocol design, implementation, and specification. He’s been active in the IETF and IRTF since 1996, and has chaired the AVT, MMUSIC, and RMCAT groups in the IETF, and is the current chair of the IRTF. He received his BEng in Electronic Engineering in 1992, and his PhD in 1996, both from the University of York.")
            self.assertEqual(h[0].history_change_reason, None)
            self.assertEqual(h[0].history_user,    "")
            self.assertEqual(h[0].history_id,      27668)
            self.assertEqual(h[0].history_type,    "~")
            self.assertEqual(h[0].history_date,    datetime.fromisoformat("2022-06-27T12:36:15-07:00"))
            
            self.assertEqual(h[1].id,              20209)
            self.assertEqual(h[1].resource_uri,    HistoricalPersonURI(uri="/api/v1/person/historicalperson/24980/"))
            self.assertEqual(h[1].name,            "Colin Perkins")
            self.assertEqual(h[1].name_from_draft, "Colin Perkins")
            self.assertEqual(h[1].ascii,           "Colin Perkins")
            self.assertEqual(h[1].ascii_short,     None)
            self.assertEqual(h[1].plain,           "")
            self.assertEqual(h[1].user,            "")
            self.assertEqual(h[1].time,            datetime.fromisoformat("2012-02-26T00:03:54-08:00"))
            self.assertEqual(h[1].photo,           "photo/csp-square.jpg")
            self.assertEqual(h[1].photo_thumb,     "photo/csp-square_GDMMZmn.jpg")
            self.assertEqual(h[1].history_change_reason, None)
            self.assertEqual(h[1].history_user,    "")
            self.assertEqual(h[1].history_id,      24980)
            self.assertEqual(h[1].history_type,    "~")
            self.assertEqual(h[1].history_date,    datetime.fromisoformat("2022-04-19T14:47:28-07:00"))
            
            self.assertEqual(h[2].id,              20209)
            self.assertEqual(h[2].resource_uri,    HistoricalPersonURI(uri="/api/v1/person/historicalperson/24978/"))
            self.assertEqual(h[2].name,            "Colin Perkins")
            self.assertEqual(h[2].name_from_draft, "Colin Perkins")
            self.assertEqual(h[2].ascii,           "Colin Perkins")
            self.assertEqual(h[2].ascii_short,     "")
            self.assertEqual(h[2].plain,           "")
            self.assertEqual(h[2].user,            "")
            self.assertEqual(h[2].time,            datetime.fromisoformat("2012-02-26T00:03:54-08:00"))
            self.assertEqual(h[2].photo,           "photo/Colin-Perkins-sm.jpg")
            self.assertEqual(h[2].photo_thumb,     "photo/Colin-Perkins-sm_PMIAhXi.jpg")
            self.assertEqual(h[2].history_change_reason, None)
            self.assertEqual(h[2].history_user,    "")
            self.assertEqual(h[2].history_id,      24978)
            self.assertEqual(h[2].history_type,    "~")
            self.assertEqual(h[2].history_date,    datetime.fromisoformat("2022-04-19T14:40:37-07:00"))
            
            self.assertEqual(h[3].id,              20209)
            self.assertEqual(h[3].resource_uri,    HistoricalPersonURI(uri="/api/v1/person/historicalperson/17735/"))
            self.assertEqual(h[3].name,            "Colin Perkins")
            self.assertEqual(h[3].name_from_draft, "Colin Perkins")
            self.assertEqual(h[3].ascii,           "Colin Perkins")
            self.assertEqual(h[3].ascii_short,     "")
            self.assertEqual(h[3].plain,           "")
            self.assertEqual(h[3].user,            "")
            self.assertEqual(h[3].time,            datetime.fromisoformat("2012-02-26T00:03:54-08:00"))
            self.assertEqual(h[3].photo,           "photo/Colin-Perkins-sm.jpg")
            self.assertEqual(h[3].photo_thumb,     "photo/Colin-Perkins-sm_PMIAhXi.jpg")
            self.assertEqual(h[3].history_change_reason, None)
            self.assertEqual(h[3].history_user,    "")
            self.assertEqual(h[3].history_id,      17735)
            self.assertEqual(h[3].history_type,    "~")
            self.assertEqual(h[3].history_date,    datetime.fromisoformat("2021-05-18T16:32:20-07:00"))
            
            self.assertEqual(h[4].id,              20209)
            self.assertEqual(h[4].resource_uri,    HistoricalPersonURI(uri="/api/v1/person/historicalperson/17734/"))
            self.assertEqual(h[4].name,            "Colin Perkins")
            self.assertEqual(h[4].name_from_draft, "Colin Perkins")
            self.assertEqual(h[4].ascii,           "Colin Perkins")
            self.assertEqual(h[4].ascii_short,     "")
            self.assertEqual(h[4].plain,           "")
            self.assertEqual(h[4].user,            "")
            self.assertEqual(h[4].time,            datetime.fromisoformat("2012-02-26T00:03:54-08:00"))
            self.assertEqual(h[4].photo,           "photo/Colin-Perkins-sm.jpg")
            self.assertEqual(h[4].photo_thumb,     "photo/Colin-Perkins-sm_PMIAhXi.jpg")
            self.assertEqual(h[4].history_change_reason, None)
            self.assertEqual(h[4].history_user,    "")
            self.assertEqual(h[4].history_id,      17734)
            self.assertEqual(h[4].history_type,    "~")
            self.assertEqual(h[4].history_date,    datetime.fromisoformat("2021-05-18T16:30:53-07:00"))
            
            self.assertEqual(h[5].id,              20209)
            self.assertEqual(h[5].resource_uri,    HistoricalPersonURI(uri="/api/v1/person/historicalperson/11731/"))
            self.assertEqual(h[5].name,            "Colin Perkins")
            self.assertEqual(h[5].name_from_draft, "Colin Perkins")
            self.assertEqual(h[5].ascii,           "Colin Perkins")
            self.assertEqual(h[5].ascii_short,     "")
            self.assertEqual(h[5].plain,           "")
            self.assertEqual(h[5].user,            "")
            self.assertEqual(h[5].time,            datetime.fromisoformat("2012-02-26T00:03:54-08:00"))
            self.assertEqual(h[5].photo,           "photo/Colin-Perkins-sm.jpg")
            self.assertEqual(h[5].photo_thumb,     "photo/Colin-Perkins-sm_PMIAhXi.jpg")
            self.assertEqual(h[5].history_change_reason, None)
            self.assertEqual(h[5].history_user,    "")
            self.assertEqual(h[5].history_id,      11731)
            self.assertEqual(h[5].history_type,    "~")
            self.assertEqual(h[5].history_date,    datetime.fromisoformat("2019-09-29T14:39:48-07:00"))
            
            self.assertEqual(h[6].id,              20209)
            self.assertEqual(h[6].resource_uri,    HistoricalPersonURI(uri="/api/v1/person/historicalperson/10878/"))
            self.assertEqual(h[6].name,            "Colin Perkins")
            self.assertEqual(h[6].name_from_draft, "Colin Perkins")
            self.assertEqual(h[6].ascii,           "Colin Perkins")
            self.assertEqual(h[6].ascii_short,     None)
            self.assertEqual(h[6].plain,           "")
            self.assertEqual(h[6].user,            "")
            self.assertEqual(h[6].time,            datetime.fromisoformat("2012-02-26T00:03:54-08:00"))
            self.assertEqual(h[6].photo,           "photo/Colin-Perkins-sm.jpg")
            self.assertEqual(h[6].photo_thumb,     "photo/Colin-Perkins-sm_PMIAhXi.jpg")
            self.assertEqual(h[6].history_change_reason, None)
            self.assertEqual(h[6].history_user,    "")
            self.assertEqual(h[6].history_id,      10878)
            self.assertEqual(h[6].history_type,    "~")
            self.assertEqual(h[6].history_date,    datetime.fromisoformat("2019-03-29T02:44:28-07:00"))
            
            self.assertEqual(h[7].id,              20209)
            self.assertEqual(h[7].resource_uri,    HistoricalPersonURI(uri="/api/v1/person/historicalperson/127/"))
            self.assertEqual(h[7].name,            "Colin Perkins")
            self.assertEqual(h[7].name_from_draft, "Colin Perkins")
            self.assertEqual(h[7].ascii,           "Colin Perkins")
            self.assertEqual(h[7].ascii_short,     "")
            self.assertEqual(h[7].plain,           "")
            self.assertEqual(h[7].user,            "")
            self.assertEqual(h[7].time,            datetime.fromisoformat("2012-02-26T00:03:54-08:00"))
            self.assertEqual(h[7].photo,           "")
            self.assertEqual(h[7].photo_thumb,     "")
            self.assertEqual(h[7].biography,       "")
            self.assertEqual(h[7].history_change_reason, None)
            self.assertEqual(h[7].history_user,    "")
            self.assertEqual(h[7].history_id,      127)
            self.assertEqual(h[7].history_type,    "~")
            self.assertEqual(h[7].history_date,    datetime.fromisoformat("2018-06-19T15:39:39-07:00"))

        else:
            self.fail("Cannot find person")


    def test_person_aliases(self) -> None:
        p  = self.dt.person(PersonURI(uri="/api/v1/person/person/20209/"))
        if p is not None:
            aliases  = list(self.dt.person_aliases(person = p))
            self.assertEqual(len(aliases), 2)
            self.assertEqual(aliases[0].id,           62)
            self.assertEqual(aliases[0].resource_uri, PersonAliasURI(uri="/api/v1/person/alias/62/"))
            self.assertEqual(aliases[0].person,       PersonURI(uri="/api/v1/person/person/20209/"))
            self.assertEqual(aliases[0].name,         "Dr. Colin Perkins")
            self.assertEqual(aliases[1].id,           22620)
            self.assertEqual(aliases[1].resource_uri, PersonAliasURI(uri="/api/v1/person/alias/22620/"))
            self.assertEqual(aliases[1].person,       PersonURI(uri="/api/v1/person/person/20209/"))
            self.assertEqual(aliases[1].name,         "Colin Perkins")
        else:
            self.fail("Cannot find person")


    #def test_person_events(self) -> None:
    #    p = self.dt.person(PersonURI(uri="/api/v1/person/person/3/"))
    #    if p is not None:
    #        events = list(self.dt.person_events(p))
    #        self.assertEqual(len(events), 1)
    #        self.assertEqual(events[0].desc,         "Sent GDPR notice email to [u'vint@google.com', u'vcerf@mci.net', u'vcerf@nri.reston.va.us', u'vinton.g.cerf@wcom.com'] with confirmation deadline 2018-10-22")
    #        self.assertEqual(events[0].id,           478)
    #        self.assertEqual(events[0].person,       PersonURI(uri="/api/v1/person/person/3/"))
    #        self.assertEqual(events[0].resource_uri, PersonEventURI(uri="/api/v1/person/personevent/478/"))
    #        self.assertEqual(events[0].time,         datetime.fromisoformat("2018-09-24T09:28:32.502465"))
    #        self.assertEqual(events[0].type,         "gdpr_notice_email")
    #    else:
    #        self.fail("Cannot find person")


    def test_people(self) -> None:
        p  = list(self.dt.people(name_contains="Colin Perkins"))
        self.assertEqual(len(p), 1)
        self.assertEqual(p[ 0].resource_uri, PersonURI(uri="/api/v1/person/person/20209/"))


    def test_person_ext_resource(self) -> None:
        r = self.dt.person_ext_resource(PersonExtResourceURI(uri="/api/v1/person/personextresource/177/"))
        if r is not None:
            self.assertEqual(r.resource_uri, PersonExtResourceURI(uri="/api/v1/person/personextresource/177/"))
            self.assertEqual(r.id,           177)
            self.assertEqual(r.display_name, "")
            self.assertEqual(r.person,       PersonURI(uri="/api/v1/person/person/20209/"))
            self.assertEqual(r.name,         ExtResourceNameURI(uri="/api/v1/name/extresourcename/github_username/"))
            self.assertEqual(r.value,        "csperkins")
        else:
            self.fail("Cannot find PersonExternalResource")


    def test_person_ext_resources(self) -> None:
        p = self.dt.person_from_email("csp@csperkins.org")
        r = list(self.dt.person_ext_resources(p))
        self.assertEqual(len(r), 3)
        self.assertEqual(r[0].value, "csperkins")
        self.assertEqual(r[1].value, "https://csperkins.org/")
        self.assertEqual(r[2].value, "https://www.gla.ac.uk/schools/computing/staff/colinperkins/")


    def test_ext_resource_name(self) -> None:
        r = self.dt.ext_resource_name(ExtResourceNameURI(uri="/api/v1/name/extresourcename/github_username/"))
        if r is not None:
            self.assertEqual(r.resource_uri, ExtResourceNameURI(uri="/api/v1/name/extresourcename/github_username/"))
            self.assertEqual(r.desc,  "GitHub Username")
            self.assertEqual(r.name,  "GitHub Username")
            self.assertEqual(r.order, 0)
            self.assertEqual(r.slug,  "github_username")
            self.assertEqual(r.type,  ExtResourceTypeNameURI(uri="/api/v1/name/extresourcetypename/string/"))
            self.assertEqual(r.used,  True)
        else:
            self.fail("Cannot find ExtResourceName")

    # -----------------------------------------------------------------------------------------------------------------------------
    # Tests relating to documents:

    # There is one test_document_*() method for each document type

    def test_document_agenda(self) -> None:
        d  = self.dt.document(DocumentURI(uri="/api/v1/doc/document/agenda-90-precis/"))
        if d is not None:
            self.assertEqual(d.expires,            None)
            self.assertEqual(d.intended_std_level, None)
            self.assertEqual(d.uploaded_filename,  "agenda-90-precis.txt")
            self.assertEqual(d.states,             [DocumentStateURI(uri="/api/v1/doc/state/81/")])
            self.assertEqual(d.abstract,           "")
            self.assertEqual(d.notify,             "")
            self.assertEqual(d.type,               DocumentTypeURI(uri="/api/v1/name/doctypename/agenda/"))
            self.assertEqual(d.rev,                "2")
            self.assertEqual(d.id,                 218)
            self.assertEqual(d.std_level,          None)
            self.assertEqual(d.ad,                 None)
            self.assertEqual(d.time,               datetime.fromisoformat("2014-07-21T18:14:17+00:00"))
            self.assertEqual(d.title,              "Agenda for PRECIS at IETF-90")
            self.assertEqual(d.shepherd,           None)
            self.assertEqual(d.pages,              None)
            self.assertEqual(d.tags,               [])
            self.assertEqual(d.resource_uri,       DocumentURI(uri="/api/v1/doc/document/agenda-90-precis/"))
            self.assertEqual(d.rfc,                None)
            self.assertEqual(d.words,              None)
            self.assertEqual(d.submissions,        [])
            self.assertEqual(d.name,               "agenda-90-precis")
            self.assertEqual(d.stream,             None)
            self.assertEqual(d.group,              GroupURI(uri="/api/v1/group/group/1798/"))
            self.assertEqual(d.note,               "")
            self.assertEqual(d.external_url,       "")

            url = d.url()
            self.assertEqual(url, "https://www.ietf.org/proceedings/90/agenda/agenda-90-precis.txt")
            self.assertEqual(self.dt.session.get(url).status_code, 200)
        else:
            self.fail("Cannot find document")


    def test_document_bluesheets(self) -> None:
        d  = self.dt.document(DocumentURI(uri="/api/v1/doc/document/bluesheets-95-xrblock-01/"))
        if d is not None:
            self.assertEqual(d.id,                 68163)
            self.assertEqual(d.name,               "bluesheets-95-xrblock-01")
            self.assertEqual(d.notify,             "")
            self.assertEqual(d.rev,                "00")
            self.assertEqual(d.external_url,       "")
            self.assertEqual(d.expires,            None)
            self.assertEqual(d.type,               DocumentTypeURI(uri="/api/v1/name/doctypename/bluesheets/"))
            self.assertEqual(d.group,              GroupURI(uri="/api/v1/group/group/1815/"))
            self.assertEqual(d.resource_uri,       DocumentURI(uri="/api/v1/doc/document/bluesheets-95-xrblock-01/"))
            self.assertEqual(d.title,              "Bluesheets IETF95 : xrblock : Wed 16:20")
            self.assertEqual(d.abstract,           "")
            self.assertEqual(d.uploaded_filename,  "bluesheets-95-xrblock-01.pdf")
            self.assertEqual(d.rfc,                None)
            self.assertEqual(d.shepherd,           None)
            self.assertEqual(d.submissions,        [])
            self.assertEqual(d.intended_std_level, None)
            self.assertEqual(d.ad,                 None)
            self.assertEqual(d.note,               "")
            self.assertEqual(d.words,              None)
            self.assertEqual(d.tags,               [])
            self.assertEqual(d.time,               datetime.fromisoformat("2016-08-22T05:39:08-07:00"))
            self.assertEqual(d.pages,              None)
            self.assertEqual(d.stream,             None)
            self.assertEqual(d.std_level,          None)
            self.assertEqual(d.states,             [DocumentStateURI(uri="/api/v1/doc/state/139/")])

            url = d.url()
            self.assertEqual(url, "https://www.ietf.org/proceedings/95/bluesheets/bluesheets-95-xrblock-01.pdf")
            self.assertEqual(self.dt.session.get(url).status_code, 200)
        else:
            self.fail("Cannot find document")


    def test_document_charter(self) -> None:
        d  = self.dt.document(DocumentURI(uri="/api/v1/doc/document/charter-ietf-vgmib/"))
        if d is not None:
            self.assertEqual(d.id,                 1)
            self.assertEqual(d.name,               "charter-ietf-vgmib")
            self.assertEqual(d.notify,             "")
            self.assertEqual(d.rev,                "01")
            self.assertEqual(d.external_url,       "")
            self.assertEqual(d.expires,            None)
            self.assertEqual(d.type,               DocumentTypeURI(uri="/api/v1/name/doctypename/charter/"))
            self.assertEqual(d.group,              GroupURI(uri="/api/v1/group/group/925/"))
            self.assertEqual(d.resource_uri,       DocumentURI(uri="/api/v1/doc/document/charter-ietf-vgmib/"))
            self.assertEqual(d.title,              "100VG-AnyLAN MIB")
            self.assertEqual(d.abstract,           "100VG-AnyLAN MIB")
            self.assertEqual(d.uploaded_filename,  "")
            self.assertEqual(d.rfc,                None)
            self.assertEqual(d.shepherd,           None)
            self.assertEqual(d.submissions,        [])
            self.assertEqual(d.intended_std_level, None)
            self.assertEqual(d.ad,                 None)
            self.assertEqual(d.note,               "")
            self.assertEqual(d.words,              None)
            self.assertEqual(d.tags,               [])
            self.assertEqual(d.time,               datetime.fromisoformat("1998-01-26T12:00:00-08:00"))
            self.assertEqual(d.pages,              None)
            self.assertEqual(d.stream,             None)
            self.assertEqual(d.std_level,          None)
            self.assertEqual(d.states,             [DocumentStateURI(uri="/api/v1/doc/state/88/")])

            url = d.url()
            self.assertEqual(url, "https://www.ietf.org/charter/charter-ietf-vgmib-01.txt")
            self.assertEqual(self.dt.session.get(url).status_code, 200)
        else:
            self.fail("Cannot find document")


    def test_document_chatlog(self) -> None:
        d = self.dt.document(DocumentURI(uri="/api/v1/doc/document/chatlog-114-ohai-202207261330/"))
        if d is not None:
            self.assertEqual(d.id,                 110925)
            self.assertEqual(d.name,               "chatlog-114-ohai-202207261330")
            self.assertEqual(d.notify,             "")
            self.assertEqual(d.rev,                "00")
            self.assertEqual(d.external_url,       "")
            self.assertEqual(d.expires,            None)
            self.assertEqual(d.type,               DocumentTypeURI(uri="/api/v1/name/doctypename/chatlog/"))
            self.assertEqual(d.group,              GroupURI(uri="/api/v1/group/group/2312/"))
            self.assertEqual(d.resource_uri,       DocumentURI(uri="/api/v1/doc/document/chatlog-114-ohai-202207261330/"))
            self.assertEqual(d.title,              "Chat Log IETF114: ohai: Tue 13:30")
            self.assertEqual(d.abstract,           "")
            self.assertEqual(d.uploaded_filename,  "chatlog-114-ohai-202207261330-00.json")
            self.assertEqual(d.rfc,                None)
            self.assertEqual(d.shepherd,           None)
            self.assertEqual(d.submissions,        [])
            self.assertEqual(d.intended_std_level, None)
            self.assertEqual(d.ad,                 None)
            self.assertEqual(d.note,               "")
            self.assertEqual(d.words,              None)
            self.assertEqual(d.tags,               [])
            self.assertEqual(d.time,               datetime.fromisoformat("2022-10-18T15:21:12+0000"))
            self.assertEqual(d.pages,              None)
            self.assertEqual(d.stream,             None)
            self.assertEqual(d.std_level,          None)
            self.assertEqual(d.states,             [DocumentStateURI(uri="/api/v1/doc/state/165/")])
        
            url = d.url()
            self.assertEqual(url, "https://datatracker.ietf.org/meeting/114/materials/chatlog-114-ohai-202207261330-00.json")
            self.assertEqual(self.dt.session.get(url).status_code, 200)
        else:
            self.fail("Cannot find document")


    def test_document_conflrev(self) -> None:
        d  = self.dt.document(DocumentURI(uri="/api/v1/doc/document/conflict-review-kiyomoto-kcipher2/"))
        if d is not None:
            self.assertEqual(d.id,                 17898)
            self.assertEqual(d.name,               "conflict-review-kiyomoto-kcipher2")
            self.assertEqual(d.notify,             "\"Nevil Brownlee\" <rfc-ise@rfc-editor.org>, draft-kiyomoto-kcipher2@tools.ietf.org")
            self.assertEqual(d.rev,                "00")
            self.assertEqual(d.external_url,       "")
            self.assertEqual(d.expires,            None)
            self.assertEqual(d.type,               DocumentTypeURI(uri="/api/v1/name/doctypename/conflrev/"))
            self.assertEqual(d.group,              GroupURI(uri="/api/v1/group/group/2/"))
            self.assertEqual(d.resource_uri,       DocumentURI(uri="/api/v1/doc/document/conflict-review-kiyomoto-kcipher2/"))
            self.assertEqual(d.title,              "IETF conflict review for draft-kiyomoto-kcipher2")
            self.assertEqual(d.abstract,           "")
            self.assertEqual(d.uploaded_filename,  "")
            self.assertEqual(d.rfc,                None)
            self.assertEqual(d.shepherd,           None)
            self.assertEqual(d.submissions,        [])
            self.assertEqual(d.intended_std_level, None)
            self.assertEqual(d.ad,                 PersonURI(uri="/api/v1/person/person/19177/"))
            self.assertEqual(d.note,               "")
            self.assertEqual(d.words,              None)
            self.assertEqual(d.tags,               [])
            self.assertEqual(d.time,               datetime.fromisoformat("2013-07-15T14:47:31-07:00"))
            self.assertEqual(d.pages,              None)
            self.assertEqual(d.stream,             StreamURI(uri="/api/v1/name/streamname/ietf/"))
            self.assertEqual(d.std_level,          None)
            self.assertEqual(d.states,             [DocumentStateURI(uri="/api/v1/doc/state/97/")])

            url = d.url()
            self.assertEqual(url, "https://www.ietf.org/cr/conflict-review-kiyomoto-kcipher2-00.txt")
            self.assertEqual(self.dt.session.get(url).status_code, 200)
        else:
            self.fail("Cannot find document")


    def test_document_draft(self) -> None:
        d  = self.dt.document(DocumentURI(uri="/api/v1/doc/document/draft-ietf-avt-rtp-new/"))
        if d is not None:
            self.assertEqual(d.id,                 19971)
            self.assertEqual(d.name,               "draft-ietf-avt-rtp-new")
            self.assertEqual(d.notify,             "magnus.westerlund@ericsson.com, csp@csperkins.org")
            self.assertEqual(d.rev,                "12")
            self.assertEqual(d.external_url,       "")
            self.assertEqual(d.expires,            "2003-09-08T07:00:12Z")
            self.assertEqual(d.type,               DocumentTypeURI(uri="/api/v1/name/doctypename/draft/"))
            self.assertEqual(d.group,              GroupURI(uri="/api/v1/group/group/941/"))
            self.assertEqual(d.resource_uri,       DocumentURI(uri="/api/v1/doc/document/draft-ietf-avt-rtp-new/"))
            self.assertEqual(d.title,              "RTP: A Transport Protocol for Real-Time Applications")
            # self.assertEqual(d.abstract,         "This memorandum describes RTP, the real-time transport protocol...")
            self.assertEqual(d.uploaded_filename,  "")
            self.assertEqual(d.rfc,                None)
            self.assertEqual(d.shepherd,           None)
            self.assertEqual(d.submissions,        [])
            self.assertEqual(d.intended_std_level, "/api/v1/name/intendedstdlevelname/std/")
            self.assertEqual(d.ad,                 PersonURI(uri="/api/v1/person/person/2515/"))
            self.assertEqual(d.note,               "")
            self.assertEqual(d.words,              34861)
            self.assertEqual(d.tags,               [DocumentTagURI(uri="/api/v1/name/doctagname/app-min/")])
            self.assertEqual(d.time,               datetime.fromisoformat("2015-10-14T20:49:52+00:00"))
            self.assertEqual(d.pages,              104)
            self.assertEqual(d.stream,             StreamURI(uri="/api/v1/name/streamname/ietf/"))
            self.assertEqual(d.std_level,          "/api/v1/name/stdlevelname/std/")
            self.assertEqual(d.states,             [DocumentStateURI(uri="/api/v1/doc/state/3/"), DocumentStateURI(uri="/api/v1/doc/state/7/")])

            url = d.url()
            self.assertEqual(url, "https://www.ietf.org/archive/id/draft-ietf-avt-rtp-new-12.txt")
            self.assertEqual(self.dt.session.get(url).status_code, 200)
        else:
            self.fail("Cannot find document")


    def test_document_liaison(self) -> None:
        d  = self.dt.document(DocumentURI(uri="/api/v1/doc/document/liaison-2012-05-31-3gpp-mmusic-on-rtcp-bandwidth-negotiation-attachment-1/"))
        if d is not None:
            self.assertEqual(d.id,                 46457)
            self.assertEqual(d.name,               "liaison-2012-05-31-3gpp-mmusic-on-rtcp-bandwidth-negotiation-attachment-1")
            self.assertEqual(d.notify,             "")
            self.assertEqual(d.rev,                "")
            self.assertEqual(d.external_url,       "")
            self.assertEqual(d.expires,            None)
            self.assertEqual(d.type,               DocumentTypeURI(uri="/api/v1/name/doctypename/liaison/"))
            self.assertEqual(d.group,              None)
            self.assertEqual(d.resource_uri,       DocumentURI(uri="/api/v1/doc/document/liaison-2012-05-31-3gpp-mmusic-on-rtcp-bandwidth-negotiation-attachment-1/"))
            self.assertEqual(d.title,              "S4-120810 DRAFT LS to IETF MMUSIC WG on RTCP Bandwidth Negotiation")
            self.assertEqual(d.abstract,           "")
            self.assertEqual(d.uploaded_filename,  "liaison-2012-05-31-3gpp-mmusic-on-rtcp-bandwidth-negotiation-attachment-1.doc")
            self.assertEqual(d.rfc,                None)
            self.assertEqual(d.shepherd,           None)
            self.assertEqual(d.submissions,        [])
            self.assertEqual(d.intended_std_level, None)
            self.assertEqual(d.ad,                 None)
            self.assertEqual(d.note,               "")
            self.assertEqual(d.words,              None)
            self.assertEqual(d.tags,               [])
            self.assertEqual(d.time,               datetime.fromisoformat("2012-06-04T15:20:38+00:00"))
            self.assertEqual(d.pages,              None)
            self.assertEqual(d.stream,             None)
            self.assertEqual(d.std_level,          None)
            self.assertEqual(d.states,             [])

            url = d.url()
            self.assertEqual(url, "https://www.ietf.org/lib/dt/documents/LIAISON/liaison-2012-05-31-3gpp-mmusic-on-rtcp-bandwidth-negotiation-attachment-1.doc")
            self.assertEqual(self.dt.session.get(url).status_code, 200)
        else:
            self.fail("Cannot find document")


    def test_document_liai_att(self) -> None:
        d  = self.dt.document(DocumentURI(uri="/api/v1/doc/document/liaison-2004-08-23-itu-t-ietf-liaison-statement-to-ietf-and-itu-t-study-groups-countering-spam-pdf-version-attachment-1/"))
        if d is not None:
            self.assertEqual(d.id,                 43519)
            self.assertEqual(d.name,               "liaison-2004-08-23-itu-t-ietf-liaison-statement-to-ietf-and-itu-t-study-groups-countering-spam-pdf-version-attachment-1")
            self.assertEqual(d.notify,             "")
            self.assertEqual(d.rev,                "")
            self.assertEqual(d.external_url,       "")
            self.assertEqual(d.expires,            None)
            self.assertEqual(d.type,               DocumentTypeURI(uri="/api/v1/name/doctypename/liai-att/"))
            self.assertEqual(d.group,              None)
            self.assertEqual(d.resource_uri,       DocumentURI(uri="/api/v1/doc/document/liaison-2004-08-23-itu-t-ietf-liaison-statement-to-ietf-and-itu-t-study-groups-countering-spam-pdf-version-attachment-1/"))
            self.assertEqual(d.title,              "Liaison Statement to IETF and ITU-T Study Groups: Countering SPAM (PDF version)")
            self.assertEqual(d.abstract,           "")
            self.assertEqual(d.uploaded_filename,  "file39.pdf")
            self.assertEqual(d.rfc,                None)
            self.assertEqual(d.shepherd,           None)
            self.assertEqual(d.submissions,        [])
            self.assertEqual(d.intended_std_level, None)
            self.assertEqual(d.ad,                 None)
            self.assertEqual(d.note,               "")
            self.assertEqual(d.words,              None)
            self.assertEqual(d.tags,               [])
            self.assertEqual(d.time,               datetime.fromisoformat("2004-08-23T07:00:00+00:00"))
            self.assertEqual(d.pages,              None)
            self.assertEqual(d.stream,             None)
            self.assertEqual(d.std_level,          None)
            self.assertEqual(d.states,             [])

            url = d.url()
            self.assertEqual(url, "https://www.ietf.org/lib/dt/documents/LIAISON/file39.pdf")
            self.assertEqual(self.dt.session.get(url).status_code, 200)
        else:
            self.fail("Cannot find document")


    def test_document_minutes(self) -> None:
        d  = self.dt.document(DocumentURI(uri="/api/v1/doc/document/minutes-89-cfrg/"))
        if d is not None:
            self.assertEqual(d.id,                 272)
            self.assertEqual(d.name,               "minutes-89-cfrg")
            self.assertEqual(d.notify,             "")
            self.assertEqual(d.rev,                "1")
            self.assertEqual(d.external_url,       "")
            self.assertEqual(d.expires,            None)
            self.assertEqual(d.type,               DocumentTypeURI(uri="/api/v1/name/doctypename/minutes/"))
            self.assertEqual(d.group,              GroupURI(uri="/api/v1/group/group/31/"))
            self.assertEqual(d.resource_uri,       DocumentURI(uri="/api/v1/doc/document/minutes-89-cfrg/"))
            self.assertEqual(d.title,              "Minutes for CFRG at IETF-89")
            self.assertEqual(d.abstract,           "")
            self.assertEqual(d.uploaded_filename,  "minutes-89-cfrg.txt")
            self.assertEqual(d.rfc,                None)
            self.assertEqual(d.shepherd,           None)
            self.assertEqual(d.submissions,        [])
            self.assertEqual(d.intended_std_level, None)
            self.assertEqual(d.ad,                 None)
            self.assertEqual(d.note,               "")
            self.assertEqual(d.words,              None)
            self.assertEqual(d.tags,               [])
            self.assertEqual(d.time,               datetime.fromisoformat("2014-04-09T08:09:14-07:00"))
            self.assertEqual(d.pages,              None)
            self.assertEqual(d.stream,             None)
            self.assertEqual(d.std_level,          None)
            self.assertEqual(d.states,             [DocumentStateURI(uri="/api/v1/doc/state/79/")])

            url = d.url()
            self.assertEqual(url, "https://www.ietf.org/proceedings/89/minutes/minutes-89-cfrg.txt")
            self.assertEqual(self.dt.session.get(url).status_code, 200)
        else:
            self.fail("Cannot find document")


    def test_document_recording(self) -> None:
        d  = self.dt.document(DocumentURI(uri="/api/v1/doc/document/recording-94-taps-1/"))
        if d is not None:
            self.assertEqual(d.id,                 49624)
            self.assertEqual(d.name,               "recording-94-taps-1")
            self.assertEqual(d.notify,             "")
            self.assertEqual(d.rev,                "00")
            self.assertEqual(d.external_url,       "https://www.ietf.org/audio/ietf94/ietf94-room304-20151103-1520.mp3")
            self.assertEqual(d.expires,            None)
            self.assertEqual(d.type,               DocumentTypeURI(uri="/api/v1/name/doctypename/recording/"))
            self.assertEqual(d.group,              GroupURI(uri="/api/v1/group/group/1924/"))
            self.assertEqual(d.resource_uri,       DocumentURI(uri="/api/v1/doc/document/recording-94-taps-1/"))
            self.assertEqual(d.title,              "Audio recording for 2015-11-03 15:20")
            self.assertEqual(d.abstract,           "")
            self.assertEqual(d.uploaded_filename,  "")
            self.assertEqual(d.rfc,                None)
            self.assertEqual(d.shepherd,           None)
            self.assertEqual(d.submissions,        [])
            self.assertEqual(d.intended_std_level, None)
            self.assertEqual(d.ad,                 None)
            self.assertEqual(d.note,               "")
            self.assertEqual(d.words,              None)
            self.assertEqual(d.tags,               [])
            self.assertEqual(d.time,               datetime.fromisoformat("2015-11-24T08:23:42-08:00"))
            self.assertEqual(d.pages,              None)
            self.assertEqual(d.stream,             None)
            self.assertEqual(d.std_level,          None)
            self.assertEqual(d.states,             [DocumentStateURI(uri="/api/v1/doc/state/135/")])

            url = d.url()
            self.assertEqual(url, "https://www.ietf.org/audio/ietf94/ietf94-room304-20151103-1520.mp3")
            # Downloading the MP3 is expensive, so check a HEAD request instead:
            # self.assertEqual(self.dt.session.head(url).status_code, 200)
        else:
            self.fail("Cannot find document")


    def test_document_review(self) -> None:
        d  = self.dt.document(DocumentURI(uri="/api/v1/doc/document/review-bchv-rfc6890bis-04-genart-lc-kyzivat-2017-02-28/"))
        if d is not None:
            self.assertEqual(d.id,                 69082)
            self.assertEqual(d.name,               "review-bchv-rfc6890bis-04-genart-lc-kyzivat-2017-02-28")
            self.assertEqual(d.notify,             "")
            self.assertEqual(d.rev,                "00")
            self.assertEqual(d.external_url,       "")
            self.assertEqual(d.expires,            None)
            self.assertEqual(d.type,               DocumentTypeURI(uri="/api/v1/name/doctypename/review/"))
            self.assertEqual(d.group,              GroupURI(uri="/api/v1/group/group/1972/"))
            self.assertEqual(d.resource_uri,       DocumentURI(uri="/api/v1/doc/document/review-bchv-rfc6890bis-04-genart-lc-kyzivat-2017-02-28/"))
            self.assertEqual(d.title,              "Last Call Review of draft-bchv-rfc6890bis-04")
            self.assertEqual(d.abstract,           "")
            self.assertEqual(d.uploaded_filename,  "")
            self.assertEqual(d.rfc,                None)
            self.assertEqual(d.shepherd,           None)
            self.assertEqual(d.submissions,        [])
            self.assertEqual(d.intended_std_level, None)
            self.assertEqual(d.ad,                 None)
            self.assertEqual(d.note,               "")
            self.assertEqual(d.words,              None)
            self.assertEqual(d.tags,               [])
            self.assertEqual(d.time,               datetime.fromisoformat("2017-02-28T12:52:33-08:00"))
            self.assertEqual(d.pages,              None)
            self.assertEqual(d.stream,             None)
            self.assertEqual(d.std_level,          None)
            self.assertEqual(d.states,             [DocumentStateURI(uri="/api/v1/doc/state/143/")])

            url = d.url()
            self.assertEqual(url, "https://datatracker.ietf.org/doc/review-bchv-rfc6890bis-04-genart-lc-kyzivat-2017-02-28")
            self.assertEqual(self.dt.session.get(url).status_code, 200)
        else:
            self.fail("Cannot find document")


    def test_document_shepwrit(self) -> None:
        for d in self.dt.documents(doctype=self.dt.document_type(DocumentTypeURI(uri="/api/v1/name/doctypename/shepwrit/"))):
            self.fail("shepwrit is not used, so this should return no documents")


    def test_document_slides(self) -> None:
        d  = self.dt.document(DocumentURI(uri="/api/v1/doc/document/slides-65-l2vpn-4/"))
        if d is not None:
            self.assertEqual(d.id,                 736)
            self.assertEqual(d.name,               "slides-65-l2vpn-4")
            self.assertEqual(d.notify,             "")
            self.assertEqual(d.rev,                "00")
            self.assertEqual(d.external_url,       "")
            self.assertEqual(d.expires,            None)
            self.assertEqual(d.type,               DocumentTypeURI(uri="/api/v1/name/doctypename/slides/"))
            self.assertEqual(d.group,              GroupURI(uri="/api/v1/group/group/1593/"))
            self.assertEqual(d.resource_uri,       DocumentURI(uri="/api/v1/doc/document/slides-65-l2vpn-4/"))
            self.assertEqual(d.title,              "Congruency for VPLS Mcast & Unicast Paths")
            self.assertEqual(d.abstract,           "")
            self.assertEqual(d.uploaded_filename,  "l2vpn-4.pdf")
            self.assertEqual(d.rfc,                None)
            self.assertEqual(d.shepherd,           None)
            self.assertEqual(d.submissions,        [])
            self.assertEqual(d.intended_std_level, None)
            self.assertEqual(d.ad,                 None)
            self.assertEqual(d.note,               "")
            self.assertEqual(d.words,              None)
            self.assertEqual(d.tags,               [])
            self.assertEqual(d.time,               datetime.fromisoformat("2006-04-07T17:30:22-07:00"))
            self.assertEqual(d.pages,              None)
            self.assertEqual(d.stream,             None)
            self.assertEqual(d.std_level,          None)
            self.assertEqual(d.states,             [DocumentStateURI(uri="/api/v1/doc/state/141/"), DocumentStateURI(uri="/api/v1/doc/state/138/")])

            url = d.url()
            self.assertEqual(url, "https://www.ietf.org/proceedings/65/slides/l2vpn-4.pdf")
            self.assertEqual(self.dt.session.get(url).status_code, 200)
        else:
            self.fail("Cannot find document")


    def test_document_statchg(self) -> None:
        d  = self.dt.document(DocumentURI(uri="/api/v1/doc/document/status-change-rfc3044-rfc3187-orig-urn-regs-to-historic/"))
        if d is not None:
            self.assertEqual(d.id,                 78306)
            self.assertEqual(d.name,               "status-change-rfc3044-rfc3187-orig-urn-regs-to-historic")
            self.assertEqual(d.notify,             "")
            self.assertEqual(d.rev,                "00")
            self.assertEqual(d.external_url,       "")
            self.assertEqual(d.expires,            None)
            self.assertEqual(d.type,               DocumentTypeURI(uri="/api/v1/name/doctypename/statchg/"))
            self.assertEqual(d.group,              GroupURI(uri="/api/v1/group/group/2/"))
            self.assertEqual(d.resource_uri,       DocumentURI(uri="/api/v1/doc/document/status-change-rfc3044-rfc3187-orig-urn-regs-to-historic/"))
            self.assertEqual(d.title,              "Change status of RFC 3044 and RFC 3187 (original ISSN and ISBN URN Namespace registrationS) to Historic")
            self.assertEqual(d.abstract,           "")
            self.assertEqual(d.uploaded_filename,  "")
            self.assertEqual(d.rfc,                None)
            self.assertEqual(d.shepherd,           None)
            self.assertEqual(d.submissions,        [])
            self.assertEqual(d.intended_std_level, None)
            self.assertEqual(d.ad,                 PersonURI(uri="/api/v1/person/person/102154/"))
            self.assertEqual(d.note,               "")
            self.assertEqual(d.words,              None)
            self.assertEqual(d.tags,               [])
            self.assertEqual(d.time,               datetime.fromisoformat("2017-08-21T09:32:46-07:00"))
            self.assertEqual(d.pages,              None)
            self.assertEqual(d.stream,             StreamURI(uri="/api/v1/name/streamname/ietf/"))
            self.assertEqual(d.std_level,          None)
            self.assertEqual(d.states,             [DocumentStateURI(uri="/api/v1/doc/state/127/")])

            url = d.url()
            self.assertEqual(url, "https://www.ietf.org/ietf-ftp/status-changes/status-change-rfc3044-rfc3187-orig-urn-regs-to-historic-00.txt")
            self.assertEqual(self.dt.session.get(url).status_code, 200)
        else:
            self.fail("Cannot find document")


    def test_documents(self):
        doctype = self.dt.document_type(DocumentTypeURI(uri="/api/v1/name/doctypename/draft/"))
        group   = self.dt.group_from_acronym("xrblock")
        documents = list(self.dt.documents(doctype = doctype, group = group))
        self.assertEqual(len(documents), 21)
        self.assertEqual(documents[ 0].name, "draft-ietf-xrblock-rtcp-xr-discard-rle-metrics")
        self.assertEqual(documents[ 1].name, "draft-ietf-xrblock-rtcp-xr-pdv")
        self.assertEqual(documents[ 2].name, "draft-ietf-xrblock-rtcp-xr-meas-identity")
        self.assertEqual(documents[ 3].name, "draft-ietf-xrblock-rtcp-xr-delay")
        self.assertEqual(documents[ 4].name, "draft-ietf-xrblock-rtcp-xr-burst-gap-loss")
        self.assertEqual(documents[ 5].name, "draft-ietf-xrblock-rtcp-xr-burst-gap-discard")
        self.assertEqual(documents[ 6].name, "draft-ietf-xrblock-rtcp-xr-discard")
        self.assertEqual(documents[ 7].name, "draft-ietf-xrblock-rtcp-xr-qoe")
        self.assertEqual(documents[ 8].name, "draft-ietf-xrblock-rtcp-xr-jb")
        self.assertEqual(documents[ 9].name, "draft-ietf-xrblock-rtcp-xr-loss-conceal")
        self.assertEqual(documents[10].name, "draft-ietf-xrblock-rtcp-xr-concsec")
        self.assertEqual(documents[11].name, "draft-ietf-xrblock-rtcp-xr-synchronization")
        self.assertEqual(documents[12].name, "draft-ietf-xrblock-rtcp-xr-summary-stat")
        self.assertEqual(documents[13].name, "draft-ietf-xrblock-rtcp-xr-decodability")
        self.assertEqual(documents[14].name, "draft-ietf-xrblock-rtcp-xr-bytes-discarded-metric")
        self.assertEqual(documents[15].name, "draft-ietf-xrblock-rtcp-xt-discard-metrics")
        self.assertEqual(documents[16].name, "draft-ietf-xrblock-rtcp-xr-post-repair-loss-count")
        self.assertEqual(documents[17].name, "draft-ietf-xrblock-rtcp-xr-psi-decodability")
        self.assertEqual(documents[18].name, "draft-ietf-xrblock-rtcweb-rtcp-xr-metrics")
        self.assertEqual(documents[19].name, "draft-ietf-xrblock-rtcp-xr-video-lc")
        self.assertEqual(documents[20].name, "draft-ietf-xrblock-independent-burst-gap-discard")


    # FIXME: this needs to be updated
    def test_document_from_draft(self) -> None:
        d  = self.dt.document_from_draft("draft-ietf-avt-rtp-new")
        if d is not None:
            self.assertEqual(d.resource_uri, DocumentURI(uri="/api/v1/doc/document/draft-ietf-avt-rtp-new/"))
        else:
            self.fail("Cannot find document")

    def test_document_from_rfc(self) -> None:
        d  = self.dt.document_from_rfc("rfc3550")
        if d is not None:
            self.assertEqual(d.resource_uri, DocumentURI(uri="/api/v1/doc/document/rfc3550/"))
        else:
            self.fail("Cannot find document")

    def test_documents_from_bcp(self) -> None:
        d  = list(self.dt.documents_from_bcp("bcp205"))
        if d is not None:
            self.assertEqual(len(d), 1)
            self.assertEqual(d[0].resource_uri, DocumentURI(uri="/api/v1/doc/document/rfc7942/"))
        else:
            self.fail("Cannot find document")

    def test_documents_from_std(self) -> None:
        d  = list(self.dt.documents_from_std("std68"))
        self.assertEqual(len(d), 1)
        self.assertEqual(d[0].resource_uri, DocumentURI(uri="/api/v1/doc/document/rfc5234/"))


    def test_document_state(self) -> None:
        s = self.dt.document_state(DocumentStateURI(uri="/api/v1/doc/state/7/"))
        if s is not None:
            self.assertEqual(s.id,           7)
            self.assertEqual(s.resource_uri, DocumentStateURI(uri="/api/v1/doc/state/7/"))
            self.assertEqual(s.name,         "RFC Published")
            self.assertEqual(s.desc,         "The ID has been published as an RFC.")
            self.assertEqual(s.type,         DocumentStateTypeURI(uri="/api/v1/doc/statetype/draft-iesg/"))
            self.assertEqual(s.next_states,  [DocumentStateURI(uri="/api/v1/doc/state/8/")])
            self.assertEqual(s.order,        32)
            self.assertEqual(s.slug,         "pub")
            self.assertEqual(s.used,         True)
        else:
            self.fail("Cannot find state")


    def test_document_states(self) -> None:
        st = self.dt.document_state_type(DocumentStateTypeURI(uri="/api/v1/doc/statetype/draft-rfceditor/"))
        states = list(self.dt.document_states(state_type = st))
        self.assertEqual(len(states), 19)
        self.assertEqual(states[ 0].name, 'AUTH')
        self.assertEqual(states[ 1].name, 'AUTH48')
        self.assertEqual(states[ 2].name, 'EDIT')
        self.assertEqual(states[ 3].name, 'IANA')
        self.assertEqual(states[ 4].name, 'IESG')
        self.assertEqual(states[ 5].name, 'ISR')
        self.assertEqual(states[ 6].name, 'ISR-AUTH')
        self.assertEqual(states[ 7].name, 'REF')
        self.assertEqual(states[ 8].name, 'RFC-EDITOR')
        self.assertEqual(states[ 9].name, 'TO')
        self.assertEqual(states[10].name, 'MISSREF')
        self.assertEqual(states[11].name, 'AUTH48-DONE')
        self.assertEqual(states[12].name, 'AUTH48-DONE')
        self.assertEqual(states[13].name, 'EDIT')
        self.assertEqual(states[14].name, 'IANA')
        self.assertEqual(states[15].name, 'IESG')
        self.assertEqual(states[16].name, 'ISR-AUTH')
        self.assertEqual(states[17].name, 'Pending')
        self.assertEqual(states[18].name, 'TI')


    def test_document_state_type(self) -> None:
        st = self.dt.document_state_type(DocumentStateTypeURI(uri="/api/v1/doc/statetype/draft-rfceditor/"))
        if st is not None:
            self.assertEqual(st.resource_uri, DocumentStateTypeURI(uri="/api/v1/doc/statetype/draft-rfceditor/"))
            self.assertEqual(st.slug,         "draft-rfceditor")
            self.assertEqual(st.label,        "RFC Editor state")
        else:
            self.fail("Cannot find state type")


    def test_document_state_types(self) -> None:
        st = list(self.dt.document_state_types())
        self.assertEqual(len(st), 34)
        self.assertEqual(st[ 0].slug, 'agenda')
        self.assertEqual(st[ 1].slug, 'bcp')
        self.assertEqual(st[ 2].slug, 'bluesheets')
        self.assertEqual(st[ 3].slug, 'bofreq')
        self.assertEqual(st[ 4].slug, 'charter')
        self.assertEqual(st[ 5].slug, 'chatlog')
        self.assertEqual(st[ 6].slug, 'conflrev')
        self.assertEqual(st[ 7].slug, 'draft')
        self.assertEqual(st[ 8].slug, 'draft-iana-action')
        self.assertEqual(st[ 9].slug, 'draft-iana-experts')
        self.assertEqual(st[10].slug, 'draft-iana-review')
        self.assertEqual(st[11].slug, 'draft-iesg')
        self.assertEqual(st[12].slug, 'draft-rfceditor')
        self.assertEqual(st[13].slug, 'draft-stream-editorial')
        self.assertEqual(st[14].slug, 'draft-stream-iab')
        self.assertEqual(st[15].slug, 'draft-stream-ietf')
        self.assertEqual(st[16].slug, 'draft-stream-irtf')
        self.assertEqual(st[17].slug, 'draft-stream-ise')
        self.assertEqual(st[18].slug, 'fyi')
        self.assertEqual(st[19].slug, 'liai-att')
        self.assertEqual(st[20].slug, 'liaison')
        self.assertEqual(st[21].slug, 'minutes')
        self.assertEqual(st[22].slug, 'narrativeminutes')
        self.assertEqual(st[23].slug, 'polls')
        self.assertEqual(st[24].slug, 'procmaterials')
        self.assertEqual(st[25].slug, 'recording')
        self.assertEqual(st[26].slug, 'reuse_policy')
        self.assertEqual(st[27].slug, 'review')
        self.assertEqual(st[28].slug, 'rfc')
        self.assertEqual(st[29].slug, 'shepwrit')
        self.assertEqual(st[30].slug, 'slides')
        self.assertEqual(st[31].slug, 'statchg')
        self.assertEqual(st[32].slug, 'statement')
        self.assertEqual(st[33].slug, 'std')


    def test_document_event(self) -> None:
        e = self.dt.document_event(DocumentEventURI(uri="/api/v1/doc/docevent/729040/"))
        if e is not None:
            self.assertEqual(e.id,              729040)
            self.assertEqual(e.resource_uri,    DocumentEventURI(uri="/api/v1/doc/docevent/729040/"))
            self.assertEqual(e.by,              PersonURI(uri="/api/v1/person/person/121595/"))
            self.assertEqual(e.doc,             DocumentURI(uri="/api/v1/doc/document/draft-irtf-cfrg-randomness-improvements/"))
            self.assertEqual(e.type,            "new_revision")
            self.assertEqual(e.desc,            "New version available: <b>draft-irtf-cfrg-randomness-improvements-09.txt</b>")
            self.assertEqual(e.rev,             "09")
            self.assertEqual(e.time,            datetime.fromisoformat("2020-01-27T06:41:36-08:00"))
        else:
            self.fail("Cannot find event")


    def test_document_events(self) -> None:
        p  = self.dt.person_from_email("csp@csperkins.org")
        d  = self.dt.document_from_draft("draft-ietf-avtcore-rtp-circuit-breakers")
        de = list(self.dt.document_events(doc=d, by=p, event_type="new_revision"))
        self.assertEqual(len(de), 19)
        self.assertEqual(de[ 0].id, 306017)
        self.assertEqual(de[ 1].id, 307226)
        self.assertEqual(de[ 2].id, 326064)
        self.assertEqual(de[ 3].id, 340119)
        self.assertEqual(de[ 4].id, 364835)
        self.assertEqual(de[ 5].id, 369306)
        self.assertEqual(de[ 6].id, 384673)
        self.assertEqual(de[ 7].id, 397776)
        self.assertEqual(de[ 8].id, 402942)
        self.assertEqual(de[ 9].id, 413197)
        self.assertEqual(de[10].id, 415925)
        self.assertEqual(de[11].id, 444539)
        self.assertEqual(de[12].id, 456736)
        self.assertEqual(de[13].id, 456912)
        self.assertEqual(de[14].id, 460235)
        self.assertEqual(de[15].id, 466353)
        self.assertEqual(de[16].id, 470372)
        self.assertEqual(de[17].id, 475709)
        self.assertEqual(de[18].id, 478637)


    def test_document_events_without_type(self) -> None:
        p  = self.dt.person_from_email("csp@csperkins.org")
        d  = self.dt.document_from_draft("draft-ietf-avtcore-rtp-circuit-breakers")
        de = list(self.dt.document_events(doc=d, by=p))
        self.assertEqual(len(de), 22)


    def test_ballot_position_name(self) -> None:
        bp = self.dt.ballot_position_name(BallotPositionNameURI(uri="/api/v1/name/ballotpositionname/moretime/"))
        if bp is not None:
            self.assertEqual(bp.blocking,     False)
            self.assertEqual(bp.desc,         "")
            self.assertEqual(bp.order,        0)
            self.assertEqual(bp.resource_uri, BallotPositionNameURI(uri="/api/v1/name/ballotpositionname/moretime/"))
            self.assertEqual(bp.slug,         "moretime")
            self.assertEqual(bp.used,         True)


    def test_ballot_position_name_from_slug(self) -> None:
        bp = self.dt.ballot_position_name_from_slug("moretime")
        if bp is not None:
            self.assertEqual(bp.blocking,     False)
            self.assertEqual(bp.desc,         "")
            self.assertEqual(bp.order,        0)
            self.assertEqual(bp.resource_uri, BallotPositionNameURI(uri="/api/v1/name/ballotpositionname/moretime/"))
            self.assertEqual(bp.slug,         "moretime")
            self.assertEqual(bp.used,         True)


    def test_ballot_position_names(self) -> None:
        bps = list(self.dt.ballot_position_names())
        self.assertEqual(len(bps), 10)
        self.assertEqual(bps[0].slug, "abstain")
        self.assertEqual(bps[1].slug, "block")
        self.assertEqual(bps[2].slug, "concern")
        self.assertEqual(bps[3].slug, "discuss")
        self.assertEqual(bps[4].slug, "moretime")
        self.assertEqual(bps[5].slug, "noobj")
        self.assertEqual(bps[6].slug, "norecord")
        self.assertEqual(bps[7].slug, "notready")
        self.assertEqual(bps[8].slug, "recuse")
        self.assertEqual(bps[9].slug, "yes")


    def test_ballot_type(self) -> None:
        bt = self.dt.ballot_type(BallotTypeURI(uri="/api/v1/doc/ballottype/5/"))
        if bt is not None:
            self.assertEqual(bt.doc_type,       DocumentTypeURI(uri="/api/v1/name/doctypename/conflrev/"))
            self.assertEqual(bt.id,             5)
            self.assertEqual(bt.name,           "Approve")
            self.assertEqual(bt.order,          0)
            self.assertEqual(len(bt.positions), 6)
            self.assertEqual(bt.positions[0],   BallotPositionNameURI(uri="/api/v1/name/ballotpositionname/yes/"))
            self.assertEqual(bt.positions[1],   BallotPositionNameURI(uri="/api/v1/name/ballotpositionname/noobj/"))
            self.assertEqual(bt.positions[2],   BallotPositionNameURI(uri="/api/v1/name/ballotpositionname/discuss/"))
            self.assertEqual(bt.positions[3],   BallotPositionNameURI(uri="/api/v1/name/ballotpositionname/abstain/"))
            self.assertEqual(bt.positions[4],   BallotPositionNameURI(uri="/api/v1/name/ballotpositionname/recuse/"))
            self.assertEqual(bt.positions[5],   BallotPositionNameURI(uri="/api/v1/name/ballotpositionname/norecord/"))
            self.assertEqual(bt.question,       "Is this the correct conflict review response?")
            self.assertEqual(bt.resource_uri,   BallotTypeURI(uri="/api/v1/doc/ballottype/5/"))
            self.assertEqual(bt.slug,           "conflrev")
            self.assertEqual(bt.used,           True)
        else:
            self.fail("Could not find ballot type")


    def test_ballot_types_doctype(self) -> None:
        bts = list(self.dt.ballot_types(self.dt.document_type(DocumentTypeURI(uri="/api/v1/name/doctypename/draft/"))))
        self.assertEqual(len(bts), 3)
        self.assertEqual(bts[0].slug, "approve")
        self.assertEqual(bts[1].slug, "irsg-approve")


    def test_ballot_document_event(self) -> None:
        e = self.dt.ballot_document_event(BallotDocumentEventURI(uri="/api/v1/doc/ballotdocevent/744784/"))
        if e is not None:
            self.assertEqual(e.ballot_type,  BallotTypeURI(uri="/api/v1/doc/ballottype/5/"))
            self.assertEqual(e.by,           PersonURI(uri="/api/v1/person/person/21684/"))
            self.assertEqual(e.desc,         'Created "Approve" ballot')
            self.assertEqual(e.doc,          DocumentURI(uri="/api/v1/doc/document/conflict-review-dold-payto/"))
            self.assertEqual(e.docevent_ptr, DocumentEventURI(uri="/api/v1/doc/docevent/744784/"))
            self.assertEqual(e.id,           744784)
            self.assertEqual(e.resource_uri, BallotDocumentEventURI(uri="/api/v1/doc/ballotdocevent/744784/"))
            self.assertEqual(e.rev,          "00")
            self.assertEqual(e.time,         datetime.fromisoformat("2020-04-04T10:57:29-07:00"))
            self.assertEqual(e.type,         "created_ballot")
        else:
            self.fail("Cannot find ballot event")


    def test_ballot_document_events(self) -> None:
        d  = self.dt.document_from_draft("draft-ietf-avtcore-rtp-circuit-breakers")
        de = list(self.dt.ballot_document_events(doc=d))
        self.assertEqual(len(de), 2)
        self.assertEqual(de[0].id, 461800)
        self.assertEqual(de[1].id, 478676)

        bt = self.dt.ballot_type(BallotTypeURI(uri="/api/v1/doc/ballottype/3/")) # Charter approval
        p  = self.dt.person(PersonURI(uri="/api/v1/person/person/108756/"))      # Cindy Morgan
        d  = self.dt.document(DocumentURI(uri="/api/v1/doc/document/charter-ietf-rmcat/"))
        de = list(self.dt.ballot_document_events(doc = d, ballot_type = bt, by = p, event_type = "closed_ballot"))
        self.assertEqual(len(de), 1)
        self.assertEqual(de[0].id, 304166)


    def test_documents_authored_by_person(self) -> None:
        p = self.dt.person_from_email("ladan@isi.edu")
        if p is not None:
            a = list(self.dt.documents_authored_by_person(p))
            self.assertEqual(len(a), 9)
            self.assertEqual(a[0].document, DocumentURI(uri='/api/v1/doc/document/draft-gharai-ac3/'))
            self.assertEqual(a[1].document, DocumentURI(uri='/api/v1/doc/document/draft-gharai-hdtv-video/'))
            self.assertEqual(a[2].document, DocumentURI(uri='/api/v1/doc/document/draft-ietf-avt-smpte292-video/'))
            self.assertEqual(a[3].document, DocumentURI(uri='/api/v1/doc/document/draft-gharai-avt-uncomp-video/'))
            self.assertEqual(a[4].document, DocumentURI(uri='/api/v1/doc/document/draft-ietf-avt-uncomp-video/'))
            self.assertEqual(a[5].document, DocumentURI(uri='/api/v1/doc/document/draft-gharai-avt-tfrc-profile/'))
            self.assertEqual(a[6].document, DocumentURI(uri='/api/v1/doc/document/draft-ietf-avt-tfrc-profile/'))
            self.assertEqual(a[7].document, DocumentURI(uri='/api/v1/doc/document/rfc3497/'))
            self.assertEqual(a[8].document, DocumentURI(uri='/api/v1/doc/document/rfc4175/'))
        else:
            self.fail("Cannot find person");


    def test_documents_authored_by_email(self) -> None:
        e = self.dt.email(EmailURI(uri="/api/v1/person/email/ladan@isi.edu/"))
        if e is not None:
            a = list(self.dt.documents_authored_by_email(e))
            self.assertEqual(len(a), 9)
            self.assertEqual(a[0].document, DocumentURI(uri='/api/v1/doc/document/draft-gharai-ac3/'))
            self.assertEqual(a[1].document, DocumentURI(uri='/api/v1/doc/document/draft-gharai-hdtv-video/'))
            self.assertEqual(a[2].document, DocumentURI(uri='/api/v1/doc/document/draft-ietf-avt-smpte292-video/'))
            self.assertEqual(a[3].document, DocumentURI(uri='/api/v1/doc/document/draft-gharai-avt-uncomp-video/'))
            self.assertEqual(a[4].document, DocumentURI(uri='/api/v1/doc/document/draft-ietf-avt-uncomp-video/'))
            self.assertEqual(a[5].document, DocumentURI(uri='/api/v1/doc/document/draft-gharai-avt-tfrc-profile/'))
            self.assertEqual(a[6].document, DocumentURI(uri='/api/v1/doc/document/draft-ietf-avt-tfrc-profile/'))
            self.assertEqual(a[7].document, DocumentURI(uri='/api/v1/doc/document/rfc3497/'))
            self.assertEqual(a[8].document, DocumentURI(uri='/api/v1/doc/document/rfc4175/'))
        else:
            self.fail("Cannot find person");




    # FIXME: this needs to be updated
    def test_submission(self) -> None:
        s  = self.dt.submission(SubmissionURI(uri="/api/v1/submit/submission/2402/"))
        if s is not None:
            #self.assertEqual(s.abstract,        "Internet technical specifications often need to...")
            self.assertEqual(s.access_key,      "f77d08da6da54f3cbecca13d31646be8")
            self.assertEqual(s.auth_key,        "fMm6hur5dJ7gV58x5SE0vkHUoDOrSuSF")
            self.assertEqual(s.authors,         "[{'email': 'dcrocker@bbiw.net', 'name': 'Dave Crocker'}, {'email': 'paul.overell@thus.net', 'name': 'Paul Overell'}]")
            self.assertEqual(s.checks,          [SubmissionCheckURI(uri="/api/v1/submit/submissioncheck/386/")])
            self.assertEqual(s.document_date,   date.fromisoformat("2007-10-09"))
            self.assertEqual(s.draft,           DocumentURI(uri="/api/v1/doc/document/draft-crocker-rfc4234bis/"))
            self.assertEqual(s.file_size,       27651)
            self.assertEqual(s.file_types,      ".txt,.xml,.pdf")
            #self.assertEqual(s.first_two_pages, "\n\n\nNetwork Working Group...")
            self.assertEqual(s.group,           GroupURI(uri="/api/v1/group/group/1027/"))
            self.assertEqual(s.id,              2402)
            self.assertEqual(s.name,            "draft-crocker-rfc4234bis")
            self.assertEqual(s.note,            "")
            self.assertEqual(s.pages,           13)
            self.assertEqual(s.remote_ip,       "72.255.3.179")
            self.assertEqual(s.replaces,        "")
            self.assertEqual(s.resource_uri,    SubmissionURI(uri="/api/v1/submit/submission/2402/"))
            self.assertEqual(s.rev,             "01")
            self.assertEqual(s.state,           "/api/v1/name/draftsubmissionstatename/posted/")
            self.assertEqual(s.submission_date, date.fromisoformat("2007-10-09"))
            self.assertEqual(s.submitter,       "Dave Crocker")
            self.assertEqual(s.title,           "Augmented BNF for Syntax Specifications: ABNF")
            self.assertEqual(s.words,           None)
            self.assertEqual(s.xml_version,     None)
        else:
            self.fail("Cannot find submission")


    def test_submission_event(self) -> None:
        e  = self.dt.submission_event(SubmissionEventURI(uri="/api/v1/submit/submissionevent/188542/"))
        if e is not None:
            self.assertEqual(e.by,           PersonURI(uri="/api/v1/person/person/115824/"))
            self.assertEqual(e.desc,         "Uploaded submission")
            self.assertEqual(e.id,           188542)
            self.assertEqual(e.resource_uri, SubmissionEventURI(uri="/api/v1/submit/submissionevent/188542/"))
            self.assertEqual(e.submission,   SubmissionURI(uri="/api/v1/submit/submission/111128/"))
            self.assertEqual(e.time,         datetime.fromisoformat("2020-03-23T04:18:27-07:00"))
        else:
            self.fail("Cannot find submission event")


    def test_document_url(self) -> None:
        doc_url = self.dt.document_url(DocumentUrlURI(uri="/api/v1/doc/documenturl/4594/"))
        if doc_url is not None:
            self.assertEqual(doc_url.desc,         "")
            self.assertEqual(doc_url.doc,          DocumentURI(uri="/api/v1/doc/document/draft-mcquistin-augmented-ascii-diagrams/"))
            self.assertEqual(doc_url.id,           4594)
            self.assertEqual(doc_url.resource_uri, DocumentUrlURI(uri="/api/v1/doc/documenturl/4594/"))
            self.assertEqual(doc_url.tag,          DocumentUrlTagURI(uri="/api/v1/name/docurltagname/repository/"))
            self.assertEqual(doc_url.url,          "https://github.com/glasgow-ipl/draft-mcquistin-augmented-ascii-diagrams")
        else:
            self.fail("Cannot find document URL")
            
            
    def test_document_urls(self) -> None:
        doc_urls = list(self.dt.document_urls(self.dt.document(DocumentURI(uri="/api/v1/doc/document/draft-mcquistin-augmented-ascii-diagrams/"))))
        self.assertEqual(len(doc_urls),  1)
        self.assertEqual(doc_urls[0].id, 4594)


    def test_document_type(self) -> None:
        doctype = self.dt.document_type(DocumentTypeURI(uri="/api/v1/name/doctypename/draft/"))
        if doctype is not None:
            self.assertEqual(doctype.resource_uri, DocumentTypeURI(uri="/api/v1/name/doctypename/draft/"))
            self.assertEqual(doctype.name,         "Draft")
            self.assertEqual(doctype.used,         True)
            self.assertEqual(doctype.prefix,       "draft")
            self.assertEqual(doctype.slug,         "draft")
            self.assertEqual(doctype.desc,         "")
            self.assertEqual(doctype.order,        0)
        else:
            self.fail("Cannot find doctype")


    def test_document_type_from_slug(self) -> None:
        doctype = self.dt.document_type_from_slug("draft")
        if doctype is not None:
            self.assertEqual(doctype.resource_uri, DocumentTypeURI(uri="/api/v1/name/doctypename/draft/"))
            self.assertEqual(doctype.name,         "Draft")
            self.assertEqual(doctype.used,         True)
            self.assertEqual(doctype.prefix,       "draft")
            self.assertEqual(doctype.slug,         "draft")
            self.assertEqual(doctype.desc,         "")
            self.assertEqual(doctype.order,        0)
        else:
            self.fail("Cannot find doctype")


    def test_document_types(self) -> None:
        types = list(self.dt.document_types())
        self.assertEqual(len(types), 23)
        self.assertEqual(types[ 0].slug, "agenda")
        self.assertEqual(types[ 1].slug, "bcp")
        self.assertEqual(types[ 2].slug, "bluesheets")
        self.assertEqual(types[ 3].slug, "bofreq")
        self.assertEqual(types[ 4].slug, "charter")
        self.assertEqual(types[ 5].slug, "chatlog")
        self.assertEqual(types[ 6].slug, "conflrev")
        self.assertEqual(types[ 7].slug, "draft")
        self.assertEqual(types[ 8].slug, "fyi")
        self.assertEqual(types[ 9].slug, "liai-att")
        self.assertEqual(types[10].slug, "liaison")
        self.assertEqual(types[11].slug, "minutes")
        self.assertEqual(types[12].slug, "narrativeminutes")
        self.assertEqual(types[13].slug, "polls")
        self.assertEqual(types[14].slug, "procmaterials")
        self.assertEqual(types[15].slug, "recording")
        self.assertEqual(types[16].slug, "review")
        self.assertEqual(types[17].slug, "rfc")
        self.assertEqual(types[18].slug, "shepwrit")
        self.assertEqual(types[19].slug, "slides")
        self.assertEqual(types[20].slug, "statchg")
        self.assertEqual(types[21].slug, "statement")
        self.assertEqual(types[22].slug, "std")

    # -----------------------------------------------------------------------------------------------------------------------------
    # Tests relating to streams:

    def test_stream(self) -> None:
        stream = self.dt.stream(StreamURI(uri="/api/v1/name/streamname/irtf/"))
        if stream is not None:
            self.assertEqual(stream.desc,         "Internet Research Task Force (IRTF)")
            self.assertEqual(stream.name,         "IRTF")
            self.assertEqual(stream.order,        3)
            self.assertEqual(stream.resource_uri, StreamURI(uri="/api/v1/name/streamname/irtf/"))
            self.assertEqual(stream.slug,         "irtf")
            self.assertEqual(stream.used,         True)
        else:
            self.fail("Cannot find stream")


    def test_stream_from_slug(self) -> None:
        stream = self.dt.stream_from_slug("irtf")
        if stream is not None:
            self.assertEqual(stream.desc,         "Internet Research Task Force (IRTF)")
            self.assertEqual(stream.name,         "IRTF")
            self.assertEqual(stream.order,        3)
            self.assertEqual(stream.resource_uri, StreamURI(uri="/api/v1/name/streamname/irtf/"))
            self.assertEqual(stream.slug,         "irtf")
            self.assertEqual(stream.used,         True)
        else:
            self.fail("Cannot find stream")


    def test_streams(self) -> None:
        streams = list(self.dt.streams())
        self.assertEqual(len(streams), 6)
        self.assertEqual(streams[ 0].slug, "editorial")
        self.assertEqual(streams[ 1].slug, "iab")
        self.assertEqual(streams[ 2].slug, "ietf")
        self.assertEqual(streams[ 3].slug, "irtf")
        self.assertEqual(streams[ 4].slug, "ise")
        self.assertEqual(streams[ 5].slug, "legacy")

    # -----------------------------------------------------------------------------------------------------------------------------
    # Tests relating to groups:

    # FIXME: this needs to be updated
    def test_group(self) -> None:
        group = self.dt.group(GroupURI(uri="/api/v1/group/group/941/"))
        if group is not None:
            self.assertEqual(group.acronym,        "avt")
            self.assertEqual(group.ad,             None)
            self.assertEqual(group.charter,        DocumentURI(uri="/api/v1/doc/document/charter-ietf-avt/"))
            self.assertEqual(group.comments,       "")
            self.assertEqual(group.description,    "\n  The Audio/Video Transport Working Group was formed to specify a protocol \n  for real-time transmission of audio and video over unicast and multicast \n  UDP/IP. This is the Real-time Transport Protocol, RTP, along with its \n  associated profiles and payload formats.")
            self.assertEqual(group.id,             941)
            self.assertEqual(group.list_archive,   "https://mailarchive.ietf.org/arch/browse/avt")
            self.assertEqual(group.list_email,     "avt@ietf.org")
            self.assertEqual(group.list_subscribe, "https://www.ietf.org/mailman/listinfo/avt")
            self.assertEqual(group.name,           "Audio/Video Transport")
            self.assertEqual(group.parent,         GroupURI(uri="/api/v1/group/group/1683/"))
            self.assertEqual(group.resource_uri,   GroupURI(uri="/api/v1/group/group/941/"))
            self.assertEqual(group.state,          GroupStateURI(uri="/api/v1/name/groupstatename/conclude/"))
            self.assertEqual(group.time,           datetime.fromisoformat("2011-12-09T12:00:00-08:00"))
            self.assertEqual(group.type,           GroupTypeNameURI(uri="/api/v1/name/grouptypename/wg/"))
            self.assertEqual(group.unused_states,  [])
            self.assertEqual(group.unused_tags,    [])
            self.assertEqual(group.meeting_seen_as_area, False)
            self.assertEqual(group.used_roles,           "[]")
            self.assertEqual(group.uses_milestone_dates, True)
        else:
            self.fail("Cannot find group")


    def test_group_from_acronym(self) -> None:
        group = self.dt.group_from_acronym("avt")
        if group is not None:
            self.assertEqual(group.id, 941)
        else:
            self.fail("Cannot find group")


    def test_group_from_acronym_invalid(self) -> None:
        group = self.dt.group_from_acronym("invalid")
        self.assertIsNone(group)


    def test_groups(self) -> None:
        groups = self.dt.groups()
        self.assertIsNot(groups, None)


    def test_groups_namecontains(self) -> None:
        groups = list(self.dt.groups(name_contains="IRTF"))
        self.assertEqual(len(groups), 4)
        self.assertEqual(groups[0].id,    3)  # IRTF
        self.assertEqual(groups[1].id, 1853)  # IRTF Open Meeting
        self.assertEqual(groups[2].id, 2282)  # ACM/IRTF Applied Networking Research Workshop
        self.assertEqual(groups[3].id, 2372)  # IAB/IRTF Workshop on Congestion Control for Interactive Real-Time Communication


    def test_group_history(self) -> None:
        group_history = self.dt.group_history(GroupHistoryURI(uri="/api/v1/group/grouphistory/4042/"))
        if group_history is not None:
            self.assertEqual(group_history.acronym,              "git")
            self.assertEqual(group_history.ad,                   None)
            self.assertEqual(group_history.comments,             "")
            self.assertEqual(group_history.description,          "")
            self.assertEqual(group_history.group,                GroupURI(uri="/api/v1/group/group/2233/"))
            self.assertEqual(group_history.id,                   4042)
            self.assertEqual(group_history.list_archive,         "https://mailarchive.ietf.org/arch/browse/ietf-and-github/")
            self.assertEqual(group_history.list_email,           "ietf-and-github@ietf.org")
            self.assertEqual(group_history.list_subscribe,       "https://www.ietf.org/mailman/listinfo/ietf-and-github")
            self.assertEqual(group_history.name,                 "GitHub Integration and Tooling")
            self.assertEqual(group_history.parent,               GroupURI(uri="/api/v1/group/group/1008/"))
            self.assertEqual(group_history.resource_uri,         GroupHistoryURI(uri="/api/v1/group/grouphistory/4042/"))
            self.assertEqual(group_history.state,                GroupStateURI(uri="/api/v1/name/groupstatename/active/"))
            self.assertEqual(group_history.time,                 datetime.fromisoformat("2019-02-08T14:07:27-08:00"))
            self.assertEqual(group_history.type,                 GroupTypeNameURI(uri="/api/v1/name/grouptypename/wg/"))
            self.assertEqual(group_history.unused_states,        [])
            self.assertEqual(group_history.unused_tags,          [])
            self.assertEqual(group_history.meeting_seen_as_area, False)
            self.assertEqual(group_history.used_roles,           "[]")
            self.assertEqual(group_history.uses_milestone_dates, True)
        else:
            self.fail("Cannot find group history")


    def test_group_histories_from_acronym(self) -> None:
        group_histories = list(self.dt.group_histories_from_acronym("spud"))
        self.assertEqual(len(group_histories), 2)
        self.assertEqual(group_histories[0].id, 2179)
        self.assertEqual(group_histories[1].id, 2257)


    def test_group_histories_group(self) -> None:
        avt = self.dt.group_from_acronym("spud")
        group_histories = list(self.dt.group_histories(group=avt))
        self.assertEqual(len(group_histories), 2)
        self.assertEqual(group_histories[0].id, 2179)
        self.assertEqual(group_histories[1].id, 2257)


    def test_group_event(self) -> None:
        group_event = self.dt.group_event(GroupEventURI(uri="/api/v1/group/groupevent/16849/"))
        if group_event is not None:
            self.assertEqual(group_event.by,           PersonURI(uri="/api/v1/person/person/108756/"))
            self.assertEqual(group_event.desc,         "Added milestone \"Submit data flow information model (informational)\", due 2020-04-30, from approved charter")
            self.assertEqual(group_event.group,        GroupURI(uri="/api/v1/group/group/1962/"))
            self.assertEqual(group_event.id,           16849)
            self.assertEqual(group_event.resource_uri, GroupEventURI(uri="/api/v1/group/groupevent/16849/"))
            self.assertEqual(group_event.time,         datetime.fromisoformat("2020-04-20T13:31:48-07:00"))
            self.assertEqual(group_event.type,         "changed_milestone")
        else:
            self.fail("Cannot find group event")


    def test_group_events_by(self) -> None:
        group_events_by = self.dt.group_events(by=self.dt.person(PersonURI(uri="/api/v1/person/person/108756/")))
        self.assertIsNot(group_events_by, None)


    def test_group_events_group(self) -> None:
        group_events_group = list(self.dt.group_events(group=self.dt.group(GroupURI(uri="/api/v1/group/group/1997/"))))
        self.assertEqual(len(group_events_group),  4)
        self.assertEqual(group_events_group[0].id, 8975)
        self.assertEqual(group_events_group[1].id, 9151)
        self.assertEqual(group_events_group[2].id, 9585)
        self.assertEqual(group_events_group[3].id, 9652)


    def test_group_events_type(self) -> None:
        group_events_type = self.dt.group_events(type="changed_state")
        self.assertIsNot(group_events_type, None)


    def test_group_url(self) -> None:
        group_url = self.dt.group_url(GroupUrlURI(uri="/api/v1/group/groupurl/1/"))
        if group_url is not None:
            self.assertEqual(group_url.group,        GroupURI(uri="/api/v1/group/group/934/"))
            self.assertEqual(group_url.id,           1)
            self.assertEqual(group_url.name,         "Applications Area Web Page")
            self.assertEqual(group_url.resource_uri, GroupUrlURI(uri="/api/v1/group/groupurl/1/"))
            self.assertEqual(group_url.url,          "http://www.apps.ietf.org/")
        else:
            self.fail("Cannot find group URL")


    def test_group_urls(self) -> None:
        group_urls = list(self.dt.group_urls(self.dt.group(GroupURI(uri="/api/v1/group/group/1062/"))))
        self.assertEqual(len(group_urls),  1)
        self.assertEqual(group_urls[0].id, 20)


    def test_group_milestone_statename(self) -> None:
        group_milestone_statename = self.dt.group_milestone_statename(GroupMilestoneStateNameURI(uri="/api/v1/name/groupmilestonestatename/active/"))
        if group_milestone_statename is not None:
            self.assertEqual(group_milestone_statename.desc,  "")
            self.assertEqual(group_milestone_statename.order, 1)
            self.assertEqual(group_milestone_statename.slug,  "active")
            self.assertEqual(group_milestone_statename.used,  True)
        else:
            self.fail("Cannot find group milestone state name")


    def test_group_milestone_statenames(self) -> None:
        group_milestone_statenames = list(self.dt.group_milestone_statenames())
        self.assertEqual(len(group_milestone_statenames),    4)
        self.assertEqual(group_milestone_statenames[0].slug, "active")
        self.assertEqual(group_milestone_statenames[1].slug, "charter")
        self.assertEqual(group_milestone_statenames[2].slug, "deleted")
        self.assertEqual(group_milestone_statenames[3].slug, "review")


    def test_group_milestone(self) -> None:
        group_milestone = self.dt.group_milestone(GroupMilestoneURI(uri="/api/v1/group/groupmilestone/1520/"))
        if group_milestone is not None:
            self.assertEqual(group_milestone.desc,         "Define a protocol for the link and IP layer.")
            self.assertEqual(group_milestone.docs,         [])
            self.assertEqual(group_milestone.due,          "1988-03-31")
            self.assertEqual(group_milestone.group,        GroupURI(uri="/api/v1/group/group/1209/"))
            self.assertEqual(group_milestone.id,           1520)
            self.assertEqual(group_milestone.order,        None)
            self.assertEqual(group_milestone.resolved,     "")
            self.assertEqual(group_milestone.resource_uri, GroupMilestoneURI(uri="/api/v1/group/groupmilestone/1520/"))
            self.assertEqual(group_milestone.state,        GroupMilestoneStateNameURI(uri="/api/v1/name/groupmilestonestatename/active/"))
            self.assertEqual(group_milestone.time,         datetime.fromisoformat("2012-02-26T00:21:52-08:00"))
        else:
            self.fail("Cannot find group milestone")


    def test_group_milestones(self) -> None:
        group_milestones = self.dt.group_milestones()
        self.assertIsNot(group_milestones, None)


    def test_group_milestones_group(self) -> None:
        group_milestones = list(self.dt.group_milestones(group=self.dt.group(GroupURI(uri="/api/v1/group/group/1209/"))))
        self.assertEqual(len(group_milestones),  1)
        self.assertEqual(group_milestones[0].id, 1520)
        self.assertIsNot(group_milestones, None)


    def test_group_milestones_state(self) -> None:
        group_milestones = self.dt.group_milestones(state=self.dt.group_milestone_statename(GroupMilestoneStateNameURI(uri="/api/v1/name/groupmilestonestatename/active/")))
        self.assertIsNot(group_milestones, None)


    def test_role_name(self) -> None:
        role_name = self.dt.role_name(RoleNameURI(uri="/api/v1/name/rolename/ceo/"))
        if role_name is not None:
            self.assertEqual(role_name.desc,         "")
            self.assertEqual(role_name.name,         "CEO")
            self.assertEqual(role_name.order,        0)
            self.assertEqual(role_name.resource_uri, RoleNameURI(uri="/api/v1/name/rolename/ceo/"))
            self.assertEqual(role_name.slug,         "ceo")
            self.assertEqual(role_name.used,         True)
        else:
            self.fail("Cannot find role name")


    def test_role_name_from_slug(self) -> None:
        role_name = self.dt.role_name_from_slug("ceo")
        if role_name is not None:
            self.assertEqual(role_name.desc,         "")
            self.assertEqual(role_name.name,         "CEO")
            self.assertEqual(role_name.order,        0)
            self.assertEqual(role_name.resource_uri, RoleNameURI(uri="/api/v1/name/rolename/ceo/"))
            self.assertEqual(role_name.slug,         "ceo")
            self.assertEqual(role_name.used,         True)
        else:
            self.fail("Cannot find role name")


    def test_role_names(self) -> None:
        role_names = list(self.dt.role_names())
        self.assertEqual(len(role_names), 35)
        self.assertEqual(role_names[ 0].slug, "ad")
        self.assertEqual(role_names[ 1].slug, "admdir")
        self.assertEqual(role_names[ 2].slug, "advisor")
        self.assertEqual(role_names[ 3].slug, "announce")
        self.assertEqual(role_names[ 4].slug, "atlarge")
        self.assertEqual(role_names[ 5].slug, "auth")
        self.assertEqual(role_names[ 6].slug, "ceo")
        self.assertEqual(role_names[ 7].slug, "chair")
        self.assertEqual(role_names[ 8].slug, "comdir")
        self.assertEqual(role_names[ 9].slug, "coord")
        self.assertEqual(role_names[10].slug, "delegate")
        self.assertEqual(role_names[11].slug, "devdir")
        self.assertEqual(role_names[12].slug, "editor")
        self.assertEqual(role_names[13].slug, "execdir")
        self.assertEqual(role_names[14].slug, "exofficio")
        self.assertEqual(role_names[15].slug, "lead")
        self.assertEqual(role_names[16].slug, "leadmaintainer")
        self.assertEqual(role_names[17].slug, "liaiman")
        self.assertEqual(role_names[18].slug, "liaison")
        self.assertEqual(role_names[19].slug, "liaison_cc_contact")
        self.assertEqual(role_names[20].slug, "liaison_contact")
        self.assertEqual(role_names[21].slug, "matman")
        self.assertEqual(role_names[22].slug, "member")
        self.assertEqual(role_names[23].slug, "pre-ad")
        self.assertEqual(role_names[24].slug, "recman")
        self.assertEqual(role_names[25].slug, "reviewer")
        self.assertEqual(role_names[26].slug, "robot")
        self.assertEqual(role_names[27].slug, "secr")
        self.assertEqual(role_names[28].slug, "techadv")
        self.assertEqual(role_names[29].slug, "trac-admin")
        self.assertEqual(role_names[30].slug, "trac-editor")
        self.assertEqual(role_names[31].slug, "wikiadmin")
        self.assertEqual(role_names[32].slug, "wikiman")
        self.assertEqual(role_names[33].slug, "yc_admin")
        self.assertEqual(role_names[34].slug, "yc_operator")



    def test_group_role(self) -> None:
        group_role = self.dt.group_role(GroupRoleURI(uri="/api/v1/group/role/1076/"))
        if group_role is not None:
            self.assertEqual(group_role.email,  EmailURI(uri="/api/v1/person/email/csp@csperkins.org/"))
            self.assertEqual(group_role.group,  GroupURI(uri="/api/v1/group/group/1727/"))
            self.assertEqual(group_role.id,     1076)
            self.assertEqual(group_role.name,   RoleNameURI(uri="/api/v1/name/rolename/chair/"))
            self.assertEqual(group_role.person, PersonURI(uri="/api/v1/person/person/20209/"))
        else:
            self.fail("Cannot find group role")


    def test_group_roles(self) -> None:
        group_roles = self.dt.group_roles()
        self.assertIsNot(group_roles, None)


    def test_group_roles_email(self) -> None:
        group_roles = list(self.dt.group_roles(email="csp@csperkins.org"))
        self.assertEqual(len(group_roles), 13)
        self.assertEqual(group_roles[0].id, 1076)   # SAFE BoF chair
        self.assertEqual(group_roles[1].id, 3998)   # TSV DIR reviewer
        self.assertEqual(group_roles[2].id, 8464)   # IRSG chair
        self.assertEqual(group_roles[3].id, 8465)   # IRTF Open Meeting chair
        self.assertEqual(group_roles[4].id, 8466)   # IRTF chair
        self.assertEqual(group_roles[5].id, 9355)   # RMCAT chair
        self.assertEqual(group_roles[6].id, 11103)  # TSV ART reviewer
        self.assertEqual(group_roles[7].id, 11680)  # IRTF ANRW chair
        self.assertEqual(group_roles[8].id, 12875)  # RSAB member
        self.assertEqual(group_roles[9].id, 12915)  # IAB-ISOC Policy Coordination
        self.assertEqual(group_roles[10].id, 13098) # IAB E-Impact workshop
        self.assertEqual(group_roles[11].id, 13698) # IAB
        self.assertEqual(group_roles[12].id, 13726) # 


    def test_group_roles_group(self) -> None:
        group_roles = list(self.dt.group_roles(group=self.dt.group(GroupURI(uri="/api/v1/group/group/1997/")))) # SPUD BoF
        self.assertEqual(len(group_roles), 3)
        self.assertEqual(group_roles[0].id, 3036)   # AD is Spencer Dawkins
        self.assertEqual(group_roles[1].id, 3037)   # Chair is Eliot Lear
        self.assertEqual(group_roles[2].id, 3038)   # Chair is Mirja Kühlewind


    def test_group_roles_group_name(self) -> None:
        iab   = self.dt.group_from_acronym("iab")
        chair = self.dt.role_name_from_slug("chair")
        group_roles = list(self.dt.group_roles(group = iab, name = chair))
        self.assertEqual(len(group_roles), 1)
        self.assertEqual(group_roles[0].id, 13626)   # IAB chair is Tommy Pauley



    def test_group_roles_name(self) -> None:
        group_roles = self.dt.group_roles(name=self.dt.role_name(RoleNameURI(uri="/api/v1/name/rolename/chair/")))
        self.assertIsNot(group_roles, None)


    def test_group_roles_person(self) -> None:
        group_roles = list(self.dt.group_roles(person=self.dt.person(PersonURI(uri="/api/v1/person/person/20209/"))))
        self.assertEqual(len(group_roles), 13)
        self.assertEqual(group_roles[0].id, 1076)   # SAFE BoF chair
        self.assertEqual(group_roles[1].id, 3998)   # TSV DIR reviewer
        self.assertEqual(group_roles[2].id, 8464)   # IRSG chair
        self.assertEqual(group_roles[3].id, 8465)   # IRTF Open Meeting chair
        self.assertEqual(group_roles[4].id, 8466)   # IRTF chair
        self.assertEqual(group_roles[5].id, 9355)   # RMCAT chair
        self.assertEqual(group_roles[6].id, 11103)  # TSV ART reviewer
        self.assertEqual(group_roles[7].id, 11680)  # IRTF ANRW chair
        self.assertEqual(group_roles[8].id, 12875)  # RSAB member
        self.assertEqual(group_roles[9].id, 12915)  # IAB-ISOC Policy Coordination
        self.assertEqual(group_roles[10].id, 13098) # IAB E-Impact workshop
        self.assertEqual(group_roles[11].id, 13698) # IAB
        self.assertEqual(group_roles[12].id, 13726) # 


    def test_group_milestone_history(self) -> None:
        group_milestone_history = self.dt.group_milestone_history(GroupMilestoneHistoryURI(uri="/api/v1/group/groupmilestonehistory/1433/"))
        if group_milestone_history is not None:
            self.assertEqual(group_milestone_history.desc,         "Agreement on charter and issues in current draft.")
            self.assertEqual(group_milestone_history.docs,         [])
            self.assertEqual(group_milestone_history.due,          "1996-05-31")
            self.assertEqual(group_milestone_history.group,        GroupURI(uri="/api/v1/group/group/1326/"))
            self.assertEqual(group_milestone_history.id,           1433)
            self.assertEqual(group_milestone_history.milestone,    GroupMilestoneURI(uri="/api/v1/group/groupmilestone/2114/"))
            self.assertEqual(group_milestone_history.order,        None)
            self.assertEqual(group_milestone_history.resolved,     "Done")
            self.assertEqual(group_milestone_history.resource_uri, GroupMilestoneHistoryURI(uri="/api/v1/group/groupmilestonehistory/1433/"))
            self.assertEqual(group_milestone_history.state,        GroupMilestoneStateNameURI(uri="/api/v1/name/groupmilestonestatename/active/"))
            self.assertEqual(group_milestone_history.time,         datetime.fromisoformat("2013-05-20T15:42:45-07:00"))
        else:
            self.fail("Cannot find group milestone history")


    def test_group_milestone_histories(self) -> None:
        group_milestone_histories = self.dt.group_milestone_histories()
        self.assertIsNot(group_milestone_histories, None)


    def test_group_milestone_histories_group(self) -> None:
        group_milestone_histories = list(self.dt.group_milestone_histories(group=self.dt.group(GroupURI(uri="/api/v1/group/group/1326/"))))
        self.assertEqual(len(group_milestone_histories), 40)


    def test_group_milestone_histories_milestone(self) -> None:
        group_milestone_histories = list(self.dt.group_milestone_histories(milestone=self.dt.group_milestone(GroupMilestoneURI(uri="/api/v1/group/groupmilestone/2114/"))))
        self.assertEqual(len(group_milestone_histories),  1)
        self.assertEqual(group_milestone_histories[0].id, 1433)


    def test_group_milestone_histories_state(self) -> None:
        group_milestone_histories = self.dt.group_milestone_histories(state=self.dt.group_milestone_statename(GroupMilestoneStateNameURI(uri="/api/v1/name/groupmilestonestatename/active/")))
        self.assertIsNot(group_milestone_histories, None)


    def test_group_milestone_event(self) -> None:
        group_milestone_event = self.dt.group_milestone_event(GroupMilestoneEventURI(uri="/api/v1/group/milestonegroupevent/16849/"))
        if group_milestone_event is not None:
            self.assertEqual(group_milestone_event.by,             PersonURI(uri="/api/v1/person/person/108756/"))
            self.assertEqual(group_milestone_event.desc,           "Added milestone \"Submit data flow information model (informational)\", due 2020-04-30, from approved charter")
            self.assertEqual(group_milestone_event.group,          GroupURI(uri="/api/v1/group/group/1962/"))
            self.assertEqual(group_milestone_event.groupevent_ptr, GroupEventURI(uri="/api/v1/group/groupevent/16849/"))
            self.assertEqual(group_milestone_event.id,             16849)
            self.assertEqual(group_milestone_event.milestone,      GroupMilestoneURI(uri="/api/v1/group/groupmilestone/8539/"))
            self.assertEqual(group_milestone_event.resource_uri,   GroupMilestoneEventURI(uri="/api/v1/group/milestonegroupevent/16849/"))
            self.assertEqual(group_milestone_event.time,           datetime.fromisoformat("2020-04-20T13:31:48-07:00"))
            self.assertEqual(group_milestone_event.type,           "changed_milestone")
        else:
            self.fail("Cannot find group milestone event")


    def test_group_milestone_events(self) -> None:
        group_milestone_events = self.dt.group_milestone_events()
        self.assertIsNot(group_milestone_events, None)


    def test_group_milestone_events_by(self) -> None:
        group_milestone_events = self.dt.group_milestone_events(by=self.dt.person(PersonURI(uri="/api/v1/person/person/108756/")))
        self.assertIsNot(group_milestone_events, None)


    def test_group_milestone_events_group(self) -> None:
        group_milestone_events = list(self.dt.group_milestone_events(group=self.dt.group(GroupURI(uri="/api/v1/group/group/1326/"))))
        self.assertEqual(len(group_milestone_events), 51)


    def test_group_milestone_events_milestone(self) -> None:
        group_milestone_events = list(self.dt.group_milestone_events(milestone=self.dt.group_milestone(GroupMilestoneURI(uri="/api/v1/group/groupmilestone/6489/"))))
        self.assertEqual(len(group_milestone_events),  3)
        self.assertEqual(group_milestone_events[0].id, 7224)
        self.assertEqual(group_milestone_events[1].id, 11947)
        self.assertEqual(group_milestone_events[2].id, 16331)


    def test_group_milestone_events_type(self) -> None:
        group_milestone_events = self.dt.group_milestone_events(type="changed_milestone")
        self.assertIsNot(group_milestone_events, None)


    def test_group_role_history(self) -> None:
        group_role_history = self.dt.group_role_history(GroupRoleHistoryURI(uri="/api/v1/group/rolehistory/519/"))
        if group_role_history is not None:
            self.assertEqual(group_role_history.email,        EmailURI(uri="/api/v1/person/email/csp@csperkins.org/"))
            self.assertEqual(group_role_history.group,        GroupHistoryURI(uri="/api/v1/group/grouphistory/256/"))
            self.assertEqual(group_role_history.id,           519)
            self.assertEqual(group_role_history.name,         RoleNameURI(uri="/api/v1/name/rolename/chair/"))
            self.assertEqual(group_role_history.person,       PersonURI(uri="/api/v1/person/person/20209/"))
            self.assertEqual(group_role_history.resource_uri, GroupRoleHistoryURI(uri="/api/v1/group/rolehistory/519/"))
        else:
            self.fail("Cannot find group role history")


    def test_group_role_histories(self) -> None:
        group_role_histories = self.dt.group_role_histories()
        self.assertIsNot(group_role_histories, None)


    def test_group_role_histories_email(self) -> None:
        group_role_histories = list(self.dt.group_role_histories(email="csp@csperkins.org"))
        self.assertEqual(len(group_role_histories), 92)


    def test_group_role_histories_group(self) -> None:
        group_role_histories = list(self.dt.group_role_histories(group=self.dt.group_history(GroupHistoryURI(uri="/api/v1/group/grouphistory/256/"))))
        self.assertEqual(len(group_role_histories), 1)
        self.assertEqual(group_role_histories[0].id, 519)


    def test_group_role_histories_name(self) -> None:
        group_role_histories = self.dt.group_role_histories(name=self.dt.role_name(RoleNameURI(uri="/api/v1/name/rolename/chair/")))
        self.assertIsNot(group_role_histories, None)


    def test_group_role_histories_person(self) -> None:
        group_role_histories = list(self.dt.group_role_histories(person=self.dt.person(PersonURI(uri="/api/v1/person/person/20209/"))))
        self.assertEqual(len(group_role_histories), 92)


    def test_group_state_change_event(self) -> None:
        group_state_change_event = self.dt.group_state_change_event(GroupStateChangeEventURI(uri="/api/v1/group/changestategroupevent/16833/"))
        if group_state_change_event is not None:
            self.assertEqual(group_state_change_event.by,             PersonURI(uri="/api/v1/person/person/106842/"))
            self.assertEqual(group_state_change_event.desc,           "State changed to <b>Proposed</b> from Unknown")
            self.assertEqual(group_state_change_event.group,          GroupURI(uri="/api/v1/group/group/2273/"))
            self.assertEqual(group_state_change_event.groupevent_ptr, GroupEventURI(uri="/api/v1/group/groupevent/16833/"))
            self.assertEqual(group_state_change_event.id,             16833)
            self.assertEqual(group_state_change_event.resource_uri,   GroupStateChangeEventURI(uri="/api/v1/group/changestategroupevent/16833/"))
            self.assertEqual(group_state_change_event.state,          GroupStateURI(uri="/api/v1/name/groupstatename/proposed/"))
            self.assertEqual(group_state_change_event.time,           datetime.fromisoformat("2020-04-14T14:52:24-07:00"))
            self.assertEqual(group_state_change_event.type,           "changed_state")
        else:
            self.fail("Cannot find group state change event")

    def test_group_state_change_events(self) -> None:
        group_state_change_events = self.dt.group_state_change_events()


    def test_group_state_change_events_by(self) -> None:
        group_state_change_events = self.dt.group_state_change_events(by=self.dt.person(PersonURI(uri="/api/v1/person/person/108756/")))
        self.assertIsNot(group_state_change_events, None)


    def test_group_state_change_events_group(self) -> None:
        group_state_change_events = self.dt.group_state_change_events(group=self.dt.group(GroupURI(uri="/api/v1/group/group/1326/")))
        self.assertIsNot(group_state_change_events, None)


    def test_group_state_change_events_state(self) -> None:
        group_state_change_events = self.dt.group_state_change_events(state=self.dt.group_state(GroupStateURI(uri="/api/v1/name/groupstatename/proposed/")))
        self.assertIsNot(group_state_change_events, None)


    def test_groups_state(self) -> None:
        groups = list(self.dt.groups(state=self.dt.group_state(GroupStateURI(uri="/api/v1/name/groupstatename/abandon/"))))
        self.assertEqual(len(groups), 15)
        self.assertEqual(groups[ 0].id, 1949)
        self.assertEqual(groups[ 1].id, 2009)
        self.assertEqual(groups[ 2].id, 2018)
        self.assertEqual(groups[ 3].id, 2155)
        self.assertEqual(groups[ 4].id, 2190)
        self.assertEqual(groups[ 5].id, 2200)
        self.assertEqual(groups[ 6].id, 2240)    # SMART
        self.assertEqual(groups[ 7].id, 2275)    # SHMO was renamed to SHMOO while chartering
        self.assertEqual(groups[ 8].id, 2290)    # 
        self.assertEqual(groups[ 9].id, 2295)    # TERM
        self.assertEqual(groups[10].id, 2334)    # JSON Web Proofs
        self.assertEqual(groups[11].id, 2348)    # RADEXTRA
        self.assertEqual(groups[12].id, 2387)    # CONGRESS was renamed to CCWG while chartering
        self.assertEqual(groups[13].id, 2389)    # NIMBY was renamed to IVY while chartering
        self.assertEqual(groups[14].id, 2400)    # MULTIFORMATS


    def test_groups_parent(self) -> None:
        groups = list(self.dt.groups(parent=self.dt.group(GroupURI(uri="/api/v1/group/group/1/"))))
        self.assertEqual(len(groups), 3)
        self.assertEqual(groups[0].id, 2)       # IESG
        self.assertEqual(groups[1].id, 7)       # IAB
        self.assertEqual(groups[2].id, 2173)    # IANA Community Coordination Group


    def test_group_state(self) -> None:
        state = self.dt.group_state(GroupStateURI(uri="/api/v1/name/groupstatename/abandon/"))
        if state is not None:
            self.assertEqual(state.desc,         "Formation of the group (most likely a BoF or Proposed WG) was abandoned")
            self.assertEqual(state.name,         "Abandoned")
            self.assertEqual(state.order,        0)
            self.assertEqual(state.resource_uri, GroupStateURI(uri="/api/v1/name/groupstatename/abandon/"))
            self.assertEqual(state.slug,         "abandon")
            self.assertEqual(state.used,         True)
        else:
            self.fail("Cannot find group state")


    def test_group_state_from_slug(self) -> None:
        state = self.dt.group_state_from_slug("abandon")
        if state is not None:
            self.assertEqual(state.desc,         "Formation of the group (most likely a BoF or Proposed WG) was abandoned")
            self.assertEqual(state.name,         "Abandoned")
            self.assertEqual(state.order,        0)
            self.assertEqual(state.resource_uri, GroupStateURI(uri="/api/v1/name/groupstatename/abandon/"))
            self.assertEqual(state.slug,         "abandon")
            self.assertEqual(state.used,         True)
        else:
            self.fail("Cannot find group state")


    # FIXME: this needs to be updated
    def test_group_states(self) -> None:
        states = list(self.dt.group_states())
        self.assertEqual(len(states),  9)
        self.assertEqual(states[0].slug, "abandon")
        self.assertEqual(states[1].slug, "active")
        self.assertEqual(states[2].slug, "bof")
        self.assertEqual(states[3].slug, "bof-conc")
        self.assertEqual(states[4].slug, "conclude")
        self.assertEqual(states[5].slug, "dormant")
        self.assertEqual(states[6].slug, "proposed")
        self.assertEqual(states[7].slug, "replaced")
        self.assertEqual(states[8].slug, "unknown")


    def test_group_type_name(self) -> None:
        group_type_name = self.dt.group_type_name(GroupTypeNameURI(uri="/api/v1/name/grouptypename/adhoc/"))
        if group_type_name is not None:
            self.assertEqual(group_type_name.desc,         "Ad Hoc schedulable Group Type, for instance HotRfc")
            self.assertEqual(group_type_name.name,         "Ad Hoc")
            self.assertEqual(group_type_name.order,        0)
            self.assertEqual(group_type_name.resource_uri, GroupTypeNameURI(uri="/api/v1/name/grouptypename/adhoc/"))
            self.assertEqual(group_type_name.slug,         "adhoc")
            self.assertEqual(group_type_name.used,         True)
            self.assertEqual(group_type_name.verbose_name, "Ad Hoc Group Type")


    def test_group_type_name_from_slug(self) -> None:
        group_type_name = self.dt.group_type_name_from_slug("adhoc")
        if group_type_name is not None:
            self.assertEqual(group_type_name.desc,         "Ad Hoc schedulable Group Type, for instance HotRfc")
            self.assertEqual(group_type_name.name,         "Ad Hoc")
            self.assertEqual(group_type_name.order,        0)
            self.assertEqual(group_type_name.resource_uri, GroupTypeNameURI(uri="/api/v1/name/grouptypename/adhoc/"))
            self.assertEqual(group_type_name.slug,         "adhoc")
            self.assertEqual(group_type_name.used,         True)
            self.assertEqual(group_type_name.verbose_name, "Ad Hoc Group Type")


    def test_group_type_names(self) -> None:
        group_type_names = list(self.dt.group_type_names())
        self.assertEqual(len(group_type_names), 26)
        self.assertEqual(group_type_names[ 0].slug, "adhoc")
        self.assertEqual(group_type_names[ 1].slug, "adm")
        self.assertEqual(group_type_names[ 2].slug, "ag")
        self.assertEqual(group_type_names[ 3].slug, "area")
        self.assertEqual(group_type_names[ 4].slug, "dir")
        self.assertEqual(group_type_names[ 5].slug, "edappr")
        self.assertEqual(group_type_names[ 6].slug, "edwg")
        self.assertEqual(group_type_names[ 7].slug, "iab")
        self.assertEqual(group_type_names[ 8].slug, "iabasg")
        self.assertEqual(group_type_names[ 9].slug, "iabworkshop")
        self.assertEqual(group_type_names[10].slug, "iana")
        self.assertEqual(group_type_names[11].slug, "iesg")
        self.assertEqual(group_type_names[12].slug, "ietf")
        self.assertEqual(group_type_names[13].slug, "individ")
        self.assertEqual(group_type_names[14].slug, "irtf")
        self.assertEqual(group_type_names[15].slug, "ise")
        self.assertEqual(group_type_names[16].slug, "isoc")
        self.assertEqual(group_type_names[17].slug, "nomcom")
        self.assertEqual(group_type_names[18].slug, "program")
        self.assertEqual(group_type_names[19].slug, "rag")
        self.assertEqual(group_type_names[20].slug, "review")
        self.assertEqual(group_type_names[21].slug, "rfcedtyp")
        self.assertEqual(group_type_names[22].slug, "rg")
        self.assertEqual(group_type_names[23].slug, "sdo")
        self.assertEqual(group_type_names[24].slug, "team")
        self.assertEqual(group_type_names[25].slug, "wg")


    # -----------------------------------------------------------------------------------------------------------------------------
    # Tests relating to meetings:

    def test_meeting_session_assignment(self) -> None:
        assignment = self.dt.meeting_session_assignment(SessionAssignmentURI(uri="/api/v1/meeting/schedtimesessassignment/61212/"))
        if assignment is not None:
            self.assertEqual(assignment.id,           61212)
            self.assertEqual(assignment.modified,     datetime.fromisoformat("2017-10-17T12:14:33-07:00"))
            self.assertEqual(assignment.extendedfrom, None)
            self.assertEqual(assignment.timeslot,     TimeslotURI(uri="/api/v1/meeting/timeslot/9132/"))
            self.assertEqual(assignment.session,      SessionURI(uri="/api/v1/meeting/session/25907/"))
            self.assertEqual(assignment.agenda,       ScheduleURI(uri="/api/v1/meeting/schedule/787/"))
            self.assertEqual(assignment.schedule,     ScheduleURI(uri="/api/v1/meeting/schedule/787/"))
            self.assertEqual(assignment.pinned,       False)
            self.assertEqual(assignment.resource_uri, SessionAssignmentURI(uri="/api/v1/meeting/schedtimesessassignment/61212/"))
            self.assertEqual(assignment.badness,      0)
        else:
            self.fail("cannot find meeting session assignment")


    def test_meeting_session_assignments(self) -> None:
        meeting  = self.dt.meeting(MeetingURI(uri="/api/v1/meeting/meeting/365/")) # IETF 90 in Toronto
        if meeting is not None and meeting.schedule is not None:
            schedule = self.dt.meeting_schedule(meeting.schedule)
            if schedule is not None:
                assignments = list(self.dt.meeting_session_assignments(schedule))
                self.assertEqual(len(assignments), 161)
            else:
                self.fail("Cannot find schedule")
        else:
            self.fail("Cannot find meeting")


    def test_meeting_session_status(self) -> None:
        session = self.dt.meeting_session(SessionURI(uri="/api/v1/meeting/session/25907/"))
        if session is not None:
            status  = self.dt.meeting_session_status(session)
            if status is None:
                self.fail("Cannot find session status")
            self.assertEqual(status.slug, "sched")
        else:
            self.fail("Cannot find session")


    def test_meeting_session_status_name(self) -> None:
        ssn = self.dt.meeting_session_status_name(SessionStatusNameURI(uri="/api/v1/name/sessionstatusname/sched/"))
        if ssn is not None:
            self.assertEqual(ssn.order,        0)
            self.assertEqual(ssn.slug,         "sched")
            self.assertEqual(ssn.resource_uri, SessionStatusNameURI(uri="/api/v1/name/sessionstatusname/sched/"))
            self.assertEqual(ssn.used,         True)
            self.assertEqual(ssn.desc,         "")
            self.assertEqual(ssn.name,         "Scheduled")
        else:
            self.fail("Cannot find meeting session status name")


    def test_meeting_session_purpose(self) -> None:
        sp = self.dt.meeting_session_purpose(SessionPurposeURI(uri="/api/v1/name/sessionpurposename/closed_meeting/"))
        if sp is not None:
            self.assertEqual(sp.used, True)
            self.assertEqual(sp.timeslot_types, "['other', 'regular']")
            self.assertEqual(sp.order, 10)
            self.assertEqual(sp.on_agenda, False)
            self.assertEqual(sp.resource_uri, SessionPurposeURI(uri="/api/v1/name/sessionpurposename/closed_meeting/"))
            self.assertEqual(sp.name, "Closed meeting")
            self.assertEqual(sp.desc, "Closed meeting")
            self.assertEqual(sp.slug, "closed_meeting")
        else:
            self.fail("Cannot find meeting session purpose")


    def test_meeting_session_status_name_from_slug(self) -> None:
        ssn = self.dt.meeting_session_status_name_from_slug("sched")
        if ssn is not None:
            self.assertEqual(ssn.order,        0)
            self.assertEqual(ssn.slug,         "sched")
            self.assertEqual(ssn.resource_uri, SessionStatusNameURI(uri="/api/v1/name/sessionstatusname/sched/"))
            self.assertEqual(ssn.used,         True)
            self.assertEqual(ssn.desc,         "")
            self.assertEqual(ssn.name,         "Scheduled")
        else:
            self.fail("Cannot find meeting session status name")


    def test_meeting_session_status_names(self) -> None:
        status_names  = list(self.dt.meeting_session_status_names())
        self.assertEqual(len(status_names),  11)
        self.assertEqual(status_names[ 0].slug, "appr")       # Approved
        self.assertEqual(status_names[ 1].slug, "apprw")      # Waiting for Approval
        self.assertEqual(status_names[ 2].slug, "canceled")   # Cancelled
        self.assertEqual(status_names[ 3].slug, "canceledpa") # Cancelled - Pre Announcement
        self.assertEqual(status_names[ 4].slug, "deleted")    # Deleted
        self.assertEqual(status_names[ 5].slug, "disappr")    # Disapproved
        self.assertEqual(status_names[ 6].slug, "notmeet")    # Not meeting
        self.assertEqual(status_names[ 7].slug, "resched")    # Rescheduled
        self.assertEqual(status_names[ 8].slug, "sched")      # Scheduled
        self.assertEqual(status_names[ 9].slug, "scheda")     # Scheduled - Announcement to be sent
        self.assertEqual(status_names[10].slug, "schedw")     # Waiting for Scheduling


    def test_meeting_session(self) -> None:
        session = self.dt.meeting_session(SessionURI(uri="/api/v1/meeting/session/25907/"))
        if session is not None:
            self.assertEqual(session.resource_uri,        SessionURI(uri="/api/v1/meeting/session/25907/"))
            self.assertEqual(session.id,                  25907)
            self.assertEqual(session.type,                "/api/v1/name/timeslottypename/regular/")
            self.assertEqual(session.name,                "")
            self.assertEqual(session.meeting,             MeetingURI(uri="/api/v1/meeting/meeting/747/"))
            self.assertEqual(session.group,               GroupURI(uri="/api/v1/group/group/1803/"))
            self.assertEqual(session.materials,           [DocumentURI(uri="/api/v1/doc/document/agenda-100-homenet/"),
                                                           DocumentURI(uri="/api/v1/doc/document/slides-100-homenet-chair-slides/"),
                                                           DocumentURI(uri="/api/v1/doc/document/slides-100-homenet-support-for-hncp-in-ipv6-ce-routers/"),
                                                           DocumentURI(uri="/api/v1/doc/document/slides-100-homenet-homenet-security/"),
                                                           DocumentURI(uri="/api/v1/doc/document/slides-100-homenet-naming/"),
                                                           DocumentURI(uri="/api/v1/doc/document/recording-100-homenet-1/"),
                                                           DocumentURI(uri="/api/v1/doc/document/minutes-100-homenet/"),
                                                           DocumentURI(uri="/api/v1/doc/document/bluesheets-100-homenet-201711131550/"),
                                                           DocumentURI(uri="/api/v1/doc/document/recording-100-homenet-2/")])
            self.assertEqual(session.scheduled,           datetime.fromisoformat("2017-10-20T17:24:10-07:00"))
            self.assertEqual(session.requested_duration,  "1:30:00")
            self.assertEqual(session.resources,           [])
            self.assertEqual(session.agenda_note,         "")
            self.assertEqual(session.assignments,         [SessionAssignmentURI(uri="/api/v1/meeting/schedtimesessassignment/57892/"),
                                                           SessionAssignmentURI(uri="/api/v1/meeting/schedtimesessassignment/58170/"),
                                                           SessionAssignmentURI(uri="/api/v1/meeting/schedtimesessassignment/59755/"),
                                                           SessionAssignmentURI(uri="/api/v1/meeting/schedtimesessassignment/58279/"),
                                                           SessionAssignmentURI(uri="/api/v1/meeting/schedtimesessassignment/58458/"),
                                                           SessionAssignmentURI(uri="/api/v1/meeting/schedtimesessassignment/58623/"),
                                                           SessionAssignmentURI(uri="/api/v1/meeting/schedtimesessassignment/58832/"),
                                                           SessionAssignmentURI(uri="/api/v1/meeting/schedtimesessassignment/59092/"),
                                                           SessionAssignmentURI(uri="/api/v1/meeting/schedtimesessassignment/59259/"),
                                                           SessionAssignmentURI(uri="/api/v1/meeting/schedtimesessassignment/59424/"),
                                                           SessionAssignmentURI(uri="/api/v1/meeting/schedtimesessassignment/59585/"),
                                                           SessionAssignmentURI(uri="/api/v1/meeting/schedtimesessassignment/59937/"),
                                                           SessionAssignmentURI(uri="/api/v1/meeting/schedtimesessassignment/60151/"),
                                                           SessionAssignmentURI(uri="/api/v1/meeting/schedtimesessassignment/60325/"),
                                                           SessionAssignmentURI(uri="/api/v1/meeting/schedtimesessassignment/60509/"),
                                                           SessionAssignmentURI(uri="/api/v1/meeting/schedtimesessassignment/60692/"),
                                                           SessionAssignmentURI(uri="/api/v1/meeting/schedtimesessassignment/60867/"),
                                                           SessionAssignmentURI(uri="/api/v1/meeting/schedtimesessassignment/61041/"),
                                                           SessionAssignmentURI(uri="/api/v1/meeting/schedtimesessassignment/61212/"),
                                                           SessionAssignmentURI(uri="/api/v1/meeting/schedtimesessassignment/61405/"),
                                                           SessionAssignmentURI(uri="/api/v1/meeting/schedtimesessassignment/61595/"),
                                                           SessionAssignmentURI(uri="/api/v1/meeting/schedtimesessassignment/61765/"),
                                                           SessionAssignmentURI(uri="/api/v1/meeting/schedtimesessassignment/61939/"),
                                                           SessionAssignmentURI(uri="/api/v1/meeting/schedtimesessassignment/67156/")])
            self.assertEqual(session.remote_instructions, "")
            self.assertEqual(session.short,               "")
            self.assertEqual(session.attendees,           120)
            self.assertEqual(session.modified,            datetime.fromisoformat("2017-10-20T17:24:10-07:00"))
            self.assertEqual(session.comments,            "")
        else:
            self.fail("cannot find meeting session")


    def test_meeting_sessions(self) -> None:
        ietf90  = self.dt.meeting(MeetingURI(uri="/api/v1/meeting/meeting/365/")) # IETF 90 in Toronto
        tsvwg   = self.dt.group_from_acronym("tsvwg")
        if ietf90 is not None and tsvwg is not None:
            sessions = list(self.dt.meeting_sessions(meeting=ietf90, group=tsvwg))
            self.assertEqual(len(sessions), 2)
            self.assertEqual(sessions[0].id, 23197)
            self.assertEqual(sessions[1].id, 23198)
        else:
            self.fail("cannot find ietf90 or tsvwg")


    def test_meeting_timeslot(self) -> None:
        ts = self.dt.meeting_timeslot(TimeslotURI(uri="/api/v1/meeting/timeslot/12857/"))
        if ts is not None:
            self.assertEqual(ts.resource_uri,   TimeslotURI(uri="/api/v1/meeting/timeslot/12857/"))
            self.assertEqual(ts.id,             12857)
            self.assertEqual(ts.type,           "/api/v1/name/timeslottypename/regular/")
            self.assertEqual(ts.meeting,       MeetingURI(uri="/api/v1/meeting/meeting/1211/"))
            self.assertEqual(ts.sessions,      [SessionURI(uri="/api/v1/meeting/session/28208/")])
            self.assertEqual(ts.name,          "")
            self.assertEqual(ts.time,          datetime.fromisoformat("2020-08-05T06:00:00-07:00"))
            self.assertEqual(ts.duration,      "2:30:00")
            self.assertEqual(ts.location,      None)
            self.assertEqual(ts.show_location, True)
            self.assertEqual(ts.modified,      datetime.fromisoformat("2020-07-30T01:28:28-07:00"))
        else:
            self.fail("cannot find timeslot")


    def test_meeting_scheduling_event(self) -> None:
        se = self.dt.meeting_scheduling_event(SchedulingEventURI(uri="/api/v1/meeting/schedulingevent/16203/"))
        if se is not None:
            self.assertEqual(se.resource_uri, SchedulingEventURI(uri="/api/v1/meeting/schedulingevent/16203/"))
            self.assertEqual(se.id,           16203)
            self.assertEqual(se.session,      SessionURI(uri="/api/v1/meeting/session/28208/"))
            self.assertEqual(se.status,       SessionStatusNameURI(uri="/api/v1/name/sessionstatusname/sched/"))
            self.assertEqual(se.by,           PersonURI(uri="/api/v1/person/person/106460/"))
            self.assertEqual(se.time,         datetime.fromisoformat("2020-06-12T13:01:38-07:00"))
        else:
            self.fail("Cannot find scheduling event")


    def test_meeting_scheduling_events(self) -> None:
        session = self.dt.meeting_session(SessionURI(uri="/api/v1/meeting/session/28208/"))
        events  = list(self.dt.meeting_scheduling_events(session=session))
        self.assertEqual(len(events),  2)
        self.assertEqual(events[0].id, 16192)
        self.assertEqual(events[1].id, 16203)


    def test_meeting_schedule(self) -> None:
        schedule = self.dt.meeting_schedule(ScheduleURI(uri="/api/v1/meeting/schedule/209/"))
        if schedule is not None:
            self.assertEqual(schedule.id,           209)
            self.assertEqual(schedule.resource_uri, ScheduleURI(uri="/api/v1/meeting/schedule/209/"))
            self.assertEqual(schedule.meeting,      MeetingURI(uri="/api/v1/meeting/meeting/365/"))
            self.assertEqual(schedule.owner,        PersonURI(uri="/api/v1/person/person/109129/"))
            self.assertEqual(schedule.name,         "prelim-fix")
            self.assertEqual(schedule.visible,      True)
            self.assertEqual(schedule.public,       True)
            self.assertEqual(schedule.badness,      None)
        else:
            self.fail("cannot find meeting schedule")


    def test_meeting(self) -> None:
        meeting = self.dt.meeting(MeetingURI(uri="/api/v1/meeting/meeting/365/"))
        if meeting is not None:
            self.assertEqual(meeting.id,                               365)
            self.assertEqual(meeting.resource_uri,                     MeetingURI(uri="/api/v1/meeting/meeting/365/"))
            self.assertEqual(meeting.type,                             MeetingTypeURI(uri="/api/v1/name/meetingtypename/ietf/"))
            self.assertEqual(meeting.city,                             "Toronto")
            self.assertEqual(meeting.country,                          "CA")
            self.assertEqual(meeting.venue_name,                       "Fairmont Royal York Hotel")
            self.assertEqual(meeting.venue_addr,                       "100 Front Street W\r\nToronto, Ontario, Canada M5J 1E3")
            self.assertEqual(meeting.date,                             date.fromisoformat("2014-07-20"))
            self.assertEqual(meeting.days,                             6)
            self.assertEqual(meeting.time_zone,                        "America/Toronto")
            self.assertEqual(meeting.idsubmit_cutoff_day_offset_00,    20)
            self.assertEqual(meeting.idsubmit_cutoff_day_offset_01,    13)
            self.assertEqual(meeting.idsubmit_cutoff_warning_days,     "21 days, 0:00:00")
            self.assertEqual(meeting.idsubmit_cutoff_time_utc,         "23:59:59")
            self.assertEqual(meeting.submission_cutoff_day_offset,     26)
            self.assertEqual(meeting.submission_correction_day_offset, 50)
            self.assertEqual(meeting.submission_start_day_offset,      90)
            self.assertEqual(meeting.attendees,                        1237)
            self.assertEqual(meeting.session_request_lock_message,     "")
            self.assertEqual(meeting.reg_area,                         "Ballroom Foyer ")
            self.assertEqual(meeting.break_area,                       "Convention and Main Mezzanine Level Foyers")
            self.assertEqual(meeting.agenda_info_note,                 "")
            self.assertEqual(meeting.agenda_warning_note,              "")
            self.assertEqual(meeting.show_important_dates,             True)
            self.assertEqual(meeting.updated,                          datetime.fromisoformat("2023-02-10T10:42:38-08:00"))
            self.assertEqual(meeting.agenda,                           ScheduleURI(uri="/api/v1/meeting/schedule/209/"))
            self.assertEqual(meeting.schedule,                         ScheduleURI(uri="/api/v1/meeting/schedule/209/"))
            self.assertEqual(meeting.number,                           "90")
            self.assertEqual(meeting.proceedings_final,                False)
            self.assertEqual(meeting.acknowledgements,                 "")
        else:
            self.fail("Cannot find meeting")


    def test_meetings(self) -> None:
        meeting_type = self.dt.meeting_type_from_slug("ietf")
        meetings = list(self.dt.meetings(start_date="2019-01-01", end_date="2019-12-31", meeting_type=meeting_type))
        self.assertEqual(len(meetings),  3)
        self.assertEqual(meetings[0].city, "Prague")
        self.assertEqual(meetings[1].city, "Montreal")
        self.assertEqual(meetings[2].city, "Singapore")


    def test_meeting_type(self) -> None:
        meeting_type = self.dt.meeting_type(MeetingTypeURI(uri="/api/v1/name/meetingtypename/ietf/"))
        if meeting_type is not None:
            self.assertEqual(meeting_type.resource_uri, MeetingTypeURI(uri="/api/v1/name/meetingtypename/ietf/"))
            self.assertEqual(meeting_type.name,         "IETF")
            self.assertEqual(meeting_type.order,        0)
            self.assertEqual(meeting_type.slug,         "ietf")
            self.assertEqual(meeting_type.desc,         "")
            self.assertEqual(meeting_type.used,         True)
        else:
            self.fail("Cannot find meeting_type")


    def test_meeting_type_from_slug(self) -> None:
        meeting_type = self.dt.meeting_type_from_slug("ietf")
        if meeting_type is not None:
            self.assertEqual(meeting_type.resource_uri, MeetingTypeURI(uri="/api/v1/name/meetingtypename/ietf/"))
            self.assertEqual(meeting_type.name,         "IETF")
            self.assertEqual(meeting_type.order,        0)
            self.assertEqual(meeting_type.slug,         "ietf")
            self.assertEqual(meeting_type.desc,         "")
            self.assertEqual(meeting_type.used,         True)
        else:
            self.fail("Cannot find meeting_type")


    def test_meeting_types(self) -> None:
        types = list(self.dt.meeting_types())
        self.assertEqual(len(types),  2)
        self.assertEqual(types[0].slug, "ietf")
        self.assertEqual(types[1].slug, "interim")


    @patch.object(ietfdata.datatracker, 'datetime', Mock(wraps=datetime))
    def test_meeting_status_future(self) -> None:
        meeting = self.dt.meeting(MeetingURI(uri="/api/v1/meeting/meeting/365/"))
        if meeting is not None:
            ietfdata.datatracker.datetime.now.return_value = date(2014, 1, 1) # type: ignore
            self.assertEqual(meeting.status(), MeetingStatus.FUTURE)
        else:
            self.fail("Cannot find meeting")


    @patch.object(ietfdata.datatracker, 'datetime', Mock(wraps=datetime))
    def test_meeting_status_completed(self) -> None:
        meeting = self.dt.meeting(MeetingURI(uri="/api/v1/meeting/meeting/365/"))
        if meeting is not None:
            ietfdata.datatracker.datetime.now.return_value = date(2014, 12, 1) # type: ignore
            self.assertEqual(meeting.status(), MeetingStatus.COMPLETED)
        else:
            self.fail("Cannot find meeting")


    @patch.object(ietfdata.datatracker, 'datetime', Mock(wraps=datetime))
    def test_meeting_status_ongoing(self) -> None:
        meeting = self.dt.meeting(MeetingURI(uri="/api/v1/meeting/meeting/365/"))
        if meeting is not None:
            ietfdata.datatracker.datetime.now.return_value = date(2014, 7, 20) # type: ignore
            self.assertEqual(meeting.status(), MeetingStatus.ONGOING)
        else:
            self.fail("Cannot find meeting")


    # -----------------------------------------------------------------------------------------------------------------------------
    # Tests relating to related documents:

    def test_related_documents_all(self) -> None:
        source = self.dt.document(DocumentURI(uri="/api/v1/doc/document/draft-rfced-info-snpp-v3/"))
        target = self.dt.document(DocumentURI(uri="/api/v1/doc/document/draft-gwinn-paging-protocol-v3"))
        rel    = self.dt.relationship_type_from_slug("replaces")
        rdocs  = list(self.dt.related_documents(source=source, target=target, relationship_type=rel))
        self.assertEqual(len(rdocs), 1)
        self.assertEqual(rdocs[0].id, 3)
        self.assertEqual(rdocs[0].relationship, RelationshipTypeURI(uri="/api/v1/name/docrelationshipname/replaces/"))
        self.assertEqual(rdocs[0].resource_uri, RelatedDocumentURI(uri="/api/v1/doc/relateddocument/3/"))
        self.assertEqual(rdocs[0].source,       DocumentURI(uri="/api/v1/doc/document/draft-rfced-info-snpp-v3/"))
        self.assertEqual(rdocs[0].target,       DocumentURI(uri="/api/v1/doc/document/draft-gwinn-paging-protocol-v3/"))


    def test_related_documents_source_target(self) -> None:
        source = self.dt.document(DocumentURI(uri="/api/v1/doc/document/draft-rfced-info-snpp-v3/"))
        target = self.dt.document(DocumentURI(uri="/api/v1/doc/document/draft-gwinn-paging-protocol-v3"))
        rdocs  = list(self.dt.related_documents(source=source, target=target))
        self.assertEqual(len(rdocs), 1)
        self.assertEqual(rdocs[0].id, 3)
        self.assertEqual(rdocs[0].relationship, RelationshipTypeURI(uri="/api/v1/name/docrelationshipname/replaces/"))
        self.assertEqual(rdocs[0].resource_uri, RelatedDocumentURI(uri="/api/v1/doc/relateddocument/3/"))
        self.assertEqual(rdocs[0].source,       DocumentURI(uri="/api/v1/doc/document/draft-rfced-info-snpp-v3/"))
        self.assertEqual(rdocs[0].target,       DocumentURI(uri="/api/v1/doc/document/draft-gwinn-paging-protocol-v3/"))


    def test_related_documents_source_relationship(self) -> None:
        source = self.dt.document(DocumentURI(uri="/api/v1/doc/document/draft-rfced-info-snpp-v3/"))
        rdocs  = list(self.dt.related_documents(source=source, relationship_type_slug = "replaces"))
        self.assertEqual(len(rdocs), 1)
        self.assertEqual(rdocs[0].id, 3)
        self.assertEqual(rdocs[0].relationship, RelationshipTypeURI(uri="/api/v1/name/docrelationshipname/replaces/"))
        self.assertEqual(rdocs[0].resource_uri, RelatedDocumentURI(uri="/api/v1/doc/relateddocument/3/"))
        self.assertEqual(rdocs[0].source,       DocumentURI(uri="/api/v1/doc/document/draft-rfced-info-snpp-v3/"))
        self.assertEqual(rdocs[0].target,       DocumentURI(uri="/api/v1/doc/document/draft-gwinn-paging-protocol-v3/"))


    def test_related_documents_target_relationship(self) -> None:
        target = self.dt.document(DocumentURI(uri="/api/v1/doc/document/draft-gwinn-paging-protocol-v3"))
        rdocs  = list(self.dt.related_documents(target=target, relationship_type_slug = "replaces"))
        self.assertEqual(len(rdocs), 1)
        self.assertEqual(rdocs[0].id, 3)
        self.assertEqual(rdocs[0].relationship, RelationshipTypeURI(uri="/api/v1/name/docrelationshipname/replaces/"))
        self.assertEqual(rdocs[0].resource_uri, RelatedDocumentURI(uri="/api/v1/doc/relateddocument/3/"))
        self.assertEqual(rdocs[0].source,       DocumentURI(uri="/api/v1/doc/document/draft-rfced-info-snpp-v3/"))
        self.assertEqual(rdocs[0].target,       DocumentURI(uri="/api/v1/doc/document/draft-gwinn-paging-protocol-v3/"))


    def test_related_documents_target(self) -> None:
        target = self.dt.document(DocumentURI(uri="/api/v1/doc/document/draft-gwinn-paging-protocol-v3"))
        rdocs  = list(self.dt.related_documents(target=target))
        self.assertEqual(len(rdocs), 1)
        self.assertEqual(rdocs[0].id, 3)
        self.assertEqual(rdocs[0].relationship, RelationshipTypeURI(uri="/api/v1/name/docrelationshipname/replaces/"))
        self.assertEqual(rdocs[0].resource_uri, RelatedDocumentURI(uri="/api/v1/doc/relateddocument/3/"))
        self.assertEqual(rdocs[0].source,       DocumentURI(uri="/api/v1/doc/document/draft-rfced-info-snpp-v3/"))
        self.assertEqual(rdocs[0].target,       DocumentURI(uri="/api/v1/doc/document/draft-gwinn-paging-protocol-v3/"))


    def test_related_documents_source(self) -> None:
        src_doc = self.dt.document(DocumentURI(uri="/api/v1/doc/document/draft-rfced-info-snpp-v3/"))
        rdocs  = list(self.dt.related_documents(source = src_doc))
        self.assertEqual(len(rdocs), 6)
        self.assertEqual(rdocs[0].id, 3)
        self.assertEqual(rdocs[0].relationship, RelationshipTypeURI(uri="/api/v1/name/docrelationshipname/replaces/"))
        self.assertEqual(rdocs[0].resource_uri, RelatedDocumentURI(uri="/api/v1/doc/relateddocument/3/"))
        self.assertEqual(rdocs[0].source,       DocumentURI(uri="/api/v1/doc/document/draft-rfced-info-snpp-v3/"))
        self.assertEqual(rdocs[0].target,       DocumentURI(uri="/api/v1/doc/document/draft-gwinn-paging-protocol-v3/"))
        self.assertEqual(rdocs[1].id, 10230)
        self.assertEqual(rdocs[1].relationship, RelationshipTypeURI(uri="/api/v1/name/docrelationshipname/refold/"))
        self.assertEqual(rdocs[1].resource_uri, RelatedDocumentURI(uri="/api/v1/doc/relateddocument/10230/"))
        self.assertEqual(rdocs[1].source,       DocumentURI(uri="/api/v1/doc/document/draft-rfced-info-snpp-v3/"))
        self.assertEqual(rdocs[1].target,       DocumentURI(uri="/api/v1/doc/document/rfc1425/"))
        self.assertEqual(rdocs[2].id, 10231)
        self.assertEqual(rdocs[2].relationship, RelationshipTypeURI(uri="/api/v1/name/docrelationshipname/refold/"))
        self.assertEqual(rdocs[2].resource_uri, RelatedDocumentURI(uri="/api/v1/doc/relateddocument/10231/"))
        self.assertEqual(rdocs[2].source,       DocumentURI(uri="/api/v1/doc/document/draft-rfced-info-snpp-v3/"))
        self.assertEqual(rdocs[2].target,       DocumentURI(uri="/api/v1/doc/document/rfc1521/"))
        self.assertEqual(rdocs[3].id, 10233)
        self.assertEqual(rdocs[3].relationship, RelationshipTypeURI(uri="/api/v1/name/docrelationshipname/refold/"))
        self.assertEqual(rdocs[3].resource_uri, RelatedDocumentURI(uri="/api/v1/doc/relateddocument/10233/"))
        self.assertEqual(rdocs[3].source,       DocumentURI(uri="/api/v1/doc/document/draft-rfced-info-snpp-v3/"))
        self.assertEqual(rdocs[3].target,       DocumentURI(uri="/api/v1/doc/document/std10/"))
        self.assertEqual(rdocs[4].id, 10234)
        self.assertEqual(rdocs[4].relationship, RelationshipTypeURI(uri="/api/v1/name/docrelationshipname/refold/"))
        self.assertEqual(rdocs[4].resource_uri, RelatedDocumentURI(uri="/api/v1/doc/relateddocument/10234/"))
        self.assertEqual(rdocs[4].source,       DocumentURI(uri="/api/v1/doc/document/draft-rfced-info-snpp-v3/"))
        self.assertEqual(rdocs[4].target,       DocumentURI(uri="/api/v1/doc/document/rfc1486/"))
        self.assertEqual(rdocs[5].id, 1289508)
        self.assertEqual(rdocs[5].relationship, RelationshipTypeURI(uri="/api/v1/name/docrelationshipname/became_rfc/"))
        self.assertEqual(rdocs[5].resource_uri, RelatedDocumentURI(uri="/api/v1/doc/relateddocument/1289508/"))
        self.assertEqual(rdocs[5].source,       DocumentURI(uri="/api/v1/doc/document/draft-rfced-info-snpp-v3/"))
        self.assertEqual(rdocs[5].target,       DocumentURI(uri="/api/v1/doc/document/rfc1861/"))


    def test_related_documents_relationship(self) -> None:
        rel    = self.dt.relationship_type_from_slug("replaces")
        rdocs  = self.dt.related_documents(relationship_type=rel)
        self.assertIsNot(rdocs, None)


    def test_relationship_types(self) -> None:
        types = list(self.dt.relationship_types())
        self.assertEqual(len(types), 18)
        self.assertEqual(types[ 0].slug, "became_rfc")
        self.assertEqual(types[ 1].slug, "conflrev")
        self.assertEqual(types[ 2].slug, "contains")
        self.assertEqual(types[ 3].slug, "downref-approval")
        self.assertEqual(types[ 4].slug, "obs")
        self.assertEqual(types[ 5].slug, "possibly-replaces")
        self.assertEqual(types[ 6].slug, "refinfo")
        self.assertEqual(types[ 7].slug, "refnorm")
        self.assertEqual(types[ 8].slug, "refold")
        self.assertEqual(types[ 9].slug, "refunk")
        self.assertEqual(types[10].slug, "replaces")
        self.assertEqual(types[11].slug, "tobcp")
        self.assertEqual(types[12].slug, "toexp")
        self.assertEqual(types[13].slug, "tohist")
        self.assertEqual(types[14].slug, "toinf")
        self.assertEqual(types[15].slug, "tois")
        self.assertEqual(types[16].slug, "tops")
        self.assertEqual(types[17].slug, "updates")


    # -----------------------------------------------------------------------------------------------------------------------------
    # Tests relating to IPR disclosures:

    def test_ipr_disclosure_state(self) -> None:
        ipr_disclosure_state = self.dt.ipr_disclosure_state(IPRDisclosureStateURI(uri="/api/v1/name/iprdisclosurestatename/pending/"))
        if ipr_disclosure_state is not None:
            self.assertEqual(ipr_disclosure_state.resource_uri, IPRDisclosureStateURI(uri="/api/v1/name/iprdisclosurestatename/pending/"))
            self.assertEqual(ipr_disclosure_state.name,         "Pending")
            self.assertEqual(ipr_disclosure_state.used,         True)
            self.assertEqual(ipr_disclosure_state.slug,         "pending")
            self.assertEqual(ipr_disclosure_state.desc,         "")
            self.assertEqual(ipr_disclosure_state.order,        0)
        else:
            self.fail("Cannot find IPR disclosure state")


    def test_ipr_disclosure_states(self) -> None:
        states = list(self.dt.ipr_disclosure_states())
        self.assertEqual(len(states), 6)
        self.assertEqual(states[0].slug,  "parked")
        self.assertEqual(states[1].slug,  "pending")
        self.assertEqual(states[2].slug,  "posted")
        self.assertEqual(states[3].slug,  "rejected")
        self.assertEqual(states[4].slug,  "removed")
        self.assertEqual(states[5].slug,  "removed_objfalse")


    def test_ipr_disclosure_base(self) -> None:
        ipr_disclosure_base = self.dt.ipr_disclosure_base(IPRDisclosureBaseURI(uri="/api/v1/ipr/iprdisclosurebase/4169/"))
        if ipr_disclosure_base is not None:
            self.assertEqual(ipr_disclosure_base.by,                 PersonURI(uri="/api/v1/person/person/1/"))
            self.assertEqual(ipr_disclosure_base.compliant,          True)
            self.assertEqual(ipr_disclosure_base.docs,               [])
            self.assertEqual(ipr_disclosure_base.holder_legal_name,  "Patent and IP Recoveries llc as use licensee for US6370629 & US6393126")
            self.assertEqual(ipr_disclosure_base.id,                 4169)
            self.assertEqual(ipr_disclosure_base.notes,              "See update #4099 for specifics")
            self.assertEqual(ipr_disclosure_base.other_designations, "")
            self.assertEqual(ipr_disclosure_base.rel,                [IPRDisclosureBaseURI(uri="/api/v1/ipr/iprdisclosurebase/4102/")])
            self.assertEqual(ipr_disclosure_base.resource_uri,       IPRDisclosureBaseURI(uri="/api/v1/ipr/iprdisclosurebase/4169/"))
            self.assertEqual(ipr_disclosure_base.state,              IPRDisclosureStateURI(uri="/api/v1/name/iprdisclosurestatename/parked/"))
            self.assertEqual(ipr_disclosure_base.submitter_email,    "tglassey1@protonmail.com")
            self.assertEqual(ipr_disclosure_base.submitter_name,     "Todd Glassey")
            self.assertEqual(ipr_disclosure_base.time,               datetime.fromisoformat("2020-05-30T16:11:44-07:00"))
            self.assertEqual(ipr_disclosure_base.title,              "Patent and IP Recoveries llc as use licensee for US6370629 & US6393126's General License Statement")
        else:
            self.fail("Cannot find IPR disclosure base")


    def test_ipr_disclosure_bases(self) -> None:
        ipr_disclosure_bases = self.dt.ipr_disclosure_bases()
        self.assertIsNot(ipr_disclosure_bases, None)


    def test_ipr_disclosure_bases_by(self) -> None:
        ipr_disclosure_bases = self.dt.ipr_disclosure_bases(by=self.dt.person(PersonURI(uri="/api/v1/person/person/1/")))
        self.assertIsNot(ipr_disclosure_bases, None)


    def test_ipr_disclosure_bases_holder_legal_name(self) -> None:
        ipr_disclosure_bases = self.dt.ipr_disclosure_bases(holder_legal_name="Patent and IP Recoveries llc as use licensee for US6370629 & US6393126")
        self.assertIsNot(ipr_disclosure_bases, None)


    def test_ipr_disclosure_bases_state(self) -> None:
        ipr_disclosure_bases = self.dt.ipr_disclosure_bases(state=self.dt.ipr_disclosure_state(IPRDisclosureStateURI(uri="/api/v1/name/iprdisclosurestatename/pending/")))
        self.assertIsNot(ipr_disclosure_bases, None)


    def test_ipr_disclosure_bases_submitter_email(self) -> None:
        ipr_disclosure_bases = self.dt.ipr_disclosure_bases(submitter_email="tglassey1@protonmail.com")
        self.assertIsNot(ipr_disclosure_bases, None)


    def test_ipr_disclosure_bases_submitter_name(self) -> None:
        ipr_disclosure_bases = self.dt.ipr_disclosure_bases(submitter_name="Todd Glassey")
        self.assertIsNot(ipr_disclosure_bases, None)


    def test_generic_ipr_disclosure(self) -> None:
        generic_ipr_disclosure = self.dt.generic_ipr_disclosure(GenericIPRDisclosureURI(uri="/api/v1/ipr/genericiprdisclosure/4061/"))
        if generic_ipr_disclosure is not None:
            self.assertEqual(generic_ipr_disclosure.by,                    PersonURI(uri="/api/v1/person/person/1/"))
            self.assertEqual(generic_ipr_disclosure.compliant,             True)
            self.assertEqual(generic_ipr_disclosure.docs,                  [])
            self.assertEqual(generic_ipr_disclosure.holder_contact_email,  "kayew@i-dns.net")
            self.assertEqual(generic_ipr_disclosure.holder_contact_info,   "Legal Counsel\r\ni-DNS.net International, Inc.\r\n#24-02 Suntec Tower Three\r\nSingapore 038988\r\nT: (65) 2486-163\r\nF: (65) 2486-199\r\n")
            self.assertEqual(generic_ipr_disclosure.holder_contact_name,   "Ka Yew Leong")
            self.assertEqual(generic_ipr_disclosure.holder_legal_name,     "i-DNS.net International,")
            self.assertEqual(generic_ipr_disclosure.id,                    4061)
            self.assertEqual(generic_ipr_disclosure.iprdisclosurebase_ptr, IPRDisclosureBaseURI(uri="/api/v1/ipr/iprdisclosurebase/4061/"))
            self.assertEqual(generic_ipr_disclosure.notes,                 "More information can be found in i-DNS.net International Technology Position\r\nPaper at http://www.i-DNS.net/tech/techposition.html")
            self.assertEqual(generic_ipr_disclosure.other_designations,    "")
            self.assertEqual(generic_ipr_disclosure.rel,                   [IPRDisclosureBaseURI(uri="/api/v1/ipr/iprdisclosurebase/3150/")])
            self.assertEqual(generic_ipr_disclosure.resource_uri,          GenericIPRDisclosureURI(uri="/api/v1/ipr/genericiprdisclosure/4061/"))
            self.assertEqual(generic_ipr_disclosure.state,                 IPRDisclosureStateURI(uri="/api/v1/name/iprdisclosurestatename/parked/"))
            self.assertEqual(generic_ipr_disclosure.statement,             "\r\nThe Patent Holder states that its position with respect to licensing any patent claims\r\ncontained in the patent(s) or patent application(s) disclosed above that would necessarily\r\nbe infringed by implementation of the technology required by the relevant IETF\r\nspecification (\"Necessary Patent Claims\"), for the purpose of implementing such\r\nspecification, is as follows(select one licensing declaration option only):\r\n\r\n\r\n    See text box below for licensing declaration.\r\n\r\n\r\nLicensing information, comments, notes or URL for further information:\r\n\r\nIn accordance with Section 10 of RFC 2026, i-DNS.net International, Inc.\r\n  (i-DNS.net) hereby states that if i-DNS.net&#39;s contribution is incorporated\r\n  into an IETF standard and i-DNS.net has patents or patent applications over\r\n  such contribution, i-DNS.net is willing to grant a license to such patent\r\n  rights to the extent it is necessary to the implementation of the standard\r\n  and on fair, reasonable and non-discriminatory terms based on reciprocity.\r\n")
            self.assertEqual(generic_ipr_disclosure.submitter_email,       "kayew@i-dns.net")
            self.assertEqual(generic_ipr_disclosure.submitter_name,        "Ka Yew Leong")
            self.assertEqual(generic_ipr_disclosure.time,                  datetime.fromisoformat("2020-03-21T04:35:16-07:00"))
            self.assertEqual(generic_ipr_disclosure.title,                 "i-DNS.net International,'s General License Statement")
        else:
            self.fail("Cannot find generic IPR disclosure")


    def test_generic_ipr_disclosures(self) -> None:
        generic_ipr_disclosures = self.dt.generic_ipr_disclosures()
        self.assertIsNot(generic_ipr_disclosures, None)


    def test_generic_ipr_disclosures_by(self) -> None:
        generic_ipr_disclosures = self.dt.generic_ipr_disclosures(by=self.dt.person(PersonURI(uri="/api/v1/person/person/1/")))
        self.assertIsNot(generic_ipr_disclosures, None)


    def test_generic_ipr_disclosures_holder_legal_name(self) -> None:
        generic_ipr_disclosures = self.dt.generic_ipr_disclosures(holder_legal_name="i-DNS.net International,")
        self.assertIsNot(generic_ipr_disclosures, None)


    def test_generic_ipr_disclosures_holder_contact_name(self) -> None:
        generic_ipr_disclosures = self.dt.generic_ipr_disclosures(holder_contact_name="Ka Yew Leong")
        self.assertIsNot(generic_ipr_disclosures, None)


    def test_generic_ipr_disclosures_state(self) -> None:
        generic_ipr_disclosures = self.dt.generic_ipr_disclosures(state=self.dt.ipr_disclosure_state(IPRDisclosureStateURI(uri="/api/v1/name/iprdisclosurestatename/parked/")))
        self.assertIsNot(generic_ipr_disclosures, None)


    def test_generic_ipr_disclosures_submitter_email(self) -> None:
        generic_ipr_disclosures = self.dt.generic_ipr_disclosures(submitter_email="kayew@i-dns.net")
        self.assertIsNot(generic_ipr_disclosures, None)


    def test_generic_ipr_disclosures_submitter_name(self) -> None:
        generic_ipr_disclosures = self.dt.generic_ipr_disclosures(submitter_name="Ka Yew Leong")
        self.assertIsNot(generic_ipr_disclosures, None)


    def test_ipr_license_type(self) -> None:
        ipr_license_type = self.dt.ipr_license_type(IPRLicenseTypeURI(uri="/api/v1/name/iprlicensetypename/no-license/"))
        if ipr_license_type is not None:
            self.assertEqual(ipr_license_type.resource_uri, IPRLicenseTypeURI(uri="/api/v1/name/iprlicensetypename/no-license/"))
            self.assertEqual(ipr_license_type.name,         "No License")
            self.assertEqual(ipr_license_type.used,         True)
            self.assertEqual(ipr_license_type.slug,         "no-license")
            self.assertEqual(ipr_license_type.desc,         "a) No License Required for Implementers")
            self.assertEqual(ipr_license_type.order,        1)
        else:
            self.fail("Cannot find IPR license type")


    def test_ipr_license_types(self) -> None:
        types = list(self.dt.ipr_license_types())
        self.assertEqual(len(types), 7)
        self.assertEqual(types[0].slug,  "no-license")
        self.assertEqual(types[1].slug,  "none-selected")
        self.assertEqual(types[2].slug,  "provided-later")
        self.assertEqual(types[3].slug,  "reasonable")
        self.assertEqual(types[4].slug,  "royalty-free")
        self.assertEqual(types[5].slug,  "see-below")
        self.assertEqual(types[6].slug,  "unwilling-to-commit")


    def test_holder_ipr_disclosure(self) -> None:
        holder_ipr_disclosure = self.dt.holder_ipr_disclosure(HolderIPRDisclosureURI(uri="/api/v1/ipr/holderiprdisclosure/4176/"))
        if holder_ipr_disclosure is not None:
            self.assertEqual(holder_ipr_disclosure.by,                                   PersonURI(uri="/api/v1/person/person/1/"))
            self.assertEqual(holder_ipr_disclosure.compliant,                            True)
            self.assertEqual(holder_ipr_disclosure.docs,                                 [DocumentURI(uri="/api/v1/doc/document/draft-gandhi-spring-twamp-srpm/")])
            self.assertEqual(holder_ipr_disclosure.has_patent_pending,                   False)
            self.assertEqual(holder_ipr_disclosure.holder_contact_email,                 "francesco.battipede@telecomitalia.it")
            self.assertEqual(holder_ipr_disclosure.holder_contact_info,                  "Technology Innovation-Patents\r\nVia G. Reiss Romoli 274\r\n10148 Torino - Italy\r\nT: +39 011 228 5580")
            self.assertEqual(holder_ipr_disclosure.holder_contact_name,                  "Francesco Battipede")
            self.assertEqual(holder_ipr_disclosure.holder_legal_name,                    "Telecom Italia SpA")
            self.assertEqual(holder_ipr_disclosure.id,                                   4176)
            self.assertEqual(holder_ipr_disclosure.ietfer_contact_email,                 "mauro.cociglio@telecomitalia.it")
            self.assertEqual(holder_ipr_disclosure.ietfer_contact_info,                  "Technology Innovation\r\nVia G. Reiss Romoli 274\r\n10148 Torino - Italy\r\nT: +39 011 228 5028")
            self.assertEqual(holder_ipr_disclosure.ietfer_name,                          "Mauro Cociglio")
            self.assertEqual(holder_ipr_disclosure.iprdisclosurebase_ptr,                IPRDisclosureBaseURI(uri="/api/v1/ipr/iprdisclosurebase/4176/"))
            self.assertEqual(holder_ipr_disclosure.licensing,                            IPRLicenseTypeURI(uri="/api/v1/name/iprlicensetypename/reasonable/"))
            self.assertEqual(holder_ipr_disclosure.licensing_comments,                   "This undertaking is made subject to the condition that those who seek licences agree to reciprocate.")
            self.assertEqual(holder_ipr_disclosure.notes,                                "")
            self.assertEqual(holder_ipr_disclosure.other_designations,                   "")
            self.assertEqual(holder_ipr_disclosure.patent_info,                          "Number: AR074847B1, CN2008801327719, EP2374241B, KR101475347, US8451734\nInventor: Mauro Cociglio, Luca Maria Castaldelli, Domenico Laforgia\nTitle: Measurement of data loss in a communication network\nDate: 2008-12-22\nNotes: EP2374241B: validated in DE, FI, FR, GB, IT, NL, SE")
            self.assertEqual(holder_ipr_disclosure.rel,                                  [])
            self.assertEqual(holder_ipr_disclosure.resource_uri,                         HolderIPRDisclosureURI(uri="/api/v1/ipr/holderiprdisclosure/4176/"))
            self.assertEqual(holder_ipr_disclosure.state,                                IPRDisclosureStateURI(uri="/api/v1/name/iprdisclosurestatename/posted/"))
            self.assertEqual(holder_ipr_disclosure.submitter_claims_all_terms_disclosed, False)
            self.assertEqual(holder_ipr_disclosure.submitter_email,                      "francesco.battipede@telecomitalia.it")
            self.assertEqual(holder_ipr_disclosure.submitter_name,                       "Francesco Battipede")
            self.assertEqual(holder_ipr_disclosure.time,                                 datetime.fromisoformat("2020-06-08T02:44:12-07:00"))
            self.assertEqual(holder_ipr_disclosure.title,                                "Telecom Italia SpA's Statement about IPR related to draft-gandhi-spring-twamp-srpm")
        else:
            self.fail("Cannot find holder IPR disclosure")


    def test_holder_ipr_disclosures(self) -> None:
        holder_ipr_disclosures = self.dt.holder_ipr_disclosures()
        self.assertIsNot(holder_ipr_disclosures, None)


    def test_holder_ipr_disclosures_by(self) -> None:
        holder_ipr_disclosures = self.dt.holder_ipr_disclosures(by=self.dt.person(PersonURI(uri="/api/v1/person/person/1/")))
        self.assertIsNot(holder_ipr_disclosures, None)


    def test_holder_ipr_disclosures_holder_legal_name(self) -> None:
        holder_ipr_disclosures = self.dt.holder_ipr_disclosures(holder_legal_name="Telecom Italia SpA")
        self.assertIsNot(holder_ipr_disclosures, None)


    def test_holder_ipr_disclosures_holder_contact_name(self) -> None:
        holder_ipr_disclosures = self.dt.holder_ipr_disclosures(holder_contact_name="Francesco Battipede")
        self.assertIsNot(holder_ipr_disclosures, None)


    def test_holder_ipr_disclosures_ietfer_contact_email(self) -> None:
        holder_ipr_disclosures = self.dt.holder_ipr_disclosures(ietfer_contact_email="mauro.cociglio@telecomitalia.it")
        self.assertIsNot(holder_ipr_disclosures, None)


    def test_holder_ipr_disclosures_ietfer_name(self) -> None:
        holder_ipr_disclosures = self.dt.holder_ipr_disclosures(ietfer_name="Mauro Cociglio")
        self.assertIsNot(holder_ipr_disclosures, None)


    def test_holder_ipr_disclosures_licensing(self) -> None:
        holder_ipr_disclosures = self.dt.holder_ipr_disclosures(licensing=self.dt.ipr_license_type(IPRLicenseTypeURI(uri="/api/v1/name/iprlicensetypename/reasonable/")))
        self.assertIsNot(holder_ipr_disclosures, None)


    def test_holder_ipr_disclosures_state(self) -> None:
        holder_ipr_disclosures = self.dt.holder_ipr_disclosures(state=self.dt.ipr_disclosure_state(IPRDisclosureStateURI(uri="/api/v1/name/iprdisclosurestatename/posted/")))
        self.assertIsNot(holder_ipr_disclosures, None)


    def test_holder_ipr_disclosures_submitter_email(self) -> None:
        holder_ipr_disclosures = self.dt.holder_ipr_disclosures(submitter_email="francesco.battipede@telecomitalia.it")
        self.assertIsNot(holder_ipr_disclosures, None)


    def test_holder_ipr_disclosures_submitter_name(self) -> None:
        holder_ipr_disclosures = self.dt.holder_ipr_disclosures(submitter_name="Francesco Battipede")
        self.assertIsNot(holder_ipr_disclosures, None)


    def test_thirdparty_ipr_disclosure(self) -> None:
        thirdparty_ipr_disclosure = self.dt.thirdparty_ipr_disclosure(ThirdPartyIPRDisclosureURI(uri="/api/v1/ipr/thirdpartyiprdisclosure/4153/"))
        if thirdparty_ipr_disclosure is not None:
            self.assertEqual(thirdparty_ipr_disclosure.by,                                   PersonURI(uri="/api/v1/person/person/1/"))
            self.assertEqual(thirdparty_ipr_disclosure.compliant,                            True)
            self.assertEqual(thirdparty_ipr_disclosure.docs,                                 [DocumentURI(uri="/api/v1/doc/document/draft-mattsson-cfrg-det-sigs-with-noise/")])
            self.assertEqual(thirdparty_ipr_disclosure.has_patent_pending,                   False)
            self.assertEqual(thirdparty_ipr_disclosure.holder_legal_name,                    "QUALCOMM Incorporated")
            self.assertEqual(thirdparty_ipr_disclosure.id,                                   4153)
            self.assertEqual(thirdparty_ipr_disclosure.ietfer_contact_email,                 "bbrumley@gmail.com")
            self.assertEqual(thirdparty_ipr_disclosure.ietfer_contact_info,                  "")
            self.assertEqual(thirdparty_ipr_disclosure.ietfer_name,                          "Billy Brumley")
            self.assertEqual(thirdparty_ipr_disclosure.iprdisclosurebase_ptr,                IPRDisclosureBaseURI(uri="/api/v1/ipr/iprdisclosurebase/4153/"))
            self.assertEqual(thirdparty_ipr_disclosure.notes,                                "")
            self.assertEqual(thirdparty_ipr_disclosure.other_designations,                   "")
            self.assertEqual(thirdparty_ipr_disclosure.patent_info,                          "Number: US9621525B2\nInventor: Billy Bob Brumley\nTitle: Semi-deterministic digital signature generation\nDate: 2014-06-02")
            self.assertEqual(thirdparty_ipr_disclosure.rel,                                  [])
            self.assertEqual(thirdparty_ipr_disclosure.resource_uri,                         ThirdPartyIPRDisclosureURI(uri="/api/v1/ipr/thirdpartyiprdisclosure/4153/"))
            self.assertEqual(thirdparty_ipr_disclosure.state,                                IPRDisclosureStateURI(uri="/api/v1/name/iprdisclosurestatename/parked/"))
            self.assertEqual(thirdparty_ipr_disclosure.submitter_email,                      "bbrumley@gmail.com")
            self.assertEqual(thirdparty_ipr_disclosure.submitter_name,                       "Billy Brumley")
            self.assertEqual(thirdparty_ipr_disclosure.time,                                 datetime.fromisoformat("2020-05-14T20:32:24-07:00"))
            self.assertEqual(thirdparty_ipr_disclosure.title,                                "Billy Brumley's Statement about IPR related to draft-mattsson-cfrg-det-sigs-with-noise belonging to QUALCOMM Incorporated")
        else:
            self.fail("Cannot find third party IPR disclosure")


    def test_thirdparty_ipr_disclosures(self) -> None:
        thirdparty_ipr_disclosures = self.dt.thirdparty_ipr_disclosures()
        self.assertIsNot(thirdparty_ipr_disclosures, None)


    def test_thirdparty_ipr_disclosures_by(self) -> None:
        thirdparty_ipr_disclosures = self.dt.thirdparty_ipr_disclosures(by=self.dt.person(PersonURI(uri="/api/v1/person/person/1/")))
        self.assertIsNot(thirdparty_ipr_disclosures, None)


    def test_thirdparty_ipr_disclosures_holder_legal_name(self) -> None:
        thirdparty_ipr_disclosures = self.dt.thirdparty_ipr_disclosures(holder_legal_name="QUALCOMM Incorporated")
        self.assertIsNot(thirdparty_ipr_disclosures, None)


    def test_thirdparty_ipr_disclosures_ietfer_contact_email(self) -> None:
        thirdparty_ipr_disclosures = self.dt.thirdparty_ipr_disclosures(ietfer_contact_email="bbrumley@gmail.com")
        self.assertIsNot(thirdparty_ipr_disclosures, None)


    def test_thirdparty_ipr_disclosures_ietfer_name(self) -> None:
        thirdparty_ipr_disclosures = self.dt.thirdparty_ipr_disclosures(ietfer_name="Billy Brumley")
        self.assertIsNot(thirdparty_ipr_disclosures, None)


    def test_thirdparty_ipr_disclosures_state(self) -> None:
        thirdparty_ipr_disclosures = self.dt.thirdparty_ipr_disclosures(state=self.dt.ipr_disclosure_state(IPRDisclosureStateURI(uri="/api/v1/name/iprdisclosurestatename/pending/")))
        self.assertIsNot(thirdparty_ipr_disclosures, None)


    def test_thirdparty_ipr_disclosures_submitter_email(self) -> None:
        thirdparty_ipr_disclosures = self.dt.thirdparty_ipr_disclosures(submitter_email="bbrumley@gmail.com")
        self.assertIsNot(thirdparty_ipr_disclosures, None)


    def test_thirdparty_ipr_disclosures_submitter_name(self) -> None:
        thirdparty_ipr_disclosures = self.dt.thirdparty_ipr_disclosures(submitter_name="Billy Brumley")
        self.assertIsNot(thirdparty_ipr_disclosures, None)


    # -----------------------------------------------------------------------------------------------------------------------------
    # Tests relating to reviews:

    def test_review_assignment_state(self) -> None:
        rev_assign_state = self.dt.review_assignment_state(ReviewAssignmentStateURI(uri="/api/v1/name/reviewassignmentstatename/accepted/"))
        if rev_assign_state is not None:
            self.assertEqual(rev_assign_state.resource_uri, ReviewAssignmentStateURI(uri="/api/v1/name/reviewassignmentstatename/accepted/"))
            self.assertEqual(rev_assign_state.name,         "Accepted")
            self.assertEqual(rev_assign_state.used,         True)
            self.assertEqual(rev_assign_state.slug,         "accepted")
            self.assertEqual(rev_assign_state.desc,         "The reviewer has accepted the assignment")
            self.assertEqual(rev_assign_state.order,        0)
        else:
            self.fail("Cannot find review assignment state")


    def test_review_assignment_state_from_slug(self) -> None:
        rev_assign_state = self.dt.review_assignment_state_from_slug("accepted")
        if rev_assign_state is not None:
            self.assertEqual(rev_assign_state.resource_uri, ReviewAssignmentStateURI(uri="/api/v1/name/reviewassignmentstatename/accepted/"))
            self.assertEqual(rev_assign_state.name,         "Accepted")
            self.assertEqual(rev_assign_state.used,         True)
            self.assertEqual(rev_assign_state.slug,         "accepted")
            self.assertEqual(rev_assign_state.desc,         "The reviewer has accepted the assignment")
            self.assertEqual(rev_assign_state.order,        0)
        else:
            self.fail("Cannot find review assignment state")


    def test_review_assignment_states(self) -> None:
        states = list(self.dt.review_assignment_states())
        self.assertEqual(len(states), 9)
        self.assertEqual(states[0].slug, "accepted")
        self.assertEqual(states[1].slug, "assigned")
        self.assertEqual(states[2].slug, "completed")
        self.assertEqual(states[3].slug, "no-response")
        self.assertEqual(states[4].slug, "overtaken")
        self.assertEqual(states[5].slug, "part-completed")
        self.assertEqual(states[6].slug, "rejected")
        self.assertEqual(states[7].slug, "unknown")
        self.assertEqual(states[8].slug, "withdrawn")


    def test_review_result_type(self) -> None:
        review_result_type = self.dt.review_result_type(ReviewResultTypeURI(uri="/api/v1/name/reviewresultname/serious-issues/"))
        if review_result_type is not None:
            self.assertEqual(review_result_type.resource_uri, ReviewResultTypeURI(uri="/api/v1/name/reviewresultname/serious-issues/"))
            self.assertEqual(review_result_type.name,         "Serious Issues")
            self.assertEqual(review_result_type.used,         True)
            self.assertEqual(review_result_type.slug,         "serious-issues")
            self.assertEqual(review_result_type.desc,         "")
            self.assertEqual(review_result_type.order,        1)
        else:
            self.fail("Cannot find review result type")


    def test_review_result_type_from_slug(self) -> None:
        review_result_type = self.dt.review_result_type_from_slug("serious-issues")
        if review_result_type is not None:
            self.assertEqual(review_result_type.resource_uri, ReviewResultTypeURI(uri="/api/v1/name/reviewresultname/serious-issues/"))
            self.assertEqual(review_result_type.name,         "Serious Issues")
            self.assertEqual(review_result_type.used,         True)
            self.assertEqual(review_result_type.slug,         "serious-issues")
            self.assertEqual(review_result_type.desc,         "")
            self.assertEqual(review_result_type.order,        1)
        else:
            self.fail("Cannot find review result type")


    def test_review_result_types(self) -> None:
        types = list(self.dt.review_result_types())
        self.assertEqual(len(types), 9)
        self.assertEqual(types[0].slug, "almost-ready")
        self.assertEqual(types[1].slug, "issues")
        self.assertEqual(types[2].slug, "nits")
        self.assertEqual(types[3].slug, "not-ready")
        self.assertEqual(types[4].slug, "ready")
        self.assertEqual(types[5].slug, "ready-issues")
        self.assertEqual(types[6].slug, "ready-nits")
        self.assertEqual(types[7].slug, "right-track")
        self.assertEqual(types[8].slug, "serious-issues")


    def test_review_type(self) -> None:
        review_type = self.dt.review_type(ReviewTypeURI(uri="/api/v1/name/reviewtypename/early/"))
        if review_type is not None:
            self.assertEqual(review_type.resource_uri, ReviewTypeURI(uri="/api/v1/name/reviewtypename/early/"))
            self.assertEqual(review_type.name,         "Early")
            self.assertEqual(review_type.used,         True)
            self.assertEqual(review_type.slug,         "early")
            self.assertEqual(review_type.desc,         "")
            self.assertEqual(review_type.order,        1)
        else:
            self.fail("Cannot find review type")


    def test_review_type_from_slug(self) -> None:
        review_type = self.dt.review_type_from_slug("early")
        if review_type is not None:
            self.assertEqual(review_type.resource_uri, ReviewTypeURI(uri="/api/v1/name/reviewtypename/early/"))
            self.assertEqual(review_type.name,         "Early")
            self.assertEqual(review_type.used,         True)
            self.assertEqual(review_type.slug,         "early")
            self.assertEqual(review_type.desc,         "")
            self.assertEqual(review_type.order,        1)
        else:
            self.fail("Cannot find review type")


    def test_review_types(self) -> None:
        types = list(self.dt.review_types())
        self.assertEqual(len(types), 3)
        self.assertEqual(types[0].slug, "early")
        self.assertEqual(types[1].slug, "lc")
        self.assertEqual(types[2].slug, "telechat")


    def test_review_request_state(self) -> None:
        review_request_state = self.dt.review_request_state(ReviewRequestStateURI(uri="/api/v1/name/reviewrequeststatename/assigned/"))
        if review_request_state is not None:
            self.assertEqual(review_request_state.resource_uri, ReviewRequestStateURI(uri="/api/v1/name/reviewrequeststatename/assigned/"))
            self.assertEqual(review_request_state.name,         "Assigned")
            self.assertEqual(review_request_state.used,         True)
            self.assertEqual(review_request_state.slug,         "assigned")
            self.assertEqual(review_request_state.desc,         "The ReviewRequest has been assigned to at least one reviewer")
            self.assertEqual(review_request_state.order,        0)
        else:
            self.fail("Cannot find review request state")


    def test_review_request_state_from_slug(self) -> None:
        review_request_state = self.dt.review_request_state_from_slug("assigned")
        if review_request_state is not None:
            self.assertEqual(review_request_state.resource_uri, ReviewRequestStateURI(uri="/api/v1/name/reviewrequeststatename/assigned/"))
            self.assertEqual(review_request_state.name,         "Assigned")
            self.assertEqual(review_request_state.used,         True)
            self.assertEqual(review_request_state.slug,         "assigned")
            self.assertEqual(review_request_state.desc,         "The ReviewRequest has been assigned to at least one reviewer")
            self.assertEqual(review_request_state.order,        0)
        else:
            self.fail("Cannot find review request state")


    def test_review_request_states(self) -> None:
        states = list(self.dt.review_request_states())
        self.assertEqual(len(states), 12)
        self.assertEqual(states[ 0].slug, "accepted")
        self.assertEqual(states[ 1].slug, "assigned")
        self.assertEqual(states[ 2].slug, "completed")
        self.assertEqual(states[ 3].slug, "no-response")
        self.assertEqual(states[ 4].slug, "no-review-document")
        self.assertEqual(states[ 5].slug, "no-review-version")
        self.assertEqual(states[ 6].slug, "overtaken")
        self.assertEqual(states[ 7].slug, "part-completed")
        self.assertEqual(states[ 8].slug, "rejected")
        self.assertEqual(states[ 9].slug, "requested")
        self.assertEqual(states[10].slug, "unknown")
        self.assertEqual(states[11].slug, "withdrawn")


    def test_review_request(self) -> None:
        review_request = self.dt.review_request(ReviewRequestURI(uri="/api/v1/review/reviewrequest/12006/"))
        if review_request is not None:
            self.assertEqual(review_request.comment,       "")
            self.assertEqual(review_request.deadline,      "2019-05-30")
            self.assertEqual(review_request.doc,           DocumentURI(uri="/api/v1/doc/document/draft-ietf-pce-inter-area-as-applicability/"))
            self.assertEqual(review_request.id,            12006)
            self.assertEqual(review_request.requested_by,  PersonURI(uri="/api/v1/person/person/1/"))
            self.assertEqual(review_request.requested_rev, "")
            self.assertEqual(review_request.resource_uri,  ReviewRequestURI(uri="/api/v1/review/reviewrequest/12006/"))
            self.assertEqual(review_request.state,         ReviewRequestStateURI(uri="/api/v1/name/reviewrequeststatename/assigned/"))
            self.assertEqual(review_request.team,          GroupURI(uri="/api/v1/group/group/1976/"))
            self.assertEqual(review_request.time,          datetime.fromisoformat("2019-05-16T13:57:00-07:00"))
            self.assertEqual(review_request.type,          ReviewTypeURI(uri="/api/v1/name/reviewtypename/lc/"))
        else:
            self.fail("Cannot find review request")


    def test_review_requests(self) -> None:
        review_requests = self.dt.review_requests()
        self.assertIsNot(review_requests, None)


    def test_review_requests_doc(self) -> None:
        review_requests = list(self.dt.review_requests(doc=self.dt.document(DocumentURI(uri="/api/v1/doc/document/draft-davis-t-langtag-ext/"))))
        self.assertEqual(len(review_requests), 2)
        self.assertEqual(review_requests[0].id, 1)
        self.assertEqual(review_requests[1].id, 4457)


    def test_review_requests_requested_by(self) -> None:
        review_requests = self.dt.review_requests(requested_by=self.dt.person(PersonURI(uri="/api/v1/person/person/1/")))
        self.assertIsNot(review_requests, None)


    def test_review_requests_state(self) -> None:
        review_requests = self.dt.review_requests(state=self.dt.review_request_state(ReviewRequestStateURI(uri="/api/v1/name/reviewrequeststatename/assigned/")))
        self.assertIsNot(review_requests, None)


    def test_review_requests_team(self) -> None:
        review_requests = self.dt.review_requests(team=self.dt.group(GroupURI(uri="/api/v1/group/group/1261/")))
        self.assertIsNot(review_requests, None)


    def test_review_requests_type(self) -> None:
        review_requests = self.dt.review_requests(type=self.dt.review_type(ReviewTypeURI(uri="/api/v1/name/reviewtypename/telechat/")))
        self.assertIsNot(review_requests, None)


    def test_review_assignment(self) -> None:
        review_assignment = self.dt.review_assignment(ReviewAssignmentURI(uri="/api/v1/review/reviewassignment/10000/"))
        if review_assignment is not None:
            self.assertEqual(review_assignment.assigned_on,    datetime.fromisoformat("2011-01-18T22:58:05-07:00"))
            self.assertEqual(review_assignment.completed_on,   datetime.fromisoformat("2011-02-26T12:33:30-07:00"))
            self.assertEqual(review_assignment.id,             10000)
            self.assertEqual(review_assignment.mailarch_url,   "http://www.ietf.org/mail-archive/web/secdir/current/msg02466.html")
            self.assertEqual(review_assignment.resource_uri,   ReviewAssignmentURI(uri="/api/v1/review/reviewassignment/10000/"))
            self.assertEqual(review_assignment.result,         None)
            self.assertEqual(review_assignment.review,         DocumentURI(uri="/api/v1/doc/document/review-holsten-about-uri-scheme-secdir-lc-laganier-2011-02-26/"))
            self.assertEqual(review_assignment.review_request, ReviewRequestURI(uri="/api/v1/review/reviewrequest/4229/"))
            self.assertEqual(review_assignment.reviewed_rev,   "")
            self.assertEqual(review_assignment.reviewer,       EmailURI(uri="/api/v1/person/email/julien.ietf@gmail.com/"))
            self.assertEqual(review_assignment.state,          ReviewAssignmentStateURI(uri="/api/v1/name/reviewassignmentstatename/completed/"))
        else:
            self.fail("Cannot find review assignment")


    def test_review_assignments(self) -> None:
        review_assignments = self.dt.review_assignments()
        self.assertIsNot(review_assignments, None)


    def test_review_assignments_result(self) -> None:
        review_assignments = self.dt.review_assignments(result=self.dt.review_result_type(ReviewResultTypeURI(uri="/api/v1/name/reviewresultname/nits/")))
        self.assertIsNot(review_assignments, None)


    def test_review_assignments_review_request(self) -> None:
        review_assignments = list(self.dt.review_assignments(review_request=self.dt.review_request(ReviewRequestURI(uri="/api/v1/review/reviewrequest/8354/"))))
        self.assertEqual(len(review_assignments),  1)
        self.assertEqual(review_assignments[0].id, 1458)


    def test_review_assignments_reviewer(self) -> None:
        review_assignments = self.dt.review_assignments(reviewer=self.dt.email(EmailURI(uri="/api/v1/person/email/csp@csperkins.org/")))
        self.assertIsNot(review_assignments, None)


    def test_review_assignments_state(self) -> None:
        review_assignments = self.dt.review_assignments(state=self.dt.review_assignment_state(ReviewAssignmentStateURI(uri="/api/v1/name/reviewassignmentstatename/completed/")))
        self.assertIsNot(review_assignments, None)


    def test_review_wish(self) -> None:
        review_wish = self.dt.review_wish(ReviewWishURI(uri="/api/v1/review/reviewwish/63/"))
        if review_wish is not None:
            self.assertEqual(review_wish.doc,          DocumentURI(uri="/api/v1/doc/document/draft-arkko-ipv6-transition-guidelines/"))
            self.assertEqual(review_wish.id,           63)
            self.assertEqual(review_wish.person,       PersonURI(uri="/api/v1/person/person/113626/"))
            self.assertEqual(review_wish.resource_uri, ReviewWishURI(uri="/api/v1/review/reviewwish/63/"))
            self.assertEqual(review_wish.team,         GroupURI(uri="/api/v1/group/group/1976/"))
            self.assertEqual(review_wish.time,         datetime.fromisoformat("2022-09-15T11:35:19+00:00"))
        else:
            self.fail("Cannot find review wish")


    def test_review_wishes(self) -> None:
        review_wishes = self.dt.review_wishes()
        self.assertIsNot(review_wishes, None)


    def test_review_wishes_doc(self) -> None:
        review_wishes = list(self.dt.review_wishes(doc=self.dt.document(DocumentURI(uri="/api/v1/doc/document/draft-arkko-ipv6-transition-guidelines/"))))
        self.assertEqual(len(review_wishes),  1)
        self.assertEqual(review_wishes[0].id, 63)


    def test_review_wishes_person(self) -> None:
        review_wishes = list(self.dt.review_wishes(person=self.dt.person(PersonURI(uri="/api/v1/person/person/113626/"))))
        self.assertEqual(len(review_wishes),  7)
        self.assertEqual(review_wishes[0].id, 60)
        self.assertEqual(review_wishes[1].id, 61)
        self.assertEqual(review_wishes[2].id, 62)
        self.assertEqual(review_wishes[3].id, 63)
        self.assertEqual(review_wishes[4].id, 64)
        self.assertEqual(review_wishes[5].id, 65)
        self.assertEqual(review_wishes[6].id, 66)


    def test_review_wishes_team(self) -> None:
        review_wishes = list(self.dt.review_wishes(team=self.dt.group(GroupURI(uri="/api/v1/group/group/1972/")))) # GenART
        self.assertEqual(len(review_wishes),  1)
        self.assertEqual(review_wishes[0].id, 24)


    def test_reviewer_settings(self) -> None:
        reviewer_settings = self.dt.reviewer_settings(ReviewerSettingsURI(uri="/api/v1/review/reviewersettings/1/"))
        if reviewer_settings is not None:
            self.assertEqual(reviewer_settings.expertise,                   "")
            self.assertEqual(reviewer_settings.filter_re,                   "^draft-carpenter-.*$")
            self.assertEqual(reviewer_settings.id,                          1)
            self.assertEqual(reviewer_settings.min_interval,                14)
            self.assertEqual(reviewer_settings.person,                      PersonURI(uri="/api/v1/person/person/1958/"))
            self.assertEqual(reviewer_settings.remind_days_before_deadline, 3)
            self.assertEqual(reviewer_settings.remind_days_open_reviews,    None)
            self.assertEqual(reviewer_settings.request_assignment_next,     False)
            self.assertEqual(reviewer_settings.resource_uri,                ReviewerSettingsURI(uri="/api/v1/review/reviewersettings/1/"))
            self.assertEqual(reviewer_settings.skip_next,                   0)
            self.assertEqual(reviewer_settings.team,                        GroupURI(uri="/api/v1/group/group/1972/"))
        else:
            self.fail("Cannot find reviewer settings")


    def test_reviewer_settings_all(self) -> None:
        reviewer_settings = self.dt.reviewer_settings_all()
        self.assertIsNot(reviewer_settings, None)


    def test_reviewer_settings_all_person(self) -> None:
        reviewer_settings = list(self.dt.reviewer_settings_all(person=self.dt.person(PersonURI(uri="/api/v1/person/person/1958/"))))
        self.assertEqual(len(reviewer_settings),  1)
        self.assertEqual(reviewer_settings[0].id, 1)


    def test_reviewer_settings_all_team(self) -> None:
        reviewer_settings = self.dt.reviewer_settings_all(team=self.dt.group(GroupURI(uri="/api/v1/group/group/1972/")))
        self.assertIsNot(reviewer_settings, None)


    def test_historical_unavailable_period(self) -> None:
        historical_unavailable_period = self.dt.historical_unavailable_period(HistoricalUnavailablePeriodURI(uri="/api/v1/review/historicalunavailableperiod/29/"))
        if historical_unavailable_period is not None:
            self.assertEqual(historical_unavailable_period.availability,          "unavailable")
            self.assertEqual(historical_unavailable_period.end_date,              "2020-05-15")
            self.assertEqual(historical_unavailable_period.history_change_reason, "Set end date of unavailability period: Francis Dupont is unavailable in genart 2020-03-16 - 2020-05-15")
            self.assertEqual(historical_unavailable_period.history_date,          datetime.fromisoformat("2020-05-11T03:40:02-07:00"))
            self.assertEqual(historical_unavailable_period.history_id,            29)
            self.assertEqual(historical_unavailable_period.history_type,          "~")
            self.assertEqual(historical_unavailable_period.id,                    334)
            self.assertEqual(historical_unavailable_period.person,                PersonURI(uri="/api/v1/person/person/106670/"))
            self.assertEqual(historical_unavailable_period.reason,                "")
            self.assertEqual(historical_unavailable_period.resource_uri,          HistoricalUnavailablePeriodURI(uri="/api/v1/review/historicalunavailableperiod/29/"))
            self.assertEqual(historical_unavailable_period.start_date,            "2020-03-16")
            self.assertEqual(historical_unavailable_period.team,                  GroupURI(uri="/api/v1/group/group/1972/"))
        else:
            self.fail("Cannot find historical unavailable period")


    def test_historical_unavailable_periods(self) -> None:
        historical_unavailable_periods = self.dt.historical_unavailable_periods()
        self.assertIsNot(historical_unavailable_periods, None)


    def test_historical_unavailable_periods_history_type(self) -> None:
        historical_unavailable_periods = self.dt.historical_unavailable_periods(history_type="~")
        self.assertIsNot(historical_unavailable_periods, None)


    def test_historical_unavailable_periods_id(self) -> None:
        historical_unavailable_periods = list(self.dt.historical_unavailable_periods(id=328))
        self.assertEqual(len(historical_unavailable_periods),          1)
        self.assertEqual(historical_unavailable_periods[0].history_id, 14)


    def test_historical_unavailable_periods_person(self) -> None:
        historical_unavailable_periods = self.dt.historical_unavailable_periods(person=self.dt.person(PersonURI(uri="/api/v1/person/person/119822/")))
        self.assertIsNot(historical_unavailable_periods, None)


    def test_historical_unavailable_periods_team(self) -> None:
        historical_unavailable_periods = self.dt.historical_unavailable_periods(team=self.dt.group(GroupURI(uri="/api/v1/group/group/1261/")))
        self.assertIsNot(historical_unavailable_periods, None)

    def test_next_reviewer_in_team(self) -> None:
        next_reviewer_in_team = self.dt.next_reviewer_in_team(NextReviewerInTeamURI(uri="/api/v1/review/nextreviewerinteam/1/"))
        if next_reviewer_in_team is not None:
            self.assertEqual(next_reviewer_in_team.id,            1)
            self.assertEqual(next_reviewer_in_team.next_reviewer, PersonURI(uri="/api/v1/person/person/106670/"))
            self.assertEqual(next_reviewer_in_team.resource_uri,  NextReviewerInTeamURI(uri="/api/v1/review/nextreviewerinteam/1/"))
            self.assertEqual(next_reviewer_in_team.team,          GroupURI(uri="/api/v1/group/group/1972/"))
        else:
            self.fail("Cannot find next reviewer in team")


    def test_historical_review_request(self) -> None:
        historical_review_request = self.dt.historical_review_request(HistoricalReviewRequestURI(uri="/api/v1/review/historicalreviewrequest/836/"))
        if historical_review_request is not None:
            self.assertEqual(historical_review_request.comment,               "")
            self.assertEqual(historical_review_request.deadline,              "2020-06-09")
            self.assertEqual(historical_review_request.doc,                   DocumentURI(uri="/api/v1/doc/document/draft-ietf-capport-rfc7710bis/"))
            self.assertEqual(historical_review_request.history_change_reason, "Requested Telechat review by IOTDIR")
            self.assertEqual(historical_review_request.history_date,          datetime.fromisoformat("2020-05-27T07:12:46-07:00"))
            self.assertEqual(historical_review_request.history_id,            836)
            self.assertEqual(historical_review_request.history_type,          "+")
            self.assertEqual(historical_review_request.id,                    13428)
            self.assertEqual(historical_review_request.requested_by,          PersonURI(uri="/api/v1/person/person/105099/"))
            self.assertEqual(historical_review_request.requested_rev,         "")
            self.assertEqual(historical_review_request.resource_uri,          HistoricalReviewRequestURI(uri="/api/v1/review/historicalreviewrequest/836/"))
            self.assertEqual(historical_review_request.state,                 ReviewRequestStateURI(uri="/api/v1/name/reviewrequeststatename/requested/"))
            self.assertEqual(historical_review_request.team,                  GroupURI(uri="/api/v1/group/group/1975/"))
            self.assertEqual(historical_review_request.time,                  datetime.fromisoformat("2020-05-27T07:12:37-07:00"))
            self.assertEqual(historical_review_request.type,                  ReviewTypeURI(uri="/api/v1/name/reviewtypename/telechat/"))
        else:
            self.fail("Cannot find historical review request")


    def test_historical_review_requests(self) -> None:
        historical_review_requests = self.dt.historical_review_requests()
        self.assertIsNot(historical_review_requests, None)


    def test_historical_review_requests_history_type(self) -> None:
        historical_review_requests = self.dt.historical_review_requests(history_type="+")
        self.assertIsNot(historical_review_requests, None)


    def test_historical_review_requests_id(self) -> None:
        historical_review_requests = self.dt.historical_review_requests(id=13428)
        self.assertIsNot(historical_review_requests, None)


    def test_historical_review_requests_doc(self) -> None:
        historical_review_requests = self.dt.historical_review_requests(doc=self.dt.document(DocumentURI(uri="/api/v1/doc/document/draft-ietf-capport-rfc7710bis/")))
        self.assertIsNot(historical_review_requests, None)


    def test_historical_review_requests_requested_by(self) -> None:
        historical_review_requests = self.dt.historical_review_requests(requested_by=self.dt.person(PersonURI(uri="/api/v1/person/person/105099/")))
        self.assertIsNot(historical_review_requests, None)


    def test_historical_review_requests_state(self) -> None:
        historical_review_requests = self.dt.historical_review_requests(state=self.dt.review_request_state(ReviewRequestStateURI(uri="/api/v1/name/reviewrequeststatename/requested/")))
        self.assertIsNot(historical_review_requests, None)


    def test_historical_review_requests_team(self) -> None:
        historical_review_requests = self.dt.historical_review_requests(team=self.dt.group(GroupURI(uri="/api/v1/group/group/1975/")))
        self.assertIsNot(historical_review_requests, None)


    def test_historical_review_requests_type(self) -> None:
        historical_review_requests = self.dt.historical_review_requests(type=self.dt.review_type(ReviewTypeURI(uri="/api/v1/name/reviewtypename/telechat/")))
        self.assertIsNot(historical_review_requests, None)


    def test_next_reviewers_in_teams(self) -> None:
        next_reviewers_in_teams = self.dt.next_reviewers_in_teams()
        self.assertIsNot(next_reviewers_in_teams, None)


    def test_next_reviewers_in_teams_team(self) -> None:
        next_reviewers_in_teams = list(self.dt.next_reviewers_in_teams(team=self.dt.group(GroupURI(uri="/api/v1/group/group/1972/"))))
        self.assertEqual(len(next_reviewers_in_teams),  1)
        self.assertEqual(next_reviewers_in_teams[0].id, 1)

    def test_review_team_settings(self) -> None:
        review_team_settings = self.dt.review_team_settings(ReviewTeamSettingsURI(uri="/api/v1/review/reviewteamsettings/1/"))
        if review_team_settings is not None:
            self.assertEqual(review_team_settings.autosuggest,                      True)
            self.assertEqual(review_team_settings.group,                            GroupURI(uri="/api/v1/group/group/1261/"))
            self.assertEqual(review_team_settings.id,                               1)
            self.assertEqual(len(review_team_settings.notify_ad_when),              3)
            self.assertEqual(review_team_settings.notify_ad_when[0],                ReviewResultTypeURI(uri="/api/v1/name/reviewresultname/serious-issues/"))
            self.assertEqual(review_team_settings.notify_ad_when[1],                ReviewResultTypeURI(uri="/api/v1/name/reviewresultname/issues/"))
            self.assertEqual(review_team_settings.notify_ad_when[2],                ReviewResultTypeURI(uri="/api/v1/name/reviewresultname/not-ready/"))
            self.assertIs(review_team_settings.remind_days_unconfirmed_assignments, None)
            self.assertEqual(review_team_settings.resource_uri,                     ReviewTeamSettingsURI(uri="/api/v1/review/reviewteamsettings/1/"))
            self.assertEqual(len(review_team_settings.review_results),              5)
            self.assertEqual(review_team_settings.review_results[0],                ReviewResultTypeURI(uri="/api/v1/name/reviewresultname/serious-issues/"))
            self.assertEqual(review_team_settings.review_results[1],                ReviewResultTypeURI(uri="/api/v1/name/reviewresultname/issues/"))
            self.assertEqual(review_team_settings.review_results[2],                ReviewResultTypeURI(uri="/api/v1/name/reviewresultname/nits/"))
            self.assertEqual(review_team_settings.review_results[3],                ReviewResultTypeURI(uri="/api/v1/name/reviewresultname/not-ready/"))
            self.assertEqual(review_team_settings.review_results[4],                ReviewResultTypeURI(uri="/api/v1/name/reviewresultname/ready/"))
            self.assertEqual(len(review_team_settings.review_types),                3)
            self.assertEqual(review_team_settings.review_types[0],                  ReviewTypeURI(uri="/api/v1/name/reviewtypename/early/"))
            self.assertEqual(review_team_settings.review_types[1],                  ReviewTypeURI(uri="/api/v1/name/reviewtypename/lc/"))
            self.assertEqual(review_team_settings.review_types[2],                  ReviewTypeURI(uri="/api/v1/name/reviewtypename/telechat/"))
            self.assertEqual(review_team_settings.secr_mail_alias,                  "")
        else:
            self.fail("Cannot find review team settings")


    def test_review_team_settings_all(self) -> None:
        review_team_settings_all = self.dt.review_team_settings_all()
        self.assertIsNot(review_team_settings_all, None)


    def test_review_team_settings_all_group(self) -> None:
        review_team_settings_all = list(self.dt.review_team_settings_all(group=self.dt.group(GroupURI(uri="/api/v1/group/group/1261/"))))
        self.assertEqual(len(review_team_settings_all),  1)
        self.assertEqual(review_team_settings_all[0].id, 1)


    def test_unavailable_period(self) -> None:
        unavailable_period = self.dt.unavailable_period(UnavailablePeriodURI(uri="/api/v1/review/unavailableperiod/1/"))
        if unavailable_period is not None:
            self.assertEqual(unavailable_period.availability, "unavailable")
            self.assertEqual(unavailable_period.end_date,     "2016-12-01")
            self.assertEqual(unavailable_period.id,           1)
            self.assertEqual(unavailable_period.person,       PersonURI(uri="/api/v1/person/person/101208/"))
            self.assertEqual(unavailable_period.reason,       "")
            self.assertEqual(unavailable_period.resource_uri, UnavailablePeriodURI(uri="/api/v1/review/unavailableperiod/1/"))
            self.assertEqual(unavailable_period.start_date,   None)
            self.assertEqual(unavailable_period.team,         GroupURI(uri="/api/v1/group/group/1261/"))
        else:
            self.fail("Cannot find unavailable period")


    def test_unavailable_periods(self) -> None:
        unavailable_periods = self.dt.unavailable_periods()
        self.assertIsNot(unavailable_periods, None)


    def test_unavailable_periods_person(self) -> None:
        unavailable_periods = self.dt.unavailable_periods(person=self.dt.person(PersonURI(uri="/api/v1/person/person/101208/")))
        self.assertIsNot(unavailable_periods, None)


    def test_unavailable_periods_team(self) -> None:
        unavailable_periods = self.dt.unavailable_periods(team=self.dt.group(GroupURI(uri="/api/v1/group/group/1261/")))
        self.assertIsNot(unavailable_periods, None)


    def test_historical_reviewer_settings(self) -> None:
        historical_reviewer_settings = self.dt.historical_reviewer_settings(HistoricalReviewerSettingsURI(uri="/api/v1/review/historicalreviewersettings/733/"))
        if historical_reviewer_settings is not None:
            self.assertEqual(historical_reviewer_settings.expertise,                   "")
            self.assertEqual(historical_reviewer_settings.filter_re,                   "^draft-(weber).*$")
            self.assertEqual(historical_reviewer_settings.history_change_reason,       None)
            self.assertEqual(historical_reviewer_settings.history_date,                datetime.fromisoformat("2020-05-27T08:15:54-07:00"))
            self.assertEqual(historical_reviewer_settings.history_id,                  733)
            self.assertEqual(historical_reviewer_settings.history_type,                "~")
            self.assertEqual(historical_reviewer_settings.history_user,                "")
            self.assertEqual(historical_reviewer_settings.id,                          97)
            self.assertEqual(historical_reviewer_settings.min_interval,                None)
            self.assertEqual(historical_reviewer_settings.person,                      PersonURI(uri="/api/v1/person/person/110404/"))
            self.assertEqual(historical_reviewer_settings.remind_days_before_deadline, None)
            self.assertEqual(historical_reviewer_settings.remind_days_open_reviews,    None)
            self.assertEqual(historical_reviewer_settings.request_assignment_next,     False)
            self.assertEqual(historical_reviewer_settings.resource_uri,                HistoricalReviewerSettingsURI(uri="/api/v1/review/historicalreviewersettings/733/"))
            self.assertEqual(historical_reviewer_settings.skip_next,                   0)
            self.assertEqual(historical_reviewer_settings.team,                        GroupURI(uri="/api/v1/group/group/1974/"))
        else:
            self.fail("Cannot find historical reviewer settings")


    def test_historical_reviewer_settings_all(self) -> None:
        historical_reviewer_settings = self.dt.historical_reviewer_settings_all()
        self.assertIsNot(historical_reviewer_settings, None)


    def test_historical_reviewer_settings_all_id(self) -> None:
        historical_reviewer_settings = self.dt.historical_reviewer_settings_all(id=97)
        self.assertIsNot(historical_reviewer_settings, None)


    def test_historical_reviewer_settings_all_person(self) -> None:
        historical_reviewer_settings = self.dt.historical_reviewer_settings_all(person=self.dt.person(PersonURI(uri="/api/v1/person/person/110404/")))
        self.assertIsNot(historical_reviewer_settings, None)


    def test_historical_reviewer_settings_all_team(self) -> None:
        historical_reviewer_settings = self.dt.historical_reviewer_settings_all(team=self.dt.group(GroupURI(uri="/api/v1/group/group/1974/")))
        self.assertIsNot(historical_reviewer_settings, None)


    def test_historical_review_assignment(self) -> None:
        historical_review_assignment = self.dt.historical_review_assignment(HistoricalReviewAssignmentURI(uri="/api/v1/review/historicalreviewassignment/1130/"))
        if historical_review_assignment is not None:
            self.assertEqual(historical_review_assignment.assigned_on,           datetime.fromisoformat("2020-05-19T08:35:44-07:00"))
            self.assertEqual(historical_review_assignment.completed_on,          datetime.fromisoformat("2020-05-27T08:17:03-07:00"))
            self.assertEqual(historical_review_assignment.history_change_reason, "Request for Last Call review by OPSDIR Completed: Not Ready. Reviewer: Scott Bradner.")
            self.assertEqual(historical_review_assignment.history_date,          datetime.fromisoformat("2020-05-27T08:17:03-07:00"))
            self.assertEqual(historical_review_assignment.history_id,            1130)
            self.assertEqual(historical_review_assignment.history_type,          "~")
            self.assertEqual(historical_review_assignment.id,                    11544)
            self.assertEqual(historical_review_assignment.mailarch_url,          None)
            self.assertEqual(historical_review_assignment.resource_uri,          HistoricalReviewAssignmentURI(uri="/api/v1/review/historicalreviewassignment/1130/"))
            self.assertEqual(historical_review_assignment.result,                ReviewResultTypeURI(uri="/api/v1/name/reviewresultname/not-ready/"))
            self.assertEqual(historical_review_assignment.review,                DocumentURI(uri="/api/v1/doc/document/review-ietf-ospf-te-link-attr-reuse-12-opsdir-lc-bradner-2020-05-27/"))
            self.assertEqual(historical_review_assignment.review_request,        ReviewRequestURI(uri="/api/v1/review/reviewrequest/13398/"))
            self.assertEqual(historical_review_assignment.reviewed_rev,          "12")
            self.assertEqual(historical_review_assignment.reviewer,              EmailURI(uri="/api/v1/person/email/sob@sobco.com/"))
            self.assertEqual(historical_review_assignment.state,                 ReviewAssignmentStateURI(uri="/api/v1/name/reviewassignmentstatename/completed/"))
        else:
            self.fail("Cannot find historical review assignment")


    def test_historical_review_assignments(self) -> None:
        historical_review_assignments = self.dt.historical_review_assignments()
        self.assertIsNot(historical_review_assignments, None)


    def test_historical_review_assignments_id(self) -> None:
        historical_review_assignments = self.dt.historical_review_assignments(id=11544)
        self.assertIsNot(historical_review_assignments, None)


    def test_historical_review_assignments_result(self) -> None:
        historical_review_assignments = self.dt.historical_review_assignments(result=self.dt.review_result_type(ReviewResultTypeURI(uri="/api/v1/name/reviewresultname/nits/")))
        self.assertIsNot(historical_review_assignments, None)


    def test_historical_review_assignments_review_request(self) -> None:
        historical_review_assignments = list(self.dt.historical_review_assignments(review_request=self.dt.review_request(ReviewRequestURI(uri="/api/v1/review/reviewrequest/13398/"))))
        self.assertIsNot(historical_review_assignments, None)


    def test_historical_review_assignments_reviewer(self) -> None:
        historical_review_assignments = self.dt.historical_review_assignments(reviewer=self.dt.email(EmailURI(uri="/api/v1/person/email/csp@csperkins.org/")))
        self.assertIsNot(historical_review_assignments, None)


    def test_historical_review_assignments_state(self) -> None:
        historical_review_assignments = self.dt.historical_review_assignments(state=self.dt.review_assignment_state(ReviewAssignmentStateURI(uri="/api/v1/name/reviewassignmentstatename/completed/")))
        self.assertIsNot(historical_review_assignments, None)


    def test_review_secretary_settings(self) -> None:
        review_secretary_settings = self.dt.review_secretary_settings(ReviewSecretarySettingsURI(uri="/api/v1/review/reviewsecretarysettings/1/"))
        if review_secretary_settings is not None:
            self.assertEqual(review_secretary_settings.days_to_show_in_reviewer_list,      None)
            self.assertEqual(review_secretary_settings.id,                                 1)
            self.assertEqual(review_secretary_settings.max_items_to_show_in_reviewer_list, None)
            self.assertEqual(review_secretary_settings.person,                             PersonURI(uri="/api/v1/person/person/105519/"))
            self.assertEqual(review_secretary_settings.remind_days_before_deadline,        2)
            self.assertEqual(review_secretary_settings.resource_uri,                       ReviewSecretarySettingsURI(uri="/api/v1/review/reviewsecretarysettings/1/"))
            self.assertEqual(review_secretary_settings.team,                               GroupURI(uri="/api/v1/group/group/2174/"))
        else:
            self.fail("Cannot find review secretary settings")


    def test_review_secretary_settings_all(self) -> None:
        review_secretary_settings = self.dt.review_secretary_settings_all()
        self.assertIsNot(review_secretary_settings, None)


    def test_review_secretary_settings_all_person(self) -> None:
        review_secretary_settings = self.dt.review_secretary_settings_all(person=self.dt.person(PersonURI(uri="/api/v1/person/person/115026/")))
        self.assertIsNot(review_secretary_settings, None)


    def test_review_secretary_settings_all_team(self) -> None:
        review_secretary_settings = self.dt.review_secretary_settings_all(team=self.dt.group(GroupURI(uri="/api/v1/group/group/1982/")))
        self.assertIsNot(review_secretary_settings, None)

    # -----------------------------------------------------------------------------------------------------------------------------
    # Tests relating to mailing lists:


    #def test_email_list(self) -> None:
    #    ml = self.dt.email_list(EmailListURI(uri="/api/v1/mailinglists/list/461/"))
    #    if ml is not None:
    #        self.assertEqual(ml.id,           461)
    #        self.assertEqual(ml.resource_uri, EmailListURI(uri="/api/v1/mailinglists/list/461/"))
    #        self.assertEqual(ml.name,         "hackathon")
    #        self.assertEqual(ml.description,  "Discussion regarding past, present, and future IETF hackathons.")
    #        self.assertEqual(ml.advertised,   True)
    #    else:
    #        self.fail("Cannot find email list")


    #def test_email_lists(self) -> None:
    #    ml = list(self.dt.email_lists(name="ietf"))
    #    if ml is not None:
    #        self.assertEqual(len(ml), 1)
    #        self.assertEqual(ml[0].id,            262)
    #        self.assertEqual(ml[0].description,  "IETF-Discussion. This is the most general IETF mailing list, intended for discussion of technical, procedural, operational, and other topics for which no dedicated mailing lists exist.")
    #        self.assertEqual(ml[0].resource_uri, EmailListURI(uri="/api/v1/mailinglists/list/262/"))
    #        self.assertEqual(ml[0].advertised,   True)
    #        self.assertEqual(ml[0].name,         "ietf")
    #    else:
    #        self.fail("Cannot find email list")


    #def test_email_list_subscriptions(self) -> None:
    #    subs = list(self.dt.email_list_subscriptions(email_addr="colin.perkins@glasgow.ac.uk"))
    #    self.assertEqual(len(subs), 1)
    #    self.assertEqual(subs[0].id,           66700)
    #    self.assertEqual(subs[0].resource_uri, EmailListSubscriptionsURI(uri="/api/v1/mailinglists/subscribed/66700/"))
    #    self.assertEqual(subs[0].email,        "colin.perkins@glasgow.ac.uk")
    #    self.assertEqual(subs[0].lists[0],     EmailListURI(uri="/api/v1/mailinglists/list/461/"))

    #def test_email_list_subscriptions_by_list(self) -> None:
    #    subs = list(self.dt.email_list_subscriptions(email_list=self.dt.email_list(EmailListURI(uri="/api/v1/mailinglists/list/1/"))))
    #    self.assertIsNot(subs, None)

    # -----------------------------------------------------------------------------------------------------------------------------
    # Tests relating to countries and continents:

    def test_continent(self) -> None:
        continent = self.dt.continent(ContinentURI(uri="/api/v1/name/continentname/europe/"))
        if continent is not None:
            self.assertEqual(continent.used, True)
            self.assertEqual(continent.order, 0)
            self.assertEqual(continent.desc, "")
            self.assertEqual(continent.name, "Europe")
            self.assertEqual(continent.resource_uri, ContinentURI(uri="/api/v1/name/continentname/europe/"))
            self.assertEqual(continent.slug, "europe")
        else:
            self.fail("Cannot find continent")


    def test_continent_from_slug(self) -> None:
        continent = self.dt.continent_from_slug("europe")
        if continent is not None:
            self.assertEqual(continent.used, True)
            self.assertEqual(continent.order, 0)
            self.assertEqual(continent.desc, "")
            self.assertEqual(continent.name, "Europe")
            self.assertEqual(continent.resource_uri, ContinentURI(uri="/api/v1/name/continentname/europe/"))
            self.assertEqual(continent.slug, "europe")
        else:
            self.fail("Cannot find continent")


    def test_continents(self) -> None:
        continents = list(self.dt.continents())
        self.assertEqual(len(continents), 7)


    def test_country(self) -> None:
        country = self.dt.country(CountryURI(uri="/api/v1/name/countryname/DE/"))
        if country is not None:
            self.assertEqual(country.order,        0)
            self.assertEqual(country.continent,    ContinentURI(uri="/api/v1/name/continentname/europe/"))
            self.assertEqual(country.resource_uri, CountryURI(uri="/api/v1/name/countryname/DE/"))
            self.assertEqual(country.used,         True)
            self.assertEqual(country.desc,         "")
            self.assertEqual(country.name,         "Germany")
            self.assertEqual(country.in_eu,        True)
            self.assertEqual(country.slug,         "DE")
        else:
            self.fail("Cannot find country")


    def test_country_from_slug(self) -> None:
        country = self.dt.country_from_slug("DE")
        if country is not None:
            self.assertEqual(country.order,        0)
            self.assertEqual(country.continent,    ContinentURI(uri="/api/v1/name/continentname/europe/"))
            self.assertEqual(country.resource_uri, CountryURI(uri="/api/v1/name/countryname/DE/"))
            self.assertEqual(country.used,         True)
            self.assertEqual(country.desc,         "")
            self.assertEqual(country.name,         "Germany")
            self.assertEqual(country.in_eu,        True)
            self.assertEqual(country.slug,         "DE")
        else:
            self.fail("Cannot find country")


    def test_countries_continent(self) -> None:
        countries = list(self.dt.countries(continent_slug = "north-america"))
        self.assertEqual(len(countries), 41)


    def test_countries_in_eu(self) -> None:
        countries = list(self.dt.countries(in_eu = True))
        self.assertEqual(len(countries), 28)  # Bollocks to Brexit


    def test_countries_slug(self) -> None:
        countries = list(self.dt.countries(slug = "DE"))
        self.assertEqual(len(countries), 1)


    def test_countries_name(self) -> None:
        countries = list(self.dt.countries(name = "Germany"))
        self.assertEqual(len(countries), 1)


    def test_country_alias(self) -> None:
        country = self.dt.country_alias(CountryAliasURI(uri="/api/v1/stats/countryalias/292/"))
        if country is not None:
            self.assertEqual(country.country,      CountryURI(uri="/api/v1/name/countryname/BE/"))
            self.assertEqual(country.resource_uri, CountryAliasURI(uri="/api/v1/stats/countryalias/292/"))
            self.assertEqual(country.alias,        "belgique")
            self.assertEqual(country.id,           292)
        else:
            self.fail("Cannot find country alias")


    def test_country_aliases(self) -> None:
        aliases = list(self.dt.country_aliases("belgique"))
        self.assertEqual(len(aliases), 1)
        self.assertEqual(aliases[0].resource_uri, CountryAliasURI(uri="/api/v1/stats/countryalias/292/"))
        self.assertEqual(aliases[0].country,      CountryURI(uri="/api/v1/name/countryname/BE/"))
        self.assertEqual(aliases[0].alias,        "belgique")
        self.assertEqual(aliases[0].id,           292)


    # -----------------------------------------------------------------------------------------------------------------------------
    # Tests relating to statistics:

    def test_meeting_registration(self) -> None:
        reg = self.dt.meeting_registration(MeetingRegistrationURI(uri="/api/v1/stats/meetingregistration/42206/"))
        if reg is not None:
            self.assertEqual(reg.affiliation,  "University of Glasgow")
            self.assertEqual(reg.attended,     True)
            self.assertEqual(reg.country_code, "GB")
            self.assertEqual(reg.email,        "sm@smcquistin.uk")
            self.assertEqual(reg.first_name,   "Stephen")
            self.assertEqual(reg.id,           42206)
            self.assertEqual(reg.last_name,    "McQuistin")
            self.assertEqual(reg.meeting,      MeetingURI(uri="/api/v1/meeting/meeting/1003/"))
            self.assertEqual(reg.person,       PersonURI(uri="/api/v1/person/person/117769/"))
            self.assertEqual(reg.reg_type,     "remote")
            self.assertEqual(reg.resource_uri, MeetingRegistrationURI(uri="/api/v1/stats/meetingregistration/42206/"))
            self.assertEqual(reg.ticket_type,  "full_week_pass")
        else:
            self.fail("Cannot find meeting registration")


    def test_meeting_registrations(self) -> None:
        regs = self.dt.meeting_registrations()
        self.assertIsNot(regs, None)


    def test_meeting_registrations_affiliation(self) -> None:
        regs = self.dt.meeting_registrations(affiliation="University of Glasgow")
        self.assertIsNot(regs, None)


    def test_meeting_registrations_attended(self) -> None:
        regs = self.dt.meeting_registrations(attended=True)
        self.assertIsNot(regs, None)


    def test_meeting_registrations_country_code(self) -> None:
        regs = self.dt.meeting_registrations(country_code="GB")
        self.assertIsNot(regs, None)


    def test_meeting_registrations_email(self) -> None:
        regs = self.dt.meeting_registrations(email="sm@smcquistin.uk")
        self.assertIsNot(regs, None)


    def test_meeting_registrations_first_name(self) -> None:
        regs = self.dt.meeting_registrations(first_name="Stephen")
        self.assertIsNot(regs, None)


    def test_meeting_registrations_last_name(self) -> None:
        regs = self.dt.meeting_registrations(last_name="McQuistin")
        self.assertIsNot(regs, None)


    def test_meeting_registrations_meeting(self) -> None:
        regs = self.dt.meeting_registrations(meeting=self.dt.meeting(MeetingURI(uri="/api/v1/meeting/meeting/1003/")))
        self.assertIsNot(regs, None)


    def test_meeting_registrations_person(self) -> None:
        regs = self.dt.meeting_registrations(person=self.dt.person(PersonURI(uri="/api/v1/person/person/117769/")))
        self.assertIsNot(regs, None)


    def test_meeting_registrations_reg_type(self) -> None:
        regs = self.dt.meeting_registrations(reg_type="remote")
        self.assertIsNot(regs, None)


    def test_meeting_registrations_ticket_type(self) -> None:
        regs = self.dt.meeting_registrations(ticket_type="one_day")
        self.assertIsNot(regs, None)


    # -----------------------------------------------------------------------------------------------------------------------------
    # Tests relating to messages:

    def test_announcement_from(self) -> None:
        announcement_from = self.dt.announcement_from(AnnouncementFromURI(uri="/api/v1/message/announcementfrom/1/"))
        if announcement_from is not None:
            self.assertEqual(announcement_from.address,      "IETF Chair <chair@ietf.org>")
            self.assertEqual(announcement_from.group,        GroupURI(uri="/api/v1/group/group/1/"))
            self.assertEqual(announcement_from.id,           1)
            self.assertEqual(announcement_from.name,         RoleNameURI(uri="/api/v1/name/rolename/chair/"))
            self.assertEqual(announcement_from.resource_uri, AnnouncementFromURI(uri="/api/v1/message/announcementfrom/1/"))
        else:
            self.fail("Cannot find announcement from metadata")


    def test_announcements_from(self) -> None:
        announcements_from = self.dt.announcements_from()
        self.assertIsNot(announcements_from, None)


    def test_announcements_from_address(self) -> None:
        announcements_from = list(self.dt.announcements_from(address="IETF Chair <chair@ietf.org>"))
        self.assertEqual(len(announcements_from),  1)
        self.assertEqual(announcements_from[0].id, 1)


    def test_announcements_from_group(self) -> None:
        announcements_from = list(self.dt.announcements_from(group=self.dt.group(GroupURI(uri="/api/v1/group/group/1/"))))
        self.assertEqual(len(announcements_from),  6)
        self.assertEqual(announcements_from[0].id, 1)
        self.assertEqual(announcements_from[1].id, 2)
        self.assertEqual(announcements_from[2].id, 7)
        self.assertEqual(announcements_from[3].id, 8)
        self.assertEqual(announcements_from[4].id, 27)
        self.assertEqual(announcements_from[5].id, 28)


    def test_announcements_from_name(self) -> None:
        announcements_from = list(self.dt.announcements_from(name=self.dt.role_name(RoleNameURI(uri="/api/v1/name/rolename/chair/"))))
        self.assertEqual(len(announcements_from),  11)
        self.assertEqual(announcements_from[0].id, 1)
        self.assertEqual(announcements_from[1].id, 2)
        self.assertEqual(announcements_from[2].id, 3)
        self.assertEqual(announcements_from[3].id, 10)
        self.assertEqual(announcements_from[4].id, 12)
        self.assertEqual(announcements_from[5].id, 13)
        self.assertEqual(announcements_from[6].id, 15)
        self.assertEqual(announcements_from[7].id, 16)
        self.assertEqual(announcements_from[8].id, 24)
        self.assertEqual(announcements_from[9].id, 26)
        self.assertEqual(announcements_from[10].id, 30)


    #def test_message(self) -> None:
    #    message = self.dt.message(DTMessageURI(uri="/api/v1/message/message/158636/"))
    #    if message is not None:
    #        self.assertEqual(message.bcc,            "")
    #        self.assertEqual(message.body,           "\nA New Internet-Draft is available from the on-line Internet-Drafts directories.\n\n\n        Title           : Describing Protocol Data Units with Augmented Packet Header Diagrams\n        Authors         : Stephen McQuistin\n                          Vivian Band\n                          Dejice Jacob\n                          Colin Perkins\n\tFilename        : draft-mcquistin-augmented-ascii-diagrams-05.txt\n\tPages           : 26\n\tDate            : 2020-06-17\n\nAbstract:\n   This document describes a machine-readable format for specifying the\n   syntax of protocol data units within a protocol specification.  This\n   format is comprised of a consistently formatted packet header\n   diagram, followed by structured explanatory text.  It is designed to\n   maintain human readability while enabling support for automated\n   parser generation from the specification document.  This document is\n   itself an example of how the format can be used.\n\n\nThe IETF datatracker status page for this draft is:\nhttps://datatracker.ietf.org/doc/draft-mcquistin-augmented-ascii-diagrams/\n\nThere are also htmlized versions available at:\nhttps://tools.ietf.org/html/draft-mcquistin-augmented-ascii-diagrams-05\nhttps://datatracker.ietf.org/doc/html/draft-mcquistin-augmented-ascii-diagrams-05\n\nA diff from the previous version is available at:\nhttps://www.ietf.org/rfcdiff?url2=draft-mcquistin-augmented-ascii-diagrams-05\n\n\nPlease note that it may take a couple of minutes from the time of submission\nuntil the htmlized version and diff are available at tools.ietf.org.\n\nInternet-Drafts are also available by anonymous FTP at:\nftp://ftp.ietf.org/internet-drafts/\n\n")
    #        self.assertEqual(message.by,             PersonURI(uri="/api/v1/person/person/1/"))
    #        self.assertEqual(message.cc,             "")
    #        self.assertEqual(message.content_type,   "text/plain")
    #        self.assertEqual(message.frm,            "internet-drafts@ietf.org")
    #        self.assertEqual(message.id,             158636)
    #        self.assertEqual(message.msgid,          "<159239631351.30959.7146324646157253269@ietfa.amsl.com>")
    #        self.assertEqual(message.related_docs,   [DocumentURI(uri="/api/v1/doc/document/draft-mcquistin-augmented-ascii-diagrams/")])
    #        self.assertEqual(message.related_groups, [])
    #        self.assertEqual(message.reply_to, "")
    #        self.assertEqual(message.resource_uri,   DTMessageURI(uri="/api/v1/message/message/158636/"))
    #        self.assertEqual(message.sent,           datetime.fromisoformat("2020-06-17T05:18:33.607859"))
    #        self.assertEqual(message.subject,        "I-D Action: draft-mcquistin-augmented-ascii-diagrams-05.txt")
    #        self.assertEqual(message.time,           datetime.fromisoformat("2020-06-17T05:18:33"))
    #        self.assertEqual(message.to,             "i-d-announce@ietf.org")
    #    else:
    #        self.fail("Cannot find message")


    #def test_messages(self) -> None:
    #    messages = self.dt.messages()
    #    self.assertIsNot(messages, None)


    #def test_messages_by(self) -> None:
    #    person = self.dt.person(PersonURI(uri="/api/v1/person/person/1/"))
    #    if person is not None:
    #        messages = list(self.dt.messages(by=person))
    #        self.assertNotEqual(len(messages), 0)
    #    else:
    #        self.fail("Cannot find person")


    #def test_messages_frm(self) -> None:
    #    messages = list(self.dt.messages(frm="internet-drafts@ietf.org"))
    #    self.assertNotEqual(len(messages), 0)


    #def test_messages_related_doc(self) -> None:
    #    doc = self.dt.document(DocumentURI(uri="/api/v1/doc/document/draft-mcquistin-augmented-ascii-diagrams/"))
    #    if doc is not None:
    #        messages = list(self.dt.messages(related_doc=doc))
    #        self.assertNotEqual(len(messages), 0)
    #    else:
    #        self.fail("Cannot find document")


    #def test_messages_subject_contains(self) -> None:
    #    messages = list(self.dt.messages(subject_contains="I-D Action: draft-mcquistin-augmented-ascii-diagrams-05.txt"))
    #    self.assertEqual(len(messages),  1)
    #    self.assertEqual(messages[0].id, 158636)


    #def test_messages_body_contains(self) -> None:
    #    messages = list(self.dt.messages(body_contains="draft-mcquistin-augmented-ascii-diagrams-05"))
    #    self.assertNotEqual(len(messages), 0)


    def test_send_queue_entry(self) -> None:
        send_queue_entry = self.dt.send_queue_entry(SendQueueURI(uri="/api/v1/message/sendqueue/1/"))
        if send_queue_entry is not None:
            self.assertEqual(send_queue_entry.by,           PersonURI(uri="/api/v1/person/person/105651/"))
            self.assertEqual(send_queue_entry.id,           1)
            self.assertEqual(send_queue_entry.message,      DTMessageURI(uri="/api/v1/message/message/4001/"))
            self.assertEqual(send_queue_entry.note,         "")
            self.assertEqual(send_queue_entry.resource_uri, SendQueueURI(uri="/api/v1/message/sendqueue/1/"))
            self.assertEqual(send_queue_entry.send_at,      None)
            self.assertEqual(send_queue_entry.sent_at,      datetime.fromisoformat("2005-04-27T22:21:09-07:00"))
            self.assertEqual(send_queue_entry.time,         datetime.fromisoformat("2005-04-26T22:21:09-07:00"))
        else:
            self.fail("Cannot find send queue entry")


    def test_send_queue(self) -> None:
        send_queue = self.dt.send_queue()
        self.assertIsNot(send_queue, None)


    def test_send_queue_by(self) -> None:
        send_queue = self.dt.send_queue(by=self.dt.person(PersonURI(uri="/api/v1/person/person/105651/")))
        self.assertIsNot(send_queue, None)


    #def test_send_queue_message(self) -> None:
    #    message = self.dt.message(DTMessageURI(uri="/api/v1/message/message/4001/"))
    #    if message is not None:
    #        send_queue = list(self.dt.send_queue(message = message))
    #        self.assertEqual(len(send_queue),  1)
    #        self.assertEqual(send_queue[0].id, 1)
    #    else:
    #        self.fail("Cannot find message")


if __name__ == '__main__':
    unittest.main()

# =================================================================================================================================
# vim: set tw=0 ai:
