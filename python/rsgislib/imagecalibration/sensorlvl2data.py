#!/usr/bin/env python
############################################################################
#  sensorlvl2data.py
#
#  Copyright 2021 RSGISLib.
#
#  RSGISLib: 'The remote sensing and GIS Software Library'
#
#  RSGISLib is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  RSGISLib is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with RSGISLib.  If not, see <http://www.gnu.org/licenses/>.
#
#
# Purpose: Provide a set of utilities for using downloaded level 2 data
#          from data providers in an easy manner.
#
# Author: Pete Bunting
# Email: petebunting@mac.com
# Date: 10/10/2021
# Version: 1.0
#
# History:
# Version 1.0 - Created.
#
############################################################################

import os

import numpy

import rsgislib
import rsgislib.tools.sensors

TQDM_AVAIL = True
try:
    import tqdm
except ImportError:
    import rios.cuiprogress

    TQDM_AVAIL = False


def create_stacked_sref_ls_oli_cl2_lv2_img(
    input_file: str,
    out_dir: str,
    tmp_dir: str,
    scale_factor: int = 10000,
    gdalformat: str = "GTIFF",
    delete_inter_data: bool = True,
    inc_full_qa_pxl_img: bool = False,
):
    """
    A function which extracts the USGS collection-2 level-2 data and creates a single
    multi-band image file in the output directory. Note the output data type is
    32bit integer and the no data value is -9999. A cloud mask and valid area images
    are also provided and extracted from the pixel QA image provided in the collection
    2 package.  Note this function just works for Landsat 8 and 9 data.

    :param input_file: file name and path to the input TAR file.
    :param out_dir: output directory where the output file will be written.
    :param tmp_dir: a temporary directory where intermediate files will be written.
    :param scale_factor: the scale factor applied to the output reflectance values.
                         default is 10,000
    :param gdalformat: the output file format.
    :param delete_inter_data: delete any intermediate files created is True (Default)
    :param inc_full_qa_pxl_img: Include the full pixel QA image split into individual
                                bands in the output.

    .. code:: python

        from rsgislib.imagecalibration.sensorlvl2data import create_stacked_sref_ls_oli_cl2_lv2_img
        create_stacked_sref_ls_oli_cl2_lv2_img("LC08_L2SP_135046_20210319_20210328_02_T1.tar", "outputs", "tmp", gdalformat="GTIFF")

    """

    import rsgislib.imagecalc
    import rsgislib.imageutils
    import rsgislib.rastergis
    import rsgislib.tools.filetools
    import rsgislib.tools.utils

    if not os.path.exists(out_dir):
        os.mkdir(out_dir)

    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)

    if gdalformat == "GTIFF":
        rsgislib.imageutils.set_env_vars_lzw_gtiff_outs()

    raw_dir = rsgislib.tools.filetools.untar_file(input_file, tmp_dir)

    mtl_header = rsgislib.tools.filetools.find_file_none(raw_dir, "*MTL.txt")

    if mtl_header is None:
        raise rsgislib.RSGISPyException("Could not find the MTL header")

    ls8_head_info = rsgislib.tools.sensors.read_landsat_mtl_to_dict(mtl_header)

    ls_prod_id = rsgislib.tools.utils.dict_struct_get_str_value(
        ls8_head_info, ["PRODUCT_CONTENTS", "LANDSAT_PRODUCT_ID"]
    ).lower()

    b1_img = rsgislib.tools.utils.dict_struct_get_str_value(
        ls8_head_info, ["PRODUCT_CONTENTS", "FILE_NAME_BAND_1"]
    )
    b2_img = rsgislib.tools.utils.dict_struct_get_str_value(
        ls8_head_info, ["PRODUCT_CONTENTS", "FILE_NAME_BAND_2"]
    )
    b3_img = rsgislib.tools.utils.dict_struct_get_str_value(
        ls8_head_info, ["PRODUCT_CONTENTS", "FILE_NAME_BAND_3"]
    )
    b4_img = rsgislib.tools.utils.dict_struct_get_str_value(
        ls8_head_info, ["PRODUCT_CONTENTS", "FILE_NAME_BAND_4"]
    )
    b5_img = rsgislib.tools.utils.dict_struct_get_str_value(
        ls8_head_info, ["PRODUCT_CONTENTS", "FILE_NAME_BAND_5"]
    )
    b6_img = rsgislib.tools.utils.dict_struct_get_str_value(
        ls8_head_info, ["PRODUCT_CONTENTS", "FILE_NAME_BAND_6"]
    )
    b7_img = rsgislib.tools.utils.dict_struct_get_str_value(
        ls8_head_info, ["PRODUCT_CONTENTS", "FILE_NAME_BAND_7"]
    )

    qa_pxl_img = rsgislib.tools.utils.dict_struct_get_str_value(
        ls8_head_info, ["PRODUCT_CONTENTS", "FILE_NAME_QUALITY_L1_PIXEL"]
    )

    b1_multi = rsgislib.tools.utils.dict_struct_get_numeric_value(
        ls8_head_info,
        ["LEVEL2_SURFACE_REFLECTANCE_PARAMETERS", "REFLECTANCE_MULT_BAND_1"],
    )
    b2_multi = rsgislib.tools.utils.dict_struct_get_numeric_value(
        ls8_head_info,
        ["LEVEL2_SURFACE_REFLECTANCE_PARAMETERS", "REFLECTANCE_MULT_BAND_2"],
    )
    b3_multi = rsgislib.tools.utils.dict_struct_get_numeric_value(
        ls8_head_info,
        ["LEVEL2_SURFACE_REFLECTANCE_PARAMETERS", "REFLECTANCE_MULT_BAND_3"],
    )
    b4_multi = rsgislib.tools.utils.dict_struct_get_numeric_value(
        ls8_head_info,
        ["LEVEL2_SURFACE_REFLECTANCE_PARAMETERS", "REFLECTANCE_MULT_BAND_4"],
    )
    b5_multi = rsgislib.tools.utils.dict_struct_get_numeric_value(
        ls8_head_info,
        ["LEVEL2_SURFACE_REFLECTANCE_PARAMETERS", "REFLECTANCE_MULT_BAND_5"],
    )
    b6_multi = rsgislib.tools.utils.dict_struct_get_numeric_value(
        ls8_head_info,
        ["LEVEL2_SURFACE_REFLECTANCE_PARAMETERS", "REFLECTANCE_MULT_BAND_6"],
    )
    b7_multi = rsgislib.tools.utils.dict_struct_get_numeric_value(
        ls8_head_info,
        ["LEVEL2_SURFACE_REFLECTANCE_PARAMETERS", "REFLECTANCE_MULT_BAND_7"],
    )

    b1_add = rsgislib.tools.utils.dict_struct_get_numeric_value(
        ls8_head_info,
        ["LEVEL2_SURFACE_REFLECTANCE_PARAMETERS", "REFLECTANCE_ADD_BAND_1"],
    )
    b2_add = rsgislib.tools.utils.dict_struct_get_numeric_value(
        ls8_head_info,
        ["LEVEL2_SURFACE_REFLECTANCE_PARAMETERS", "REFLECTANCE_ADD_BAND_2"],
    )
    b3_add = rsgislib.tools.utils.dict_struct_get_numeric_value(
        ls8_head_info,
        ["LEVEL2_SURFACE_REFLECTANCE_PARAMETERS", "REFLECTANCE_ADD_BAND_3"],
    )
    b4_add = rsgislib.tools.utils.dict_struct_get_numeric_value(
        ls8_head_info,
        ["LEVEL2_SURFACE_REFLECTANCE_PARAMETERS", "REFLECTANCE_ADD_BAND_4"],
    )
    b5_add = rsgislib.tools.utils.dict_struct_get_numeric_value(
        ls8_head_info,
        ["LEVEL2_SURFACE_REFLECTANCE_PARAMETERS", "REFLECTANCE_ADD_BAND_5"],
    )
    b6_add = rsgislib.tools.utils.dict_struct_get_numeric_value(
        ls8_head_info,
        ["LEVEL2_SURFACE_REFLECTANCE_PARAMETERS", "REFLECTANCE_ADD_BAND_6"],
    )
    b7_add = rsgislib.tools.utils.dict_struct_get_numeric_value(
        ls8_head_info,
        ["LEVEL2_SURFACE_REFLECTANCE_PARAMETERS", "REFLECTANCE_ADD_BAND_7"],
    )

    band_info = []
    band_info.append(
        {"img": os.path.join(raw_dir, b1_img), "multi": b1_multi, "add": b1_add}
    )
    band_info.append(
        {"img": os.path.join(raw_dir, b2_img), "multi": b2_multi, "add": b2_add}
    )
    band_info.append(
        {"img": os.path.join(raw_dir, b3_img), "multi": b3_multi, "add": b3_add}
    )
    band_info.append(
        {"img": os.path.join(raw_dir, b4_img), "multi": b4_multi, "add": b4_add}
    )
    band_info.append(
        {"img": os.path.join(raw_dir, b5_img), "multi": b5_multi, "add": b5_add}
    )
    band_info.append(
        {"img": os.path.join(raw_dir, b6_img), "multi": b6_multi, "add": b6_add}
    )
    band_info.append(
        {"img": os.path.join(raw_dir, b7_img), "multi": b7_multi, "add": b7_add}
    )

    sref_bands = []
    for i, band in enumerate(band_info):
        out_img_band = os.path.join(
            tmp_dir, "{}_b{}_sref.tif".format(ls_prod_id, i + 1)
        )
        rsgislib.imagecalc.image_math(
            band["img"],
            out_img_band,
            "b1==0?-9999:((b1*{})+{})*{}".format(
                band["multi"], band["add"], scale_factor
            ),
            "GTIFF",
            rsgislib.TYPE_32INT,
        )
        sref_bands.append(out_img_band)

    band_names = ["coastal", "blue", "green", "red", "nir", "swir1", "swir2"]
    out_img_ext = rsgislib.imageutils.get_file_img_extension(gdalformat)
    output_img = os.path.join(out_dir, "{}_sref.{}".format(ls_prod_id, out_img_ext))
    rsgislib.imageutils.stack_img_bands(
        sref_bands, band_names, output_img, None, -9999, gdalformat, rsgislib.TYPE_32INT
    )
    rsgislib.imageutils.pop_img_stats(
        output_img, use_no_data=True, no_data_val=-9999, calc_pyramids=True
    )

    if inc_full_qa_pxl_img:
        qa_pxl_mband_img = os.path.join(
            out_dir, "{}_pxl_qa.{}".format(ls_prod_id, out_img_ext)
        )
        qa_pxl_format = gdalformat
    else:
        qa_pxl_mband_img = os.path.join(tmp_dir, "{}_pxl_qa.tif".format(ls_prod_id))
        qa_pxl_format = "GTIFF"

    qa_pxl_img_path = os.path.join(raw_dir, qa_pxl_img)
    parse_landsat_c2_qa_pixel_img(qa_pxl_img_path, qa_pxl_mband_img, qa_pxl_format)

    cloud_msk_img = os.path.join(
        out_dir, "{}_clouds.{}".format(ls_prod_id, out_img_ext)
    )
    band_defns = list()
    band_defns.append(rsgislib.imagecalc.BandDefn("DilatedCloud", qa_pxl_mband_img, 2))
    band_defns.append(rsgislib.imagecalc.BandDefn("Cirrus", qa_pxl_mband_img, 3))
    band_defns.append(rsgislib.imagecalc.BandDefn("Cloud", qa_pxl_mband_img, 4))
    band_defns.append(rsgislib.imagecalc.BandDefn("CloudShadow", qa_pxl_mband_img, 5))
    rsgislib.imagecalc.band_math(
        cloud_msk_img,
        "DilatedCloud==1?1:Cirrus==1?1:Cloud==1?1:CloudShadow==1?2:0",
        gdalformat,
        rsgislib.TYPE_8UINT,
        band_defns,
    )
    if gdalformat == "KEA":
        rsgislib.rastergis.pop_rat_img_stats(
            cloud_msk_img, add_clr_tab=True, calc_pyramids=True, ignore_zero=True
        )
    else:
        rsgislib.imageutils.pop_thmt_img_stats(
            cloud_msk_img, add_clr_tab=True, calc_pyramids=True, ignore_zero=True
        )

    vld_msk_img = os.path.join(out_dir, "{}_vld_msk.{}".format(ls_prod_id, out_img_ext))
    band_defns = list()
    band_defns.append(rsgislib.imagecalc.BandDefn("fill", qa_pxl_mband_img, 1))
    rsgislib.imagecalc.band_math(
        vld_msk_img, "fill==0?1:0", gdalformat, rsgislib.TYPE_8UINT, band_defns
    )
    if gdalformat == "KEA":
        rsgislib.rastergis.pop_rat_img_stats(
            vld_msk_img, add_clr_tab=True, calc_pyramids=True, ignore_zero=True
        )
    else:
        rsgislib.imageutils.pop_thmt_img_stats(
            vld_msk_img, add_clr_tab=True, calc_pyramids=True, ignore_zero=True
        )

    if delete_inter_data:
        import shutil

        shutil.rmtree(raw_dir)
        for img_band in sref_bands:
            rsgislib.imageutils.delete_gdal_layer(img_band)
        if not inc_full_qa_pxl_img:
            rsgislib.imageutils.delete_gdal_layer(qa_pxl_mband_img)


def create_stacked_sref_ls_4_5_7_lv2_img(
    input_file: str,
    out_dir: str,
    tmp_dir: str,
    scale_factor: int = 10000,
    gdalformat: str = "GTIFF",
    delete_inter_data: bool = True,
    inc_full_qa_pxl_img: bool = False,
):
    """
    A function which extracts the USGS collection-2 level-2 data and creates a single
    multi-band image file in the output directory. Note the output data type is
    32bit integer and the no data value is -9999. A cloud mask and valid area images
    are also provided and extracted from the pixel QA image provided in the collection
    2 package.  Note this function just works for Landsat 4, 5 and 7 data.

    :param input_file: file name and path to the input TAR file.
    :param out_dir: output directory where the output file will be written.
    :param tmp_dir: a temporary directory where intermediate files will be written.
    :param scale_factor: the scale factor applied to the output reflectance values.
                         default is 10,000
    :param gdalformat: the output file format.
    :param delete_inter_data: delete any intermediate files created is True (Default)
    :param inc_full_qa_pxl_img: Include the full pixel QA image split into individual
                                bands in the output.


    """

    import rsgislib.imagecalc
    import rsgislib.imageutils
    import rsgislib.rastergis
    import rsgislib.tools.filetools
    import rsgislib.tools.utils

    if not os.path.exists(out_dir):
        os.mkdir(out_dir)

    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)

    if gdalformat == "GTIFF":
        rsgislib.imageutils.set_env_vars_lzw_gtiff_outs()

    raw_dir = rsgislib.tools.filetools.untar_file(input_file, tmp_dir)

    mtl_header = rsgislib.tools.filetools.find_file_none(raw_dir, "*MTL.txt")

    if mtl_header is None:
        raise rsgislib.RSGISPyException("Could not find the MTL header")

    ls8_head_info = rsgislib.tools.sensors.read_landsat_mtl_to_dict(mtl_header)

    ls_prod_id = rsgislib.tools.utils.dict_struct_get_str_value(
        ls8_head_info, ["PRODUCT_CONTENTS", "LANDSAT_PRODUCT_ID"]
    ).lower()

    b1_img = rsgislib.tools.utils.dict_struct_get_str_value(
        ls8_head_info, ["PRODUCT_CONTENTS", "FILE_NAME_BAND_1"]
    )
    b2_img = rsgislib.tools.utils.dict_struct_get_str_value(
        ls8_head_info, ["PRODUCT_CONTENTS", "FILE_NAME_BAND_2"]
    )
    b3_img = rsgislib.tools.utils.dict_struct_get_str_value(
        ls8_head_info, ["PRODUCT_CONTENTS", "FILE_NAME_BAND_3"]
    )
    b4_img = rsgislib.tools.utils.dict_struct_get_str_value(
        ls8_head_info, ["PRODUCT_CONTENTS", "FILE_NAME_BAND_4"]
    )
    b5_img = rsgislib.tools.utils.dict_struct_get_str_value(
        ls8_head_info, ["PRODUCT_CONTENTS", "FILE_NAME_BAND_5"]
    )
    b7_img = rsgislib.tools.utils.dict_struct_get_str_value(
        ls8_head_info, ["PRODUCT_CONTENTS", "FILE_NAME_BAND_7"]
    )

    qa_pxl_img = rsgislib.tools.utils.dict_struct_get_str_value(
        ls8_head_info, ["PRODUCT_CONTENTS", "FILE_NAME_QUALITY_L1_PIXEL"]
    )

    b1_multi = rsgislib.tools.utils.dict_struct_get_numeric_value(
        ls8_head_info,
        ["LEVEL2_SURFACE_REFLECTANCE_PARAMETERS", "REFLECTANCE_MULT_BAND_1"],
    )
    b2_multi = rsgislib.tools.utils.dict_struct_get_numeric_value(
        ls8_head_info,
        ["LEVEL2_SURFACE_REFLECTANCE_PARAMETERS", "REFLECTANCE_MULT_BAND_2"],
    )
    b3_multi = rsgislib.tools.utils.dict_struct_get_numeric_value(
        ls8_head_info,
        ["LEVEL2_SURFACE_REFLECTANCE_PARAMETERS", "REFLECTANCE_MULT_BAND_3"],
    )
    b4_multi = rsgislib.tools.utils.dict_struct_get_numeric_value(
        ls8_head_info,
        ["LEVEL2_SURFACE_REFLECTANCE_PARAMETERS", "REFLECTANCE_MULT_BAND_4"],
    )
    b5_multi = rsgislib.tools.utils.dict_struct_get_numeric_value(
        ls8_head_info,
        ["LEVEL2_SURFACE_REFLECTANCE_PARAMETERS", "REFLECTANCE_MULT_BAND_5"],
    )
    b7_multi = rsgislib.tools.utils.dict_struct_get_numeric_value(
        ls8_head_info,
        ["LEVEL2_SURFACE_REFLECTANCE_PARAMETERS", "REFLECTANCE_MULT_BAND_7"],
    )

    b1_add = rsgislib.tools.utils.dict_struct_get_numeric_value(
        ls8_head_info,
        ["LEVEL2_SURFACE_REFLECTANCE_PARAMETERS", "REFLECTANCE_ADD_BAND_1"],
    )
    b2_add = rsgislib.tools.utils.dict_struct_get_numeric_value(
        ls8_head_info,
        ["LEVEL2_SURFACE_REFLECTANCE_PARAMETERS", "REFLECTANCE_ADD_BAND_2"],
    )
    b3_add = rsgislib.tools.utils.dict_struct_get_numeric_value(
        ls8_head_info,
        ["LEVEL2_SURFACE_REFLECTANCE_PARAMETERS", "REFLECTANCE_ADD_BAND_3"],
    )
    b4_add = rsgislib.tools.utils.dict_struct_get_numeric_value(
        ls8_head_info,
        ["LEVEL2_SURFACE_REFLECTANCE_PARAMETERS", "REFLECTANCE_ADD_BAND_4"],
    )
    b5_add = rsgislib.tools.utils.dict_struct_get_numeric_value(
        ls8_head_info,
        ["LEVEL2_SURFACE_REFLECTANCE_PARAMETERS", "REFLECTANCE_ADD_BAND_5"],
    )
    b7_add = rsgislib.tools.utils.dict_struct_get_numeric_value(
        ls8_head_info,
        ["LEVEL2_SURFACE_REFLECTANCE_PARAMETERS", "REFLECTANCE_ADD_BAND_7"],
    )

    band_info = []
    band_info.append(
        {"img": os.path.join(raw_dir, b1_img), "multi": b1_multi, "add": b1_add}
    )
    band_info.append(
        {"img": os.path.join(raw_dir, b2_img), "multi": b2_multi, "add": b2_add}
    )
    band_info.append(
        {"img": os.path.join(raw_dir, b3_img), "multi": b3_multi, "add": b3_add}
    )
    band_info.append(
        {"img": os.path.join(raw_dir, b4_img), "multi": b4_multi, "add": b4_add}
    )
    band_info.append(
        {"img": os.path.join(raw_dir, b5_img), "multi": b5_multi, "add": b5_add}
    )
    band_info.append(
        {"img": os.path.join(raw_dir, b7_img), "multi": b7_multi, "add": b7_add}
    )

    sref_bands = []
    for i, band in enumerate(band_info):
        out_img_band = os.path.join(
            tmp_dir, "{}_b{}_sref.tif".format(ls_prod_id, i + 1)
        )
        rsgislib.imagecalc.image_math(
            band["img"],
            out_img_band,
            "b1==0?-9999:((b1*{})+{})*{}".format(
                band["multi"], band["add"], scale_factor
            ),
            "GTIFF",
            rsgislib.TYPE_32INT,
        )
        sref_bands.append(out_img_band)

    band_names = ["blue", "green", "red", "nir", "swir1", "swir2"]
    out_img_ext = rsgislib.imageutils.get_file_img_extension(gdalformat)
    output_img = os.path.join(out_dir, "{}_sref.{}".format(ls_prod_id, out_img_ext))
    rsgislib.imageutils.stack_img_bands(
        sref_bands, band_names, output_img, None, -9999, gdalformat, rsgislib.TYPE_32INT
    )
    rsgislib.imageutils.pop_img_stats(
        output_img, use_no_data=True, no_data_val=-9999, calc_pyramids=True
    )

    if inc_full_qa_pxl_img:
        qa_pxl_mband_img = os.path.join(
            out_dir, "{}_pxl_qa.{}".format(ls_prod_id, out_img_ext)
        )
        qa_pxl_format = gdalformat
    else:
        qa_pxl_mband_img = os.path.join(tmp_dir, "{}_pxl_qa.tif".format(ls_prod_id))
        qa_pxl_format = "GTIFF"

    qa_pxl_img_path = os.path.join(raw_dir, qa_pxl_img)
    parse_landsat_c2_qa_pixel_img(qa_pxl_img_path, qa_pxl_mband_img, qa_pxl_format)

    cloud_msk_img = os.path.join(
        out_dir, "{}_clouds.{}".format(ls_prod_id, out_img_ext)
    )
    band_defns = list()
    band_defns.append(rsgislib.imagecalc.BandDefn("DilatedCloud", qa_pxl_mband_img, 2))
    band_defns.append(rsgislib.imagecalc.BandDefn("Cirrus", qa_pxl_mband_img, 3))
    band_defns.append(rsgislib.imagecalc.BandDefn("Cloud", qa_pxl_mband_img, 4))
    band_defns.append(rsgislib.imagecalc.BandDefn("CloudShadow", qa_pxl_mband_img, 5))
    rsgislib.imagecalc.band_math(
        cloud_msk_img,
        "DilatedCloud==1?1:Cirrus==1?1:Cloud==1?1:CloudShadow==1?2:0",
        gdalformat,
        rsgislib.TYPE_8UINT,
        band_defns,
    )
    if gdalformat == "KEA":
        rsgislib.rastergis.pop_rat_img_stats(
            cloud_msk_img, add_clr_tab=True, calc_pyramids=True, ignore_zero=True
        )
    else:
        rsgislib.imageutils.pop_thmt_img_stats(
            cloud_msk_img, add_clr_tab=True, calc_pyramids=True, ignore_zero=True
        )

    vld_msk_img = os.path.join(out_dir, "{}_vld_msk.{}".format(ls_prod_id, out_img_ext))
    band_defns = list()
    band_defns.append(rsgislib.imagecalc.BandDefn("fill", qa_pxl_mband_img, 1))
    rsgislib.imagecalc.band_math(
        vld_msk_img, "fill==0?1:0", gdalformat, rsgislib.TYPE_8UINT, band_defns
    )
    if gdalformat == "KEA":
        rsgislib.rastergis.pop_rat_img_stats(
            vld_msk_img, add_clr_tab=True, calc_pyramids=True, ignore_zero=True
        )
    else:
        rsgislib.imageutils.pop_thmt_img_stats(
            vld_msk_img, add_clr_tab=True, calc_pyramids=True, ignore_zero=True
        )

    if delete_inter_data:
        import shutil

        shutil.rmtree(raw_dir)
        for img_band in sref_bands:
            rsgislib.imageutils.delete_gdal_layer(img_band)
        if not inc_full_qa_pxl_img:
            rsgislib.imageutils.delete_gdal_layer(qa_pxl_mband_img)


def parse_landsat_c2_qa_pixel_img(
    input_img: str, output_img: str, gdalformat: str = "GTIFF"
):
    """
    A function which will parse the bit QA Pixel image from Landsat Collection 2
    and create a multi-band output - 1 band per variable. While this takes up more
    disk space than the bit encoded image it is much easier to use!

    The output bands are:
     * Fill - No data regions (0-1)
     * DilatedCloud - Cloud dilation regions (0-1)
     * Cirrus - Cirrus clouds present (0-1)
     * Cloud - Clouds present (0-1)
     * CloudShadow - Cloud shadow present (0-1)
     * Snow - Snow present (0-1)
     * Clear - Clear sky pixel (0-1)
     * Water - Water present (0-1)
     * CloudConfidence - Confidence of cloud classification (1-4)
     * CloudShadowConfidence - Confidence of cloud shadows classification (1-4)
     * SnowIceConfidence - Confidence of snow and ice classification (1-4)
     * CirrusConfidence - Confidence of cirrus classification (1-4)

    :param input_img: The input landsat pixel QA image.
    :param output_img: The output image path - the output image will have 12 bands.
    :param gdalformat: the output image format.

    """
    from rios import applier

    import rsgislib.imagecalc
    import rsgislib.imageutils

    if gdalformat == "GTIFF":
        rsgislib.imageutils.set_env_vars_lzw_gtiff_outs()

    unq_img_vals = rsgislib.imagecalc.get_unique_values(input_img, img_band=1)

    qa_lut = dict()
    for val in unq_img_vals:
        qa_lut[val] = dict()
        qa_lut[val]["Fill"] = 0
        qa_lut[val]["DilatedCloud"] = 0
        qa_lut[val]["Cirrus"] = 0
        qa_lut[val]["Cloud"] = 0
        qa_lut[val]["CloudShadow"] = 0
        qa_lut[val]["Snow"] = 0
        qa_lut[val]["Clear"] = 0
        qa_lut[val]["Water"] = 0
        qa_lut[val]["CloudConfidence"] = 0
        qa_lut[val]["CloudShadowConfidence"] = 0
        qa_lut[val]["SnowIceConfidence"] = 0
        qa_lut[val]["CirrusConfidence"] = 0

        val_bin = numpy.flip(
            numpy.unpackbits(numpy.flip(numpy.array([val]).view(numpy.uint8)))
        )
        # print("{} = {}".format(val, val_bin))
        if val_bin[0] == 1:
            qa_lut[val]["Fill"] = 1
        if val_bin[1] == 1:
            qa_lut[val]["DilatedCloud"] = 1
        if val_bin[2] == 1:
            qa_lut[val]["Cirrus"] = 1
        if val_bin[3] == 1:
            qa_lut[val]["Cloud"] = 1
        if val_bin[4] == 1:
            qa_lut[val]["CloudShadow"] = 1
        if val_bin[5] == 1:
            qa_lut[val]["Snow"] = 1
        if val_bin[6] == 1:
            qa_lut[val]["Clear"] = 1
        if val_bin[7] == 1:
            qa_lut[val]["Water"] = 1

        if (val_bin[8] == 0) & (val_bin[9] == 1):
            qa_lut[val]["CloudConfidence"] = 2
        elif (val_bin[8] == 1) & (val_bin[9] == 0):
            qa_lut[val]["CloudConfidence"] = 3
        elif (val_bin[8] == 1) & (val_bin[9] == 1):
            qa_lut[val]["CloudConfidence"] = 4
        else:
            qa_lut[val]["CloudConfidence"] = 1

        if (val_bin[10] == 0) & (val_bin[11] == 1):
            qa_lut[val]["CloudShadowConfidence"] = 2
        elif (val_bin[10] == 1) & (val_bin[11] == 0):
            qa_lut[val]["CloudShadowConfidence"] = 3
        elif (val_bin[10] == 1) & (val_bin[11] == 1):
            qa_lut[val]["CloudShadowConfidence"] = 4
        else:
            qa_lut[val]["CloudShadowConfidence"] = 1

        if (val_bin[12] == 0) & (val_bin[13] == 1):
            qa_lut[val]["SnowIceConfidence"] = 2
        elif (val_bin[12] == 1) & (val_bin[13] == 0):
            qa_lut[val]["SnowIceConfidence"] = 3
        elif (val_bin[12] == 1) & (val_bin[13] == 1):
            qa_lut[val]["SnowIceConfidence"] = 4
        else:
            qa_lut[val]["SnowIceConfidence"] = 1

        if (val_bin[14] == 0) & (val_bin[15] == 1):
            qa_lut[val]["CirrusConfidence"] = 2
        elif (val_bin[14] == 1) & (val_bin[15] == 0):
            qa_lut[val]["CirrusConfidence"] = 3
        elif (val_bin[14] == 1) & (val_bin[15] == 1):
            qa_lut[val]["CirrusConfidence"] = 4
        else:
            qa_lut[val]["CirrusConfidence"] = 1

    if TQDM_AVAIL:
        progress_bar = rsgislib.TQDMProgressBar()
    else:
        progress_bar = rios.cuiprogress.GDALProgressBar()

    infiles = applier.FilenameAssociations()
    infiles.image = input_img
    outfiles = applier.FilenameAssociations()
    outfiles.outimage = output_img
    otherargs = applier.OtherInputs()
    otherargs.qa_lut = qa_lut
    aControls = applier.ApplierControls()
    aControls.progress = progress_bar
    aControls.creationoptions = rsgislib.imageutils.get_rios_img_creation_opts(
        gdalformat
    )
    aControls.drivername = gdalformat
    aControls.omitPyramids = True
    aControls.calcStats = False

    def _apply_gen_ls_c2_qa_img(info, inputs, outputs, otherargs):
        """
        This is an internal rios function
        """
        img_dims = inputs.image.shape
        img_dims_lst = list(img_dims)
        img_dims_lst[0] = 12
        outputs.outimage = numpy.zeros(img_dims_lst, dtype=numpy.uint8)

        for val in otherargs.qa_lut:
            outputs.outimage[0][inputs.image[0] == val] = otherargs.qa_lut[val]["Fill"]
            outputs.outimage[1][inputs.image[0] == val] = otherargs.qa_lut[val][
                "DilatedCloud"
            ]
            outputs.outimage[2][inputs.image[0] == val] = otherargs.qa_lut[val][
                "Cirrus"
            ]
            outputs.outimage[3][inputs.image[0] == val] = otherargs.qa_lut[val]["Cloud"]
            outputs.outimage[4][inputs.image[0] == val] = otherargs.qa_lut[val][
                "CloudShadow"
            ]
            outputs.outimage[5][inputs.image[0] == val] = otherargs.qa_lut[val]["Snow"]
            outputs.outimage[6][inputs.image[0] == val] = otherargs.qa_lut[val]["Clear"]
            outputs.outimage[7][inputs.image[0] == val] = otherargs.qa_lut[val]["Water"]
            outputs.outimage[8][inputs.image[0] == val] = otherargs.qa_lut[val][
                "CloudConfidence"
            ]
            outputs.outimage[9][inputs.image[0] == val] = otherargs.qa_lut[val][
                "CloudShadowConfidence"
            ]
            outputs.outimage[10][inputs.image[0] == val] = otherargs.qa_lut[val][
                "SnowIceConfidence"
            ]
            outputs.outimage[11][inputs.image[0] == val] = otherargs.qa_lut[val][
                "CirrusConfidence"
            ]

    applier.apply(
        _apply_gen_ls_c2_qa_img, infiles, outfiles, otherargs, controls=aControls
    )

    rsgislib.imageutils.set_band_names(
        output_img,
        band_names=[
            "Fill",
            "DilatedCloud",
            "Cirrus",
            "Cloud",
            "CloudShadow",
            "Snow",
            "Clear",
            "Water",
            "CloudConfidence",
            "CloudShadowConfidence",
            "SnowIceConfidence",
            "CirrusConfidence",
        ],
    )
    rsgislib.imageutils.pop_img_stats(
        output_img, use_no_data=True, no_data_val=0, calc_pyramids=True
    )


def create_stacked_sen2_esa_l2a_img(
    input_safe: str,
    out_dir: str,
    tmp_dir: str,
    out_res_10m: bool = True,
    sharpen_10m: bool = True,
    scale_factor: int = 10000,
    gdalformat: str = "GTIFF",
    datatype: int = rsgislib.TYPE_32INT,
    delete_inter_data: bool = True,
    resample_10m_method=rsgislib.INTERP_CUBIC,
    resample_20m_method=rsgislib.INTERP_AVERAGE,
    use_multi_core: bool = False,
):
    """
    A function which extracts the ESA Sentinel-2 Level 2A data from the SAFE download
    file structure to create a single multi-band image file in the output directory.

    :param input_safe: Input SAFE file format directory.
    :param out_dir: output directory for the output files.
    :param tmp_dir: tmp directory for intermediate files.
    :param out_res_10m: boolean to specify that the output image should be at a
                        pixel resolution of 10 m. Default: True
    :param sharpen_10m: boolean specifying that the output image should sharpen
                        the 20 m bands when creating a 10 m output image
    :param scale_factor: the scale factor applied to the output reflectance values.
                         default is 10,000
    :param gdalformat: the output file format.
    :param datatype: output data type - Default: rsgislib.TYPE_32INT
    :param delete_inter_data: delete any intermediate files created is True (Default)
    :param resample_10m_method: the method for resampling the 20 m bands to 10 m.
                                Default: rsgislib.INTERP_CUBIC
    :param resample_20m_method: the method for resampling the 10 m bands to 20 m.
                                Default: rsgislib.INTERP_AVERAGE
    :param use_multi_core: boolean specifying whether multiple cores should be used
                           when resampling the image data. Default: False

    """
    import rsgislib.imagecalc
    import rsgislib.imageutils
    import rsgislib.tools.filetools
    import rsgislib.tools.utils

    if not os.path.exists(out_dir):
        os.mkdir(out_dir)

    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)

    uid_str = rsgislib.tools.utils.uid_generator()
    uid_tmp_dir = os.path.join(tmp_dir, uid_str)
    if not os.path.exists(uid_tmp_dir):
        os.mkdir(uid_tmp_dir)

    if gdalformat == "GTIFF":
        rsgislib.imageutils.set_env_vars_lzw_gtiff_outs()
    out_img_ext = rsgislib.imageutils.get_file_img_extension(gdalformat)

    input_safe_abs = os.path.abspath(input_safe)

    mtd_header_file = rsgislib.tools.filetools.find_file_none(
        input_safe, "MTD_MSIL2A.xml"
    )

    if mtd_header_file is None:
        raise rsgislib.RSGISPyException("Could not find the Sentinel-2 MTD header")

    s2_hdr_info = rsgislib.tools.sensors.read_sen2_l2a_mtd_to_dict(mtd_header_file)

    if len(s2_hdr_info["Product_Info"]["Product_Organisation"]["Granule_List"]) != 1:
        raise rsgislib.RSGISPyException("Was expecting just a single granule.")

    scn_file_name = s2_hdr_info["Product_Info"]["PRODUCT_URI"].replace(".SAFE", "")

    no_data_val = float(
        s2_hdr_info["Product_Image_Characteristics"]["Special_Values"]["NODATA"]
    )

    quant_boa_val = s2_hdr_info["Product_Image_Characteristics"][
        "Quantification_values"
    ]["BOA_QUANTIFICATION_VALUE"]
    update_scale_factor = True
    if scale_factor == quant_boa_val:
        update_scale_factor = False

    granule_info = s2_hdr_info["Product_Info"]["Product_Organisation"]["Granule_List"][
        0
    ]
    img_files = granule_info["IMAGE_FILES"]
    imgs_10m = dict()
    imgs_10m["B02"] = None
    imgs_10m["B03"] = None
    imgs_10m["B04"] = None
    imgs_10m["B08"] = None
    comp_imgs_10m_20m = dict()
    comp_imgs_10m_20m["B05"] = None
    comp_imgs_10m_20m["B06"] = None
    comp_imgs_10m_20m["B07"] = None
    comp_imgs_10m_20m["B8A"] = None
    comp_imgs_10m_20m["B11"] = None
    comp_imgs_10m_20m["B12"] = None
    all_20m_imgs = dict()
    all_20m_imgs["B02"] = None
    all_20m_imgs["B03"] = None
    all_20m_imgs["B04"] = None
    all_20m_imgs["B05"] = None
    all_20m_imgs["B06"] = None
    all_20m_imgs["B07"] = None
    all_20m_imgs["B8A"] = None
    all_20m_imgs["B11"] = None
    all_20m_imgs["B12"] = None
    scl_20m_img = None
    for img in img_files:
        if "10m" in img:
            for band in imgs_10m.keys():
                if band in img:
                    imgs_10m[band] = os.path.join(input_safe_abs, f"{img}.jp2")
                    break
        elif "20m" in img:
            if "SCL" in img:
                scl_20m_img = os.path.join(input_safe_abs, f"{img}.jp2")
                break
            for band in all_20m_imgs.keys():
                if band in img:
                    all_20m_imgs[band] = os.path.join(input_safe_abs, f"{img}.jp2")
                    if band in comp_imgs_10m_20m.keys():
                        comp_imgs_10m_20m[band] = os.path.join(
                            input_safe_abs, f"{img}.jp2"
                        )
                    break

    if out_res_10m:
        ref_img = imgs_10m["B02"]
        for band in comp_imgs_10m_20m:
            img_basename = rsgislib.tools.filetools.get_file_basename(
                comp_imgs_10m_20m[band]
            )
            img_basename_10m = img_basename.replace("20m", "10m")
            out_10m_img = os.path.join(uid_tmp_dir, f"{img_basename_10m}.tif")
            if sharpen_10m:
                resample_10m_method = rsgislib.INTERP_NEAREST_NEIGHBOUR
            rsgislib.imageutils.resample_img_to_match(
                ref_img,
                comp_imgs_10m_20m[band],
                out_10m_img,
                gdalformat="GTIFF",
                interp_method=resample_10m_method,
                datatype=rsgislib.TYPE_16UINT,
                no_data_val=no_data_val,
                multicore=use_multi_core,
            )
            imgs_10m[band] = out_10m_img

        input_imgs = list()
        input_imgs.append(imgs_10m["B02"])
        input_imgs.append(imgs_10m["B03"])
        input_imgs.append(imgs_10m["B04"])
        input_imgs.append(imgs_10m["B05"])
        input_imgs.append(imgs_10m["B06"])
        input_imgs.append(imgs_10m["B07"])
        input_imgs.append(imgs_10m["B08"])
        input_imgs.append(imgs_10m["B8A"])
        input_imgs.append(imgs_10m["B11"])
        input_imgs.append(imgs_10m["B12"])

        tmp_sref_img = os.path.join(uid_tmp_dir, f"{scn_file_name}_10m_sref.tif")
        out_sref_img = os.path.join(out_dir, f"{scn_file_name}_10m_sref.{out_img_ext}")
        if not update_scale_factor:
            tmp_sref_img = out_sref_img

        if sharpen_10m:
            # Create_VRT
            tmp_vrt_img = os.path.join(uid_tmp_dir, f"{scn_file_name}_tmp_stck.vrt")
            rsgislib.imageutils.create_stack_images_vrt(input_imgs, tmp_vrt_img)

            band_shp_info = []
            band_shp_info.append(
                rsgislib.imageutils.SharpBandInfo(
                    band=1, status=rsgislib.SHARP_RES_HIGH, name="Blue"
                )
            )
            band_shp_info.append(
                rsgislib.imageutils.SharpBandInfo(
                    band=2, status=rsgislib.SHARP_RES_HIGH, name="Green"
                )
            )
            band_shp_info.append(
                rsgislib.imageutils.SharpBandInfo(
                    band=3, status=rsgislib.SHARP_RES_HIGH, name="Red"
                )
            )
            band_shp_info.append(
                rsgislib.imageutils.SharpBandInfo(
                    band=4, status=rsgislib.SHARP_RES_LOW, name="RE_B5"
                )
            )
            band_shp_info.append(
                rsgislib.imageutils.SharpBandInfo(
                    band=5, status=rsgislib.SHARP_RES_LOW, name="RE_B6"
                )
            )
            band_shp_info.append(
                rsgislib.imageutils.SharpBandInfo(
                    band=6, status=rsgislib.SHARP_RES_LOW, name="RE_B7"
                )
            )
            band_shp_info.append(
                rsgislib.imageutils.SharpBandInfo(
                    band=7, status=rsgislib.SHARP_RES_HIGH, name="NIR_B8"
                )
            )
            band_shp_info.append(
                rsgislib.imageutils.SharpBandInfo(
                    band=8, status=rsgislib.SHARP_RES_LOW, name="NIR_B8A"
                )
            )
            band_shp_info.append(
                rsgislib.imageutils.SharpBandInfo(
                    band=9, status=rsgislib.SHARP_RES_LOW, name="SWIR1"
                )
            )
            band_shp_info.append(
                rsgislib.imageutils.SharpBandInfo(
                    band=10, status=rsgislib.SHARP_RES_LOW, name="SWIR2"
                )
            )

            rsgislib.imageutils.sharpen_low_res_bands(
                tmp_vrt_img,
                tmp_sref_img,
                band_info=band_shp_info,
                win_size=7,
                no_data_val=int(no_data_val),
                gdalformat=gdalformat,
                datatype=rsgislib.TYPE_16UINT,
            )
        else:
            rsgislib.imageutils.stack_img_bands(
                input_imgs,
                None,
                tmp_sref_img,
                skip_value=no_data_val,
                no_data_val=no_data_val,
                gdalformat=gdalformat,
                datatype=rsgislib.TYPE_16UINT,
            )

        out_scl_img = os.path.join(out_dir, f"{scn_file_name}_10m_scl.{out_img_ext}")
        rsgislib.imageutils.resample_img_to_match(
            ref_img,
            scl_20m_img,
            out_scl_img,
            gdalformat=gdalformat,
            interp_method=resample_10m_method,
            datatype=rsgislib.TYPE_8UINT,
            no_data_val=-1,
            multicore=use_multi_core,
        )
        out_clouds_img = os.path.join(
            out_dir, f"{scn_file_name}_10m_clouds.{out_img_ext}"
        )
        rsgislib.imagecalc.image_math(
            out_scl_img,
            out_clouds_img,
            "(b1==8)||(b1==9)||(b1==10)?1:(b1==3)?2:0",
            gdalformat,
            rsgislib.TYPE_8UINT,
        )
        out_vld_img = os.path.join(out_dir, f"{scn_file_name}_10m_vld.{out_img_ext}")
        rsgislib.imagecalc.image_math(
            out_scl_img, out_vld_img, "b1==0?1:0", gdalformat, rsgislib.TYPE_8UINT
        )
    else:
        ref_img = all_20m_imgs["B02"]
        img_basename = rsgislib.tools.filetools.get_file_basename(imgs_10m["B08"])
        img_basename_20m = img_basename.replace("10m", "20m")
        out_b08_20m_img = os.path.join(uid_tmp_dir, f"{img_basename_20m}.tif")
        rsgislib.imageutils.resample_img_to_match(
            ref_img,
            imgs_10m["B08"],
            out_b08_20m_img,
            gdalformat="GTIFF",
            interp_method=resample_20m_method,
            datatype=rsgislib.TYPE_16UINT,
            no_data_val=no_data_val,
            multicore=use_multi_core,
        )
        all_20m_imgs["B08"] = out_b08_20m_img

        input_imgs = list()
        input_imgs.append(all_20m_imgs["B02"])
        input_imgs.append(all_20m_imgs["B03"])
        input_imgs.append(all_20m_imgs["B04"])
        input_imgs.append(all_20m_imgs["B05"])
        input_imgs.append(all_20m_imgs["B06"])
        input_imgs.append(all_20m_imgs["B07"])
        input_imgs.append(all_20m_imgs["B08"])
        input_imgs.append(all_20m_imgs["B8A"])
        input_imgs.append(all_20m_imgs["B11"])
        input_imgs.append(all_20m_imgs["B12"])

        tmp_sref_img = os.path.join(uid_tmp_dir, f"{scn_file_name}_20m_sref.tif")
        out_sref_img = os.path.join(out_dir, f"{scn_file_name}_20m_sref.{out_img_ext}")
        if not update_scale_factor:
            tmp_sref_img = out_sref_img

        rsgislib.imageutils.stack_img_bands(
            input_imgs,
            None,
            tmp_sref_img,
            skip_value=no_data_val,
            no_data_val=no_data_val,
            gdalformat=gdalformat,
            datatype=rsgislib.TYPE_16UINT,
        )

        out_scl_img = os.path.join(out_dir, f"{scn_file_name}_20m_scl.{out_img_ext}")
        rsgislib.imagecalc.image_math(
            scl_20m_img, out_scl_img, "b1", gdalformat, rsgislib.TYPE_8UINT
        )
        out_clouds_img = os.path.join(
            out_dir, f"{scn_file_name}_20m_clouds.{out_img_ext}"
        )
        rsgislib.imagecalc.image_math(
            scl_20m_img,
            out_clouds_img,
            "(b1==8)||(b1==9)||(b1==10)?1:(b1==3)?2:0",
            gdalformat,
            rsgislib.TYPE_8UINT,
        )
        out_vld_img = os.path.join(out_dir, f"{scn_file_name}_20m_vld.{out_img_ext}")
        rsgislib.imagecalc.image_math(
            scl_20m_img, out_vld_img, "b1==0?1:0", gdalformat, rsgislib.TYPE_8UINT
        )

    if update_scale_factor:
        exp = f"b1=={no_data_val}?{no_data_val}:(b1/{quant_boa_val})*{scale_factor}"
        rsgislib.imagecalc.image_math(
            tmp_sref_img, out_sref_img, exp, gdalformat, datatype
        )

    band_names = [
        "Blue",
        "Green",
        "Red",
        "RE_B5",
        "RE_B6",
        "RE_B7",
        "NIR_B8",
        "NIR_B8A",
        "SWIR1",
        "SWIR2",
    ]
    rsgislib.imageutils.set_band_names(out_sref_img, band_names)
    rsgislib.imageutils.pop_img_stats(
        out_sref_img, use_no_data=True, no_data_val=no_data_val, calc_pyramids=True
    )

    if gdalformat == "KEA":
        import rsgislib.rastergis

        rsgislib.rastergis.pop_rat_img_stats(
            out_scl_img, add_clr_tab=True, calc_pyramids=True, ignore_zero=False
        )
        rsgislib.rastergis.pop_rat_img_stats(
            out_clouds_img, add_clr_tab=True, calc_pyramids=True, ignore_zero=True
        )
        rsgislib.rastergis.pop_rat_img_stats(
            out_vld_img, add_clr_tab=True, calc_pyramids=True, ignore_zero=True
        )
    else:
        rsgislib.imageutils.pop_thmt_img_stats(
            out_scl_img, add_clr_tab=True, calc_pyramids=True, ignore_zero=False
        )
        rsgislib.imageutils.pop_thmt_img_stats(
            out_clouds_img, add_clr_tab=True, calc_pyramids=True, ignore_zero=True
        )
        rsgislib.imageutils.pop_thmt_img_stats(
            out_vld_img, add_clr_tab=True, calc_pyramids=True, ignore_zero=True
        )

    if delete_inter_data:
        import shutil

        shutil.rmtree(uid_tmp_dir)
