# Copyright (C) 2024 University of Glasgow
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
from ietfdata.datatracker     import *
from ietfdata.datatracker_ext import *


# =================================================================================================================================
# Unit tests:

class TestDatatracker(unittest.TestCase):
    dt : DataTrackerExt

    @classmethod
    def setUpClass(self) -> None:
        self.dt = DataTrackerExt(cache_dir = "cache", cache_timeout = timedelta(minutes = 15))

    # -----------------------------------------------------------------------------------------------------------------------------
    # Tests relating to the datatracker access layer:

    def test_draft_history(self) -> None:
        draft = self.dt.document_from_draft("draft-ietf-pana-statemachine")
        if draft is not None:
            self.assertEqual(draft.name, "draft-ietf-pana-statemachine")

            # Now retrieve the history:
            history = self.dt.draft_history(draft)
            self.assertEqual(len(history), 14)
        else:
            self.fail("Cannot retrieve draft-ietf-pana-statemachine")


