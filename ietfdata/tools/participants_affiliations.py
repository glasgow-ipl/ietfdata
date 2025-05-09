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


# Todo: Class to go through datatracker to extract the information, clean up names, match two orgs etc.
# Affiliation Entry Class 
class AffiliationEntry:
    _start_date  : datetime.date
    _end_date    : datetime.date
    _OIDs : list[str]
    def __init__(self, start_date:datetime.date, end_date:Optional[datetime.date],OIDs:list[str]):
        self._OIDs=copy.deepcopy(OIDs) # prevent unintended modification of list
        self._start_date = start_date
        if end_date is None:
            self._end_date = start_date
        else:
            self._end_date = end_date

    def get_start_date(self)->datetime.date:
        return self._start_date

    def get_end_date(self)->datetime.date:
        return self._end_date
    
    def get_OIDs(self) -> list[str]:
        return self._OIDs
    
    def set_start_date(self,new_start_date:datetime.date)->None:
        if new_start_date > self._end_date:
            raise RuntimeError(f"Cannot set the start date ({new_start_date}) to be past the current end date {self._end_date}.")
        self._start_date = new_start_date
        
    def set_end_date(self, new_end_date:datetime.date):
        if new_end_date < self._start_date:
            raise RuntimeError(f"Cannot set the end date ({new_end_date}) to be earlier than the current start date {self._start_date}.")
        self.end_date = new_end_date

    def set_start_end_dates(self, new_start_date:datetime.date, new_end_date:datetime.date) -> None:
        if new_start_date > new_end_date:
            raise RuntimeError(f"Cannot set the end date ({new_end_date}) to be earlier than the new start date {new_start_date}.")
        self._start_date = new_start_date
        self._end_date = new_end_date
    
    def match_OIDs(self, OIDs:list[str])->bool:
        for OID in OIDs:
            if OID not in self._OIDs:
                return False
        return True
    
    def __str__(self):
        return_str = '{"OIDs":['
        return_str += ",".join(f'"{oid}"' for oid in self._OIDs)
        return_str =  return_str.rstrip(',')
        return_str += "],"
        return_str += f'"start_date":"{self._start_date}","end_date":"{self._end_date}"}}'
        return return_str


# Sets of Affiliation for Person class
class AffiliationsForPerson:
    _PID : str
    _affiliations: Optional[list[AffiliationEntry]]
    # _affiliations_by_start_date: Optional[dict[date,AffiliationEntry]]
    
    def __init__(self,PID:str,affiliations:Optional[list[AffiliationEntry]]):
        self._PID = PID 
        self._affiliations = list()
        if affiliations is not None:
            self._affiliations = affiliations
    
    def get_PID(self) -> str:
        return self._PID
        
    def get_affiliations(self) -> list[AffiliationEntry]:
        return self._affiliations
    
    
    def add_affiliation_with_date(self, OID:str, date:datetime.date) -> None:
        # TODO: Go through the timeline, insert the entry 
        new_oid = OID
        new_date = date 
        new_end = new_date
        new_affil = AffiliationEntry(new_date,new_end,[new_oid])
        if len(self._affiliations) == 0 :
            self._affiliations.append(new_affil)
            return
        for affil in self._affiliations:
            i = self._affiliations.index(affil)
            if affil.get_start_date()<=new_date and affil.get_end_date() >= new_end: 
                # new affil is within this affil's period
                if affil.match_OIDs(new_affil.get_OIDs()): 
                    # matching OIDs, no action
                    print(f"OIDs {new_affil.get_OIDs()} already within the date range in the existing entry.")
                    return
                else:
                    # non-matching OIDs, split
                    print(f"New OIDs {new_affil.get_OIDs()} do not match but falls within the date range for {affil.get_OIDs()}: split.")
                    old_affil_end_date = affil.get_end_date()
                    old_affil_oids = affil.get_OIDs()
                    self._affiliations[i].set_end_date(new_affil.get_end_date())
                    self._affiliations.insert(i+1,new_affil) # add just after
                    split_aff = AffiliationEntry(new_affil.get_end_date(),old_affil_end_date,old_affil_oids)
                    self._affiliations.insert(i+2,split_aff)
                    return
            # new affil is NOT within this affil's period
            if new_date <= affil.get_start_date():
                # new affil is before start date
                if affil.match_OIDs([new_oid]):
                    # same affil but newer, extend
                    affil.set_start_date(new_date)
                    return
                # not matching
                if i > 0 :
                    # affil is not the first element, check the element before, extend if same
                    if self._affiliations[i-1].match_OIDs([new_oid]):
                        # one before affil matches oid, extend the one before
                        self._affiliations[i-1].set_end_date(new_date)
                        return
                # no match found, insert, extend new affil's end date
                new_affil.set_end_date(affil.get_end_date())
                self._affiliations.insert(i,new_affil) 
                return
            # new affil is NOT within this affil, not within prior affils period
            # AND new affil is after this affil's period 
            if i == len(self._affiliations)-1 and affil.match_OIDs([new_oid]):
                # since this is last element with matching OID, extend
                affil.set_end_date(new_date)
                return
        # does not fit within the existing timeline, append to extend
        print(f"Appending new affilition with ID: {OID}, with date: {new_date}")
        print(f"Extending last affiliation with ID: {self._affiliations[-1].get_OIDs()}, with date: {new_date}")
        self._affiliations[-1].set_end_date(new_date)
        self._affiliations.append(new_affil)
        return
    
    def consolidate(self):
        # TODO: Go through the timeline, consolidate the history
        # This should only be run if and only if everything has been scraped
        tmp_head_affil = None # temporary first affil in the batch
        consolidated_affil = list()
        for affil in self._affiliations:
            if tmp_head_affil is None:
                tmp_head_affil = copy.deepcopy(affil)
                continue
            if not tmp_head_affil.match_names(affil.OIDs):
                    tmp_head_affil.end_date = (datetime.strptime(affil.start_date,'%Y-%m-%d').date() - timedelta(days=1))
                    consolidated_affil.append(tmp_head_affil)
                    tmp_head_affil = copy.deepcopy(affil)
            if(tmp_head_affil not in consolidated_affil):
                consolidated_affil.append(tmp_head_affil)
        self._affiliations = copy.deepcopy(consolidated_affil)
    
    def __str__(self):
        returnstr = f"\"{self._PID}\":"
        returnstr += "{\"affiliations\":["
        for affil in self._affiliations:
            returnstr+=f"{str(affil)},"
        returnstr = returnstr.rstrip(',') # strip last comma
        returnstr += "]}"
        return returnstr
        
class ParticipantsAffiliations:
    _pid_oid_map : dict[str,AffiliationsForPerson]
    
    def __init__(self) -> None:
        self._pid_oid_map = dict()
    
    def add_participants_affiliation_with_date(self, PID:str,OID:str,date:datetime.date)->None:
        if PID is None or PID == "":
            raise RuntimeError("PID is None or Empty")
        if OID is None or PID == "":
            raise RuntimeError("OID is None or Empty")
        if date is None:
            raise RuntimeError("date is None")
        if PID not in self._pid_oid_map:
            self._pid_oid_map[PID]=AffiliationsForPerson(PID,None)
        
        self._pid_oid_map[PID].add_affiliation_with_date(OID,date)
        
    def __str__(self):
        returnstr = "{"
        for pid in self._pid_oid_map:
            returnstr+=f"{str(self._pid_oid_map[pid])},"
        returnstr = returnstr.rstrip(',')
        returnstr += "}"
        return returnstr
    
# generate mapping for PID->[OID,start,end]
if __name__ == "__main__":
    print("*** ietfdata.tools.participants_affiliations")
    
    if len(sys.argv) == 4:
        path = Path(sys.argv[3])
    else:
        print("Usage: python3 -m ietfdata.tools.participants_affiliations <participants.json> <organisations.json> <output.json>")
        sys.exit(1)
    
    participants_affiliations = ParticipantsAffiliations()
    participants = None
    organisations = None
    with open(sys.argv[1]) as f:
        participants = json.load(f)
    with open(sys.argv[2]) as f:
        organisations = json.load(f)
    print(f"Loading participants from: {sys.argv[1]} and organisations from: {sys.argv[2]}")
    count = 0
    for participant in participants:
        print(f"{participant}:{participants[participant]}")
        count+=1
        if count > 10:
            break
    count = 0
    for organisation in organisations:
        print(f"{organisation}:{organisations[organisation]}")
        count+=1
        if count > 10:
            break
           
    dt = DataTracker(cache_timeout = timedelta(days=7))
    ri = RFCIndex(cache_dir = "cache")
    
    print("Going through IETF stream RFCs")
    for rfc in ri.rfcs(stream="IETF", since="1995-01"):
        #print(f"   {rfc.doc_id}: {textwrap.shorten(rfc.title, width=80, placeholder='...')}")
        date = rfc.date()
        dt_document = dt.document_from_rfc(rfc.doc_id)
        if dt_document is not None:
            for dt_author in dt.document_authors(dt_document):
                person_uri = str(dt_author.person)
                if dt_author.affiliation == "" or dt_author.email is None:
                    continue
                email  = dt.email(dt_author.email)
                
                tmp_pid = None
                
                for pid in participants:
                    participant = participants[pid]
                    if person_uri in participant.get("dt_person_uri",[]):
                        tmp_pid = pid
                        break
                    if email in participant.get("email",[]):
                        tmp_pid = pid
                        break
                        
                if tmp_pid is None or tmp_pid == "":
                    continue
                
                tmp_oid = None
                
                for oid in organisations:
                    organisation = organisations[oid]
                    for name in organisation.get("names",[]):
                        if dt_author.affiliation.lower() == name.lower():
                            tmp_oid = oid
                if tmp_oid is None or tmp_oid == "":
                    continue
                participants_affiliations.add_participants_affiliation_with_date(tmp_pid,tmp_oid,date)
    with open(sys.argv[3],'w') as f:
        print(f"About to write output to:{sys.argv[3]}")
        f.write(str(participants_affiliations))
    
    