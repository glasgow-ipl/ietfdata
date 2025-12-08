# Copyright (C) 2021-2025 University of Glasgow
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT thirdpartyS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import unittest
import os
import sqlite3
import sys

import pymongo 

from datetime             import date, datetime, timedelta, timezone
from email.headerregistry import Address
from pathlib              import Path
from unittest.mock        import patch, Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ietfdata.datatracker  import *
from ietfdata.mailarchive3 import *
from ietfdata.mailarchive3 import _parse_message

# =================================================================================================================================
# Unit tests:

class TestMailArchive3(unittest.TestCase):
    db : sqlite3.Connection
    dt : DataTracker
    ma : MailArchive

    @classmethod
    def setUpClass(self) -> None:
        sqlite_file = "data/ietfdata-ma.sqlite"
        self.ma = MailArchive(sqlite_file)
        self.db = sqlite3.connect(sqlite_file)

    # ==============================================================================================
    # Tests for message header parsing follow:

    def _check_from(self, ml_name: str, uidvalidity, uid: int, name: Optional[str], addr: Optional[str]) -> None:
        dbc = self.db.cursor()
        sql = "SELECT message FROM ietf_ma_msg WHERE mailing_list = ? and uidvalidity = ? and uid = ?;"
        res = dbc.execute(sql, (ml_name, uidvalidity, uid)).fetchall()
        if len(res) == 0:
            self.fail(f"Cannot find message {ml_name}/{uid} with uidvalidity={uidvalidity}")
        msg = _parse_message(uidvalidity, uid, res[0][0])
        self.assertEqual(msg["from_name"], name)
        self.assertEqual(msg["from_addr"], addr)


    def test_mailarchive3_parsing_header_from(self) -> None:
        self._check_from("822ext",            1455297825,    280, 'Bob Miles',                         'rsm@spyder.ssw.com')
        self._check_from("87all",             1455297825,      9, 'IAB Chair',                         'iab-chair@ietf.org')
        self._check_from("appleip",           1455297825,    144, 'Mike Traynor',                      'mtraynor@hpindps.cup.hp.com')
        self._check_from("apps-discuss",      1455297825,   1033, 'The IESG',                          'iesg-secretary@ietf.org')
        self._check_from("apps-discuss",      1455297825,   2538, 'Dave CROCKER',                      'dhc@dcrocker.net')
        self._check_from("apps-discuss",      1455297825,   5965, 'Murray S. Kucherawy',               'msk@cloudmark.com')
        self._check_from("apps-discuss",      1455297825,   7905, 'Mark Nottingham',                   'mnot@mnot.net')
        self._check_from("apps-discuss",      1455297825,   7905, 'Mark Nottingham',                   'mnot@mnot.net')
        self._check_from("atm",               1455297825,   1011, 'Earl E. McCoy',                      None)
        self._check_from("atm",               1455297825,   4828,  None,                               'Michelle.Claude@prism.uvsq.fr')
        self._check_from("big-internet",      1455297825,   4756, "Ole Christian Flem",                 None)
        self._check_from("big-internet",      1455297825,   2079,  None,                               'Christian.Huitema@sophia.inria.fr')
        self._check_from("bmwg",              1455297825,   1896, 'The IESG',                          'iesg-secretary@ietf.org')
        self._check_from("ccamp",             1455297825,  11101, "IETF Secretariat",                  'ietf-ipr@ietf.org')
        self._check_from("cfrg",              1455297825,   1202, 'Sara Caswell',                      'sara@nist.gov')
        self._check_from("datatracker-rqmts", 1455297825,     51, 'IETF Secretariat',                  'messenger@webex.com')
        self._check_from("dbound",            1455297825,    443, 'Pete Resnick',                      'presnick@qti.qualcomm.com')
        self._check_from("dcp",               1455297825,    120,  None,                                None)
        self._check_from("dhcwg",             1455297825,    561, '��������',                          'office7000@yahoo.co.kr')
        self._check_from("dhcwg",             1455297825,    562, '��������',                          'office700@yahoo.co.kr')
        self._check_from("dhcwg",             1455297825,    573, '��������',                          'office7000@yahoo.co.kr')
        self._check_from("dhcwg",             1455297825,    691,  None,                                None)
        self._check_from("dhcwg",             1455297825,   2001, 'Ted Lemon',                         'mellon@nominum.com')
        self._check_from("dmarc",             1455297825,   9284, 'Alessandro Vesely',                 'vesely@tana.it')
        self._check_from("dmarc",             1455297825,  10674, 'Alessandro Vesely',                 'vesely@tana.it')
        self._check_from("dnsext",            1455297825,   6156, 'The IESG',                          'iesg-secretary@ietf.org')
        self._check_from("dnsext",            1455297825,  19659, 'Olafur Gudmundsson',                'ogud@ogud.com')
        self._check_from("dnsext",            1455297825,  19389, 'Randy Bush',                        'randy@psg.com')
        self._check_from("dnsext",            1455297825,  14975, 'David Blacka',                      'davidb@verisignlabs.com')
        self._check_from("dnsext",            1455297825,  22410, 'Olafur Gudmundsson',                'ogud@hlid.dc.ogud.com')
        self._check_from("dnsext",            1455297825,  25204, 'Olafur Gudmundsson',                'ogud@ogud.com')
        self._check_from("dnsext",            1455297825,  25483, 'Olafur Gudmundsson',                'ogud@tislabs.com')
        self._check_from("dnsext",            1455297825,  26743, 'Dwayne Carter',                     'wisdom@mindless.com')
        self._check_from("dnsop",             1455297825,   7857, 'Paul Vixie',                        'vixie@isc.org')
        self._check_from("domainrep",         1455297825,    235, 'Scott Kitterman',                   'ietf-dkim@kitterman.com')
        self._check_from("drums",             1455297825,    893, 'D. J. Bernstein',                   'djb@cr.yp.to')
        self._check_from("endymail",          1455297825,      3, 'Pete Resnick',                      'presnick@qti.qualcomm.com')
        self._check_from("entmib",            1455297825,     84, 'Margaret Wasserman',                'mrw@windriver.com')
        self._check_from("enum",              1455297825,   1342, 'â������',                           'office700700@yahoo.co.kr')
        self._check_from("enum",              1455297825,   1385, '��������',                          'office700@yahoo.co.kr')
        self._check_from("enum",              1455297825,   1691,  None,                                None)
        self._check_from("enum",              1455297825,   1697,  None,                                None)
        self._check_from("enum",              1455297825,   2504, 'Internet-Drafts Administrator',     'internet-drafts@ietf.org')
        self._check_from("gen-art",           1455297825,   1838, 'Derek Atkins <derek@ihtfp.com>',    'derek@MIT.EDU')
        self._check_from("hipsec",            1455297825,     95, 'Dave Crocker',                      'dcrocker@brandenburg.com')
        self._check_from("hipsec",            1455297825,    523, 'Spencer Dawkins',                   'spencer@mcsr-labs.org')
        self._check_from("hostmib",           1455297825,    126, 'Harry Lewis <harryl@vnet.ibm.com>', 'harryl@vnet.ibm.com')
        self._check_from("httpbisa",          1455297825,  26679, 'Marcelline Adala',                  'postmaster@rcs-moscow.ru')
        self._check_from("httpbisa",          1455297825,  27964, 'Mr Cyril Oba',                      'hgdgd@hkjhkjhk.onmicrosoft.com')
        self._check_from("httpbisa",          1455297825,  30493, 'Famous translation experts',        'kehu@newbridgetranslation.com.cn')
        self._check_from("hubmib",            1455297825,    187, 'C. M. Heard',                       'heard@pobox.com')
        self._check_from("icnrg",             1455297825,   3172, 'Mosko, Marc <mmosko@parc.com>',     'mmosko@parc.com')
        self._check_from("ident",             1455297825,    426, 'Scott Bradner',                     'sob@harvard.edu')
        self._check_from("idn",               1455297825,   1755, 'D. J. Bernstein',                   'djb@cr.yp.to')
        self._check_from("idn",               1455297825,   3364, '헨타이',                            'sadfsad-a@yahoo.co.kr')
        self._check_from("idr",               1455297825,   6959, 'Fenggen Jia',                       'fgjia@mail.zjgsu.edu.cn')
        self._check_from("ietf",              1455297825,    762, 'Jeffrey Case',                      'case@utkvx.utk.edu')
        self._check_from("ietf",              1455297825,   1448, 'Einar Stefferud',                   'stef@nma.com')
        self._check_from("ietf",              1455297825,   1799, 'Steve Hardcastle-Kille',            'S.Kille@isode.com')
        self._check_from("ietf",              1455297825,   4207, 'Taso N. Devetzis',                  'devetzis@bellcore.com')
        self._check_from("ietf",              1455297825,   4236, 'Joyce Reynolds',                    'jkrey@isi.edu')
        self._check_from("ietf",              1455297825,   5582, 'Erik Huizer (SURFnet BV)',          'Erik.Huizer@surfnet.nl')
        self._check_from("ietf",              1455297825,   6670, 'Scott Bradner',                     'sob@harvard.edu')
        self._check_from("ietf",              1455297825,   7139, 'David Crocker',                     'dcrocker@mordor.stanford.edu')
        self._check_from("ietf",              1455297825,   7281, 'Ellen Hoffman',                     'ellen@merit.edu')
        self._check_from("ietf",              1455297825,  24815, 'Mail Delivery Subsystem',           'MAILER-DAEMON@OPTIMUS.IETF.ORG')
        self._check_from("ietf",              1455297825,  31528, 'Michael W. Condry',                 'condry@intel.com')
        self._check_from("ietf",              1455297825,  32393,  None,                                None)
        self._check_from("ietf",              1455297825,  33565, 'kim hyun jung',                     'hjin23@yahoo.co.kr')
        self._check_from("ietf",              1455297825,  34496, 'David Farber',                      'dave@farber.net')
        self._check_from("ietf",              1455297825,  40934, 'Dave Crocker',                      'dhc@dcrocker.net')
        self._check_from("ietf",              1455297825,  40941, 'Dave Crocker',                      'dcrocker@brandenburg.com')
        self._check_from("ietf",              1455297825,  60328, 'John Schnizlein',                   'jschnizl@cisco.com')
        self._check_from("ietf",              1455297825,  63551, 'Sam Hartman',                       'hartmans-ietf@mit.edu')
        self._check_from("ietf",              1455297825,  66909, 'The IESG',                          'iesg@ietf.org')
        self._check_from("ietf",              1455297825,  81507, 'RSOC Chair',                        'rsoc-chair@iab.org')
        self._check_from("ietf",              1455297825,  83166, 'RSOC Chair',                        'rsoc-chair@iab.org')
        self._check_from("ietf",              1455297825,  83218, 'Sam Hartman',                       'hartmans-ietf@mit.edu')
        self._check_from("ietf",              1455297825,  86553, 'Ole Jacobsen',                      'ole@cisco.com')
        self._check_from("ietf",              1455297825, 100370, 'Pete Resnick',                      'presnick@qti.qualcomm.com')
        self._check_from("ietf-announce",     1455297825,   4454, 'The IESG',                          'iesg-secretary@ietf.org')
        self._check_from("ietf-announce",     1455297825,   8883, 'RSOC Chair',                        'rsoc-chair@iab.org')
        self._check_from("ietf-announce",     1455297825,  13988, 'IAB Chair',                         'iab-chair@ietf.org')
        self._check_from("ietf-dkim",         1455297825,   7435, 'J.D. Falk',                         'jdfalk@cybernothing.org')
        self._check_from("ietf-dkim",         1455297825,   7444, 'Matthew Joseff',                    'matthew@joseff.com')
        self._check_from("ietf-languages",    1490901519,   3097, 'Michelle Cotton via RT',            'iana-prot-param@icann.org')
        self._check_from("ietf-languages",    1490901519,   4003, 'Sudhindra Kumar',                   'tlsudhi442@gmail.com')
        self._check_from("ietf-languages",    1490901519,   4960, 'CE Whitehead',                      'cewcathar@hotmail.com')
        self._check_from("ietf-smtp",         1455297825,   7178, 'Robert A. Rosenberg',               'hal9001@panix.com')
        self._check_from("ietf-types",        1455297825,     27, 'Chris Lilley',                      'chris@w3.org')
        self._check_from("imap",              1455297825,    326, 'Peter Svanberg',                    'psv@nada.kth.se')
        self._check_from("imap",              1455297825,   1007, 'Olle Jarnefors',                    'ojarnef@admin.kth.se')
        self._check_from("ipae",              1455297825,    306,  None,                               'Christian.Huitema@sophia.inria.fr')
        self._check_from("ipp",               1455297825,   3963,  None,                                None)
        self._check_from("ipp",               1455297825,   4406,  None,                                None)
        self._check_from("ipp",               1455297825,   4418,  None,                                None)
        self._check_from("ipp",               1455297825,   4419,  None,                                None)
        self._check_from("ipp",               1455297825,   4531,  None,                                None)
        self._check_from("ipp",               1455297825,   6240,  None,                                None)
        self._check_from("ipp",               1455297825,   6242,  None,                                None)
        self._check_from("ipp",               1455297825,   6248,  None,                                None)
        self._check_from("ipp",               1455297825,   6255,  None,                                None)
        self._check_from("ipp",               1455297825,   6259,  None,                                None)
        self._check_from("ipp",               1455297825,   6262,  None,                                None)
        self._check_from("ipp",               1455297825,   6600,  None,                                None)
        self._check_from("ipp",               1455297825,   6604,  None,                                None)
        self._check_from("ipp",               1455297825,   6605,  None,                                None)
        self._check_from("ipp",               1455297825,   6608,  None,                                None)
        self._check_from("ipp",               1455297825,   6626,  None,                                None)
        self._check_from("ipp",               1455297825,   6724,  None,                                None)
        self._check_from("ipp",               1455297825,   6742,  None,                                None)
        self._check_from("ipsec",             1455297825,   2183, 'The IESG',                          'iesg-secretary@ietf.org')
        self._check_from("ipsec",             1455297825,   2383, 'The IESG',                          'iesg-secretary@ietf.org')
        self._check_from("ipsec",             1455297825,  13089, 'burt',                              'burt@RSA.COM')
        self._check_from("ipsec",             1455297825,  15533, 'by way of Frank Reeves <freeves@pop.hq.tis.com>', 'owner-ipsec@tis.com')
        self._check_from("ipsec",             1455297825,  18758, 'Michael Richardson',                'mcr@sandelman.ottawa.on.ca')
        self._check_from("kitten",            1455297825,    623, 'Sam Hartman',                       'hartmans-ietf@mit.edu')
        self._check_from("krb-wg",            1455297825,   4473,  None,                                None)
        self._check_from("krb-wg",            1455297825,   4477,  None,                                None)
        self._check_from("krb-wg",            1455297825,   4492,  None,                                None)
        self._check_from("krb-wg",            1455297825,   4558,  None,                                None)
        self._check_from("krb-wg",            1455297825,   4567,  None,                                None)
        self._check_from("krb-wg",            1455297825,   4874, 'Vydox',                             'evinces@fatroop.eu')
        self._check_from("krb-wg",            1455297825,   4919, 'Paleo Burn',                        'indigested@coud.eu')
        self._check_from("krb-wg",            1455297825,   4991,  None,                                None)
        self._check_from("krb-wg",            1455297825,   5053,  None,                                None)
        self._check_from("krb-wg",            1455297825,   5090, 'Paleo Burn',                        'broadness@commitee.eu')
        self._check_from("krb-wg",            1455297825,   5296, 'Protect Your Children � Kids Live Safe', 'americanised@wretchedness.red')
        self._check_from("krb-wg",            1455297825,   5403, 'Kids Live Safe',                    'carbolization@Tagspace.kim')
        self._check_from("krb-wg",            1455297825,   5417, 'Research Update',                   'flours@Demiveo.blue')
        self._check_from("krb-wg",            1455297825,   5563, 'Paleo Burn',                        'Aida@Viboo-boo.red')
        self._check_from("krb-wg",            1455297825,   5592, 'Blood Pressure Fix',                'bolster@me5good.club')
        self._check_from("krb-wg",            1455297825,   6119,  None,                                None)
        self._check_from("krb-wg",            1455297825,   6121,  None,                                None)
        self._check_from("krb-wg",            1455297825,   6129,  None,                                None)
        self._check_from("krb-wg",            1455297825,   6307, 'Mike Ward',                         'greatly@papaumbrella.pw')
        self._check_from("krb-wg",            1455297825,   6471,  None,                                None)
        self._check_from("krb-wg",            1455297825,   6511, 'Rent To Own Homes',                 'coppery@mailgoingstrong.rocks')
        self._check_from("krb-wg",            1455297825,   6741,  None,                                None)
        self._check_from("krb-wg",            1455297825,   6968, 'Rent To Own Homes',                 'heartily@thingstodo.rocks')
        self._check_from("krb-wg",            1455297825,   6969, 'Rent To Own Homes',                 'cranwell@thingstodo.rocks')
        self._check_from("krb-wg",            1455297825,   7528,  None,                                None)
        self._check_from("krb-wg",            1455297825,   7556,  None,                                None)
        self._check_from("krb-wg",            1455297825,   8348,  None,                                None)
        self._check_from("krb-wg",            1455297825,   8383,  None,                                None)
        self._check_from("krb-wg",            1455297825,   8386,  None,                                None)
        self._check_from("krb-wg",            1455297825,  12650,  None,                                None)
        self._check_from("krb-wg",            1455297825,  12651,  None,                                None)
        self._check_from("krb-wg",            1455297825,  14268,  None,                                None)
        self._check_from("ldap-dir",          1455297825,   1407, 'Belcher',                           'breezeysaqb@yahoo.co.kr')
        self._check_from("ldap-dir",          1455297825,   1423, 'Mcrae',                             'nathankutjewqmb@yahoo.co.kr')
        self._check_from("ldap-dir",          1455297825,   1554, 'MRS.MONICA LOPEZ',                  'semana-santa@excite.com')
        self._check_from("ldap-dir",          1455297825,   1676, 'oavkho pwqhwyczx',                  'fzorqda@nemoves.com')
        self._check_from("lisp",              1455297825,   1241, 'Sam Hartman',                       'hartmans-ietf@mit.edu')
        self._check_from("ltru",              1455297825,   4950, 'Debbie Garside',                    'md@ictmarketing.co.uk')
        self._check_from("manet",             1455297825,   2827, 'Joo-Han Song',                      'sjh1swj@yahoo.co.kr')
        self._check_from("megaco",            1455297825,   1513, 'â������',                           'office7000@yahoo.co.kr')
        self._check_from("megaco",            1455297825,   1752, '�������Ĵ���',                       'kisroom@yahoo.co.kr')
        self._check_from("midcom",            1455297825,   1758, '[����]�ٱ���.wo.to',                 'phj234@yahoo.co.kr')
        self._check_from("midcom",            1455297825,   1774, 'â������',                           'office7000@yahoo.co.kr')
        self._check_from("midcom",            1455297825,   1836, '�������Ĵ���',                       'kisroom@yahoo.co.kr')
        self._check_from("midcom",            1455297825,   1927, 'mgpwkr',                            'adadcom3@yahoo.co.kr')
        self._check_from("midcom",            1455297825,   1958, '����õ��',                           'mailad1004@yahoo.co.kr')
        self._check_from("mmusic",            1455297825,   3935, 'creditcard',                        'creditcard5@yahoo.co.kr')
        self._check_from("mmusic",            1455297825,   3936, 'insuwa',                            'insuwa@yahoo.co.kr')
        self._check_from("mmusic",            1455297825,   3977, 'ktf member',                        'adadcom3@yahoo.co.kr')
        self._check_from("mmusic",            1455297825,   4742, 'Nils Henrik Lorentzen',             'nhl@tandberg.no')
        self._check_from("mobopts",           1455297825,    521, 'WiMAX Day',                         'distribution@wimaxday.com')
        self._check_from("msec",              1455297825,    386, 'Herb Falk <herb@sisconet.com>',     'Herb@sisconet.com')
        self._check_from("msec",              1455297825,    409, 'Herb Falk <herb@sisconet.com>',     'Herb@sisconet.com')
        self._check_from("namedroppers",      1455297825,   4872, 'The IESG',                          'iesg-secretary@ietf.org')
        self._check_from("namedroppers",      1455297825,  10473, 'Randy Bush',                        'randy@psg.com')
        self._check_from("namedroppers",      1455297825,  12725, 'David Blacka',                      'davidb@verisignlabs.com')
        self._check_from("namedroppers",      1455297825,  13479, 'Ted Lemon',                         'mellon@nominum.com')
        self._check_from("nat",               1455297825,    148, 'â������',                           'office7000@yahoo.co.kr')
        self._check_from("netext",            1455297825,    158,  None,                               'jouni.nospam@gmail.com')
        self._check_from("netext",            1455297825,   3217,  None,                                None)
        self._check_from("netext",            1455297825,   3219, 'Domagoj Premec',                    'netext-bounces@mail.mobileip.jp')
        self._check_from("netext",            1455297825,   3226, 'marcelo bagnulo braun',             'netext-bounces@mail.mobileip.jp')
        self._check_from("netext",            1455297825,   3224,  None,                                None)
        self._check_from("netext",            1455297825,   3221, 'Behcet Sarikaya',                   'netext-bounces@mail.mobileip.jp')
        self._check_from("netext",            1455297825,   3222, 'Sri Gundavelli',                    'netext-bounces@mail.mobileip.jp')
        self._check_from("netext",            1455297825,   3223, 'Sri Gundavelli',                    'netext-bounces@mail.mobileip.jp')
        self._check_from("ngtrans",           1706314513,   2648, 'Anne Lord',                         'anne@apnic.net')
        self._check_from("nntpext",           1455297825,    884, 'SilverSingles Associate',           'info@adidanos.com')
        self._check_from("nntpext",           1455297825,    887, 'Natural Cannabis Gummies',          'info@adidanos.com')
        self._check_from("nntpext",           1455297825,    894, 'Dr.Theo Diktaban',                  'info@adidanos.com')
        self._check_from("nntpext",           1455297825,    903, 'South Beach Skin',                  'info@adidanos.com')
        self._check_from("nntpext",           1455297825,    905, 'SilverSingles Associate',           'info@adidanos.com')
        self._check_from("nntpext",           1455297825,    910, 'SilverSingles Associate',           'info@adidanos.com')
        self._check_from("nntpext",           1455297825,    919, '2020 Scores Details',               'info@adidanos.com')
        self._check_from("nntpext",           1455297825,    920, 'Age-Defying-Energy',                'info@adidanos.com')
        self._check_from("nntpext",           1455297825,    921, '2020Roofing Deals',                 'info@adidanos.com')
        self._check_from("nntpext",           1455297825,    922, 'Vivint.SmartHome',                  'info@adidanos.com')
        self._check_from("nntpext",           1455297825,    923, 'Immunity 911',                      'info@adidanos.com')
        self._check_from("nntpext",           1455297825,    924, '3 Bureau Credit Scores',            'info@adidanos.com')
        self._check_from("nntpext",           1455297825,    929, 'Youthful Brain',                    'info@adidanos.com')
        self._check_from("nsis",              1455297825,   1642,  None,                                None)
        self._check_from("nsis",              1455297825,   1741,  None,                                None)
        self._check_from("openpgp",           1455297825,    941, 'Steve Crocker',                     'crocker@cybercash.com')
        self._check_from("openpgp",           1455297825,   1669, 'Uri Blumenthal',                    'uri@watson.ibm.com')
        self._check_from("openpgp",           1455297825,   5844, 'Derek Atkins <derek@ihtfp.com>',    'derek@MIT.EDU')
        self._check_from("openpgp",           1455297825,   8138,  None,                                None)
        self._check_from("openpgp",           1455297825,   8139,  None,                                None)
        self._check_from("opes",              1455297825,     21, 'Dr.Chris Makeba',                   'chrismakeba@yahoo.com')
        self._check_from("pilc",              1455297825,    708, 'Reiner Ludwig',                     'rludwig@huginn.CS.Berkeley.EDU')
        self._check_from("pkix",              1455297825,     56, 'Michael S Baum',                    'baum@world.std.com')
        self._check_from("pkix",              1455297825,  22542, 'The IESG',                          'iesg-secretary@ietf.org')
        self._check_from("policy",            1455297825,    115, 'â������',                           'office7000@yahoo.co.kr')
        self._check_from("pwg",               1455297825,     16, 'Harry Lewis <harryl@vnet.ibm.com>', 'harryl@vnet.ibm.com')
        self._check_from("pwg",               1455297825,   1023, 'Marcia Beaulieu',                   'mbeaulie@ns.ietf.org')
        self._check_from("pwg",               1455297825,   1193, 'David R Spencer',                   'david@spencer.com')
        self._check_from("pwg",               1455297825,   1307, 'EKR',                               'ekr@terisa.com')
        self._check_from("pwg",               1455297825,   1371, 'Chen Chen',                         'cchen@cp10.es.xerox.com')
        self._check_from("pwg",               1455297825,   1946, 'Daniel Manchala',                   'manchala@cp10.es.xerox.com')
        self._check_from("pwg",               1455297825,   1998, 'Dan Wing',                          'dwing@cisco.com')
        self._check_from("pwg",               1455297825,   2155, 'The IESG',                          'iesg-secretary@ns.ietf.org')
        self._check_from("pwg",               1455297825,   2326, 'Josh Cohen',                        'joshco@microsoft.com')
        self._check_from("pwg",               1455297825,   2333, 'Jim Whitehead',                     'ejw@cloud.ics.uci.edu')
        self._check_from("pwg",               1455297825,   2429, 'Larry Masinter',                    'masinter@parc.xerox.com')
        self._check_from("pwg",               1455297825,   2537, 'Keith Moore',                       'moore@cs.utk.edu')
        self._check_from("pwg",               1455297825,   2575, 'Scott Isaacson',                    'SISAACSON@novell.com')
        self._check_from("pwg",               1455297825,   2706, 'Keith Moore',                       'moore@cs.utk.edu')
        self._check_from("qosr",              1455297825,     61, 'RFC Editor',                        'rfc-ed@isi.edu')
        self._check_from("rmt",               1455297825,     72, 'mgpwkr',                            'mgpwkr@yahoo.co.kr')
        self._check_from("rmt",               1455297825,     81, '��������',                          'kisroom@yahoo.co.kr')
        self._check_from("rserpool",          1455297825,    264, 'â������',                           'office7000@yahoo.co.kr')
        self._check_from("rsn",               1455297825,    249, '김진형',                            'jhkim1112@yahoo.co.kr')
        self._check_from("rsvp",              1455297825,     46, '王春文',                            'shenzhenlzh@126.com')
        self._check_from("rsvp",              1455297825,     71, '王文胜',                            'shenzhenlzh@126.com')
        self._check_from("rsvp",              1455297825,     81, '刘明辉',                            'shenzhenlzh@126.com')
        self._check_from("rsvp",              1455297825,     87, '王文胜',                            'shenzhenlzh@126.com')
        self._check_from("seamoby",           1455297825,   2236,  None,                                None)
        self._check_from("secsh",             1455297825,     14,  None,                                None)
        self._check_from("secsh",             1455297825,    719, 'Career Builder',                    'joboffer@careerinfo.com')
        self._check_from("send",              1455297825,    136,  None,                                None)
        self._check_from("sidrops",           1476641893,   2575, 'Randy Bush',                        'randy@psg.com')
        self._check_from("sip",               1455297825,  11549, 'â������',                           'office7000@yahoo.co.kr')
        self._check_from("sipp",              1455297825,    124,  None,                               'Christian.Huitema@sophia.inria.fr')
        self._check_from("smime",             1455297825,   3666, 'The IESG',                          'iesg-secretary@ietf.org')
        self._check_from("smime",             1455297825,   5090,  None,                                None)
        self._check_from("smtpext",           1455297825,   2881, 'Einar Stefferud',                   'stef@nma.com')
        self._check_from("smtpext",           1455297825,   3138, 'Olle Jarnefors',                    'ojarnef@admin.kth.se')
        self._check_from("snmp",              1455297825,    297, '(Contractor',                       'lbabb@wpdis11.hq.aflc.af.mil')
        self._check_from("snmp",              1455297825,   1217, 'Jeffrey Case',                      'case@utkvx.utk.edu')
        self._check_from("snmp",              1455297825,   1229, 'Jeffrey Case',                      'case@utkvx.utk.edu')
        self._check_from("snmpsec",           1455297825,    320, 'The Emminent Professor Case',       'case@seymour1.cs.utk.edu')
        self._check_from("snmpsec",           1455297825,    425, 'Marshall Rose',                     'mrose@dbc.mtview.ca.us')
        self._check_from("snmpv2",            1455297825,   2811, 'arw',                               'frt935t@gl0500.trt-philips.fr')
        self._check_from("snmpv2",            1455297825,   2985, 'arw',                               'frt935t@gl0500.trt-philips.fr')
        self._check_from("snmpv2",            1455297825,   3142, 'Keith McCloghrie',                  'kzm@cisco.com')
        self._check_from("thinosi",           1455297825,     30, 'System Manager and Postmaster <Postmaster@Ulcc>', 'SYSTEM@ulcc.ac.uk')
        self._check_from("thinosi",           1455297825,     53, 'System Manager and Postmaster <Postmaster@Ulcc>', 'SYSTEM@scgate.ulcc.ac.uk')
        self._check_from("thinosi",           1455297825,     66, 'System Manager and Postmaster <Postmaster@Ulcc>', 'SYSTEM@ulcc.ac.uk')
        self._check_from("thinosi",           1455297825,    113, 'System Manager and Postmaster <Postmaster@Ulcc>', 'SYSTEM@ulcc.ac.uk')
        self._check_from("tls",               1455297825,   2111, 'The IESG',                          'iesg-secretary@ietf.org')
        self._check_from("tmrg",              1455297825,      1,  None,                               'service@paypal.com')
        self._check_from("tmrg",              1455297825,      2,  None,                                None)
        self._check_from("tmrg",              1455297825,      3, 'LaSalle Bank',                      'security@lasallebank.com')
        self._check_from("tmrg",              1455297825,      7, 'PayPal',                            'PayPal@yahoo.com')
        self._check_from("tmrg",              1455297825,      9, 'Martha Hurley',                     'TerriWhalen@rsvp5.com')
        self._check_from("tmrg",              1455297825,     11, 'Erica Thacker',                     'MaureenHenderson@thefixishere.com')
        self._check_from("tmrg",              1455297825,     14, 'Robbie Ochoa',                      'arvweiz@nationalmens40.com')
        self._check_from("tmrg",              1455297825,     15, 'Josephine  Eubanks',                'ShelbyNehemias@nathaniel-brown.com')
        self._check_from("tmrg",              1455297825,     19, 'Doug Johnston',                     'CarmelaHolmes@allstretchedout.co.uk')
        self._check_from("tmrg",              1455297825,     20, 'eBay',                              'aw-verify@ebay.com')
        self._check_from("tmrg",              1455297825,     24, 'Terri Norman',                      'JenniferSellers@akerlie.co.uk')
        self._check_from("tmrg",              1455297825,     26, 'NCUA',                              'custserv@ncua.gov')
        self._check_from("tmrg",              1455297825,     28, 'Margery Benson',                    'SheldonHunter@chinking.net')
        self._check_from("tmrg",              1455297825,     29, 'Sky Bank',                          'personalib@skyfi.com')
        self._check_from("tmrg",              1455297825,     32, 'Nicole Cortes',                     'NicoleMcnamara@danielleosicki.com')
        self._check_from("tmrg",              1455297825,     33, 'Derek Pettit',                      'AidaBecker@evertoneproductions.com')
        self._check_from("tmrg",              1455297825,     38, 'Brenda Karpf',                      'CarolynDraper@santafecohousing.org')
        self._check_from("tmrg",              1455297825,     41, 'Francine Muniz',                    'AlfonsoSilva@zoomgirls.com')
        self._check_from("tmrg",              1455297825,     42, 'Jonas Hubbard',                     'LynnOuellette@withteacher.net')
        self._check_from("tmrg",              1455297825,     46, 'Carmela Livingston',                'DanniePortnoy@wallal.com')
        self._check_from("tmrg",              1455297825,     48, 'Ingrid Rollins',                    'MelanieMead@ydpr.com')
        self._check_from("tmrg",              1455297825,     63, 'Erica Tisch',                       'KateLowe@backbands.com')
        self._check_from("tmrg",              1455297825,     64, 'Sylvester Arellano',                'ColemanKoenig@xiangrentang.com')
        self._check_from("tmrg",              1455297825,     65, 'Armed Forces Bank',                 'customerservices@afbank.com')
        self._check_from("tools-discuss",     1455297825,   4928, 'Michael Witten',                    'mfwitten@gmail.com')
        self._check_from("trade",             1455297825,   1013, '��<��<',                            'eunil4259@yahoo.co.kr')
        self._check_from("trigtran",          1455297825,     82,  None,                                None)
        self._check_from("trunkmib",          1455297825,     19, 'Jose J. Hoard <HOARD@RALVM6.VNET.IBM.COM>', 'HOARD@ralvm6.vnet.ibm.com')
        self._check_from("trunkmib",          1455297825,    544, 'Jose J. Hoard <hoard@vnet.ibm.com>',        'hoard@vnet.ibm.com')
        self._check_from("tsvwg",             1455297825,   1879, 'â������',                           'office700@yahoo.co.kr')
        self._check_from("tsvwg",             1455297825,   1939, 'â������',                           'office7000@yahoo.co.kr')
        self._check_from("tsvwg",             1455297825,   2162, 'fighterbird',                       'fighterbird@yahoo.co.kr')
        self._check_from("tsvwg",             1455297825,   4588, 'Kwok Ho Chan',                      'khchan@nortelnetworks.com')
        self._check_from("uri",               1455297825,     72, 'Rickard Schoultz',                  'schoultz@othello.admin.kth.se')
        self._check_from("uri",               1455297825,   1770, 'Olle Jarnefors',                    'ojarnef@admin.kth.se')
        self._check_from("urn",               1455297825,    232, 'David G. Durand',                   'dgd@cs.bu.edu')
        self._check_from("v6ops",             1455297825,  24521,  None,                                None)
        self._check_from("v6ops",             1455297825,  24530,  None,                                None)
        self._check_from("v6ops",             1455297825,  24531,  None,                                None)
        self._check_from("webdav",            1455297825,  20954, 'Ronald E. Blaylock',                'quote@pfizersourcing-nl.com')
        self._check_from("webdav",            1455297825,  21014, 'Myunga',                            'ddirik@esertelekom.com')
        self._check_from("wgchairs",          1455297825,   9778, 'RSOC Chair',                        'rsoc-chair@iab.org')
        self._check_from("wgchairs",          1455297825,  12800, 'Pete Resnick',                      'presnick@qti.qualcomm.com')
        self._check_from("wrec",              1455297825,   1218, 'Jemma',                             'xcon-bounces@ietf.org')
        self._check_from("wrec",              1455297825,   1219, 'Verran',                            'xcon-bounces@ietf.org')
        self._check_from("wrec",              1455297825,   1618, 'Delroy',                            'osipenko@vidnoe-online.ru')
        self._check_from("wrec",              1455297825,   1628, 'Dick',                              'koro@pervy.ru')
        self._check_from("wrec",              1455297825,   1831, 'WATCHES',                           'veronica@kashlinsky.com')
        self._check_from("wrec",              1455297825,   1891, 'Best Watch',                        'janna12@rufox.ru')
        self._check_from("wrec",              1455297825,   1903, 'Super Watch',                       'natalex1506@unitybox.de')
        self._check_from("wrec",              1455297825,   1992, 'Luxury watches',                    'Herbert@mail.ru')
        self._check_from("wrec",              1455297825,   2006, 'Luxury watches',                    'ali-wilson@tiscali.co.uk')
        self._check_from("wrec",              1455297825,   2012, 'Luxury watch',                      'reseberry@hanmail.net')
        self._check_from("wrec",              1455297825,   2062, 'REPLICA WATCHES',                   'jgirard@fused-media.com')
        self._check_from("wrec",              1455297825,   2450, 'REPLICA WATCH',                     'Gordb@outlook.com')
        self._check_from("wrec",              1455297825,   2673, 'Shelton',                           'Sheltonai@sbcglobal.net')
        self._check_from("wrec",              1455297825,   2738, 'MyCanadian Pharmacy',               'Rosamundnjobe@sbcglobal.net')
        self._check_from("wrec",              1455297825,   2743, 'MyCanadian Pharmacy',               'Leenag@sbcglobal.net')
        self._check_from("xml2rfc",           1455297825,     40, 'Bjoern Hoehrmann',                  'derhoermi@gmx.net')
        self._check_from("xml2rfc",           1455297825,    177, 'Michael Mealling',                  'michael@neonym.net')
        self._check_from("xml2rfc",           1455297825,    935, 'Spencer Dawkins',                   'spencer@mcsr-labs.org')
        self._check_from("xml2rfc",           1455297825,   1367, 'Russ White',                        'riw@cisco.com')

    # ==============================================================================================
    # Tests for the Envelope class follow:

    def test_mailarchive3_envelope_mailing_list(self) -> None:
        msgs = self.ma.message("<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].mailing_list().name(), "cfrg")


    def test_mailarchive3_envelope_uidvalidity(self) -> None:
        msgs = self.ma.message("<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].uidvalidity(), 1455297825)


    def test_mailarchive3_envelope_uid(self) -> None:
        msgs = self.ma.message("<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].uid(), 14157)


    def test_mailarchive3_envelope_date_received(self) -> None:
        msgs = self.ma.message("<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].date_received(), datetime.fromisoformat("2025-04-18T05:30:21+00:00"))


    def test_mailarchive3_envelope_size(self) -> None:
        msgs = self.ma.message("<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].size(), 6866)


    def test_mailarchive3_envelope_message_id(self) -> None:
        msgs = self.ma.message("<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].message_id(), "<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")


    def test_mailarchive3_envelope_from(self) -> None:
        msgs = self.ma.message("<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")
        self.assertEqual(len(msgs), 1)
        from_ = msgs[0].from_()
        if from_ is not None:
            self.assertEqual(from_.display_name, "Stanislav V. Smyshlyaev")
            self.assertEqual(from_.username,     "smyshsv")
            self.assertEqual(from_.domain,       "gmail.com")
            self.assertEqual(from_.addr_spec,    "smyshsv@gmail.com")
        else:
            self.fail(f"Cannot find message")


    def test_mailarchive3_envelope_to(self) -> None:
        msgs = self.ma.message("<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(len(msgs[0].to()), 1)
        self.assertEqual(msgs[0].to()[0].display_name, "CFRG")
        self.assertEqual(msgs[0].to()[0].username,     "cfrg")
        self.assertEqual(msgs[0].to()[0].domain,       "irtf.org")
        self.assertEqual(msgs[0].to()[0].addr_spec,    "cfrg@irtf.org")


    def test_mailarchive3_envelope_cc(self) -> None:
        msgs = self.ma.message("<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(len(msgs[0].cc()), 2)
        self.assertEqual(msgs[0].cc()[0].display_name, "")
        self.assertEqual(msgs[0].cc()[0].username,     "cfrg-chairs")
        self.assertEqual(msgs[0].cc()[0].domain,       "ietf.org")
        self.assertEqual(msgs[0].cc()[0].addr_spec,    "cfrg-chairs@ietf.org")
        self.assertEqual(msgs[0].cc()[1].display_name, "")
        self.assertEqual(msgs[0].cc()[1].username,     "draft-orru-zkproof-sigma-protocols")
        self.assertEqual(msgs[0].cc()[1].domain,       "ietf.org")
        self.assertEqual(msgs[0].cc()[1].addr_spec,    "draft-orru-zkproof-sigma-protocols@ietf.org")


    def test_mailarchive3_envelope_subject(self) -> None:
        msgs = self.ma.message("<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].subject(), "[CFRG] Adoption Call: Sigma Protocols")


    def test_mailarchive3_envelope_date(self) -> None:
        # The "Date:" header on this message is "Fri, 18 Apr 2025 09:30:05 +0300"
        msgs = self.ma.message("<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].date(), datetime.fromisoformat("2025-04-18T06:30:05+00:00"))


    def test_mailarchive3_envelope_header(self) -> None:
        msgs = self.ma.message("<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].header("from"),    ["\"Stanislav V. Smyshlyaev\" <smyshsv@gmail.com>"])
        self.assertEqual(msgs[0].header("subject"), ["[CFRG] Adoption Call: Sigma Protocols"])


    def test_mailarchive3_envelope_contents(self) -> None:
        msgs = self.ma.message("<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].contents().get_all("from"),    ["\"Stanislav V. Smyshlyaev\" <smyshsv@gmail.com>"])
        self.assertEqual(msgs[0].contents().get_all("subject"), ["[CFRG] Adoption Call: Sigma Protocols"])


    def test_mailarchive3_envelope_in_reply_to(self) -> None:
        msgs = self.ma.message("<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].in_reply_to(), [])

        msgs = self.ma.message("<CAMr0u6npL+TjkdVr4Jnouha6SGjQeMjiLTuRtRD7CLqWBZ2CBw@mail.gmail.com>")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(len(msgs[0].in_reply_to()), 1)
        self.assertEqual(msgs[0].in_reply_to()[0].message_id(), "<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")

        msgs = self.ma.message("<399B1F51-1C36-4F6D-B1ED-2F293707A6BF@gmail.com>")
        self.assertEqual(len(msgs), 2)                  # This message has copies to both 100attendees@ and ietf@
        self.assertEqual(len(msgs[0].in_reply_to()), 2) # ...as does the message to which it is a reply


    def test_mailarchive3_envelope_replies(self) -> None:
        msgs = self.ma.message("<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].replies()[0].message_id(), "<CAMr0u6npL+TjkdVr4Jnouha6SGjQeMjiLTuRtRD7CLqWBZ2CBw@mail.gmail.com>")
        self.assertEqual(msgs[0].replies()[1].message_id(), "<CADhumskFy4-Jsr7YC7Xd38NUJ4Nv0xTvKgivXE-U0D3k3cCMtQ@mail.gmail.com>")


    def test_mailarchive3_envelope_metadata(self) -> None:
        msg = self.ma.message("<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")[0]
        self.assertEqual(msg.get_metadata("test_mailarchive3", "testing"), None)
        msg.add_metadata("test_mailarchive3", "testing", "1... 2... 3...")
        self.assertEqual(msg.get_metadata("test_mailarchive3", "testing"), "1... 2... 3...")
        msg.clear_metadata("test_mailarchive3", "testing")
        self.assertEqual(msg.get_metadata("test_mailarchive3", "testing"), None)


    # =============================================================================================
    # Tests for the MailingList class follow:

    def test_mailarchive3_mailinglist_name(self) -> None:
        mlist = self.ma.mailing_list("100attendees")
        self.assertEqual(mlist.name(), "100attendees")


    def test_mailarchive3_mailinglist_uidvalidity(self) -> None:
        mlist = self.ma.mailing_list("100attendees")
        self.assertEqual(mlist.uidvalidity(), 1505323361)


    def test_mailarchive3_mailinglist_num_messages(self) -> None:
        mlist = self.ma.mailing_list("100attendees")
        self.assertEqual(mlist.num_messages(), 434)


    def test_mailarchive3_mailinglist_message_uids(self) -> None:
        mlist = self.ma.mailing_list("100attendees")
        uids  = list(mlist.message_uids())
        self.assertEqual(len(uids), 434)


    def test_mailarchive3_mailinglist_message(self) -> None:
        mlist = self.ma.mailing_list("cfrg")
        msg   = mlist.message(14157)
        if msg is not None:
            self.assertEqual(msg.message_id(), "<CAMr0u6mtvLBNnurVjw3rq5PmSF6okisAg5OVRzoqVvzpR7+r=A@mail.gmail.com>")
        else:
            self.fail("Cannot find message")


    def test_mailarchive3_mailinglist_messages(self) -> None:
        mlist = self.ma.mailing_list("100attendees")
        # Test all messages:
        msgs  = list(mlist.messages())
        self.assertEqual(len(msgs), 434)
        # Test messages with received before/after constraints:
        msgs  = list(mlist.messages(received_after  = "2017-10-01T00:00:00+00:00",
                                    received_before = "2017-11-01T00:00:00+00:00"))
        self.assertEqual(len(msgs), 9)


    def test_mailarchive3_mailinglist_messages_as_dataframe(self) -> None:
        mlist = self.ma.mailing_list("100attendees")
        # Test all messages:
        df = mlist.messages_as_dataframe()
        self.assertEqual(df.shape, (434, 7))

        # Test messages with received before/after constraints:
        df  = mlist.messages_as_dataframe(received_after  = "2017-10-01T00:00:00+00:00",
                                          received_before = "2017-11-01T00:00:00+00:00")
        self.assertEqual(df.shape, (9, 7))


    def test_mailarchive3_mailinglist_threads(self) -> None:
        mlist   = self.ma.mailing_list("100attendees")
        threads = mlist.threads()
        self.assertEqual(len(threads), 111)
        # Message <9B50505D-A7E7-40E0-B789-419DA14C6021@gmail.com> is copied to both the
        # 100attendees and ietf lists, so there will be two envolopes in the thread head..
        self.assertEqual(len(threads["<9B50505D-A7E7-40E0-B789-419DA14C6021@gmail.com>"]), 2)


    def test_mailarchive3_mailinglist_metadata(self) -> None:
        mlist = self.ma.mailing_list("100attendees")
        self.assertEqual(mlist.get_metadata("test_mailarchive3", "testing"), None)
        mlist.add_metadata("test_mailarchive3", "testing", "1... 2... 3...")
        self.assertEqual(mlist.get_metadata("test_mailarchive3", "testing"), "1... 2... 3...")
        mlist.clear_metadata("test_mailarchive3", "testing")
        self.assertEqual(mlist.get_metadata("test_mailarchive3", "testing"), None)


    # =============================================================================================
    # Tests for the MailArchive class follow:

    def test_mailarchive3_mailarchive_mailing_list_names(self) -> None:
        ml_names = list(self.ma.mailing_list_names())
        self.assertGreater(len(ml_names), 0)
        self.assertIn("ietf",          ml_names)
        self.assertIn("ietf-announce", ml_names)
        self.assertIn("irtf-announce", ml_names)


    def test_mailarchive3_mailarchive_mailing_list(self) -> None:
        mlist = self.ma.mailing_list("100attendees")
        self.assertEqual(mlist.name(), "100attendees")
        self.assertEqual(mlist.num_messages(), 434)


    def test_mailarchive3_mailarchive_message(self) -> None:
        # This assumes there is a local mailarchive containing data up to 2025-01-21 or later.
        msgs = self.ma.message("<0D393D01-F267-43BC-8F9C-1638B3E17EA5@csperkins.org>")
        self.assertEqual(len(msgs), 4)
        self.assertEqual(msgs[0].mailing_list().name(), "e-impact")
        self.assertEqual(msgs[0].uid(),         1591)
        self.assertEqual(msgs[0].uidvalidity(), 1674241031)
        self.assertEqual(msgs[0].subject(),     '[E-impact] Sustainability and the Internet Research Group chartered')
        self.assertEqual(msgs[0].from_(),       Address(display_name="Colin Perkins", addr_spec="csp@csperkins.org"))

        self.assertEqual(msgs[1].mailing_list().name(), "green")
        self.assertEqual(msgs[1].uid(),         159)
        self.assertEqual(msgs[1].uidvalidity(), 1728069020)
        self.assertEqual(msgs[1].subject(),     '[Green] Sustainability and the Internet Research Group chartered')
        self.assertEqual(msgs[1].from_(),       Address(display_name="Colin Perkins", addr_spec="csp@csperkins.org"))

        self.assertEqual(msgs[2].mailing_list().name(), "irtf-announce")
        self.assertEqual(msgs[2].uid(),         613)
        self.assertEqual(msgs[2].uidvalidity(), 1455297825)
        self.assertEqual(msgs[2].subject(),     '[IRTF-Announce] Sustainability and the Internet Research Group chartered')
        self.assertEqual(msgs[2].from_(),       Address(display_name="Colin Perkins", addr_spec="csp@csperkins.org"))

        self.assertEqual(msgs[3].mailing_list().name(), "irtf-discuss")
        self.assertEqual(msgs[3].uid(),         819)
        self.assertEqual(msgs[3].uidvalidity(), 1455297825)
        self.assertEqual(msgs[3].subject(),     '[irtf-discuss] Sustainability and the Internet Research Group chartered')
        self.assertEqual(msgs[3].from_(),       Address(display_name="Colin Perkins", addr_spec="csp@csperkins.org"))


    def test_mailarchive3_mailarchive_messages_from_list(self) -> None:
        # Messages from a person to specific mailing list
        msgs = list(self.ma.messages(from_addr="csp@csperkins.org", mailing_list_name="sip"))
        self.assertEqual(len(msgs), 8)
        self.assertEqual(msgs[0].subject(), "[Sip] Review request: draft-ietf-mmusic-connection-precon-00.txt")
        self.assertEqual(msgs[1].subject(), "Re: [Sip] SDP Query")
        self.assertEqual(msgs[2].subject(), "Re: [Sip] SDP Query")
        self.assertEqual(msgs[3].subject(), "Re: [Sip] Changing SSRC/sequence numbers during a call")
        self.assertEqual(msgs[4].subject(), "[Sip] Progressing ICE")
        self.assertEqual(msgs[5].subject(), "Re: [Sip] SIP IPv6 ABNF: Essential correction to RFC3261")
        self.assertEqual(msgs[6].subject(), "Re: [Sip] SIP IPv6 ABNF: Essential correction to RFC3261")
        self.assertEqual(msgs[7].subject(), "Re: [Sip] Maximum allowed value of Clock rate in SDP ???")


    def test_mailarchive3_mailarchive_messages_from_to(self) -> None:
        # Messages between two people, irrespective of mailing list
        msgs = list(self.ma.messages(from_addr="csp@csperkins.org", to_addr="ladan@isi.edu"))
        self.assertEqual(len(msgs), 3)
        self.assertEqual(msgs[0].subject(),             "Re: [AVT] Header formats for RTP profile for TFRC")
        self.assertEqual(msgs[0].mailing_list().name(), "avt")
        self.assertEqual(msgs[0].uid(),                 4969)
        self.assertEqual(msgs[0].uidvalidity(),         1455297825)

        self.assertEqual(msgs[1].subject(),             "Re: [AVT] I-D ACTION:draft-ietf-avt-tfrc-profile-06.txt")
        self.assertEqual(msgs[1].mailing_list().name(), "avt")
        self.assertEqual(msgs[1].uid(),                 6312)
        self.assertEqual(msgs[1].uidvalidity(),         1455297825)

        self.assertEqual(msgs[2].subject(),             "Re: [AVT] I-D ACTION:draft-ietf-avt-tfrc-profile-09.txt")
        self.assertEqual(msgs[2].mailing_list().name(), "avt")
        self.assertEqual(msgs[2].uid(),                 7549)
        self.assertEqual(msgs[2].uidvalidity(),         1455297825)


    def test_mailarchive3_mailarchive_messages_subject(self) -> None:
        # Messages with a particular subject
        msgs = list(self.ma.messages(subject="Secdir last call review of draft-ietf-anima-brski-cloud-11"))
        self.assertEqual(len(msgs), 3)
        self.assertEqual(msgs[0].subject(),             "[Anima] Secdir last call review of draft-ietf-anima-brski-cloud-11")
        self.assertEqual(msgs[0].mailing_list().name(), "anima")
        self.assertEqual(msgs[0].uid(),                 7522)
        self.assertEqual(msgs[0].uidvalidity(),         1455297825)

        self.assertEqual(msgs[1].subject(),             "[Last-Call] Secdir last call review of draft-ietf-anima-brski-cloud-11")
        self.assertEqual(msgs[1].mailing_list().name(), "last-call")
        self.assertEqual(msgs[1].uid(),                 12409)
        self.assertEqual(msgs[1].uidvalidity(),         1571671002)

        self.assertEqual(msgs[2].subject(),             "[secdir] Secdir last call review of draft-ietf-anima-brski-cloud-11")
        self.assertEqual(msgs[2].mailing_list().name(), "secdir")
        self.assertEqual(msgs[2].uid(),                 12606)
        self.assertEqual(msgs[2].uidvalidity(),         1455297825)

        # This should find three messages sent to ietf@ietf.org with dates:
        #   1994-11-07T14:06:35+00:00
        #   1994-11-07T16:16:39+00:00
        #   1994-11-10T01:47:30+00:00
        msgs = list(self.ma.messages(subject="Chair's contest for an IETF Logo"))
        self.assertEqual(len(msgs), 3)


if __name__ == '__main__':
    unittest.main()

# =================================================================================================================================
# vim: set tw=0 ai:
