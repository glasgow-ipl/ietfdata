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

# affiliations.py --- script to generate extract affiliations
# Mappings generated:
# 1. raw affiliation -> normalised affiliation mappings
# 2. email_domain -> normalised affiliations mappings
# 3. identity -> start year-month, end year-month, affiliation mapping

affiliations_norm_mapping_dict = dict()

if os.path.isfile("ietfdata/tools/affiliation_normalisation_mapping.json"):
    with open("ietfdata/tools/affiliation_normalisation_mapping.json") as f:
        affiliations_norm_mapping_dict = json.load(f)
else:
    print(f"file: affiliation_normalisation_mapping.json not found")

# Affiliation Entry Class
class AffiliationEntry:
    start_date  : datetime.date
    end_date    : Optional[datetime.date]
    name : str
    
    def __init__(self, affiliation:str, start_date:datetime.date, end_date:Optional[datetime.date]):
        self.name = cleanup_affiliation(affiliation)
        self.start_date = start_date
        self.end_date = end_date
    
    def set_end_date(self, new_end_date:datetime.date):
        self.end_date = new_end_date
    
    def set_affiliation_name(self, affiliation:str):
        self.name=cleanup_affiliation(affiliation)
    
    def __str__(self):
        return f'{{"name":"{self.name}","start_date":"{self.start_date}","end_date":"{self.end_date}"}}'

# Affiliation mapping class
class AffiliationMap:
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
            if tmp_head_affil.name is not affil.name:
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

def remove_suffix(input_string:str, suffix:str):
    if suffix and input_string.endswith(suffix):
        return input_string[:-len(suffix)]
    return input_string


def cleanup_affiliation(affiliation_str:str):
    affiliation_str = affiliation_str.strip()
    affiliation_str = affiliation_str.replace("\n","")
    affiliation_str = re.sub(' +', ' ', affiliation_str)
    affiliation_suffixes = [", Inc.", "Inc", "LLC", "Ltd", "Limited", "Incorporated", "GmbH", "Inc.", "Systems", "Corporation", "Corp.", "Ltd.", "Technologies", "AG", "B.V."]
    alt_university = ["Univ.","Universtaet","Universteit","Universitaet","Université"]
    for alt in alt_university:
        affiliation_str = affiliation_str.replace(alt, "University")
    affiliation_str = affiliation_str.replace("TU","Technical University of")
    affiliation_str = affiliation_str.replace("U. of", "University of")
    for suffix in affiliation_suffixes:
        affiliation_str = remove_suffix(affiliation_str, suffix)
    affiliation_str = affiliation_str.replace(",","")
    affiliation_str = affiliation_str.strip()
    affiliation_str = re.sub(r"^\.|\.$", "", affiliation_str)
    
    if affiliations_norm_mapping_dict is not None:
        if affiliation_str in affiliations_norm_mapping_dict:
            affiliation_str = affiliations_norm_mapping_dict.get(affiliation_str)
    
    return affiliation_str

def load_mapping(input_dict:dict):
    pass


