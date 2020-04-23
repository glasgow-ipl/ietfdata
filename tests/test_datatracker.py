# Copyright (C) 2017-2020 University of Glasgow
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

import unittest
import os
import sys

from pathlib       import Path
from unittest.mock import patch, Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import ietfdata
from ietfdata.datatracker import *


# =================================================================================================================================
# Unit tests:

class TestDatatracker(unittest.TestCase):
    dt : DataTracker

    # -----------------------------------------------------------------------------------------------------------------------------
    # Tests relating to email addresses:

    @classmethod
    def setUpClass(self) -> None:
        self.dt = DataTracker(cache_dir=Path("cache"))

    def test_email(self) -> None:
        e  = self.dt.email(EmailURI("/api/v1/person/email/csp@csperkins.org"))
        if e is not None:
            self.assertEqual(e.resource_uri, EmailURI("/api/v1/person/email/csp@csperkins.org/"))
            self.assertEqual(e.address,      "csp@csperkins.org")
            self.assertEqual(e.person,       PersonURI("/api/v1/person/person/20209/"))
            self.assertEqual(e.time,         datetime.fromisoformat("1970-01-01T23:59:59"))
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
            self.assertEqual(es[0].address, "csp@csperkins.org")
            self.assertEqual(es[1].address, "csp@isi.edu")
            self.assertEqual(es[2].address, "colin.perkins@glasgow.ac.uk")
            self.assertEqual(es[3].address, "csp@cperkins.net")
            self.assertEqual(es[4].address, "c.perkins@cs.ucl.ac.uk")
        else:
            self.fail("Cannot find person")


    def test_email_history_for_address(self) -> None:
        h  = list(self.dt.email_history_for_address("csp@isi.edu"))
        self.assertEqual(len(h), 2)
        self.assertEqual(h[0].resource_uri, EmailURI("/api/v1/person/historicalemail/71987/"))
        self.assertEqual(h[0].address,      "csp@isi.edu")
        self.assertEqual(h[0].person,       PersonURI("/api/v1/person/person/20209/"))
        self.assertEqual(h[0].origin,       "author: draft-ietf-avt-rtptest")
        self.assertEqual(h[0].time,         datetime.fromisoformat("2012-02-26T00:46:44"))
        self.assertEqual(h[0].active,       False)
        self.assertEqual(h[0].primary,      False)
        self.assertEqual(h[0].history_id,   71987)
        self.assertEqual(h[0].history_date, datetime.fromisoformat("2019-09-29T14:39:48.385541"))
        self.assertEqual(h[0].history_type, "~")
        self.assertEqual(h[0].history_user, "")
        self.assertEqual(h[0].history_change_reason, None)

        self.assertEqual(h[1].resource_uri, EmailURI("/api/v1/person/historicalemail/2090/"))
        self.assertEqual(h[1].address,      "csp@isi.edu")
        self.assertEqual(h[1].person,       PersonURI("/api/v1/person/person/20209/"))
        self.assertEqual(h[1].origin,       "author: draft-ietf-avt-rtptest")
        self.assertEqual(h[1].time,         datetime.fromisoformat("2012-02-26T00:46:44"))
        self.assertEqual(h[1].active,       False)
        self.assertEqual(h[1].primary,      False)
        self.assertEqual(h[1].history_id,   2090)
        self.assertEqual(h[1].history_date, datetime.fromisoformat("2018-06-19T15:39:40.008875"))
        self.assertEqual(h[1].history_type, "~")
        self.assertEqual(h[1].history_user, "")
        self.assertEqual(h[1].history_change_reason, None)


    def test_email_history_for_person(self) -> None:
        p  = self.dt.person_from_email("casner@acm.org")
        if p is not None:
            h = list(self.dt.email_history_for_person(p))
            self.assertEqual(len(h), 4)
            self.assertEqual(h[0].address, "casner@packetdesign.com")
            self.assertEqual(h[1].address, "casner@acm.org")
            self.assertEqual(h[2].address, "casner@cisco.com")
            self.assertEqual(h[3].address, "casner@precept.com")
        else:
            self.fail("Cannot find person")


    def test_emails(self) -> None:
        e = list(self.dt.emails(addr_contains="csperkins.org"))
        self.assertEqual(len(e), 1)
        self.assertEqual(e[0].resource_uri, EmailURI('/api/v1/person/email/csp@csperkins.org/'))


    # -----------------------------------------------------------------------------------------------------------------------------
    # Tests relating to people:

    def test_person_from_email(self) -> None:
        p  = self.dt.person_from_email("csp@csperkins.org")
        if p is not None:
            self.assertEqual(p.id,              20209)
            self.assertEqual(p.resource_uri,    PersonURI("/api/v1/person/person/20209/"))
            self.assertEqual(p.name,            "Colin Perkins")
            self.assertEqual(p.name_from_draft, "Colin Perkins")
            self.assertEqual(p.ascii,           "Colin Perkins")
            self.assertEqual(p.ascii_short,     "")
            self.assertEqual(p.user,            "")
            self.assertEqual(p.time,            datetime.fromisoformat("2012-02-26T00:03:54"))
            self.assertEqual(p.photo,           "https://www.ietf.org/lib/dt/media/photo/Colin-Perkins-sm.jpg")
            self.assertEqual(p.photo_thumb,     "https://www.ietf.org/lib/dt/media/photo/Colin-Perkins-sm_PMIAhXi.jpg")
            # self.assertEqual(p.biography,     "Colin Perkins is a ...")
            self.assertEqual(p.consent,         True)
        else:
            self.fail("Cannot find person")

    def test_person(self) -> None:
        p  = self.dt.person(PersonURI("/api/v1/person/person/20209/"))
        if p is not None:
            self.assertEqual(p.id,              20209)
            self.assertEqual(p.resource_uri,    PersonURI("/api/v1/person/person/20209/"))
            self.assertEqual(p.name,            "Colin Perkins")
            self.assertEqual(p.name_from_draft, "Colin Perkins")
            self.assertEqual(p.ascii,           "Colin Perkins")
            self.assertEqual(p.ascii_short,     "")
            self.assertEqual(p.user,            "")
            self.assertEqual(p.time,            datetime.fromisoformat("2012-02-26T00:03:54"))
            self.assertEqual(p.photo,           "https://www.ietf.org/lib/dt/media/photo/Colin-Perkins-sm.jpg")
            self.assertEqual(p.photo_thumb,     "https://www.ietf.org/lib/dt/media/photo/Colin-Perkins-sm_PMIAhXi.jpg")
            # self.assertEqual(p.biography,     "Colin Perkins is a ...")
            self.assertEqual(p.consent,         True)
        else:
            self.fail("Cannot find person")


    def test_person_history(self) -> None:
        p  = self.dt.person(PersonURI("/api/v1/person/person/20209/"))
        if p is not None:
            h  = list(self.dt.person_history(p))
            # As of 2019-08-18, there are two history items for csp@csperkins.org
            self.assertEqual(len(h), 3)

            self.assertEqual(h[0].id,              20209)
            self.assertEqual(h[0].resource_uri,    PersonURI("/api/v1/person/historicalperson/11731/"))
            self.assertEqual(h[0].name,            "Colin Perkins")
            self.assertEqual(h[0].name_from_draft, "Colin Perkins")
            self.assertEqual(h[0].ascii,           "Colin Perkins")
            self.assertEqual(h[0].ascii_short,     "")
            self.assertEqual(h[0].user,            "")
            self.assertEqual(h[0].time,            datetime.fromisoformat("2012-02-26T00:03:54"))
            self.assertEqual(h[0].photo,           "photo/Colin-Perkins-sm.jpg")
            self.assertEqual(h[0].photo_thumb,     "photo/Colin-Perkins-sm_PMIAhXi.jpg")
            # self.assertEqual(h[0].biography,     "Colin Perkins is a ...")
            self.assertEqual(h[0].consent,         True)
            self.assertEqual(h[0].history_change_reason, None)
            self.assertEqual(h[0].history_user,    "")
            self.assertEqual(h[0].history_id,      11731)
            self.assertEqual(h[0].history_type,    "~")
            self.assertEqual(h[0].history_date,    datetime.fromisoformat("2019-09-29T14:39:48.278674"))

            self.assertEqual(h[1].id,              20209)
            self.assertEqual(h[1].resource_uri,    PersonURI("/api/v1/person/historicalperson/10878/"))
            self.assertEqual(h[1].name,            "Colin Perkins")
            self.assertEqual(h[1].name_from_draft, "Colin Perkins")
            self.assertEqual(h[1].ascii,           "Colin Perkins")
            self.assertEqual(h[1].ascii_short,     None)
            self.assertEqual(h[1].user,            "")
            self.assertEqual(h[1].time,            datetime.fromisoformat("2012-02-26T00:03:54"))
            self.assertEqual(h[1].photo,           "photo/Colin-Perkins-sm.jpg")
            self.assertEqual(h[1].photo_thumb,     "photo/Colin-Perkins-sm_PMIAhXi.jpg")
            # self.assertEqual(h[1].biography,     "Colin Perkins is a ...")
            self.assertEqual(h[1].consent,         True)
            self.assertEqual(h[1].history_change_reason, None)
            self.assertEqual(h[1].history_user,    "")
            self.assertEqual(h[1].history_id,      10878)
            self.assertEqual(h[1].history_type,    "~")
            self.assertEqual(h[1].history_date,    datetime.fromisoformat("2019-03-29T02:44:28.426049"))

            self.assertEqual(h[2].id,              20209)
            self.assertEqual(h[2].resource_uri,    PersonURI("/api/v1/person/historicalperson/127/"))
            self.assertEqual(h[2].name,            "Colin Perkins")
            self.assertEqual(h[2].name_from_draft, "Colin Perkins")
            self.assertEqual(h[2].ascii,           "Colin Perkins")
            self.assertEqual(h[2].ascii_short,     "")
            self.assertEqual(h[2].user,            "")
            self.assertEqual(h[2].time,            datetime.fromisoformat("2012-02-26T00:03:54"))
            self.assertEqual(h[2].photo,           "")
            self.assertEqual(h[2].photo_thumb,     "")
            self.assertEqual(h[2].biography,       "")
            self.assertEqual(h[2].consent,         True)
            self.assertEqual(h[2].history_change_reason, None)
            self.assertEqual(h[2].history_user,    "")
            self.assertEqual(h[2].history_id,      127)
            self.assertEqual(h[2].history_type,    "~")
            self.assertEqual(h[2].history_date,    datetime.fromisoformat("2018-06-19T15:39:39.929158"))
        else:
            self.fail("Cannot find person")


    def test_person_aliases(self) -> None:
        p  = self.dt.person(PersonURI("/api/v1/person/person/20209/"))
        if p is not None:
            aliases  = list(self.dt.person_aliases(p))
            self.assertEqual(len(aliases), 2)
            self.assertEqual(aliases[0].id,           62)
            self.assertEqual(aliases[0].resource_uri, PersonAliasURI("/api/v1/person/alias/62/"))
            self.assertEqual(aliases[0].person,       PersonURI("/api/v1/person/person/20209/"))
            self.assertEqual(aliases[0].name,         "Dr. Colin Perkins")
            self.assertEqual(aliases[1].id,           22620)
            self.assertEqual(aliases[1].resource_uri, PersonAliasURI("/api/v1/person/alias/22620/"))
            self.assertEqual(aliases[1].person,       PersonURI("/api/v1/person/person/20209/"))
            self.assertEqual(aliases[1].name,         "Colin Perkins")
        else:
            self.fail("Cannot find person")


    def test_person_events(self) -> None:
        p = self.dt.person(PersonURI("/api/v1/person/person/3/"))
        if p is not None:
            events = list(self.dt.person_events(p))
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].desc,         "Sent GDPR notice email to [u'vint@google.com', u'vcerf@mci.net', u'vcerf@nri.reston.va.us', u'vinton.g.cerf@wcom.com'] with confirmation deadline 2018-10-22")
            self.assertEqual(events[0].id,           478)
            self.assertEqual(events[0].person,       PersonURI("/api/v1/person/person/3/"))
            self.assertEqual(events[0].resource_uri, PersonEventURI("/api/v1/person/personevent/478/"))
            self.assertEqual(events[0].time,         datetime.fromisoformat("2018-09-24T09:28:32.502465"))
            self.assertEqual(events[0].type,         "gdpr_notice_email")
        else:
            self.fail("Cannot find person")


    def test_people(self) -> None:
        p  = list(self.dt.people(name_contains="Colin Perkins"))
        self.assertEqual(len(p), 1)
        self.assertEqual(p[ 0].resource_uri, PersonURI("/api/v1/person/person/20209/"))


    # -----------------------------------------------------------------------------------------------------------------------------
    # Tests relating to documents:

    # There is one test_document_*() method for each document type

    def test_document_agenda(self) -> None:
        d  = self.dt.document(DocumentURI("/api/v1/doc/document/agenda-90-precis/"))
        if d is not None:
            self.assertEqual(d.expires,            None)
            self.assertEqual(d.order,              1)
            self.assertEqual(d.intended_std_level, None)
            self.assertEqual(d.uploaded_filename,  "agenda-90-precis.txt")
            self.assertEqual(d.states,             [DocumentStateURI("/api/v1/doc/state/81/")])
            self.assertEqual(d.abstract,           "")
            self.assertEqual(d.notify,             "")
            self.assertEqual(d.type,               DocumentTypeURI("/api/v1/name/doctypename/agenda/"))
            self.assertEqual(d.rev,                "2")
            self.assertEqual(d.internal_comments,  "")
            self.assertEqual(d.id,                 218)
            self.assertEqual(d.std_level,          None)
            self.assertEqual(d.ad,                 None)
            self.assertEqual(d.time,               datetime.fromisoformat("2014-07-21T11:14:17"))
            self.assertEqual(d.title,              "Agenda for PRECIS at IETF-90")
            self.assertEqual(d.shepherd,           None)
            self.assertEqual(d.pages,              None)
            self.assertEqual(d.tags,               [])
            self.assertEqual(d.resource_uri,       DocumentURI("/api/v1/doc/document/agenda-90-precis/"))
            self.assertEqual(d.rfc,                None)
            self.assertEqual(d.words,              None)
            self.assertEqual(d.submissions,        [])
            self.assertEqual(d.name,               "agenda-90-precis")
            self.assertEqual(d.stream,             None)
            self.assertEqual(d.group,              GroupURI("/api/v1/group/group/1798/"))
            self.assertEqual(d.note,               "")
            self.assertEqual(d.external_url,       "")

            url = d.url()
            self.assertEqual(url, "https://datatracker.ietf.org/meeting/90/materials/agenda-90-precis.txt")
            self.assertEqual(self.dt.session.get(url).status_code, 200)
        else:
            self.fail("Cannot find document")


    def test_document_bluesheets(self) -> None:
        d  = self.dt.document(DocumentURI("/api/v1/doc/document/bluesheets-95-xrblock-01/"))
        if d is not None:
            self.assertEqual(d.internal_comments,  "")
            self.assertEqual(d.id,                 68163)
            self.assertEqual(d.name,               "bluesheets-95-xrblock-01")
            self.assertEqual(d.notify,             "")
            self.assertEqual(d.order,              1)
            self.assertEqual(d.rev,                "00")
            self.assertEqual(d.external_url,       "")
            self.assertEqual(d.expires,            None)
            self.assertEqual(d.type,               DocumentTypeURI("/api/v1/name/doctypename/bluesheets/"))
            self.assertEqual(d.group,              GroupURI("/api/v1/group/group/1815/"))
            self.assertEqual(d.resource_uri,       DocumentURI("/api/v1/doc/document/bluesheets-95-xrblock-01/"))
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
            self.assertEqual(d.time,               datetime.fromisoformat("2016-08-22T05:39:08"))
            self.assertEqual(d.pages,              None)
            self.assertEqual(d.stream,             None)
            self.assertEqual(d.std_level,          None)
            self.assertEqual(d.states,             [DocumentStateURI("/api/v1/doc/state/139/")])

            url = d.url()
            self.assertEqual(url, "https://www.ietf.org/proceedings/95/bluesheets/bluesheets-95-xrblock-01.pdf")
            self.assertEqual(self.dt.session.get(url).status_code, 200)
        else:
            self.fail("Cannot find document")


    def test_document_charter(self) -> None:
        d  = self.dt.document(DocumentURI("/api/v1/doc/document/charter-ietf-vgmib/"))
        if d is not None:
            self.assertEqual(d.internal_comments,  "")
            self.assertEqual(d.id,                 1)
            self.assertEqual(d.name,               "charter-ietf-vgmib")
            self.assertEqual(d.notify,             "")
            self.assertEqual(d.order,              1)
            self.assertEqual(d.rev,                "01")
            self.assertEqual(d.external_url,       "")
            self.assertEqual(d.expires,            None)
            self.assertEqual(d.type,               DocumentTypeURI("/api/v1/name/doctypename/charter/"))
            self.assertEqual(d.group,              GroupURI("/api/v1/group/group/925/"))
            self.assertEqual(d.resource_uri,       DocumentURI("/api/v1/doc/document/charter-ietf-vgmib/"))
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
            self.assertEqual(d.time,               datetime.fromisoformat("1998-01-26T12:00:00"))
            self.assertEqual(d.pages,              None)
            self.assertEqual(d.stream,             None)
            self.assertEqual(d.std_level,          None)
            self.assertEqual(d.states,             [DocumentStateURI("/api/v1/doc/state/88/")])

            url = d.url()
            self.assertEqual(url, "https://www.ietf.org/charter/charter-ietf-vgmib-01.txt")
            self.assertEqual(self.dt.session.get(url).status_code, 200)
        else:
            self.fail("Cannot find document")


    def test_document_conflrev(self) -> None:
        d  = self.dt.document(DocumentURI("/api/v1/doc/document/conflict-review-kiyomoto-kcipher2/"))
        if d is not None:
            self.assertEqual(d.internal_comments,  "")
            self.assertEqual(d.id,                 17898)
            self.assertEqual(d.name,               "conflict-review-kiyomoto-kcipher2")
            self.assertEqual(d.notify,             "\"Nevil Brownlee\" <rfc-ise@rfc-editor.org>, draft-kiyomoto-kcipher2@tools.ietf.org")
            self.assertEqual(d.order,              1)
            self.assertEqual(d.rev,                "00")
            self.assertEqual(d.external_url,       "")
            self.assertEqual(d.expires,            None)
            self.assertEqual(d.type,               DocumentTypeURI("/api/v1/name/doctypename/conflrev/"))
            self.assertEqual(d.group,              GroupURI("/api/v1/group/group/2/"))
            self.assertEqual(d.resource_uri,       DocumentURI("/api/v1/doc/document/conflict-review-kiyomoto-kcipher2/"))
            self.assertEqual(d.title,              "IETF conflict review for draft-kiyomoto-kcipher2")
            self.assertEqual(d.abstract,           "")
            self.assertEqual(d.uploaded_filename,  "")
            self.assertEqual(d.rfc,                None)
            self.assertEqual(d.shepherd,           None)
            self.assertEqual(d.submissions,        [])
            self.assertEqual(d.intended_std_level, None)
            self.assertEqual(d.ad,                 PersonURI("/api/v1/person/person/19177/"))
            self.assertEqual(d.note,               "")
            self.assertEqual(d.words,              None)
            self.assertEqual(d.tags,               [])
            self.assertEqual(d.time,               datetime.fromisoformat("2013-07-15T14:47:31"))
            self.assertEqual(d.pages,              None)
            self.assertEqual(d.stream,             StreamURI("/api/v1/name/streamname/ietf/"))
            self.assertEqual(d.std_level,          None)
            self.assertEqual(d.states,             [DocumentStateURI("/api/v1/doc/state/97/")])

            url = d.url()
            self.assertEqual(url, "https://www.ietf.org/cr/conflict-review-kiyomoto-kcipher2-00.txt")
            self.assertEqual(self.dt.session.get(url).status_code, 200)
        else:
            self.fail("Cannot find document")


    def test_document_draft(self) -> None:
        d  = self.dt.document(DocumentURI("/api/v1/doc/document/draft-ietf-avt-rtp-new/"))
        if d is not None:
            self.assertEqual(d.internal_comments,  "")
            self.assertEqual(d.id,                 19971)
            self.assertEqual(d.name,               "draft-ietf-avt-rtp-new")
            self.assertEqual(d.notify,             "magnus.westerlund@ericsson.com, csp@csperkins.org")
            self.assertEqual(d.order,              1)
            self.assertEqual(d.rev,                "12")
            self.assertEqual(d.external_url,       "")
            self.assertEqual(d.expires,            "2003-09-08T00:00:12")
            self.assertEqual(d.type,               DocumentTypeURI("/api/v1/name/doctypename/draft/"))
            self.assertEqual(d.group,              GroupURI("/api/v1/group/group/941/"))
            self.assertEqual(d.resource_uri,       DocumentURI("/api/v1/doc/document/draft-ietf-avt-rtp-new/"))
            self.assertEqual(d.title,              "RTP: A Transport Protocol for Real-Time Applications")
            # self.assertEqual(d.abstract,         "This memorandum describes RTP, the real-time transport protocol...")
            self.assertEqual(d.uploaded_filename,  "")
            self.assertEqual(d.rfc,                3550)
            self.assertEqual(d.shepherd,           None)
            self.assertEqual(d.submissions,        [])
            self.assertEqual(d.intended_std_level, "/api/v1/name/intendedstdlevelname/std/")
            self.assertEqual(d.ad,                 PersonURI("/api/v1/person/person/2515/"))
            self.assertEqual(d.note,               "")
            self.assertEqual(d.words,              34861)
            self.assertEqual(d.tags,               ["/api/v1/name/doctagname/app-min/", "/api/v1/name/doctagname/errata/"])
            self.assertEqual(d.time,               datetime.fromisoformat("2015-10-14T13:49:52"))
            self.assertEqual(d.pages,              104)
            self.assertEqual(d.stream,             StreamURI("/api/v1/name/streamname/ietf/"))
            self.assertEqual(d.std_level,          "/api/v1/name/stdlevelname/std/")
            self.assertEqual(d.states,             [DocumentStateURI("/api/v1/doc/state/3/"), DocumentStateURI("/api/v1/doc/state/7/")])

            url = d.url()
            self.assertEqual(url, "https://www.ietf.org/archive/id/draft-ietf-avt-rtp-new-12.txt")
            self.assertEqual(self.dt.session.get(url).status_code, 200)
        else:
            self.fail("Cannot find document")


    def test_document_liaison(self) -> None:
        d  = self.dt.document(DocumentURI("/api/v1/doc/document/liaison-2012-05-31-3gpp-mmusic-on-rtcp-bandwidth-negotiation-attachment-1/"))
        if d is not None:
            self.assertEqual(d.internal_comments,  "")
            self.assertEqual(d.id,                 46457)
            self.assertEqual(d.name,               "liaison-2012-05-31-3gpp-mmusic-on-rtcp-bandwidth-negotiation-attachment-1")
            self.assertEqual(d.notify,             "")
            self.assertEqual(d.order,              1)
            self.assertEqual(d.rev,                "")
            self.assertEqual(d.external_url,       "")
            self.assertEqual(d.expires,            None)
            self.assertEqual(d.type,               DocumentTypeURI("/api/v1/name/doctypename/liaison/"))
            self.assertEqual(d.group,              None)
            self.assertEqual(d.resource_uri,       DocumentURI("/api/v1/doc/document/liaison-2012-05-31-3gpp-mmusic-on-rtcp-bandwidth-negotiation-attachment-1/"))
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
            self.assertEqual(d.time,               datetime.fromisoformat("2012-06-04T08:20:38"))
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
        d  = self.dt.document(DocumentURI("/api/v1/doc/document/liaison-2004-08-23-itu-t-ietf-liaison-statement-to-ietf-and-itu-t-study-groups-countering-spam-pdf-version-attachment-1/"))
        if d is not None:
            self.assertEqual(d.internal_comments,  "")
            self.assertEqual(d.id,                 43519)
            self.assertEqual(d.name,               "liaison-2004-08-23-itu-t-ietf-liaison-statement-to-ietf-and-itu-t-study-groups-countering-spam-pdf-version-attachment-1")
            self.assertEqual(d.notify,             "")
            self.assertEqual(d.order,              1)
            self.assertEqual(d.rev,                "")
            self.assertEqual(d.external_url,       "")
            self.assertEqual(d.expires,            None)
            self.assertEqual(d.type,               DocumentTypeURI("/api/v1/name/doctypename/liai-att/"))
            self.assertEqual(d.group,              None)
            self.assertEqual(d.resource_uri,       DocumentURI("/api/v1/doc/document/liaison-2004-08-23-itu-t-ietf-liaison-statement-to-ietf-and-itu-t-study-groups-countering-spam-pdf-version-attachment-1/"))
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
            self.assertEqual(d.time,               datetime.fromisoformat("2004-08-23T00:00:00"))
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
        d  = self.dt.document(DocumentURI("/api/v1/doc/document/minutes-89-cfrg/"))
        if d is not None:
            self.assertEqual(d.internal_comments,  "")
            self.assertEqual(d.id,                 272)
            self.assertEqual(d.name,               "minutes-89-cfrg")
            self.assertEqual(d.notify,             "")
            self.assertEqual(d.order,              1)
            self.assertEqual(d.rev,                "1")
            self.assertEqual(d.external_url,       "")
            self.assertEqual(d.expires,            None)
            self.assertEqual(d.type,               DocumentTypeURI("/api/v1/name/doctypename/minutes/"))
            self.assertEqual(d.group,              GroupURI("/api/v1/group/group/31/"))
            self.assertEqual(d.resource_uri,       DocumentURI("/api/v1/doc/document/minutes-89-cfrg/"))
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
            self.assertEqual(d.time,               datetime.fromisoformat("2014-04-09T08:09:14"))
            self.assertEqual(d.pages,              None)
            self.assertEqual(d.stream,             None)
            self.assertEqual(d.std_level,          None)
            self.assertEqual(d.states,             [DocumentStateURI("/api/v1/doc/state/79/")])

            url = d.url()
            self.assertEqual(url, "https://datatracker.ietf.org/meeting/89/materials/minutes-89-cfrg.txt")
            self.assertEqual(self.dt.session.get(url).status_code, 200)
        else:
            self.fail("Cannot find document")


    def test_document_recording(self) -> None:
        d  = self.dt.document(DocumentURI("/api/v1/doc/document/recording-94-taps-1/"))
        if d is not None:
            self.assertEqual(d.internal_comments,  "")
            self.assertEqual(d.id,                 49624)
            self.assertEqual(d.name,               "recording-94-taps-1")
            self.assertEqual(d.notify,             "")
            self.assertEqual(d.order,              1)
            self.assertEqual(d.rev,                "00")
            self.assertEqual(d.external_url,       "https://www.ietf.org/audio/ietf94/ietf94-room304-20151103-1520.mp3")
            self.assertEqual(d.expires,            None)
            self.assertEqual(d.type,               DocumentTypeURI("/api/v1/name/doctypename/recording/"))
            self.assertEqual(d.group,              GroupURI("/api/v1/group/group/1924/"))
            self.assertEqual(d.resource_uri,       DocumentURI("/api/v1/doc/document/recording-94-taps-1/"))
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
            self.assertEqual(d.time,               datetime.fromisoformat("2015-11-24T08:23:42"))
            self.assertEqual(d.pages,              None)
            self.assertEqual(d.stream,             None)
            self.assertEqual(d.std_level,          None)
            self.assertEqual(d.states,             [DocumentStateURI("/api/v1/doc/state/135/")])

            url = d.url()
            self.assertEqual(url, "https://www.ietf.org/audio/ietf94/ietf94-room304-20151103-1520.mp3")
            # Downloading the MP3 is expensive, so check a HEAD request instead:
            self.assertEqual(self.dt.session.head(url).status_code, 200)
        else:
            self.fail("Cannot find document")


    def test_document_review(self) -> None:
        d  = self.dt.document(DocumentURI("/api/v1/doc/document/review-bchv-rfc6890bis-04-genart-lc-kyzivat-2017-02-28/"))
        if d is not None:
            self.assertEqual(d.internal_comments,  "")
            self.assertEqual(d.id,                 69082)
            self.assertEqual(d.name,               "review-bchv-rfc6890bis-04-genart-lc-kyzivat-2017-02-28")
            self.assertEqual(d.notify,             "")
            self.assertEqual(d.order,              1)
            self.assertEqual(d.rev,                "00")
            self.assertEqual(d.external_url,       "")
            self.assertEqual(d.expires,            None)
            self.assertEqual(d.type,               DocumentTypeURI("/api/v1/name/doctypename/review/"))
            self.assertEqual(d.group,              GroupURI("/api/v1/group/group/1972/"))
            self.assertEqual(d.resource_uri,       DocumentURI("/api/v1/doc/document/review-bchv-rfc6890bis-04-genart-lc-kyzivat-2017-02-28/"))
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
            self.assertEqual(d.time,               datetime.fromisoformat("2017-02-28T12:52:33"))
            self.assertEqual(d.pages,              None)
            self.assertEqual(d.stream,             None)
            self.assertEqual(d.std_level,          None)
            self.assertEqual(d.states,             [DocumentStateURI("/api/v1/doc/state/143/")])

            url = d.url()
            self.assertEqual(url, "https://datatracker.ietf.org/doc/review-bchv-rfc6890bis-04-genart-lc-kyzivat-2017-02-28")
            self.assertEqual(self.dt.session.get(url).status_code, 200)
        else:
            self.fail("Cannot find document")


    def test_document_shepwrit(self) -> None:
        for d in self.dt.documents(doctype=self.dt.document_type(DocumentTypeURI("/api/v1/name/doctypename/shepwrit"))):
            self.fail("shepwrit is not used, so this should return no documents")


    def test_document_slides(self) -> None:
        d  = self.dt.document(DocumentURI("/api/v1/doc/document/slides-65-l2vpn-4/"))
        if d is not None:
            self.assertEqual(d.internal_comments,  "")
            self.assertEqual(d.id,                 736)
            self.assertEqual(d.name,               "slides-65-l2vpn-4")
            self.assertEqual(d.notify,             "")
            self.assertEqual(d.order,              4)
            self.assertEqual(d.rev,                "00")
            self.assertEqual(d.external_url,       "")
            self.assertEqual(d.expires,            None)
            self.assertEqual(d.type,               DocumentTypeURI("/api/v1/name/doctypename/slides/"))
            self.assertEqual(d.group,              GroupURI("/api/v1/group/group/1593/"))
            self.assertEqual(d.resource_uri,       DocumentURI("/api/v1/doc/document/slides-65-l2vpn-4/"))
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
            self.assertEqual(d.time,               datetime.fromisoformat("2006-04-07T17:30:22"))
            self.assertEqual(d.pages,              None)
            self.assertEqual(d.stream,             None)
            self.assertEqual(d.std_level,          None)
            self.assertEqual(d.states,             [DocumentStateURI("/api/v1/doc/state/141/"), DocumentStateURI("/api/v1/doc/state/138/")])

            url = d.url()
            self.assertEqual(url, "https://www.ietf.org/proceedings/65/slides/l2vpn-4.pdf")
            self.assertEqual(self.dt.session.get(url).status_code, 200)
        else:
            self.fail("Cannot find document")


    def test_document_statchg(self) -> None:
        d  = self.dt.document(DocumentURI("/api/v1/doc/document/status-change-rfc3044-rfc3187-orig-urn-regs-to-historic/"))
        if d is not None:
            self.assertEqual(d.internal_comments,  "")
            self.assertEqual(d.id,                 78306)
            self.assertEqual(d.name,               "status-change-rfc3044-rfc3187-orig-urn-regs-to-historic")
            self.assertEqual(d.notify,             "")
            self.assertEqual(d.order,              1)
            self.assertEqual(d.rev,                "00")
            self.assertEqual(d.external_url,       "")
            self.assertEqual(d.expires,            None)
            self.assertEqual(d.type,               DocumentTypeURI("/api/v1/name/doctypename/statchg/"))
            self.assertEqual(d.group,              GroupURI("/api/v1/group/group/2/"))
            self.assertEqual(d.resource_uri,       DocumentURI("/api/v1/doc/document/status-change-rfc3044-rfc3187-orig-urn-regs-to-historic/"))
            self.assertEqual(d.title,              "Change status of RFC 3044 and RFC 3187 (original ISSN and ISBN URN Namespace registrationS) to Historic")
            self.assertEqual(d.abstract,           "")
            self.assertEqual(d.uploaded_filename,  "")
            self.assertEqual(d.rfc,                None)
            self.assertEqual(d.shepherd,           None)
            self.assertEqual(d.submissions,        [])
            self.assertEqual(d.intended_std_level, None)
            self.assertEqual(d.ad,                 PersonURI("/api/v1/person/person/102154/"))
            self.assertEqual(d.note,               "")
            self.assertEqual(d.words,              None)
            self.assertEqual(d.tags,               [])
            self.assertEqual(d.time,               datetime.fromisoformat("2017-08-21T09:32:46"))
            self.assertEqual(d.pages,              None)
            self.assertEqual(d.stream,             StreamURI("/api/v1/name/streamname/ietf/"))
            self.assertEqual(d.std_level,          None)
            self.assertEqual(d.states,             [DocumentStateURI("/api/v1/doc/state/127/")])

            url = d.url()
            self.assertEqual(url, "https://www.ietf.org/sc/status-change-rfc3044-rfc3187-orig-urn-regs-to-historic-00.txt")
            self.assertEqual(self.dt.session.get(url).status_code, 200)
        else:
            self.fail("Cannot find document")


    def test_documents(self):
        doctype = self.dt.document_type(DocumentTypeURI("/api/v1/name/doctypename/draft"))
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
            self.assertEqual(d.resource_uri, DocumentURI("/api/v1/doc/document/draft-ietf-avt-rtp-new/"))
        else:
            self.fail("Cannot find document")

    # FIXME: this needs to be updated
    def test_document_from_rfc(self) -> None:
        d  = self.dt.document_from_rfc("rfc3550")
        if d is not None:
            self.assertEqual(d.resource_uri, DocumentURI("/api/v1/doc/document/draft-ietf-avt-rtp-new/"))
        else:
            self.fail("Cannot find document")

    # FIXME: this needs to be updated
    def test_documents_from_bcp(self) -> None:
        d  = list(self.dt.documents_from_bcp("bcp205"))
        if d is not None:
            self.assertEqual(len(d), 1)
            self.assertEqual(d[0].resource_uri, DocumentURI("/api/v1/doc/document/draft-sheffer-rfc6982bis/"))
        else:
            self.fail("Cannot find document")

    # FIXME: this needs to be updated
    def test_documents_from_std(self) -> None:
        d  = list(self.dt.documents_from_std("std68"))
        self.assertEqual(len(d), 1)
        self.assertEqual(d[0].resource_uri, DocumentURI("/api/v1/doc/document/draft-crocker-rfc4234bis/"))


    def test_document_state(self) -> None:
        s = self.dt.document_state(DocumentStateURI('/api/v1/doc/state/7/'))
        if s is not None:
            self.assertEqual(s.id,           7)
            self.assertEqual(s.resource_uri, DocumentStateURI("/api/v1/doc/state/7/"))
            self.assertEqual(s.name,         "RFC Published")
            self.assertEqual(s.desc,         "The ID has been published as an RFC.")
            self.assertEqual(s.type,         DocumentStateTypeURI("/api/v1/doc/statetype/draft-iesg/"))
            self.assertEqual(s.next_states,  [DocumentStateURI("/api/v1/doc/state/8/")])
            self.assertEqual(s.order,        32)
            self.assertEqual(s.slug,         "pub")
            self.assertEqual(s.used,         True)
        else:
            self.fail("Cannot find state")


    def test_document_states(self) -> None:
        st = self.dt.document_state_type(DocumentStateTypeURI("/api/v1/doc/statetype/draft-rfceditor/"))
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
        st = self.dt.document_state_type(DocumentStateTypeURI("/api/v1/doc/statetype/draft-rfceditor/"))
        if st is not None:
            self.assertEqual(st.resource_uri, DocumentStateTypeURI("/api/v1/doc/statetype/draft-rfceditor/"))
            self.assertEqual(st.slug,         "draft-rfceditor")
            self.assertEqual(st.label,        "RFC Editor state")
        else:
            self.fail("Cannot find state type")


    def test_document_state_types(self) -> None:
        st = list(self.dt.document_state_types())
        self.assertEqual(len(st), 24)
        self.assertEqual(st[ 0].slug, 'draft')
        self.assertEqual(st[ 1].slug, 'draft-iesg')
        self.assertEqual(st[ 2].slug, 'draft-iana')
        self.assertEqual(st[ 3].slug, 'draft-rfceditor')
        self.assertEqual(st[ 4].slug, 'draft-stream-ietf')
        self.assertEqual(st[ 5].slug, 'draft-stream-irtf')
        self.assertEqual(st[ 6].slug, 'draft-stream-ise')
        self.assertEqual(st[ 7].slug, 'draft-stream-iab')
        self.assertEqual(st[ 8].slug, 'slides')
        self.assertEqual(st[ 9].slug, 'minutes')
        self.assertEqual(st[10].slug, 'agenda')
        self.assertEqual(st[11].slug, 'liai-att')
        self.assertEqual(st[12].slug, 'charter')
        self.assertEqual(st[13].slug, 'conflrev')
        self.assertEqual(st[14].slug, 'draft-iana-action')
        self.assertEqual(st[15].slug, 'draft-iana-review')
        self.assertEqual(st[16].slug, 'statchg')
        self.assertEqual(st[17].slug, 'recording')
        self.assertEqual(st[18].slug, 'bluesheets')
        self.assertEqual(st[19].slug, 'reuse_policy')
        self.assertEqual(st[20].slug, 'review')
        self.assertEqual(st[21].slug, 'liaison')
        self.assertEqual(st[22].slug, 'shepwrit')
        self.assertEqual(st[23].slug, 'draft-iana-experts')


    def test_document_event(self) -> None:
        e = self.dt.document_event(DocumentEventURI("/api/v1/doc/docevent/729040/"))
        if e is not None:
            self.assertEqual(e.id,              729040)
            self.assertEqual(e.resource_uri,    DocumentEventURI("/api/v1/doc/docevent/729040/"))
            self.assertEqual(e.by,              PersonURI("/api/v1/person/person/121595/"))
            self.assertEqual(e.doc,             DocumentURI("/api/v1/doc/document/draft-irtf-cfrg-randomness-improvements/"))
            self.assertEqual(e.type,            "new_revision")
            self.assertEqual(e.desc,            "New version available: <b>draft-irtf-cfrg-randomness-improvements-09.txt</b>")
            self.assertEqual(e.rev,             "09")
            self.assertEqual(e.time,            datetime.fromisoformat("2020-01-27T06:41:36"))
        else:
            self.fail("Cannot find event")


    def test_document_events(self) -> None:
        p  = self.dt.person_from_email("csp@csperkins.org")
        d  = self.dt.document_from_draft("draft-ietf-avtcore-rtp-circuit-breakers")
        de = list(self.dt.document_events(doc=d, by=p, event_type="new_revision"))
        self.assertEqual(len(de), 19)
        self.assertEqual(de[ 0].id, 478637)
        self.assertEqual(de[ 1].id, 475709)
        self.assertEqual(de[ 2].id, 470372)
        self.assertEqual(de[ 3].id, 466353)
        self.assertEqual(de[ 4].id, 460235)
        self.assertEqual(de[ 5].id, 456912)
        self.assertEqual(de[ 6].id, 456736)
        self.assertEqual(de[ 7].id, 444539)
        self.assertEqual(de[ 8].id, 415925)
        self.assertEqual(de[ 9].id, 413197)
        self.assertEqual(de[10].id, 402942)
        self.assertEqual(de[11].id, 397776)
        self.assertEqual(de[12].id, 384673)
        self.assertEqual(de[13].id, 369306)
        self.assertEqual(de[14].id, 364835)
        self.assertEqual(de[15].id, 340119)
        self.assertEqual(de[16].id, 326064)
        self.assertEqual(de[17].id, 307226)
        self.assertEqual(de[18].id, 306017)


    def test_ballot_position_name(self) -> None:
        bp = self.dt.ballot_position_name(BallotPositionNameURI("/api/v1/name/ballotpositionname/moretime/"))
        if bp is not None:
            self.assertEqual(bp.blocking,     False)
            self.assertEqual(bp.desc,         "")
            self.assertEqual(bp.order,        0)
            self.assertEqual(bp.resource_uri, BallotPositionNameURI("/api/v1/name/ballotpositionname/moretime/"))
            self.assertEqual(bp.slug,         "moretime")
            self.assertEqual(bp.used,         True)


    def test_ballot_position_names(self) -> None:
        bps = list(self.dt.ballot_position_names())
        self.assertEqual(len(bps), 9)
        self.assertEqual(bps[0].slug, "moretime")
        self.assertEqual(bps[1].slug, "notready")
        self.assertEqual(bps[2].slug, "yes")
        self.assertEqual(bps[3].slug, "noobj")
        self.assertEqual(bps[4].slug, "block")
        self.assertEqual(bps[5].slug, "discuss")
        self.assertEqual(bps[6].slug, "abstain")
        self.assertEqual(bps[7].slug, "recuse")
        self.assertEqual(bps[8].slug, "norecord")


    def test_ballot_type(self) -> None:
        bt = self.dt.ballot_type(BallotTypeURI("/api/v1/doc/ballottype/5/"))
        if bt is not None:
            self.assertEqual(bt.doc_type,       DocumentTypeURI("/api/v1/name/doctypename/conflrev/"))
            self.assertEqual(bt.id,             5)
            self.assertEqual(bt.name,           "Approve")
            self.assertEqual(bt.order,          0)
            self.assertEqual(len(bt.positions), 6)
            self.assertEqual(bt.positions[0],   BallotPositionNameURI("/api/v1/name/ballotpositionname/yes/"))
            self.assertEqual(bt.positions[1],   BallotPositionNameURI("/api/v1/name/ballotpositionname/noobj/"))
            self.assertEqual(bt.positions[2],   BallotPositionNameURI("/api/v1/name/ballotpositionname/discuss/"))
            self.assertEqual(bt.positions[3],   BallotPositionNameURI("/api/v1/name/ballotpositionname/abstain/"))
            self.assertEqual(bt.positions[4],   BallotPositionNameURI("/api/v1/name/ballotpositionname/recuse/"))
            self.assertEqual(bt.positions[5],   BallotPositionNameURI("/api/v1/name/ballotpositionname/norecord/"))
            self.assertEqual(bt.question,       "Is this the correct conflict review response?")
            self.assertEqual(bt.resource_uri,   BallotTypeURI("/api/v1/doc/ballottype/5/"))
            self.assertEqual(bt.slug,           "conflrev")
            self.assertEqual(bt.used,           True)
        else:
            self.fail("Could not find ballot type")


    def test_ballot_types_doctype(self) -> None:
        bts = list(self.dt.ballot_types(self.dt.document_type(DocumentTypeURI("/api/v1/name/doctypename/draft"))))
        self.assertEqual(len(bts), 2)
        self.assertEqual(bts[0].slug, "irsg-approve")
        self.assertEqual(bts[1].slug, "approve")


    def test_ballot_document_event(self) -> None:
        e = self.dt.ballot_document_event(BallotDocumentEventURI("/api/v1/doc/ballotdocevent/744784/"))
        if e is not None:
            self.assertEqual(e.ballot_type,  BallotTypeURI("/api/v1/doc/ballottype/5/"))
            self.assertEqual(e.by,           PersonURI("/api/v1/person/person/21684/"))
            self.assertEqual(e.desc,         'Created "Approve" ballot')
            self.assertEqual(e.doc,          DocumentURI("/api/v1/doc/document/conflict-review-dold-payto/"))
            self.assertEqual(e.docevent_ptr, DocumentEventURI("/api/v1/doc/docevent/744784/"))
            self.assertEqual(e.id,           744784)
            self.assertEqual(e.resource_uri, BallotDocumentEventURI("/api/v1/doc/ballotdocevent/744784/"))
            self.assertEqual(e.rev,          "00")
            self.assertEqual(e.time,         datetime.fromisoformat("2020-04-04T10:57:29"))
            self.assertEqual(e.type,         "created_ballot")
        else:
            self.fail("Cannot find ballot event")


    def test_ballot_document_events(self) -> None:
        d  = self.dt.document_from_draft("draft-ietf-avtcore-rtp-circuit-breakers")
        de = list(self.dt.ballot_document_events(doc=d))
        self.assertEqual(len(de), 2)
        self.assertEqual(de[0].id, 478676)
        self.assertEqual(de[1].id, 461800)

        bt = self.dt.ballot_type(BallotTypeURI("/api/v1/doc/ballottype/3/")) # Charter approval
        p  = self.dt.person(PersonURI("/api/v1/person/person/108756/"))      # Cindy Morgan
        d  = self.dt.document(DocumentURI("/api/v1/doc/document/charter-ietf-rmcat/"))
        de = list(self.dt.ballot_document_events(doc = d, ballot_type = bt, by = p, event_type = "closed_ballot"))
        self.assertEqual(len(de), 1)
        self.assertEqual(de[0].id, 304166)


    def test_documents_authored_by_person(self) -> None:
        p = self.dt.person_from_email("ladan@isi.edu")
        if p is not None:
            a = list(self.dt.documents_authored_by_person(p))
            self.assertEqual(len(a), 7)
            self.assertEqual(a[0].document, DocumentURI(uri='/api/v1/doc/document/draft-gharai-ac3/'))
            self.assertEqual(a[1].document, DocumentURI(uri='/api/v1/doc/document/draft-gharai-hdtv-video/'))
            self.assertEqual(a[2].document, DocumentURI(uri='/api/v1/doc/document/draft-ietf-avt-smpte292-video/'))
            self.assertEqual(a[3].document, DocumentURI(uri='/api/v1/doc/document/draft-gharai-avt-uncomp-video/'))
            self.assertEqual(a[4].document, DocumentURI(uri='/api/v1/doc/document/draft-ietf-avt-uncomp-video/'))
            self.assertEqual(a[5].document, DocumentURI(uri='/api/v1/doc/document/draft-gharai-avt-tfrc-profile/'))
            self.assertEqual(a[6].document, DocumentURI(uri='/api/v1/doc/document/draft-ietf-avt-tfrc-profile/'))
        else:
            self.fail("Cannot find person");


    def test_documents_authored_by_email(self) -> None:
        e = self.dt.email(EmailURI("/api/v1/person/email/ladan@isi.edu/"))
        if e is not None:
            a = list(self.dt.documents_authored_by_email(e))
            self.assertEqual(len(a), 7)
            self.assertEqual(a[0].document, DocumentURI(uri='/api/v1/doc/document/draft-gharai-ac3/'))
            self.assertEqual(a[1].document, DocumentURI(uri='/api/v1/doc/document/draft-gharai-hdtv-video/'))
            self.assertEqual(a[2].document, DocumentURI(uri='/api/v1/doc/document/draft-ietf-avt-smpte292-video/'))
            self.assertEqual(a[3].document, DocumentURI(uri='/api/v1/doc/document/draft-gharai-avt-uncomp-video/'))
            self.assertEqual(a[4].document, DocumentURI(uri='/api/v1/doc/document/draft-ietf-avt-uncomp-video/'))
            self.assertEqual(a[5].document, DocumentURI(uri='/api/v1/doc/document/draft-gharai-avt-tfrc-profile/'))
            self.assertEqual(a[6].document, DocumentURI(uri='/api/v1/doc/document/draft-ietf-avt-tfrc-profile/'))
        else:
            self.fail("Cannot find person");




    # FIXME: this needs to be updated
    def test_submission(self) -> None:
        s  = self.dt.submission(SubmissionURI("/api/v1/submit/submission/2402/"))
        if s is not None:
            #self.assertEqual(s.abstract,        "Internet technical specifications often need to...")
            self.assertEqual(s.access_key,      "f77d08da6da54f3cbecca13d31646be8")
            self.assertEqual(s.auth_key,        "fMm6hur5dJ7gV58x5SE0vkHUoDOrSuSF")
            self.assertEqual(s.authors,         "[{'email': 'dcrocker@bbiw.net', 'name': 'Dave Crocker'}, {'email': 'paul.overell@thus.net', 'name': 'Paul Overell'}]")
            self.assertEqual(s.checks,          [SubmissionCheckURI("/api/v1/submit/submissioncheck/386/")])
            self.assertEqual(s.document_date,   "2007-10-09")
            self.assertEqual(s.draft,           DocumentURI("/api/v1/doc/document/draft-crocker-rfc4234bis/"))
            self.assertEqual(s.file_size,       27651)
            self.assertEqual(s.file_types,      ".txt,.xml,.pdf")
            #self.assertEqual(s.first_two_pages, "\n\n\nNetwork Working Group...")
            self.assertEqual(s.group,           GroupURI("/api/v1/group/group/1027/"))
            self.assertEqual(s.id,              2402)
            self.assertEqual(s.name,            "draft-crocker-rfc4234bis")
            self.assertEqual(s.note,            "")
            self.assertEqual(s.pages,           13)
            self.assertEqual(s.remote_ip,       "72.255.3.179")
            self.assertEqual(s.replaces,        "")
            self.assertEqual(s.resource_uri,    SubmissionURI("/api/v1/submit/submission/2402/"))
            self.assertEqual(s.rev,             "01")
            self.assertEqual(s.state,           "/api/v1/name/draftsubmissionstatename/posted/")
            self.assertEqual(s.submission_date, "2007-10-09")
            self.assertEqual(s.submitter,       "Dave Crocker")
            self.assertEqual(s.title,           "Augmented BNF for Syntax Specifications: ABNF")
            self.assertEqual(s.words,           None)
        else:
            self.fail("Cannot find submission")


    def test_submission_event(self) -> None:
        e  = self.dt.submission_event(SubmissionEventURI("/api/v1/submit/submissionevent/188542/"))
        if e is not None:
            self.assertEqual(e.by,           PersonURI("/api/v1/person/person/115824/"))
            self.assertEqual(e.desc,         "Uploaded submission")
            self.assertEqual(e.id,           188542)
            self.assertEqual(e.resource_uri, SubmissionEventURI("/api/v1/submit/submissionevent/188542/"))
            self.assertEqual(e.submission,   SubmissionURI("/api/v1/submit/submission/111128/"))
            self.assertEqual(e.time,         datetime.fromisoformat("2020-03-23T04:18:27"))
        else:
            self.fail("Cannot find submission event")


    # FIXME: this needs to be updated
    def test_document_type(self) -> None:
        doctype = self.dt.document_type(DocumentTypeURI("/api/v1/name/doctypename/draft"))
        if doctype is not None:
            self.assertEqual(doctype.resource_uri, DocumentTypeURI("/api/v1/name/doctypename/draft/"))
            self.assertEqual(doctype.name,         "Draft")
            self.assertEqual(doctype.used,         True)
            self.assertEqual(doctype.prefix,       "draft")
            self.assertEqual(doctype.slug,         "draft")
            self.assertEqual(doctype.desc,         "")
            self.assertEqual(doctype.order,        0)
        else:
            self.fail("Cannot find doctype")

    # FIXME: this needs to be updated
    def test_document_types(self) -> None:
        types = list(self.dt.document_types())
        self.assertEqual(len(types), 13)
        self.assertEqual(types[ 0].slug, "agenda")
        self.assertEqual(types[ 1].slug, "bluesheets")
        self.assertEqual(types[ 2].slug, "charter")
        self.assertEqual(types[ 3].slug, "conflrev")
        self.assertEqual(types[ 4].slug, "draft")
        self.assertEqual(types[ 5].slug, "liaison")
        self.assertEqual(types[ 6].slug, "liai-att")
        self.assertEqual(types[ 7].slug, "minutes")
        self.assertEqual(types[ 8].slug, "recording")
        self.assertEqual(types[ 9].slug, "review")
        self.assertEqual(types[10].slug, "shepwrit")
        self.assertEqual(types[11].slug, "slides")
        self.assertEqual(types[12].slug, "statchg")

    # -----------------------------------------------------------------------------------------------------------------------------
    # Tests relating to streams:

    # FIXME: this needs to be updated
    def test_stream(self) -> None:
        stream = self.dt.stream(StreamURI("/api/v1/name/streamname/irtf/"))
        if stream is not None:
            self.assertEqual(stream.desc,         "IRTF Stream")
            self.assertEqual(stream.name,         "IRTF")
            self.assertEqual(stream.order,        3)
            self.assertEqual(stream.resource_uri, StreamURI("/api/v1/name/streamname/irtf/"))
            self.assertEqual(stream.slug,         "irtf")
            self.assertEqual(stream.used,         True)
        else:
            self.fail("Cannot find stream")

    # FIXME: this needs to be updated
    def test_streams(self) -> None:
        streams = list(self.dt.streams())
        self.assertEqual(len(streams), 5)
        self.assertEqual(streams[ 0].slug, "ietf")
        self.assertEqual(streams[ 1].slug, "ise")
        self.assertEqual(streams[ 2].slug, "irtf")
        self.assertEqual(streams[ 3].slug, "iab")
        self.assertEqual(streams[ 4].slug, "legacy")

    # -----------------------------------------------------------------------------------------------------------------------------
    # Tests relating to groups:

    # FIXME: this needs to be updated
    def test_group(self) -> None:
        group = self.dt.group(GroupURI("/api/v1/group/group/941/"))
        if group is not None:
            self.assertEqual(group.acronym,        "avt")
            self.assertEqual(group.ad,             None)
            self.assertEqual(group.charter,        DocumentURI("/api/v1/doc/document/charter-ietf-avt/"))
            self.assertEqual(group.comments,       "")
            self.assertEqual(group.description,    "\n  The Audio/Video Transport Working Group was formed to specify a protocol \n  for real-time transmission of audio and video over unicast and multicast \n  UDP/IP. This is the Real-time Transport Protocol, RTP, along with its \n  associated profiles and payload formats.")
            self.assertEqual(group.id,             941)
            self.assertEqual(group.list_archive,   "https://mailarchive.ietf.org/arch/search/?email_list=avt")
            self.assertEqual(group.list_email,     "avt@ietf.org")
            self.assertEqual(group.list_subscribe, "https://www.ietf.org/mailman/listinfo/avt")
            self.assertEqual(group.name,           "Audio/Video Transport")
            self.assertEqual(group.parent,         GroupURI("/api/v1/group/group/1683/"))
            self.assertEqual(group.resource_uri,   GroupURI("/api/v1/group/group/941/"))
            self.assertEqual(group.state,          GroupStateURI("/api/v1/name/groupstatename/conclude/"))
            self.assertEqual(group.time,           datetime.fromisoformat("2011-12-09T12:00:00"))
            self.assertEqual(group.type,           "/api/v1/name/grouptypename/wg/")
            self.assertEqual(group.unused_states,  [])
            self.assertEqual(group.unused_tags,    [])
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
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0].id, 3)
        self.assertEqual(groups[1].id, 1853)


    def test_group_history(self) -> None:
        group_history = self.dt.group_history(GroupHistoryURI("/api/v1/group/grouphistory/4042/"))
        if group_history is not None:
            self.assertEqual(group_history.acronym,              "git")
            self.assertEqual(group_history.ad,                   None)
            self.assertEqual(group_history.comments,             "")
            self.assertEqual(group_history.description,          "")
            self.assertEqual(group_history.group,                GroupURI("/api/v1/group/group/2233/"))
            self.assertEqual(group_history.id,                   4042)
            self.assertEqual(group_history.list_archive,         "https://mailarchive.ietf.org/arch/browse/ietf-and-github/")
            self.assertEqual(group_history.list_email,           "ietf-and-github@ietf.org")
            self.assertEqual(group_history.list_subscribe,       "https://www.ietf.org/mailman/listinfo/ietf-and-github")
            self.assertEqual(group_history.name,                 "GitHub Integration and Tooling")
            self.assertEqual(group_history.parent,               GroupURI("/api/v1/group/group/1008/"))
            self.assertEqual(group_history.resource_uri,         GroupHistoryURI("/api/v1/group/grouphistory/4042/"))
            self.assertEqual(group_history.state,                GroupStateURI("/api/v1/name/groupstatename/active/"))
            self.assertEqual(group_history.time,                 datetime.fromisoformat("2019-02-08T14:07:27"))
            self.assertEqual(group_history.type,                 "/api/v1/name/grouptypename/wg/")
            self.assertEqual(group_history.unused_states,        [])
            self.assertEqual(group_history.unused_tags,          [])
            self.assertEqual(group_history.uses_milestone_dates, True)
        else:
            self.fail("Cannot find group history")


    def test_group_histories_from_acronym(self) -> None:
        group_histories = list(self.dt.group_histories_from_acronym("spud"))
        self.assertEqual(len(group_histories), 2)
        self.assertEqual(group_histories[0].id, 2179)
        self.assertEqual(group_histories[1].id, 2257)


    def test_group_histories(self) -> None:
        group_histories = self.dt.group_histories()
        self.assertIsNot(group_histories, None)


    def test_group_event(self) -> None:
        group_event = self.dt.group_event(GroupEventURI("/api/v1/group/groupevent/16849/"))
        if group_event is not None:
            self.assertEqual(group_event.by,           PersonURI("/api/v1/person/person/108756/"))
            self.assertEqual(group_event.desc,         "Added milestone \"Submit data flow information model (informational)\", due 2020-04-30, from approved charter")
            self.assertEqual(group_event.group,        GroupURI("/api/v1/group/group/1962/"))
            self.assertEqual(group_event.id,           16849)
            self.assertEqual(group_event.resource_uri, GroupEventURI("/api/v1/group/groupevent/16849/"))
            self.assertEqual(group_event.time,         datetime.fromisoformat("2020-04-20T13:31:48"))
            self.assertEqual(group_event.type,         "changed_milestone")
        else:
            self.fail("Cannot find group event")


    def test_group_events_by(self) -> None:
        group_events_by = self.dt.group_events(by=self.dt.person(PersonURI("/api/v1/person/person/108756/")))
        self.assertIsNot(group_events_by, None)


    def test_group_events_group(self) -> None:
        group_events_group = list(self.dt.group_events(group=self.dt.group(GroupURI("/api/v1/group/group/1997/"))))
        self.assertEqual(len(group_events_group),  4)
        self.assertEqual(group_events_group[0].id, 9652)
        self.assertEqual(group_events_group[1].id, 9585)
        self.assertEqual(group_events_group[2].id, 9151)
        self.assertEqual(group_events_group[3].id, 8975)


    def test_group_events_type(self) -> None:
        group_events_type = self.dt.group_events(type="changed_state")
        self.assertIsNot(group_events_type, None)


    def test_group_url(self) -> None:
        group_url = self.dt.group_url(GroupUrlURI("/api/v1/group/groupurl/1/"))
        if group_url is not None:
            self.assertEqual(group_url.group,        GroupURI("/api/v1/group/group/934/"))
            self.assertEqual(group_url.id,           1)
            self.assertEqual(group_url.name,         "Applications Area Web Page")
            self.assertEqual(group_url.resource_uri, GroupUrlURI("/api/v1/group/groupurl/1/"))
            self.assertEqual(group_url.url,          "http://www.apps.ietf.org/")
        else:
            self.fail("Cannot find group URL")


    def test_group_urls(self) -> None:
        group_urls = list(self.dt.group_urls(self.dt.group(GroupURI("/api/v1/group/group/1062/"))))
        self.assertEqual(len(group_urls),  1)
        self.assertEqual(group_urls[0].id, 20)


    def test_group_milestone_statename(self) -> None:
        group_milestone_statename = self.dt.group_milestone_statename(GroupMilestoneStateNameURI("/api/v1/name/groupmilestonestatename/active/"))
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
        self.assertEqual(group_milestone_statenames[1].slug, "deleted")
        self.assertEqual(group_milestone_statenames[2].slug, "review")
        self.assertEqual(group_milestone_statenames[3].slug, "charter")


    def test_group_milestone(self) -> None:
        group_milestone = self.dt.group_milestone(GroupMilestoneURI("/api/v1/group/groupmilestone/1520/"))
        if group_milestone is not None:
            self.assertEqual(group_milestone.desc,         "Define a protocol for the link and IP layer.")
            self.assertEqual(group_milestone.docs,         [])
            self.assertEqual(group_milestone.due,          "1988-03-31")
            self.assertEqual(group_milestone.group,        GroupURI("/api/v1/group/group/1209/"))
            self.assertEqual(group_milestone.id,           1520)
            self.assertEqual(group_milestone.order,        None)
            self.assertEqual(group_milestone.resolved,     "")
            self.assertEqual(group_milestone.resource_uri, GroupMilestoneURI("/api/v1/group/groupmilestone/1520/"))
            self.assertEqual(group_milestone.state,        GroupMilestoneStateNameURI("/api/v1/name/groupmilestonestatename/active/"))
            self.assertEqual(group_milestone.time,         datetime.fromisoformat("2012-02-26T00:21:52"))
        else:
            self.fail("Cannot find group milestone")


    def test_group_milestones(self) -> None:
        group_milestones = self.dt.group_milestones()
        self.assertIsNot(group_milestones, None)


    def test_group_milestones_group(self) -> None:
        group_milestones = list(self.dt.group_milestones(group=self.dt.group(GroupURI("/api/v1/group/group/1209/"))))
        self.assertEqual(len(group_milestones),  1)
        self.assertEqual(group_milestones[0].id, 1520)
        self.assertIsNot(group_milestones, None)


    def test_group_milestones_state(self) -> None:
        group_milestones = self.dt.group_milestones(state=self.dt.group_milestone_statename(GroupMilestoneStateNameURI("/api/v1/name/groupmilestonestatename/active/")))
        self.assertIsNot(group_milestones, None)


    def test_role_name(self) -> None:
        role_name = self.dt.role_name(RoleNameURI("/api/v1/name/rolename/ceo/"))
        if role_name is not None:
            self.assertEqual(role_name.desc,         "")
            self.assertEqual(role_name.name,         "CEO")
            self.assertEqual(role_name.order,        0)
            self.assertEqual(role_name.resource_uri, RoleNameURI("/api/v1/name/rolename/ceo/"))
            self.assertEqual(role_name.slug,         "ceo")
            self.assertEqual(role_name.used,         True)
        else:
            self.fail("Cannot find role name")


    def test_role_names(self) -> None:
        role_names = list(self.dt.role_names())
        self.assertEqual(len(role_names), 25)
        self.assertEqual(role_names[0].slug, "ceo")
        self.assertEqual(role_names[1].slug, "coord")
        self.assertEqual(role_names[2].slug, "comdir")
        self.assertEqual(role_names[3].slug, "lead")
        self.assertEqual(role_names[4].slug, "trac-admin")
        self.assertEqual(role_names[5].slug, "trac-editor")
        self.assertEqual(role_names[6].slug, "chair")
        self.assertEqual(role_names[7].slug, "ad")
        self.assertEqual(role_names[8].slug, "execdir")
        self.assertEqual(role_names[9].slug, "admdir")
        self.assertEqual(role_names[10].slug, "pre-ad")
        self.assertEqual(role_names[11].slug, "advisor")
        self.assertEqual(role_names[12].slug, "liaiman")
        self.assertEqual(role_names[13].slug, "techadv")
        self.assertEqual(role_names[14].slug, "auth")
        self.assertEqual(role_names[15].slug, "editor")
        self.assertEqual(role_names[16].slug, "delegate")
        self.assertEqual(role_names[17].slug, "secr")
        self.assertEqual(role_names[18].slug, "member")
        self.assertEqual(role_names[19].slug, "atlarge")
        self.assertEqual(role_names[20].slug, "liaison")
        self.assertEqual(role_names[21].slug, "announce")
        self.assertEqual(role_names[22].slug, "matman")
        self.assertEqual(role_names[23].slug, "recman")
        self.assertEqual(role_names[24].slug, "reviewer")


    def test_group_role(self) -> None:
        group_role = self.dt.group_role(GroupRoleURI("/api/v1/group/role/1076/"))
        if group_role is not None:
            self.assertEqual(group_role.email,  EmailURI("/api/v1/person/email/csp@csperkins.org/"))
            self.assertEqual(group_role.group,  GroupURI("/api/v1/group/group/1727/"))
            self.assertEqual(group_role.id,     1076)
            self.assertEqual(group_role.name,   RoleNameURI("/api/v1/name/rolename/chair/"))
            self.assertEqual(group_role.person, PersonURI("/api/v1/person/person/20209/"))
        else:
            self.fail("Cannot find group role")


    def test_group_roles(self) -> None:
        group_roles = self.dt.group_roles()
        self.assertIsNot(group_roles, None)


    def test_group_roles_email(self) -> None:
        group_roles = list(self.dt.group_roles(email="csp@csperkins.org"))
        self.assertEqual(len(group_roles), 7)
        self.assertEqual(group_roles[0].id, 1076)
        self.assertEqual(group_roles[1].id, 9355)
        self.assertEqual(group_roles[2].id, 8464)
        self.assertEqual(group_roles[3].id, 8465)
        self.assertEqual(group_roles[4].id, 8466)
        self.assertEqual(group_roles[5].id, 3998)
        self.assertEqual(group_roles[6].id, 9772)


    def test_group_roles_group(self) -> None:
        group_roles = list(self.dt.group_roles(group=self.dt.group(GroupURI("/api/v1/group/group/1997/"))))
        self.assertEqual(len(group_roles), 3)
        self.assertEqual(group_roles[0].id, 3036)
        self.assertEqual(group_roles[1].id, 3037)
        self.assertEqual(group_roles[2].id, 3038)


    def test_group_roles_name(self) -> None:
        group_roles = self.dt.group_roles(name=self.dt.role_name(RoleNameURI("/api/v1/name/rolename/chair/")))
        self.assertIsNot(group_roles, None)


    def test_group_roles_person(self) -> None:
        group_roles = list(self.dt.group_roles(person=self.dt.person(PersonURI("/api/v1/person/person/20209/"))))
        self.assertEqual(len(group_roles), 7)
        self.assertEqual(group_roles[0].id, 1076)
        self.assertEqual(group_roles[1].id, 9355)
        self.assertEqual(group_roles[2].id, 8464)
        self.assertEqual(group_roles[3].id, 8465)
        self.assertEqual(group_roles[4].id, 8466)
        self.assertEqual(group_roles[5].id, 3998)
        self.assertEqual(group_roles[6].id, 9772)


    def test_group_milestone_history(self) -> None:
        group_milestone_history = self.dt.group_milestone_history(GroupMilestoneHistoryURI("/api/v1/group/groupmilestonehistory/1433/"))
        if group_milestone_history is not None:
            self.assertEqual(group_milestone_history.desc,         "Agreement on charter and issues in current draft.")
            self.assertEqual(group_milestone_history.docs,         [])
            self.assertEqual(group_milestone_history.due,          "1996-05-31")
            self.assertEqual(group_milestone_history.group,        GroupURI("/api/v1/group/group/1326/"))
            self.assertEqual(group_milestone_history.id,           1433)
            self.assertEqual(group_milestone_history.milestone,    GroupMilestoneURI("/api/v1/group/groupmilestone/2114/"))
            self.assertEqual(group_milestone_history.order,        None)
            self.assertEqual(group_milestone_history.resolved,     "Done")
            self.assertEqual(group_milestone_history.resource_uri, GroupMilestoneHistoryURI("/api/v1/group/groupmilestonehistory/1433/"))
            self.assertEqual(group_milestone_history.state,        GroupMilestoneStateNameURI("/api/v1/name/groupmilestonestatename/active/"))
            self.assertEqual(group_milestone_history.time,         datetime.fromisoformat("2013-05-20T15:42:45"))
        else:
            self.fail("Cannot find group milestone history")


    def test_group_milestone_histories(self) -> None:
        group_milestone_histories = self.dt.group_milestone_histories()
        self.assertIsNot(group_milestone_histories, None)


    def test_group_milestone_histories_group(self) -> None:
        group_milestone_histories = list(self.dt.group_milestone_histories(group=self.dt.group(GroupURI("/api/v1/group/group/1326/"))))
        self.assertEqual(len(group_milestone_histories), 35)


    def test_group_milestone_histories_milestone(self) -> None:
        group_milestone_histories = list(self.dt.group_milestone_histories(milestone=self.dt.group_milestone(GroupMilestoneURI("/api/v1/group/groupmilestone/2114"))))
        self.assertEqual(len(group_milestone_histories),  1)
        self.assertEqual(group_milestone_histories[0].id, 1433)


    def test_group_milestone_histories_state(self) -> None:
        group_milestone_histories = self.dt.group_milestone_histories(state=self.dt.group_milestone_statename(GroupMilestoneStateNameURI("/api/v1/name/groupmilestonestatename/active/")))
        self.assertIsNot(group_milestone_histories, None)


    def test_group_milestone_event(self) -> None:
        group_milestone_event = self.dt.group_milestone_event(GroupMilestoneEventURI("/api/v1/group/milestonegroupevent/16849/"))
        if group_milestone_event is not None:
            self.assertEqual(group_milestone_event.by,             PersonURI("/api/v1/person/person/108756/"))
            self.assertEqual(group_milestone_event.desc,           "Added milestone \"Submit data flow information model (informational)\", due 2020-04-30, from approved charter")
            self.assertEqual(group_milestone_event.group,          GroupURI("/api/v1/group/group/1962/"))
            self.assertEqual(group_milestone_event.groupevent_ptr, GroupEventURI("/api/v1/group/groupevent/16849/"))
            self.assertEqual(group_milestone_event.id,             16849)
            self.assertEqual(group_milestone_event.milestone,      GroupMilestoneURI("/api/v1/group/groupmilestone/8539/"))
            self.assertEqual(group_milestone_event.resource_uri,   GroupMilestoneEventURI("/api/v1/group/milestonegroupevent/16849/"))
            self.assertEqual(group_milestone_event.time,           datetime.fromisoformat("2020-04-20T13:31:48"))
            self.assertEqual(group_milestone_event.type,           "changed_milestone")
        else:
            self.fail("Cannot find group milestone event")


    def test_group_milestone_events(self) -> None:
        group_milestone_events = self.dt.group_milestone_events()
        self.assertIsNot(group_milestone_events, None)


    def test_group_milestone_events_by(self) -> None:
        group_milestone_events = self.dt.group_milestone_events(by=self.dt.person(PersonURI("/api/v1/person/person/108756/")))
        self.assertIsNot(group_milestone_events, None)


    def test_group_milestone_events_group(self) -> None:
        group_milestone_events = list(self.dt.group_milestone_events(group=self.dt.group(GroupURI("/api/v1/group/group/1326/"))))
        self.assertEqual(len(group_milestone_events), 46)


    def test_group_milestone_events_milestone(self) -> None:
        group_milestone_events = list(self.dt.group_milestone_events(milestone=self.dt.group_milestone(GroupMilestoneURI("/api/v1/group/groupmilestone/6489/"))))
        self.assertEqual(len(group_milestone_events),  3)
        self.assertEqual(group_milestone_events[0].id, 16331)
        self.assertEqual(group_milestone_events[1].id, 11947)
        self.assertEqual(group_milestone_events[2].id, 7224)


    def test_group_milestone_events_type(self) -> None:
        group_milestone_events = self.dt.group_milestone_events(type="changed_milestone")
        self.assertIsNot(group_milestone_events, None)


    def test_group_role_history(self) -> None:
        group_role_history = self.dt.group_role_history(GroupRoleHistoryURI("/api/v1/group/rolehistory/519/"))
        if group_role_history is not None:
            self.assertEqual(group_role_history.email,        EmailURI("/api/v1/person/email/csp@csperkins.org/"))
            self.assertEqual(group_role_history.group,        GroupHistoryURI("/api/v1/group/grouphistory/256/"))
            self.assertEqual(group_role_history.id,           519)
            self.assertEqual(group_role_history.name,         RoleNameURI("/api/v1/name/rolename/chair/"))
            self.assertEqual(group_role_history.person,       PersonURI("/api/v1/person/person/20209/"))
            self.assertEqual(group_role_history.resource_uri, GroupRoleHistoryURI("/api/v1/group/rolehistory/519/"))
        else:
            self.fail("Cannot find group role history")


    def test_group_role_histories(self) -> None:
        group_role_histories = self.dt.group_role_histories()
        self.assertIsNot(group_role_histories, None)


    def test_group_role_histories_email(self) -> None:
        group_role_histories = list(self.dt.group_role_histories(email="csp@csperkins.org"))
        self.assertEqual(len(group_role_histories), 25)


    def test_group_role_histories_group(self) -> None:
        group_role_histories = list(self.dt.group_role_histories(group=self.dt.group(GroupURI("/api/v1/group/group/1997/"))))
        self.assertEqual(len(group_role_histories), 4)
        self.assertEqual(group_role_histories[0].id, 4062)
        self.assertEqual(group_role_histories[1].id, 4063)
        self.assertEqual(group_role_histories[2].id, 4064)
        self.assertEqual(group_role_histories[3].id, 4065)


    def test_group_role_histories_name(self) -> None:
        group_role_histories = self.dt.group_role_histories(name=self.dt.role_name(RoleNameURI("/api/v1/name/rolename/chair/")))
        self.assertIsNot(group_role_histories, None)


    def test_group_role_histories_person(self) -> None:
        group_role_histories = list(self.dt.group_role_histories(person=self.dt.person(PersonURI("/api/v1/person/person/20209/"))))
        self.assertEqual(len(group_role_histories), 25)


    def test_groups_state(self) -> None:
        groups = list(self.dt.groups(state=self.dt.group_state(GroupStateURI("/api/v1/name/groupstatename/abandon"))))
        self.assertEqual(len(groups), 6)
        self.assertEqual(groups[0].id, 1949)
        self.assertEqual(groups[1].id, 2009)
        self.assertEqual(groups[2].id, 2018)
        self.assertEqual(groups[3].id, 2155)
        self.assertEqual(groups[4].id, 2190)
        self.assertEqual(groups[5].id, 2200)


    def test_groups_parent(self) -> None:
        groups = list(self.dt.groups(parent=self.dt.group(GroupURI("/api/v1/group/group/1/"))))
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0].id, 2)
        self.assertEqual(groups[1].id, 2225)


    def test_group_state(self) -> None:
        state = self.dt.group_state(GroupStateURI("/api/v1/name/groupstatename/abandon"))
        if state is not None:
            self.assertEqual(state.desc,         "Formation of the group (most likely a BoF or Proposed WG) was abandoned")
            self.assertEqual(state.name,         "Abandoned")
            self.assertEqual(state.order,        0)
            self.assertEqual(state.resource_uri, GroupStateURI("/api/v1/name/groupstatename/abandon/"))
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


    # -----------------------------------------------------------------------------------------------------------------------------
    # Tests relating to meetings:

    def test_meeting_schedule(self) -> None:
        schedule = self.dt.meeting_schedule(ScheduleURI("/api/v1/meeting/schedule/209/"))
        if schedule is not None:
            self.assertEqual(schedule.id,           209)
            self.assertEqual(schedule.resource_uri, ScheduleURI("/api/v1/meeting/schedule/209/"))
            self.assertEqual(schedule.meeting,      MeetingURI("/api/v1/meeting/meeting/365/"))
            self.assertEqual(schedule.owner,        PersonURI("/api/v1/person/person/109129/"))
            self.assertEqual(schedule.name,         "prelim-fix")
            self.assertEqual(schedule.visible,      True)
            self.assertEqual(schedule.public,       True)
            self.assertEqual(schedule.badness,      None)
        else:
            self.fail("cannot find meeting schedule")


    def test_meeting_session_assignment(self) -> None:
        assignment = self.dt.meeting_session_assignment(SessionAssignmentURI("/api/v1/meeting/schedtimesessassignment/61212/"))
        if assignment is not None:
            self.assertEqual(assignment.id,           61212)
            self.assertEqual(assignment.modified,     datetime.fromisoformat("2017-10-17T12:14:33"))
            self.assertEqual(assignment.extendedfrom, None)
            self.assertEqual(assignment.timeslot,     TimeslotURI("/api/v1/meeting/timeslot/9132/"))
            self.assertEqual(assignment.session,      SessionURI("/api/v1/meeting/session/25907/"))
            self.assertEqual(assignment.agenda,       ScheduleURI("/api/v1/meeting/schedule/787/"))
            self.assertEqual(assignment.schedule,     ScheduleURI("/api/v1/meeting/schedule/787/"))
            self.assertEqual(assignment.pinned,       False)
            self.assertEqual(assignment.resource_uri, SessionAssignmentURI("/api/v1/meeting/schedtimesessassignment/61212/"))
            self.assertEqual(assignment.badness,      0)
            self.assertEqual(assignment.notes, "")
        else:
            self.fail("cannot find meeting session assignment")


    def test_meeting_session_assignments(self) -> None:
        meeting  = self.dt.meeting(MeetingURI("/api/v1/meeting/meeting/365/")) # IETF 90 in Toronto
        if meeting is not None:
            schedule = self.dt.meeting_schedule(meeting.schedule)
            if schedule is not None:
                assignments = list(self.dt.meeting_session_assignments(schedule))
                self.assertEqual(len(assignments), 161)
            else:
                self.fail("Cannot find schedule")
        else:
            self.fail("Cannot find meeting")


    def test_meeting(self) -> None:
        meeting = self.dt.meeting(MeetingURI("/api/v1/meeting/meeting/365/"))
        if meeting is not None:
            self.assertEqual(meeting.id,                               365)
            self.assertEqual(meeting.resource_uri,                     MeetingURI("/api/v1/meeting/meeting/365/"))
            self.assertEqual(meeting.type,                             MeetingTypeURI("/api/v1/name/meetingtypename/ietf/"))
            self.assertEqual(meeting.city,                             "Toronto")
            self.assertEqual(meeting.country,                          "CA")
            self.assertEqual(meeting.venue_name,                       "Fairmont Royal York Hotel")
            self.assertEqual(meeting.venue_addr,                       "100 Front Street W\r\nToronto, Ontario, Canada M5J 1E3")
            self.assertEqual(meeting.date,                             "2014-07-20")
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
            self.assertEqual(meeting.updated,                          datetime.fromisoformat("2016-12-22T09:57:15-08:00"))
            self.assertEqual(meeting.agenda,                           ScheduleURI("/api/v1/meeting/schedule/209/"))
            self.assertEqual(meeting.schedule,                         ScheduleURI("/api/v1/meeting/schedule/209/"))
            self.assertEqual(meeting.number,                           "90")
            self.assertEqual(meeting.proceedings_final,                False)
            self.assertEqual(meeting.acknowledgements,                 "")
        else:
            self.fail("Cannot find meeting")


    def test_meetings(self) -> None:
        meetings = list(self.dt.meetings(start_date="2019-01-01", end_date="2019-12-31", meeting_type=self.dt.meeting_type("ietf")))
        self.assertEqual(len(meetings),  3)
        self.assertEqual(meetings[0].city, "Singapore")
        self.assertEqual(meetings[1].city, "Montreal")
        self.assertEqual(meetings[2].city, "Prague")


    def test_meeting_types(self) -> None:
        types = list(self.dt.meeting_types())
        self.assertEqual(len(types),  2)
        self.assertEqual(types[0].slug, "ietf")
        self.assertEqual(types[1].slug, "interim")


    @patch.object(ietfdata.datatracker, 'datetime', Mock(wraps=datetime))
    def test_meeting_status_future(self) -> None:
        meeting = self.dt.meeting(MeetingURI("/api/v1/meeting/meeting/365/"))
        if meeting is not None:
            ietfdata.datatracker.datetime.now.return_value = datetime(2014, 1, 1) # type: ignore
            self.assertEqual(meeting.status(), MeetingStatus.FUTURE)
        else:
            self.fail("Cannot find meeting")


    @patch.object(ietfdata.datatracker, 'datetime', Mock(wraps=datetime))
    def test_meeting_status_completed(self) -> None:
        meeting = self.dt.meeting(MeetingURI("/api/v1/meeting/meeting/365/"))
        if meeting is not None:
            ietfdata.datatracker.datetime.now.return_value = datetime(2014, 12, 1) # type: ignore
            self.assertEqual(meeting.status(), MeetingStatus.COMPLETED)
        else:
            self.fail("Cannot find meeting")


    @patch.object(ietfdata.datatracker, 'datetime', Mock(wraps=datetime))
    def test_meeting_status_ongoing(self) -> None:
        meeting = self.dt.meeting(MeetingURI("/api/v1/meeting/meeting/365/"))
        if meeting is not None:
            ietfdata.datatracker.datetime.now.return_value = datetime(2014, 7, 20) # type: ignore
            self.assertEqual(meeting.status(), MeetingStatus.ONGOING)
        else:
            self.fail("Cannot find meeting")


    # -----------------------------------------------------------------------------------------------------------------------------
    # Tests relating to related documents:

    def test_related_documents_all(self) -> None:
        source = self.dt.document(DocumentURI("/api/v1/doc/document/draft-rfced-info-snpp-v3/"))
        target = list(self.dt.docaliases_from_name("draft-gwinn-paging-protocol-v3"))[0]
        rel    = self.dt.relationship_type(RelationshipTypeURI("/api/v1/name/docrelationshipname/replaces/"))
        rdocs  = list(self.dt.related_documents(source=source, target=target, relationship_type=rel))
        self.assertEqual(len(rdocs), 1)
        self.assertEqual(rdocs[0].id, 3)
        self.assertEqual(rdocs[0].relationship, RelationshipTypeURI("/api/v1/name/docrelationshipname/replaces/"))
        self.assertEqual(rdocs[0].resource_uri, RelatedDocumentURI("/api/v1/doc/relateddocument/3/"))
        self.assertEqual(rdocs[0].source,       DocumentURI("/api/v1/doc/document/draft-rfced-info-snpp-v3/"))
        self.assertEqual(rdocs[0].target,       DocumentAliasURI("/api/v1/doc/docalias/draft-gwinn-paging-protocol-v3/"))


    def test_related_documents_source_target(self) -> None:
        source = self.dt.document(DocumentURI("/api/v1/doc/document/draft-rfced-info-snpp-v3/"))
        target = list(self.dt.docaliases_from_name("draft-gwinn-paging-protocol-v3"))[0]
        rdocs  = list(self.dt.related_documents(source=source, target=target))
        self.assertEqual(len(rdocs), 1)
        self.assertEqual(rdocs[0].id, 3)
        self.assertEqual(rdocs[0].relationship, RelationshipTypeURI("/api/v1/name/docrelationshipname/replaces/"))
        self.assertEqual(rdocs[0].resource_uri, RelatedDocumentURI("/api/v1/doc/relateddocument/3/"))
        self.assertEqual(rdocs[0].source,       DocumentURI("/api/v1/doc/document/draft-rfced-info-snpp-v3/"))
        self.assertEqual(rdocs[0].target,       DocumentAliasURI("/api/v1/doc/docalias/draft-gwinn-paging-protocol-v3/"))


    def test_related_documents_source_relationship(self) -> None:
        source = self.dt.document(DocumentURI("/api/v1/doc/document/draft-rfced-info-snpp-v3/"))
        rel    = self.dt.relationship_type(RelationshipTypeURI("/api/v1/name/docrelationshipname/replaces/"))
        rdocs  = list(self.dt.related_documents(source=source, relationship_type=rel))
        self.assertEqual(len(rdocs), 1)
        self.assertEqual(rdocs[0].id, 3)
        self.assertEqual(rdocs[0].relationship, RelationshipTypeURI("/api/v1/name/docrelationshipname/replaces/"))
        self.assertEqual(rdocs[0].resource_uri, RelatedDocumentURI("/api/v1/doc/relateddocument/3/"))
        self.assertEqual(rdocs[0].source,       DocumentURI("/api/v1/doc/document/draft-rfced-info-snpp-v3/"))
        self.assertEqual(rdocs[0].target,       DocumentAliasURI("/api/v1/doc/docalias/draft-gwinn-paging-protocol-v3/"))


    def test_related_documents_target_relationship(self) -> None:
        target = list(self.dt.docaliases_from_name("draft-gwinn-paging-protocol-v3"))[0]
        rel    = self.dt.relationship_type(RelationshipTypeURI("/api/v1/name/docrelationshipname/replaces/"))
        rdocs  = list(self.dt.related_documents(target=target, relationship_type=rel))
        self.assertEqual(len(rdocs), 1)
        self.assertEqual(rdocs[0].id, 3)
        self.assertEqual(rdocs[0].relationship, RelationshipTypeURI("/api/v1/name/docrelationshipname/replaces/"))
        self.assertEqual(rdocs[0].resource_uri, RelatedDocumentURI("/api/v1/doc/relateddocument/3/"))
        self.assertEqual(rdocs[0].source,       DocumentURI("/api/v1/doc/document/draft-rfced-info-snpp-v3/"))
        self.assertEqual(rdocs[0].target,       DocumentAliasURI("/api/v1/doc/docalias/draft-gwinn-paging-protocol-v3/"))


    def test_related_documents_target(self) -> None:
        target = list(self.dt.docaliases_from_name("draft-gwinn-paging-protocol-v3"))[0]
        rdocs  = list(self.dt.related_documents(target=target))
        self.assertEqual(len(rdocs), 1)
        self.assertEqual(rdocs[0].id, 3)
        self.assertEqual(rdocs[0].relationship, RelationshipTypeURI("/api/v1/name/docrelationshipname/replaces/"))
        self.assertEqual(rdocs[0].resource_uri, RelatedDocumentURI("/api/v1/doc/relateddocument/3/"))
        self.assertEqual(rdocs[0].source,       DocumentURI("/api/v1/doc/document/draft-rfced-info-snpp-v3/"))
        self.assertEqual(rdocs[0].target,       DocumentAliasURI("/api/v1/doc/docalias/draft-gwinn-paging-protocol-v3/"))


    def test_related_documents_source(self) -> None:
        source = self.dt.document(DocumentURI("/api/v1/doc/document/draft-rfced-info-snpp-v3/"))
        rdocs  = list(self.dt.related_documents(source=source))
        self.assertEqual(len(rdocs), 6)
        self.assertEqual(rdocs[0].id, 3)
        self.assertEqual(rdocs[0].relationship, RelationshipTypeURI("/api/v1/name/docrelationshipname/replaces/"))
        self.assertEqual(rdocs[0].resource_uri, RelatedDocumentURI("/api/v1/doc/relateddocument/3/"))
        self.assertEqual(rdocs[0].source,       DocumentURI("/api/v1/doc/document/draft-rfced-info-snpp-v3/"))
        self.assertEqual(rdocs[0].target,       DocumentAliasURI("/api/v1/doc/docalias/draft-gwinn-paging-protocol-v3/"))
        self.assertEqual(rdocs[1].id, 2059)
        self.assertEqual(rdocs[1].relationship, RelationshipTypeURI("/api/v1/name/docrelationshipname/obs/"))
        self.assertEqual(rdocs[1].resource_uri, RelatedDocumentURI("/api/v1/doc/relateddocument/2059/"))
        self.assertEqual(rdocs[1].source,       DocumentURI("/api/v1/doc/document/draft-rfced-info-snpp-v3/"))
        self.assertEqual(rdocs[1].target,       DocumentAliasURI("/api/v1/doc/docalias/rfc1645/"))
        self.assertEqual(rdocs[2].id, 10230)
        self.assertEqual(rdocs[2].relationship, RelationshipTypeURI("/api/v1/name/docrelationshipname/refold/"))
        self.assertEqual(rdocs[2].resource_uri, RelatedDocumentURI("/api/v1/doc/relateddocument/10230/"))
        self.assertEqual(rdocs[2].source,       DocumentURI("/api/v1/doc/document/draft-rfced-info-snpp-v3/"))
        self.assertEqual(rdocs[2].target,       DocumentAliasURI("/api/v1/doc/docalias/rfc1425/"))
        self.assertEqual(rdocs[3].id, 10231)
        self.assertEqual(rdocs[3].relationship, RelationshipTypeURI("/api/v1/name/docrelationshipname/refold/"))
        self.assertEqual(rdocs[3].resource_uri, RelatedDocumentURI("/api/v1/doc/relateddocument/10231/"))
        self.assertEqual(rdocs[3].source,       DocumentURI("/api/v1/doc/document/draft-rfced-info-snpp-v3/"))
        self.assertEqual(rdocs[3].target,       DocumentAliasURI("/api/v1/doc/docalias/rfc1521/"))
        self.assertEqual(rdocs[4].id, 10233)
        self.assertEqual(rdocs[4].relationship, RelationshipTypeURI("/api/v1/name/docrelationshipname/refold/"))
        self.assertEqual(rdocs[4].resource_uri, RelatedDocumentURI("/api/v1/doc/relateddocument/10233/"))
        self.assertEqual(rdocs[4].source,       DocumentURI("/api/v1/doc/document/draft-rfced-info-snpp-v3/"))
        self.assertEqual(rdocs[4].target,       DocumentAliasURI("/api/v1/doc/docalias/std10/"))
        self.assertEqual(rdocs[5].id, 10234)
        self.assertEqual(rdocs[5].relationship, RelationshipTypeURI("/api/v1/name/docrelationshipname/refold/"))
        self.assertEqual(rdocs[5].resource_uri, RelatedDocumentURI("/api/v1/doc/relateddocument/10234/"))
        self.assertEqual(rdocs[5].source,       DocumentURI("/api/v1/doc/document/draft-rfced-info-snpp-v3/"))
        self.assertEqual(rdocs[5].target,       DocumentAliasURI("/api/v1/doc/docalias/rfc1486/"))


    def test_related_documents_relationship(self) -> None:
        rel    = self.dt.relationship_type(RelationshipTypeURI("/api/v1/name/docrelationshipname/replaces/"))
        rdocs  = self.dt.related_documents(relationship_type=rel)
        self.assertIsNot(rdocs, None)


    def test_relationship_types(self) -> None:
        types = list(self.dt.relationship_types())
        self.assertEqual(len(types), 16)
        self.assertEqual(types[0].slug,  "downref-approval")
        self.assertEqual(types[1].slug,  "conflrev")
        self.assertEqual(types[2].slug,  "refinfo")
        self.assertEqual(types[3].slug,  "tobcp")
        self.assertEqual(types[4].slug,  "toexp")
        self.assertEqual(types[5].slug,  "tohist")
        self.assertEqual(types[6].slug,  "toinf")
        self.assertEqual(types[7].slug,  "tois")
        self.assertEqual(types[8].slug,  "tops")
        self.assertEqual(types[9].slug,  "refnorm")
        self.assertEqual(types[10].slug, "obs")
        self.assertEqual(types[11].slug, "possibly-replaces")
        self.assertEqual(types[12].slug, "refold")
        self.assertEqual(types[13].slug, "replaces")
        self.assertEqual(types[14].slug, "updates")
        self.assertEqual(types[15].slug, "refunk")


    def test_mailing_list(self) -> None:
        ml = self.dt.mailing_list(MailingListURI("/api/v1/mailinglists/list/461/"))
        if ml is not None:
            self.assertEqual(ml.id,           461)
            self.assertEqual(ml.resource_uri, MailingListURI("/api/v1/mailinglists/list/461/"))
            self.assertEqual(ml.name,         "hackathon")
            self.assertEqual(ml.description,  "Discussion regarding past, present, and future IETF hackathons.")
            self.assertEqual(ml.advertised,   True)
        else:
            self.fail("Cannot find mailing list")


    def test_mailing_lists(self) -> None:
        ml = list(self.dt.mailing_lists())
        if ml is not None:
            self.assertNotEqual(len(ml), 0)
        else:
            self.fail("Cannot find mailing lists")


    def test_mailing_list_subscriptions(self) -> None:
        subs = list(self.dt.mailing_list_subscriptions("colin.perkins@glasgow.ac.uk"))
        self.assertEqual(len(subs), 1)
        self.assertEqual(subs[0].id,           66700)
        self.assertEqual(subs[0].resource_uri, MailingListSubscriptionsURI(uri="/api/v1/mailinglists/subscribed/66700/"))
        self.assertEqual(subs[0].email,        "colin.perkins@glasgow.ac.uk")
        self.assertEqual(subs[0].lists[0],     MailingListURI("/api/v1/mailinglists/list/461/"))


if __name__ == '__main__':
    unittest.main()

# =================================================================================================================================
# vim: set tw=0 ai:
