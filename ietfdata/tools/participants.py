# Copyright (C) 2023-2025 University of Glasgow
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

import email.utils
import logging
import json
import sys

from datetime    import timedelta
from dataclasses import dataclass, field
from typing      import List, Dict, Optional, Iterator

from ietfdata.datatracker     import *
from ietfdata.datatracker_ext import *
from ietfdata.mailarchive3    import *

class Participant:
    log         : logging.Logger
    person_id   : Optional[str]
    identifiers : Dict[str,List[str]]
    names       : List[str]


    def __init__(self, person_id: Optional[str] = None):
        logging.basicConfig(level=os.environ.get("IETFDATA_LOGLEVEL", "INFO"))
        self.log         = logging.getLogger("ietfdata")
        self.person_id   = person_id
        self.identifiers = {}
        self.names       = []
        self.log.debug(f"Participant({id(self)}) created ({self.person_id})")


    def add_name(self, name:str):
        if name not in self.names:
            self.log.debug(f"Participant({id(self)}) add_name: {name}")
            self.names.append(name)


    def add_identifier(self, ident_type:str, ident_value:str):
        assert ident_type != "names"
        if ident_type not in self.identifiers:
            self.identifiers[ident_type] = [ident_value]
            self.log.debug(f"Participant({id(self)}) add_identifier: {ident_type} -> {ident_value}")
        else:
            if ident_value not in self.identifiers[ident_type]:
                self.log.debug(f"Participant({id(self)}) add_identifier: {ident_type} -> {ident_value}")
                if ident_type == "dt_person_uri" and len(self.identifiers[ident_type]) > 1:
                    self.log.warning(f"Participant({id(self)}) adding additional dt_person_uri {ident_value}")
                    for dt_person_uri in self.identifiers[ident_type]:
                        self.log.warning(f"Participant({id(self)})          existing dt_person_uri {dt_person_uri}")
                self.identifiers[ident_type].append(ident_value)
            else:
                self.log.debug(f"Participant({id(self)}) has_identifier: {ident_type} -> {ident_value}")


    def num_idents(self) -> int:
        count = 0
        for ident_type in self.identifiers:
            count += len(self.identifiers[ident_type])
        return count


    def merge_into(self, other):
        self.log.debug(f"Participant({id(self)}) merge data into Participant({id(other)})")
        for name in self.names:
            other.add_name(name)
        self.names = []
        for ident_type in self.identifiers:
            for ident_value in self.identifiers[ident_type]:
                other.add_identifier(ident_type, ident_value)
        self.identifiers = {}


    def __repr__(self) -> str:
        return f"Participant({id(self)}){str(self.identifiers)}"



class ParticipantDB:
    log: logging.Logger
    pid: int
    idents: Dict[str,Dict[str,Participant]]
    people: set[Participant]

    def __init__(self):
        logging.basicConfig(level=os.environ.get("IETFDATA_LOGLEVEL", "INFO"))
        self.log = logging.getLogger("ietfdata")
        self.pid = 0
        self.idents = {}
        self.people = set()


    def save(self, path:Path):
        people = {}
        for person in self.people:
            if person.person_id is None:
                self.pid += 1
                person.person_id = f"PID:{self.pid:06}"
            people[person.person_id] = person.identifiers
            people[person.person_id]["names"] = person.names
        with open(path, "w") as outf:
            json.dump(people, outf, indent=3, sort_keys=True)


    def person_with_name(self, ident_type: str, ident_value: str, name:str) -> None:
        if ident_type in self.idents:
            if ident_value in self.idents[ident_type]:
                person = self.idents[ident_type][ident_value]
                person.add_name(name)


    def person_with_identifier(self, ident_type: str, ident_value: str) -> Participant:
        """
        Specify that there is a person identified by the specific identifer.

        Example: `pdb.person_with_identifier("email", "j.doe@example.org")
        """
        person = None
        if not ident_type in self.idents:
            person = Participant()
            person.add_identifier(ident_type, ident_value)
            self.people.add(person)
            self.idents[ident_type] = {}
            self.idents[ident_type][ident_value] = person
        else:
            if ident_value not in self.idents[ident_type]:
                person = Participant()
                person.add_identifier(ident_type, ident_value)
                self.people.add(person)
                self.idents[ident_type][ident_value] = person
            else:
                person = self.idents[ident_type][ident_value]
                self.log.debug(f"Participant({id(person)}) already_exists: {ident_type} -> {ident_value}")
        return person


    def identifies_same_person(self, ident_type1:str, ident_value1: str, ident_type2:str, ident_value2: str):
        """
        Specify that the two identifiers refer to the same person.

        Example: `pdb.identifies_same_person("email", "j.doe@example.org", "name", "Jane Doe")
        """
        if not ident_type1 in self.idents:
            self.idents[ident_type1] = {}
        if not ident_type2 in self.idents:
            self.idents[ident_type2] = {}

        if   ident_value1 not in self.idents[ident_type1] and ident_value2 not in self.idents[ident_type2]:
            # Neither identifier represents a known person
            self.person_with_identifier(ident_type1, ident_value1)
            self.identifies_same_person(ident_type1, ident_value1, ident_type2, ident_value2)
        elif ident_value1     in self.idents[ident_type1] and ident_value2 not in self.idents[ident_type2]:
            # There is a person associated with the first identifier but not the second
            person = self.idents[ident_type1][ident_value1]
            person.add_identifier(ident_type2, ident_value2)
            self.idents[ident_type2][ident_value2] = person
        elif ident_value1 not in self.idents[ident_type1] and ident_value2     in self.idents[ident_type2]:
            # There is a person associated with the second identifier but not the first
            person = self.idents[ident_type2][ident_value2]
            person.add_identifier(ident_type1, ident_value1)
            self.idents[ident_type1][ident_value1] = person
        elif ident_value1     in self.idents[ident_type1] and ident_value2     in self.idents[ident_type2]:
            # Both identifiers are associated with people
            person1 = self.idents[ident_type1][ident_value1]
            person2 = self.idents[ident_type2][ident_value2]
            if person1 == person2:
                # Both identifiers are associated with the same person, nothing to do
                pass
            else:
                # Both identifiers exist but refer to different people that
                # must be merged into one.
                # If one person has a person_id assigned but the other does
                # not, merge the identifiers for the person that does not have
                # a person_id into the record for the person that does.
                if   person1.person_id is     None and person2.person_id is     None:
                    person2.merge_into(person1)
                    self._update_refs(person2, person1)
                    self.people.remove(person2)
                elif person1.person_id is not None and person2.person_id is     None:
                    person2.merge_into(person1)
                    self._update_refs(person2, person1)
                    self.people.remove(person2)
                elif person1.person_id is     None and person2.person_id is not None:
                    person1.merge_into(person2)
                    self._update_refs(person1, person2)
                    self.people.remove(person1)
                elif person1.person_id is not None and person2.person_id is not None:
                    # If both people have a person_id, merge the records and leave
                    # behind a "replaced_by" field to indicate that the merge took
                    # place.
                    if person2.num_idents() > person1.num_idents():
                        person2.merge_into(person1)
                        self._update_refs(person2, person1)
                        person2.add_identifier("replaced_by", person1.person_id)
                    else:
                        person1.merge_into(person2)
                        self._update_refs(person1, person2)
                        person1.add_identifier("replaced_by", person2.person_id)
                else:
                    raise RuntimeError("This cannot happen (1)")
        else:
            raise RuntimeError("This cannot happen (2)")


    def _update_refs(self, from_person: Participant, to_person: Participant):
        """
        Private helper method: do not use.
        """
        self.log.debug(f"Participant({id(from_person)}) -> Participant({id(to_person)})")
        for ident_type in self.idents:
            for ident_value in self.idents[ident_type]:
                if self.idents[ident_type][ident_value] == from_person:
                    self.idents[ident_type][ident_value] = to_person
                    self.log.debug(f"    {ident_type} -> {ident_value}")



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
        print(f"Usage: python3 -m ietfdata.tools.participants <ietfdata-dt.sqlite> <ietfdata-ma.sqlite> <participants.json>")
        print("")
        sys.exit(1)

    print(f"*** ietfdata.tools.participants")

    pdb  = ParticipantDB()

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

    print("Finding participants in IETF datatracker: names")
    for dt_person in dt.people():
        log.debug(f"{str(dt_person.resource_uri)}")
        pdb.person_with_identifier("dt_person_uri", str(dt_person.resource_uri))
        # Add names:
        if dt_person.name != "":
            pdb.person_with_name("dt_person_uri", str(dt_person.resource_uri), dt_person.name)
        if dt_person.name_from_draft is not None and dt_person.name_from_draft != "":
            pdb.person_with_name("dt_person_uri", str(dt_person.resource_uri), dt_person.name_from_draft)
        if dt_person.ascii != "":
            pdb.person_with_name("dt_person_uri", str(dt_person.resource_uri), dt_person.ascii)
        if dt_person.ascii_short is not None and dt_person.ascii_short != "":
            pdb.person_with_name("dt_person_uri", str(dt_person.resource_uri), dt_person.ascii_short)
        if dt_person.plain != "":
            pdb.person_with_name("dt_person_uri", str(dt_person.resource_uri), dt_person.plain)


    print("Finding participants in IETF datatracker: emails")
    for msg in dt.emails():
        log.debug(f"{msg.address}")
        if msg.address in ignore:
            continue
        pdb.person_with_identifier("email", msg.address)
        pdb.identifies_same_person("email", msg.address, "dt_person_uri", str(msg.person))
        seen_addr.add(msg.address)


    print("Finding participants in IETF datatracker: external resources")
    for resource in dt.person_ext_resources():
        log.debug(str(resource.resource_uri))
        if str(resource.name) == "/api/v1/name/extresourcename/webpage/":
            pdb.identifies_same_person("dt_person_uri", str(resource.person), "webpage", resource.value)
        if str(resource.name) == "/api/v1/name/extresourcename/github_username/":
            pdb.identifies_same_person("dt_person_uri", str(resource.person), "github_username", resource.value)
        if str(resource.name) == "/api/v1/name/extresourcename/gitlab_username/":
            pdb.identifies_same_person("dt_person_uri", str(resource.person), "gitlab_username", resource.value)
        if str(resource.name) == "/api/v1/name/extresourcename/orcid/":
            pdb.identifies_same_person("dt_person_uri", str(resource.person), "orcid", resource.value)


    # Add identifiers based on the IETF mailing list archive:
    print("Finding participants in IETF mailarchive")
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
                pdb.person_with_identifier("email", email_addr)
                person = dt.person_from_name_email(email_name, email_addr)
                if person is not None and envelope.header("X-Spam-Flag") != "YES":
                    pdb.identifies_same_person("email", email_addr, "dt_person_uri", str(person.resource_uri))
                    if email_name is not None and email_name != "":
                        pdb.person_with_name("dt_person_uri", str(person.resource_uri), email_name)
                if email_name is not None and email_name != "" and envelope.header("X-Spam-Flag") != "YES":
                    pdb.person_with_name("email", email_addr, email_name)
                seen_full.add(email_full)

    print(f"Saving {new_path}")
    pdb.save(new_path)


