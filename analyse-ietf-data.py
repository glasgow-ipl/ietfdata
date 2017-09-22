#!/usr/bin/env python3
#
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
from rfcindex import RFCIndex
from rfc      import RFC

import datetime
import requests
import time

for d in ["data", "data/rfc", "data/id", "plots"]:
    if not Path(d).is_dir():
        print("[mkdir]", d)
        Path(d).mkdir(exist_ok=True)

# Fetch the index if it doesn't exist or is more than 24 hours old:
index_path = Path("data/rfc-index.xml")
if not index_path.exists() or ((time.time() - index_path.stat().st_mtime) > 86400):
    print("Fetch", index_path)
    response = requests.get("https://www.rfc-editor.org/rfc-index.xml")
    with open(index_path, "w") as f:
        f.write(response.text)

print("Parse", index_path)
index = RFCIndex(index_path)

with open("plots/rfcs-by-year.dat", "w") as f:
    total = 0
    for year in range(1968, datetime.datetime.now().year+1):
        x = list(filter(lambda rfc: rfc.year == year, index.rfc.values()))
        total += len(x)
        f.write("{0} {1} {2}\n".format(year, len(x), total))

# Fetch the RFC text:
print("Fetch and Parse RFCs:", end="", flush=True)
cnt = -1
rfc = {}
for r in index.rfc.values():
    # Display progress:
    cnt = cnt + 1
    if (cnt % 100) == 0:
        print("", flush=True)
        print("{:5}: ".format(cnt), end="", flush=True)
    else:
        print(".", end="", flush=True)

    rfc[r.doc_id] = RFC(r)
    a = rfc[r.doc_id].authors()
#    if a == None:
#        print(r.doc_id, a)




