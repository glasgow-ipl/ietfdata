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

import json
import sys
import textwrap

from pathlib import Path
from typing  import List, Dict, Optional, Iterator

from ietfdata.datatracker     import *
from ietfdata.datatracker_ext import *
from ietfdata.mailarchive2    import *

class Organisation:
    _preferred_name : Optional[str]
    _names          : List[str]
    _domain         : Optional[str]

    def __init__(self, name:str) -> None:
        self._preferred_name = None
        self._names          = [name]
        self._domain         = None


    def preferred_name(self) -> Optional[str]:
        return self._preferred_name


    def names(self) -> List[str]:
        return self._names


    def domain(self) -> Optional[str]:
        return self._domain


    def set_preferred_name(self, name: str) -> None:
        if name in self._names and self._preferred_name is None:
            self._preferred_name = name
        else:
            raise RuntimeError(f"Cannot set preferred name: {self._preferred_name} -> {name}")


    def add_name(self, name:str) -> None:
        if name not in self._names:
            self._names.append(name)


    def set_domain(self, domain: str) -> None:
        if self._domain is None:
            self._domain = domain
        elif self._domain == domain:
            pass
        else:
            raise RuntimeError(f"Cannot set domain: {self._domain} -> {domain}")



class OrganisationDB:
    _organisations : Dict[str,Organisation]
    _domains       : Dict[str,Organisation]

    def __init__(self) -> None:
        self._organisations = {}
        self._domains       = {}


    def get_domains(self) -> List[str]:
        return sorted(list(self._domains.keys()))

    
    def get_organisations(self) -> List[str]:
        return sorted(list(self._organisations.keys()))


    def organisation_exists(self, name: str) -> None:
        """
        Indicate that an organisation with the specified `name` exists
        """
        if name not in self._organisations:
            print(f"Organisation exists: \"{name}\"")
            self._organisations[name] = Organisation(name)


    def organisation_has_domain(self, name:str, domain:str) -> None:
        """
        Indicate that an organisation with the specified `name` has sole
        use of the `domain`
        """
        self.organisation_exists(name)
        if domain not in self._domains:
            print(f"Organisation has domain: \"{name}\" -> \"{domain}\"")
            self._organisations[name].set_domain(domain)
            self._domains[domain] = self._organisations[name]
        else:
            if self._domains[domain] == self._organisations[name]:
                # The domain has already been recorded as belonging to this organisation
                pass
            else:
                # There is another organisation with this domain. Merge the two, since
                # domains are supposed to uniquely idenitify organisations.
                self._merge(self._organisations[name], self._domains[domain])


    def organisation_has_preferred_name(self, name: str) -> None:
        """
        Indicates that `name` is the preferred name for an organisation.
        """
        self.organisation_exists(name)
        print(f"Organisation has preferred name: \"{name}\"")
        self._organisations[name].set_preferred_name(name)


    def organisations_match(self, name1: str, name2: str) -> None:
        """
        Indicate that `name1` and `name2` exist and are the same organisation
        so should merge into one.
        """
        self.organisation_exists(name1)
        self.organisation_exists(name2)
        self._merge(self._organisations[name1], self._organisations[name2])


    def _merge(self, org1: Organisation, org2: Organisation) -> None:
        if org1 == org2:
            return
        print(f"Merging organisations: {org1.names()} -> {org2.names()}")
        # Merge names from org1 into org2:
        for name in org1.names():
            org2.add_name(name)
        # Merge domain from org1 into org2:
        domain = org1.domain()
        if domain is not None:
            if org2.domain() is None:
                org2.set_domain(domain)
            elif org2.domain() == domain:
                pass
            else:
                raise RuntimeError(f"Cannot merge organisations with mismatched domains: {org1.domain()} != {org2.domain()}")
        # Merge preferred name from org1 into org2:
        preferred = org1.preferred_name()
        if preferred is not None:
            if org2.preferred_name() is None:
                org2.set_preferred_name(preferred)
            elif org2.preferred_name() == preferred:
                pass
            else:
                raise RuntimeError("Cannot merge organisations with mismatched preferred name")
        # Change all references to org1 by name to refer to org2:
        for name, org in self._organisations.items():
            if name in org1.names():
                self._organisations[name] = org2
        # Change all references to org1 by dmomain to refer to org2:
        for domain, org in self._domains.items():
            if domain == org1.domain():
                self._domains[domain] = org2


    # FIXME
    def normalise(self, name: str, domain_hint: Optional[str]=None) -> str:
        # Normalise the organisation name to a canonical form. Uses a
        # combination of a rule-based approach and information given
        # in calls to the other methods on this class to perform the
        # normalisation.
        #
        # The `domain_hint`, if provided, is a hint that can be used
        # to help the normalisation process. The `domain_hint` is not
        # stored.
        return name


    def dump(self, json_path: Path) -> None:
        found = []
        items = {}
        orgid = 0
        for name, org in self._organisations.items():
            if org not in found:
                orgid += 1
                item  = {"preferred_name": org.preferred_name(), "names": org.names(), "domain": org.domain()}
                items[f"ORG:{orgid:06}"] = item
                found.append(org)
        with open(json_path, "w") as outf:
            json.dump(items, outf, indent=3)


    def debug_dump(self) -> None:
        print("{")
        for name, org in self._organisations.items():
            print(f'  name {name} -> ("preferred_name": {org.preferred_name()}, "names": {org.names()}, "domain": {org.domain()})')
        for domain, org in self._domains.items():
            print(f'  domain {domain} -> ("preferred_name": {org.preferred_name()}, "names": {org.names()}, "domain": {org.domain()})')
        print("}")



# =============================================================================
# Helper functions for extracting affiliations from the datatracker:

def fix_affiliation(name:str) -> str:
    name = name.replace("\n", " ")
    return name


def record_affiliation(orgs: OrganisationDB, name:str, email:str) -> Optional[Tuple[str,str]]:
    # Clean-up malformed organisation names:
    name = fix_affiliation(name)

    # Record the organisation
    orgs.organisation_exists(name)

    # If the organisation name ends in a known company suffix, also record
    # the variant without the suffix and mark them as matching:
    for suffix in ["Ltd", "Inc", "Pty", "GmbH"]:
        for variant in [f", {suffix}.", f", {suffix}", f" {suffix}.", f" {suffix}"]: 
            if name.endswith(variant):
                bare_name = name[:-len(variant)]
                orgs.organisation_exists(bare_name)
                orgs.organisations_match(bare_name, name)
                break

    # If the organisation name ends in a known abbreviation, also record
    # the variant with the full name and mark them as matching:
    for abbr, full in [("Corp", "Corporation"),
                       ("Univ", "University")]:
        for variant in [f", {abbr}.", f", {abbr}", f" {abbr}.", f" {abbr}"]: 
            if name.endswith(variant):
                full_name = f"{name[:-len(variant)]} {full}"
                orgs.organisation_exists(full_name)
                orgs.organisations_match(name, full_name)
                break

    # If the organisation name starts with a known abbreviation, also record
    # the variant with the full name and mark them as matching:
    for abbr, full in [("Univ", "University")]:
        for variant in [f"{abbr}. ", f"{abbr} "]: 
            if name.startswith(variant):
                full_name = f"{full} {name[len(variant):]}"
                orgs.organisation_exists(full_name)
                orgs.organisations_match(name, full_name)
                break

    # If the organisation name matches the domain, record the domain as
    # belonging to this organisation:
    org_domain = None
    if "@" in email:
        parts  = email.split("@")[1].split(".")
        for tld in ["com", "org", "edu"]:
            if len(parts) >= 2 and parts[-1] == tld:
                domain = f"{parts[-2]}.{parts[-1]}".lower()
                if domain in ["iana.com"]:
                    print(f"Domain in blocklist: {domain}")
                else:
                    if name.lower() == parts[-2].lower():
                        # Organisation name directly matches domain
                        orgs.organisation_has_domain(name, domain)
                        org_domain = (name, domain)
                    # elif name.replace(" ", "").lower() == parts[-2].lower():
                    #     # Organisation name, with spaces removed, matches domain
                    #     orgs.organisation_has_domain(name, domain)
                    #     org_domain = (name, domain)
    return org_domain


# =============================================================================
# Code to extract affiliations from the datatracker:

if __name__ == "__main__":
    if len(sys.argv) == 2:
        path = Path(sys.argv[1])
    else:
        print("Usage: python3 -m ietfdata.tools.affiliations [new.json]")
        sys.exit(1)

    print("*** ietfdata.tools.affiliations")

    orgs = OrganisationDB()

    dt = DataTracker(cache_timeout = timedelta(days=7))
    ri = RFCIndex(cache_dir = "cache")

    org_domains = []

    # Record affiliations for RFC authors
    print("Fetching affiliations for RFC authors:")
    for rfc in ri.rfcs(stream="IETF", since="1995-01"):
        #print(f"   {rfc.doc_id}: {textwrap.shorten(rfc.title, width=80, placeholder='...')}")
        dt_document = dt.document_from_rfc(rfc.doc_id)
        if dt_document is not None:
            for dt_author in dt.document_authors(dt_document):
                if dt_author.affiliation == "" or dt_author.email is None:
                    continue
                email  = dt.email(dt_author.email)
                org_domain = record_affiliation(orgs, dt_author.affiliation, email.address)
                if org_domain is not None and org_domain not in org_domains:
                    org_domains.append(org_domain)

    # Record affiliations based on meeting registrations
    for reg in dt.meeting_registrations():
        org_domain = record_affiliation(orgs, reg.affiliation, reg.email)
        if org_domain is not None and org_domain not in org_domains:
            org_domains.append(org_domain)
    
    # Merge affiliations that start with an affiliation that matched its domain.
    # e.g., "Cisco Belgique" starts with "Cisco", which matched "cisco.com", so
    # should be merged with Cisco
    for org_name in orgs.get_organisations():
        for name, domain in org_domains:
            if org_name.startswith(f"{name} "):
                orgs.organisations_match(org_name, name)


    orgs.dump(path)

