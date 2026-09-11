# Copyright (C) 2026 University of Glasgow
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

import json
import requests
import time
import sys

from bs4                 import BeautifulSoup
from datetime            import datetime
from pathlib             import Path
from typing              import Any, Dict
from ietfdata.ma_backend import *

class MailArchiveBackendW3C(MailArchiveBackend):

    def __init__(self):
        self.session = requests.Session()
        self.delay   = 0.33


    def db_prefix(self) -> str:
        return "w3c"


    def mailboxes(self) -> List[str]:
        mailing_lists = []
        time.sleep(self.delay)
        resp = self.session.get("https://lists.w3.org/Archives/Public/")
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            list_groups = soup.find_all("ul", class_="clean-list lol")
            for lists in list_groups:
                for ml in lists.find_all("li"):
                    if ml.h3:
                        name = ml.h3.text
                        mailing_lists.append(name)
            return mailing_lists
        else:
            print(f"ERROR: {resp.status_code}")
            sys.exit()


    def open_mailbox(self, mailbox: str) -> None:
        # https://lists.w3.org/Archives/Public/xml-dist-app/
        print(f"open_mailbox {mailbox}")
        pass


    def close_mailbox(self) -> None:
        print("close_mailbox")
        pass


    def validity(self) -> int:
        print("validity")
        return 0


    def message_ids(self) -> List[int]:
        print("message_ids")
        return []


    def fetch(self, message_ids: List[int]) -> Iterator[Tuple[int, bytes]]:
        print(f"fetch {message_ids}")
        for i, b in [(0, bytes())]:
            yield (i, b)


