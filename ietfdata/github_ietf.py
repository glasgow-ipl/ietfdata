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

import requests
import sys
import json

from pathlib  import Path

from ietfdata.datatracker import *
from ietfdata.github      import GitHub

class GitHubIETF(GitHub):
    _dt     : DataTracker
    _id_dir : str
    _users  : list[str]
    _repos  : list[dict[str,str]]

    def __init__(self, sqlite_file:str, dt:DataTracker, id_archive_dir:str):
        """
        The GitHubIETF class extends the GitHub class with methods to
        retrieve information about GitHub users and repositories used
        in the IETF.
        """
        super().__init__(sqlite_file)
        self._dt     = dt
        self._id_dir = id_archive_dir
        self._users  = []
        self._repos  = []
        Path(id_archive_dir).mkdir(exist_ok = True)


    def _add_username(self, username) -> None:
        if username not in self._users:
            gh_user = self.user(username)
            if gh_user is not None:
                print(f"    Found user {username}")
                self._users.append(username)


    def _add_reponame(self, repo_url) -> None:
        assert repo_url.startswith("https://github.com/")
        user = repo_url[19:repo_url.find("/", 19)]
        repo = repo_url[repo_url.rfind("/") + 1:]
        reponame = {"username": user, "reponame": repo, "url": repo_url}
        if reponame not in self._repos:
            print(f"    Found repo {repo_url}")
            self._repos.append(reponame)


    def _fix_username(self, username:str) -> str:
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
        elif username.startswith("http://") and username.endswith(".github.io/"):
            username = username[7:-11]
        elif username.startswith("https://") and username.endswith(".github.io/"):
            username = username[8:-11]
        elif username.startswith("https://") and username.endswith(".github.io"):
            username = username[8:-10]

        if "/" in username and not username.startswith("http"):
            username = username[:username.find("/")]
        if "?" in username:
            username = username[:username.find("?")]

        return username


    def _fix_reponame(self, reponame:str) -> str:
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
            rname = self._dt.ext_resource_name(resource.name).slug
            if rname == "github_username":
                username = self._fix_username(resource.value)
                if len(username) > 1:
                    self._add_username(username)
            if rname == "github_repo":
                if resource.value.startswith("https://github.com/"):
                    url_stem = resource.value[19:]
                    username = self._fix_username(url_stem[:url_stem.find("/")])
                    self._add_username(username)


    def _search_group_urls(self) -> None:
        print("  Search for GitHub data in group_urls()")
        for url in self._dt.group_urls():
            if "github" in url.url:
                username = self._fix_username(url.url)
                self._add_username(username)


    def _search_document_urls(self) -> None:
        print("  Search for GitHub data in document_urls()")
        for url in self._dt.document_urls():
            if "github" in url.url:
                reponame = self._fix_reponame(url.url)
                self._add_reponame(reponame)
                username = self._fix_username(reponame)
                self._add_username(username)


    def _download_drafts(self) -> list[str]:
        """
        Fetch the latest revisions of all Internet-drafts and save into
        `self._id_dir`.
        """
        print("  Download Internet-drafts")
        session = requests.Session()
        paths   = []
        width   = 80

        for doc in dt.documents(doctype = dt.document_type_from_slug("draft")):
            if doc.submissions == []:
                # Drafts without submissions cannot be downloaded
                continue

            draft_name = doc.name
            draft_rev  = "00"
            for submission_uri in doc.submissions:
                submission = dt.submission(submission_uri)
                if submission.rev >= draft_rev:
                    draft_name = submission.name
                    draft_rev  = submission.rev

            url  = f"https://www.ietf.org/archive/id/{draft_name}-{draft_rev}.txt"
            path = f"{self._id_dir}/{draft_name}-{draft_rev}.txt"

            if Path(path).exists():
                paths.append(path)
            else:
                response = session.get(url, verify=True, stream=False)
                if response.status_code == 200:
                    print(f"\r    200 {url:{width}s}", end="")
                    with open(path, "wb") as outf:
                        outf.write(response.content)
                    paths.append(path)
                elif response.status_code == 404:
                    print(f"\r    404 {url:{width}s}")
                else:
                    print(f"\r    {response.status_code:3} {url:{width}s}")
                    sys.exit(1)
                width = len(url) + 4
        return paths


    def _search_drafts(self) -> None:
        # Find GitHub repos in Internet-Drafts:
        paths = self._download_drafts()
        print("  Search for GitHub data in Internet-drafts")
        for path in paths:
            try:
                with open(path, "r") as inf:
                    lines = list(inf.readlines())
                for index in range(0, len(lines)):
                    line = lines[index]
                    if "Source for this draft and an issue tracker can be found at" in line.strip():
                        # FIXME: handle cases where the URL is split across two lines
                        repo_url = lines[index+1].strip()
                        finish   = repo_url.find(" ")
                        repo_url = repo_url[:finish].rstrip(".")
                        if repo_url.startswith("https://github.com/"):
                            self._add_reponame(self._fix_reponame(repo_url))
                            self._add_username(self._fix_username(repo_url))
            except KeyboardInterrupt:
                return
            except:
                print(f"    Cannot parse {path}")


    def _search_repos_for_users(self) -> None:
        for user in sorted(self._users):
            print(f"  Search for drafts in GitHub repos of user {user}")
            for repo_data in self.repos_for_user(user):
                if repo_data["name"].startswith("draft-") and repo_data["fork"] == False:
                    reponame = repo_data["html_url"]
                    self._add_reponame(reponame)


    def find_repositories(self) -> None:
        """
        Search the DataTracker and Internet-drafts to locate the GitHub
        usernames and repositories mentioned; expand the search to find
        missing repositories named "draft-..." for those usernames.

        Both the IETF DataTracker and GitHub rate limit API access, so
        this method will be very slow if the data is not cached in the
        `sqlite_file` specified when instantiating this class.
        """
        self._search_person_ext_resources()
        self._search_group_urls()
        self._search_document_urls()
        self._search_drafts()
        self._search_repos_for_users()


    def users(self) -> list[str]:
        """
        Retrieve the list of GitHub users relating to the IETF.

        This will return an empty list if `find_repositories()` has not
        previously been called.
        """
        return sorted(self._users)


    def repos(self) -> list[dict[str,str]]:
        """
        Retrieve the list of GitHub repos relating to the IETF.

        This will return an empty list if `find_repositories()` has not
        previously been called.
        """
        return self._repos


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python3 -m ietfdata.github_ietf archive/ietf-dt.sqlite archive/github.sqlite archive/ietf-gh.json")
        sys.exit(1)

    dt = DataTracker(DTBackendArchive(sys.argv[1]))
    gh_ietf = GitHubIETF(sys.argv[2], dt, "archive/ietf-drafts")
    gh_ietf.find_repositories()

    gh_users = []
    gh_repos = {}

    for user in gh_ietf.users():
        gh_users.append(user)
    for owner, repo, url in gh_ietf.repos():
        gh_repos[url] = {"owner": owner, "repo": repo, "url": url}

    gh_json = {"users": gh_users, "repos": gh_repos}

    with open(sys.argv[3], "w") as outf:
        json.dump(gh_json, outf, indent=3)

