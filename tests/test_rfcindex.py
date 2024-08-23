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

from ietfdata.rfcindex import *

# ==================================================================================================
# Unit tests:

class TestRFCIndex(unittest.TestCase):
    index : RFCIndex

    @classmethod
    def setUpClass(self) -> None:
        self.index = RFCIndex(cache_dir = "cache")

    def test_rfc(self):
        rfc = self.index.rfc("RFC3550")
        if rfc is not None:
            self.assertEqual(rfc.doc_id,       "RFC3550")
            self.assertEqual(rfc.title,        "RTP: A Transport Protocol for Real-Time Applications")
            self.assertEqual(rfc.authors,      ["H. Schulzrinne", "S. Casner", "R. Frederick", "V. Jacobson"])
            self.assertEqual(rfc.doi,          "10.17487/RFC3550")
            self.assertEqual(rfc.stream,       "IETF")
            self.assertEqual(rfc.wg,           "avt")
            self.assertEqual(rfc.area,         "rai")
            self.assertEqual(rfc.curr_status,  "INTERNET STANDARD")
            self.assertEqual(rfc.publ_status,  "DRAFT STANDARD")
            self.assertEqual(rfc.day,          None)
            self.assertEqual(rfc.month,        "July")
            self.assertEqual(rfc.year,         2003)
            self.assertEqual(rfc.formats,      ["ASCII", "PS", "PDF", "HTML"])
            self.assertEqual(rfc.draft,        "draft-ietf-avt-rtp-new-12")
            self.assertEqual(rfc.keywords,     ["RTP", "Real-Time Transport Protocol", "end-to-end", "network", "audio", "video", "RTCP", "RTP Control Protocol"])
            self.assertEqual(rfc.updates,      [])
            self.assertEqual(rfc.updated_by,   ["RFC5506", "RFC5761", "RFC6051", "RFC6222", "RFC7022", "RFC7160", "RFC7164", "RFC8083", "RFC8108", "RFC8860"])
            self.assertEqual(rfc.obsoletes,    ["RFC1889"])
            self.assertEqual(rfc.obsoleted_by, [])
            self.assertEqual(rfc.is_also,      ["STD0064"])
            self.assertEqual(rfc.see_also,     [])
            self.assertEqual(rfc.errata_url,   "https://www.rfc-editor.org/errata/rfc3550")
            self.assertEqual(rfc.charset(),    "utf-8")
            self.assertEqual(rfc.content_url("ASCII"), "https://www.rfc-editor.org/rfc/rfc3550.txt")
            self.assertEqual(rfc.content_url("PS"),    "https://www.rfc-editor.org/rfc/rfc3550.ps")
            self.assertEqual(rfc.content_url("PDF"),   "https://www.rfc-editor.org/rfc/rfc3550.pdf")
            self.assertEqual(rfc.content_url("XML"),   None)
            self.assertEqual(rfc.page_count,   104)
            # FIXME: no text for the abstract
        else:
            self.fail("Cannot find RFC")

    def test_rfc_april_fool(self):
        # RFCs published on 1 April are the only ones to specify a day in the XML
        rfc = self.index.rfc("RFC1149")
        if rfc is not None:
            self.assertEqual(rfc.day,   1)
            self.assertEqual(rfc.month, "April")
            self.assertEqual(rfc.year,  1990)
        else:
            self.fail("Cannot find RFC")

    def test_rfc_editor(self):
        # Some RFCs have <title>...</title> within an author block, usually "Editor". Check that we correctly strip this out.
        rfc = self.index.rfc("RFC1256")
        if rfc is not None:
            self.assertEqual(rfc.authors, ["S. Deering"])
        else:
            self.fail("Cannot find RFC")

    def test_rfc_empty_kw(self):
        # Some RFCs have <kw></kw> which is not useful. Check that we correctly strip this out.
        rfc = self.index.rfc("RFC2351")
        if rfc is not None:
            self.assertEqual(rfc.keywords, ["IP", "internet protocol", "encapsulation", "transactional", "traffic", "messaging"])
        else:
            self.fail("Cannot find RFC")

    def test_rfc_not_issued(self):
        rne = self.index.rfc_not_issued("RFC7907")
        if rne is not None:
            self.assertEqual(rne.doc_id,  "RFC7907")
        else:
            self.fail("Cannot find RFC not issued")

    def test_bcp(self):
        bcp = self.index.bcp("BCP0009")
        if bcp is not None:
            self.assertEqual(bcp.doc_id,  "BCP0009")
            self.assertEqual(bcp.is_also, ["RFC2026", "RFC5657", "RFC6410", "RFC7100", "RFC7127", "RFC7475", "RFC8789", "RFC9282"])
        else:
            self.fail("Cannot find BCP")

    def test_fyi(self):
        fyi = self.index.fyi("FYI0036")
        if fyi is not None:
            self.assertEqual(fyi.doc_id,  "FYI0036")
            self.assertEqual(fyi.is_also, ["RFC4949"])
        else:
            self.fail("Cannot find FYI")

    def test_std(self):
        std =  self.index.std("STD0064")
        if std is not None:
            self.assertEqual(std.doc_id,  "STD0064")
            self.assertEqual(std.is_also, ["RFC3550"])
            self.assertEqual(std.title,   "RTP: A Transport Protocol for Real-Time Applications")
        else:
            self.fail("Cannot find STD")

    def test_rfcs(self):
        rfcs = list(self.index.rfcs(since="2019-07", until="2019-07", stream="IRTF"))
        self.assertEqual(len(rfcs), 2)
        self.assertEqual(rfcs[0].doc_id, "RFC8569")
        self.assertEqual(rfcs[1].doc_id, "RFC8609")

        rfcs = list(self.index.rfcs(since="2019-07", until="2019-07", stream="IETF", area="art", wg="payload"))
        self.assertEqual(len(rfcs), 1)
        self.assertEqual(rfcs[0].doc_id, "RFC8627")


if __name__ == '__main__':
    unittest.main()

# =================================================================================================================================
# vim: set tw=0 ai:
