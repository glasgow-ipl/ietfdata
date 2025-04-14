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
from ietfdata.rfcindex import *
import ietfdata.tools.affiliations as aff


class TestAffiliations(unittest.TestCase):
    
    def test__setup_affiliation_mappings(self) -> None:
        print("Basic input/output test of affiliation mapping")
        mapping_list = list()
        
        tmp_ident_list= ['john@cisco.net']
        tmp_aff = aff.AffiliationEntry('Cisco Systems ','2019-02-01',None)
        tmp_aff_list = [tmp_aff]
        
        mapping_list.append(aff.AffiliationMap(tmp_ident_list,tmp_aff_list))
        
        for map in mapping_list:
            print(map)
            
            
    def test__setup_affiliation_mapping_sorts(self) -> None:
        print("Testing affiliation sorting")
        mapping_list = list()
        
        tmp_ident_list= ['john@cisco.net']
        tmp_aff = aff.AffiliationEntry('Cisco Systems ','2019-02-01',None)
        tmp_aff_list = [tmp_aff]
        
        tmp_aff2 = aff.AffiliationEntry('Cisco Systems','2021-02-01',None)
        tmp_aff3 = aff.AffiliationEntry('Cisco Systems','2023-02-01',None)
        tmp_aff4 = aff.AffiliationEntry('Juniper','2010-02-03',None)
        tmp_aff5 = aff.AffiliationEntry('Extreme Networks','2022-01-01',None)
        
        mapping_list.append(aff.AffiliationMap(tmp_ident_list,tmp_aff_list))
        mapping_list[0].add_affiliation(tmp_aff2)
        mapping_list[0].add_affiliation(tmp_aff3)
        mapping_list[0].add_affiliation(tmp_aff4)
        mapping_list[0].add_affiliation(tmp_aff5)
        for map in mapping_list:
            print(map)
            
    def test__setup_affiliation_mapping_consolidation(self) -> None:
        print("Testing affiliation consolidation")
        mapping_list = list()
        
        tmp_ident_list= ['john@cisco.net']
        tmp_aff = aff.AffiliationEntry('Cisco Systems ','2019-02-01',None)
        tmp_aff_list = [tmp_aff]
        
        tmp_aff2 = aff.AffiliationEntry('Cisco Systems','2021-02-01',None)
        tmp_aff3 = aff.AffiliationEntry('Cisco Systems','2023-02-01',None)
        tmp_aff4 = aff.AffiliationEntry('Juniper','2010-02-03',None)
        tmp_aff5 = aff.AffiliationEntry('Extreme Networks','2022-01-01',None)
        
        mapping_list.append(aff.AffiliationMap(tmp_ident_list,tmp_aff_list))
        mapping_list[0].add_affiliation(tmp_aff2)
        mapping_list[0].add_affiliation(tmp_aff3)
        mapping_list[0].add_affiliation(tmp_aff4)
        mapping_list[0].add_affiliation(tmp_aff5)
        for map in mapping_list:
            map.consolidate()
            print(map)        

if __name__ == '__main__':
    unittest.main()