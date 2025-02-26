import os
import sys
import datetime
from pathlib import Path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import ietfdata
from ietfdata.datatracker import *
import ietfdata.rfcindex import *

import ietfdata.tools.affiliations as aff

if __name__ == '__main__':
    dt = DataTracker(cache_dir = "cache",cache_timeout = timedelta(minutes = 15))
    
    
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
            person_email_address = str(author.email)
            tmp_ident_list = [person_uri,person_email_address]
            
            affiliation_str = None
            if author.affiliation is None:
                affiliation_str = "Unknown"
            else:
                affiliation_str = author.affiliation
            if author.affiliation == "":
                affiliation_str = "Unknown"
           
            # affiliation_str = cleanup_affiliation(affiliation_str)
            
            # aff_name = ""
            # if affiliation_str in affiliation_norm_map:
            #     aff_name = affiliation_norm_map[affiliation_str]
            # 
            # if aff_name == "":
            #     for key in affiliation_norm_map:
            #         if affiliation_str.lower() in key.lower():
            #             aff_name = affiliation_norm_map[key]
            # 
            # if aff_name == "":
            #     for key in academic_affiliations_map:
            #         if affiliation_str.lower() in key.lower():
            #             aff_name = academic_affiliations_map[key]
            
            # if aff_name == "" :
            #     print(f"Could not normalise affiliation: {affiliation_str}")
            #     aff_name = f"Unknown ({affiliation_str})"
                
            doc_date = rfc.date()
            
            
                    