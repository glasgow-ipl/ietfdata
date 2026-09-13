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
import logging
import requests
import time
import sys

from bs4                 import BeautifulSoup
from datetime            import datetime
from email.message       import EmailMessage
from pathlib             import Path
from typing              import Any, Dict
from ietfdata.ma_backend import *

class MailArchiveBackendW3C(MailArchiveBackend):
    def __init__(self):
        self._log    = logging.getLogger("ietfdata")
        self.session = requests.Session()
        self.delay   = 0.33
        self.mailbox = None


    def _find_indexes(self, list_url):
        indexes = []
        time.sleep(self.delay)
        resp = self.session.get(list_url)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            main = soup.find("main")
            for tbody in main.find_all("tbody"):
                for period in tbody.find_all("td", class_="cell_period"):
                    period_date = period.text
                    period_url  = list_url + period.a["href"]
                    period_path = period.a["href"]
                    item = {"period": period_date, "url": period_url, "path": period_path}
                    indexes.append(item)
        else:
            print(f"ERROR: {resp.status_code} {list_url}")
        return indexes


    def _find_messages(self, index_url):
        messages = []
        time.sleep(self.delay)
        resp = self.session.get(index_url)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            main = soup.find("main", class_="messages-list")
            date = None
            for item in main.children:
                if item.name == "h2":
                    try:
                        date = datetime.strptime(item.text.strip(), "%A, %d %B %Y").date()
                    except:
                        print(f"Cannot parse date: {item.text.strip()}")
                        date = None
                elif item.name == "ul":
                    for msg in item.find_all("li"):
                        msg_uri = resp.url + msg.a["href"]
                        msg_uid = msg.a["id"]
                        subject = msg.a.text
                        sender  = msg.span.text
                        result = {"uid": msg_uid, "date": date, "url": msg_uri, "subject": subject, "sender": sender}
                        messages.append(result)
                elif item.name == "p":
                    pass
                elif item.name is None:
                    pass
                else:
                    print(f"eeror [{item}]")
                    sys.exit()
            return messages
        else:
            print(f"ERROR: {resp.status_code} {index_url}")


    def _fetch_message(self, msg_url, base_url):
        time.sleep(self.delay)
        resp = self.session.get(msg_url)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            main = soup.find("main", class_="mail")

            headers = main.find("ul", class_="headers")
            hdr_subject = "Subject: " + soup.find("h1").text.strip()
            hdr_date    = headers.find("span", class_ = "date")
            hdr_from    = headers.find("span", class_ = "from")
            hdr_to      = headers.find("span", class_ = "to")
            hdr_cc      = headers.find("span", class_ = "cc")
            hdr_msg_id  = headers.find("span", class_ = "message-id")

            msg_body = main.find("pre", class_ = "body")

            attach_list = []
            attachments = main.find("section", class_ = "message-body-part attachment-links")
            if attachments is not None:
                for attach in attachments.find_all("li"):
                    parts = attach.text.split()
                    if parts[1] == "attachment:":
                        if len(parts) == 3 and parts[2] == "stored":
                            attach_type = parts[0]
                            attach_disp = "inline"
                        else:
                            attach_type = parts[0]
                            attach_disp = "attach"
                    else:
                        print(f"ERROR: can't parse attachment")
                        print(attach)
                        sys.exit()
                    attach_path = attach.find("a")["href"]
                    attach_url  = base_url + attach_path
                    attachment = {"media_type"  : attach_type,
                                  "url"         : attach_url,
                                  "path"        : attach_path,
                                  "disposition" : attach_disp}
                    attach_list.append(attachment)


            footer = soup.find("footer")
            in_reply_to = None
            for fitem in footer.find_all("li"):
                fheader = fitem.find("span", class_="heading")
                if fheader is not None:
                    if fheader.text.strip() == "In reply to" or fheader.text.strip() == "Maybe in reply to":
                        anchor = fitem.find("a")
                        if anchor.text == "Message archived in another list or period":
                            in_reply_to = anchor["href"]
                        else:
                            in_reply_to = base_url + anchor["href"]


            item = {"msg_url"      : msg_url,
                    "subject"      : hdr_subject,
                    "date"         : hdr_date.text.strip()    if hdr_date   is not None else None,
                    "from"         : hdr_from.text.strip()    if hdr_from   is not None else None,
                    "to"           : hdr_to.text.strip()      if hdr_to     is not None else None,
                    "cc"           : hdr_cc.text.strip()      if hdr_cc     is not None else None,
                    "message-id"   : hdr_msg_id.text.strip()  if hdr_msg_id is not None else None,
                    "body"         : msg_body.text.strip()    if msg_body   is not None else None,
                    "reply_to_url" : in_reply_to,
                    "attachments"  : attach_list}
            return item
        else:
            print(f"ERROR: {resp.status_code} {msg_url}")


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
        self.mailbox  = mailbox
        self.msg_urls = {}
        self.base_url = {}

        tmp_msg_urls = {}
        tmp_base_url = {}
        count = 0
        list_url = f"https://lists.w3.org/Archives/Public/{self.mailbox}/"
        for index in self._find_indexes(list_url):
            self._log.warning(f"messages_ids {index['url']}")
            for msg_to_fetch in self._find_messages(index["url"]):
                tmp_msg_urls[count] = msg_to_fetch['url']
                tmp_base_url[count] = index['url']
                count += 1
        # Messages on the server are stored in reverse chronological order,
        # reverse the ids so we retrieve them in date order.
        for i in range(0, count):
            self.msg_urls[count - i] = tmp_msg_urls[i]
            self.base_url[count - i] = tmp_base_url[i]


    def close_mailbox(self) -> None:
        self.mailbox  = None
        self.msg_urls = {}
        self.base_url = {}


    def validity(self) -> int:
        return 0


    def message_ids(self) -> List[int]:
        return list(self.msg_urls.keys())


    def fetch(self, message_ids: List[int]) -> Iterator[Tuple[int, bytes]]:
        msg_id_for_url = {}

        for uid in message_ids:
            msg_url  = self.msg_urls[uid]
            base_url = self.base_url[uid]

            item = self._fetch_message(msg_url, base_url)

            print(f"{uid:5} {item['subject']}")

            if item["message-id"] is not None:
                msg_id_for_url[msg_url] = item["message-id"]

            email_msg = ""
            if item["from"] is not None:
                email_msg += f"{item['from']}\r\n"
            if item["to"] is not None:
                email_msg += f"{item['to']}\r\n"
            if item["cc"] is not None:
                email_msg += f"{item['cc']}\r\n"
            if item["subject"] is not None:
                email_msg += f"{item['subject']}\r\n"
            if item["date"] is not None:
                email_msg += f"{item['date']}\r\n"
            if item["message-id"] is not None:
                email_msg += f"{item['message-id']}\r\n"
            if item['reply_to_url'] is not None:
                if item['reply_to_url'] in msg_id_for_url:
                    email_msg += f"In-Reply-To: {msg_id_for_url[item['reply_to_url']][12:]}\r\n"
                else:
                    print("Missing in-reply-to")
            email_msg += "\r\n"
            if item["body"] is not None:
                email_msg += item["body"]

            # FIXME: handle attachments

            yield uid, bytes(email_msg, encoding="utf-8")

