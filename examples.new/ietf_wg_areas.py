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

from ietfdata.datatracker import *

def working_groups(dt:DataTracker) -> Iterator[Group]:
    for area in dt.groups(parent = dt.group_from_acronym("iesg")):
        for group in dt.groups(parent = area):
            t = dt.group_type_name(group.type)
            if t == dt.group_type_name_from_slug("wg"):
                yield group


def find_area(dt:DataTracker, area_name:str) -> Group:
    areas = list(dt.groups(parent = dt.group_from_acronym("iesg"), name = area_name))
    if len(areas) == 1:
        return areas[0]
    else:
        raise RuntimeError(f"Cannot find area {area_name}")


if len(sys.argv) != 3:
    print("Usage: python ietf_wg_areas.py archive/ietf_dt.sqlite data/ietf_wg_areas.json")
    sys.exit(1)

dt = DataTracker(DTBackendArchive(sys.argv[1]))

area_history : dict[str,list[dict[str,str|None]]] = {}

for wg in working_groups(dt):
    area = dt.group(wg.parent)
    assert area is not None

    prev_time = None
    prev_area = None

    area_history[wg.acronym] = []

    for event in dt.group_events(group = wg):
        event_time = event.time.strftime('%Y-%m-%d')
        if event.type == "info_changed" and event.desc.startswith("Group parent changed to <b>"):
            # There are four variants:
            #   Group parent changed to <b>Web and Internet Transport</b> from Transport Area
            #   Group parent changed to <b>Applications and Real-Time Area</b>
            #   Group parent changed to <b>General Area</b> from None
            #   Group parent changed to <b>None</b> from Applications Area
            new_area_end  = event.desc.find("</b>")
            new_area_name = event.desc[27:new_area_end]
            if new_area_name == "None":
                new_area = None
            else:
                new_area = find_area(dt, new_area_name)

            if "</b> from " in event.desc:
                old_area_start = event.desc.find("</b> from ") + 10
                old_area_name  = event.desc[old_area_start:]
                if old_area_name == "None":
                    old_area = None
                else:
                    old_area = find_area(dt, old_area_name)
            else:
                old_area_name = None
                old_area = None

            if prev_area is None and old_area is not None:
                prev_area = old_area.acronym
            area_history[wg.acronym].append({"from": prev_time,
                                             "to"  : event_time,
                                             "area": prev_area})
            if new_area is not None:
                prev_area = new_area.acronym
            else:
                prev_area = None
            prev_time = event_time

    area_history[wg.acronym].append({"from": prev_time,
                                     "to"  : None,
                                     "area": area.acronym})

with open(sys.argv[2], "w") as outf:
    json.dump(area_history, outf, indent=3)


