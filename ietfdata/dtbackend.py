# Copyright (C) 2025 University of Glasgow
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

import copy
import os
import logging
import pprint
import re
import requests
import requests_cache
import sqlite3
import sys
import time

from abc               import ABC, abstractmethod
from datetime          import date, datetime, timedelta, timezone
from typing            import List, Optional, Tuple, Dict, Iterator, Type, TypeVar, Any, Generic
from typing_extensions import Self

from ietfdata.datatracker_types import *

# =================================================================================================
# Base class

class DTBackend(ABC):
    @abstractmethod
    def __init__(self, sqlite_file : str) -> None:
        pass

    @abstractmethod
    def update(self) -> None:
        pass

    @abstractmethod
    def datatracker_get_single(self, obj_uri: URI) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def datatracker_get_multi(self, get_uri: URI, order_by: Optional[str] = None) -> Iterator[Dict[Any, Any]]:
        pass


# =================================================================================================
# Backend for live access to the datatracker:

class DTBackendLive(DTBackend):
    def __init__(self, sqlite_file : str = "ietfdata-dt-cache.sqlite") -> None:
        logging.getLogger('requests').setLevel('ERROR')
        logging.getLogger('requests_cache').setLevel('ERROR')
        logging.getLogger("urllib3").setLevel('ERROR')
        logging.basicConfig(level=os.getenv("IETFDATA_LOGLEVEL", default="INFO"))

        self.log       = logging.getLogger("ietfdata")
        self.ua        = "glasgow-ietfdata/0.9.0"          # Update when making a new relaase
        self.base_url  = os.environ.get("IETFDATA_DT_URL", "https://datatracker.ietf.org")
        self.cache     = requests_cache.SQLiteCache(sqlite_file)
        self.session   = requests_cache.CachedSession(backend=self.cache, expire_after=timedelta(hours=1))
        self.get_count = 0

        self.log.info(f"DTBackendLive at {self.base_url}")


    def update(self) -> None:
        self.cache.delete(expired=True)


    def datatracker_get_single(self, obj_uri: URI) -> Optional[Dict[str, Any]]:
        assert obj_uri.uri is not None
        retry_delay  = 1.875
        while True:
            try:
                req_url     = self.base_url + obj_uri.uri
                req_headers = {'User-Agent': self.ua}
                req_params  = obj_uri.params
                self.get_count += 1
                r = self.session.get(req_url, params = req_params, headers = req_headers, verify = True, stream = False)
                self.log.debug(f"datatracker_get_single in_cache={r.from_cache} cached={r.created_at} expires={r.expires} {req_url}")
                if r.status_code == 200:
                    self.log.debug(F"datatracker_get_single: ({r.status_code}) {obj_uri}")
                    url_obj = r.json() # type: Dict[str, Any]
                    return url_obj
                elif r.status_code == 404:
                    self.log.debug(F"datatracker_get_single: ({r.status_code}) {obj_uri}")
                    return None
                elif r.status_code == 429:
                    # Some versions of the datatracker incorrectly send 429 with "Retry-After: 0".
                    # Handle this with an exponential backoff as-if we got a 500 error.
                    retry_after = int(r.headers['Retry-After']) 
                    if retry_after != 0:
                        self.log.warning(F"datatracker_get_single: {r.status_code} {obj_uri} - retry in {retry_after}")
                        time.sleep(retry_after)
                    else:
                        self.log.warning(F"datatracker_get_single: {r.status_code} {obj_uri} - retry in {retry_delay}")
                        self.log.debug(r.headers)
                        if retry_delay > 60:
                            self.log.error(F"datatracker_get_single: retry limit exceeded")
                            sys.exit(1)
                        time.sleep(retry_delay)
                        retry_delay *= 2
                else:
                    self.log.warning(F"datatracker_get_single: {r.status_code} {obj_uri} - retry in {retry_delay}")
                    if retry_delay > 60:
                        self.log.error(F"datatracker_get_single: retry limit exceeded")
                        sys.exit(1)
                    time.sleep(retry_delay)
                    retry_delay *= 2
            except requests.exceptions.ConnectionError:
                self.log.warning(F"datatracker_get_single: connection error - retry in {retry_delay}")
                if retry_delay > 60:
                    self.log.error(F"datatracker_get_single: retry limit exceeded")
                    sys.exit(1)
                time.sleep(retry_delay)
                retry_delay *= 2


    def datatracker_get_multi(self, get_uri: URI, order_by: Optional[str] = None) -> Iterator[Dict[Any, Any]]:
        obj_uri = copy.deepcopy(get_uri)

        assert "order_by" not in obj_uri.params
        assert "limit"    not in obj_uri.params

        if order_by != None:
            obj_uri.params["order_by"] = order_by
        obj_uri.params[   "limit"] = 100

        total_count  = -1
        fetched_objs = {} # type: Dict[str, Dict[Any, Any]]
        while obj_uri.uri is not None:
            retry = True
            retry_delay = 1.875
            while retry:
                retry = False
                req_url     = self.base_url + obj_uri.uri
                req_params  = obj_uri.params
                req_headers = {'User-Agent': self.ua}
                try:
                    self.get_count += 1
                    r = self.session.get(url = req_url, params = req_params, headers = req_headers, verify = True, stream = False)
                    self.log.debug(f"datatracker_get_multi  in_cache={r.from_cache} cached={r.created_at} expires={r.expires} {obj_uri}")
                    if r.status_code == 200:
                        self.log.debug(F"datatracker_get_multi ({r.status_code}) {obj_uri}")
                        meta = r.json()['meta']
                        objs = r.json()['objects']
                        obj_uri  = URI(uri=meta['next'])
                        for obj in objs:
                            # API requests returning lists should never return duplicate
                            # objects, but due to datatracker bugs this sometimes happens.
                            # Check for and log such problems, but pass the duplicates up
                            # to the higher layers for reconcilition.
                            if obj["resource_uri"] in fetched_objs:
                                self.log.warning(F"datatracker_get_multi duplicate object {obj['resource_uri']}")
                            else:
                                fetched_objs[obj["resource_uri"]] = obj
                            yield obj
                        total_count = meta["total_count"]
                    elif r.status_code == 429:
                        # Some versions of the datatracker incorrectly send 429 with "Retry-After: 0".
                        # Handle this with an exponential backoff as-if we got a 500 error.
                        retry_after = int(r.headers['Retry-After']) 
                        if retry_after != 0:
                            self.log.warning(F"datatracker_get_multi: {r.status_code} {obj_uri} - retry in {retry_after}")
                            time.sleep(retry_after)
                        else:
                            self.log.warning(F"datatracker_get_multi: {r.status_code} {obj_uri} - retry in {retry_delay}")
                            self.log.debug(r.headers)
                            if retry_delay > 60:
                                self.log.error(F"datatracker_get_multi: retry limit exceeded")
                                sys.exit(1)
                            time.sleep(retry_delay)
                            retry_delay *= 2
                        retry = True
                    elif r.status_code == 500:
                        self.log.warning(F"datatracker_get_multi ({r.status_code}) {obj_uri}")
                        if retry_delay > 60:
                            self.log.info(F"datatracker_get_multi retry time exceeded")
                            sys.exit(1)
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        retry = True
                    else:
                        self.log.error(F"datatracker_get_multi ({r.status_code}) {obj_uri}")
                        sys.exit(1)
                except requests.exceptions.ConnectionError:
                    self.log.warning(F"datatracker_get_multi: connection error - will retry in {retry_delay}")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    retry = True
        if total_count != len(fetched_objs):
            self.log.warning(F"datatracker_get_multi: expected {total_count} objects but got {len(fetched_objs)}")


# =================================================================================================
# Backend for access to the datatracker via an offline archive:


class DTBackendArchive(DTBackend):
    def __init__(self, sqlite_file : str = "ietfdata.sqlite") -> None:
        logging.getLogger('requests').setLevel('ERROR')
        logging.getLogger("urllib3").setLevel('ERROR')
        logging.basicConfig(level=os.getenv("IETFDATA_LOGLEVEL", default="INFO"))

        self._log         = logging.getLogger("ietfdata")
        self._ua          = "glasgow-ietfdata/0.9.0 (archive)"     # Update when making a new relaase
        self._base_url    = os.environ.get("IETFDATA_DT_URL", "https://datatracker.ietf.org")
        self._multi_delay = 0.1
        self._session     = requests.Session()
        self._db          = sqlite3.connect(sqlite_file)
        self._db.execute('PRAGMA synchronous = OFF;')
        self._log.info(f"DTBackendArchive at {self._base_url} (multi_delay={self._multi_delay}s)")



    def _dt_fetch(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """
        Fetch the data for a single API endpoint from the datatracker:
        """
        retry_delay = 1.875
        while True:
            try:
                r = self._session.get(self._base_url + endpoint, headers={'User-Agent': self._ua}, verify=True, stream=False)
                self._log.debug(f"_dt_fetch: {r.status_code} {endpoint}")
                if r.status_code == 200:
                    res = r.json() # type: Dict[str,Any]
                    return res
                elif r.status_code == 400:
                    self._log.error(f"_dt_fetch: bad request {self._base_url}{endpoint}")
                    sys.exit(1)
                elif r.status_code == 404:
                    return None
                elif r.status_code == 429:
                    retry_after = int(r.headers['Retry-After']) 
                    if retry_after != 0:
                        self._log.warning(f"_dt_fetch: retry in {retry_after} (1)")
                        time.sleep(retry_after)
                        # Increase the delay between repeated fetches, to try to avoid
                        # rate limiting in future:
                        self._multi_delay *= 1.1
                        self._log.debug(f"_dt_fetch: multi_delay now {self._multi_delay}s")
                    else:
                        # Some versions of the datatracker incorrectly send 429 with "Retry-After: 0".
                        # Handle this with an exponential backoff as-if we got a 500 error.
                        self._log.warning(f"_dt_fetch: retry in {retry_delay} (2)")
                        if retry_delay > 60:
                            self._log.error(f"_dt_fetch: retry limit exceeded")
                            sys.exit(1)
                        time.sleep(retry_delay)
                        retry_delay *= 2
                else:
                    self._log.warning(f"_dt_fetch: retry in {retry_delay} (3)")
                    if retry_delay > 60:
                        self._log.error(f"_dt_fetch: retry limit exceeded")
                        sys.exit(1)
                    time.sleep(retry_delay)
                    retry_delay *= 2
            except requests.exceptions.ConnectionError:
                self._log.warning(F"_dt_fetch: retry in {retry_delay} - connection error")
                if retry_delay > 60:
                    self._log.error(f"_dt_fetch: retry limit exceeded")
                    sys.exit(1)
                time.sleep(retry_delay)
                retry_delay *= 2



    def _dt_fetch_multi(self, endpoint: str) -> Iterator[Dict[str, Any]]:
        uri = endpoint
        while uri is not None:
            r = self._dt_fetch(uri)
            if r is None:
                # Sometimes the datatracker will return a 404 error for a URL returned
                # in the r["meta"]["next"] field of the previous value. An example, at
                # the time of writing is /api/v1/review/historicalunavailableperiod/?limit=20&offset=300
                # This appears to be due to corrupt values in the database.
                # In the following, we attempt to correct for this, by fetching
                # the items in the query one-by-one, returning any that succeed.
                # If any succeed, we then construct an appropriate next URL and 
                # continue the multi fetch.
                if "?limit=" in uri and "&offset=" in uri:
                    self._log.warn(f"_dt_fetch_multi: cannot fetch {uri} - trying individual")
                    found_some = False
                    limit_pos  = uri.find("?limit=")
                    offset_pos = uri.find("&offset=")
                    base   = uri[:limit_pos-1]
                    limit  = int(uri[limit_pos+7:offset_pos])
                    offset = int(uri[offset_pos+8:])
                    for index in range(offset, offset+limit):
                        item_uri = f"{base}/?limit=1&offset={index}"
                        r = self._dt_fetch(item_uri)
                        if r is not None:
                            found_some = True
                            for obj in r["objects"]:
                                yield obj
                    if not found_some:
                        break
                    uri = f"{base}/?limit={limit}&offset={offset+limit}"
                else:
                    break
            else:
                for obj in r["objects"]:
                    yield obj
                uri = r["meta"]["next"]
            # Rate limit the fetch of large amounts of data
            time.sleep(self._multi_delay)



    def _fetch_schema(self, endpoint: str) -> Dict[str,Any]: 
        schema = self._dt_fetch(f"{endpoint}schema/")
        assert schema is not None

        result : Dict[str,Any] = {
            "endpoint"       : endpoint,
            "table"          : "ietf_dt" + endpoint.replace("/", "_")[7:-1],
            "sort_by"        : None,
            "columns"        : {}
        }
        if "ordering" in schema and schema["ordering"] is not None:
            result["sort_by"] = schema["ordering"][0]
        if "historical" in endpoint:
            result["sort_by"] = None
        for field_name in schema["fields"]:
            column = {}
            column["name"]     = field_name
            column["type"]     = schema["fields"][field_name]["type"]
            column["unique"]   = schema["fields"][field_name]["unique"]
            if column["type"] == "related":
                column["type"] = schema["fields"][field_name]["related_type"]
            result["columns"][field_name] = column
        return result



    def _fetch_schemas(self, endpoints) -> None:
        self._db.execute("""CREATE TABLE IF NOT EXISTS ietf_dt_schema (
                                endpoint    TEXT PRIMARY KEY,
                                table_name  TEXT,
                                sort_by     TEXT);""")

        self._db.execute("""CREATE TABLE IF NOT EXISTS ietf_dt_schema_columns (
                                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                                endpoint    TEXT NOT NULL,
                                column_name TEXT,
                                column_type TEXT,
                                FOREIGN KEY (endpoint) REFERENCES ietf_dt_schema (endpoint));""")

        for endpoint in endpoints:
            dbc = self._db.cursor()
            dbc.execute("SELECT COUNT(endpoint) FROM ietf_dt_schema WHERE endpoint = ?;", (endpoint, ))
            if int(dbc.fetchone()[0]) == 1:
                self._log.debug(f"_fetch_schemas: already got schema for {endpoint}")
                continue

            print(f"Fetch schema from datatracker: {endpoint}")

            schema = self._fetch_schema(endpoint)
            assert schema is not None

            sql1 = "INSERT INTO ietf_dt_schema VALUES (?, ?, ?);"
            val1 = (schema["endpoint"], schema["table"], schema["sort_by"])
            dbc.execute(sql1, val1)

            for column in schema["columns"].values():
                sql2 = "INSERT INTO ietf_dt_schema_columns VALUES (null, ?, ?, ?);"
                val2 = (schema["endpoint"], column["name"], column["type"])
                dbc.execute(sql2, val2)
            self._db.commit()



    def _create_tables(self, endpoints) -> None:
        for endpoint in endpoints:
            dbc = self._db.cursor()
            sql = "SELECT table_name FROM ietf_dt_schema WHERE endpoint = ?;"
            val = (endpoint, )
            table_name = dbc.execute(sql, val).fetchone()[0]

            columns   = []
            subtables = {}

            sql = "SELECT column_name, column_type FROM ietf_dt_schema_columns WHERE endpoint = ?;"
            val = (endpoint, )
            schema_columns = dbc.execute(sql, val).fetchall()

            for column_name, column_type in schema_columns:
                if column_name == "resource_uri":
                    primary = " PRIMARY KEY"
                else:
                    primary = ""

                if column_type == "integer":
                    columns.append(f"   \"{column_name}\" INTEGER{primary}")
                elif column_type == "boolean":
                    columns.append(f"   \"{column_name}\" INTEGER{primary}")
                elif column_type == "string":
                    columns.append(f"   \"{column_name}\" TEXT{primary}")
                elif column_type == "date":
                    columns.append(f"   \"{column_name}\" TEXT{primary}")
                elif column_type == "datetime":
                    columns.append(f"   \"{column_name}\" TEXT{primary}")
                elif column_type == "timedelta":
                    columns.append(f"   \"{column_name}\" TEXT{primary}")
                elif column_type == "to_one":
                    columns.append(f"   \"{column_name}\" TEXT{primary}")
                elif column_type == "to_many":
                    subtable  = f"CREATE TABLE IF NOT EXISTS {table_name}_{column_name} (\n"
                    subtable += f"   \"id\" INTEGER PRIMARY KEY AUTOINCREMENT,\n"
                    subtable += f"   \"_parent\" TEXT,\n"
                    subtable += f"   \"{column_name}\" TEXT,\n"
                    subtable += f"   FOREIGN KEY (_parent) REFERENCES {table_name} (resource_uri)\n"
                    subtable += f");"
                    subtables[f"{table_name}_{column_name}"] = subtable
                else:
                    print(f"ERROR: unknown column type: {column_type}")
                    sys.exit(1)

            self._log.debug(f"_create_tables: create table {table_name}")
            sql  = f"CREATE TABLE IF NOT EXISTS {table_name} (\n"
            sql += ",\n".join(columns)
            sql += f")"
            dbc.execute(sql, "")

            for table_name, subtable in subtables.items():
                self._log.debug(f"_create_tables: create table {table_name}")
                dbc.execute(subtable, "")
            self._db.commit()



    def _download_data(self, endpoints) -> None:
        for endpoint in endpoints:
            dbc = self._db.cursor()
            sql = "SELECT table_name, sort_by FROM ietf_dt_schema WHERE endpoint = ?;"
            val = (endpoint, )
            table_name, sort_by = dbc.execute(sql, val).fetchone()

            dbc.execute(f"SELECT COUNT(*) FROM {table_name};", ())
            if int(dbc.fetchone()[0]) > 0:
                self._log.debug(f"_download_data: already downloaded {endpoint}")
                continue

            print(f"Fetch content from datatracker: {endpoint}")

            columns = []
            to_many = []
            sql = "SELECT column_name, column_type FROM ietf_dt_schema_columns WHERE endpoint = ?"
            val = (endpoint, )
            for column_name, column_type in dbc.execute(sql, val).fetchall():
                if column_type == "to_many":
                    to_many.append(column_name)
                else:
                    columns.append(column_name)

            if sort_by is None:
                self._log.debug(f"_download_data: not sorting {endpoint}")
                uri = f"{endpoint}"
            else:
                if sort_by in columns or sort_by in to_many:
                    self._log.debug(f"_download_data: sorting {endpoint} by {sort_by}")
                    uri = f"{endpoint}?order_by={sort_by}"
                else:
                    self._log.debug(f"_download_data: not sorting {endpoint} - {sort_by} is not a column")
                    uri = f"{endpoint}"
            self._log.debug(f"_download_data: download {uri}")

            for item in self._dt_fetch_multi(uri):
                placeholders = ",".join(["?"] * len(columns))
                # The following should be INSERT INTO, but the datatracker occasionally
                # returns duplicate values so we use INSERT OR REPLACE INTO instead, to
                # avoid "UNIQUE constraint failed" errors from sqlite.
                sql = f"INSERT OR REPLACE INTO {table_name} VALUES ({placeholders});"
                col_val = []
                for column in columns:
                    col_val.append(item[column])
                dbc.execute(sql, col_val)

                for column in to_many:
                    for subitem in item[column]:
                        dbc.execute(f"INSERT INTO {table_name}_{column} VALUES (null, ?, ?);", (item["resource_uri"], subitem))
            self._db.commit()



    def update(self) -> None:
        endpoints_to_mirror = [
            "/api/v1/doc/ballotdocevent/",
            "/api/v1/doc/ballottype/",
            "/api/v1/doc/docevent/",
            "/api/v1/doc/document/",
            "/api/v1/doc/documentauthor/",
            "/api/v1/doc/documenturl/",
            "/api/v1/doc/relateddocument/",
            "/api/v1/doc/state/",
            "/api/v1/doc/statetype/",
            "/api/v1/group/changestategroupevent/",
            "/api/v1/group/group/",
            "/api/v1/group/groupevent/",
            "/api/v1/group/grouphistory/",
            "/api/v1/group/groupmilestone/",
            "/api/v1/group/groupmilestonehistory/",
            "/api/v1/group/groupurl/",
            "/api/v1/group/milestonegroupevent/",
            "/api/v1/group/role/",
            "/api/v1/group/rolehistory/",
            "/api/v1/ipr/genericiprdisclosure/",
            "/api/v1/ipr/holderiprdisclosure/",
            "/api/v1/ipr/iprdisclosurebase/",
            "/api/v1/ipr/thirdpartyiprdisclosure/",
            "/api/v1/meeting/meeting/",
            "/api/v1/meeting/schedtimesessassignment/",
            "/api/v1/meeting/schedule/",
            "/api/v1/meeting/schedulingevent/",
            "/api/v1/meeting/session/",
            "/api/v1/meeting/timeslot/",
            "/api/v1/name/ballotpositionname/",
            "/api/v1/name/continentname/",
            "/api/v1/name/countryname/",
            "/api/v1/name/docrelationshipname/",
            "/api/v1/name/doctagname/",
            "/api/v1/name/doctypename/",
            "/api/v1/name/docurltagname/",
            "/api/v1/name/extresourcename/",
            "/api/v1/name/extresourcetypename/",
            "/api/v1/name/groupmilestonestatename/",
            "/api/v1/name/groupstatename/",
            "/api/v1/name/grouptypename/",
            "/api/v1/name/iprdisclosurestatename/",
            "/api/v1/name/iprlicensetypename/",
            "/api/v1/name/meetingtypename/",
            "/api/v1/name/reviewassignmentstatename/",
            "/api/v1/name/reviewrequeststatename/",
            "/api/v1/name/reviewresultname/",
            "/api/v1/name/reviewtypename/",
            "/api/v1/name/rolename/",
            "/api/v1/name/sessionpurposename/",
            "/api/v1/name/sessionstatusname/",
            "/api/v1/name/streamname/",
            "/api/v1/person/alias/",
            "/api/v1/person/email/",
            "/api/v1/person/historicalemail/",
            "/api/v1/person/historicalperson/",
            "/api/v1/person/person/",
            "/api/v1/person/personevent/",
            "/api/v1/person/personextresource/",
            "/api/v1/review/historicalreviewassignment/",
            "/api/v1/review/historicalreviewersettings/",
            "/api/v1/review/historicalreviewrequest/",
            "/api/v1/review/historicalunavailableperiod/",
            "/api/v1/review/nextreviewerinteam/",
            "/api/v1/review/reviewassignment/",
            "/api/v1/review/reviewersettings/",
            "/api/v1/review/reviewrequest/",
            "/api/v1/review/reviewsecretarysettings/",
            "/api/v1/review/reviewteamsettings/",
            "/api/v1/review/reviewwish/",
            "/api/v1/review/unavailableperiod/",
            "/api/v1/stats/countryalias/",
            "/api/v1/stats/meetingregistration/",
            "/api/v1/submit/submission/",
            "/api/v1/submit/submissioncheck/",
            "/api/v1/submit/submissionevent/"
            ]

        self._fetch_schemas(endpoints_to_mirror)
        self._create_tables(endpoints_to_mirror)
        self._download_data(endpoints_to_mirror)



    def datatracker_get_single(self, obj_uri: URI) -> Optional[Dict[str, Any]]:
        assert obj_uri.uri is not None
        assert obj_uri.params == {}

        # Find the endpoint to fetch:
        split = obj_uri.uri.rfind("/", 0, -1) + 1
        endpoint = obj_uri.uri[:split]

        self._log.debug(f"datatracker_get_single: {endpoint}")

        # Find the table from which it will be fetched:
        dbc = self._db.cursor()
        sql = "SELECT table_name FROM ietf_dt_schema WHERE endpoint = ?;"
        val = (endpoint, )
        table_name = dbc.execute(sql, val).fetchone()[0]

        # Find the colums to extract and whether single or to_many
        columns = []
        to_one  = []
        to_many = []
        sql = "SELECT column_name, column_type FROM ietf_dt_schema_columns WHERE endpoint = ?"
        for column_name, column_type in dbc.execute(sql, (endpoint, )).fetchall():
            if column_type == "to_many":
                to_many.append(column_name)
            else:
                columns.append(column_name)
                if column_type == "to_one":
                    to_one.append(column_name)

        # Reconstruct single value fields in JSON
        result = {}
        sql    = f"SELECT "
        sql   += ", ".join(map(lambda x : f"\"{x}\"", columns))
        sql   += f" FROM {table_name} WHERE resource_uri = ?;"
        res1   = dbc.execute(sql, (obj_uri.uri, )).fetchone()
        if res1 is None:
            self._log.warn(f"datatracker_get_single: cannot find {obj_uri.uri} in database")
            return None
        for column_name, column_val in zip(columns, res1):
            result[column_name] = column_val

        # Reconstruct to_many fields in JSON
        for column in to_many:
            result[column] = []
            sql = f"SELECT {column} FROM {table_name}_{column} WHERE _parent = ?;"
            for res2 in dbc.execute(sql, (obj_uri.uri, )).fetchall():
                result[column].append(res2[0])

        return result



    def datatracker_get_multi(self, obj_uri: URI, order_by: Optional[str] = None) -> Iterator[Dict[Any, Any]]:
        assert obj_uri.uri is not None

        # Find the endpoint from which to fetch items:
        endpoint = obj_uri.uri

        self._log.debug(f"_datatracker_get_multi: {endpoint}")

        # Find the table from which they will be fetched:
        dbc = self._db.cursor()
        sql = "SELECT table_name FROM ietf_dt_schema WHERE endpoint = ?;"
        val = (endpoint, )
        table_name = dbc.execute(sql, val).fetchone()[0]

        # FIXME: This should built an appropriate index on the table if one does not exist

        # Find the colums to extract and whether they are single or to_many:
        columns = []
        to_one  = []
        to_many = []
        sql = "SELECT column_name, column_type FROM ietf_dt_schema_columns WHERE endpoint = ?"
        for column_name, column_type in dbc.execute(sql, (endpoint, )).fetchall():
            if column_type == "to_many":
                to_many.append(column_name)
            elif column_type == "to_one":
                to_one.append(column_name)
            else:
                columns.append(column_name)

        # Build the SQL query to select the items from the endpoint:
        sql  = f"SELECT "
        sql += ", ".join(map(lambda x : f"\"{x}\"", columns + to_one))
        sql += f" FROM {table_name}"
        param_names  = []
        param_values = []
        if len(obj_uri.params) > 0:
            sql += f" WHERE "
            for param_name, param_value in obj_uri.params.items():
                if param_name in columns:
                    param_names.append(f"\"{param_name}\" = ?")
                    param_values.append(param_value)
                elif param_name.endswith("__contains") and param_name[:-10] in columns:
                    param_names.append(f"\"{param_name[:-10]}\" LIKE ?")
                    param_values.append(f"%{param_value}%")
                elif param_name.endswith("__gt") and param_name[:-4] in columns:
                    param_names.append(f"\"{param_name[:-4]}\" > ?")
                    param_values.append(param_value)
                elif param_name.endswith("__gte") and param_name[:-5] in columns:
                    param_names.append(f"\"{param_name[:-5]}\" >= ?")
                    param_values.append(param_value)
                elif param_name.endswith("__lt") and param_name[:-4] in columns:
                    param_names.append(f"\"{param_name[:-4]}\" < ?")
                    param_values.append(param_value)
                elif param_name.endswith("__lte") and param_name[:-5] in columns:
                    param_names.append(f"\"{param_name[:-5]}\" <= ?")
                    param_values.append(param_value)
                elif param_name in to_one:
                    param_names.append(f"\"{param_name}\" LIKE ?")
                    # Several datatracker API endpoints allow querying documents, but
                    # take a document ID rather than a document name as their parameter.
                    # The value returned by the datatracker, that we store in the sqlite
                    # database, is however the document name. We use params_alt to allow
                    # DataTracker() class to pass in both the document ID and name.
                    if param_name in obj_uri.params_alt:
                        param_values.append(f"/api/v1/%/{obj_uri.params_alt[param_name]}/")
                    else:
                        param_values.append(f"/api/v1/%/{param_value}/")
                elif param_name in to_many:
                    raise RuntimeError(f"Not implmemented")
                else:
                    raise RuntimeError(f"Parameter references unknown column: {param_name}")
            sql += " AND ".join(param_names)
        sql += ";"

        # Reconstruct the JSON object
        for items in dbc.execute(sql, param_values).fetchall():
            result = {}
            for column_name, column_val in zip(columns + to_one, items):
                result[column_name] = column_val
            for column in to_many:
                result[column] = []
                sql = f"SELECT {column} FROM {table_name}_{column} WHERE _parent = ?;"
                for res2 in dbc.execute(sql, (obj_uri.uri, )).fetchall():
                    result[column].append(res2[0])
            yield result

