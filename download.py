#!/usr/bin/env python3

from ietfdata import RFCIndex

#for d in ["data", "data/rfc", "data/id"]:
#    Path(d).mkdir(exist_ok=True)

# # Fetch the index if it doesn't exist or is more than 24 hours old:
# if not self.path.exists() or ((time.time() - self.path.stat().st_mtime) > 86400):
#     print("[ietf-data] fetch", self.path)
#     response = requests.get("https://www.rfc-editor.org/rfc-index.xml")
#     with open(self.path, "w") as f:
#         f.write(response.text)

index = RFCIndex("data/rfc-index.xml")
for doc in index.rfcs:
    print(doc)

for doc in index.rfcs_not_issued:
    print(doc)

for doc in index.bcps:
    print(doc)

for doc in index.stds:
    print(doc)

for doc in index.fyis:
    print(doc)



