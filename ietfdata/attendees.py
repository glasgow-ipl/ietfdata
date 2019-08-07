# Copyright (C) 2019 University of Glasgow
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
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
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

import requests
import unittest

class Attendees:
    meeting: int

    def __init__(self, meeting: int):
        self.session = requests.Session()
        self.meeting = meeting

        if meeting >= 72:
            url = "https://www.ietf.org/registration/ietf{}//attendance.py".format(meeting)
            response = self.session.get(url, verify=True)
            if response.status_code == 200:
                print(response)
            else:
                raise RuntimeError
        elif meeting >= 61 and meeting < 72:
            for i in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]:
                url = "https://www.ietf.org/proceedings/{}/att{}.html".format(meeting, i)
                response = self.session.get(url, verify=True)
                if response.status_code == 200:
                    print(response.text)
                else:
                    raise RuntimeError
        elif meeting >= 53 and meeting < 61:
            for i in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]:
                url = "https://www.ietf.org/proceedings/{}/atts{}.html".format(meeting, i)
                response = self.session.get(url, verify=True)
                if response.status_code == 200:
                    print(response.text)
                else:
                    raise RuntimeError
        elif meeting == 52:
            url = "https://www.ietf.org/proceedings/52/atts.txt"
            response = self.session.get(url, verify=True)
            if response.status_code == 200:
                print(response.text)
            else:
                raise RuntimeError
        elif meeting == 51:
            url = "https://www.ietf.org/proceedings/51/atts51.txt"
            response = self.session.get(url, verify=True)
            if response.status_code == 200:
                print(response.text)
            else:
                raise RuntimeError
        elif meeting == 50:
            url = "https://www.ietf.org/proceedings/50/attachments/atts50.txt"
            response = self.session.get(url, verify=True)
            if response.status_code == 200:
                print(response.text)
            else:
                raise RuntimeError
        elif meeting == 49:
            url = "https://www.ietf.org/49/attachments/attendees.txt"
            response = self.session.get(url, verify=True)
            if response.status_code == 200:
                print(response.text)
            else:
                raise RuntimeError
        else:
            raise RuntimeError

# 48 https://www.ietf.org/proceedings/48/attachments/48ietf-attendees.txt
# 47 https://www.ietf.org/proceedings/47/attachments/47ietf-attendees.txt
# 46 https://www.ietf.org/proceedings/46/attachments/attendees-list-99nov.txt
# 45 https://www.ietf.org/proceedings/45/attachments/attendees-list-99jul.txt
# 44 https://www.ietf.org/proceedings/44/attachments/attendees-list-99mar.txt
# 43 https://www.ietf.org/proceedings/43/attachments/attendees-list-98dec.txt
# 42 https://www.ietf.org/proceedings/42/attendees/98aug-attendees.txt
# 41 https://www.ietf.org/proceedings/41/attendees/la-attendees.txt
# 40 https://www.ietf.org/proceedings/40/attendees/attendees-97dec.txt
# 39 https://www.ietf.org/proceedings/39/attendees-97aug.txt
# 38 https://www.ietf.org/proceedings/38/97apr-final/attendees.txt
# 37 attendee lists per WG only?
# 36 https://www.ietf.org/proceedings/36/report/att96jun.txt
# 35 ftp://ftp.ietf.org/ietf-online-proceedings/96mar/att96mar.txt
# 34 ftp://ftp.ietf.org/ietf-online-proceedings/95dec/Attendees
# 33 ftp://ftp.ietf.org/ietf-online-proceedings/95jul/att95jul.txt
# 32 ftp://ftp.ietf.org/ietf-online-proceedings/95apr/att95apr.txt
# 31 ftp://ftp.ietf.org/ietf-online-proceedings/94dec/att94dec.txt
# 30 ftp://ftp.ietf.org/ietf-online-proceedings/94jul/att94jul.txt 
# 29 ftp://ftp.ietf.org/ietf-online-proceedings/94mar/attendees.txt
# 28 ftp://ftp.ietf.org/ietf-online-proceedings/93nov/attendees.txt
# For IETF 27 and older, the proceedings only appear to be available as PDF files

# =================================================================================================
# Unit tests:

class TestAttendees(unittest.TestCase):
    def test_105(self):
        a = Attendees(105)

    def test_70(self):
        a = Attendees(70)

    def test_55(self):
        a = Attendees(70)

    def test_52(self):
        a = Attendees(70)

    def test_51(self):
        a = Attendees(70)

    def test_49(self):
        a = Attendees(70)

if __name__ == '__main__':
    unittest.main()

# =================================================================================================
# vim: set tw=0 ai:
