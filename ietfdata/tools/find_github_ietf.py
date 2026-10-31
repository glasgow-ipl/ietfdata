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

import sys

from ietfdata.datatracker import *
from ietfdata.github_ietf import GitHubIETF

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python3 -m ietfdata.find_github_ietf <ietf-dt.sqlite> <id-dir> <github.sqlite> <github-ietf.json>")
        sys.exit(1)

    ietf_dt_sqlite = sys.argv[1]
    id_archive_dir = sys.argv[2]
    github_sqlite  = sys.argv[3]
    output_json    = sys.argv[4]

    dt = DataTracker(DTBackendArchive(ietf_dt_sqlite))
    gh_ietf = GitHubIETF(github_sqlite, dt, id_archive_dir)
    gh_ietf.find_repositories()

    gh_users = []
    gh_repos = {}

    for user in gh_ietf.users():
        gh_users.append(user)
    for repo in gh_ietf.repos():
        gh_repos[f"{repo['user']}/{repo['repo']}"] = repo

    gh_json = {"users": gh_users, "repos": gh_repos}

    with open(output_json, "w") as outf:
        json.dump(gh_json, outf, indent=3)

