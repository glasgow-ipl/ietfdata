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

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime                 import timedelta
from pathlib                  import Path
from ietfdata.datatracker     import *
from ietfdata.datatracker_ext import *
from dateutil.parser          import *

dt = DataTrackerExt()

# =============================================================================
# Information about the IAB:

print(F"The IAB chair is {dt.iab_chair().name}")

print("The IAB members are:")
for m in dt.iab_members():
    print(F"  {m.name}")
print("")

# =============================================================================
# Information about the IRTF leadership:

print(F"The IRTF chair is {dt.irtf_chair().name}")

print("The IRSG members are:")
for m in dt.irsg_members():
    print(F"  {m.name}")
print("")

print("The IRTF research group chairs are:")
for m in dt.research_group_chairs():
    print(F"  {m.name}")
print("")

# =============================================================================
# Information about the IETF leadership:

print(F"The IETF chair is {dt.ietf_chair().name}")

print("The IESG members are:")
for m in dt.iesg_members():
    print(F"  {m.name}")
print("")

print("The IETF working group chairs are:")
for m in dt.working_group_chairs():
    print(F"  {m.name}")
print("")

# =============================================================================
