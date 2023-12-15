# Copyright (C) 2023 University of Glasgow
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

import glob

import email.utils
import json
import sys

from datetime    import timedelta
from dataclasses import dataclass, field
from typing      import List, Dict, Optional, Iterator

from ietfdata.datatracker     import *
from ietfdata.datatracker_ext import *
from ietfdata.mailarchive2    import *

class Participant:
    person_id   : Optional[str]
    identifiers : Dict[str,List[str]]
    names       : List[str]

    def __init__(self, person_id: Optional[str] = None):
        self.person_id   = person_id
        self.identifiers = {}
        self.names       = []
        print(f"Participant({id(self)}) created ({self.person_id})")


    def add_identifier(self, ident_type:str, ident_value:str):
        if ident_type not in self.identifiers:
            self.identifiers[ident_type] = [ident_value]
            print(f"Participant({id(self)}) add_identifier: {ident_type} -> {ident_value}")
        else:
            if ident_value not in self.identifiers[ident_type]:
                self.identifiers[ident_type].append(ident_value)
                print(f"Participant({id(self)}) add_identifier: {ident_type} -> {ident_value}")
            else:
                print(f"Participant({id(self)}) has_identifier: {ident_type} -> {ident_value}")


    def add_name(self, name: str):
        if name not in self.names:
            self.names.append(name)
            print(f"Participant({id(self)}) add_name: {name}")
        else:
            print(f"Participant({id(self)}) has_name: {name}")


    def num_idents(self) -> int:
        count = 0
        for ident_type in self.identifiers:
            count += len(self.identifiers[ident_type])
        return count


    def merge_into(self, other):
        print(f"Participant({id(self)}) merge data into Participant({id(other)})")
        for ident_type in self.identifiers:
            for ident_value in self.identifiers[ident_type]:
                other.add_identifier(ident_type, ident_value)
        for name in self.names:
            other.add_name(name)
        self.identifiers = {}
        self.names = []


    def __repr__(self) -> str:
        return f"Participant({id(self)}){str(self.names), str(self.identifiers)}"



class ParticipantDB:
    pid: int
    idents: Dict[str,Dict[str,Participant]]
    names: Dict[str,List[Participant]]
    people: set[Participant]

    def __init__(self, path:Optional[Path] = None):
        self.pid = 0
        self.idents = {}
        self.people = set()
        self.names = {}
        if path is not None:
            with open(path, "r") as inf:
                saved_data = json.load(inf)
                for pid in saved_data:
                    person = Participant(pid)
                    self.people.add(person)
                    for ident_type in saved_data[pid]:
                        if ident_type == "name":
                            for name in saved_data[pid]["name"]:
                                self.add_name(person, name)
                        else:
                            for ident_value in saved_data[pid][ident_type]:
                                person.add_identifier(ident_type, ident_value)
                                if not ident_type in self.idents:
                                    self.idents[ident_type] = {}
                                self.idents[ident_type][ident_value] = person
                    pid_int = int(pid[4:])
                    if pid_int > self.pid:
                        self.pid = pid_int


    def save(self, path:Path):
        people = {}
        for person in self.people:
            if person.person_id is None:
                self.pid += 1
                person.person_id = f"PID:{self.pid:06}"
            people[person.person_id] = {"names": person.names} | person.identifiers
        with open(path, "w") as outf:
            json.dump(people, outf, indent=3, sort_keys=True)


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
                print(f"Participant({id(person)}) already_exists: {ident_type} -> {ident_value}")
        return person


    def person_with_name_email(self, name: str, email_addr: str) -> Participant:
        """
        Given a name and an email address, for example as might be extracted from an
        email "From:" header, try to find an existing participant. This uses a
        number of heuristics if there is no exact match.
        """

        # Decode DMARC (e.g., arnaud.taddei=40broadcom.com@dmarc.ietf.org -> arnaud.taddei@broadcom.com)
        if email_addr.endswith("@dmarc.ietf.org"):
            email_addr = email_addr[:-15].replace("=40", "@")

        # Try to match on the email address:
        if self.has_identifier("email", email_addr):
            p = self.person_with_identifier("email", email_addr)
            self.add_name(p, name)
            return p

        # Try to match on the base email address:
        if "@" in email_addr:
            local, remote = email_addr.rsplit("@", 1)
            if local.count("+") == 1:
                base, suffix = local.rsplit("+", 1)
                email_base = F"{base}@{remote}"
                if self.has_identifier("email", email_base):
                    p = self.person_with_identifier("email", email_base)
                    self.add_name(p, email_name)
                    return p

        # Try to match on the name:
        p = self.person_with_name(name)
        self.add_identifier(p, "email", email_addr)
        return p
        
    def person_with_name(self, name: str) -> Participant:
        # Try to match on the name:
        for suffix in [" via Datatracker", " via RT"]:
            if name.endswith(suffix):
                name = name[:-len(suffix)]

        for n in names_to_try(name, ""):
            people = self.names.get(n.lower(), [])
            if len(people) == 1:
                print(f"person_with_name: {name} -> Participant({id(people[0])}) (name match)")
                p = people[0]
                self.add_name(p, name)
                return p

        print(f"person_with_name: {name} failed to match")
        p = Participant()
        self.add_name(p, name)
        self.people.add(p)
        return p


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


    def add_name(self, person: Participant, name: str):
        if name == "":
            return
        person.add_name(name)
        if name.lower() not in self.names:
            self.names[name.lower()] = []
        if person not in self.names[name.lower()]:
            self.names[name.lower()].append(person)


    def add_identifier(self, person: Participant, ident_type: str, ident_value: str):
        person.add_identifier(ident_type, ident_value)
        if not ident_type in self.idents:
            self.idents[ident_type] = {}
            self.idents[ident_type][ident_value] = person
        else:
            if ident_value not in self.idents[ident_type]:
                self.idents[ident_type][ident_value] = person
            else:
                person.merge_into(self.idents[ident_type][ident_value])


    def has_identifier(self, ident_type: str, ident_value: str) -> bool:
        return ident_type in self.idents and ident_value in self.idents[ident_type]


    def _update_refs(self, from_person: Participant, to_person: Participant):
        """
        Private helper method: do not use.
        """
        print(f"Participant({id(from_person)}) -> Participant({id(to_person)})")
        for ident_type in self.idents:
            for ident_value in self.idents[ident_type]:
                if self.idents[ident_type][ident_value] == from_person:
                    self.idents[ident_type][ident_value] = to_person
                    print(f"    {ident_type} -> {ident_value}")
        for name in to_person.names:
            if from_person in self.names[name.lower()]:
                self.names[name.lower()].remove(from_person)
            if to_person not in self.names[name.lower()]:
                self.names[name.lower()].append(to_person)
                print(f"    name -> {name}")

if __name__ == "__main__":
    if len(sys.argv) == 2:
        old_path = None
        new_path = Path(sys.argv[1])
    elif len(sys.argv) == 3:
        old_path = Path(sys.argv[1])
        new_path = Path(sys.argv[2])
    else:
        print("Usage: python3 -m ietfdata.tools.participants [new.json]")
        print("   or: python3 -m ietfdata.tools.participants [old.json] [new.json]")
        sys.exit(1)

    print(f"*** ietfdata.tools.participants")
    if old_path is not None:
        print(f"Loading: {old_path}")

    if old_path == new_path:
        print("")
        print("ERROR: refusing to overwrite input file")
        sys.exit(2)

    pdb  = ParticipantDB(old_path)

    ignore = ["noreply@ietf.org",
              "noreply@github.com",
              "noreply=40github.com@dmarc.ietf.org",
              "notifications@github.com",
              "noreply@icloud.com",
              "support@github.com",
              
              ]

    # Fetch all IETF Datatracker people:
    dt  = DataTrackerExt(cache_timeout = timedelta(hours=12))
    dt_people = {}
    for dt_person in dt.people():
        dt_people[str(dt_person.resource_uri)] = dt_person
    
    # Add identifiers based on the IETF DataTracker:
    seen_addr = set()
    seen_people = set()

    for msg in dt.emails():
        if msg.address in ignore:
            continue
        p = pdb.person_with_identifier("email", msg.address)
        pdb.identifies_same_person("email", msg.address, "dt_person_uri", str(msg.person))
        if msg.person is not None and str(msg.person) not in seen_people:
            dt_person = dt_people[str(msg.person)]
            pdb.add_name(p, dt_person.name)
            pdb.add_name(p, dt_person.ascii)
            if dt_person.name_from_draft is not None and dt_person.name_from_draft != "":
                pdb.add_name(p, dt_person.name_from_draft)
            if dt_person.ascii_short is not None and dt_person.ascii_short != "":
                pdb.add_name(p, dt_person.ascii_short)
            if dt_person.plain is not None and dt_person.plain != "":
                pdb.add_name(p, dt_person.plain)
            seen_people.add(str(msg.person))
        seen_addr.add(msg.address)


    for resource in dt.person_ext_resources():
        if str(resource.name) == "/api/v1/name/extresourcename/webpage/":
            pdb.identifies_same_person("dt_person_uri", str(resource.person), "webpage", resource.value)
        if str(resource.name) == "/api/v1/name/extresourcename/github_username/":
            pdb.identifies_same_person("dt_person_uri", str(resource.person), "github_username", resource.value)
        if str(resource.name) == "/api/v1/name/extresourcename/gitlab_username/":
            pdb.identifies_same_person("dt_person_uri", str(resource.person), "gitlab_username", resource.value)


    # Add the mailing list addresses, and their -admin, -archive, and -request 
    # addresses, to the ignore list. These will never appear in the legitimate
    # "From:" lines but are frequently used by spammers.
    for n in ma.mailing_list_names():
        ignore.append(f"{n}@ietf.org")
        ignore.append(f"{n}-admin@ietf.org")
        ignore.append(f"{n}-archive@ietf.org")
        ignore.append(f"{n}-archive@lists.ietf.org")
        ignore.append(f"{n}-archive@megatron.ietf.org")
        ignore.append(f"{n}-request@ietf.org")


    # Add identifiers based on the IETF mailing list archive:
    seen_full = set()
    ma   = MailArchive()
    for n in ma.mailing_list_names():
        ml = ma.mailing_list(n)
        print(f"*** ")
        print(f"*** {ml.name()}")
        print(f"*** ")
        for envelope in ml.messages():
            print(f"{ml.name()}/{envelope.uid()}")
            for email_name, email_addr in email.utils.getaddresses(envelope.header("from")):
                email_full = f"{email_name} <{email_addr}>"
                if email_addr == "":
                    continue
                if email_addr in ignore:
                    continue
                if email_addr in seen_addr:
                    # This address is already associated with a datatracker uri
                    continue
                if email_name.endswith(" via RT"):
                    # This is an automated email from the RT issues tracker software
                    continue
                if email_full not in seen_full:
                    pdb.person_with_name_email(email_name, email_addr)
                    seen_full.add(email_full)


    print(f"Saving: {new_path}")
    pdb.save(new_path)


