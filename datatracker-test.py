from datatracker import *

dt = DataTracker()

# p1 = dt.person("20209")
# print(p1)
# print(p1['name'])
# 
# p2 = dt.person_from_email("ietf@trammell.ch")
# print(p2)
# 
# people = dt.people(since="2018-04-01T00:00:00", until="2018-04-01T23:59:59")
# print(len(people))

documents = dt.documents(since="2018-04-27T00:00:00", doctype="charter")
print(len(documents))
for d in documents:
    print(d)
    print("")
    print("")

documents = dt.documents(since="2018-04-27T00:00:00", doctype="draft", group="2161")
print(len(documents))
for d in documents:
    print(d)
    print("")
    print("")

# d1 = dt.document("draft-ietf-quic-transport")
# print(d1)

# d2 = dt.document_from_rfc("rfc3550")
# print(d2)
# print("")
# for s in d2['states']:
#     print(dt.document_state(s))
#     print("")

# for s in dt.document_states():
#     print(s)
#     print("")

