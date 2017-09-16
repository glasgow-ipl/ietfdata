#!/usr/bin/env python3

from pathlib  import Path
from ietfdata import RFCIndex

import requests
import time

for d in ["data", "data/rfc", "data/id"]:
    if not Path(d).is_dir():
        print("[mkdir]", d)
        Path(d).mkdir(exist_ok=True)

# Fetch the index if it doesn't exist or is more than 24 hours old:
index_path = Path("data/rfc-index.xml")
if not index_path.exists() or ((time.time() - index_path.stat().st_mtime) > 86400):
    print("[fetch]", index_path)
    response = requests.get("https://www.rfc-editor.org/rfc-index.xml")
    with open(index_path, "w") as f:
        f.write(response.text)

print("[parse]", index_path)
index = RFCIndex(index_path)



