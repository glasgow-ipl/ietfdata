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
                u = f"https://datatracker.ietf.org{top_level_endpoints[endpoint]['list_endpoint']}"
                r = self.dt.session.get(u, params = {"fullschema" : "true" }, headers = req_headers, verify = True, stream = False)
                self.dt.get_count += 1
                if r.status_code == 200:
                    second_level_endpoints = r.json()
                    for endpoint in second_level_endpoints:
                        sl_endpoint = second_level_endpoints[endpoint]
                        self.endpoint_uris[sl_endpoint['list_endpoint']] = list(sl_endpoint['schema']["fields"].keys())

    @classmethod
    def setUpClass(self) -> None:
        self.dt = DataTracker(cache_dir = "cache", cache_timeout = timedelta(minutes = 15))
        self.fetch_api_schema()


    @unittest.expectedFailure
    def test_endpoint_coverage(self) -> None:
        # These endpoints are intentionally not implemented by the ietfdata library:
        ignored_endpoints = [
                    "/api/v1/community/communitylist/",
                    "/api/v1/community/emailsubscription/",
                    "/api/v1/community/searchrule/",
                    "/api/v1/dbtemplate/dbtemplate/",
                    "/api/v1/message/messageattachment/",
                    "/api/v1/name/nomineepositionstatename/",
                    "/api/v1/nomcom/feedback/",
                    "/api/v1/nomcom/feedbacklastseen/",
                    "/api/v1/nomcom/nomcom/",
                    "/api/v1/nomcom/nomination/",
                    "/api/v1/nomcom/nominee/",
                    "/api/v1/nomcom/nomineeposition/",
                    "/api/v1/nomcom/position/",
                    "/api/v1/nomcom/reminderdates/",
                    "/api/v1/nomcom/topic/",
                    "/api/v1/nomcom/topicfeedbacklastseen/",
                    "/api/v1/person/personalapikey/",
                    "/api/v1/person/personapikeyevent/",
                    "/api/v1/redirects/command/",
                    "/api/v1/redirects/redirect/",
                    "/api/v1/redirects/suffix/",
                    "/api/v1/submit/preapproval/",
                    "/api/v1/submit/submissioncheck/",
                    "/api/v1/submit/submissionemailevent/",
                    "/api/v1/submit/submissionextresource/",
                    "/api/v1/submit/submissionextresource/",
                    "/api/v1/utils/dumpinfo/",
                    "/api/v1/utils/versioninfo/"
                ]

        covered_uris = []
        for covered_uri in self.dt._hints:
            self.assertNotIn(covered_uri, ignored_endpoints)
            covered_uris.append(covered_uri)
        for endpoint_uri in self.endpoint_uris:
            if endpoint_uri not in ignored_endpoints:
                with self.subTest(msg=endpoint_uri):
                    if endpoint_uri not in covered_uris:
                        self.fail(f"No API methods for datatracker endpoint {endpoint_uri}")


    #def test_endpoint_fields(self) -> None:
    #    for uri in self.dt._hints:
    #        if uri in self.endpoint_uris:
    #            with self.subTest(msg=f"{uri}, {self.dt._hints[uri].obj_type.__name__}"):
    #                fields_in_object = list(self.dt._hints[uri].obj_type.__dict__["__dataclass_fields__"].keys())
    #                fields_in_schema = self.endpoint_uris[uri]
    #                for object_field in fields_in_object:
    #                    self.assertIn(object_field, fields_in_schema, msg="object has field not in schema")
    #                for schema_field in fields_in_schema:
    #                    self.assertIn(schema_field, fields_in_object, msg="schema has field not in object")
    #                self.assertCountEqual(fields_in_object, fields_in_schema)

