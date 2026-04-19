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

import logging
import re

from datetime                 import date, datetime, timezone, UTC
from email.header             import decode_header
from email.headerregistry     import Address
from email.parser             import BytesHeaderParser
from email.policy             import EmailPolicy
from email.utils              import parseaddr, parsedate_to_datetime, getaddresses, unquote
from typing                   import Any, Dict, Optional, Tuple

class EmailPolicyCustom(EmailPolicy):
    def __init__(self, **kw):
        super().__init__(**kw)


    def header_source_parse(self, sourcelines):
        log = logging.getLogger("ietfdata")
        name, value = sourcelines[0].split(':', 1)
        value = ''.join((value, *sourcelines[1:])).lstrip(' \t\r\n')
        value = value.rstrip('\r\n')

        if name.lower() == "to" or name.lower() == "cc":
            # Many messages sent to ietf-announce have malformed "To:" and "Cc:" headers,
            # some of which are so corrupt that they make the Python email package throw
            # an exception ('Group' object has no attribute 'local_part').  Rewrite such
            # headers to use the canonical ietf-announce@ietf.org list address.
            value = value.replace("\r\n", " ")
            patterns_to_replace = [
                (r'("IETF-Announce:; ; ; ; ; @tis.com"@tis.com[; ]+ , )(.*)', r'ietf-announce@ietf.org, \2'),
                (r'(.*)(IETF-Announce:[ ;,]+[a-zA-Z\.@:;-]+$)', r'\1ietf-announce@ietf.org'),
                (r'(.*)(IETF-Announce:(; )+[; a-z\.@\r\n]+)',   r'\1ietf-announce@ietf.org'),
                (r'(.*)(<"?IETF-Announce:"?)([a-z0-9\.@;"]+)?(>)(, @tislabs.com@tislabs.com)?(.*)',  r'\1<ietf-announce@ietf.org>\6'),
                (r'IETF-Announce: ;, tis.com@CNRI.Reston.VA.US, tis.com@magellan.tis.com',           r'ietf-announce@ietf.org'),
                (r'IETF-Announce: ;, "localhost.MIT.EDU": cclark@ietf.org;',                         r'ietf-announce@ietf.org'),
                (r'IETF-Announce: @IETF.CNRI.Reston.VA.US:;, IETF.CNRI.Reston.VA.US@isi.edu',        r'ietf-announce@ietf.org'),
                (r'IETF-Announce <IETF-Announce:@auemlsrv.firewall.lucent.com;>',                    r'ietf-announce@ietf.org'),
                (r'IETF-Announce: ;,  "CNRI.Reston.VA.US" <@sun.com:CNRI.Reston.VA.US@eng.sun.com>', r'ietf-announce@ietf.org'),
                (r'IETF-Announce: ;,  "neptune.tis.com" <@tis.com, @baynetworks.com:neptune.tis.com@baynetworks.com>, tis.com@tis.com', r'ietf-announce@ietf.org'),
                (r'IETF-Announce: "IETF-Announce:;@IETF.CNRI.Reston.VA.US@PacBell.COM" <>;,  IETF.CNRI.Reston.VA.US@pacbell.com', r'ietf-announce@ietf.org'),
                (r'IETF-Announce: %IETF.CNRI.Reston.VA.US@tgv.com;',  r'ietf-announce@ietf.org'),
                (r'(IETF-Announce: ; ; ; , )(@pa.dec.com[ ;,]+)+',    r'ietf-announce@ietf.org'), 
                (r'IETF-Announce:;;;@gis.net;',              r'ietf-announce@ietf.org'),
                (r'IETF-Announce:;;@gis.net',                r'ietf-announce@ietf.org'),
                (r'IETF-Announce:@ietf.org, ;;;@ietf.org;',  r'ietf-announce@ietf.org'),
                (r'IETF-Announce:@cisco.com, ";"@cisco.com', r'ietf-announce@ietf.org'),
                (r'IETF-Announce:, ";"@cisco.com',           r'ietf-announce@ietf.org'),
                (r'IETF-Announce:@cisco.com',                r'ietf-announce@ietf.org'),
                (r'"IETF-Announce:"@netcentrex.net',         r'ietf-announce@ietf.org'),
                (r'IETF-Announce:@above.proper.com',         r'ietf-announce@ietf.org'),
                (r'IETF-Announce:all-ietf@ietf.org',         r'ietf-announce@ietf.org'),
                (r'i IETF-Announce: ;',                      r'ietf-announce@ietf.org'),
                (r'IETF-Announce: ;',                        r'ietf-announce@ietf.org'),
                (r'IETF-Announce:;',                         r'ietf-announce@ietf.org'),
                (r'IETF-Announce:',                          r'ietf-announce@ietf.org'),
                (r'^IETF-Announce$',                         r'ietf-announce@ietf.org'),
                # Rewrite variants of "undisclosed-recipients; ;" into a consistent form:
                (r'("?[Uu]ndisclosed.recipients"?: ;+)(, @[a-z\.]+)?(.*)',                        r'undisclosed-recipients: ;\3'),
                (r'(.*)(unlisted-recipients:; \(no To-header on input\))(.*)',                    r'\1undisclosed-recipients: ;\3'),
                (r'(.*)(random-recipients:;;;@cs.utk.edu; \(info-mime and ietf-822 lists\))(.*)', r'\1undisclosed-recipients: ;\3'),
                (r'(.*)("[A-Za-z\.]+":;+@tislabs.com;;;)(.*)',                                    r'\1undisclosed-recipients: ;\3'),
                (r'undisclosed-recipients:;;:;',                                                  r'undisclosed-recipients: ;'),
                # Rewrite MIME encoded headers that decode to values containing \r\n
                (r'=\?ISO-8859-1\?B\?QWJhcmJhbmVsLA0KICAgIEJlbmphbWlu\?=',  r'Benjamin Abarbanel'),
                (r'=\?ISO-8859-15\?B\?V2lqbmVuLA0KICAgIEJlcnQgKEJlcnQp\?=', r'Bert Wijnen'),
                (r'=\?ISO-8859-15\?B\?UGV0ZXJzb24sDQogICAgSm9u\?=',         r'Jon Peterson'),
                # Rewrite other problematic headers:
                (r'(moore@cs.utk.edu)?(, )?(authors:;+@cs.utk.edu;+)(.*)',  r'\1\4'),
                (r'(RFC 3023 authors: ;)',                                  r'mmurata@trl.ibm.co.jp, simonstl@simonstl.com, dan@dankohn.com'),
                (r'=\?gb2312\?q\?=D1=F9_<1@21cn.com>\?=',                   r'1@21cn.com'),
                (r'(.*Denny Vrande)(.*)(<denny.vrandecic@wikimedia.de>.*)', r'\1 \3'),
                (r'(.*)("Martin J. =\?utf-8\?Q\?D=C3=BCrst"\?=)(.*)',       r'\1Martin J. Dürst\3'),
            ]
            for (pattern, replacement) in patterns_to_replace:
                new_value = re.sub(pattern, replacement, value)
                if new_value != value:
                    try:
                        log.debug(f"header_source_parse: rewrite {name}: {value} -> {new_value}")
                    except:
                        log.debug(f"header_source_parse: rewrite {name}: ?unprintable? -> {new_value}")
                    value = new_value
            value = value.rstrip(",")

        if name.lower() == "from":
            # There are also some messages with unparsable "From:" headers that need to
            # be written into something that Python can handle:
            value = value.replace("\r\n", " ")
            patterns_to_replace = [
                (r'(.D. J. Bernstein.)(.*)(@cr.yp.to>)', r'\1 <djb@cr.yp.to>'),
            ]
            for (pattern, replacement) in patterns_to_replace:
                new_value = re.sub(pattern, replacement, value)
                new_value = new_value.rstrip(",")
                if new_value != value:
                    try:
                        log.debug(f"header_source_parse: rewrite {name}: {value} -> {new_value}")
                    except:
                        log.debug(f"header_source_parse: rewrite {name}: ?unprintable? -> {new_value}")
                    value = new_value
                    break

        return (name, value)


def _fixup_from_addr_0at(from_name:str, from_addr:str):
    # Fix From: header when the from_addr does not conain an @
    if " at " in from_addr:
        repl_addr = from_addr.replace(" at ", "@")
        print(f"_fixup_from_addr_0at: rewrite From: \"{from_addr}\" -> \"{repl_addr}\"")
        return from_name, repl_addr

    if from_name == "":
        print(f"_fixup_from_addr_0at: returned \"{from_addr}\" as name with no address")
        return from_addr, None
    else:
        print(f"_fixup_from_addr_0at: cannot rewrite From: \"{from_addr}\"")
        return from_name, from_addr


def _fixup_from_addr_1at(from_name:str, from_addr:str):
    # Fix From: header when the from_addr contains one @ sign
    patterns = [(r'(.*)( <)([^ ]+)( \()(.*)(\))', r'\5', r'\3'), # e.g., Spencer Dawkins <spencer@mcsr-labs.org (Spencer Dawkins)
                (r'(.*)( on behalf of )(.*)',     r'\3', r'\1'), # e.g., netext-bounces@mail.mobileip.jp on behalf of Domagoj Premec
                (r'(")([^"]+ [^"]+)("@)([A-Za-z0-9\.]+)', r'\2', None), # e.g., "Paul Barajas"@core3.amsl.com
                ]
    for pattern, name_sub, addr_sub in patterns:
        if re.fullmatch(pattern, from_addr):
            repl_name = re.sub(pattern, name_sub, from_addr)
            if addr_sub is not None:
                repl_addr = re.sub(pattern, addr_sub, from_addr)
            else:
                repl_addr = ""
            print(f"_fixup_from_addr_1at: rewrite [{from_name}] [{from_addr}] -> [{repl_name}] [{repl_addr}]")
            return repl_name, repl_addr

    return from_name, from_addr


def _fixup_from_addr_2at(from_name:str, from_addr:str):
    # Fix From: header when the from_addr contains two @ signs
    replacements = [('"CN=David Hemsath/OU=Endicott/O=IBM@IBMLMS01"@US.IBM.COM',        'hemsath@us.ibm.com'),
                    ('"IAOC Chair <bob.hinden@gmail.com>"@core3.amsl.com',              'bob.hinden@gmail.com'),
                    ('"Jürgen Schönwälder <j.schoenwaelder@jac"@ietfa.amsl.com',        'j.schoenwaelder@jacobs-university.de'),
                    ('"maruyama@IBMUS"@US.IBM.COM',                                     'maruyama@us.ibm.com'),
                    ('"maz1@miavx1.muohio.edu"@stream.mcs.muohio.edu',                  'maz1@miavx1.muohio.edu'),
                    ('"Michael Tüxen <tuexen@fh-muenster.de>"@ietfa.amsl.com',          'tuexen@fh-muenster.de'),
                    ('"postmaster@africaonline.co.ci"@pop1.africaonline.co.ci',         'postmaster@africaonline.co.ci'),
                    ('"us4rmc::bajan@bunyip.com"@boco.enet.dec.com',                    'bajan@bunyip.com'),
                    ('"us4rmc::raisch@internet.com"@boco.enet.dec.com',                 'raisch@internet.com'),
                    ('"Xiaodong(Sheldon) Lee <lee@cnnic.cn>"@NeuStar.com',              'lee@cnnic.cn'),
                    ('"Michelle Claudé <Michelle.Claude@prism.uvsq.fr>"@prism.uvsq.fr', 'Michelle.Claude@prism.uvsq.fr'),
                    ('"kaufman@zk3.dec.com"@minsrv.enet.dec.com',                       'kaufman@zk3.dec.com'),
                    ('"ietf-ipr@ietf.org"@ietfa.amsl.com',                              'ietf-ipr@ietf.org')]
    for orig_addr, repl_addr in replacements:
        if from_addr == orig_addr:
            print(f"_fixup_from_addr_2at: rewrite From: \"{orig_addr}\" -> \"{repl_addr}\"")
            return from_name, repl_addr
    raise RuntimeError(f"Cannot fix from_addr containing two @ signs: {from_addr}")


def _parse_header_from(msg) -> Tuple[Optional[str],Optional[str]]:
    """
    This is a private helper function - do not use.
    """
    from_hdr = msg["from"]
    if from_hdr is None:
        # The "From:" header is missing
        return (None, None)

    parts = decode_header(from_hdr)
    init_hdr, init_charset = parts[0]
    if isinstance(init_hdr, str):
        hdr, charset = parts[0]
        assert charset is None
    else:
        hdr = ""
        for part_bytes, charset in parts:
            if charset is None or charset == "unknown-8bit":
                part_text = part_bytes.decode(errors="backslashreplace")
            else:
                part_text = part_bytes.decode(charset, errors="backslashreplace")
            hdr = hdr + part_text

    addr_list = getaddresses([hdr])
    if len(addr_list) == 0:
        # The "From:" header is present but empty:
        from_name = ""
        from_addr = ""
    elif len(addr_list) == 1:
        # The "From:" header contains a single address:
        from_name, from_addr = addr_list[0]
        if from_addr is not None and from_addr.count("@") == 0:
            from_name, from_addr = _fixup_from_addr_0at(from_name, from_addr)
        if from_addr is not None and from_addr.count("@") == 1:
            from_name, from_addr = _fixup_from_addr_1at(from_name, from_addr)
        if from_addr is not None and from_addr.count("@") == 2:
            from_name, from_addr = _fixup_from_addr_2at(from_name, from_addr)
        if from_addr is not None and from_addr.count("@") >= 2:
            raise RuntimeError("Cannot fix from address with more than two @ signs")
    elif len(addr_list) > 1:
        # The "From:" header contains multiple addresses; use the first one with a valid domain:
        from_name = ""
        from_addr = ""
        for group in from_hdr.groups:
            if   len(group.addresses) == 0:
                pass
            elif len(group.addresses) == 1:
                if "." in group.addresses[0].domain: # We consider the domain to be valid if it contains a "."
                    from_name = group.addresses[0].display_name
                    from_addr = group.addresses[0].addr_spec
                    break
            else:
                raise RuntimeError(f"Cannot parse \"From:\" header: multiple addresses in group")
        if from_addr is not None and from_addr.count("@") == 0:
            from_name, from_addr = _fixup_from_addr_0at(from_name, from_addr)
        if from_addr is not None and from_addr.count("@") == 1:
            from_name, from_addr = _fixup_from_addr_1at(from_name, from_addr)
        if from_addr is not None and from_addr.count("@") == 2:
            from_name, from_addr = _fixup_from_addr_2at(from_name, from_addr)
        if from_addr is not None and from_addr.count("@") >= 2:
            raise RuntimeError("Cannot fix from address with more than two @ signs")
        print(f"_parse_header_from: multiple addresses [{hdr}] -> [{from_name}] [{from_addr}]")
    else:
        raise RuntimeError(f"Cannot parse \"From:\" header: cannot happen")

    # The result returned here is stored in the database and later
    # returned an an Address object. Check if from_name, from_addr
    # are parsable into such an object and return them if so, If
    # not, return (None, None) to indicate a failure.
    try:
        discarded = Address(display_name = from_name, addr_spec = from_addr)
        if from_name == "":
            return_from = None
        else:
            return_from = from_name
        if from_addr == None:
            return_addr = None
        else:
            return_addr = from_addr
        return (return_from, return_addr)
    except:
        print(f"_parse_header_from: cannot convert to Address")
        print(f"   from header: {hdr}")
        print(f"   parsed name: {from_name}")
        print(f"   parsed addr: {from_addr}")
        return (None, None)



def _parse_header_to_cc(msg, to_cc:str):
    """
    This is a private helper function - do not use.
    """
    to_cc_hdr = msg[to_cc]
    if to_cc_hdr is None:
        return []
    else:
        addr_list = getaddresses([to_cc_hdr])   # Should use 'strict=False'?
        if len(addr_list) == 0:
            raise RuntimeError(f"_parse_header_to_cc: empty or unparseable {to_cc} header: hdr={to_cc_hdr}")
        elif len(addr_list) > 0:
            headers = []
            index   = 0
            for name, addr in addr_list:
                # Decode MIME-encoded internationalised names:
                parts = decode_header(name)
                init_name, init_charset = parts[0]
                if isinstance(init_name, str):
                    decoded_name, charset = parts[0]
                    assert charset is None
                else:
                    decoded_name = ""
                    for part_bytes, charset in parts:
                        if charset is None or charset == "unknown-8bit":
                            part_text = part_bytes.decode(errors="backslashreplace")
                        else:
                            # The "To:" header for ipv6/41694 has a malformed charset that crashes part_bytes.decode()
                            if charset == "ut f-8":
                                charset = "utf-8"
                            part_text = part_bytes.decode(charset, errors="backslashreplace")
                        decoded_name = decoded_name + part_text

                # Fix-up addresses:
                addr = addr.strip()

                if addr.endswith("@dmarc.ietf.org"):
                    fixed_addr = addr[:-15].replace("=40", "@")
                    #print(f"_parse_header_to_cc: undo DMARC {to_cc} processing: {addr} -> {fixed_addr}")
                    addr = fixed_addr

                if " at " in addr and addr.count("@") == 0:
                    fixed_addr = addr.replace(" at ", "@")
                    if fixed_addr.startswith('"') and fixed_addr.endswith('"'):
                        fixed_addr = fixed_addr[1:-1]
                    print(f"_parse_header_to_cc: undo anti-spam {to_cc} processing: {addr} -> {fixed_addr}")
                    addr = fixed_addr

                # Discard malfored addresses:
                if addr != "" and addr.count("@") == 0:
                    print(f"_parse_header_to_cc: discarded malformed {to_cc} address (1): [{decoded_name}] [{addr}]")
                    continue
                if addr != "" and addr.count("@") >= 2:
                    print(f"_parse_header_to_cc: discarded malformed {to_cc} address (2): [{decoded_name}] [{addr}]")
                    continue

                # The headers extracted here are stored in the database and later
                # returned an Address objects. Check if decoded_name, addr can be
                # converted into such an object, discarding unusable values.
                try:
                    if decoded_name == "" and addr == "":
                        # print(f"_parse_header_to_cc: skipped empty {to_cc} header:")
                        pass
                    else:
                        discarded = Address(display_name = decoded_name, addr_spec = addr)
                        headers.append((index, decoded_name, addr))
                except:
                    print(f"_parse_header_to_cc: discarded malformed {to_cc} address (3): [{decoded_name}] [{addr}]")

                index += 1
            return headers
        else:
            raise RuntimeError(f"_parse_header_to_cc: cannot parse {to_cc} header: {to_cc_hdr}")


def _parse_header_subject(msg):
    """
    This is a private helper function - do not use.
    """
    hdr = msg["subject"]
    if hdr is None:
        return None
    else:
        return hdr.strip()


def _parse_header_date(msg):
    """
    This is a private helper function - do not use.
    """
    if msg["date"] is None:
        return None
    hdr = msg["date"].strip()

    try:
        # Standard date format:
        temp = parsedate_to_datetime(hdr)
        date = temp.astimezone(UTC).isoformat()
        # print(f"_parse_header_date: okay (0): {date} | {hdr}")
        return date
    except:
        try:
            # Standard format, with invalid timezone: Mon, 27 Dec 1993 13:46:36 +22306256
            # Parse assuming the timezone is UTC
            split = hdr.split(" ")[:-1]
            split.append("+0000")
            joined = " ".join(split)
            date = parsedate_to_datetime(joined).astimezone(UTC).isoformat()
            # print(f"_parse_header_date: okay (1): {date} | {hdr}")
            return date
        except:
            try:
                # Non-standard date format: 04-Jan-93 13:22:13 (assume UTC timezone)
                temp = datetime.strptime(hdr, "%d-%b-%y %H:%M:%S")
                date = temp.astimezone(UTC).isoformat()
                # print(f"_parse_header_date: okay (2): {date} | {hdr}")
                return date
            except:
                try:
                    # Non-standard date format: 30-Nov-93 17:23 (assume UTC timezone)
                    temp = datetime.strptime(hdr, "%d-%b-%y %H:%M")
                    date = temp.astimezone(UTC).isoformat()
                    # print(f"_parse_header_date: okay (3): {date} | {hdr}")
                    return date
                except:
                    try:
                        # Non-standard date format: 2006-07-29 00:55:01 (assume UTC timezone)
                        temp = datetime.strptime(hdr, "%Y-%m-%d %H:%M:%S")
                        date = temp.astimezone(UTC).isoformat()
                        # print(f"_parse_header_date: okay (4): {date} | {hdr}")
                        return date
                    except:
                        try:
                            # Non-standard date format: Mon, 17 Apr 2006  8: 9: 2 +0300
                            tmp1 = hdr.replace(": ", ":0").replace("  ", " 0")
                            tmp2 = parsedate_to_datetime(tmp1)
                            date = tmp2.astimezone(UTC).isoformat()
                            # print(f"_parse_header_date: okay (5): {date} | {hdr}")
                            return date

                        except:
                            print(f"_parse_header_date: invalid Date: {hdr}")
                            return None


def _parse_header_message_id(msg):
    """
    This is a private helper function - do not use.
    """
    hdr = msg["message-id"]
    if hdr is None:
        return None
    else:
        return hdr.strip()


def _parse_header_in_reply_to(msg):
    """
    This is a private helper function - do not use.
    """
    hdr = msg["in-reply-to"]
    if hdr is not None and hdr != "":
        return hdr.strip()
    hdr = msg["references"]
    if hdr is not None and hdr != "":
        return hdr.strip().split(" ")[-1]
    return None


def parse_message(uidvalidity:int, uid:int, msg_raw:bytes) -> Dict[str,Any]:
    """
    Parse an RFC 822-style email message, extracting headers of interest.

    This applies a number of heuristics to parse and correct malformed
    header fields.
    """
    parsing_policy = EmailPolicyCustom()

    msg = BytesHeaderParser(policy=parsing_policy).parsebytes(msg_raw)

    from_name, from_addr = _parse_header_from(msg)

    res = {
            "uid"         : uid,
            "from_name"   : from_name,
            "from_addr"   : from_addr,
            "to"          : _parse_header_to_cc(msg, "to"),
            "cc"          : _parse_header_to_cc(msg, "cc"),
            "subject"     : _parse_header_subject(msg),
            "date"        : _parse_header_date(msg),
            "message_id"  : _parse_header_message_id(msg),
            "in_reply_to" : _parse_header_in_reply_to(msg),
            "raw_data"    : msg_raw
          }

    return res


