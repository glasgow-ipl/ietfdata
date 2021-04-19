# Copyright (C) 2020 University of Glasgow
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

import os
import sys
import textwrap

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pathlib              import Path
from ietfdata.datatracker import *

# =============================================================================

def person_chair_roles(dt: DataTracker, person: Person):
    group_acronyms = set()

    for role in dt.group_roles(person=person):
        if dt.role_name(role.name).slug == "chair":
            group = dt.group(role.group)
            group_state = dt.group_state(group.state)
            group_type  = dt.group_type_name(group.type)
            print(F"is chair of {group.acronym} which is {group_state.name} {group_type.name}")
            group_acronyms.add(dt.group(role.group).acronym)
    for role in dt.group_role_histories(person=p):
        if dt.role_name(role.name).slug == "chair":
            gh = dt.group_history(role.group)
            group_state = dt.group_state(gh.state)
            group_type  = dt.group_type_name(gh.type)
            print(F"chaired {group.acronym} which was {group_state.name} {group_type.name} on {gh.time}")
            group_acronyms.add(dt.group_history(role.group).acronym)

    for acronym in group_acronyms:
        group = dt.group_from_acronym(acronym)
        print(F"  {acronym} state {dt.group_state(group.state).name}")

        if group.comments != "":
            # This is natural language, and it's a mess
            pass


        for event in reversed(list(dt.group_events(group = dt.group_from_acronym(acronym)))):
            if event.type == "info_changed" and event.desc.startswith("Chairs changed to"):
                split_loc  = event.desc.find("</b> from ")
                new_chairs = event.desc[21:split_loc]
                old_chairs = event.desc[split_loc+10:]
                if person.name in new_chairs and not person.name in old_chairs:
                    print(F"started as chair of {acronym} on {event.time}")
                if not person.name in new_chairs and person.name in old_chairs:
                    print(F"stopped as chair of {acronym} on {event.time}")
            elif event.type == "changed_state" and event.desc.startswith("State changed to <b>Concluded</b>"):
                print(F"  {acronym} concluded on {event.time}")
            elif event.type == "changed_state" and event.desc == "Concluded group":
                print(F"  {acronym} concluded on {event.time}")
            elif event.type == "changed_state" and event.desc == "Started group":
                print(F"  {acronym} started on {event.time}")
            elif event.type == "changed_state" and event.desc == "Proposed group":
                print(F"  {acronym} proposed on {event.time}")


# =============================================================================
# Example: print information about a person

dt = DataTracker()

p = dt.person_from_email("rachel.huang@huawei.com")
print("Name: {}".format(p.name))
person_chair_roles(dt, p)
print("")

p = dt.person_from_email("csp@csperkins.org")
print("Name: {}".format(p.name))
person_chair_roles(dt, p)
print("")

p = dt.person_from_email("magnus.westerlund@ericsson.com")
print("Name: {}".format(p.name))
person_chair_roles(dt, p)
print("")


#for group in dt.groups():
#    if group.comments != "":
#        print(F"{group.acronym}: {group.comments}")






#print("Name: {}".format(p.name))
#print("Biography: {}".format(p.biography))
#
#
#for alias in dt.person_aliases(p):
#    print("Known as: {}".format(alias.name))
#
#
#for email in dt.email_for_person(p):
#    if email.primary:
#        primary = "(primary)"
#    else:
#        primary = ""
#    print("Email: {} {}".format(email.address, primary))
#
#    for subscriptions in dt.mailing_list_subscriptions(email.address):
#        for mailing_list_uri in subscriptions.lists:
#            mailing_list = dt.mailing_list(mailing_list_uri)
#            print("  Subscribed to mailing list {}".format(mailing_list.name))
#
#
#for h in dt.email_history_for_person(p):
#    print(F"Found email {h.address} on {h.history_date} origin: \"{h.origin}\"")
#
#
#for d in dt.documents_authored_by_person(p):
#    doc = dt.document(d.document)
#    print("Author of {}".format(doc.name))
#    print("  Title:       {}".format(doc.title))
#    print("  Affiliation: {}".format(d.affiliation))
#    print("  Country:     {}".format(d.country))
#    for s in doc.submissions:
#        sub = dt.submission(s)
#        print(F"  Submission:  {sub.name}-{sub.rev} on {sub.submission_date}")
#
#
#for ballot in dt.ballot_document_events(by=p):
#    ballot_doc = dt.document(ballot.doc)
#    print(F"Ballot: {ballot.time} {ballot.desc} on {ballot_doc.name}")
#
#
#for event in dt.group_events(by=p):
#    group = dt.group(event.group)
#    print(F"Group Event: {group.acronym.upper()} {event.type} on {event.time}")
#    print(F"  {textwrap.shorten(event.desc, width=98, placeholder='...')}")
#
#
#for event in dt.group_milestone_events(by=p):
#    group = dt.group(event.group)
#    print(F"Group Milestone Event: {group.acronym.upper()} {event.type} on {event.time}")
#    print(F"  {textwrap.shorten(event.desc, width=98, placeholder='...')}")
#
#
#for event in dt.group_state_change_events(by=p):
#    group = dt.group(event.group)
#    print(F"Group State Change Event: {group.acronym.upper()} {event.type} on {event.time}")
#    print(F"  {textwrap.shorten(event.desc, width=98, placeholder='...')}")
#
#
#for role in dt.group_roles(person=p):
#    rolename = dt.role_name(role.name)
#    group    = dt.group(role.group)
#    print(F"Current role: {rolename.name} of {group.acronym.upper()}")
#
#
#for role in dt.group_role_histories(person=p):
#    e  = dt.email(role.email)
#    rn = dt.role_name(role.name)
#    gh = dt.group_history(role.group)
#    print(F"Previous role: {rn.name} of {gh.acronym.upper()} on {gh.time}")
#
#
#for reg in dt.meeting_registrations(person=p):
#    meeting = dt.meeting(reg.meeting)
#    if dt.meeting_type(meeting.type) == dt.meeting_type_from_slug("ietf"):
#        print(F"Registered for IETF {meeting.number} in {meeting.city}")
#        print(F"  Name: {reg.first_name} {reg.last_name}")
#        print(F"  Affiliation: {reg.affiliation}")
#        print(F"  Attended: {reg.attended}")
#
#    else:
#        print(meeting.number)
#
#
#for email in dt.email_for_person(p):
#    for r in dt.review_assignments(reviewer=email):
#        if r.review is not None:
#            doc = dt.document(r.review)
#            res = dt.review_result_type(r.result)
#            print(F"Review: {doc.name} (revision {r.reviewed_rev})")
#            print(F"  Assigned:  {r.assigned_on}")
#            print(F"  Completed: {r.completed_on}") 
#            print(F"  State:     {dt.review_assignment_state(r.state).name}")
#            print(F"  Result:    {res.name}")
#            print(F"  Review:    {r.mailarch_url}")


# =============================================================================
