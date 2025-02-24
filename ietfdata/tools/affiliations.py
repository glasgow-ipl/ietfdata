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
    end_date    : datetime.date
    affiliation : str
    def __init__(self, affiliation:str, start_date:datetime.date, end_date:Optional[datetime.date]):
        pass
    def set_end_date(self, new_end_date:datetime.date):
        pass
    def set_affiliation(self, affiliation:str):
        pass

class AffiliationMap:
    identifiers : list[str]
    affiliations: list[AffiliationEntry]
    
    def __init__(self,identifiers:list[str],affiliations:list[AffiliationEntry]):
        pass
    def add_identifier(self, identifier:str):
        pass
    def add_affiliation(self, aff_entry:AffiliationEntry):
        pass

    

class Affiliations:
    entries # entries of affiliations
    
    def __init__(self, input_file:Optional[Path]):
        if input_file is None:
            self.entries = dict()
            return
        if Path(os.path.isfile(input_file)):
            with open(input_file):
                self.entries=json.load(file)
    
    def add_affiliation(self, date:date, affiliation_str:str, identifier:str):
        pass
    def save(self, output_path:Path):
        pass

def remove_suffix(input_string, suffix):
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

if __name-_ == "__main__":
    if len(sys.argv) == 2:
        old_path = None
        new_path = Path(sys.argv[1])
    elif len(sys.argv) == 3:
        old_path = Path(sys.argv[1])
        new_path = Path(sys.argv[2])
    else:
        print("Usage: python3 -m ietfdata.tools.affiliations [[new.json]")
        print("   or: python3 -m ietfdata.tools.affiliations [old.json] [new.json]")
        sys.exit(1)

    
    
    # normalisation patterns
    # Load normalisation patterns
        
    # Load Raw affil. -> normalised affil. mapping
    
    
    # Load email_domain -> normalised affil. mapping
    
    # Load public suffix list https://publicsuffix.org/list/ (mozilla)
    
    # Load Participants file
    
    
    #========================================================================#
    # Go through RFC Documents
    
    
    
    #========================================================================#
    # Go through Emails