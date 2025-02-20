import sys
import csv
import json 

from ietfdata.datatracker     import *
from ietfdata.datatracker_ext import *
from ietfdata.mailarchive2    import *
import mailarchive_mbox 

# affiliations.py --- script to generate extract affiliations
# Mappings generated:
# 1. raw affiliation -> normalised affiliation mappings
# 2. email_domain -> normalised affiliations mappings
# 3. [PID] -> [years] -> [affiliations] mappings from documents 
# 4. [PID] -> [years] -> [affiliations] mappings from emails

# normalisation strings

