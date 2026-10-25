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
import json

from ietfdata.datatracker import *
from ietfdata.github      import *

class GitHubIETF:
    _gh : GitHub
    _dt : DataTracker

    def __init__(self, gh:GitHub, dt:DataTracker):
        """
        The GitHubIETF class is used to retrieve information about
        GitHub users and repositories used in the IETF.
        """
        self._gh = gh
        self._dt = dt
        self._users = []
        self._repos = []


    def _fix_username(self, username) -> str:
        if username.startswith("(") and username.endswith(")"):
            username = username[1:-1]
        if username.startswith("'") and username.endswith("'"):
            username = username[1:-1]

        if username.startswith("https://github.com/"):
            username = username[19:]
        elif username.startswith("https://www.github.com/"):
            username = username[23:]
        elif username.startswith("github.com/"):
            username = username[11:]
        elif username.startswith("https://") and username.endswith(".github.io/"):
            username = username[8:-11]
        elif username.startswith("https://") and username.endswith(".github.io"):
            username = username[8:-10]

        if "/" in username and not username.startswith("http"):
            username = username[:username.find("/")]
        if "?" in username:
            username = username[:username.find("?")]

        return username


    def _fix_reponame(self, reponame) -> str:
        if reponame.count("/") > 4:
            index  = 0
            offset = 0
            while index < 5:
                offset = reponame.find("/", offset) + 1
                index += 1
            reponame = reponame[:offset - 1]
        return reponame


    def _search_person_ext_resources(self) -> None:
        print("  Search for GitHub data in person_ext_resources()")
        for resource in self._dt.person_ext_resources():
            rname = dt.ext_resource_name(resource.name).slug
            if rname == "github_username":
                username = self._fix_username(resource.value)
                if len(username) > 1 and username not in self._users:
                    print(f"    Found user {username}")
                    self._users.append(username)
            if rname == "github_repo":
                if resource.value.startswith("https://github.com/"):
                    url_stem = resource.value[19:]
                    username = self._fix_username(url_stem[:url_stem.find("/")])
                    if username not in self._users:
                        print(f"    Found user {username}")
                        self._users.append(username)


    def _search_group_urls(self) -> None:
        print("  Search for GitHub data in group_urls()")
        for url in dt.group_urls():
            if "github" in url.url:
                username = self._fix_username(url.url)
                if username not in self._users:
                    print(f"    Found user {username}")
                    self._users.append(username)


    def _search_document_urls(self) -> None:
        print("  Search for GitHub data in document_urls()")
        for url in dt.document_urls():
            if "github" in url.url:
                reponame = self._fix_reponame(url.url)
                if reponame not in self._repos:
                    print(f"    Found repo {reponame}")
                    self._repos.append(reponame)
                username = self._fix_username(reponame)
                if username not in self._users:
                    print(f"    Found user {username}")
                    self._users.append(username)


    def _search_drafts(self) -> None:
        # Find GitHub repos in Internet-Drafts:
        # FIXME: to be implemented
        pass


    def _search_repos_for_users(self) -> None:
        for user in sorted(self._users):
            print(f"  Search GitHub repos for user {user}")
            for repo_data in gh.repos_for_user(user):
                if repo_data["name"].startswith("draft-") and repo_data["fork"] == False:
                    reponame = repo_data["html_url"]
                    if reponame not in self._repos:
                        print(f"    Found repo {reponame}")
                        self._repos.append(reponame)


    def find_ietf_github(self) -> None:
        """
        Search the DataTracker and Internet-drafts to locate the GitHub
        usernames and repositories mentioned; expand the search to find
        missing repositories named "draft-..." for those usernames.

        Both the IETF DataTracker and GitHub rate limit API access, so
        this method will be very slow if the data is not cached.
        """
        self._search_person_ext_resources()
        self._search_group_urls()
        self._search_document_urls()
        self._search_drafts()
        self._search_repos_for_users()


    def users(self) -> List[str]:
        """
        Retrieve the list of GitHub users found by find_ietf_github().

        This will return an empty list if find_ietf_github() has not
        been called.
        """
        return sorted(self._users)


    def repos(self) -> List[str]:
        """
        Retrieve the list of GitHub repos found by find_ietf_github().

        This will return an empty list if find_ietf_github() has not
        been called.
        """
        return sorted(self._repos)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python3 -m ietfdata.tools.download_gh_ietf archive/ietf-dt.sqlite archive/github.sqlite archive/ietf-gh.json")
        sys.exit(1)

    dt = DataTracker(DTBackendArchive(sys.argv[1]))
    gh = GitHub(sys.argv[2])

    gh_ietf = GitHubIETF(gh, dt)
    gh_ietf.find_ietf_github()

    gh_json = {"users": [],
               "repos": []}

    for user in gh_ietf.users():
        gh_json["users"].append(user)
    for repo in gh_ietf.repos():
        gh_json["repos"].append(repo)

    with open(sys.argv[3], "w") as outf:
        json.dump(gh_json, outf, indent=3)

    
