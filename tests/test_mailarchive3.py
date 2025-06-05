# Copyright (C) 2021-2025 University of Glasgow
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

import pymongo 

from datetime      import date, datetime, timedelta, timezone
from email.headerregistry import Address
from pathlib              import Path
from unittest.mock        import patch, Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ietfdata.datatracker  import *
from ietfdata.mailarchive3 import *

# =================================================================================================================================
# Unit tests:

class TestMailArchive3(unittest.TestCase):
    dt : DataTracker
    ma : MailArchive

    @classmethod
    def setUpClass(self) -> None:
        self.dt = DataTracker(DTBackendLive())
        self.ma = MailArchive(sqlite_file = "cache/ietfdata.sqlite")
        # Fetch the mailing lists used in these tests:
        self.ma.update_mailing_list_names()
        self.ma.update_mailing_list("100attendees")
        self.ma.update_mailing_list("avt")
        self.ma.update_mailing_list("anima")
        self.ma.update_mailing_list("cfrg")
        self.ma.update_mailing_list("e-impact")
        self.ma.update_mailing_list("green")
        self.ma.update_mailing_list("ietf")
        self.ma.update_mailing_list("irtf-announce")
        self.ma.update_mailing_list("irtf-discuss")
        self.ma.update_mailing_list("last-call")
        self.ma.update_mailing_list("secdir")
        self.ma.update_mailing_list("sip")


    # ==============================================================================================
    # Tests for the Envelope class follow:

    def test_mailarchive3_envelope_mailing_list(self) -> None:
        msgs = self.ma.message("<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].mailing_list().name(), "cfrg")


    def test_mailarchive3_envelope_uidvalidity(self) -> None:
        msgs = self.ma.message("<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].uidvalidity(), 1455297825)


    def test_mailarchive3_envelope_uid(self) -> None:
        msgs = self.ma.message("<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].uid(), 14157)


    def test_mailarchive3_envelope_date_received(self) -> None:
        msgs = self.ma.message("<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].date_received(), datetime.fromisoformat("2025-04-18T06:30:21Z"))


    def test_mailarchive3_envelope_size(self) -> None:
        msgs = self.ma.message("<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].size(), 6866)


    def test_mailarchive3_envelope_message_id(self) -> None:
        msgs = self.ma.message("<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].message_id(), "<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")


    def test_mailarchive3_envelope_from(self) -> None:
        msgs = self.ma.message("<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].from_().display_name, "Stanislav V. Smyshlyaev")
        self.assertEqual(msgs[0].from_().username,     "smyshsv")
        self.assertEqual(msgs[0].from_().domain,       "gmail.com")
        self.assertEqual(msgs[0].from_().addr_spec,    "smyshsv@gmail.com")


    def test_mailarchive3_envelope_to(self) -> None:
        msgs = self.ma.message("<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(len(msgs[0].to()), 1)
        self.assertEqual(msgs[0].to()[0].display_name, "CFRG")
        self.assertEqual(msgs[0].to()[0].username,     "cfrg")
        self.assertEqual(msgs[0].to()[0].domain,       "irtf.org")
        self.assertEqual(msgs[0].to()[0].addr_spec,    "cfrg@irtf.org")


    def test_mailarchive3_envelope_cc(self) -> None:
        msgs = self.ma.message("<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(len(msgs[0].cc()), 2)
        self.assertEqual(msgs[0].cc()[0].display_name, "")
        self.assertEqual(msgs[0].cc()[0].username,     "cfrg-chairs")
        self.assertEqual(msgs[0].cc()[0].domain,       "ietf.org")
        self.assertEqual(msgs[0].cc()[0].addr_spec,    "cfrg-chairs@ietf.org")
        self.assertEqual(msgs[0].cc()[1].display_name, "")
        self.assertEqual(msgs[0].cc()[1].username,     "draft-orru-zkproof-sigma-protocols")
        self.assertEqual(msgs[0].cc()[1].domain,       "ietf.org")
        self.assertEqual(msgs[0].cc()[1].addr_spec,    "draft-orru-zkproof-sigma-protocols@ietf.org")


    def test_mailarchive3_envelope_subject(self) -> None:
        msgs = self.ma.message("<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].subject(), "[CFRG] Adoption Call: Sigma Protocols")


    def test_mailarchive3_envelope_date(self) -> None:
        # The "Date:" header on this message is "Fri, 18 Apr 2025 09:30:05 +0300"
        msgs = self.ma.message("<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].date(), datetime.fromisoformat("2025-04-18T06:30:05+00:00"))


    def test_mailarchive3_envelope_header(self) -> None:
        msgs = self.ma.message("<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].header("from"),    ["\"Stanislav V. Smyshlyaev\" <smyshsv@gmail.com>"])
        self.assertEqual(msgs[0].header("subject"), ["[CFRG] Adoption Call: Sigma Protocols"])


    def test_mailarchive3_envelope_contents(self) -> None:
        msgs = self.ma.message("<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].contents().get_all("from"),    ["\"Stanislav V. Smyshlyaev\" <smyshsv@gmail.com>"])
        self.assertEqual(msgs[0].contents().get_all("subject"), ["[CFRG] Adoption Call: Sigma Protocols"])


    def test_mailarchive3_envelope_in_reply_to(self) -> None:
        msgs = self.ma.message("<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].in_reply_to(), [])

        msgs = self.ma.message("<CAMr0u6npL+TjkdVr4Jnouha6SGjQeMjiLTuRtRD7CLqWBZ2CBw@mail.gmail.com>")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(len(msgs[0].in_reply_to()), 1)
        self.assertEqual(msgs[0].in_reply_to()[0].message_id(), "<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")

        msgs = self.ma.message("<399B1F51-1C36-4F6D-B1ED-2F293707A6BF@gmail.com>")
        self.assertEqual(len(msgs), 2)                  # This message has copies to both 100attendees@ and ietf@
        self.assertEqual(len(msgs[0].in_reply_to()), 2) # ...as does the message to which it is a reply


    def test_mailarchive3_envelope_replies(self) -> None:
        msgs = self.ma.message("<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].replies()[0].message_id(), "<CAMr0u6npL+TjkdVr4Jnouha6SGjQeMjiLTuRtRD7CLqWBZ2CBw@mail.gmail.com>")
        self.assertEqual(msgs[0].replies()[1].message_id(), "<CADhumskFy4-Jsr7YC7Xd38NUJ4Nv0xTvKgivXE-U0D3k3cCMtQ@mail.gmail.com>")


    def test_mailarchive3_envelope_metadata(self) -> None:
        msg = self.ma.message("<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")[0]
        self.assertEqual(msg.get_metadata("test_mailarchive3", "testing"), None)
        msg.add_metadata("test_mailarchive3", "testing", "1... 2... 3...")
        self.assertEqual(msg.get_metadata("test_mailarchive3", "testing"), "1... 2... 3...")
        msg.clear_metadata("test_mailarchive3", "testing")
        self.assertEqual(msg.get_metadata("test_mailarchive3", "testing"), None)


    # =============================================================================================
    # Tests for the MailingList class follow:

    def test_mailarchive3_mailinglist_name(self) -> None:
        mlist = self.ma.mailing_list("100attendees")
        self.assertEqual(mlist.name(), "100attendees")


    def test_mailarchive3_mailinglist_uidvalidity(self) -> None:
        mlist = self.ma.mailing_list("100attendees")
        self.assertEqual(mlist.uidvalidity(), 1505323361)


    def test_mailarchive3_mailinglist_num_messages(self) -> None:
        mlist = self.ma.mailing_list("100attendees")
        self.assertEqual(mlist.num_messages(), 434)


    def test_mailarchive3_mailinglist_message_uids(self) -> None:
        mlist = self.ma.mailing_list("100attendees")
        uids  = list(mlist.message_uids())
        self.assertEqual(len(uids), 434)


    def test_mailarchive3_mailinglist_message(self) -> None:
        mlist = self.ma.mailing_list("cfrg")
        msg   = mlist.message(14157)
        if msg is not None:
            self.assertEqual(msg.message_id(), "<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")
        else:
            self.fail("Cannot find message")


    def test_mailarchive3_mailinglist_messages(self) -> None:
        mlist = self.ma.mailing_list("100attendees")
        # Test all messages:
        msgs  = list(mlist.messages())
        self.assertEqual(len(msgs), 434)
        # Test messages with received before/after constraints:
        msgs  = list(mlist.messages(received_after  = "2017-10-01T00:00:00+00:00",
                                    received_before = "2017-11-01T00:00:00+00:00"))
        self.assertEqual(len(msgs), 9)


    def test_mailarchive3_mailinglist_messages_as_dataframe(self) -> None:
        mlist = self.ma.mailing_list("100attendees")
        # Test all messages:
        df = mlist.messages_as_dataframe()
        self.assertEqual(df.shape, (434, 7))

        # Test messages with received before/after constraints:
        df  = mlist.messages_as_dataframe(received_after  = "2017-10-01T00:00:00+00:00",
                                          received_before = "2017-11-01T00:00:00+00:00")
        self.assertEqual(df.shape, (9, 7))


    def test_mailarchive3_mailinglist_threads(self) -> None:
        mlist   = self.ma.mailing_list("100attendees")
        threads = mlist.threads()
        self.assertEqual(len(threads), 111)
        # Message <9B50505D-A7E7-40E0-B789-419DA14C6021@gmail.com> is copied to both the
        # 100attendees and ietf lists, so there will be two envolopes in the thread head..
        self.assertEqual(len(threads["<9B50505D-A7E7-40E0-B789-419DA14C6021@gmail.com>"]), 2)


    def test_mailarchive3_mailinglist_metadata(self) -> None:
        mlist = self.ma.mailing_list("100attendees")
        self.assertEqual(mlist.get_metadata("test_mailarchive3", "testing"), None)
        mlist.add_metadata("test_mailarchive3", "testing", "1... 2... 3...")
        self.assertEqual(mlist.get_metadata("test_mailarchive3", "testing"), "1... 2... 3...")
        mlist.clear_metadata("test_mailarchive3", "testing")
        self.assertEqual(mlist.get_metadata("test_mailarchive3", "testing"), None)


    # =============================================================================================
    # Tests for the MailArchive class follow:

    def test_mailarchive3_mailarchive_mailing_list_names(self) -> None:
        ml_names = list(self.ma.mailing_list_names())
        self.assertGreater(len(ml_names), 0)
        self.assertIn("ietf",          ml_names)
        self.assertIn("ietf-announce", ml_names)
        self.assertIn("irtf-announce", ml_names)


    def test_mailarchive3_mailarchive_mailing_list(self) -> None:
        mlist = self.ma.mailing_list("100attendees")
        self.assertEqual(mlist.name(), "100attendees")
        self.assertEqual(mlist.num_messages(), 434)


    def test_mailarchive3_mailarchive_message(self) -> None:
        # This assumes there is a local mailarchive containing data up to 2025-01-21 or later.
        msgs = self.ma.message("<0D393D01-F267-43BC-8F9C-1638B3E17EA5@csperkins.org>")
        self.assertEqual(len(msgs), 4)
        self.assertEqual(msgs[0].mailing_list().name(), "e-impact")
        self.assertEqual(msgs[0].uid(),         1591)
        self.assertEqual(msgs[0].uidvalidity(), 1674241031)
        self.assertEqual(msgs[0].subject(),     '[E-impact] Sustainability and the Internet Research Group chartered')
        self.assertEqual(msgs[0].from_(),       Address(display_name="Colin Perkins", addr_spec="csp@csperkins.org"))

        self.assertEqual(msgs[1].mailing_list().name(), "green")
        self.assertEqual(msgs[1].uid(),         159)
        self.assertEqual(msgs[1].uidvalidity(), 1728069020)
        self.assertEqual(msgs[1].subject(),     '[Green] Sustainability and the Internet Research Group chartered')
        self.assertEqual(msgs[1].from_(),       Address(display_name="Colin Perkins", addr_spec="csp@csperkins.org"))

        self.assertEqual(msgs[2].mailing_list().name(), "irtf-announce")
        self.assertEqual(msgs[2].uid(),         613)
        self.assertEqual(msgs[2].uidvalidity(), 1455297825)
        self.assertEqual(msgs[2].subject(),     '[IRTF-Announce] Sustainability and the Internet Research Group chartered')
        self.assertEqual(msgs[2].from_(),       Address(display_name="Colin Perkins", addr_spec="csp@csperkins.org"))

        self.assertEqual(msgs[3].mailing_list().name(), "irtf-discuss")
        self.assertEqual(msgs[3].uid(),         819)
        self.assertEqual(msgs[3].uidvalidity(), 1455297825)
        self.assertEqual(msgs[3].subject(),     '[irtf-discuss] Sustainability and the Internet Research Group chartered')
        self.assertEqual(msgs[3].from_(),       Address(display_name="Colin Perkins", addr_spec="csp@csperkins.org"))


    def test_mailarchive3_mailarchive_messages_from_list(self) -> None:
        # Messages from a person to specific mailing list
        msgs = list(self.ma.messages(from_addr="csp@csperkins.org", mailing_list_name="sip"))
        self.assertEqual(len(msgs), 8)
        self.assertEqual(msgs[0].subject(), "[Sip] Review request: draft-ietf-mmusic-connection-precon-00.txt")
        self.assertEqual(msgs[1].subject(), "Re: [Sip] SDP Query")
        self.assertEqual(msgs[2].subject(), "Re: [Sip] SDP Query")
        self.assertEqual(msgs[3].subject(), "Re: [Sip] Changing SSRC/sequence numbers during a call")
        self.assertEqual(msgs[4].subject(), "[Sip] Progressing ICE")
        self.assertEqual(msgs[5].subject(), "Re: [Sip] SIP IPv6 ABNF: Essential correction to RFC3261")
        self.assertEqual(msgs[6].subject(), "Re: [Sip] SIP IPv6 ABNF: Essential correction to RFC3261")
        self.assertEqual(msgs[7].subject(), "Re: [Sip] Maximum allowed value of Clock rate in SDP ???")


    def test_mailarchive3_mailarchive_messages_from_to(self) -> None:
        # Messages between two people, irrespective of mailing list
        msgs = list(self.ma.messages(from_addr="csp@csperkins.org", to_addr="ladan@isi.edu"))
        self.assertEqual(len(msgs), 3)
        self.assertEqual(msgs[0].subject(),             "Re: [AVT] Header formats for RTP profile for TFRC")
        self.assertEqual(msgs[0].mailing_list().name(), "avt")
        self.assertEqual(msgs[0].uid(),                 4969)
        self.assertEqual(msgs[0].uidvalidity(),         1455297825)

        self.assertEqual(msgs[1].subject(),             "Re: [AVT] I-D ACTION:draft-ietf-avt-tfrc-profile-06.txt")
        self.assertEqual(msgs[1].mailing_list().name(), "avt")
        self.assertEqual(msgs[1].uid(),                 6312)
        self.assertEqual(msgs[1].uidvalidity(),         1455297825)

        self.assertEqual(msgs[2].subject(),             "Re: [AVT] I-D ACTION:draft-ietf-avt-tfrc-profile-09.txt")
        self.assertEqual(msgs[2].mailing_list().name(), "avt")
        self.assertEqual(msgs[2].uid(),                 7549)
        self.assertEqual(msgs[2].uidvalidity(),         1455297825)


    def test_mailarchive3_mailarchive_messages_subject(self) -> None:
        # Messages with a particular subject
        msgs = list(self.ma.messages(subject="Secdir last call review of draft-ietf-anima-brski-cloud-11"))
        self.assertEqual(len(msgs), 3)
        self.assertEqual(msgs[0].subject(),             "[Anima] Secdir last call review of draft-ietf-anima-brski-cloud-11")
        self.assertEqual(msgs[0].mailing_list().name(), "anima")
        self.assertEqual(msgs[0].uid(),                 7522)
        self.assertEqual(msgs[0].uidvalidity(),         1455297825)

        self.assertEqual(msgs[1].subject(),             "[Last-Call] Secdir last call review of draft-ietf-anima-brski-cloud-11")
        self.assertEqual(msgs[1].mailing_list().name(), "last-call")
        self.assertEqual(msgs[1].uid(),                 12409)
        self.assertEqual(msgs[1].uidvalidity(),         1571671002)

        self.assertEqual(msgs[2].subject(),             "[secdir] Secdir last call review of draft-ietf-anima-brski-cloud-11")
        self.assertEqual(msgs[2].mailing_list().name(), "secdir")
        self.assertEqual(msgs[2].uid(),                 12606)
        self.assertEqual(msgs[2].uidvalidity(),         1455297825)

        # This should find three messages sent to ietf@ietf.org with dates:
        #   1994-11-07T14:06:35+00:00
        #   1994-11-07T16:16:39+00:00
        #   1994-11-10T01:47:30+00:00
        msgs = list(self.ma.messages(subject="Chair's contest for an IETF Logo"))
        self.assertEqual(len(msgs), 3)


if __name__ == '__main__':
    unittest.main()

# =================================================================================================================================
# vim: set tw=0 ai:
