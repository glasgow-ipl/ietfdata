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

from pathlib       import Path
from unittest.mock import patch, Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ietfdata.datatracker  import *
from ietfdata.mailarchive2 import *


# =================================================================================================================================
# Unit tests:

class TestMailArchive(unittest.TestCase):
    dt : DataTracker
    ma : MailArchive

    @classmethod
    def setUpClass(self) -> None:
        self.dt = DataTracker(cache_dir = "cache", cache_timeout = timedelta(minutes = 15))
        try:
            self.ma = MailArchive()
        except pymongo.errors.ServerSelectionTimeoutError:
            raise unittest.SkipTest("Couldn't connect to MongoDB instance -- skipping MailArchive tests")


    def test_mailarchive_mailing_list_names(self) -> None:
        ml_names = list(self.ma.mailing_list_names())
        self.assertGreater(len(ml_names), 0)
        self.assertIn("ietf",          ml_names)
        self.assertIn("ietf-announce", ml_names)
        self.assertIn("irtf-announce", ml_names)


    def test_mailarchive_mailing_list(self) -> None:
        mlist = self.ma.mailing_list("100attendees")
        mlist.update()
        self.assertEqual(mlist.name(), "100attendees")
        self.assertEqual(mlist.num_messages(), 434)


    def test_mailarchive_message(self) -> None:
        # This assumes there is a local mailarchive containing data up to 2025-01-21 or later.
        msgs = self.ma.message("<0D393D01-F267-43BC-8F9C-1638B3E17EA5@csperkins.org>")
        self.assertEqual(len(msgs), 4)
        self.assertEqual(msgs[0].mailing_list().name(), "e-impact")
        self.assertEqual(msgs[0].uid(),             1591)
        self.assertEqual(msgs[0].uidvalidity(),     1674241031)
        self.assertEqual(msgs[0].header("subject"), ['[E-impact] Sustainability and the Internet Research Group chartered'])
        self.assertEqual(msgs[0].header("from"),    ['Colin Perkins <csp@csperkins.org>'])

        self.assertEqual(msgs[1].mailing_list().name(), "green")
        self.assertEqual(msgs[1].uid(),             159)
        self.assertEqual(msgs[1].uidvalidity(),     1728069020)
        self.assertEqual(msgs[1].header("subject"), ['[Green] Sustainability and the Internet Research Group chartered'])
        self.assertEqual(msgs[1].header("from"),    ['Colin Perkins <csp@csperkins.org>'])

        self.assertEqual(msgs[2].mailing_list().name(), "irtf-announce")
        self.assertEqual(msgs[2].uid(),             613)
        self.assertEqual(msgs[2].uidvalidity(),     1455297825)
        self.assertEqual(msgs[2].header("subject"), ['[IRTF-Announce] Sustainability and the Internet Research Group chartered'])
        self.assertEqual(msgs[2].header("from"),    ['Colin Perkins <csp@csperkins.org>'])

        self.assertEqual(msgs[3].mailing_list().name(), "irtf-discuss")
        self.assertEqual(msgs[3].uid(),             819)
        self.assertEqual(msgs[3].uidvalidity(),     1455297825)
        self.assertEqual(msgs[3].header("subject"), ['[irtf-discuss] Sustainability and the Internet Research Group chartered'])
        self.assertEqual(msgs[3].header("from"),    ['Colin Perkins <csp@csperkins.org>'])



    def test_mailarchive_messages_from_list(self) -> None:
        # From person to specific mailing list
        msgs = list(self.ma.messages(header_from="csp@csperkins.org", mailing_list_name="sip"))
        self.assertEqual(len(msgs), 8)
        self.assertEqual(msgs[0].header("subject"), ['[Sip] Review request: draft-ietf-mmusic-connection-precon-00.txt'])
        self.assertEqual(msgs[1].header("subject"), ['Re: [Sip] SDP Query'])
        self.assertEqual(msgs[2].header("subject"), ['Re: [Sip] SDP Query'])
        self.assertEqual(msgs[3].header("subject"), ['Re: [Sip] Changing SSRC/sequence numbers during a call'])
        self.assertEqual(msgs[4].header("subject"), ['[Sip] Progressing ICE'])
        self.assertEqual(msgs[5].header("subject"), ['Re: [Sip] SIP IPv6 ABNF: Essential correction to RFC3261'])
        self.assertEqual(msgs[6].header("subject"), ['Re: [Sip] SIP IPv6 ABNF: Essential correction to RFC3261'])
        self.assertEqual(msgs[7].header("subject"), ['Re: [Sip] Maximum allowed value of Clock rate in SDP ???'])


    def test_mailarchive_messages_from_to(self) -> None:
        # Between two people, irrespective of mailing list
        msgs = list(self.ma.messages(header_from="csp@csperkins.org", header_to="ladan@isi.edu"))
        self.assertEqual(len(msgs), 3)
        self.assertEqual(msgs[0].header("subject"), ['Re: [AVT] Header formats for RTP profile for TFRC'])
        self.assertEqual(msgs[0].mailing_list().name(), "avt")
        self.assertEqual(msgs[0].uid(),             4969)
        self.assertEqual(msgs[0].uidvalidity(),     1455297825)

        self.assertEqual(msgs[1].header("subject"), ['Re: [AVT] I-D ACTION:draft-ietf-avt-tfrc-profile-06.txt'])
        self.assertEqual(msgs[1].mailing_list().name(), "avt")
        self.assertEqual(msgs[1].uid(),             6312)
        self.assertEqual(msgs[1].uidvalidity(),     1455297825)

        self.assertEqual(msgs[2].header("subject"), ['Re: [AVT] I-D ACTION:draft-ietf-avt-tfrc-profile-09.txt '])
        self.assertEqual(msgs[2].mailing_list().name(), "avt")
        self.assertEqual(msgs[2].uid(),             7549)
        self.assertEqual(msgs[2].uidvalidity(),     1455297825)


    def test_mailarchive_messages_subject(self) -> None:
        # With a particular subject
        msgs = list(self.ma.messages(header_subject="Secdir last call review of draft-ietf-anima-brski-cloud-11"))
        self.assertEqual(len(msgs), 3)
        self.assertEqual(msgs[0].header("subject"), ['[Anima] Secdir last call review of draft-ietf-anima-brski-cloud-11'])
        self.assertEqual(msgs[0].mailing_list().name(), "anima")
        self.assertEqual(msgs[0].uid(),             7522)
        self.assertEqual(msgs[0].uidvalidity(),     1455297825)

        self.assertEqual(msgs[1].header("subject"), ['[Last-Call] Secdir last call review of draft-ietf-anima-brski-cloud-11'])
        self.assertEqual(msgs[1].mailing_list().name(), "last-call")
        self.assertEqual(msgs[1].uid(),             12409)
        self.assertEqual(msgs[1].uidvalidity(),     1571671002)

        self.assertEqual(msgs[2].header("subject"), ['[secdir] Secdir last call review of draft-ietf-anima-brski-cloud-11'])
        self.assertEqual(msgs[2].mailing_list().name(), "secdir")
        self.assertEqual(msgs[2].uid(),             12606)
        self.assertEqual(msgs[2].uidvalidity(),     1455297825)



if __name__ == '__main__':
    unittest.main()

# =================================================================================================================================
# vim: set tw=0 ai:
