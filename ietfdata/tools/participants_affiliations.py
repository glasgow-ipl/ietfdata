import sys
import csv
import json 
import copy

from datetime import timedelta,date
from typing import Optional
from ietfdata.datatracker     import *
from ietfdata.datatracker_ext import *

# TODO: tests
# A class representing an affiliation entry 
class AffiliationEntry:
    _start_date  : date
    _end_date    : date
    _OID : str
    
    ## initialise
    def __init__(self, start_date:date, end_date:Optional[date],OID:str):
        self._OID = OID
        if isinstance(start_date,datetime):
            start_date = start_date.date()
        if end_date is not None and isinstance(end_date,datetime):
            end_date = end_date.date()
        self._start_date = start_date
        if end_date is not None and start_date < end_date:
            self._end_date = end_date 
        else:
            self._end_date = start_date 
    
    ## Getters
    def get_start_date(self)->date:
        return self._start_date

    def get_end_date(self)->date:
        return self._end_date
    
    def get_OID(self) -> str:
        return self._OID
    
    ## Setters
    def set_start_date(self,new_start_date:date)->None:
        if new_start_date > self._end_date:
            raise RuntimeError(f"Cannot set the start date ({new_start_date}) to be past the current end date {self._end_date}.")
        self._start_date = new_start_date
        
    def set_end_date(self, new_end_date:date):
        if new_end_date < self._start_date:
            raise RuntimeError(f"Cannot set the end date ({new_end_date}) to be earlier than the current start date {self._start_date}.")
        self._end_date = new_end_date

    def set_start_end_dates(self, new_start_date:date, new_end_date:date) -> None:
        if new_start_date > new_end_date:
            raise RuntimeError(f"Cannot set the end date ({new_end_date}) to be earlier than the new start date {new_start_date}.")
        self._start_date = new_start_date
        self._end_date = new_end_date
    
    ## Matches OIDs with given OIDs
    def match_OID(self, OID:str)->bool:
        return (self._OID == OID)
    
    def get_dictionary(self) -> dict:
        return_dict = dict()
        return_dict['organisation'] = self._OID 
        return_dict['start_date'] = self._start_date.strftime("%Y-%m-%d")
        return_dict['end_date'] = self._end_date.strftime("%Y-%m-%d")
        return return_dict
    
    # JSON Repl.
    # def __str__(self):
    #     return_str = '{"organisation":['
    #     return_str += ",".join(f'"{oid}"' for oid in self._OID)
    #     return_str =  return_str.rstrip(',')
    #     return_str += "],"
    #     return_str += f'"start_date":"{self._start_date}","end_date":"{self._end_date}"}}'
    #     return return_str


# Class representing a set of Affiliations for a Person, identified by PID from participants.py
class AffiliationsForPerson:
    _PID : str
    _affiliations: list[AffiliationEntry]
    
    def __init__(self,PID:str,affiliations:Optional[list[AffiliationEntry]]):
        self._PID = PID 
        self._affiliations = list()
        if affiliations is not None:
            self._affiliations = affiliations
    
    ## Getters
    def get_PID(self) -> str:
        return self._PID
        
    def get_affiliations(self) -> list[AffiliationEntry]:
        return self._affiliations
    
    ## Other func.
    def add_affiliation_with_date(self, OID:str, date:date) -> None:
        # Adds affiliation by date, fills any gap in dates towards later date
        # e.g. Affil. A, followed by another Affil. B with later date leads to Affil. A's end-date extended, and Affil. B entry added. 
        # Affil. C added within Affil. A's date range will split the 
        # Affil. A entry to two, inserting Affil. C between them.
        new_oid = OID
        if isinstance(date, datetime):
            date = date.date()
        new_date = date 
        new_end = new_date
        new_affil = AffiliationEntry(new_date,new_end,new_oid)
        if len(self._affiliations) == 0 :
            self._affiliations.append(new_affil)
            return
        for affil in self._affiliations:
            i = self._affiliations.index(affil)
            if affil.get_start_date()<=new_date and affil.get_end_date() >= new_end: 
                # new affil is within this affil's period
                if affil.match_OID(new_affil.get_OID()): 
                    # matching OIDs, no action
                    print(f"OIDs {new_affil.get_OID()} already within the date range in the existing entry.")
                    return
                else:
                    # non-matching OIDs, split
                    print(f"New OIDs {new_affil.get_OID()} do not match but falls within the date range for {affil.get_OID()}: split.")
                    old_affil_end_date = affil.get_end_date()
                    old_affil_OID = affil.get_OID()
                    self._affiliations[i].set_end_date(new_affil.get_end_date())
                    self._affiliations.insert(i+1,new_affil) # add just after
                    split_aff = AffiliationEntry(new_affil.get_end_date(),old_affil_end_date,old_affil_OID)
                    self._affiliations.insert(i+2,split_aff)
                    return
            # new affil is NOT within this affil's period
            if new_date <= affil.get_start_date():
                # new affil is before start date
                if affil.match_OID(new_oid):
                    # same affil but newer, extend
                    affil.set_start_date(new_date)
                    return
                # not matching
                if i > 0 :
                    # affil is not the first element, check the element before, extend if same
                    if self._affiliations[i-1].match_OID(new_oid):
                        # one before affil matches oid, extend the one before
                        self._affiliations[i-1].set_end_date(new_date)
                        return
                # no match found, insert, extend new affil's end date
                new_affil.set_end_date(affil.get_end_date())
                self._affiliations.insert(i,new_affil) 
                return
            # new affil is NOT within this affil, not within prior affils period
            # AND new affil is after this affil's period 
            if i == len(self._affiliations)-1 and affil.match_OID(new_oid):
                # since this is last element with matching OID, extend
                affil.set_end_date(new_date)
                return
        # does not fit within the existing timeline, append to extend
        print(f"Appending new affilition with ID: {OID}, with date: {new_date}")
        print(f"Extending last affiliation with ID: {self._affiliations[-1].get_OID()}, with date: {new_date}")
        self._affiliations[-1].set_end_date(new_date)
        self._affiliations.append(new_affil)
        return
    
    
    
    # def consolidate(self):
    #     # TODO: Go through the timeline, consolidate the history
    #     # This should only be run if and only if everything has been scraped
    #     tmp_head_affil = None # temporary first affil in the batch
    #     consolidated_affil = list()
    #     for affil in self._affiliations:
    #         if tmp_head_affil is None:
    #             tmp_head_affil = copy.deepcopy(affil)
    #             continue
    #         if not tmp_head_affil.match_names(affil.OIDs):
    #                 tmp_head_affil.end_date = (datetime.strptime(affil.start_date,'%Y-%m-%d').date() - timedelta(days=1))
    #                 consolidated_affil.append(tmp_head_affil)
    #                 tmp_head_affil = copy.deepcopy(affil)
    #         if(tmp_head_affil not in consolidated_affil):
    #             consolidated_affil.append(tmp_head_affil)
    #     self._affiliations = copy.deepcopy(consolidated_affil)
    
    # dictionary 
    def get_dictionary(self) -> dict[str,list]:
        return_dict : dict[str,list] = dict()
        return_dict['affiliations'] = list()
        for affil in self._affiliations:
            return_dict['affiliations'].append(affil.get_dictionary())
        return return_dict
    
    # JSON repl
    def __str__(self):
        returnstr = f"\"{self._PID}\":"
        returnstr += "{\"affiliations\":["
        for affil in self._affiliations:
            returnstr+=f"{str(affil)},"
        returnstr = returnstr.rstrip(',') # strip last comma
        returnstr += "]}"
        return returnstr

# This class holds and populated participants to affiliation mappings. 
# This needs participants and organisations information in dictionary from ietfdata.tools.participants and ietfdata.tools.organisations.
# If you create a subclass for other sources, the `__init__()` method of the
# subclass MUST call `super().__init__()` to correctly initialise the object.
class ParticipantsAffiliations:
    _pid_oid_map : dict[str,AffiliationsForPerson]
    _participants: dict
    _organisations: dict
    
    def __init__(self, participants:dict, organisations:dict) -> None:
        self._pid_oid_map = dict()
        self._participants = participants
        self._organisations = organisations
    
    def add_participants_affiliation_with_date(self, PID:str,OID:str,date:date)->None:
        if PID is None or PID == "":
            raise RuntimeError("PID is None or Empty")
        if OID is None or PID == "":
            raise RuntimeError("OID is None or Empty")
        if date is None:
            raise RuntimeError("date is None")
        if PID not in self._pid_oid_map:
            self._pid_oid_map[PID]=AffiliationsForPerson(PID,None)
        
        self._pid_oid_map[PID].add_affiliation_with_date(OID,date)
        
    ## IETF specific code:
    ### RFC
    def _find_participants_affiliations_ietf_rfc(self, dt:DataTracker, ri:RFCIndex) -> None:
        participants = self._participants
        organisations = self._organisations
        print("Going through IETF stream RFCs:")
        for rfc in ri.rfcs(stream="IETF", since="1995-01"):
            #print(f"   {rfc.doc_id}: {textwrap.shorten(rfc.title, width=80, placeholder='...')}")
            rfc_date = rfc.date()
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
                                break
                    if tmp_oid is None or tmp_oid == "":
                        continue
                    self.add_participants_affiliation_with_date(tmp_pid,tmp_oid,rfc_date)
    ### drafts
    def _find_participants_affiliations_ietf_drafts(self, dt:DataTracker, ri:RFCIndex) -> None:
        participants = self._participants
        organisations = self._organisations
        print(f"Going through draft submissions from \"1995-01-01\" until \"{date.today().strftime('%Y-%m-%d')}\":")
        for submission in dt.submissions(date_since = "1995-01-01", date_until = date.today().strftime('%Y-%m-%d')):
            print(f"{submission.name}-{submission.rev}")
            tmp_date = submission.submission_date
            for author in submission.parse_authors():
                if author['email'] is not None:
                    email = author['email']
                if 'affiliation' not in author:
                    print("** Missing affiliation in author dictionary.")
                    continue 
                if author['affiliation'] is not None:
                    affiliation = author['affiliation']
                
                tmp_pid = None
                for pid in participants:
                    participant = participants[pid]
                    if email.lower() in participant.get("email",[]):
                        tmp_pid = pid
                        break
                if tmp_pid is None or tmp_pid == "":
                    continue
                
                tmp_oid = None
                for oid in organisations:
                    organisation = organisations[oid]
                    for name in organisation.get("names",[]):
                            if affiliation.lower() == name.lower():
                                tmp_oid = oid
                                break
                if tmp_oid is None or tmp_oid == "":
                    continue
                self.add_participants_affiliation_with_date(tmp_pid,tmp_oid,tmp_date)
    
    ### Meeting registration
    def _find_participants_affiliations_ietf_meeting_reg(self, dt:DataTracker, ri:RFCIndex) -> None:
        participants = self._participants
        organisations = self._organisations
        print("Going through Meeting Registration:")
        for reg in dt.meeting_registrations():
            tmp_person = reg.person
            tmp_affiliation = reg.affiliation
            tmp_email = reg.email
            
            tmp_meeting = dt.meeting(reg.meeting)
            if tmp_meeting is None:
                print("Meeting is None, continue.")
                continue
            tmp_date = tmp_meeting.date
            tmp_pid = None
            
            for pid in participants:
                participant = participants[pid]
                if tmp_person in participant.get("dt_person_uri",[]):
                    tmp_pid = pid
                    break
                if tmp_email in participant.get("email",[]):
                    tmp_pid = pid
                    break
                    
            if tmp_pid is None or tmp_pid == "":
                continue
            
            tmp_oid = None
            
            for oid in organisations:
                organisation = organisations[oid]
                for name in organisation.get("names",[]):
                    if tmp_affiliation.lower() == name.lower():
                        tmp_oid = oid
                        break
            if tmp_oid is None or tmp_oid == "":
                continue
            self.add_participants_affiliation_with_date(tmp_pid,tmp_oid,tmp_date)
    
    ## gathers participants_affiliations mapping from ietf datatracker. 
    ## Needs to instanciate DataTracker and RFCIndex objects
    def find_participants_affiliations_ietf(self, dt:DataTracker, ri:RFCIndex) -> None:
        self._find_participants_affiliations_ietf_rfc(dt,ri)
        self._find_participants_affiliations_ietf_drafts(dt,ri)
        self._find_participants_affiliations_ietf_meeting_reg(dt,ri)
    
    ## Output code
    def toJSON(self) -> str:
        return_dict = dict()
        for pid, affil in self._pid_oid_map.items():
            return_dict[pid] = affil.get_dictionary()
        return json.dumps(return_dict, indent=4)
    
    def output(self,path) -> None:
        with open(path,'w') as f:
            print(f"About to write output to:{path}")
            f.write(self.toJSON())
    
    ## String output for debugging
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
    
    if len(sys.argv) == 5:
        path = Path(sys.argv[4])
    else:
        print("Usage: python3 -m ietfdata.tools.participants_affiliations <ietfdata.sqlite> <participants.json> <organisations.json> <output.json>")
        sys.exit(1)
    
    print(f"Loading participants from: {sys.argv[2]} and organisations from: {sys.argv[3]}")
    participants = None
    organisations = None
    with open(sys.argv[2]) as f:
        participants = json.load(f)
    with open(sys.argv[3]) as f:
        organisations = json.load(f)
    
    participants_affiliations = ParticipantsAffiliations(participants,organisations)       
    dt = DataTracker(DTBackendArchive(sqlite_file=sys.argv[1]))
    ri = RFCIndex(cache_dir = "cache")
    participants_affiliations.find_participants_affiliations_ietf(dt,ri)
    participants_affiliations.output(path)
    
    

    
   
        
        

    
    
