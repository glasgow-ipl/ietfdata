# Copyright (C) 2023-2026 University of Glasgow
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

import logging
import os
import sys

from pathlib                     import Path
from ietfdata.datatracker_ext    import DataTrackerExt
from ietfdata.dt_backend         import DTBackendArchive
from ietfdata.mailarchive3       import MailArchive
from ietfdata.tools.participants import Participant, Participants

if __name__ == "__main__":
    logging.basicConfig(level=os.environ.get("IETFDATA_LOGLEVEL", "INFO"))
    log = logging.getLogger("ietfdata")

    if len(sys.argv) == 4:
        dt_sqlite_file = sys.argv[1]
        ma_sqlite_file = sys.argv[2]
        new_path       = Path(sys.argv[3])
    else:
        print("")
        print("This script performs entity resolution on IETF participants. It reads")
        print("from the datatracker and mailarchive to associate the many different")
        print("identifiers used by each participant with a 'PID' number that can be")
        print("used to uniquely idenitify that participant.")
        print("")
        print(f"Usage: python3 -m ietfdata.tools.participants_ietf <ietfdata-dt.sqlite> <ietfdata-ma.sqlite> <participants.json>")
        print("")
        sys.exit(1)

    print(f"*** ietfdata.tools.participants_ietf")

    pdb  = Participants()

    ignore = ["noreply@ietf.org",
              "noreply@github.com",
              "noreply=40github.com@dmarc.ietf.org",
              "notifications@github.com",
              "noreply@icloud.com",
              "noname@noname.com",
              "messenger@webex.com",
              "tracker-forces@mip4.org", # FORCES issue tracker
              "tracker-forces@MIP4.ORG", # FORCES issue tracker
              "tracker-mip6@mip4.org",   # Mobile IPv6 issue tracker
              "tracker-mip4@mip4.org",   # Mobile IPv4 issue tracker
              "tracker-mip4@levkowetz.com",
              "3761bis@frobbit.se",      # 3761bis issue tracker
              "ietf-action@ietf.org",    # IETF issues tracker
              "ctp_issues@danforsberg.info", # Seamoby CTP issue tracker
             ]

    # Add identifiers based on the IETF DataTracker:
    seen_addr = set()
    dt  = DataTrackerExt(DTBackendArchive(dt_sqlite_file))

    print("Finding participants in IETF datatracker: people")
    for dt_person in dt.people():
        pdb.add_person("dt_person_uri", str(dt_person.resource_uri))
        # Add names:
        if dt_person.name != "":
            pdb.add_person_with_name("dt_person_uri", str(dt_person.resource_uri), dt_person.name)
        if dt_person.name_from_draft is not None and dt_person.name_from_draft != "":
            pdb.add_person_with_name("dt_person_uri", str(dt_person.resource_uri), dt_person.name_from_draft)
        if dt_person.ascii != "":
            pdb.add_person_with_name("dt_person_uri", str(dt_person.resource_uri), dt_person.ascii)
        if dt_person.ascii_short is not None and dt_person.ascii_short != "":
            pdb.add_person_with_name("dt_person_uri", str(dt_person.resource_uri), dt_person.ascii_short)
        if dt_person.plain != "":
            pdb.add_person_with_name("dt_person_uri", str(dt_person.resource_uri), dt_person.plain)


    print("Finding participants in IETF datatracker: emails")
    for msg in dt.emails():
        if msg.address in ignore:
            continue
        pdb.add_person("email", msg.address)
        pdb.merge_people("email", msg.address, "dt_person_uri", str(msg.person))
        if msg.address.lower() != msg.address:
            pdb.add_person("email", msg.address.lower())
            pdb.merge_people("email", msg.address.lower(), "email", msg.address)
            log.debug(f"case match {str(msg.person):30} {msg.address} <-> {msg.address.lower()}")
        seen_addr.add(msg.address)

    print("Finding participants in IETF datatracker: person_ext_resources")
    for resource in dt.person_ext_resources():
        log.debug(str(resource.resource_uri))
        if str(resource.name) == "/api/v1/name/extresourcename/webpage/":
            pdb.merge_people("dt_person_uri", str(resource.person), "webpage", resource.value)
        if str(resource.name) == "/api/v1/name/extresourcename/github_username/":
            pdb.merge_people("dt_person_uri", str(resource.person), "github_username", resource.value)
        if str(resource.name) == "/api/v1/name/extresourcename/gitlab_username/":
            pdb.merge_people("dt_person_uri", str(resource.person), "gitlab_username", resource.value)
        if str(resource.name) == "/api/v1/name/extresourcename/orcid/":
            pdb.merge_people("dt_person_uri", str(resource.person), "orcid", resource.value)

    # FIXME: extract participants from DocumentAuthor

    # FIXME: extract participants from Internet-draft submissions

    # FIXME: extract participants from meeting registration data

    # FIXME: extract participants from IPR disclosures


    # Add identifiers based on the IETF mailing list archive:
    seen_full = set()
    ma   = MailArchive(ma_sqlite_file)

    # Add the mailing list addresses, and their -admin, -archive, and -request 
    # addresses, to the ignore list. These will never appear in the legitimate
    # "From:" lines but are frequently used by spammers.
    for n in ma.mailing_list_names():
        ignore.append(f"{n}@ietf.org")
        ignore.append(f"{n}-admin@ietf.org")
        ignore.append(f"{n}-archive@ietf.org")
        ignore.append(f"{n}-archive@lists.ietf.org")
        ignore.append(f"{n}-archive@megatron.ietf.org")
        ignore.append(f"{n}-bounces@ietf.org")
        ignore.append(f"{n}-request@ietf.org")

    for ml_name in ma.mailing_list_names():
        print(f"Finding participants in IETF mailarchive: {ml_name}")
        ml = ma.mailing_list(ml_name)
        log.info(f"{ml.name()}")
        for envelope in ml.messages():
            from_addr = envelope.from_()
            if from_addr is None:
                continue

            email_name = from_addr.display_name
            email_addr = from_addr.addr_spec
            email_full = f"{email_name} <{email_addr}>"

            if email_addr == "":
                continue
            if email_addr in ignore:
                continue
            if email_addr.startswith(f"{ml_name}-bounces@"):
                continue
            if email_addr.lower().startswith("mailer-daemon@"):
                continue
            if email_addr in seen_addr:
                # This address is already associated with a datatracker uri
                continue
            if email_name.endswith(" via RT") or email_name.endswith(" via Datatracker"):
                # Discard automated emails
                continue
            if email_name.startswith("Datatracker on behalf of"):
                # Discard automated emails
                continue
            if email_full not in seen_full:
                pdb.add_person("email", email_addr)
                person = dt.person_from_name_email(email_name, email_addr)
                if person is not None and envelope.header("X-Spam-Flag") != "YES":
                    pdb.merge_people("email", email_addr, "dt_person_uri", str(person.resource_uri))
                    if email_name is not None and email_name != "":
                        pdb.add_person_with_name("dt_person_uri", str(person.resource_uri), email_name)
                if email_name is not None and email_name != "" and envelope.header("X-Spam-Flag") != "YES":
                    pdb.add_person_with_name("email", email_addr, email_name)
                if email_addr.lower() != email_addr:
                    pdb.add_person("email", email_addr.lower())
                    pdb.merge_people("email", email_addr.lower(), "email", email_addr)
                    log.debug(f"case match {str(msg.person):30} {email_addr} <-> {email_addr.lower()}")
                seen_full.add(email_full)

    print(f"Saving {new_path}")
    pdb.save(new_path)


