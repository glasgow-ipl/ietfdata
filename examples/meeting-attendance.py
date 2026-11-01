# Copyright (C) 2025 University of Glasgow
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
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ietfdata.datatracker import *

dt = DataTracker(DTBackendArchive("archive/ietf-dt.sqlite"))

# Meeting attendance from https://www.ietf.org/meeting/past/
proceedings = {}
proceedings["122"] = {"onsite":  752, "remote":  549}
proceedings["121"] = {"onsite":  993, "remote":  559}
proceedings["120"] = {"onsite":  833, "remote":  681}
proceedings["119"] = {"onsite":  687, "remote":  742}
proceedings["118"] = {"onsite": 1050, "remote":  588}
proceedings["117"] = {"onsite":  890, "remote":  544}
proceedings["116"] = {"onsite":  993, "remote":  594}
proceedings["115"] = {"onsite":  849, "remote":  667}
proceedings["114"] = {"onsite":  618, "remote":  675}
proceedings["113"] = {"onsite":  314, "remote":  976}
proceedings["112"] = {"onsite":    0, "remote": 1177}
proceedings["111"] = {"onsite":    0, "remote": 1206}
proceedings["110"] = {"onsite":    0, "remote": 1177}
proceedings["109"] = {"onsite":    0, "remote": 1061}
proceedings["108"] = {"onsite":    0, "remote": 1102}
proceedings["107"] = {"onsite":    0, "remote":  701}
proceedings["106"] = {"onsite": 1004, "remote":  607}
proceedings["105"] = {"onsite": 1103, "remote":  861}
proceedings["104"] = {"onsite": 1213, "remote":  864}
proceedings["103"] = {"onsite":  879, "remote":  521}
proceedings["102"] = {"onsite": 1078, "remote":  547}
proceedings["101"] = {"onsite": 1235, "remote":  575}
proceedings["100"] = {"onsite": 1018, "remote":  468}

mt_ietf = dt.meeting_type_from_slug("ietf")


def meeting_sessions(meeting) -> List[Session]:
    sessions = []
    if meeting.schedule is not None:
        schedule = dt.meeting_schedule(meeting.schedule)
        for sa in dt.meeting_session_assignments(schedule):
            session = dt.meeting_session(sa.session)
            if session is not None:
                sessions.append(session)
    return sessions


def session_attendees(sessions):
    attendees = {}
    for session in sessions:
        attendees[session.id] = []
        for attendee in dt.meeting_attendance(session):
            person = dt.person(attendee.person)
            attendees[session.id].append(person.id)
    return attendees


def joined_session(sessions, attendees, person_uri) -> bool:
    person = dt.person(person_uri)
    joined_other = []
    for session in sessions:
        if person.id in attendees[session.id]:
            group = dt.group(session.group)
            gtype = dt.group_type_name(group.type)
            if gtype.slug in ["wg", "rg", "ag", "rag"]:
                # Participation in working groups, research groups, area
                # groups, or reseaarch area groups (except for the ANRW)
                # counts as attendance.
                if group.acronym.upper() != "ANRW":
                    return True
            elif gtype.slug in ["team", "dir", "ietf", "edwg", "program"]:
                # Participation in other types of session does not... 
                joined_other.append(f"{gtype.slug}-{group.acronym}")
                pass
            else:
                raise RuntimeError(f"Unknown group type: {gtype.slug}")
    #if len(joined_other) > 0:
    #    print(f"   joined other {person.name}: {joined_other}")
    return False

results = {}

for meeting in sorted(dt.meetings(meeting_type = mt_ietf), key=lambda meeting: int(meeting.number)):
    if meeting.status() != MeetingStatus.COMPLETED:
        continue

    # No records prior to IETF 72 in the datatracker
    if int(meeting.number) < 72:
        continue

    sessions  = meeting_sessions(meeting)
    attendees = session_attendees(sessions)

    print(f"IETF {meeting.number:3} ({len(sessions)} sessions) -- {meeting.city}")

    combined_attend = []
    onsite_attend = []
    onsite_noshow = []
    remote_attend = []
    hackathon_onsite_attend = []
    hackathon_remote_attend = []
    anrw_onsite_attend = []

    for reg in dt.meeting_registrations(meeting = meeting):
        if reg.reg_type == "":
            # From IETF 72 to IETF 99, inclusive, we have registration data
            # but no indication if the attendee was onsite or remote
            assert reg.checkedin == False
            if reg.person is None:
                # FIXME: datatracker name lookup?
                combined_attend.append(f"{reg.first_name} {reg.last_name}")
            else:
                combined_attend.append(reg.person)
        else:
            # From IETF 100 onwards, we can differentiate onesite or remote
            # attendees, and those who attended the hackathon or ANRW.
            #
            # From IETF 100 to IETF 114, the reg.attended indicates whether
            # the person attended the meeting. From IETF 115, reg.checkedin
            # is used to indicate if person collected their name badge.
            if reg.reg_type == "onsite":
                if   reg.attended and reg.checkedin:
                    # Attended and picked-up their name badge
                    onsite_attend.append(reg.person)
                elif reg.attended and not reg.checkedin:
                    # There are a small number of people for IETF 113 or
                    # IETF 114, the first two in-person meetings after the
                    # pandemic, that are marked as having attended but not
                    # collected their name badge.
                    assert int(meeting.number) == 113 or int(meeting.number) == 114
                    if joined_session(sessions, attendees, reg.person):
                        # Marked as having attended, did not collect badge, but
                        # joined at lesst one session. Likely self-isolating in
                        # their hotel room having picked-up COVID on the way to
                        # the meeting and joining sessions remotely.
                        onsite_attend.append(reg.person)
                    else:
                        # Marked as having attended, did not collect badge, and
                        # did not attend any sessions. Likely no-show.
                        onsite_noshow.append(reg.person)
                elif not reg.attended and reg.checkedin:
                    # From IETF 113 onwards, when IETF returned to in-person
                    # meetings after the pandemic, we start to see attendees
                    # marked as not attending but collecting their name badge.
                    # Assume the registration system changed at the point and
                    # mark them as having attended.
                    assert int(meeting.number) >= 113
                    onsite_attend.append(reg.person)
                elif not reg.attended and not reg.checkedin:
                    if joined_session(sessions, attendees, reg.person):
                        # Registered, not recorded as attending and did not
                        # collect their name badge, but joined some sessions.
                        # They either attended in-person and forgot to collect
                        # their name badge, or planned to attend in-person but
                        # switched to remote attendance at the last minute
                        # without changing their registration.
                        onsite_attend.append(reg.person)
                    else:
                        # Registered, not recorded as attending, did not
                        # collect their name badge, and did not join any
                        # sessions.
                        onsite_noshow.append(reg.person)
                    pass
                else:
                    raise RuntimeError("Can never happen")
            elif reg.reg_type == "remote":
                if int(meeting.number) < 100:
                    remote_attend.append(reg.person)
                elif int(meeting.number) >= 100 and int(meeting.number) <= 106:
                    # From IETF 100 to IETF 106 are missing remote attendee data
                    pass
                elif int(meeting.number) >= 107 and int(meeting.number) <= 114:
                    # From IETF 107 to IETF 114, reg.attended indicates
                    # whether the remote attendee actually participated.
                    assert reg.checkedin == False
                    if reg.attended:
                        remote_attend.append(reg.person)
                else:
                    # From IETF 115 onwards, reg.attended is not valid
                    # for remote attendees. 
                    assert reg.attended == False
                    if reg.checkedin:
                        # Registered for remote attendance but collected a name
                        # badge. This is likely a data entry bug and the person
                        # was actually remote, but mark them as attended onsite
                        # to align the participant count with the proceedings
                        # (occurs for one participant during IETF 116).
                        onsite_attend.append(reg.person)
                    else:
                        # Mark as attended remotely if they joined any session.
                        if joined_session(sessions, attendees, reg.person):
                            remote_attend.append(reg.person)
            elif reg.reg_type == "hackathon_onsite":
                hackathon_onsite_attend.append(reg.person)
            elif reg.reg_type == "hackathon_remote":
                hackathon_remote_attend.append(reg.person)
            elif reg.reg_type == "anrw_onsite":
                anrw_onsite_attend.append(reg.person)
            else:
                raise RuntimeError(f"Unknown registration type: {reg.reg_type}")

    hack_only_joined = []
    hack_not_plenary = []
    for person_uri in hackathon_onsite_attend:
        if person_uri not in onsite_attend:
            hack_not_plenary.append(person_uri)
            if joined_session(sessions, attendees, person_uri):
                # Registered for the hackathon but not onsite attendance, but
                # joined onsite sessions anyway:
                onsite_attend.append(person_uri)
                hack_only_joined.append(person_uri)

    anrw_only_joined = []
    anrw_not_plenary = []
    for person_uri in anrw_onsite_attend:
        if person_uri not in onsite_attend:
            anrw_not_plenary.append(person_uri)
            if joined_session(sessions, attendees, person_uri):
                # Registered for the hackathon but not onsite attendance, but
                # joined onsite sessions anyway:
                onsite_attend.append(person_uri)
                anrw_only_joined.append(person_uri)

    print(f"           combined: {len(combined_attend):4}")
    print(f"             onsite: {len(onsite_attend):4}") # ({proceedings[meeting.number]['onsite']:4})")
    print(f"             remote: {len(remote_attend):4}") # ({proceedings[meeting.number]['remote']:4})")
    print(f"             noshow: {len(onsite_noshow):4}")
    print(f"   hackathon_onsite: {len(hackathon_onsite_attend):4}")
    print(f"        ...of which  {len(hack_not_plenary):4} were not registered for the plenary meeting")
    print(f"        ...of which  {len(hack_only_joined):4} joined the plenary meeting anyway")
    print(f"   hackathon_remote: {len(hackathon_remote_attend):4}")
    print(f"        anrw_onsite: {len(anrw_onsite_attend):4}")
    print(f"        ...of which  {len(anrw_not_plenary):4} were not registered for the plenary meeting")
    print(f"        ...of which  {len(anrw_only_joined):4} joined the plenary meeting anyway")
    print("")

    ietf = f"IETF{meeting.number}"
    results[ietf] = {}
    results[ietf]["combined_attendees"] = sorted(map(lambda x: str(x), combined_attend))
    results[ietf]["onsite_attendees"] = sorted(map(lambda x: str(x), onsite_attend))
    results[ietf]["remote_attendees"] = sorted(map(lambda x: str(x), remote_attend))
    results[ietf]["onsite_noshow"]    = sorted(map(lambda x: str(x), onsite_noshow))
    results[ietf]["hackathon_onsite_attendees"]      = sorted(map(lambda x: str(x), hackathon_onsite_attend))
    results[ietf]["hackathon_remote_attendees"]      = sorted(map(lambda x: str(x), hackathon_remote_attend))
    results[ietf]["hackathon_only_onsite_attendees"] = sorted(map(lambda x: str(x), hack_not_plenary))
    results[ietf]["hackathon_only_onsite_attendees_plenary"] = sorted(map(lambda x: str(x), hack_only_joined))
    results[ietf]["anrw_onsite_attendees"]              = sorted(map(lambda x: str(x), anrw_onsite_attend))
    results[ietf]["anrw_only_onsite_attendees"]         = sorted(map(lambda x: str(x), anrw_not_plenary))
    results[ietf]["anrw_only_onstie_attendees_plenary"] = sorted(map(lambda x: str(x), anrw_only_joined))


with open("attendees.json", "w") as outf:
    json.dump(results, outf, indent=3)

