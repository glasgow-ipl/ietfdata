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
def meeting_affiliation_mapping(from_year:int, until_year:int, input_mapping:Optional[list[aff.AffiliationMap]]):
    
    if input_mapping is None:
        af_mapping = list()
    else:
        af_mapping = copy.deepcopy(input_mapping)
    ident_index_map = dict()
    uniq_affil_list = dict()
    uniq_affil_raw = dict()
    # seen_addr_ietf = list()
    
    # Meeting type list API output:
    # [...]
    # <object>
    # <desc/>
    # <name>IETF</name>
    # <order type="integer">0</order>
    # <resource_uri>/api/v1/name/meetingtypename/ietf/</resource_uri>
    # <slug>ietf</slug>
    # <used type="boolean">True</used>
    # </object>
    # [...]
    meeting_registrations = dict()
    meeting_obj_from_id = dict()
    for meeting in dt.meetings(f"{from_year}-01-01",f"{until_year}-01-01",dt.meeting_type_from_slug('ietf')):
        registrations = dt.meeting_registrations(meeting=meeting)
        if meeting.id not in meeting_registrations:
            meeting_registrations[meeting.id] = registrations
        else:
            meeting_registrations[meeting.id].append(registrations)
        meeting_obj_from_id[meeting.id] = meeting
    for meeting_id in meeting_registrations:
        # Fetch date of the meeting
        meeting = meeting_obj_from_id[meeting_id]
        meeting_date = meeting.date
        for reg in meeting_registrations[meeting_id]:
            
            # TODO: fetch person_uri if possible, create mapping
            if reg.email is None:
                print(f"This registration by {reg.last_name}.{reg.first_name} does not have email, skip")
                continue
            person_obj = dt.person_from_email(email_addr=reg.email)
            if person_obj is not None:
                person_uri = str(person_obj.resource_uri)
            else:
                person_uri=None
            person_email_address = reg.email
            # tmp_ident_list = [person_uri,person_email_address]
            
            affiliation_str = None
            if reg.affiliation is None:
                affiliation_str = "Unknown"
            else:
                affiliation_str = reg.affiliation
            if reg.affiliation == "":
                affiliation_str = "Unknown"
        
            if affiliation_str not in uniq_affil_raw:
                uniq_affil_raw[affiliation_str] = 1
            else:
                uniq_affil_raw[affiliation_str] += 1
                
            aff_entry = aff.AffiliationEntry(affiliation_str,meeting_date,None,None)
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
        with open("./rfc_unique_affiliations_meetings.json",'w') as f:
            json.dump(uniq_affil_list,f)
        with open("./rfc_unique_affiliations_raw_meetings.json",'w') as f:
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
    affil_map = meeting_affiliation_mapping(2003,2025,affil_map)
    
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
