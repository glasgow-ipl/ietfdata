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

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import ietfdata
from ietfdata.datatracker import *


# =================================================================================================================================
# Unit tests:

class TestDatatrackerCoverage(unittest.TestCase):
    dt : DataTracker
    endpoint_uris : Dict[str, List[str]]

    @classmethod
    def fetch_api_schema(self) -> None:
        req_headers = {'User-Agent': self.dt.ua}
        r = self.dt.session.get("https://datatracker.ietf.org/api/v1", headers = req_headers, verify = True, stream = False)
        self.dt.get_count += 1
        self.endpoint_uris = {}
        if r.status_code == 200:
            top_level_endpoints = r.json()
            for endpoint in top_level_endpoints:
                r = self.dt.session.get(f"https://datatracker.ietf.org{top_level_endpoints[endpoint]['list_endpoint']}", params = {"fullschema" : "true" }, headers = req_headers, verify = True, stream = False)
                self.dt.get_count += 1
                if r.status_code == 200:
                    second_level_endpoints = r.json()
                    for endpoint in second_level_endpoints:
                        self.endpoint_uris[second_level_endpoints[endpoint]['list_endpoint']] = list(second_level_endpoints[endpoint]['schema']["fields"].keys())

    @classmethod
    def setUpClass(self) -> None:
        self.dt = DataTracker()
        self.fetch_api_schema()


    def test_endpoint_coverage(self) -> None:
        covered_uris = []
        for covered_uri in self.dt._cache_indexes:
            covered_uris.append(covered_uri.root)
        for endpoint_uri in self.endpoint_uris:
            with self.subTest(msg=endpoint_uri):
                self.assertIn(endpoint_uri, covered_uris)


    def test_endpoint_fields(self) -> None:
        for uri in self.dt._cache_indexes:
            if uri.root in self.endpoint_uris:
                with self.subTest(msg=f"{uri.root}, {self.dt._cache_indexes[uri].resource_type.__name__}"):
                    self.assertCountEqual(list(self.dt._cache_indexes[uri].resource_type.__dict__["__dataclass_fields__"].keys()), self.endpoint_uris[uri.root])
