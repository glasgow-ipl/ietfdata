
import requests
import time
import xml.etree.ElementTree as ET

# ==================================================================================================

class RfcEntry:
    """
      An RFC entry in the rfc-index.xml file. No attempt is made to
      normalise the data included here.

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
    """
    def __init__(self, rfc_element):
        self.wg           = None
        self.area         = None
        self.authors      = []
        self.day          = None
        self.errata_url   = None
        self.abstract     = None
        self.draft        = None
        self.keywords     = []
        self.updates      = []
        self.updated_by   = []
        self.obsoletes    = []
        self.obsoleted_by = []
        self.is_also      = []
        self.see_also     = []
        self.formats      = []

        for elem in rfc_element:
            if   elem.tag == "{http://www.rfc-editor.org/rfc-index}doc-id":
                self.doc_id = elem.text
            elif elem.tag == "{http://www.rfc-editor.org/rfc-index}title":
                self.title  = elem.text
            elif elem.tag == "{http://www.rfc-editor.org/rfc-index}doi":
                self.doi = elem.text
            elif elem.tag == "{http://www.rfc-editor.org/rfc-index}stream":
                self.stream = elem.text
            elif elem.tag == "{http://www.rfc-editor.org/rfc-index}wg_acronym":
                self.wg = elem.text
            elif elem.tag == "{http://www.rfc-editor.org/rfc-index}area":
                self.area = elem.text
            elif elem.tag == "{http://www.rfc-editor.org/rfc-index}current-status":
                self.curr_status = elem.text
            elif elem.tag == "{http://www.rfc-editor.org/rfc-index}publication-status":
                self.publ_status = elem.text
            elif elem.tag == "{http://www.rfc-editor.org/rfc-index}author":
                for inner in elem:
                    if   inner.tag == "{http://www.rfc-editor.org/rfc-index}name":
                        self.authors.append(inner.text)
                    elif inner.tag == "{http://www.rfc-editor.org/rfc-index}title":
                        # Ignore <title>...</title> within <author>...</author> tags
                        # (this is normally just "Editor", which isn't useful)
                        pass 
                    else:
                        raise NotImplementedError
            elif elem.tag == "{http://www.rfc-editor.org/rfc-index}date":
                for inner in elem:
                    if   inner.tag == "{http://www.rfc-editor.org/rfc-index}day":
                        # <day>...</day> is only included for 1 April RFCs
                        self.day = int(inner.text)
                    elif inner.tag == "{http://www.rfc-editor.org/rfc-index}month":
                        self.month = inner.text
                    elif inner.tag == "{http://www.rfc-editor.org/rfc-index}year":
                        self.year = int(inner.text)
                    else:
                        raise NotImplementedError
            elif elem.tag == "{http://www.rfc-editor.org/rfc-index}format":
                # Not all formats have pages, and some of those that do don't have a page count
                page_count = None

                for inner in elem:
                    if   inner.tag == "{http://www.rfc-editor.org/rfc-index}file-format":
                        file_format = inner.text
                    elif inner.tag == "{http://www.rfc-editor.org/rfc-index}char-count":
                        char_count = inner.text
                    elif inner.tag == "{http://www.rfc-editor.org/rfc-index}page-count":
                        page_count = inner.text
                    else:
                        raise NotImplementedError
                self.formats.append((file_format, char_count, page_count))
            elif elem.tag == "{http://www.rfc-editor.org/rfc-index}draft":
                self.draft = elem.text
            elif elem.tag == "{http://www.rfc-editor.org/rfc-index}keywords":
                for inner in elem:
                    if   inner.tag == "{http://www.rfc-editor.org/rfc-index}kw":
                        # Omit empty <kw></kw> 
                        if inner.text != None:
                            self.keywords.append(inner.text)
                    else:
                        raise NotImplementedError
            elif elem.tag == "{http://www.rfc-editor.org/rfc-index}updates":
                for inner in elem:
                    if   inner.tag == "{http://www.rfc-editor.org/rfc-index}doc-id":
                        self.updates.append(inner.text)
                    else:
                        raise NotImplementedError
            elif elem.tag == "{http://www.rfc-editor.org/rfc-index}updated-by":
                for inner in elem:
                    if   inner.tag == "{http://www.rfc-editor.org/rfc-index}doc-id":
                        self.updated_by.append(inner.text)
                    else:
                        raise NotImplementedError
            elif elem.tag == "{http://www.rfc-editor.org/rfc-index}obsoletes":
                for inner in elem:
                    if   inner.tag == "{http://www.rfc-editor.org/rfc-index}doc-id":
                        self.obsoletes.append(inner.text)
                    else:
                        raise NotImplementedError
            elif elem.tag == "{http://www.rfc-editor.org/rfc-index}obsoleted-by":
                for inner in elem:
                    if   inner.tag == "{http://www.rfc-editor.org/rfc-index}doc-id":
                        self.obsoleted_by.append(inner.text)
                    else:
                        raise NotImplementedError
            elif elem.tag == "{http://www.rfc-editor.org/rfc-index}is-also":
                for inner in elem:
                    if   inner.tag == "{http://www.rfc-editor.org/rfc-index}doc-id":
                        self.is_also.append(inner.text)
                    else:
                        raise NotImplementedError
            elif elem.tag == "{http://www.rfc-editor.org/rfc-index}see-also":
                for inner in elem:
                    if   inner.tag == "{http://www.rfc-editor.org/rfc-index}doc-id":
                        self.see_also.append(inner.text)
                    else:
                        raise NotImplementedError
            elif elem.tag == "{http://www.rfc-editor.org/rfc-index}errata-url":
                self.errata_url = elem.text
            elif elem.tag == "{http://www.rfc-editor.org/rfc-index}abstract":
                # The <abstract>...</abstract> contains formatted XML
                self.abstract = elem
            else:
                raise NotImplementedError

    def __str__(self):
        repr =        "RFC {\n"
        repr = repr + "      doc_id : " + self.doc_id      + "\n"
        repr = repr + "      title  : " + self.title       + "\n"
        for author in self.authors:
            repr = repr + "      author : " + author       + "\n"
        repr = repr + "         doi : " + self.doi         + "\n"
        repr = repr + "      stream : " + self.stream      + "\n"
        repr = repr + "          wg : " + str(self.wg)     + "\n" 
        repr = repr + "        area : " + str(self.area)   + "\n" 
        repr = repr + " curr_status : " + self.curr_status + "\n"
        repr = repr + " publ_status : " + self.publ_status + "\n"
        repr = repr + "         day : " + str(self.day)    + "\n"
        repr = repr + "       month : " + self.month       + "\n"
        repr = repr + "        year : " + str(self.year)   + "\n"
        for (file_format, char_count, page_count) in self.formats:
            repr = repr + "      format : " + file_format + " " + char_count + " " + str(page_count)  + "\n"
        repr = repr + "       draft : " + str(self.draft)  + "\n"
        for kwd in self.keywords:
            repr = repr + "    keywords : " + kwd  + "\n"
        for doc in self.updates:
            repr = repr + "     updates : " + doc  + "\n"
        for doc in self.updated_by:
            repr = repr + "  updated_by : " + doc  + "\n"
        for doc in self.obsoletes:
            repr = repr + "   obsoletes : " + doc  + "\n"
        for doc in self.obsoleted_by:
            repr = repr + "obsoleted_by : " + doc  + "\n"
        for doc in self.is_also:
            repr = repr + "     is_also : " + doc  + "\n"
        for doc in self.see_also:
            repr = repr + "    see_also : " + doc  + "\n"
        repr = repr + "  errata_url : " + str(self.errata_url)  + "\n"
        repr = repr + "    abstract : " + str(self.abstract)    + "\n"
        repr = repr + "}\n"
        return repr

# ==================================================================================================

class RfcNotIssuedEntry:
    """
      An RFC that was not issued in the rfc-index.xml file.

      Attributes:
        doc_id       : String, e.g., "RFC3550"
    """
    def __init__(self, rfc_not_issued_element):
        for elem in rfc_not_issued_element:
            if   elem.tag == "{http://www.rfc-editor.org/rfc-index}doc-id":
                self.doc_id = elem.text
            else:
                raise NotImplementedError

    def __str__(self):
        repr =        "RFC-Not-Issued {\n"
        repr = repr + "      doc_id : " + self.doc_id + "\n"
        repr = repr + "}\n"
        return repr

# ==================================================================================================

class BcpEntry:
    """
      A BCP entry in the rfc-index.xml file.

      Attributes:
        doc_id       : String, e.g., "RFC3550"
        is_also      : List of strings
    """
    def __init__(self, bcp_element):
        self.is_also = []

        for elem in bcp_element:
            if   elem.tag == "{http://www.rfc-editor.org/rfc-index}doc-id":
                self.doc_id = elem.text
            elif elem.tag == "{http://www.rfc-editor.org/rfc-index}is-also":
                for inner in elem:
                    if   inner.tag == "{http://www.rfc-editor.org/rfc-index}doc-id":
                        self.is_also.append(inner.text)
                    else:
                        raise NotImplementedError
            else:
                raise NotImplementedError

    def __str__(self):
        repr =        "BCP {\n"
        repr = repr + "      doc_id : " + self.doc_id + "\n"
        for doc in self.is_also:
            repr = repr + "     is_also : " + doc  + "\n"
        repr = repr + "}\n"
        return repr

# ==================================================================================================

class StdEntry:
    """
      An STD entry in the rfc-index.xml file.

      Attributes:
        doc_id       : String, e.g., "RFC3550"
        title        : String
        is_also      : List of strings
    """
    def __init__(self, std_element):
        self.is_also = []

        for elem in std_element:
            if   elem.tag == "{http://www.rfc-editor.org/rfc-index}doc-id":
                self.doc_id = elem.text
            elif elem.tag == "{http://www.rfc-editor.org/rfc-index}title":
                self.title  = elem.text
            elif elem.tag == "{http://www.rfc-editor.org/rfc-index}is-also":
                for inner in elem:
                    if   inner.tag == "{http://www.rfc-editor.org/rfc-index}doc-id":
                        self.is_also.append(inner.text)
                    else:
                        raise NotImplementedError
            else:
                raise NotImplementedError

    def __str__(self):
        repr =        "STD {\n"
        repr = repr + "      doc_id : " + self.doc_id + "\n"
        repr = repr + "       title : " + self.title  + "\n"
        for doc in self.is_also:
            repr = repr + "     is_also : " + doc  + "\n"
        repr = repr + "}\n"
        return repr

# ==================================================================================================

class FyiEntry:
    """
      A FYI entry in the rfc-index.xml file.

      Attributes:
        doc_id       : String, e.g., "RFC3550"
        is_also      : List of strings
    """
    def __init__(self, fyi_element):
        self.is_also = []

        for elem in fyi_element:
            if   elem.tag == "{http://www.rfc-editor.org/rfc-index}doc-id":
                self.doc_id = elem.text
            elif elem.tag == "{http://www.rfc-editor.org/rfc-index}is-also":
                for inner in elem:
                    if   inner.tag == "{http://www.rfc-editor.org/rfc-index}doc-id":
                        self.is_also.append(inner.text)
                    else:
                        raise NotImplementedError
            else:
                print(elem.tag)
                raise NotImplementedError

    def __str__(self):
        repr =        "FYI {\n"
        repr = repr + "      doc_id : " + self.doc_id + "\n"
        for doc in self.is_also:
            repr = repr + "     is_also : " + doc  + "\n"
        repr = repr + "}\n"
        return repr

# ==================================================================================================

class RFCIndex:
    """
    The RFC Index.

    Attributes:
        xml             : An ElementTree representing the parsed XML of the index
        rfcs            : List of RfcEntry
        rfcs_not_issued : List of RfcNotIssuedEntry
        bcps            : List of BcpEntry
        stds            : List of StdEntry
        fyis            : List of FyiEntry
    """
    def __init__(self, indexfile):
        self.xml = ET.parse(indexfile)

        self.rfcs = []
        self.rfcs_not_issued = []
        self.bcps = []
        self.stds = []
        self.fyis = []

        for doc in self.xml.getroot():
            if   doc.tag == "{http://www.rfc-editor.org/rfc-index}rfc-entry":
                self.rfcs.append(RfcEntry(doc))
            elif doc.tag == "{http://www.rfc-editor.org/rfc-index}rfc-not-issued-entry":
                self.rfcs_not_issued.append(RfcNotIssuedEntry(doc))
            elif doc.tag == "{http://www.rfc-editor.org/rfc-index}bcp-entry":
                self.bcps.append(BcpEntry(doc))
            elif doc.tag == "{http://www.rfc-editor.org/rfc-index}std-entry":
                self.stds.append(StdEntry(doc))
            elif doc.tag == "{http://www.rfc-editor.org/rfc-index}fyi-entry":
                self.fyis.append(FyiEntry(doc))
            else:
                print("unknown tag:", doc.tag)

# ==================================================================================================

