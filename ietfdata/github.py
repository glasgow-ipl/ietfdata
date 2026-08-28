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

import json
import logging
import os
import requests
import sys
import time

from dataclasses       import dataclass
from typing            import Any, Iterator
from typing_extensions import Self

@dataclass
class GHResponse:
    obj_json : list | dict
    next_uri : str | None


class GitHub:
    _log         : logging.Logger   # Private
    _session     : requests.Session # Private
    _ua          : str              # Private
    _multi_delay : float            # Private
    _base_url    : str              # Private


    def __init__(self) -> None:
        logging.getLogger('requests').setLevel('ERROR')
        logging.getLogger("urllib3").setLevel('ERROR')
        logging.basicConfig(level=os.getenv("IETFDATA_LOGLEVEL", default="INFO"))

        self._log      = logging.getLogger("ietfdata")
        self._session  = requests.Session()
        self._ua       = "glasgow-ietfdata/0.9.1" # Update when making a new release
        self._base_url = os.environ.get("IETFDATA_GH_URL", "https://api.github.com")
        self._token    = os.getenv("GITHUB_API_TOKEN", default=None)
        self._headers  = {}

        self._headers["User-Agent"] = self._ua
        self._headers["Accept"] = "application/vnd.github+json"
        self._headers["X-GitHub-Api-Version"] = "2026-03-10"

        if self._token is None:
            self._log.warning("Environment variable GITHUB_API_TOKEN is not set")
            self._log.warning("Rate limited to 60 requests/hour")
            self._multi_delay = 3600.0 / 60.0
        else:
            # Rate limit is 5000 requests/hour if authorised
            self._multi_delay = 3600.0 / 5000.0
            self._headers["Authorization"] = f"Bearer {self._token}"


    def _gh_fetch(self, endpoint: str) -> GHResponse:
        """
        Private helper method.
        Fetch data for a single API endpoint from GitHub.
        """
        retry_delay = 1.875
        while True:
            self._log.debug(f"_gh_fetch: {endpoint}")
            try:
                r = self._session.get(self._base_url + endpoint, headers=self._headers, verify=True)

                if r.status_code == 200:
                    self._log.debug(f"_gh_fetch: {r.status_code} {endpoint}")

                    obj_json = r.json()

                    if "next" not in r.links:
                        next_uri = None
                    else:
                        next_uri = r.links["next"]["url"]
                        if next_uri.startswith(self._base_url):
                            next_uri = next_uri[len(self._base_url):]

                    return GHResponse(obj_json, next_uri)
                elif r.status_code == 400:
                    self._log.error(f"_gh_fetch: {r.status_code} {endpoint}")
                    sys.exit(1)
                elif r.status_code == 403 or r.status_code == 404:
                    self._log.warning(f"_gh_fetch: {r.status_code} {endpoint}")
                    return GHResponse({}, None)
                elif r.status_code == 429:
                    retry_after = int(r.headers['Retry-After']) 
                    if retry_after != 0:
                        self._log.warning(f"_gh_fetch: {r.status_code} {endpoint} (retry in {retry_after}s)")
                        time.sleep(retry_after)
                        self._multi_delay *= 1.1
                    else:
                        # Handle "Retry-After: 0" with an exponential backoff.
                        self._log.warning(f"_gh_fetch: {r.status_code} {endpoint} (retry in {retry_delay})s (implicit)")
                        if retry_delay > 60:
                            self._log.error(f"_gh_fetch: retry limit exceeded")
                            sys.exit(1)
                        time.sleep(retry_delay)
                        retry_delay *= 2
                else:
                    self._log.warning(f"_gh_fetch: {r.status_code} {endpoint} (retry in {retry_delay}s)")
                    if retry_delay > 60:
                        self._log.error(f"_gh_fetch: retry limit exceeded")
                        sys.exit(1)
                    time.sleep(retry_delay)
                    retry_delay *= 2
            except requests.exceptions.ConnectionError:
                self._log.warning(f"_gh_fetch: connection error, will retry in {retry_delay}s")
                if retry_delay > 60:
                    self._log.error(f"_gh_fetch: retry limit exceeded")
                    sys.exit(1)
                time.sleep(retry_delay)
                retry_delay *= 2


    def _gh_fetch_multi(self, endpoint: str|None) -> Iterator[dict[str,Any]]:
        """
        Private helper method.
        Fetch data for multiple API endpoints from the datatracker.
        """
        self._log.debug(f"_gh_fetch_multi: {endpoint}")
        uri = endpoint
        while uri is not None:
            res = self._gh_fetch(uri)
            assert isinstance(res.obj_json, list)
            for obj in res.obj_json:
                yield obj
            uri = res.next_uri
            # Rate limit the fetch of large amounts of data
            time.sleep(self._multi_delay)


    # https://docs.github.com/en/rest/issues/issues?apiVersion=2026-03-10#list-repository-issues
    def issues(self, owner:str, repo:str) -> Iterator[dict[str,Any]]:
        for issue in self._gh_fetch_multi(f"/repos/{owner}/{repo}/issues?state=all"):
            yield issue


    # https://docs.github.com/en/rest/issues/comments?apiVersion=2026-03-10#list-issue-comments
    def comments_for_issue(self, owner:str, repo:str, issue:str) -> Iterator[dict[str,Any]]:
        for comment in self._gh_fetch_multi(f"/repos/{owner}/{repo}/issues/{issue}/comments"):
            yield comment


    # https://docs.github.com/en/rest/repos/repos?apiVersion=2026-03-10#get-a-user
    def user(self, username:str) -> dict[str,Any]:
        res = self._gh_fetch(f"/users/{username}")
        assert isinstance(res.obj_json, dict)
        return res.obj_json


    # https://docs.github.com/en/rest/repos/repos?apiVersion=2026-03-10#list-repositories-for-a-user
    def repos_for_user(self, username:str) -> Iterator[dict[str,Any]]:
        for repo in self._gh_fetch_multi(f"/users/{username}/repos"):
            yield repo


# vim: set tw=0 ai:
