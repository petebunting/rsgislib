#!/usr/bin/env python
"""
The tools.wmts_tools module contains some useful tools for
working with WMTS tile services
"""
import os
import shutil
from typing import List

import rsgislib


def get_wmts_layer_list(wmts_url: str, name_filter: str = None) -> List[str]:
    """
    A function which uses the owslib module to retrieve the list of
    available layers from a WMTS service.

    :param wmts_url: the URL for the WMTS service.
    :param name_filter: an optional layer name filter the filter has to be found
                        within the layer name using the 'in' operator
                        (e.g., layers with 'visual' in layer_name)
    :return: list of layers names

    """
    import owslib.wmts

    wmts_obj = owslib.wmts.WebMapTileService(wmts_url)
    wmts_lyrs = list(wmts_obj.contents)
    if name_filter is not None:
        tmp_wmts_lyrs = list()
        for lyr in wmts_lyrs:
            if name_filter in lyr:
                tmp_wmts_lyrs.append(lyr)
        wmts_lyrs = tmp_wmts_lyrs
    wmts_obj = None
    return wmts_lyrs


def get_wmts_as_img(
    wmts_url: str,
    wmts_lyr: str,
    bbox: List[float],
    bbox_epsg: int,
    output_img: str,
    gdalformat="GTIFF",
    zoom_level: int = None,
    tmp_dir: str = None,
    wmts_epsg: int = None,
):
    """
    A function which retrieves an image (e.g., GTIFF) from a WMTS for a specified
    region of interest. Be care to ask for large areas at high zoom levels!

    Note, gdal will cache tiles which will be saved to a default path which
    can be defined using the GDAL_DEFAULT_WMS_CACHE_PATH variable.

    :param wmts_url: The url for the WMTS service
    :param wmts_lyr: the layer within the WMTS to use
    :param bbox: the bounding bbox for the region of interest [MinX, MaxX, MinY, MaxY]
    :param bbox_epsg: the EPSG code of the inputted bbox.
    :param output_img: the output image file path.
    :param gdalformat: the output image format.
    :param zoom_level: Optionally, the zoom level to be outputted.
    :param tmp_dir: Optionally, a temporary directory for some intermediate files.
                    If not specified, a tmp dir is created and removed in the local
                    path from where the script is run from.
    :param wmts_epsg: Provide the epsg code for the WMTS layer (probably 3857) if
                      the code can't automatically find it.

    """
    import xml.etree.ElementTree as ET

    from osgeo import gdal

    import rsgislib.imageutils
    import rsgislib.tools.geometrytools
    import rsgislib.tools.utils

    uid_str = rsgislib.tools.utils.uid_generator()
    create_tmp_dir = False
    if tmp_dir is None:
        tmp_dir = f"tmp_{uid_str}"
        if not os.path.exists(tmp_dir):
            os.mkdir(tmp_dir)
            create_tmp_dir = True

    gdal_lyr_url = f"WMTS:{wmts_url},layer={wmts_lyr}"
    out_tmp_xml = os.path.join(tmp_dir, f"wmts_tmp_xml_{uid_str}.xml")
    trans_opt = gdal.TranslateOptions(format="WMTS")
    gdal.Translate(out_tmp_xml, gdal_lyr_url, options=trans_opt)

    if wmts_epsg is None:
        wmts_epsg = rsgislib.imageutils.get_epsg_proj_from_img(out_tmp_xml)
    if wmts_epsg != bbox_epsg:
        wmts_bbox = rsgislib.tools.geometrytools.reproj_bbox_epsg(
            bbox, bbox_epsg, wmts_epsg
        )
    else:
        wmts_bbox = bbox

    tree = ET.parse(out_tmp_xml)
    gdal_wmts_tag = tree.getroot()
    if gdal_wmts_tag.tag != "GDAL_WMTS":
        raise rsgislib.RSGISPyException("Something has gone wrong: Root not GDAL_WMTS.")
    data_win_tag = gdal_wmts_tag.find("DataWindow")
    if data_win_tag is None:
        raise rsgislib.RSGISPyException("Something has gone wrong: No DataWindow tag.")
    ul_x_tag = data_win_tag.find("UpperLeftX")
    if ul_x_tag is None:
        raise rsgislib.RSGISPyException("Something has gone wrong: No UpperLeftX tag.")
    ul_y_tag = data_win_tag.find("UpperLeftY")
    if ul_y_tag is None:
        raise rsgislib.RSGISPyException("Something has gone wrong: No UpperLeftY tag.")
    lr_x_tag = data_win_tag.find("LowerRightX")
    if lr_x_tag is None:
        raise rsgislib.RSGISPyException("Something has gone wrong: No LowerRightX tag.")
    lr_y_tag = data_win_tag.find("LowerRightY")
    if lr_y_tag is None:
        raise rsgislib.RSGISPyException("Something has gone wrong: No LowerRightY tag.")

    ul_x_tag.text = f"{wmts_bbox[0]}"
    ul_y_tag.text = f"{wmts_bbox[3]}"
    lr_x_tag.text = f"{wmts_bbox[1]}"
    lr_y_tag.text = f"{wmts_bbox[2]}"

    if zoom_level is not None:
        zoom_lvl_tag = ET.Element("ZoomLevel")
        zoom_lvl_tag.text = f"{zoom_level}"
        gdal_wmts_tag.append(zoom_lvl_tag)

    ET.indent(tree, space="    ", level=0)

    out_sub_tmp_xml = os.path.join(tmp_dir, f"wmts_tmp_sub_xml_{uid_str}.xml")
    tree.write(out_sub_tmp_xml)

    # Create the output image file.
    if wmts_epsg != bbox_epsg:
        out_tmp_img = os.path.join(tmp_dir, f"tmp_out_img_{uid_str}.tif")
        rsgislib.imageutils.gdal_translate(out_sub_tmp_xml, out_tmp_img, "GTIFF")
        rsgislib.imageutils.gdal_warp(
            out_tmp_img,
            output_img,
            bbox_epsg,
            interp_method=rsgislib.INTERP_CUBIC,
            gdalformat=gdalformat,
            use_multi_threaded=False,
        )
    else:
        rsgislib.imageutils.gdal_translate(out_sub_tmp_xml, output_img, gdalformat)

    # Remove the XML files created.
    os.remove(out_tmp_xml)
    os.remove(out_sub_tmp_xml)

    # If created remove the tmp directory
    if create_tmp_dir:
        shutil.rmtree(tmp_dir)
