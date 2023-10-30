# Copyright (C) 2020-2022 University of Glasgow
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
from mailarchive2 import *
from tqdm import tqdm

# SPAM
def is_spam(m: Envelope) -> bool:
    return m.get_metadata("spam", "decision")

# SEGMENTATION 

class EmailSegment:
    def __init__(self):
        self.type = "unknown"
        self.content = ""
        self.antecedent = None
        self.id = None
        
    def from_params(i, text, ctype, a):
        c = EmailSegment()
        c.id = i
        c.content = text
        c.type = ctype
        c.antecedent = a
        return c

    def __str__(self):
        return "*** TYPE OF SEGMENT: %s **** \n\n %s \n ************************************** " % (self.type, self.content)
 
    def __repr__(self):
        return "*** TYPE OF SEGMENT: %s **** \n\n %s \n ************************************** " % (self.type, self.content)

def get_segmentation(m : Envelope) -> list[EmailSegment]:
    pass #TODO


# PSEUDOLABELS

def get_DA_pseudolabels(m: Envelope) -> dict[str,list[float]]:
    pass #TODO

def get_possible_DA_labels():
    return [] # TODO


# SIGNATURES

def get_signature(m: Envelope) -> str:
    pass #TODO


# some TESTS
if __name__ == "__main__": # testing code
        ma = MailArchive(mongodb_username = "admin", mongodb_password = "DzKvurBMsKtAEOQ9s9r")

        g = ma.messages()
        m1 = next(g)
        m1.clear_metadata("spam")

        # try  the API a bit for the 

        # add single
        try:
            m1.add_metadata("spam","sa_score", 0.21)
            m1.add_metadata("spam","decision", True)
            print("Add single OK!")
        except Exception as e:
            print(e)
            print("Add single FAIL!")

        # fetch by messagea

        try:
            sc = m1.get_metadata("spam","sa_score")
            assert sc - 0.21 <= 0.000001
            print("Fetch single directly OK!")
        except Exception as e:
            print(e)
            print("Fetch single directly FAIL!")


        try:
            dec = is_spam(m1)
            assert dec == True
            print("Fetch through is_spam function OK!")
        except Exception as e :
            print(e)
            print("Fetch through is_spam function FAIL!")


        m1.clear_metadata("spam")
        try:
            dec2 = is_spam(m1)
            print("Clearing FAIL!")
        except: 
            print("Clearing OK!") # it is supposed to raise an error because the metadata is cleared
        

        # testing the thread roots code (for crashing at least)
        thread_roots = list(m1._mailing_list.threads())
        messages = list(m1._mailing_list.messages())
        num_roots = len(thread_roots)
        num_messages = len(messages)
        print("Mailing list of m1 has %d messages, out of which %d are roots." % (num_messages, num_roots))

        # testing the functions that generate in_reply_to and replies data        
        num_processed, num_irt, num_rep = 0, 0, 0
        for list_name in tqdm(list(ma.mailing_list_names())[0:50], desc = "Processing mailing lists "):
            # print("Working on " + list_name)
            ml = ma.mailing_list(list_name)
            if ml:
                for msg in ml.messages():
                    try:
                        irt = list(msg.in_reply_to())
                        num_irt += 1
                    except Exception as e:
                        pass
                    try:
                        rep = list(msg.replies())
                        num_rep += 1 
                    except Exception as e:
                        print(e)
                        pass
                    num_processed += 1
        print("In reply to success rate: %d / %d (%.3f)" % (num_irt, num_processed, num_irt / num_processed))
        print("Replies success rate: %d / %d (%.3f)" % (num_rep, num_processed, num_rep / num_processed))
        print("Done!")
        

        

        
        








