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
import logging
import sys
import textwrap

from pathlib import Path
from typing  import List, Dict, Optional, Iterator

from ietfdata.rfcindex        import *
from ietfdata.datatracker     import *
from ietfdata.datatracker_ext import *

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
        if name == self._preferred_name:
            pass
        elif name in self._names and self._preferred_name is None:
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
    _log           : logging.Logger
    _organisations : Dict[str,Organisation]   # Map from name to Organisation
    _domains       : Dict[str,Organisation]   # Map from domain to Organisation

    def __init__(self) -> None:
        logging.basicConfig(level=os.environ.get("IETFDATA_LOGLEVEL", "INFO"))
        self._log           = logging.getLogger("ietfdata")
        self._organisations = {}
        self._domains       = {}


    def get_domains(self) -> List[str]:
        return sorted(list(self._domains.keys()))


    def get_organisations(self) -> List[str]:
        return sorted(list(self._organisations.keys()))


    def add_organisation(self, name: str) -> None:
        """
        Indicate that an organisation with the specified `name` exists
        """
        if name not in self._organisations:
            self._log.debug(f"Add organisation: \"{name}\"")
            self._organisations[name] = Organisation(name)


    def add_domain_for_organisation(self, name:str, domain:str) -> None:
        """
        Indicate that an organisation with the specified `name` has sole
        use of the `domain`
        """
        self.add_organisation(name)
        if domain not in self._domains:
            self._log.debug(f"Add domain for organisation: \"{name}\" -> \"{domain}\"")
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


    def add_preferred_name_for_organisation(self, name: str) -> None:
        """
        Indicates that `name` is the preferred name for an organisation.
        """
        self.add_organisation(name)
        self._organisations[name].set_preferred_name(name)


    def organisation_has_domain(self, name:str) -> bool:
        if name not in self._organisations:
            return False
        return self._organisations[name].domain() != None


    def organisations_match(self, name1: str, name2: str) -> None:
        """
        Indicate that `name1` and `name2` exist and are the same organisation
        so should merge into one.
        """
        self.add_organisation(name1)
        self.add_organisation(name2)
        self._merge(self._organisations[name1], self._organisations[name2])


    def _merge(self, org1: Organisation, org2: Organisation) -> None:
        if org1 == org2:
            return
        self._log.debug(f"Merging organisations: {org1.names()} -> {org2.names()}")
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
# The OrganisationMatcher class extracts information from the IETF
# datatacker then uses the OrganisationDB and Organisation classes
# to organise that information and perform entity resolution.
#
# If you want to perform entity resolution across organisations, for
# example to combine data from W3C with data from the IETF, create a
# subclass of `OrganisationMatcher` with an additional method (e.g.,
# `find_organisations_w3c()`) that extracts the data for that other
# organisation and calls the `add()` method with that data. Use that
# subclass as follows:
#
#    om = OrganisationMatcherExt()   <- instantiate subclass
#    om.find_organisations_ietf()
#    om.find_organisations_w3c()     <- call additional method
#    om.consolidate_organisations()
#    om.dump(output_path)
#
# If you create such a subclass, the `__init__()` method of the
# subclass MUST call `super().__init__()` to correctly initialise
# things.

class OrganisationMatcher:
    _org_db : OrganisationDB
    _orgs   : set[Tuple[str,str]]

    def __init__(self):
        logging.basicConfig(level=os.environ.get("IETFDATA_LOGLEVEL", "INFO"))
        self._log    = logging.getLogger("ietfdata")
        self._org_db = OrganisationDB()
        self._orgs   = set()


    def add(self, organisation:Optional[str], email:str):
        blocklist = ["University"]
        if organisation is None or organisation == "" or organisation in blocklist:
            return
        self._orgs.add((organisation, email))


    def find_organisations_ietf(self, sqlite_file:str):
        """
        Search the IETF Datatracker to find organisations.

        This methods uses the IETF datatracker to extract information about
        organisations, then calls the `add()` method in this class to record
        that information.
        """
        dt = DataTracker(DTBackendArchive(sqlite_file))
        ri = RFCIndex(cache_dir = "data")

        print("Finding organisations in RFCs")
        for rfc in ri.rfcs(since="1995-01"):
            self._log.info(f"{rfc.doc_id}: {textwrap.shorten(rfc.title, width=80, placeholder='...')}")
            dt_document = dt.document_from_rfc(rfc.doc_id)
            if dt_document is not None:
                for dt_author in dt.document_authors(dt_document):
                    if dt_author.email is None:
                        self.add(dt_author.affiliation, "")
                    else:
                        email = dt.email(dt_author.email)
                        assert email is not None
                        self.add(dt_author.affiliation, email.address)

        print("Finding affiliations in internet-drafts")
        for submission in dt.submissions():
            self._log.info(f"{submission.name}-{submission.rev}")
            if submission.state != "/api/v1/name/draftsubmissionstatename/posted/":
                # Skip submissions that are not posted to the archive
                self._log.debug(f"Skipped submission in state {submission.state}")
                continue
            for author in submission.parse_authors():
                if "affiliation" not in author:
                    continue
                if "email" not in author:
                    self.add(author["affiliation"], "")
                else:
                    self.add(author["affiliation"], author["email"])

        print("Finding organisations in meeting registrations")
        for reg in dt.meeting_registrations():
            self.add(reg.affiliation, reg.email)


    def consolidate_organisations(self):
        print("Consolidating organisations (pass 1)")
        orgs_for_domain : Dict[str,List[str]] = {}
        for name, email in self._orgs:
            # Clean-up malformed organisation names:
            name = name.replace("\n", " ")

            # Record the organisation
            self._org_db.add_organisation(name)

            # If the organisation name ends in a known company suffix, also record
            # the variant without the suffix and mark them as matching:
            for suffix in ["Ltd", "Inc", "Pty", "GmbH"]:
                for variant in [f", {suffix}.", f", {suffix}", f" {suffix}.", f" {suffix}"]:
                    if name.endswith(variant):
                        bare_name = name[:-len(variant)]
                        self._org_db.add_organisation(bare_name)
                        self._org_db.organisations_match(bare_name, name)
                        break

            # If the organisation name ends in a known abbreviation, also record
            # the variant with the full name and mark them as matching:
            for abbr, full in [("Corp", "Corporation"),
                               ("Univ", "University")]:
                for variant in [f", {abbr}.", f", {abbr}", f" {abbr}.", f" {abbr}"]:
                    if name.endswith(variant):
                        full_name = f"{name[:-len(variant)]} {full}"
                        self._org_db.add_organisation(full_name)
                        self._org_db.organisations_match(name, full_name)
                        break

            # If the organisation name starts with a known abbreviation, also record
            # the variant with the full name and mark them as matching:
            for abbr, full in [("Univ", "University")]:
                for variant in [f"{abbr}. ", f"{abbr} "]:
                    if name.startswith(variant):
                        full_name = f"{full} {name[len(variant):]}"
                        self._org_db.add_organisation(full_name)
                        self._org_db.organisations_match(name, full_name)
                        break

            # # If the organisation name contains a "/", add variants with or without
            # # surrounding spaces and match as matching.
            # if " / " in name:
            #     no_slash = name.replace(" / ", "/")
            #     self._org_db.add_organisation(no_slash)
            #     self._org_db.organisations_match(name, no_slash)
            # elif "/ " in name:
            #     no_slash = name.replace("/ ", "/")
            #     self._org_db.add_organisation(no_slash)
            #     self._org_db.organisations_match(name, no_slash)
            # elif " /" in name:
            #     no_slash = name.replace(" /", "/")
            #     self._org_db.add_organisation(no_slash)
            #     self._org_db.organisations_match(name, no_slash)

            # If the organisation name matches the domain, record the domain as
            # belonging to this organisation:
            org_domain = None
            if email is not None and "@" in email:
                parts  = email.split("@")[1].split(".")
                for tld in ["com", "org", "edu"]:
                    if len(parts) >= 2 and parts[-1] == tld:
                        domain = f"{parts[-2]}.{parts[-1]}".lower()
                        if domain in ["iana.com", "linaro.com", "mit.org"]:
                            # print(f"    Domain in blocklist: {domain}")
                            pass
                        else:
                            if name.lower() == parts[-2].lower():
                                # Organisation name directly matches domain
                                self._org_db.add_domain_for_organisation(name, domain)
                                # If the organisation name has an initial upper case letter and
                                # the remaining letters are lower case, set as preferred name.
                                if name[0].upper() == name[0] and name[1:].lower() == name[1:]:
                                    self._org_db.add_preferred_name_for_organisation(name)
                            # Record the organisations used with this domain
                            if domain not in orgs_for_domain:
                                orgs_for_domain[domain] = []
                            if name not in orgs_for_domain[domain]:
                                orgs_for_domain[domain].append(name)

        print("Consolidating organisations (pass 2)")
        for org_name in self._org_db.get_organisations():
            for name, domain in self._orgs:
                if org_name == name:
                    self._org_db.organisations_match(org_name, name)
                elif org_name.lower() == name.lower():
                    # Merge organisations that differ only in case
                    self._log.debug(f"Organisations match (case): \"{name}\" -> \"{org_name}\"")
                    self._org_db.organisations_match(org_name, name)
                elif org_name.startswith(f"{name} "):
                    # Merge organisations that start with an organisation that matched its domain.
                    # e.g., "Cisco Belgique" starts with "Cisco", which matched "cisco.com", so
                    # should be merged with "Cisco".
                    self._log.debug(f"Organisations match (prefix): \"{name}\" -> \"{org_name}\"")
                    self._org_db.organisations_match(org_name, name)

        print("Consolidating organisations (pass 3)")
        for domain in orgs_for_domain:
            # If the domain is only used by a single organisation and that
            # organisation has not already been assigned a domain, assign
            # to that organisation.
            if len(orgs_for_domain[domain]) == 1:
                name = orgs_for_domain[domain][0]
                if not self._org_db.organisation_has_domain(name):
                    self._org_db.add_domain_for_organisation(name, domain)


    def dump(self, path:Path):
        self._org_db.dump(path)


# =============================================================================
# Code to extract organisations from the datatracker:

if __name__ == "__main__":
    print(f"*** ietfdata.tools.organisations")

    if len(sys.argv) == 3:
        output_path = Path(sys.argv[2])
    else:
        print('')
        print('Usage: python3 -m ietfdata.tools.organisations <ietfdata-dt.sqlite> <organisations.json>')
        print('')
        print('This tools find canonical names for the organisations with')
        print('which IETF participants are affiliated and identifies when')
        print('multiple names refer to the same organisation. Output is a')
        print('JSON file mapping a unique identifier to each organisation')
        print('with its names, domains, and preferred name. An example of')
        print('an entry in the JSON output file might be:')
        print('')
        print('   "ORG:000007": {')
        print('      "preferred_name": "Motorola",')
        print('      "names": [')
        print('         "Motorola, Inc.",')
        print('         "Motorola",')
        print('         "Motorola BCS",')
        print('         "Motorola Codex",')
        print('         "Motorola India Electronics Ltd.",')
        print('         "Motorola India Electronics",')
        print('         "Motorola Laboratories",')
        print('         "Motorola Labs",')
        print('         "Motorola Mobility",')
        print('         "Motorola Solutions"')
        print('      ],')
        print('      "domain": "motorola.com"')
        print('   },')
        print('')
        sys.exit(1)

    om = OrganisationMatcher()
    om.find_organisations_ietf(sys.argv[1])
    om.consolidate_organisations()
    om.dump(output_path)

