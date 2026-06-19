# Copyright (C) 2025 University of Glasgow
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

import datetime
import sys
import os
import json
import pprint

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ietfdata.datatracker     import *
from ietfdata.datatracker_ext import *
from ietfdata.rfcindex        import *

dt = DataTrackerExt(DTBackendArchive("archive/ietfdata-dt.sqlite"))
ri = RFCIndex(rfc_index="archive/rfc-index.xml")

rfcs = []

for rfc in reversed(list(ri.rfcs())):
    assert rfc is not None

    print(f"  {rfc.doc_id}")

    item = {"rfc_num"            : rfc.doc_id,
            "rfc_title"          : rfc.title,
            "rfc_stream"         : rfc.stream,
            "rfc_wg"             : rfc.wg,
            "rfc_area"           : rfc.area,
            "rfc_year"           : rfc.year,
            "rfc_month"          : rfc.month,
            "rfc_day"            : rfc.day,
            "drafts"             : [],
            "iesg_started"       : None,
            "iesg_finished"      : None,
            "rfc_editor_started" : None}

    history = dt.draft_history_for_rfc(rfc)

    for d in history:
        #print("    {0: <50} | {1} | {2}".format(d.draft.name, d.rev, d.date.strftime("%Y-%m-%d")))
        draft = {"name" : d.draft.name,
                 "rev"  : d.rev,
                 "date" : d.date.isoformat()}
        item["drafts"].append(draft)

    if len(history) > 0:
        for event in dt.document_events(history[0].draft):
            if  item["iesg_started"] is None and event.desc.startswith("IESG process started"):
                item["iesg_started"] = [event.time.isoformat(), event.desc]
            if  item["iesg_started"] is None and event.desc.startswith("Document is now in IESG state <b>Publication Requested"):
                item["iesg_started"] = [event.time.isoformat(), event.desc]
            if  item["iesg_started"] is None and event.desc.startswith("IETF state changed to <b>Submitted to IESG for Publication"):
                item["iesg_started"] = [event.time.isoformat(), event.desc]
            if  item["iesg_started"] is None and event.desc.startswith("State changed to <b>Publication Requested"):
                item["iesg_started"] = [event.time.isoformat(), event.desc]
            if  item["iesg_started"] is None and event.desc.startswith("State Changes to <b>Publication Requested"):
                item["iesg_started"] = [event.time.isoformat(), event.desc]
            if  item["iesg_started"] is None and event.desc.startswith("IESG state changed to <b>Publication Requested"):
                item["iesg_started"] = [event.time.isoformat(), event.desc]
            if  item["iesg_started"] is None and event.desc.startswith("IESG state changed to <b>Last Call Requested"):
                item["iesg_started"] = [event.time.isoformat(), event.desc]
            if  item["iesg_started"] is None and event.desc.startswith("Draft added in state Publication Requested"):
                item["iesg_started"] = [event.time.isoformat(), event.desc]
            if  item["iesg_started"] is None and event.desc.startswith("Draft Added") and event.desc.endswith("in state Publication Requested"):
                item["iesg_started"] = [event.time.isoformat(), event.desc]
            if  item["iesg_started"] is None and event.desc.startswith("Draft Added") and event.desc.endswith("in state AD Evaluation"):
                item["iesg_started"] = [event.time.isoformat(), event.desc]
            if  item["iesg_started"] is None and event.desc.startswith("Draft Added") and event.desc.endswith("in state IESG Evaluation"):
                item["iesg_started"] = [event.time.isoformat(), event.desc]
            if  item["iesg_started"] is None and event.desc.startswith("Draft Added") and event.desc.endswith("in state Last Call Requested"):
                item["iesg_started"] = [event.time.isoformat(), event.desc]
            if  item["iesg_started"] is None and event.desc.startswith("State changed to <b>AD Evaluation"):
                item["iesg_started"] = [event.time.isoformat(), event.desc]
            if  item["iesg_started"] is None and event.desc.startswith("State Changes to <b>AD Evaluation"):
                item["iesg_started"] = [event.time.isoformat(), event.desc]
            if  item["iesg_started"] is None and event.desc.startswith("State changed to <b>IESG Evaluation"):
                item["iesg_started"] = [event.time.isoformat(), event.desc]
            if  item["iesg_started"] is None and event.desc.startswith("State Changes to <b>IESG Evaluation"):
                item["iesg_started"] = [event.time.isoformat(), event.desc]
            if  item["iesg_started"] is None and event.desc.startswith("State changed to <b>Last Call Requested"):
                item["iesg_started"] = [event.time.isoformat(), event.desc]
            if  item["iesg_started"] is None and event.desc.startswith("State Changes to <b>Last Call Requested"):
                item["iesg_started"] = [event.time.isoformat(), event.desc]
            if  item["iesg_started"] is None and event.desc.startswith("Last call sent"):
                item["iesg_started"] = [event.time.isoformat(), event.desc]
            if  item["iesg_started"] is None and event.desc.startswith("Ballot has been issued"):
                item["iesg_started"] = [event.time.isoformat(), event.desc]

            if  item["iesg_finished"] is None and event.desc.startswith("IESG has approved the document"):
                item["iesg_finished"] = [event.time.isoformat(), event.desc]
            if  item["iesg_finished"] is None and event.desc.startswith("State Changes to <b>Approved-announcement to be sent"):
                item["iesg_finished"] = [event.time.isoformat(), event.desc]

            if  item["rfc_editor_started"] is None and event.desc.startswith("Announcement was received by RFC Editor"):
                item["rfc_editor_started"] = [event.time.isoformat(), event.desc]
            if  item["rfc_editor_started"] is None and event.desc.startswith("Sent request for publication to the RFC Editor"):
                item["rfc_editor_started"] = [event.time.isoformat(), event.desc]
            if  item["rfc_editor_started"] is None and event.desc.startswith("ISE state changed to <b>Sent to the RFC Editor"):
                item["rfc_editor_started"] = [event.time.isoformat(), event.desc]
            if  item["rfc_editor_started"] is None and event.desc.startswith("IAB state changed to <b>Sent to the RFC Editor"):
                item["rfc_editor_started"] = [event.time.isoformat(), event.desc]
            if  item["rfc_editor_started"] is None and event.desc.startswith("State changed to <b>RFC Ed Queue"):
                item["rfc_editor_started"] = [event.time.isoformat(), event.desc]
            if  item["rfc_editor_started"] is None and event.desc.startswith("State Changes to <b>RFC Ed Queue"):
                item["rfc_editor_started"] = [event.time.isoformat(), event.desc]
            if  item["rfc_editor_started"] is None and event.desc.startswith("RFC Editor state changed to"):
                item["rfc_editor_started"] = [event.time.isoformat(), event.desc]

    if rfc.stream == "IETF" and item["iesg_started"] is None:
        print(f"    Could not identify start of IESG processing for {rfc.doc_id}")
    if rfc.stream == "IETF" and item["iesg_finished"] is None:
        print(f"    Could not identify end of IESG processing for {rfc.doc_id}")
    if item["rfc_editor_started"] is None:
        print(f"    Could not identify start of RFC Editor processing for {rfc.doc_id}")

    rfcs.append(item)


with open("data/rfc-history.json", "w") as outf:
    json.dump(rfcs, outf, indent=3)


