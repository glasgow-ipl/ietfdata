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

def cleanup_affiliation_strip_chars(affiliation:str):
    affiliation = affiliation.strip()
    affiliation = affiliation.replace("\n","")
    affiliation = re.sub(' +', ' ', affiliation)
    affiliation = affiliation.replace(",","")
    affiliation = affiliation.strip()
    affiliation = re.sub(r"^\.|\.$", "", affiliation)
    return affiliation

def cleanup_affiliation_suffix(affiliation:str):
    affiliation_suffixes = [", Inc.", "Inc", "LLC", "Ltd", "Limited", "Incorporated", "GmbH", "Inc.", "Systems", "Corporation", "Corp.", "Ltd.", "Technologies", "AG", "B.V.","s.r.o."]
    for suffix in affiliation_suffixes:
        affiliation = remove_suffix(affiliation, suffix)
    return affiliation

def cleanup_affiliation_academic(affiliation:str):
    alt_university = ["Univ.","Universtaet","Universteit","Universitaet","Université"]
    for alt in alt_university:
        affiliation = affiliation.replace(alt, "University")
    affiliation = affiliation.replace("TU","Technical University of")
    affiliation = affiliation.replace("U. of", "University of")
    return affiliation

def normalise_affiliation(affiliation:str):
    # do the look_up and return list item
    for key in afmap.affiliation_list_map:
        if affiliation.lower() is key.lower():
            return afmap.affiliation_list_map.get(key)
    return None

def cleanup_affiliation(affiliation:str):
    affiliation = cleanup_affiliation_academic(affiliation)
    affiliation = cleanup_affiliation_strip_chars(affiliation)
    affiliation = cleanup_affiliation_suffix(affiliation)
    affiliation_list = None
    affiliation_list = normalise_affiliation(affiliation)
    if affiliation_list is None: # attempt 2 — unknown multi-affiliation case
        tmp_split = affiliation.split("/")
        for part in tmp_split:
            tmp_part = part
            tmp_part = cleanup_affiliation_academic(tmp_part)
            tmp_part = cleanup_affiliation_strip_chars(tmp_part)
            tmp_part = cleanup_affiliation_suffix(tmp_part)
            tmp_list = normalise_affiliation(tmp_part)
            if tmp_list is not None:
                affiliation_list.append(tmp_list)
    if affiliation_list is None: # if all else fails, leave after clense
        affiliation_list = [affiliation]
    return affiliation_list



