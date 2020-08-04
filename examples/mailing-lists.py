# Copyright (C) 2020 University of Glasgow
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

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pathlib                  import Path

import ietfdata.datatracker as dt
import ietfdata.mailarchive as mailarchive

from ietfdata.mailhelper_headerdata      import *
from ietfdata.mailhelper_datatracker     import *

datatracker = dt.DataTracker(cache_dir=Path("cache"))
archive = mailarchive.MailArchive(cache_dir=Path("cache"), helpers=[HeaderDataMailHelper(), DatatrackerMailHelper()])

def pretty_print_message_metadata(msg: mailarchive.MailingListMessage):
    subject = msg.message["Subject"].replace('\n', "\\n")
    string = f"{msg.metadata('from_name'):50s} | {msg.metadata('from_addr'):30s} | {str(msg.metadata('from_person').id) if msg.metadata('from_person') is not None else '--':6s} | {msg.metadata('timestamp'):%Y-%m-%d %H:%M} | {subject:30s}"
    for document in msg.metadata("related_docs"):
        name = document.name
        if document.rfc is not None:
            name = f"RFC{document.rfc}"
        string += f"\n\tRelated Document: {document.title} ({name})"
    return string

for ml_name in ["rfced-future"]:
    ml = archive.mailing_list(ml_name)
    ml.update()
    print(ml_name)
    
    for thread in ml.threads():
        first_index, first_message = thread.messages[0]
        print("--|", pretty_print_message_metadata(ml.message(first_index)))
        for index, message in thread.messages[1:]:
            print("  |", pretty_print_message_metadata(ml.message(index)))
        print()

    print()

    # filter by Person
    print("Filter by Person")
    for index, im in ml.messages(from_person=datatracker.person_from_email("csp@csperkins.org")):
        print(f"  {pretty_print_message_metadata(im)}")
    print()

    # filter by Document
    print("Filter by Document")
    for index, im in ml.messages(related_doc=datatracker.document_from_draft("draft-carpenter-rfc-principles")):
        print(f"  {pretty_print_message_metadata(im)}")

print()

# archive-wide searching
ml = archive.mailing_list("fdt")
ml.update()
ml = archive.mailing_list("abnf-discuss")
ml.update()

print("Archive-wide searching")
for msg_id, msg in archive.messages(from_addr="Stephen.McQuistin@glasgow.ac.uk"):
    list_name, msg_index = msg_id
    print(f"{list_name:15s} | {pretty_print_message_metadata(msg)}")
