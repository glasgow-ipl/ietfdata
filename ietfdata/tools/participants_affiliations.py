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
	start_date  : datetime.date
	end_date    : Optional[datetime.date]
	OIDs : list[str]
	def __init__(self, start_date:datetime.date, end_date:Optional[datetime.date],OIDs:list[str]):
		self.OIDs=OIDs
		self.start_date = start_date
		if end_date is None:
			self.end_date = start_date
		else:
			self.end_date = end_date
	
	def set_end_date(self, new_end_date:datetime.date):
		self.end_date = new_end_date
	
	def set_affiliation_OIDs(self, OIDs:list[str]):
		self.OIDs=OIDs
	
	def match_OIDs(self, OIDs:list[str]):
		for OID in OIDs:
			if OID not in self.OIDs:
				return False
		return True
	
	def __str__(self):
		return_str = '{"OIDs":['
		return_str += ",".join(self.OIDs)
		return_str =  return_str.rstrip(',')
		return_str += "],"
		return_str += f'"start_date":"{self.start_date}","end_date":"{self.end_date}"}}'
		return return_str


# Sets of Affiliation for Person class
class AffiliationsForPerson:
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

			if not tmp_head_affil.match_names(affil.OIDs):
					tmp_head_affil.end_date = (datetime.strptime(affil.start_date,'%Y-%m-%d').date() - timedelta(days=1))
					consolidated_affil.append(tmp_head_affil)
					tmp_head_affil = copy.deepcopy(affil)
			if(tmp_head_affil not in consolidated_affil):
				consolidated_affil.append(tmp_head_affil)
		self.affiliations = copy.deepcopy(consolidated_affil)
	
	# def __str__(self):
	# 	returnstr = '{"identifiers":['
	# 	for ident in self.identifiers:
	# 		returnstr += f'"{ident}",'
	# 	returnstr = returnstr[:-1] # strip last comma
	# 	returnstr += "],"
	# 	returnstr += '"affiliations":['
	# 	for affil in self.affiliations:
	# 		returnstr+=str(affil)
	# 		returnstr+=","
	# 	returnstr = returnstr[:-1] # strip last comma
	# 	returnstr += "]}"
	# 	return returnstr
# generate mapping for PID->[OID,start,end]
if __name__ is "__main__":
	