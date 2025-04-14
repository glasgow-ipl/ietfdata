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

# Affiliation Entry Class
class AffiliationEntry:
    start_date  : datetime.date
    end_date    : Optional[datetime.date]
    names : list[str]
    
    def __init__(self, affiliation_str:str, start_date:datetime.date, end_date:Optional[datetime.date],names_list:Optional[list[str]]):
        if names_list is not None:
            self.names=copy.deepcopy(names_list)
        else:
            self.names = cleanup_affiliation(affiliation_str)
        self.start_date = start_date
        self.end_date = end_date
    
    def set_end_date(self, new_end_date:datetime.date):
        self.end_date = new_end_date
    
    def set_affiliation_names(self, affiliation:str):
        self.namse=cleanup_affiliation(affiliation)
    
    def match_names(self, names:list[str]):
        for name in names:
            if name not in self.names:
                return False
        return True
    
    def __str__(self):
        return_str = '{"names":['
        for name in self.names:
            return_str+=f'"{name}",'
        return_str =  return_str.rstrip(',')
        return_str += "],"
        return_str += f'"start_date":"{self.start_date}","end_date":"{self.end_date}"}}'
        return return_str

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

def remove_suffix(input_string:str, suffix:str):
    if suffix and input_string.endswith(suffix):
        return input_string[:-len(suffix)]
    return input_string


def cleanup_affiliation(affiliation_str:str):
    affiliation_str = affiliation_str.strip()
    affiliation_str = affiliation_str.replace("\n","")
    affiliation_str = re.sub(' +', ' ', affiliation_str)
    affiliation_suffixes = [", Inc.", "Inc", "LLC", "Ltd", "Limited", "Incorporated", "GmbH", "Inc.", "Systems", "Corporation", "Corp.", "Ltd.", "Technologies", "AG", "B.V.","s.r.o."]
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
    affiliation_list = None
    if afmap.affiliation_raw_list_map is not None:
        if affiliation_str in afmap.affiliation_raw_list_map:
            affiliation_list = copy.deepcopy(afmap.affiliation_raw_list_map.get(affiliation_str))
        if affiliation_list is None:
            for aff_key in afmap.affiliation_raw_list_map:
                if affiliation_str.lower() is aff_key.lower():
                    affiliation_list = copy.deepcopy((afmap.affiliation_raw_list_map.get(aff_key)))
    if affiliation_list is None:
        affiliation_list = [affiliation_str]
    return affiliation_list

def load_mapping(input_dict:dict):
    pass


