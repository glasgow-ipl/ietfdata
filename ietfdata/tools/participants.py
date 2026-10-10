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

import email.utils
import logging
import os
import json
import sys

from datetime    import timedelta
from dataclasses import dataclass, field
from pathlib     import Path
from typing      import List, Dict, Optional, Iterator

class Participant:
    """
    The `Participant` class represents a single person that participates
    in Internet standards development.
    """
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
        """
        Add a name by which this participant is known.

        Multiple participants may have the same name.
        """
        if name not in self.names:
            self.log.debug(f"Participant({id(self)}) add_name: {name}")
            self.names.append(name)


    def add_identifier(self, ident_type:str, ident_value:str):
        """
        Add an identifier for this participant.

        The `ident_type` indicates the type of identifier being added to
        the participant, for example "dt_person_uri", "email", "webpage",
        "github_username", or "orcid". The `ident_value` is the value of
        the identifier.

        Example: `p.add_identifier("email", "csp@csperkins.org")`

        The expectation is that the identifier uniquely identifier the
        participant.
        """
        assert ident_type != "names"
        if ident_type not in self.identifiers:
            self.identifiers[ident_type] = [ident_value]
            self.log.debug(f"Participant({id(self)}) add_identifier: {ident_type} -> {ident_value}")
        else:
            if ident_value not in self.identifiers[ident_type]:
                self.log.debug(f"Participant({id(self)}) add_identifier: {ident_type} -> {ident_value}")
                if ident_type == "dt_person_uri" and len(self.identifiers[ident_type]) > 1:
                    self.log.info(f"Participant({id(self)}) adding additional dt_person_uri {ident_value}")
                    for dt_person_uri in self.identifiers[ident_type]:
                        self.log.info(f"Participant({id(self)}) existing dt_person_uri {dt_person_uri}")
                self.identifiers[ident_type].append(ident_value)
            else:
                self.log.debug(f"Participant({id(self)}) has_identifier: {ident_type} -> {ident_value}")


    def num_idents(self) -> int:
        count = 0
        for ident_type in self.identifiers:
            count += len(self.identifiers[ident_type])
        return count


    def merge_into(self, other:Participant):
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



class Participants:
    """
    The `Participants` class represents the set of people that have been
    found to participate in Internet standards development.
    """
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


    def add_person_with_name(self, ident_type: str, ident_value: str, name:str) -> Participant:
        """
        Add a person with the specified identifier and name.

        If a person with that identifier already exists, the name is added
        to the existing person.

        Example: `pdb.add_person_with_name("email", "j.doe@example.org", "Jane Doe")
        """
        person = self.add_person(ident_type, ident_value)
        person.add_name(name)
        return person


    def add_person(self, ident_type: str, ident_value: str) -> Participant:
        """
        Add a person with the specified identifier.

        If a person with the specified identifier already exists, this has
        no effect.

        Example: `pdb.add_person("email", "j.doe@example.org")
        """
        if not ident_type in self.idents:
            self.idents[ident_type] = {}

        if ident_value not in self.idents[ident_type]:
            person = Participant()
            person.add_identifier(ident_type, ident_value)
            self.people.add(person)
            self.idents[ident_type][ident_value] = person
        else:
            person = self.idents[ident_type][ident_value]
            self.log.debug(f"Participant({id(person)}) already_exists: {ident_type} -> {ident_value}")
        return person


    def merge_people(self, ident_type1: str, ident_value1: str, ident_type2: str, ident_value2: str):
        """
        Specify that the two identifiers refer to the same person.

        Example: `pdb.merge_people("email", "csp@csperkins.org", "github_username", "csperkins")
        """
        if not ident_type1 in self.idents:
            self.idents[ident_type1] = {}
        if not ident_type2 in self.idents:
            self.idents[ident_type2] = {}

        if   ident_value1 not in self.idents[ident_type1] and ident_value2 not in self.idents[ident_type2]:
            # Neither identifier represents a known person
            self.add_person(ident_type1, ident_value1)
            self.merge_people(ident_type1, ident_value1, ident_type2, ident_value2)
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

