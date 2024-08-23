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


if __name__ == '__main__':
    unittest.main()

# =================================================================================================================================
# vim: set tw=0 ai:
