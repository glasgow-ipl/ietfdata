import os
import sys
import json
import datetime
from pathlib import Path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import ietfdata
from ietfdata.datatracker import *
from ietfdata.rfcindex import *

import ietfdata.tools.affiliations as aff

if __name__ == '__main__':
    dt = DataTracker(cache_dir = "cache",cache_timeout = timedelta(minutes = 15))
    
    affil_map = list()
    uniq_affil_list = list()
    uniq_affil_raw = list()
    
    ident_index_map = dict()
    
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
                uniq_affil_raw.append(affiliation_str)
            aff_entry = aff.AffiliationEntry(affiliation_str,rfc.date(),None)
            if aff_entry.name not in uniq_affil_list :
                uniq_affil_list.append(aff_entry.name)
                
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
            
            #aff_name = ""
            # if affiliation_str in affiliation_norm_map:
            #     aff_name = affiliation_norm_map[affiliation_str]
            # 
            # if aff_name == "":
            #     for key in affiliation_norm_map:
            #         if affiliation_str.lower() in key.lower():
            #             aff_name = affiliation_norm_map[key]
            # 
            # if aff_name == "":
            #     for key in ac ademic_affiliations_map:
            #         if affiliation_str.lower() in key.lower():
            #             aff_name = academic_affiliations_map[key]
            
            # if aff_name == "" :
            #     print(f"Could not normalise affiliation: {affiliation_str}")
            #     aff_name = f"Unknown ({affiliation_str})"
                
    print(affil_map[0])            
    with open("./identifier_affiliation_map_pre_consolidation.json",'w') as f:
        print("[",file=f,end='')
        n = len(affil_map)
        counter = 0
        for map in affil_map:
            counter += 1
            print(f"{str(map)}",file=f,end='')
            if counter < n:
                print(",",file=f)
        print("]",file=f)
                
    with open("./unique_affiliations.json",'w') as f:
        json.dump(uniq_affil_list,f)
    with open("./unique_affiliations_raw.json",'w') as f:
        json.dump(uniq_affil_raw,f)