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
    _names          : List[str]
    _domains        : List[str]

    def __init__(self, name:str) -> None:
        self._names          = [name]
        self._domains        = []


    def names(self) -> List[str]:
        return self._names


    def domains(self) -> List[str]:
        return self._domains


    def add_name(self, name:str) -> None:
        if name not in self._names:
            self._names.append(name)


    def add_domain(self, domain: str) -> None:
        if domain not in self._domains:
            self._domains.append(domain)



class OrganisationDB:
    _log           : logging.Logger
    _organisations : Dict[str,Organisation]   # Map from name to Organisation
    _domains       : Dict[str,Organisation]   # Map from domain to Organisation

    def __init__(self) -> None:
        logging.basicConfig(level=os.environ.get("IETFDATA_LOGLEVEL", "INFO"))
        self._log           = logging.getLogger("ietfdata")
        self._organisations = {}
        self._domains       = {}


    def get_all_organisations(self) -> List[str]:
        return sorted(list(self._organisations.keys()))


    def get_all_domains(self) -> List[str]:
        return sorted(list(self._domains.keys()))


    def get_organisation(self, org_name: str) -> Organisation:
        return self._organisations[org_name]


    def get_domains_for_organisation(self, org_name: str) -> List[str]:
        return self._organisations[org_name].domains()


    def add_organisation(self, org_name: str) -> None:
        """
        Indicate that an organisation with the specified `org_name` exists
        """
        if org_name not in self._organisations:
            self._log.debug(f"Add organisation: \"{org_name}\"")
            self._organisations[org_name] = Organisation(org_name)


    def add_domain_for_organisation(self, org_name:str, domain:str) -> None:
        """
        Indicate that an organisation with the specified `org_name` has sole
        use of the `domain`.
        """
        self.add_organisation(org_name)
        if domain not in self._domains:
            self._log.debug(f"Add domain for organisation: \"{org_name}\" -> \"{domain}\"")
            self._organisations[org_name].add_domain(domain)
            self._domains[domain] = self._organisations[org_name]
        else:
            if self._domains[domain] == self._organisations[org_name]:
                # The domain has already been recorded as belonging to this organisation
                pass
            else:
                # There is another organisation with this domain. Merge the two, since
                # domains are supposed to uniquely idenitify organisations.
                self._merge(self._organisations[org_name], self._domains[domain])


    def organisation_has_domains(self, org_name:str) -> bool:
        if org_name not in self._organisations:
            return False
        return self._organisations[org_name].domains() != []


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
        for domain in org1.domains():
            org2.add_domain(domain)
        # Change all references to org1 by name to refer to org2:
        for name, org in self._organisations.items():
            if name in org1.names():
                self._organisations[name] = org2
        # Change all references to org1 by dmomain to refer to org2:
        for domain, org in self._domains.items():
            if domain in org1.domains():
                self._domains[domain] = org2


    def dump(self, json_path: Path) -> None:
        found = []
        items = {}
        orgid = 0
        for name, org in self._organisations.items():
            if org not in found:
                orgid += 1
                item  = {"names": org.names(), "domains": org.domains()}
                items[f"ORG:{orgid:06}"] = item
                found.append(org)
        with open(json_path, "w") as outf:
            json.dump(items, outf, indent=3)


    def debug_dump(self) -> None:
        print("{")
        for name, org in self._organisations.items():
            print(f'  name {name} -> ("names": {org.names()}, "domains": {org.domains()})')
        for domain, org in self._domains.items():
            print(f'  domain {domain} -> ("names": {org.names()}, "domains": {org.domains()})')
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

def variant_names(name:str) -> List[str]:
    variants = []

    # Generate variants based on known suffixes
    for suffix in ["Ltd", "LLC", "Inc", "Pty", "GmbH", "Company", "Co.,Ltd", "z.s.p.o", "TZI"]:
        for variant in [f", {suffix}.", f", {suffix}", f" {suffix}.", f" {suffix}"]:
            if name.endswith(variant):
                bare_name = name[:-len(variant)]
                variants.append(bare_name)

    # Generate variants ending with known abbreviations
    for abbr, full in [("Corp", "Corporation"),
                       ("Univ", "University")]:
        for variant in [f", {abbr}.", f", {abbr}", f" {abbr}.", f" {abbr}"]:
            if name.endswith(variant):
                full_name = f"{name[:-len(variant)]} {full}"
                variants.append(full_name)

    # Generate variants based on known prefixes
    for prefix in ["The", "TZI", "TZI/", "TZI,"]:
        for variant in [f"{prefix} "]:
            if name.startswith(variant):
                bare_name = name[len(variant):]
                variants.append(bare_name)

    # Generate variants starting with known abbreviations
    for abbr, full in [("Univ",       "University"),
                       ("Univ",       "Université"),
                       ("Univ",       "Universität"),
                       ("Univ",       "Universitaet"),
                       ("Univ",       "University of"),
                       ("Uni",        "University"),
                       ("Uni",        "Université"),
                       ("Uni",        "Universität"),
                       ("Uni",        "Universitaet"),
                       ("Uni",        "University of"),
                       ("U",          "University"),
                       ("U",          "Université"),
                       ("U",          "Universität"),
                       ("U",          "Universitaet"),
                       ("U",          "University of"),
                       ("U. of",      "University of"),
                       ("TZI/Uni",    "University of"),
                       ("TU",         "Technische Universität"),
                       ("FU",         "Freie Universität")]:
        for variant in [f"{abbr}. ", f"{abbr} "]:
            if name.startswith(variant):
                full_name = f"{full} {name[len(variant):]}"
                variants.append(full_name)

    # Generate variants based on alternate spellings
    mod_name = name
    for orig, repl in [("Universitaet",                "Universität"),
                       ("Universitaet",                "University of"),
                       ("Universität",                 "Universitaet"),
                       ("Universit\u00c3\u00a4t",      "Universität"),
                       ("TZI, Universit\u00c3\u00a4t", "Universität"),
                       ("Universität",                 "University of"),
                       ("University",                  "University of"), 
                       ("Universite",                  "University"),
                       ("Université",                  "University"),
                       ("Université de",               "University of"),
                       ("Universit\u00e9",             "Universite"),
                       ("Universit\u00c3\u00a9",       "Universite"),
                       ("Univ. of",                    "University of"),
                       ("Technische Universitaet",     "Technical University of"),
                       ("Technische Universität",      "Technical University of"),
                       ("Liège",                       "Liege"),
                       ("Muenchen",                    "München"),
                       ("Munich",                      "München"),
                       ("Muenster",                    "Münster"),
                       ("Deuetsche",                   "Deutsche"),
                       ("Technology",                  "Technologies"),
                       ("NC State",                    "North Carolina State"),
                       ("USC/ISI",                     "USC/Information Sciences Institute"),
                       ("uc3m",                        "Universidad Carlos III de Madrid"),
                       ("CDT",                         "Center for Democracy and Technology"),
                       ("HKUST",                       "Hong Kong University of Science and Techology"),
                       ("APNIC",                       "Asia Pacific Network Information Centre"),
                       ("UCLouvain",                   "Universite Catholique de Louvain"),
                       ("Appl. Sciences",              "Applied Sciences"),
                       ("App. Sciences",               "Applied Sciences"),
                       (" & ",                         " and "),
                       (" / ",                         "/")]:
        if orig in name:
            new_name = name.replace(orig, repl)
            variants.append(new_name)
        if orig in mod_name:
            mod_name = mod_name.replace(orig, repl)
            variants.append(new_name)

    #if variants != []:
    #    print(f"Variants for {name}:")
    #    for variant in variants:
    #        print(f"    {variant}")

    return variants


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

        print("Finding organisations in internet-drafts")
        for submission in dt.submissions():
            self._log.info(f"{submission.name}-{submission.rev}")
            if submission.state != "/api/v1/name/draftsubmissionstatename/posted/":
                # Skip submissions that are not posted to the archive
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


    def print_stats(self) -> None:
        names = self._org_db.get_all_organisations()
        orgs = []
        for org_name in names:
            org = self._org_db.get_organisation(org_name)
            if org not in orgs:
                orgs.append(org)
        print(f"  {len(names):5} names for {len(orgs):5} organisations")


    def consolidate_organisations(self):
        assert self._org_db.get_all_domains() == []
        assert self._org_db.get_all_organisations() == []

        # Record original names:
        print("Consolidating organisations: pass 1a (organisation names)")
        for name, email in self._orgs:
            self._org_db.add_organisation(name)
        self.print_stats()

        # =========================================================================================
        # Name matching consolidation

        # Record names with stray whitespace removed and match to original names:
        print("Consolidating organisations: pass 2a (fixup whitespace)")
        for name, email in self._orgs:
            new_name = name.replace("\n", " ")
            new_name = new_name.replace("\t", " ")
            while "  " in new_name:
                new_name = new_name.replace("  ", " ")
            if new_name != name:
                self._org_db.organisations_match(new_name, name)
        self.print_stats()

        # Generate other variants and record matches:
        print("Consolidating organisations: pass 2b (variant names)")
        for name, email in self._orgs:
            for variant in variant_names(name):
                for other_name, other_email in self._orgs:
                    if variant == other_name:
                        self._log.debug(f"Organisation matches variant: {name} -> {variant}")
                        self._org_db.organisations_match(variant, name)
                        continue
        self.print_stats()

        # for name, email in self._orgs:
        #     # If the organisation name contains a "/", add variants with or without
        #     # surrounding spaces and match as matching.
        #     if " / " in name:
        #         no_slash = name.replace(" / ", "/")
        #         self._org_db.add_organisation(no_slash)
        #         self._org_db.organisations_match(name, no_slash)
        #     elif "/ " in name:
        #         no_slash = name.replace("/ ", "/")
        #         self._org_db.add_organisation(no_slash)
        #         self._org_db.organisations_match(name, no_slash)
        #     elif " /" in name:
        #         no_slash = name.replace(" /", "/")
        #         self._org_db.add_organisation(no_slash)
        #         self._org_db.organisations_match(name, no_slash)

        # Merge organisations that differ only in case
        print("Consolidating organisations: pass 2c (case folding)")
        for name, email in self._orgs:
            lname = name.lower()
            for other_name, other_email in self._orgs:
                if name == other_name:
                    continue
                if lname == other_name.lower():
                    self._org_db.organisations_match(other_name, name)
        self.print_stats()

        # =========================================================================================
        # Domain matching consolidation

        # If the organisation name matches the domain, record the domain as
        # belonging to this organisation (e.g., "cisco.com" -> "Cisco")
        print("Consolidating organisations: pass 3a (organisation matches domain)")
        orgs_matching_domain : Dict[str,str] = {}
        for name, email in self._orgs:
            org_domain = None
            if email is not None and "@" in email:
                parts  = email.split("@")[1].split(".")
                for tld in ["com", "org", "edu"]:
                    if len(parts) >= 2 and parts[-1] == tld:
                        domain = f"{parts[-2]}.{parts[-1]}".lower()
                        if name.lower() == parts[-2].lower():
                            # Organisation name directly matches domain
                            self._log.debug(f"Organisation matches domain (1): {domain} -> {name}")
                            self._org_db.add_domain_for_organisation(name, domain)
                            orgs_matching_domain[name] = domain
                        elif name.replace(" ", "").lower() == parts[-2].lower():
                            # Organisation name with spaces removes matches domain
                            self._log.debug(f"Organisation matches domain (2): {domain} -> {name}")
                            self._org_db.add_domain_for_organisation(name, domain)
                            orgs_matching_domain[name] = domain
        self.print_stats()

        # If the organisation name starts with the name of an organisation that matched its
        # domain, merge those organisations (e.g., "Cisco Belgique" starts with "Cisco",
        # which matched "cisco.com", so should be merged with "Cisco")
        print("Consolidating organisations: pass 3b (organisation prefix matches domain)")
        for name, email in self._orgs:
            for org_name, domain in orgs_matching_domain.items():
                if name.lower().startswith(f"{org_name} ".lower()):
                    self._log.debug(f"Organisation prefix matches domain: {name} -> {domain}")
                    self._org_db.organisations_match(org_name, name)
        self.print_stats()

        # If the domain is used by multiple email addresses with a single organisation
        # name, then assign the domain to that organisation.
        print("Consolidating organisations: pass 3c (single organisation domains)")
        orgs_for_domain  : Dict[str, List[str]] = {}
        email_for_domain : Dict[str, List[str]] = {}
        for name, email in self._orgs:
            if email is not None and "@" in email:
                domain = email.split("@")[1].lower()
                if domain in orgs_for_domain:
                    if name not in orgs_for_domain[domain]:
                        orgs_for_domain[domain].append(name)
                else:
                    orgs_for_domain[domain] = [name]
                if domain in email_for_domain:
                    if email not in email_for_domain[domain]:
                        email_for_domain[domain].append(email)
                else:
                    email_for_domain[domain] = [email]
        for domain, orgs in orgs_for_domain.items():
            emails = email_for_domain[domain]
            if len(orgs) == 1 and len(emails) > 1 and orgs[0] not in orgs_matching_domain:
                self._log.debug(f"Found single organisation domain: {orgs[0]} -> {domain}")
                self._org_db.add_domain_for_organisation(orgs[0], domain)
        self.print_stats()

        # FIXME: not clear this gives useful mappings
        #   print("Consolidating organisations (pass 4)")
        #   # Map names to acronyms. This merges, e.g., "ISC" and "Internet Systems Consortium".
        #   expansions = {}
        #   for name, domain in self._orgs:
        #       if name.isalpha() and name.isascii() and name.isupper():
        #           # `name` is all upper case ASCII with no spaces, potentially an acronym
        #           for org_name in self._org_db.get_all_organisations():
        #               new_name = org_name.strip().replace("\n", " ")
        #               while "\t" in new_name:
        #                   new_name = new_name.replace("\t", " ")
        #               while "  " in new_name:
        #                   new_name = new_name.replace("  ", " ")
        #   
        #               acronym = "".join(map(lambda x : x[0].upper(), new_name.split(" ")))
        #               if name == acronym:
        #                   if acronym in expansions:
        #                       expansions[acronym].append(org_name)
        #                   else:
        #                       expansions[acronym] = [org_name]
        #   for acronym, names in expansions.items():
        #       if len(names) == 1:
        #           # Only consider cases where there is a unique expansion for the acronym
        #           org = self._org_db.get_organisation(names[0])
        #           print(f"*********** {acronym} -> {names[0]} -> {org.names()}")


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
        print('with its names and domains. An example of an entry in the')
        print('JSON output file might be:')
        print('')
        print('   "ORG:000007": {')
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

