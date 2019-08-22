# Copyright (C) 2017-2019 University of Glasgow
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

from ietfdata.rfcindex import *

# ==================================================================================================
# Unit tests:

class TestRFCIndex(unittest.TestCase):
    index : RFCIndex

    @classmethod
    def setUpClass(self) -> None:
        self.index = RFCIndex()

    def test_rfc(self):
        self.assertEqual(self.index.rfc["RFC3550"].doc_id,       "RFC3550")
        self.assertEqual(self.index.rfc["RFC3550"].title,        "RTP: A Transport Protocol for Real-Time Applications")
        self.assertEqual(self.index.rfc["RFC3550"].authors,      ["H. Schulzrinne", "S. Casner", "R. Frederick", "V. Jacobson"])
        self.assertEqual(self.index.rfc["RFC3550"].doi,          "10.17487/RFC3550")
        self.assertEqual(self.index.rfc["RFC3550"].stream,       "IETF")
        self.assertEqual(self.index.rfc["RFC3550"].wg,           "avt")
        self.assertEqual(self.index.rfc["RFC3550"].area,         "rai")
        self.assertEqual(self.index.rfc["RFC3550"].curr_status,  "INTERNET STANDARD")
        self.assertEqual(self.index.rfc["RFC3550"].publ_status,  "DRAFT STANDARD")
        self.assertEqual(self.index.rfc["RFC3550"].day,          None)
        self.assertEqual(self.index.rfc["RFC3550"].month,        "July")
        self.assertEqual(self.index.rfc["RFC3550"].year,         2003)
        self.assertEqual(self.index.rfc["RFC3550"].formats,      [("ASCII", 259985, 104), ("PS", 630740, None), ("PDF", 504117, None), ("HTML", None, None)])
        self.assertEqual(self.index.rfc["RFC3550"].draft,        "draft-ietf-avt-rtp-new-12")
        self.assertEqual(self.index.rfc["RFC3550"].keywords,     ["RTP", "end-to-end", "network", "audio", "video", "RTCP"])
        self.assertEqual(self.index.rfc["RFC3550"].updates,      [])
        self.assertEqual(self.index.rfc["RFC3550"].updated_by,   ["RFC5506", "RFC5761", "RFC6051", "RFC6222", "RFC7022", "RFC7160", "RFC7164", "RFC8083", "RFC8108"])
        self.assertEqual(self.index.rfc["RFC3550"].obsoletes,    ["RFC1889"])
        self.assertEqual(self.index.rfc["RFC3550"].obsoleted_by, [])
        self.assertEqual(self.index.rfc["RFC3550"].is_also,      ["STD0064"])
        self.assertEqual(self.index.rfc["RFC3550"].see_also,     [])
        self.assertEqual(self.index.rfc["RFC3550"].errata_url,   "http://www.rfc-editor.org/errata_search.php?rfc=3550")
        self.assertEqual(self.index.rfc["RFC3550"].charset(),    "utf-8")
        self.assertEqual(self.index.rfc["RFC3550"].content_url("ASCII"), "https://www.rfc-editor.org/rfc/rfc3550.txt")
        self.assertEqual(self.index.rfc["RFC3550"].content_url("PS"),    "https://www.rfc-editor.org/rfc/rfc3550.ps")
        self.assertEqual(self.index.rfc["RFC3550"].content_url("PDF"),   "https://www.rfc-editor.org/rfc/rfc3550.pdf")
        self.assertEqual(self.index.rfc["RFC3550"].content_url("XML"),   None)
        # FIXME: no text for the abstract

    def test_rfc_april_fool(self):
        # RFCs published on 1 April are the only ones to specify a day in the XML
        self.assertEqual(self.index.rfc["RFC1149"].day,   1)
        self.assertEqual(self.index.rfc["RFC1149"].month, "April")
        self.assertEqual(self.index.rfc["RFC1149"].year,  1990)

    def test_rfc_editor(self):
        # Some RFCs have <title>...</title> within an author block, usually "Editor". Check that we correctly strip this out.
        self.assertEqual(self.index.rfc["RFC1256"].authors, ["S. Deering"])

    def test_rfc_empty_kw(self):
        # Some RFCs have <kw></kw> which is not useful. Check that we correctly strip this out.
        self.assertEqual(self.index.rfc["RFC2351"].keywords, ["internet", "protocol", "encapsulation", "transactional", "traffic", "messaging"])

    def test_rfc_not_issued(self):
        self.assertEqual(self.index.rfc_not_issued["RFC7907"].doc_id,  "RFC7907")

    def test_bcp(self):
        self.assertEqual(self.index.bcp["BCP0009"].doc_id,  "BCP0009")
        self.assertEqual(self.index.bcp["BCP0009"].is_also, ["RFC2026", "RFC5657", "RFC6410", "RFC7100", "RFC7127", "RFC7475"])

    def test_fyi(self):
        self.assertEqual(self.index.fyi["FYI0036"].doc_id,  "FYI0036")
        self.assertEqual(self.index.fyi["FYI0036"].is_also, ["RFC4949"])

    def test_std(self):
        self.assertEqual(self.index.std["STD0064"].doc_id,  "STD0064")
        self.assertEqual(self.index.std["STD0064"].is_also, ["RFC3550"])
        self.assertEqual(self.index.std["STD0064"].title,   "RTP: A Transport Protocol for Real-Time Applications")


if __name__ == '__main__':
    unittest.main()

# =================================================================================================================================
# vim: set tw=0 ai:
