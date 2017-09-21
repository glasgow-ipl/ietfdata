# Copyright (C) 2017 University of Glasgow
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

from pathlib  import Path

import re
import requests

def fetch_rfc(num, extn):
    """
    A helper function to fetch an RFC. 
    """
    url = "https://www.rfc-editor.org/rfc/rfc" + num + extn
    loc = Path("data/rfc/rfc" + num + extn)

    if not loc.exists():
        print("[fetch]", url, "->", loc)
        response = requests.get(url)
        if response.status_code != 200:
            print("  Failed: ", response.status_code)
            return None
        else:
            with open(loc, "wb") as f:
                f.write(response.content)
    return loc

def is_authors_address_header(line):
    if   re.compile("^( *Appendix)? *(([A-Z]|([0-9]+(\\.[0-9]+)?))([:\\.]?))? *Author('|s|'s|s')? +(and Contributor('|s|'s|s') +)?[Aa]dd?ress(es)?:? *$").match(line) != None:
        return True
    elif re.compile("^( *Appendix)? *(([A-Z]|([0-9]+(\\.[0-9]+)?))([:\\.]?))? *Editor('|s|'s|s')? +(and [Cc]ontributor('|s|'s|s') +)?[Aa]dd?ress(es)?:? *$").match(line) != None:
        return True
    elif re.compile("^( *Appendix)? *(([A-Z]|([0-9]+(\\.[0-9]+)?))([:\\.]?))? *(Author|Editor)('|s|'s|s')? +[Ii]nformation( and [Aa]cknowledgments)?:? *$").match(line) != None:
        return True
    elif re.compile("^( *Appendix)? *(([A-Z]|([0-9]+(\\.[0-9]+)?))([:\\.]?))? *((Author|Editor)('|s|'s|s')? +)?([Cc]ontact +)?[Aa]ddress(es)?:? *$").match(line) != None:
        return True
    elif re.compile("^( *Appendix)? *(([A-Z]|([0-9]+(\\.[0-9]+)?))([:\\.]?))? *((Author|Editor)('|s|'s|s')? +)?([Cc]ontact +)?[Ii]nformation:? *$").match(line) != None:
        return True
    elif re.compile("^( *Appendix)? *(([A-Z]|([0-9]+(\\.[0-9]+)?))([:\\.]?))? *(Author|Editor)('|s|'s|s')?:? *$").match(line) != None:
        return True
    elif re.compile("^( *Appendix)? *(([A-Z]|([0-9]+(\\.[0-9]+)?))([:\\.]?))? *Author('|s|'s|s')? and Editor('|s|'s|s')? [Aa]ddress(es)?:? *$").match(line) != None:
        return True
    elif re.compile("^( *Appendix)? *(([A-Z]|([0-9]+(\\.[0-9]+)?))([:\\.]?))? *-? +(Author|Editor)('|s|'s|s')? [Aa]ddress(es)?( and [Cc]ontacts)?:? *$").match(line) != None:
        return True
    elif re.compile("^( *Appendix)? *(([A-Z]|([0-9]+(\\.[0-9]+)?))([:\\.]?))? *[Cc]omplete [Ll]ist of (Author|Editor)('|s|'s|s')( Addresses)? *$").match(line) != None:
        return True
    elif re.compile("^( *Appendix)? *(([A-Z]|([0-9]+(\\.[0-9]+)?))([:\\.]?))? *(AUTHOR|EDITOR)('|S|'S|S')? ADDRESS(ES)?:? *$").match(line) != None:
        return True
    elif re.compile("^( *Appendix)? *(([A-Z]|([0-9]+(\\.[0-9]+)?))([:\\.]?))? *Addresses of (the )?(Author|Editor)('|s|'s|s')?( and( +[a-zA-Z0-9]+)? (Working Group )?Chairs?)? *$").match(line) != None:
        return True
    elif re.compile("^( *Appendix)? *(([A-Z]|([0-9]+(\\.[0-9]+)?))([:\\.]?))? *(Author|Editor)('|s|'s|s')? (and (Working Group )?Chair('|s|'s|s')?( Address(es)?)?)? *$").match(line) != None:
        return True
    elif re.compile("^( *Appendix)? *(([A-Z]|([0-9]+(\\.[0-9]+)?))([:\\.]?))? *Contact Information and useful links *$").match(line) != None:
        return True
    elif re.compile("^Authors \\(volunteer EF Design Team members\\) *$").match(line) != None:
        return True
    elif re.compile("^Contacts$").match(line) != None:
        return True
    elif re.compile("^CONTACT$").match(line) != None:
        return True
    elif re.compile("^Addresses$").match(line) != None:
        return true
    elif re.compile("^XV. AUTHOR'S ADDRESS$").match(line) != None:
        return True
    else:
        return False

class RFC:
    """
    A class to represent an RFC. 

    Attributes:
        doc_id       : String, e.g., "RFC3550"
        title        : String
        authors      : List of strings 
        doi          : String
        stream       : String
        wg           : None or string
        area         : None or string
        curr_status  : String
        publ_status  : String
        day          : None or integer
        month        : String holding the month name
        year         : Integer
        format       : List of tuples (file format, char count, page count)
        draft        : None or string
        keywords     : List of strings
        updates      : List of strings
        updated_by   : List of strings
        obsoletes    : List of strings
        obsoleted_by : List of strings
        is_also      : List of strings
        see_also     : List of strings
        errata_url   : None or string
        abstract     : None or Element
        file_txt     : None or Path of the RFC in .txt format
        file_pdf     : None or Path of the RFC in .pdf format
        file_ps      : None or Path of the RFC in .ps  format
    """

    def __init__(self, rfc_index_entry):
        # Fill in information from rfc-index.xml:
        self.doc_id       = rfc_index_entry.doc_id
        self.title        = rfc_index_entry.title
        self.author_names = rfc_index_entry.authors
        self.doi          = rfc_index_entry.doi
        self.stream       = rfc_index_entry.stream
        self.wg           = rfc_index_entry.wg
        self.area         = rfc_index_entry.area
        self.curr_status  = rfc_index_entry.curr_status
        self.publ_status  = rfc_index_entry.publ_status
        self.day          = rfc_index_entry.day
        self.month        = rfc_index_entry.month
        self.year         = rfc_index_entry.year
        self.formats      = rfc_index_entry.formats
        self.draft        = rfc_index_entry.draft
        self.keywords     = rfc_index_entry.keywords
        self.updates      = rfc_index_entry.updates
        self.updated_by   = rfc_index_entry.updated_by
        self.obsoletes    = rfc_index_entry.obsoletes
        self.obsoleted_by = rfc_index_entry.obsoleted_by
        self.is_also      = rfc_index_entry.is_also
        self.see_also     = rfc_index_entry.see_also
        self.errata_url   = rfc_index_entry.errata_url
        self.abstract     = rfc_index_entry.abstract
        self.file_txt     = None
        self.file_pdf     = None
        self.file_ps      = None

        # Fetch the RFC files:
        for (file_format, char_count, page_count) in self.formats:
            num = str(int(self.doc_id[3:]))
            if   file_format == "ASCII":
                self.file_txt = fetch_rfc(num, ".txt")
            elif file_format == "PDF":
                self.file_pdf = fetch_rfc(num, ".pdf")
            elif file_format == "PS":
                self.file_ps  = fetch_rfc(num, ".ps")
            else:
                raise NotImplementedError

    def file_txt_encoding(self):
        # Most RFCs are UTF-8, or it's ASCII subset. A few are not. Return
        # an appropriate encoding for the text of this RFC.
        if   (self.doc_id == "RFC0064") or (self.doc_id == "RFC0101") or \
             (self.doc_id == "RFC0177") or (self.doc_id == "RFC0178") or \
             (self.doc_id == "RFC0182") or (self.doc_id == "RFC0227") or \
             (self.doc_id == "RFC0234") or (self.doc_id == "RFC0235") or \
             (self.doc_id == "RFC0237") or (self.doc_id == "RFC0243") or \
             (self.doc_id == "RFC0270") or (self.doc_id == "RFC0282") or \
             (self.doc_id == "RFC0288") or (self.doc_id == "RFC0290") or \
             (self.doc_id == "RFC0292") or (self.doc_id == "RFC0303") or \
             (self.doc_id == "RFC0306") or (self.doc_id == "RFC0307") or \
             (self.doc_id == "RFC0310") or (self.doc_id == "RFC0313") or \
             (self.doc_id == "RFC0315") or (self.doc_id == "RFC0316") or \
             (self.doc_id == "RFC0317") or (self.doc_id == "RFC0323") or \
             (self.doc_id == "RFC0327") or (self.doc_id == "RFC0367") or \
             (self.doc_id == "RFC0369") or (self.doc_id == "RFC0441") or \
             (self.doc_id == "RFC1305"):
            return "iso8859_1"
        elif self.doc_id == "RFC2166":
            return "windows-1252"
        elif (self.doc_id == "RFC2497") or (self.doc_id == "RFC2497") or \
             (self.doc_id == "RFC2557"):
            return "iso8859_1"
        elif self.doc_id == "RFC2708":
            # This RFC is corrupt: line 521 has a byte with value 0xC6 that
            # is clearly intended to be a ' character, but that code point
            # doesn't correspond to ' in any character set I can find. Use
            # ISO 8859-1 which gets all characters right apart from this.
            return "iso8859_1"
        elif self.doc_id == "RFC2875":
            # Both the text and PDF versions of this document have corrupt
            # characters (lines 754 and 926 of the text version). Using 
            # ISO 8859-1 is no more corrupt than the original.
            return "iso8859_1"
        else:
            return "utf-8"

    def authors(self): 
        if self.file_txt == None:
            return None

        authors = []
        with open(self.file_txt, encoding=self.file_txt_encoding()) as inf:
            while True:
                line = inf.readline()
                if is_authors_address_header(line):
                    break
                if line == "":
                    # Reached end of file without finding an "Authors' Address" line
                    return None

            authors.append(line)
        return authors


