import os
import sys
import json
import copy
from datetime import timedelta
from typing import Optional
from pathlib import Path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import ietfdata
from ietfdata.datatracker import *
from ietfdata.rfcindex import *

import ietfdata.tools.affiliations as aff

# Function to fetch RFC affiliations 
def rfc_affiliation_mapping(from_year:int, until_year:int, input_mapping:Optional[list[aff.AffiliationMap]]):
    
    if input_mapping is None:
        af_mapping = list()
    else:
        af_mapping = copy.deepcopy(input_mapping)
    ri = ietfdata.rfcindex.RFCIndex()
    ident_index_map = dict()
    uniq_affil_list = dict()
    uniq_affil_raw = dict()
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
            # person_email_obj = dt.email(author.email)
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
           
            if affiliation_str not in uniq_affil_raw:
                uniq_affil_raw[affiliation_str] = 1
            else:
                uniq_affil_raw[affiliation_str] += 1
                
            aff_entry = aff.AffiliationEntry(affiliation_str,rfc.date(),None,None)
            for individual_aff in aff_entry.names:
                if individual_aff not in uniq_affil_list :
                    uniq_affil_list[individual_aff]=1
                else:
                    uniq_affil_list[individual_aff]+=1
                
            af_mapping = None
            print(f"Looking for {person_uri} or {person_email_address}")
            index = None
            if person_uri in ident_index_map:
                index=ident_index_map[person_uri]
            elif person_email_address in ident_index_map:
                index=ident_index_map[person_email_address]
            if index is not None:
                af_mapping = affil_map[index]
            if af_mapping is not None:
                print("found")
                if person_uri not in af_mapping.identifiers:
                    affil_map[index].add_identifier(person_uri)
                    ident_index_map[person_uri]=index
                elif person_email_address not in af_mapping.identifiers and \
                    person_email_address is not None:
                    affil_map[index].add_identifier(person_email_address)
                    ident_index_map[person_email_address] = index
                affil_map[index].add_affiliation(aff_entry)
                break # found the mapping 
            
            if af_mapping is None:
                print(f"New mapping: {person_uri}")
                tmp_ident = [person_uri]
                if person_email_address is not None:
                    tmp_ident.append(person_email_address)
                tmp_afil = [aff_entry]
                tmp_mapping = aff.AffiliationMap(tmp_ident,tmp_afil)
                affil_map.append(tmp_mapping)
                i = len(affil_map)-1
                for ident in tmp_ident:
                    ident_index_map[ident] = i
        with open("./rfc_unique_affiliations.json",'w') as f:
            json.dump(uniq_affil_list,f)
        with open("./rfc_unique_affiliations_raw.json",'w') as f:
            json.dump(uniq_affil_raw,f)
    return affil_map

if __name__ == '__main__':
    if len(sys.argv) == 2:
        input_path = None
        output_path = Path(sys.argv[1])
    elif len(sys.argv) == 3:
        input_path = Path(sys.argv[1])
        output_path = Path(sys.argv[2])
    else:
        print("Needs either: [input path] [output path] ")
        print("          or: [output path]")
        sys.exit(1)
    
    dt = ietfdata.datatracker.DataTracker(cache_dir = "cache",cache_timeout = timedelta(minutes = 15))
    
    affil_map = list()
    affil_map = rfc_affiliation_mapping(2003,2025,affil_map)
    
    print(affil_map[0])            
    with open(output_path,'w') as f:
        print("[",file=f,end='')
        n = len(affil_map)
        counter = 0
        for map in affil_map:
            counter += 1
            print(f"{str(map)}",file=f,end='')
            if counter < n:
                print(",",file=f)
        print("]",file=f)
