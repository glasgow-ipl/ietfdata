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

import matplotlib
import matplotlib.pyplot as plt
import numpy  as np
import pandas as pd
import sys
 
if len(sys.argv) != 3:
    print(f"Usage: python3 {sys.argv[0]} <input_file.csv> <output_file.pdf>")
    sys.exit(1)

csv_path = sys.argv[1]
pdf_path = sys.argv[2]

csv = pd.read_csv(csv_path)

matplotlib.use("PDF")

plt.figure(figsize=(3.5,2))
plt.rcParams["font.family"] = "serif"
plt.rcParams["font.serif"] = ["Times"]
plt.rcParams["font.size"] = 9
plt.rcParams["text.usetex"] = True
plt.rcParams["pdf.fonttype"] = 42
plt.rcParams["axes.axisbelow"] = True

fig, ax = plt.subplots(figsize=(3.5,2))

bottom = np.zeros(len(csv))
for stream in csv.columns[1:]:
    ax.bar(csv["Year"], csv[stream], bottom=bottom, label=stream)
    bottom += np.array(csv[stream])
ax.legend(fontsize=6, ncol=4, loc="upper left", bbox_to_anchor=(0.0, 1.45), frameon=False)

plt.plot()

plt.xlabel("Year")
plt.ylabel("RFCs Published")
plt.ylim(top=500)

# Annotate with date IETF created
plt.plot([1986, 1986], [0, 400], ':', color='black')
plt.text(1983, 410, 'IETF Created', color='black', fontsize=7)

plt.savefig(pdf_path, format="pdf", bbox_inches="tight")

