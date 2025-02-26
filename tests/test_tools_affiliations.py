import os
import sys
import json
import unittest
import datetime
from pathlib       import Path
from unittest.mock import patch, Mock


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import ietfdata
from ietfdata.datatracker import *
import ietfdata.rfcindex import *
import ietfdata.tools.affiliations as aff


class TestAffiliations(unittest.TestCase):
    
    def test__setup_affiliation_mappings(self) -> None:
        mapping_list = list()
        
        tmp_ident_list= ['john@cisco.net']
        tmp_aff = aff.AffiliationEntry('Cisco Systems ','2019-02-01',None)
        tmp_aff_list = [tmp_aff]
        
        mapping_list.append(aff.AffiliationMap(tmp_ident_list,tmp_aff_list))
        
        for map in mapping_list:
            print(map)

if __name__ == '__main__':
    unittest.main()