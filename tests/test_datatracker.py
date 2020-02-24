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

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ietfdata.datatracker import *

# =================================================================================================================================
# Unit tests:

class TestDatatracker(unittest.TestCase):
    dt : DataTracker

    # -----------------------------------------------------------------------------------------------------------------------------
    # Tests relating to email addresses:

    @classmethod
    def setUpClass(self) -> None:
        self.dt = DataTracker()

    def test_email(self) -> None:
        e  = self.dt.email(EmailURI("/api/v1/person/email/csp@csperkins.org"))
        if e is not None:
            self.assertEqual(e.resource_uri, EmailURI("/api/v1/person/email/csp@csperkins.org/"))
            self.assertEqual(e.address,      "csp@csperkins.org")
            self.assertEqual(e.person,       PersonURI("/api/v1/person/person/20209/"))
            self.assertEqual(e.time,         "1970-01-01T23:59:59")
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
        self.assertEqual(h[0].time,         "2012-02-26T00:46:44")
        self.assertEqual(h[0].active,       False)
        self.assertEqual(h[0].primary,      False)
        self.assertEqual(h[0].history_id,   71987)
        self.assertEqual(h[0].history_date, "2019-09-29T14:39:48.385541")
        self.assertEqual(h[0].history_type, "~")
        self.assertEqual(h[0].history_user, "")
        self.assertEqual(h[0].history_change_reason, None)

        self.assertEqual(h[1].resource_uri, EmailURI("/api/v1/person/historicalemail/2090/"))
        self.assertEqual(h[1].address,      "csp@isi.edu")
        self.assertEqual(h[1].person,       PersonURI("/api/v1/person/person/20209/"))
        self.assertEqual(h[1].origin,       "author: draft-ietf-avt-rtptest")
        self.assertEqual(h[1].time,         "2012-02-26T00:46:44")
        self.assertEqual(h[1].active,       False)
        self.assertEqual(h[1].primary,      False)
        self.assertEqual(h[1].history_id,   2090)
        self.assertEqual(h[1].history_date, "2018-06-19T15:39:40.008875")
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
        e = list(self.dt.emails(since="2018-04-01T00:00:00", until="2018-04-30T23:59:59"))
        self.assertEqual(len(e), 32)
        self.assertEqual(e[ 0].resource_uri, EmailURI('/api/v1/person/email/jeromee.marcon@free.fr/'))
        self.assertEqual(e[ 1].resource_uri, EmailURI('/api/v1/person/email/to-niwa@kddi.com/'))
        self.assertEqual(e[ 2].resource_uri, EmailURI('/api/v1/person/email/lucaspardue.24.7@gmail.com/'))
        self.assertEqual(e[ 3].resource_uri, EmailURI('/api/v1/person/email/eagros@dolby.com/'))
        self.assertEqual(e[ 4].resource_uri, EmailURI('/api/v1/person/email/loghyr@hammer.space/'))
        self.assertEqual(e[ 5].resource_uri, EmailURI('/api/v1/person/email/abashandy.ietf@gmail.com/'))
        self.assertEqual(e[ 6].resource_uri, EmailURI('/api/v1/person/email/nasimparvez21@gmail.com/'))
        self.assertEqual(e[ 7].resource_uri, EmailURI('/api/v1/person/email/bkaduk@akamai.com/'))
        self.assertEqual(e[ 8].resource_uri, EmailURI('/api/v1/person/email/16111011@bjtu.edu.cn/'))
        self.assertEqual(e[ 9].resource_uri, EmailURI('/api/v1/person/email/bhfeng@bjtu.edu.cn/'))
        self.assertEqual(e[10].resource_uri, EmailURI('/api/v1/person/email/kouhei@chromium.org/'))
        self.assertEqual(e[11].resource_uri, EmailURI('/api/v1/person/email/christian.grothoff@bfh.ch/'))
        self.assertEqual(e[12].resource_uri, EmailURI('/api/v1/person/email/unknown-email-Nikos-Triantafillis/'))
        self.assertEqual(e[13].resource_uri, EmailURI('/api/v1/person/email/nikos@linkedin.com/'))
        self.assertEqual(e[14].resource_uri, EmailURI('/api/v1/person/email/ccassar@tesla.com/'))
        self.assertEqual(e[15].resource_uri, EmailURI('/api/v1/person/email/benjamin.phister@op3ft.org/'))
        self.assertEqual(e[16].resource_uri, EmailURI('/api/v1/person/email/jean-emmanuel.rodriguez@op3ft.org/'))
        self.assertEqual(e[17].resource_uri, EmailURI('/api/v1/person/email/simon.perreault@logmein.com/'))
        self.assertEqual(e[18].resource_uri, EmailURI('/api/v1/person/email/brian@trammell.ch/'))
        self.assertEqual(e[19].resource_uri, EmailURI('/api/v1/person/email/oyvind.ronningstad@nordicsemi.no/'))
        self.assertEqual(e[20].resource_uri, EmailURI('/api/v1/person/email/zs_yolanda@163.com/'))
        self.assertEqual(e[21].resource_uri, EmailURI('/api/v1/person/email/18810320812@163.com/'))
        self.assertEqual(e[22].resource_uri, EmailURI('/api/v1/person/email/190449115@qq.com/'))
        self.assertEqual(e[23].resource_uri, EmailURI('/api/v1/person/email/smd@simplemetadata.org/'))
        self.assertEqual(e[24].resource_uri, EmailURI('/api/v1/person/email/michael.slusarz@open-xchange.com/'))
        self.assertEqual(e[25].resource_uri, EmailURI('/api/v1/person/email/unknown-email-Giorgio-Campo/'))
        self.assertEqual(e[26].resource_uri, EmailURI('/api/v1/person/email/security@paragonie.com/'))
        self.assertEqual(e[27].resource_uri, EmailURI('/api/v1/person/email/hausss@rpi.edu/'))
        self.assertEqual(e[28].resource_uri, EmailURI('/api/v1/person/email/daniel@kais3r.de/'))
        self.assertEqual(e[29].resource_uri, EmailURI('/api/v1/person/email/farhadiba44@gmail.com/'))
        self.assertEqual(e[30].resource_uri, EmailURI('/api/v1/person/email/lee.howard@retevia.net/'))
        self.assertEqual(e[31].resource_uri, EmailURI('/api/v1/person/email/yolanda.xia@huawei.com/'))

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
            self.assertEqual(p.time,            "2012-02-26T00:03:54")
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
            self.assertEqual(p.time,            "2012-02-26T00:03:54")
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
            self.assertEqual(h[0].time,            "2012-02-26T00:03:54")
            self.assertEqual(h[0].photo,           "photo/Colin-Perkins-sm.jpg")
            self.assertEqual(h[0].photo_thumb,     "photo/Colin-Perkins-sm_PMIAhXi.jpg")
            # self.assertEqual(h[0].biography,     "Colin Perkins is a ...")
            self.assertEqual(h[0].consent,         True)
            self.assertEqual(h[0].history_change_reason, None)
            self.assertEqual(h[0].history_user,    "")
            self.assertEqual(h[0].history_id,      11731)
            self.assertEqual(h[0].history_type,    "~")
            self.assertEqual(h[0].history_date,    "2019-09-29T14:39:48.278674")

            self.assertEqual(h[1].id,              20209)
            self.assertEqual(h[1].resource_uri,    PersonURI("/api/v1/person/historicalperson/10878/"))
            self.assertEqual(h[1].name,            "Colin Perkins")
            self.assertEqual(h[1].name_from_draft, "Colin Perkins")
            self.assertEqual(h[1].ascii,           "Colin Perkins")
            self.assertEqual(h[1].ascii_short,     None)
            self.assertEqual(h[1].user,            "")
            self.assertEqual(h[1].time,            "2012-02-26T00:03:54")
            self.assertEqual(h[1].photo,           "photo/Colin-Perkins-sm.jpg")
            self.assertEqual(h[1].photo_thumb,     "photo/Colin-Perkins-sm_PMIAhXi.jpg")
            # self.assertEqual(h[1].biography,     "Colin Perkins is a ...")
            self.assertEqual(h[1].consent,         True)
            self.assertEqual(h[1].history_change_reason, None)
            self.assertEqual(h[1].history_user,    "")
            self.assertEqual(h[1].history_id,      10878)
            self.assertEqual(h[1].history_type,    "~")
            self.assertEqual(h[1].history_date,    "2019-03-29T02:44:28.426049")

            self.assertEqual(h[2].id,              20209)
            self.assertEqual(h[2].resource_uri,    PersonURI("/api/v1/person/historicalperson/127/"))
            self.assertEqual(h[2].name,            "Colin Perkins")
            self.assertEqual(h[2].name_from_draft, "Colin Perkins")
            self.assertEqual(h[2].ascii,           "Colin Perkins")
            self.assertEqual(h[2].ascii_short,     "")
            self.assertEqual(h[2].user,            "")
            self.assertEqual(h[2].time,            "2012-02-26T00:03:54")
            self.assertEqual(h[2].photo,           "")
            self.assertEqual(h[2].photo_thumb,     "")
            self.assertEqual(h[2].biography,       "")
            self.assertEqual(h[2].consent,         True)
            self.assertEqual(h[2].history_change_reason, None)
            self.assertEqual(h[2].history_user,    "")
            self.assertEqual(h[2].history_id,      127)
            self.assertEqual(h[2].history_type,    "~")
            self.assertEqual(h[2].history_date,    "2018-06-19T15:39:39.929158")
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
            self.assertEqual(events[0].time,         "2018-09-24T09:28:32.502465")
            self.assertEqual(events[0].type,         "gdpr_notice_email")
        else:
            self.fail("Cannot find person")


    def test_people(self) -> None:
        p  = list(self.dt.people(since="2018-04-01T00:00:00", until="2018-04-30T23:59:59"))
        self.assertEqual(len(p), 17)
        self.assertEqual(p[ 0].resource_uri, PersonURI("/api/v1/person/person/124773/"))
        self.assertEqual(p[ 1].resource_uri, PersonURI("/api/v1/person/person/124759/"))
        self.assertEqual(p[ 2].resource_uri, PersonURI("/api/v1/person/person/124760/"))
        self.assertEqual(p[ 3].resource_uri, PersonURI("/api/v1/person/person/124763/"))
        self.assertEqual(p[ 4].resource_uri, PersonURI("/api/v1/person/person/124765/"))
        self.assertEqual(p[ 5].resource_uri, PersonURI("/api/v1/person/person/124766/"))
        self.assertEqual(p[ 6].resource_uri, PersonURI("/api/v1/person/person/124767/"))
        self.assertEqual(p[ 7].resource_uri, PersonURI("/api/v1/person/person/124768/"))
        self.assertEqual(p[ 8].resource_uri, PersonURI("/api/v1/person/person/124769/"))
        self.assertEqual(p[ 9].resource_uri, PersonURI("/api/v1/person/person/124770/"))
        self.assertEqual(p[10].resource_uri, PersonURI("/api/v1/person/person/124771/"))
        self.assertEqual(p[11].resource_uri, PersonURI("/api/v1/person/person/124772/"))
        self.assertEqual(p[12].resource_uri, PersonURI("/api/v1/person/person/124774/"))
        self.assertEqual(p[13].resource_uri, PersonURI("/api/v1/person/person/124775/"))
        self.assertEqual(p[14].resource_uri, PersonURI("/api/v1/person/person/124776/"))
        self.assertEqual(p[15].resource_uri, PersonURI("/api/v1/person/person/124779/"))
        self.assertEqual(p[16].resource_uri, PersonURI("/api/v1/person/person/124780/"))


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
            self.assertEqual(d.time,               "2014-07-21T11:14:17")
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

            url = d.document_url()
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
            self.assertEqual(d.time,               "2016-08-22T05:39:08")
            self.assertEqual(d.pages,              None)
            self.assertEqual(d.stream,             None)
            self.assertEqual(d.std_level,          None)
            self.assertEqual(d.states,             [DocumentStateURI("/api/v1/doc/state/139/")])

            url = d.document_url()
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
            self.assertEqual(d.time,               "1998-01-26T12:00:00")
            self.assertEqual(d.pages,              None)
            self.assertEqual(d.stream,             None)
            self.assertEqual(d.std_level,          None)
            self.assertEqual(d.states,             [DocumentStateURI("/api/v1/doc/state/88/")])

            url = d.document_url()
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
            self.assertEqual(d.time,               "2013-07-15T14:47:31")
            self.assertEqual(d.pages,              None)
            self.assertEqual(d.stream,             StreamURI("/api/v1/name/streamname/ietf/"))
            self.assertEqual(d.std_level,          None)
            self.assertEqual(d.states,             [DocumentStateURI("/api/v1/doc/state/97/")])

            url = d.document_url()
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
            self.assertEqual(d.time,               "2015-10-14T13:49:52")
            self.assertEqual(d.pages,              104)
            self.assertEqual(d.stream,             StreamURI("/api/v1/name/streamname/ietf/"))
            self.assertEqual(d.std_level,          "/api/v1/name/stdlevelname/std/")
            self.assertEqual(d.states,             [DocumentStateURI("/api/v1/doc/state/3/"), DocumentStateURI("/api/v1/doc/state/7/")])

            url = d.document_url()
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
            self.assertEqual(d.time,               "2012-06-04T08:20:38")
            self.assertEqual(d.pages,              None)
            self.assertEqual(d.stream,             None)
            self.assertEqual(d.std_level,          None)
            self.assertEqual(d.states,             [])

            url = d.document_url()
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
            self.assertEqual(d.time,               "2004-08-23T00:00:00")
            self.assertEqual(d.pages,              None)
            self.assertEqual(d.stream,             None)
            self.assertEqual(d.std_level,          None)
            self.assertEqual(d.states,             [])

            url = d.document_url()
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
            self.assertEqual(d.time,               "2014-04-09T08:09:14")
            self.assertEqual(d.pages,              None)
            self.assertEqual(d.stream,             None)
            self.assertEqual(d.std_level,          None)
            self.assertEqual(d.states,             [DocumentStateURI("/api/v1/doc/state/79/")])

            url = d.document_url()
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
            self.assertEqual(d.time,               "2015-11-24T08:23:42")
            self.assertEqual(d.pages,              None)
            self.assertEqual(d.stream,             None)
            self.assertEqual(d.std_level,          None)
            self.assertEqual(d.states,             [DocumentStateURI("/api/v1/doc/state/135/")])

            url = d.document_url()
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
            self.assertEqual(d.time,               "2017-02-28T12:52:33")
            self.assertEqual(d.pages,              None)
            self.assertEqual(d.stream,             None)
            self.assertEqual(d.std_level,          None)
            self.assertEqual(d.states,             [DocumentStateURI("/api/v1/doc/state/143/")])

            url = d.document_url()
            self.assertEqual(url, "https://datatracker.ietf.org/doc/review-bchv-rfc6890bis-04-genart-lc-kyzivat-2017-02-28")
            self.assertEqual(self.dt.session.get(url).status_code, 200)
        else:
            self.fail("Cannot find document")


    def test_document_shepwrit(self) -> None:
        for d in self.dt.documents(doctype=self.dt.document_type("shepwrit")):
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
            self.assertEqual(d.time,               "2006-04-07T17:30:22")
            self.assertEqual(d.pages,              None)
            self.assertEqual(d.stream,             None)
            self.assertEqual(d.std_level,          None)
            self.assertEqual(d.states,             [DocumentStateURI("/api/v1/doc/state/141/"), DocumentStateURI("/api/v1/doc/state/138/")])

            url = d.document_url()
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
            self.assertEqual(d.time,               "2017-08-21T09:32:46")
            self.assertEqual(d.pages,              None)
            self.assertEqual(d.stream,             StreamURI("/api/v1/name/streamname/ietf/"))
            self.assertEqual(d.std_level,          None)
            self.assertEqual(d.states,             [DocumentStateURI("/api/v1/doc/state/127/")])

            url = d.document_url()
            self.assertEqual(url, "https://www.ietf.org/sc/status-change-rfc3044-rfc3187-orig-urn-regs-to-historic-00.txt")
            self.assertEqual(self.dt.session.get(url).status_code, 200)
        else:
            self.fail("Cannot find document")



    # FIXME: this needs to be updated
#    def test_documents(self):
#        documents = list(self.dt.documents(since="2007-01-01T00:00:00", until="2007-12-31T23:59:59", doctype="draft", group="941"))


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

    # FIXME: this needs to be updated
    def test_document_state(self) -> None:
        s = self.dt.document_state(DocumentStateURI('/api/v1/doc/state/7/'))
        if s is not None:
            self.assertEqual(s.desc,         'The ID has been published as an RFC.')
            self.assertEqual(s.id,           7)
            self.assertEqual(s.name,         'RFC Published')
            self.assertEqual(s.next_states,  [DocumentStateURI('/api/v1/doc/state/8/')])
            self.assertEqual(s.order,        32)
            self.assertEqual(s.resource_uri, DocumentStateURI('/api/v1/doc/state/7/'))
            self.assertEqual(s.slug,         'pub')
            self.assertEqual(s.type,         DocumentStateTypeURI('/api/v1/doc/statetype/draft-iesg/'))
            self.assertEqual(s.used,         True)
        else:
            self.fail("Cannot find state")

    # FIXME: this needs to be updated
    def test_document_states(self) -> None:
        states = list(self.dt.document_states(statetype="draft-rfceditor"))
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

    # FIXME: this needs to be updated
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
            self.assertEqual(e.by,              PersonURI("/api/v1/person/person/121595/"))
            self.assertEqual(e.desc,            "New version available: <b>draft-irtf-cfrg-randomness-improvements-09.txt</b>")
            self.assertEqual(e.doc,             DocumentURI("/api/v1/doc/document/draft-irtf-cfrg-randomness-improvements/"))
            self.assertEqual(e.id,              729040)
            self.assertEqual(e.resource_uri,    DocumentEventURI("/api/v1/doc/docevent/729040/"))
            self.assertEqual(e.rev,             "09")
            self.assertEqual(e.time,            "2020-01-27T06:41:36")
            self.assertEqual(e.type,            "new_revision")
        else:
            self.fail("Cannot find event")


    # FIXME: this needs to be updated
    def test_document_events(self) -> None:
        pass



    # FIXME: this needs to be updated
    def test_submission(self) -> None:
        s  = self.dt.submission(SubmissionURI("/api/v1/submit/submission/2402/"))
        if s is not None:
            #self.assertEqual(s.abstract,        "Internet technical specifications often need to...")
            self.assertEqual(s.access_key,      "f77d08da6da54f3cbecca13d31646be8")
            self.assertEqual(s.auth_key,        "fMm6hur5dJ7gV58x5SE0vkHUoDOrSuSF")
            self.assertEqual(s.authors,         "[{'email': 'dcrocker@bbiw.net', 'name': 'Dave Crocker'}, {'email': 'paul.overell@thus.net', 'name': 'Paul Overell'}]")
            self.assertEqual(s.checks,          ["/api/v1/submit/submissioncheck/386/"])
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

    # FIXME: this needs to be updated
    def test_document_type(self) -> None:
        doctype = self.dt.document_type("draft")
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
            self.assertEqual(group.state,          "/api/v1/name/groupstatename/conclude/")
            self.assertEqual(group.time,           "2011-12-09T12:00:00")
            self.assertEqual(group.type,           "/api/v1/name/grouptypename/wg/")
            self.assertEqual(group.unused_states,  [])
            self.assertEqual(group.unused_tags,    [])
        else:
            self.fail("Cannot find group")

    # FIXME: this needs to be updated
    def test_group_from_acronym(self) -> None:
        group = self.dt.group_from_acronym("avt")
        if group is not None:
            self.assertEqual(group.id, 941)
        else:
            self.fail("Cannot find group")

    # FIXME: this needs to be updated
    def test_groups(self) -> None:
        # FIXME: split into two tests? _timerange, and _namecontains -- testing without parameters not practical
        groups = list(self.dt.groups(since="2019-01-01T00:00:00", until="2019-01-31T23:59:59"))
        self.assertEqual(len(groups),  2)
        self.assertEqual(groups[0].id, 1897)
        self.assertEqual(groups[1].id, 2220)

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

    # FIXME: this needs to be updated
    def test_meetings(self) -> None:
        meetings = list(self.dt.meetings(since="2019-01-01", until="2019-12-31", meeting_type=self.dt.meeting_type("ietf")))
        self.assertEqual(len(meetings),  3)
        self.assertEqual(meetings[0].city, "Singapore")
        self.assertEqual(meetings[1].city, "Montreal")
        self.assertEqual(meetings[2].city, "Prague")

    # FIXME: this needs to be updated
    def test_meeting_types(self) -> None:
        types = list(self.dt.meeting_types())
        self.assertEqual(len(types),  2)
        self.assertEqual(types[0].slug, "ietf")
        self.assertEqual(types[1].slug, "interim")


if __name__ == '__main__':
    unittest.main()

# =================================================================================================================================
# vim: set tw=0 ai:
