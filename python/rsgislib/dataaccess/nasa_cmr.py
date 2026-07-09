#!/usr/bin/env python
"""
Tools for accessing (searching and downloading) datasets from the NASA
EOSDIS Common Metadata Repository API (https://cmr.earthdata.nasa.gov/search/)

"""

import datetime
import os
from typing import Dict, List, Union

import requests
import requests.utils

import rsgislib
import rsgislib.tools.httptools
import rsgislib.tools.utils

# CMR_OPS = "https://cmr.earthdata.nasa.gov/search/"
# CMR_UAT = "https://cmr.uat.earthdata.nasa.gov/search/"
# CMR_SIT = "https://cmr.sit.earthdata.nasa.gov/search/"

CMR_COLLECTS_URL = "https://cmr.earthdata.nasa.gov/search/collections.json"
CMR_GRANULES_URL = "https://cmr.earthdata.nasa.gov/search/granules.json"


class SessionWithHeaderNASARedirection(requests.Session):
    AUTH_HOST = "urs.earthdata.nasa.gov"

    def __init__(self, username, password):
        super().__init__()
        self.auth = (username, password)

    def rebuild_auth(self, prepared_request, response):
        """
        Overrides from the library to keep headers when redirected to or from
        the NASA auth host.

        :param prepared_request:
        :param response:
        :return:
        """
        headers = prepared_request.headers
        url = prepared_request.url

        if "Authorization" in headers:
            original_parsed = requests.utils.urlparse(response.request.url)
            redirect_parsed = requests.utils.urlparse(url)
            if (
                (original_parsed.hostname != redirect_parsed.hostname)
                and redirect_parsed.hostname != self.AUTH_HOST
                and original_parsed.hostname != self.AUTH_HOST
            ):
                del headers["Authorization"]

        return


def _check_cmr_response(data: Dict) -> Union[str, List, Dict]:
    """
    A function which checks the response for an error (producing an exception)
    and extracts the text output and returns it.

    :param data:
    :return:

    """

    if not rsgislib.tools.utils.dict_struct_does_path_exist(data, ["feed", "entry"]):
        print(data)
        raise rsgislib.RSGISPyException("Data structure is not as expected - check.")

    return data["feed"]["entry"]


def get_prods_info(prod_short_name: str) -> List[Dict]:
    """
    A function which returns information for a product available from the CMR.

    Available products can be found here:
    https://earthdata.nasa.gov/eosdis/science-system-description/eosdis-standard-products

    :param prod_short_name: The name of the product you are interested in.
    :return: A list of products (probably different versions).

    """
    prod_srch_params = {"short_name": prod_short_name}
    header_info = {"Accept": "application/json"}

    rtnd_data = rsgislib.tools.httptools.send_http_json_request(
        CMR_COLLECTS_URL,
        data=prod_srch_params,
        convert_to_json=False,
        header_data=header_info,
    )
    prod_lst = _check_cmr_response(rtnd_data)

    return prod_lst


def check_prod_version_avail(prod_short_name: str, version: str) -> bool:
    """
    A function which checks if a version is available.

    :param prod_short_name: the product short name for the product of interest.
    :param version: the version of the product to be retrieved.
    :return: Boolean specifying whether the version is available.

    """
    prod_lst = get_prods_info(prod_short_name)
    found_version = False
    for prod in prod_lst:
        if prod["version_id"] == version:
            found_version = True
            break
    return found_version


def get_max_prod_version(prod_short_name: str) -> str:
    """
    A function which attempts to find the highest (latest) version for
    a product.

    :param prod_short_name: the product short name for the product of interest.
    :return: string representation of the highest version.

    """
    prod_lst = get_prods_info(prod_short_name)
    first = True
    max_version_int = 0
    max_version = ""
    for prod in prod_lst:
        version_int = int(prod["version_id"])
        if first:
            max_version_int = version_int
            max_version = prod["version_id"]
            first = False
        elif version_int > max_version_int:
            max_version_int = version_int
            max_version = prod["version_id"]
    return max_version


def find_granules(
    prod_short_name: str,
    version: str,
    only_dnwld: bool = True,
    bbox: List[float] = None,
    pt: List[float] = None,
    start_date: datetime.datetime = None,
    end_date: datetime.datetime = None,
    cloud_min: int = 0,
    cloud_max: int = None,
    sort_date: bool = True,
    sort_desc: bool = True,
    page_size: int = 100,
    page_num: int = 1,
    other_params: Dict[str, str] = None,
) -> List[Dict]:
    """
    A function which will find granules from the CMR system for the product of
    interest using the search parameters provided.

    https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html#granule-search-by-parameters

    :param prod_short_name: the product short name for the product of interest.
    :param version: the version of the product to be retrieved.
    :param only_dnwld: If true (default)
    :param bbox: (MinX, MaxX, MinY, MaxY)
    :param pt: (X, Y)
    :param start_date: Start date as a datetime object. (Earlier date)
    :param end_date: End date as a datetime object. (Later date)
    :param cloud_min: Minimum cloud cover (Default: 0)
    :param cloud_max: Maximum cloud cover.
    :param sort_date: Sort the response by the acquisition date
    :param sort_desc: Sort order (ascending or descending). Ascending: oldest version.
                      Descending: newest version.
    :param page_size: The number of records to be returned by a single query as a
                      'page'.
    :param page_num: The page number to be retrieved allowing results greater than
                     the number which will fit on a single page to be retrieved.
    :param other_params: A dict of other parameters where the key is the search
                         parameter name and the value is the value to search with.
    :return: A list of dictionaries with a dictionary for item.
    """

    prod_srch_params = {"short_name": prod_short_name, "version": version}
    header_info = {"Accept": "application/json"}

    prod_srch_params["page_size"] = page_size
    prod_srch_params["page_num"] = page_num

    if only_dnwld:
        prod_srch_params["downloadable"] = True

    if (start_date is not None) or (end_date is not None):
        start_date_str = ""
        if start_date is not None:
            start_date_str = start_date.strftime("%Y-%m-%dT00:00:00Z")

        end_date_str = ""
        if end_date is not None:
            end_date_str = end_date.strftime("%Y-%m-%dT00:00:00Z")

        prod_srch_params["temporal"] = f"{start_date_str},{end_date_str}"

    if (cloud_min > 0) or (cloud_max is not None):
        cloud_min_str = ""
        if cloud_min > 0:
            cloud_min_str = f"{cloud_min}"

        cloud_max_str = ""
        if cloud_max is not None:
            cloud_max_str = f"{cloud_max}"

        prod_srch_params["cloud_cover"] = f"{cloud_min_str},{cloud_max_str}"

    if pt is not None:
        pt_str = "{},{}".format(pt[0], pt[1])
        prod_srch_params["point"] = pt_str
    elif bbox is not None:
        bbox_str = "{},{},{},{}".format(bbox[0], bbox[2], bbox[1], bbox[3])
        prod_srch_params["bounding_box"] = bbox_str

    if sort_date:
        if sort_desc:
            prod_srch_params["sort_key"] = "-start_date"
        else:
            prod_srch_params["sort_key"] = "%2Bstart_date"

    if other_params is not None:
        prod_srch_params = {**prod_srch_params, **other_params}

    rtnd_data = rsgislib.tools.httptools.send_http_json_request(
        CMR_GRANULES_URL,
        data=prod_srch_params,
        convert_to_json=False,
        header_data=header_info,
    )
    granules_lst = _check_cmr_response(rtnd_data)

    return granules_lst


def find_all_granules(
    prod_short_name: str,
    version: str,
    only_dnwld: bool = True,
    bbox: List[float] = None,
    pt: List[float] = None,
    start_date: datetime.datetime = None,
    end_date: datetime.datetime = None,
    cloud_min: int = 0,
    cloud_max: int = None,
    sort_date: bool = True,
    sort_desc: bool = True,
    page_size: int = 100,
    max_n_pages: int = 100,
    other_params: Dict[str, str] = None,
) -> List[Dict]:
    """
    A function which will find granules from the CMR system for the product of
    interest using the search parameters provided using the find_granules function
    but iterates through all the pages available to return all the available
    granules rather than just a single page.

    :param prod_short_name: the product short name for the product of interest.
    :param version: the version of the product to be retrieved.
    :param only_dnwld: If true (default)
    :param bbox: (MinX, MaxX, MinY, MaxY)
    :param pt: (X, Y)
    :param start_date: Start date as a datetime object. (Earlier date)
    :param end_date: End date as a datetime object. (Later date)
    :param cloud_min: Minimum cloud cover (Default: 0)
    :param cloud_max: Maximum cloud cover.
    :param sort_date: Sort the response by the acquisition date
    :param sort_desc: Sort order (ascending or descending). Ascending: oldest version.
                      Descending: newest version.
    :param page_size: The number of records to be returned by a single query as a
                      'page'. (Default: 100)
    :param max_n_pages: the maximum number of pages returned (Default: 100)
    :param other_params: A dict of other parameters where the key is the search
                         parameter name and the value is the value to search with.
    :return: A list of dictionaries with a dictionary for item.
    """
    import tqdm

    rtn_granules = list()
    print("Note. Progress bar is for the maximum number of pages...")
    print("Hopefully you do not need the maximum so it will be quicker...")
    for i in tqdm.tqdm(range(max_n_pages)):
        page_granules = find_granules(
            prod_short_name=prod_short_name,
            version=version,
            only_dnwld=only_dnwld,
            bbox=bbox,
            pt=pt,
            start_date=start_date,
            end_date=end_date,
            cloud_min=cloud_min,
            cloud_max=cloud_max,
            sort_date=sort_date,
            sort_desc=sort_desc,
            page_size=page_size,
            page_num=i + 1,
            other_params=other_params,
        )
        if len(page_granules) > 0:
            rtn_granules += page_granules
        else:
            break

    return rtn_granules


def get_total_file_size(granule_lst: List[Dict]) -> float:
    """
    A function which using the list granules to sum the total file
    size of the granules in the list. The file size units are whatever
    has been use for the product but seems to be usually be MegaBytes (MB).

    :param granule_lst: List of granules from find_granules or find_all_granules
    :return: float for the total file size.

    """
    tot_file_size = 0.0
    for granule in granule_lst:
        tot_file_size += float(granule["granule_size"])
    return tot_file_size


def create_cmr_dwnld_db(
    db_json: str,
    granule_lst: List[Dict],
    dwnld_file_mime_type: str = None,
    file_ext: str = None,
    dwnld_protocol: str = "http",
) -> List[str]:
    """
    A function which iterates through a granule list and builds a json database
    of file to be downloaded. The database can then be used to keep track of
    which files have been successfully downloaded allowing those which haven't
    downloaded to be tried again.

    For the mine types, print a few of the granule list of the terminal (i.e.,
    pprint.pprint(granule_lst) and check what the mime type is for the download
    you want. However, for GEDI data it is probably application/x-hdfeos.

    :param db_json: The file path for the databases JSON file.
    :param granule_lst: List of granules from find_granules or find_all_granules
    :param dwnld_file_mime_type: (e.g., application/x-hdfeos, application/x-hdf) if
                                 None then no mime type filtering will be applied but
                                 the file extension is expected to be used instead.
    :param file_ext: (e.g., .h5, .hdf) if None then no file extension filtering will
                     be applied and only applied if dwnld_file_mime_type has not
                     been specified.
    :param dwnld_protocol: (e.g., http, https, s3) if None then no protocol filtering
                           will be applied.
    :return: a List of producer_granule_id's for the granules where a
             URL could not be found.

    """
    import pysondb
    import tqdm
    import pprint
    import os

    db_data = []
    granules_no_url = []
    for granule in tqdm.tqdm(granule_lst):
        id_val = granule["id"]
        if ("producer_granule_id" in granule) or ("title" in granule):
            if "producer_granule_id" in granule:
                producer_granule_id = granule["producer_granule_id"]
            elif "title" in granule:
                producer_granule_id = granule["title"]
            else:
                raise Exception("No producer_granule_id or title found in granule")
            granule_size = granule["granule_size"]
            found_url = False
            for link in granule["links"]:
                if dwnld_file_mime_type is not None:
                    if "type" in link:
                        if link["type"] == dwnld_file_mime_type:
                            if dwnld_protocol is not None:
                                if dwnld_protocol in link["href"]:
                                    granule_url = link["href"]
                                    found_url = True
                                    break
                            else:
                                granule_url = link["href"]
                                found_url = True
                                break
                elif file_ext is not None:
                    tmp_file_ext = os.path.splitext(link["href"])[1]
                    if tmp_file_ext == file_ext:
                        if dwnld_protocol is not None:
                            if dwnld_protocol in link["href"]:
                                granule_url = link["href"]
                                found_url = True
                                break
                        else:
                            granule_url = link["href"]
                            found_url = True
                            break
            if found_url:
                db_data.append(
                    {
                        "id": id_val,
                        "producer_granule_id": producer_granule_id,
                        "granule_size": granule_size,
                        "granule_url": granule_url,
                        "lcl_path": "",
                        "downloaded": False,
                    }
                )
            else:
                granules_no_url.append(producer_granule_id)
        else:
            granules_no_url.append(producer_granule_id)

    lst_db = pysondb.getDb(db_json)
    if len(db_data) > 0:
        lst_db.addMany(db_data)
    return granules_no_url


def cmr_download_file_http(
    input_url: str,
    out_file_path: str,
    username: str,
    password: str,
    no_except: bool = True,
) -> bool:
    """

    :param input_url: The input remote URL to be downloaded.
    :param out_file_path: the local file path and file name
    :param username: the username for the server
    :param password: the password for the server
    :return: boolean as to whether the file was successfully downloaded or not.

    """
    import tqdm

    import rsgislib.tools.httptools

    session_http = SessionWithHeaderNASARedirection(username, password)

    user_agent = "rsgislib/{}".format(rsgislib.get_rsgislib_version())
    session_http.headers["User-Agent"] = user_agent

    tmp_dwnld_path = out_file_path + ".incomplete"

    headers = {}

    try:
        with session_http.get(input_url, stream=True, headers=headers) as r:
            if rsgislib.tools.httptools.check_http_response(r, input_url):
                total = int(r.headers.get("content-length", 0))
                chunk_size = 2**20
                n_chunks = int(total / chunk_size) + 1

                with open(tmp_dwnld_path, "wb") as f:
                    for chunk in tqdm.tqdm(
                        r.iter_content(chunk_size=chunk_size), total=n_chunks
                    ):
                        if chunk:  # filter out keep-alive new chunks
                            f.write(chunk)
        if os.path.exists(tmp_dwnld_path):
            os.rename(tmp_dwnld_path, out_file_path)
            print("Download Complete: {}".format(out_file_path))

    except Exception as e:
        if no_except:
            print(e)
        else:
            raise rsgislib.RSGISPyException("{}".format(e))
        return False
    return True


def download_granules_use_dwnld_db(
    db_json: str, out_path: str, user_pass_file: str, use_wget: bool = False
):
    """
    A function which can use the JSON database built by create_cmr_dwnld_db to
    batch download a set of files keeping track of those which where successfully
    downloaded and those that were unsuccessful.

    :param db_json: file path for the JSON db file.
    :param out_path: the output path where data should be downloaded to.
    :param user_pass_file: path to an encoded (base64) username/password file
    :param use_wget: boolean as to whether to use wget to download files or
                     a pure python function. (Default: False - i.e., pure python).

    """
    import pysondb

    import rsgislib.tools.httptools
    import rsgislib.tools.utils

    username, password = rsgislib.tools.utils.get_username_password(user_pass_file)

    lst_db = pysondb.getDb(db_json)

    dwld_files = lst_db.getByQuery({"downloaded": False})

    for dwn_file in dwld_files:
        out_file_path = os.path.join(out_path, dwn_file["producer_granule_id"])
        print(f"Downloading: {out_file_path}")
        dwn_success = False
        if use_wget:
            dwn_success, dwn_message = rsgislib.tools.httptools.wget_download_file(
                input_url=dwn_file["granule_url"],
                out_file_path=out_file_path,
                username=username,
                password=password,
            )
        else:
            dwn_success = cmr_download_file_http(
                input_url=dwn_file["granule_url"],
                out_file_path=out_file_path,
                username=username,
                password=password,
            )

        if dwn_success:
            lst_db.updateById(
                dwn_file["id"], {"lcl_path": out_file_path, "downloaded": True}
            )
