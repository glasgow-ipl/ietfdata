# TODO: Add licensing

import sys
import csv
import json 
import copy

import datetime
from datetime import timedelta
from typing import Optional

from ietfdata.datatracker     import *
from ietfdata.datatracker_ext import *
from ietfdata.mailarchive2    import *

# load affiliation_mappings
# import affiliations_map #hugo
import ietfdata.tools.affiliation_mapping_dictionary as afmap #yangjun
# affiliations.py --- script to generate extract affiliations
# Mappings generated:
# 1. raw affiliation -> normalised affiliation mappings
# 2. email_domain -> normalised affiliations mappings
# 3. identity -> start year-month, end year-month, affiliation mapping

# Affiliation class
class Affiliation:
    
    _preferred_name: Optional[str]
    _names : list[str]
    _domain : Optional[str]
    
    def __init__(self,name:str) -> None:
        self._preferred_name = name
        self._names = [name]
        self._domain = None
    
    def preferred_name(self) -> Optional[str]:
        return self._preferred_name
    
    def names(self) -> list[str]:
        return self._names
    
    def domain(self) -> Optional[str]:
        return self._domain
    
    def set_preferred_name(self,name: str) -> None:
        if name in self._names:
            if self._preferred_name is not None:
                print(f"Preferred name already set to: {self._preferred_name}, overriding to {name}")
            self._preferred_name = name
        else:
            raise RuntimeError(f"{name} not in the Names.")
    
    def add_name(self,name:str)->None:
        if (name is None) | (name == ""):
            raise RuntimeError("Name is None or empty.")
        elif name not in self._names:
            self._names.append(name) 
        else:
            print(f"{name} already present for {self._preferred_name}.")
    
    def add_domain(self, domain:str)->None:
        if (domain is None) | (domain ==""):
            raise RuntimeError("Domain is None or empty.")
        if self._domain is None:
            self._domain = domain
        else:
            print(f"DEBUG: Domain already set to {self._domain}, but add_domain({domain}) was called.", file=sys.stderr)
            # raise RuntimeError(f"Domain already set to {self._domain}, but add_domain({domain}) was called.")
   
    def __repr__(self):
        return f"names:[{",".join(self._names)}],preferred_name:{self._preferred_name}, domain: {getattr(self,"_domain","")}"
    
    
# Class to hold a set of known affiliations
class Affiliations:
    _affiliations : dict[str,Affiliation]
    _affiliations_by_name : dict[str,Affiliation]
    
    def __init__(self) -> None:
        self._affiliations = dict()
        self._affiliations_by_name = dict()
    
    def affiliation_by_name(self, name: str) -> Affiliation:
        if name not in self._affiliations:
            raise KeyError(f"{name} is not a known preferred name.")
        return self._affiliations[name]
    
    def affiliation_exists(self, name: str) -> None:
        if name not in self._affiliations:
            self._affiliations[name] = Affiliation(name)
            self._affiliations[name].set_preferred_name(name)
        else:
            print(f"Affiliation \"{name}\" already exists with matching preferred name.")
        if name not in self._affiliations_by_name:
            self._affiliations_by_name[name] = self._affiliations[name]
            
    def merge(self, name_1: str, name_2: str) -> None:
        # merge name_2 to name_1
        if name_1 not in self._affiliations:
            raise KeyError(f"{name_1} is not a known preferred name.")
        if name_2 not in self._affiliations:
            raise KeyError(f"{name_2} is not a known preferred name.")
        
        for name in self._affiliations[name_2].names():
            if name not in self._affiliations[name_1]:
                self._affiliations[name_1].add_name(name)
            if name_2 not in self._affiliations[name_1]:
                self._affiliations[name_1].add_name(name_2)
        
        name_2_domain = self._affiliations[name_2].domain()
        if name_2_domain is not None:
            if self._affiliations[name_1].domain() is None:
                self._affiliations[name_1].add_domain(name_2_domain)
            elif self._affiliations[name_1].domain() == name_2_domain:
                pass
            else:
                raise RuntimeError(f"Mismatching domains for {name_1} ({self._affiliations[name_1].domain()}) and {name_2}({name_2_domain})")
        
        self._affiliations_by_name[name_2] = self.affiliations[name_1]
        for name in self._affiliations[name_2].names():
            self._affiliations_by_name[name] = self._affiliations[name_1]
            
        del self._affiliations[name_2]
    
    def affiliation_domain(self, name:str, domain:str) -> None:
        # Indicates that `domain` is known to be used solely by the 
        # `affiliation`
        domain = domain.lower()
        if name not in self._affiliations:
            raise KeyError(f"Unknown affiliation: {name}")
        if self._affiliations[name].domain() is None:
            self._affiliations[name].add_domain(domain)
        elif self._affiliations[name].domain() == domain:
            print(f"Provided domain matches the existing domain:{domain}")
        else:
            print(f"DEBUG: Multiple domains for affiliation: {name}, {self._affiliations[name].domain()} exists while {domain} was supplied.")
            self._affiliations[name].add_domain(domain)
            # raise RuntimeError(f"Multiple domains for affiliation: {name}, {self._affiliations[name].domain()} exists while {domain} was supplied.")

        
    def affiliation_update_preferred_name(self, name: str, new_name: str) -> None:
        # Indicates the preferred name for an affiliation
        if name not in self._affiliations:
            raise KeyError(f"Unknown affiliation: {name}")
        self._affiliations[new_name]=self._affiliations.pop(name)        
        self._affiliations[new_name].set_preferred_name(new_name)
        if name not in self._affiliations[new_name].names():
            self._affiliations[new_name].add_name(name)
        if name not in self._affiliations_by_name:
            self._affiliations_by_name[name] = self._affiliations[new_name]
    
    def normalise_affiliation(self, name:str) -> str:
        # normalise the given name
        tmp_name = name
        if tmp_name in self._affiliations: #this **is** the preferred name
            return tmp_name
        if tmp_name in self._affiliations_by_name:
            return self._affiliations_by_name[tmp_name].preferred_name()
        return None
    
    def __repr__(self) -> str:
        repr_str = "{"
        affil_keys = list(self._affiliations.keys()).sort()
        for affil in affil_keys:
            repr_str+=f"{affil}:{repr(self._affiliations[affil])},"
        repr_str+=repr_str.rstrip(',')
        repr_str = "}"

# Todo: Class to go through datatracker to extract the information, clean up names, match two orgs etc.
# Affiliation Entry Class 
class AffiliationEntry:
    start_date  : datetime.date
    end_date    : Optional[datetime.date]
    names : list[str]
    def __init__(self, start_date:datetime.date, end_date:Optional[datetime.date],names:list[str]):
        self.names=names
        self.start_date = start_date
        self.end_date = end_date
    
    def set_end_date(self, new_end_date:datetime.date):
        self.end_date = new_end_date
    
    def set_affiliation_names(self, names:list[str]):
        self.names=names
    
    def match_names(self, names:list[str]):
        for name in names:
            if name not in self.names:
                return False
        return True
    
    def __str__(self):
        return_str = '{"names":['
        return_str += ",".join(self.names)
        return_str =  return_str.rstrip(',')
        return_str += "],"
        return_str += f'"start_date":"{self.start_date}","end_date":"{self.end_date}"}}'
        return return_str


# Sets of Affiliation for Person class
class AffiliationsForPerson:
    identifiers : list[str]
    affiliations: list[AffiliationEntry]
    
    def __init__(self,identifiers:list[str],affiliations:list[AffiliationEntry]):
        self.identifiers = copy.deepcopy(identifiers)
        self.affiliations = copy.deepcopy(affiliations)
    
    def add_identifier(self, identifier:str):
        self.identifiers.append(identifier)
    
    def add_affiliation(self, aff_entry:AffiliationEntry):
        # TODO: Go through the timeline, insert the entry 
        new_date = aff_entry.start_date
        for affil in self.affiliations:
            i = self.affiliations.index(affil)
            if new_date <= affil.start_date:
                self.affiliations.insert(i,aff_entry)
                return #inserted entry
        self.affiliations.append(aff_entry)
        return
            
    def consolidate(self):
        # TODO: Go through the timeline, consolidate the history
        # This should only be run if and only if everything has been scraped
        tmp_head_affil = None # temporary first affil in the batch
        consolidated_affil = list()
        for affil in self.affiliations:
            if tmp_head_affil is None:
                tmp_head_affil = copy.deepcopy(affil)
                continue
            # set_head_affil_names = set(tmp_head_affil.names)
            # diff_list = [item for item in affil.names not in set_head_affil_names]
            if not tmp_head_affil.match_names(affil.names):
                    tmp_head_affil.end_date = (datetime.strptime(affil.start_date,'%Y-%m-%d').date() - timedelta(days=1))
                    consolidated_affil.append(tmp_head_affil)
                    tmp_head_affil = copy.deepcopy(affil)
            if(tmp_head_affil not in consolidated_affil):
                consolidated_affil.append(tmp_head_affil)
        self.affiliations = copy.deepcopy(consolidated_affil)
    
    def __str__(self):
        returnstr = '{"identifiers":['
        for ident in self.identifiers:
            returnstr += f'"{ident}",'
        returnstr = returnstr[:-1] # strip last comma
        returnstr += "],"
        returnstr += '"affiliations":['
        for affil in self.affiliations:
            returnstr+=str(affil)
            returnstr+=","
        returnstr = returnstr[:-1] # strip last comma
        returnstr += "]}"
        return returnstr

# Auxiliary functions
    
def _remove_suffix(input_string:str, suffix:str) -> str:
            if suffix and input_string.lower().endswith(suffix.lower()):
                return input_string[:-len(suffix)]
            return input_string
        
def _cleanup_affiliation_strip_chars(affiliation:str) -> str:
    affiliation = affiliation.replace("\n","")
    affiliation = " ".join(affiliation.split()) # clean up all white spaces and re-join
    affiliation = affiliation.replace(",","")
    affiliation = re.sub(r"^\.|\.$", "", affiliation)
    affiliation = re.sub(' /', '/', affiliation)
    affiliation = re.sub('/ ', '/', affiliation)
    return affiliation

def _cleanup_affiliation_suffix(affiliation:str) -> str:
    affiliation_suffixes = [", Inc.", "Inc", "LLC", "Ltd", "Limited", "Incorporated", "GmbH", "Inc.", "Systems", "Corporation", "Co", "Co.","Corp", "Corp.", "Ltd.", "Technologies", "AG", "B.V.","s.r.o.","s.r.o","a.s"]
    for suffix in affiliation_suffixes:
        affiliation = _remove_suffix(affiliation,suffix).strip()
    return affiliation

def _cleanup_affiliation_academic(affiliation:str) ->str:
    alt_university = ["Univ.","Universtaet","Universteit","Universitaet","Université"]
    for alt in alt_university:
        affiliation = affiliation.replace(alt, "University")
    affiliation = affiliation.replace("TU","Technical University of")
    affiliation = affiliation.replace("U. of", "University of")
    return affiliation

# def normalise(affiliation:str):
#     # do the look_up and return list item
#     for key in afmap:
#         if affiliation.lower() is key.lower():
#             return afmap.get(key)


def cleanup_affiliation_str(affiliation:str)->str:
    affiliation = _cleanup_affiliation_academic(affiliation)
    affiliation = _cleanup_affiliation_strip_chars(affiliation)
    affiliation = _cleanup_affiliation_suffix(affiliation)
    return affiliation
    # affiliation_list = None
    # affiliation_list = normalise(affiliation)
    # if affiliation_list is None: # attempt 2 — unknown multi-affiliation case
    #     tmp_split = affiliation.split("/")
    #     for part in tmp_split:
    #         tmp_part = part
    #         tmp_part = _cleanup_affiliation_academic(tmp_part)
    #         tmp_part = _cleanup_affiliation_strip_chars(tmp_part)
    #         tmp_part = _cleanup_affiliation_suffix(tmp_part)
    #         tmp_list = normalise(tmp_part)
    #         if tmp_list is not None:
    #             affiliation_list.append(tmp_list)
    # if affiliation_list is None: # if all else fails, leave after cleanse
    #     affiliation_list = [affiliation]
    # return affiliation_list
def cleanup_affiliation(affiliation:str)->list[str]:
    affiliation = cleanup_affiliation_str(affiliation)
    affiliation_list = None
    # affiliation_list = normalise(affiliation)
    if affiliation_list is None: # attempt 2 — unknown multi-affiliation case
        tmp_split = affiliation.split("/")
        for part in tmp_split:
            tmp_part = part
            tmp_part = cleanup_affiliation_str(tmp_part) 
            # tmp_list = normalise(tmp_part)
            # if tmp_list is not None:
            #     affiliation_list.append(tmp_list)
    if affiliation_list is None: # if all else fails, leave after cleanse
        affiliation_list = [affiliation]
    return affiliation_list

## affiliation collection
if __name__ == "__main__":
    if len(sys.argv) == 2:
        old_path = None
        new_path = Path(sys.argv[1])
    else:
        print("Usage: python3 -m ietfdata.tools.affiliations [new.json]")
        # print("   or: python3 -m ietfdata.tools.participants [old.json] [new.json]")
        sys.exit(1)
    
    affil_collection = Affiliations()
    
    print(f"*** ietfdata.tools.affiliations")
    print("*** Collecting affiliations from the datatracker")
    dt  = DataTracker(cache_dir = "cache",cache_timeout = timedelta(hours=12))
    
    print("*** Published RFC")
    ri = RFCIndex()
    seen_addr_ietf = list()
    for rfc in ri.rfcs():
        year = rfc.date().year
        if year < 2003:
            print('pre 2003, skip')
            continue
        if year > 2024:
            print('post 2024, skip')
            continue
        # setup additional attributes
        stream = "stream_"
        try:
            stream += rfc.stream
        except TypeError:
            stream += "N/A"
        if stream is None:
            stream += "N/A"
        if (stream != "stream_IETF" and stream != "stream_Legacy"): # only look at IETF and Legacy stream
            continue
        
        status = "status_"  
        try:
            status += rfc.publ_status
        except TypeError:
            status += "N/A"
        if status is None:
            status += "N/A"
        # end setup additional attributes
        print(rfc.doc_id)
        # fetch values for additional attributes
        # Authors handling:  
        document = dt.document_from_rfc(rfc.doc_id)
        if document is None:
            print(f"No document in data tracker from {rfc.doc_id}")
            continue
        authors = dt.document_authors(document)
        if authors is None:
            print(f"No authors in data tracker from {rfc.doc_id}")
            continue
        for author in authors:
            person_uri = str(author.person)
            if author.email is not None:
                person_email_address = str(dt.email(author.email).address)
            else:
                person_email_address = None
            tmp_ident_list = [person_uri,person_email_address]
            
            affiliation_str = None
            if author.affiliation is None:
                affiliation_str = "Unknown"
            else:
                affiliation_str = author.affiliation
            if author.affiliation == "":
                affiliation_str = "Unknown"
            if affiliation_str == "Unknown":
                print("Affiliation either None, empty, or unknown")
                continue
            if person_email_address == "":
                print("missing email addr.")
                continue
            if person_email_address.find("@") == -1:
                print("Not an email addr.")
                continue
            tmp_domain = person_email_address.split('@')[-1]
            affil_collection.affiliation_exists(affiliation_str)
            if tmp_domain != "":
                affil_collection.affiliation_domain(affiliation_str,tmp_domain)
            
    with open(new_path,'w') as f:
        print(repr(affil_collection),FILE=f)