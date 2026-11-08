# Copyright (C) 2026 University of Glasgow
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

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime             import datetime
from ietfdata.datatracker import *

class WGAreas:
    _wg_areas : dict[str,list[dict[str,str|None]]]
    _wgs      : list[str]
    _areas    : list[str]

    def __init__(self, wg_area_file:str):
        with open(sys.argv[2], "r") as inf:
            self._wg_areas = json.load(inf)
        self._wgs   = []
        self._areas = []
        for wg, wg_areas in self._wg_areas.items():
            self._wgs.append(wg)
            for item in wg_areas:
                if item["area"] is not None and item["area"] not in self._areas:
                    self._areas.append(item["area"])


    def areas(self) -> list[str]:
        return sorted(self._areas)


    def area_for_wg(self, wg:str, pub_date:datetime) -> str:
        if wg in ["none", "iesg"]:
            return "other"
        
        date_str = pub_date.strftime("%Y-%m-%d")

        for item in self._wg_areas[wg]:
            if item["from"] == None and item["to"] == None:
                area = item["area"]
            elif item["from"] == None and item["to"] is not None:
                if date_str < item["to"]:
                    area = item["area"]
            elif item["from"] is not None and item["to"] == None:
                if date_str >= item["from"]:
                    area = item["area"]
            elif item["from"] is not None and item["to"] is not None:
                if date_str >= item["from"] and date_str < item["to"]:
                    area = item["area"]
        assert area is not None
        return area



if len(sys.argv) != 4:
    print("Usage: python rfcs_per_year.py archive/ietf_dt.sqlite data/rfcs_per_year_area.csv data/ietf_wg_areas.json")
    sys.exit(1)

dt   = DataTracker(DTBackendArchive(sys.argv[1]))
wga  = WGAreas(sys.argv[2])

rfcs_per_year : dict[int,dict[str,int]] = {}

for rfc in dt.documents(doctype = dt.document_type_from_slug("rfc")):
    for event in dt.document_events(doc = rfc, event_type = "published_rfc"):
        year = event.time.year
        if year not in rfcs_per_year:
            rfcs_per_year[year] = {}
            for area in wga.areas():
                rfcs_per_year[year][area] = 0
            rfcs_per_year[year]["Legacy"] = 0
            rfcs_per_year[year]["other"] = 0
        assert rfc.stream is not None
        assert rfc.group  is not None
        stream_name = dt.stream(rfc.stream).slug
        if stream_name == "ietf":
            group  = dt.group(rfc.group)
            assert group.parent is not None
            parent = dt.group(group.parent)
            g_type = dt.group_type_name(group.type).slug

            if g_type == "wg":
                # The RFC was publihed by a working group
                wg_area = wga.area_for_wg(group.acronym, rfc.time)
                rfcs_per_year[year][wg_area] += 1
            elif g_type == "area":
                # The RFC was published by an area
                rfcs_per_year[year][group.acronym] += 1
            elif g_type == "ag":
                # The RFC was published by an area working group
                rfcs_per_year[year][parent.acronym] += 1
            elif g_type == "ietf":
                # The RFC was published on the IETF stream but is not from
                # a WG or area (e.g., IANA or IAB documents the IESG chose
                # to published)
                rfcs_per_year[year]["other"] += 1
            elif g_type == "individ":
                # The RFC was an AD-sponsored individial draft publiahed on
                # the IETF stream, and doesn't belong to an area.
                rfcs_per_year[year]["other"] += 1
            else:
                raise RuntimeError(f"unknown group type {g_type}")
        else:
            # Not IETF stream
            rfcs_per_year[year]["Legacy"] += 1

with open(sys.argv[3], "w") as outf:
    print("Year,Non-IETF,IETF No Area", file=outf, end="")
    for area in wga.areas():
        print(f",{area.upper()}", file=outf, end="")
    print("", file=outf)

    for year in sorted(rfcs_per_year.keys()):
        print(f"{year}", file=outf, end="")
        print(f",{rfcs_per_year[year]['Legacy']}", file=outf, end="")
        print(f",{rfcs_per_year[year]['other']}", file=outf, end="")
        for area in wga.areas():
            print(f",{rfcs_per_year[year][area]}", file=outf, end="")
        print(f"", file=outf)

