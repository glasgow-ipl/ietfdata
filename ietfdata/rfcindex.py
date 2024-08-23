# Copyright (C) 2017-2020 University of Glasgow
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

from typing   import NewType, Iterator, List, Optional, Tuple, Dict
from datetime import datetime, timedelta
from pathlib  import Path

import xml.etree.ElementTree as ET
import requests
import unittest
import os
import logging

# ==================================================================================================

DocID = NewType('DocID', str)

class RfcEntry:
    """
    An RFC entry in the rfc-index.xml file. No attempt is made to
    normalise the data included here.
    """
    doc_id       : DocID                # DocumentID (e.g., "RFC8700")
    title        : str
    authors      : List[str]
    doi          : str
    stream       : str
    wg           : Optional[str]        # For IETF stream RFCs, the working group
    area         : Optional[str]        # For IETF stream RFCs, the area
    publ_status  : str                  # The RFC status when published
    curr_status  : str                  # The RFC status now
    day          : Optional[int]        # The publication day; only recorded for 1 April RFCs
    month        : str                  # The publication month (e.g., "December")
    year         : int                  # The publication year
    formats      : List[str]
    draft        : Optional[str]        # The Internet-draft that became this RFC
    keywords     : List[str]
    updates      : List[DocID]
    updated_by   : List[DocID]
    obsoletes    : List[DocID]
    obsoleted_by : List[DocID]
    is_also      : List[DocID]
    see_also     : List[DocID]
    errata_url   : Optional[str]
    abstract     : Optional[ET.Element] # The abstract, as formatted XML
    page_count   : int


    def __init__(self, rfc_element: ET.Element) -> None:
        self.wg           = None
        self.area         = None
        self.day          = None
        self.errata_url   = None
        self.abstract     = None
        self.draft        = None
        self.authors      = []
        self.keywords     = []
        self.updates      = []
        self.updated_by   = []
        self.obsoletes    = []
        self.obsoleted_by = []
        self.is_also      = []
        self.see_also     = []
        self.formats      = []

        for elem in rfc_element:
            if   elem.tag == "{https://www.rfc-editor.org/rfc-index}doc-id":
                assert elem.text is not None
                self.doc_id = DocID(elem.text)
            elif elem.tag == "{https://www.rfc-editor.org/rfc-index}title":
                assert elem.text is not None
                self.title  = elem.text
            elif elem.tag == "{https://www.rfc-editor.org/rfc-index}doi":
                assert elem.text is not None
                self.doi = elem.text
            elif elem.tag == "{https://www.rfc-editor.org/rfc-index}stream":
                assert elem.text is not None
                self.stream = elem.text
            elif elem.tag == "{https://www.rfc-editor.org/rfc-index}wg_acronym":
                self.wg = elem.text
            elif elem.tag == "{https://www.rfc-editor.org/rfc-index}area":
                self.area = elem.text
            elif elem.tag == "{https://www.rfc-editor.org/rfc-index}current-status":
                assert elem.text is not None
                self.curr_status = elem.text
            elif elem.tag == "{https://www.rfc-editor.org/rfc-index}publication-status":
                assert elem.text is not None
                self.publ_status = elem.text
            elif elem.tag == "{https://www.rfc-editor.org/rfc-index}author":
                for inner in elem:
                    if   inner.tag == "{https://www.rfc-editor.org/rfc-index}name":
                        assert inner.text is not None
                        self.authors.append(inner.text)
                    elif inner.tag == "{https://www.rfc-editor.org/rfc-index}title":
                        # Ignore <title>...</title> within <author>...</author> tags
                        # (this is normally just "Editor", which isn't useful)
                        pass 
                    else:
                        raise NotImplementedError
            elif elem.tag == "{https://www.rfc-editor.org/rfc-index}date":
                for inner in elem:
                    assert inner.text is not None
                    if   inner.tag == "{https://www.rfc-editor.org/rfc-index}day":
                        # <day>...</day> is only included for 1 April RFCs
                        self.day = int(inner.text)
                    elif inner.tag == "{https://www.rfc-editor.org/rfc-index}month":
                        self.month = inner.text
                    elif inner.tag == "{https://www.rfc-editor.org/rfc-index}year":
                        self.year = int(inner.text)
                    else:
                        raise NotImplementedError
            elif elem.tag == "{https://www.rfc-editor.org/rfc-index}format":
                for inner in elem:
                    assert inner.text is not None
                    if   inner.tag == "{https://www.rfc-editor.org/rfc-index}file-format":
                        self.formats.append(inner.text)
                    else:
                        raise NotImplementedError
            elif elem.tag == "{https://www.rfc-editor.org/rfc-index}draft":
                if elem.text == "rfc4049bis":
                    # RFC 6019 is RFC 4049 republished as a Proposed Standard RF. 
                    # with virtually no change. It was never published as a draft,
                    # but the index lists "rfc4049bis" as its draft name. Replace
                    # this with the name of the draft that became RFC 4049.
                    self.draft = "draft-housley-binarytime-02"
                elif elem.text == "draft-luckie-recn":
                    self.draft = None
                else:
                    self.draft = elem.text
            elif elem.tag == "{https://www.rfc-editor.org/rfc-index}keywords":
                for inner in elem:
                    if   inner.tag == "{https://www.rfc-editor.org/rfc-index}kw":
                        # Omit empty <kw></kw> 
                        if inner.text is not None:
                            self.keywords.append(inner.text)
                    else:
                        raise NotImplementedError
            elif elem.tag == "{https://www.rfc-editor.org/rfc-index}updates":
                for inner in elem:
                    assert inner.text is not None
                    if   inner.tag == "{https://www.rfc-editor.org/rfc-index}doc-id":
                        self.updates.append(DocID(inner.text))
                    else:
                        raise NotImplementedError
            elif elem.tag == "{https://www.rfc-editor.org/rfc-index}updated-by":
                for inner in elem:
                    assert inner.text is not None
                    if   inner.tag == "{https://www.rfc-editor.org/rfc-index}doc-id":
                        self.updated_by.append(DocID(inner.text))
                    else:
                        raise NotImplementedError
            elif elem.tag == "{https://www.rfc-editor.org/rfc-index}obsoletes":
                for inner in elem:
                    assert inner.text is not None
                    if   inner.tag == "{https://www.rfc-editor.org/rfc-index}doc-id":
                        self.obsoletes.append(DocID(inner.text))
                    else:
                        raise NotImplementedError
            elif elem.tag == "{https://www.rfc-editor.org/rfc-index}obsoleted-by":
                for inner in elem:
                    assert inner.text is not None
                    if   inner.tag == "{https://www.rfc-editor.org/rfc-index}doc-id":
                        self.obsoleted_by.append(DocID(inner.text))
                    else:
                        raise NotImplementedError
            elif elem.tag == "{https://www.rfc-editor.org/rfc-index}is-also":
                for inner in elem:
                    assert inner.text is not None
                    if   inner.tag == "{https://www.rfc-editor.org/rfc-index}doc-id":
                        self.is_also.append(DocID(inner.text))
                    else:
                        raise NotImplementedError
            elif elem.tag == "{https://www.rfc-editor.org/rfc-index}see-also":
                for inner in elem:
                    assert inner.text is not None
                    if   inner.tag == "{https://www.rfc-editor.org/rfc-index}doc-id":
                        self.see_also.append(DocID(inner.text))
                    else:
                        raise NotImplementedError
            elif elem.tag == "{https://www.rfc-editor.org/rfc-index}errata-url":
                self.errata_url = elem.text
            elif elem.tag == "{https://www.rfc-editor.org/rfc-index}abstract":
                # The <abstract>...</abstract> contains formatted XML, most
                # typically a sequence of <p>...</p> tags.
                self.abstract = elem
            elif elem.tag == "{https://www.rfc-editor.org/rfc-index}page-count":
                assert elem.text is not None
                self.page_count = int(elem.text)
            else:
                print("Unknown tag: " + elem.tag)
                raise NotImplementedError


    def __str__(self) -> str:
        return "RFC {\n" \
             + "      doc_id: " + self.doc_id            + "\n" \
             + "       title: " + self.title             + "\n" \
             + "     authors: " + str(self.authors)      + "\n" \
             + "         doi: " + self.doi               + "\n" \
             + "      stream: " + self.stream            + "\n" \
             + "          wg: " + str(self.wg)           + "\n" \
             + "        area: " + str(self.area)         + "\n" \
             + " curr_status: " + self.curr_status       + "\n" \
             + " publ_status: " + self.publ_status       + "\n" \
             + "         day: " + str(self.day)          + "\n" \
             + "       month: " + self.month             + "\n" \
             + "        year: " + str(self.year)         + "\n" \
             + "     formats: " + str(self.formats)      + "\n" \
             + "       draft: " + str(self.draft)        + "\n" \
             + "    keywords: " + str(self.keywords)     + "\n" \
             + "     updates: " + str(self.updates)      + "\n" \
             + "  updated_by: " + str(self.updated_by)   + "\n" \
             + "   obsoletes: " + str(self.obsoletes)    + "\n" \
             + "obsoleted_by: " + str(self.obsoleted_by) + "\n" \
             + "     is_also: " + str(self.is_also)      + "\n" \
             + "    see_also: " + str(self.see_also)     + "\n" \
             + "  errata_url: " + str(self.errata_url)   + "\n" \
             + "    abstract: " + str(self.abstract)     + "\n" \
             + "}\n"


    def charset(self) -> str:
        """
        Most RFCs are UTF-8, or it's ASCII subset. A few are not. Return
        an appropriate encoding for the text of this RFC.
        """
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
        elif (self.doc_id == "RFC2497") or (self.doc_id == "RFC2557"):
            return "iso8859_1"
        elif self.doc_id == "RFC2708":
            # This RFC is corrupt: line 521 has a byte with value 0xC6 that
            # is clearly intended to be a ' character, but that code point
            # doesn't correspond to ' in any character set I can find. Use
            # ISO 8859-1 which gets all characters right apart from this.
            #
            # According to Greg Skinner: "regarding the test in line 268
            # for RFC2708, as far as I can tell, U+0092 was introduced in
            # draft-ietf-printmib-job-protomap-01 in multiple places. In -02,
            # it was replaced with U+0027 everywhere except section 5.0.
            # Somehow, that stray character became the corrupt text you
            # identified."
            # (https://github.com/glasgow-ipl/ietfdata/issues/137)
            return "iso8859_1"
        elif self.doc_id == "RFC2875":
            # Both the text and PDF versions of this document have corrupt
            # characters (lines 754 and 926 of the text version). Using 
            # ISO 8859-1 is no more corrupt than the original.
            return "iso8859_1"
        else:
            return "utf-8"


    def content_url(self, required_format: str) -> Optional[str]:
        rfcnum = "rfc" + self.doc_id[3:].lstrip("0")
        for fmt in self.formats:
            if fmt == required_format:
                if required_format in [ "ASCII", "TEXT"] :
                    return "https://www.rfc-editor.org/rfc/" + rfcnum + ".txt"
                elif required_format == "PS":
                    return "https://www.rfc-editor.org/rfc/" + rfcnum + ".ps"
                elif required_format == "PDF":
                    return "https://www.rfc-editor.org/rfc/" + rfcnum + ".pdf"
                elif required_format == "HTML":
                    return "https://www.rfc-editor.org/rfc/" + rfcnum + ".html"
                elif required_format == "XML":
                    return "https://www.rfc-editor.org/rfc/" + rfcnum + ".xml"
                else:
                    return None
        return None


    def date(self) -> datetime:
        if self.day != None:
            date = "{} {} {}".format(self.day, self.month, self.year)
            return datetime.strptime(date, "%d %B %Y")
        else:
            date = "{} {}".format(self.month, self.year)
            return datetime.strptime(date, "%B %Y")



# ==================================================================================================

class RfcNotIssuedEntry:
    """
      An RFC that was not issued in the rfc-index.xml file.
    """
    doc_id : DocID


    def __init__(self, rfc_not_issued_element: ET.Element) -> None:
        for elem in rfc_not_issued_element:
            if   elem.tag == "{https://www.rfc-editor.org/rfc-index}doc-id":
                assert elem.text is not None
                self.doc_id = DocID(elem.text)
            else:
                raise NotImplementedError


    def __str__(self) -> str:
        return "RFC-Not-Issued {\n" \
             + "      doc_id: " + self.doc_id + "\n" \
             + "}\n"


# ==================================================================================================

class BcpEntry:
    """
      A BCP entry in the rfc-index.xml file.
    """
    doc_id  : DocID
    is_also : List[DocID]


    def __init__(self, bcp_element: ET.Element) -> None:
        self.is_also = []

        for elem in bcp_element:
            if   elem.tag == "{https://www.rfc-editor.org/rfc-index}doc-id":
                assert elem.text is not None
                self.doc_id = DocID(elem.text)
            elif elem.tag == "{https://www.rfc-editor.org/rfc-index}is-also":
                for inner in elem:
                    assert inner.text is not None
                    if   inner.tag == "{https://www.rfc-editor.org/rfc-index}doc-id":
                        self.is_also.append(DocID(inner.text))
                    else:
                        raise NotImplementedError
            else:
                raise NotImplementedError


    def __str__(self) -> str:
        return "BCP {\n" \
             + "      doc_id: " + self.doc_id        + "\n" \
             + "     is_also: " + str(self.is_also)  + "\n" \
             + "}\n"


# ==================================================================================================

class StdEntry:
    """
      An STD entry in the rfc-index.xml file.
    """
    doc_id  : DocID
    title   : str
    is_also : List[DocID]


    def __init__(self, std_element: ET.Element) -> None:
        self.is_also = []

        for elem in std_element:
            assert elem.text is not None
            if   elem.tag == "{https://www.rfc-editor.org/rfc-index}doc-id":
                self.doc_id = DocID(elem.text)
            elif elem.tag == "{https://www.rfc-editor.org/rfc-index}title":
                self.title  = elem.text
            elif elem.tag == "{https://www.rfc-editor.org/rfc-index}is-also":
                for inner in elem:
                    assert inner.text is not None
                    if   inner.tag == "{https://www.rfc-editor.org/rfc-index}doc-id":
                        self.is_also.append(DocID(inner.text))
                    else:
                        raise NotImplementedError
            else:
                raise NotImplementedError


    def __str__(self) -> str:
        return "STD {\n" \
             + "      doc_id: " + self.doc_id       + "\n" \
             + "       title: " + self.title        + "\n" \
             + "     is_also: " + str(self.is_also) + "\n" \
             + "}\n"

# ==================================================================================================

class FyiEntry:
    """
      A FYI entry in the rfc-index.xml file.
    """
    doc_id   : DocID
    is_also  : List[DocID]


    def __init__(self, fyi_element: ET.Element) -> None:
        self.is_also = []

        for elem in fyi_element:
            assert elem.text is not None
            if   elem.tag == "{https://www.rfc-editor.org/rfc-index}doc-id":
                self.doc_id = DocID(elem.text)
            elif elem.tag == "{https://www.rfc-editor.org/rfc-index}is-also":
                for inner in elem:
                    assert inner.text is not None
                    if   inner.tag == "{https://www.rfc-editor.org/rfc-index}doc-id":
                        self.is_also.append(DocID(inner.text))
                    else:
                        raise NotImplementedError
            else:
                raise NotImplementedError


    def __str__(self) -> str:
        return "FYI {\n" \
             + "      doc_id: " + self.doc_id       + "\n" \
             + "     is_also: " + str(self.is_also) + "\n" \
             + "}\n"


# ==================================================================================================

class RFCIndex:
    """
    The RFC Index.
    """
    _rfc            : Dict[str, RfcEntry]
    _rfc_not_issued : Dict[str, RfcNotIssuedEntry]
    _bcp            : Dict[str, BcpEntry]
    _std            : Dict[str, StdEntry]
    _fyi            : Dict[str, FyiEntry]


    def _download_index(self) -> Optional[str]:
        with requests.Session() as session:
            response = session.get("https://www.rfc-editor.org/rfc-index.xml", verify=True)
            if response.status_code == 200:
                return response.text
            else:
                return None


    def _is_cached(self, cache_filepath : Path) -> bool:
        if cache_filepath.exists():
            curr_time = datetime.now()
            prev_time = datetime.fromtimestamp(cache_filepath.stat().st_mtime)
            if curr_time < prev_time + timedelta(days = 1):
                return True
        return False


    def _retrieve_index(self, rfc_index) -> Optional[str]:
        if rfc_index is not None:
            with open(rfc_index, "r") as xml_file:
                return xml_file.read()

        if self.cache_dir is not None:
            cache_filepath = Path(self.cache_dir, "rfc", "rfc-index.xml")
            if self._is_cached(cache_filepath):
                with open(cache_filepath, "r") as cache_file:
                    return cache_file.read()
            else:
                response = self._download_index()
                if response is not None:
                    cache_filepath.parent.mkdir(parents=True, exist_ok=True)
                    with open(cache_filepath, "w") as cache_file:
                        cache_file.write(response)
                        return response
                else:
                    return None
        else:
            return self._download_index()


    def __init__(self, cache_dir: Optional[str] = None, rfc_index: Optional[str] = None):
        """
        Parameters:
            cache_dir -- If set, use this directory as a cache
        """
        logging.getLogger('requests').setLevel('ERROR')
        logging.getLogger('requests_cache').setLevel('ERROR')
        logging.getLogger("urllib3").setLevel('ERROR')

        logging.basicConfig(level=os.getenv("IETFDATA_LOGLEVEL", default="INFO"))
        self.log = logging.getLogger("rfcindex")

        self.cache_dir       = os.getenv("IETFDATA_CACHEDIR", default=cache_dir)
        self._rfc            = {}
        self._rfc_not_issued = {}
        self._bcp            = {}
        self._std            = {}
        self._fyi            = {}

        self.log.warning(f"cache enabled: dir={self.cache_dir}")

        xml = self._retrieve_index(rfc_index)
        if xml is None:
            raise RuntimeError

        for doc in ET.fromstring(xml):
            if   doc.tag == "{https://www.rfc-editor.org/rfc-index}rfc-entry":
                rfc = RfcEntry(doc)
                self._rfc[rfc.doc_id] = rfc
            elif doc.tag == "{https://www.rfc-editor.org/rfc-index}rfc-not-issued-entry":
                rne = RfcNotIssuedEntry(doc)
                self._rfc_not_issued[rne.doc_id] = rne
            elif doc.tag == "{https://www.rfc-editor.org/rfc-index}bcp-entry":
                bcp = BcpEntry(doc)
                self._bcp[bcp.doc_id] = bcp
            elif doc.tag == "{https://www.rfc-editor.org/rfc-index}std-entry":
                std = StdEntry(doc)
                self._std[std.doc_id] = std
            elif doc.tag == "{https://www.rfc-editor.org/rfc-index}fyi-entry":
                fyi = FyiEntry(doc)
                self._fyi[fyi.doc_id] = fyi
            else:
                print(f"Unexpected doc.tag: {doc.tag}")
                raise NotImplementedError


    def rfc(self, rfc_id: str) -> Optional[RfcEntry]:
        return self._rfc[rfc_id]


    def rfc_not_issued(self, rfc_id: str) -> Optional[RfcNotIssuedEntry]:
        return self._rfc_not_issued[rfc_id]


    def bcp(self, bcp_id: str) -> Optional[BcpEntry]:
        return self._bcp[bcp_id]


    def fyi(self, fyi_id: str) -> Optional[FyiEntry]:
        return self._fyi[fyi_id]


    def std(self, std_id: str) -> Optional[StdEntry]:
        return self._std[std_id]


    def rfcs(self,
            since:  str = "1969-01",  # The first RFCs were published in 1969
            until:  str = "2038-01",
            stream: Optional[str] = None,
            area:   Optional[str] = None,
            wg:     Optional[str] = None,
            status: Optional[str] = None) -> Iterator[RfcEntry]:
        for rfc_id in self._rfc:
            rfc = self._rfc[rfc_id]
            if stream is not None and rfc.stream != stream:
                continue
            if area   is not None and rfc.area   != area:
                continue
            if wg     is not None and rfc.wg     != wg:
                continue
            if status is not None and rfc.curr_status != status:
                continue
            if rfc.date() < datetime.strptime(since, "%Y-%m"):
                continue
            if rfc.date() > datetime.strptime(until, "%Y-%m"):
                continue
            yield(rfc)


# ==================================================================================================
