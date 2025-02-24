# TODO: Add licensing

import sys
import csv
import json 

import datetime

from typing import Optional

from ietfdata.datatracker     import *
from ietfdata.datatracker_ext import *
from ietfdata.mailarchive2    import *
import mailarchive_mbox 

# affiliations.py --- script to generate extract affiliations
# Mappings generated:
# 1. raw affiliation -> normalised affiliation mappings
# 2. email_domain -> normalised affiliations mappings
# 3. identity -> start year-month, end year-month, affiliation mapping

# Affiliation Class
class AffiliationEntry:
    start_date  : datetime.date
    end_date    : Optional[datetime.date]
    affiliation_name : str
    def __init__(self, affiliation:str, start_date:datetime.date, end_date:Optional[datetime.date]):
        self.affiliation_name = affiliation
        self.start_date = start_date
        self.end_date = end_date
    def set_end_date(self, new_end_date:datetime.date):
        self.end_date = new_end_date
    def set_affiliation_name(self, affiliation:str):
        self.affiliation_name=affiliation

class AffiliationMap:
    identifiers : list[str]
    affiliations: list[AffiliationEntry]
    
    def __init__(self,identifiers:list[str],affiliations:list[AffiliationEntry]):
        self.identifiers = identifiers
        self.affiliations = affiliations
    def add_identifier(self, identifier:str):
        self.identifiers.append(identifier)
    def add_affiliation(self, aff_entry:AffiliationEntry):
        # TODO: deal with affiliation entry, adjusting 'end' and start
        pass

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
    return affiliation_str



