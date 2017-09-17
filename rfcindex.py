
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
        # We explicitly set all attributes that are optional in the XML 
        # to None, or to an empty list, so code using this doesn't need 
        # worry about missing attributes.
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
                        char_count = int(inner.text)
                    elif inner.tag == "{http://www.rfc-editor.org/rfc-index}page-count":
                        page_count = int(inner.text)
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
        return "RFC-Not-Issued {\n" \
             + "      doc_id: " + self.doc_id + "\n" \
             + "}\n"

# ==================================================================================================

class BcpEntry:
    """
      A BCP entry in the rfc-index.xml file.

      Attributes:
        doc_id       : String, e.g., "BCP002"
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
        return "BCP {\n" \
             + "      doc_id: " + self.doc_id        + "\n" \
             + "     is_also: " + str(self.is_also)  + "\n" \
             + "}\n"

# ==================================================================================================

class StdEntry:
    """
      An STD entry in the rfc-index.xml file.

      Attributes:
        doc_id       : String, e.g., "STD0089"
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
        return "STD {\n" \
             + "      doc_id: " + self.doc_id       + "\n" \
             + "       title: " + self.title        + "\n" \
             + "     is_also: " + str(self.is_also) + "\n" \
             + "}\n"

# ==================================================================================================

class FyiEntry:
    """
      A FYI entry in the rfc-index.xml file.

      Attributes:
        doc_id       : String, e.g., "FYI0038"
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
                raise NotImplementedError

    def __str__(self):
        return "FYI {\n" \
             + "      doc_id: " + self.doc_id       + "\n" \
             + "     is_also: " + str(self.is_also) + "\n" \
             + "}\n"

# ==================================================================================================

class RFCIndex:
    """
    The RFC Index.

    Attributes:
        rfc            : Dictionary of RfcEntry
        rfc_not_issued : Dictionary of RfcNotIssuedEntry
        bcp            : Dictionary of BcpEntry
        std            : Dictionary of StdEntry
        fyi            : Dictionary of FyiEntry
    """
    def __init__(self, indexfile):
        self.rfc            = {}
        self.rfc_not_issued = {}
        self.bcp            = {}
        self.std            = {}
        self.fyi            = {}

        for doc in ET.parse(indexfile).getroot():
            if   doc.tag == "{http://www.rfc-editor.org/rfc-index}rfc-entry":
                val = RfcEntry(doc)
                self.rfc[val.doc_id] = val
            elif doc.tag == "{http://www.rfc-editor.org/rfc-index}rfc-not-issued-entry":
                val = RfcNotIssuedEntry(doc)
                self.rfc_not_issued[val.doc_id] = val
            elif doc.tag == "{http://www.rfc-editor.org/rfc-index}bcp-entry":
                val = BcpEntry(doc)
                self.bcp[val.doc_id] = val
            elif doc.tag == "{http://www.rfc-editor.org/rfc-index}std-entry":
                val = StdEntry(doc)
                self.std[val.doc_id] = val
            elif doc.tag == "{http://www.rfc-editor.org/rfc-index}fyi-entry":
                val = FyiEntry(doc)
                self.fyi[val.doc_id] = val
            else:
                raise NotImplementedError

# ==================================================================================================

