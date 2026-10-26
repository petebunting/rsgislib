#!/usr/bin/env python
"""
The tools and utilities for specific sensors.
"""
import datetime
import os

import rsgislib


def read_landsat_mtl_to_dict(in_mtl_file):
    """
    A function which can read a Landsat MTL header file and return a
    structured dict with the information from the MTL file.

    :param in_mtl_file: the file path to MTL header file (*MTL.txt)
    :return: dict structure.

    .. code:: python

        import pprint
        import rsgislib.tools.sensors

        ls_header = rsgislib.tools.sensors.read_landsat_mtl_to_dict("landsat_MTL.txt")
        pprint.pprint(ls_header)

    """
    h_file = open(in_mtl_file, "r")
    header_params = dict()
    for line in h_file:
        line = line.strip()
        if line:
            line_vals = line.split("=")
            if len(line_vals) == 2:
                if line_vals[0].strip() == "GROUP":
                    c_dict = dict()
                    header_params[line_vals[1].strip()] = c_dict
                elif line_vals[0].strip() != "END_GROUP":
                    c_dict[line_vals[0].strip()] = line_vals[1].strip().replace('"', "")
    h_file.close()
    return header_params


def read_sen2_l2a_mtd_to_dict(mtd_header_file: str):
    """
    A function which parses the top level Sentinel-2 Level2A XML MTD header file
    to create a dict with the information to make it easier to use.

    :param mtd_header_file: file path to the MTD header file (MTD_MSIL2A.xml)
    :return: dict structure with the header information

    """
    import xml.etree.ElementTree as ET

    if not os.path.exists(mtd_header_file):
        raise rsgislib.RSGISPyException(
            f"MTD header file doesn't exist: {mtd_header_file}"
        )

    out_header_dict = dict()

    tree = ET.parse(mtd_header_file)
    root = tree.getroot()

    general_info_tag = root.find(
        "{https://psd-15.sentinel2.eo.esa.int/PSD/User_Product_Level-2A.xsd}General_Info"
    )
    if general_info_tag is None:
        general_info_tag = root.find("{https://psd-14.sentinel2.eo.esa.int/PSD/User_Product_Level-2A.xsd}General_Info")
        if general_info_tag is None:
            general_info_tag = root.find("{https://psd-16.sentinel2.eo.esa.int/PSD/User_Product_Level-2A.xsd}General_Info")
            if general_info_tag is None:
                raise rsgislib.RSGISPyException(
                    "Cannot open top level section 'General_Info' - "
                    "is this really a Sentinel-2 image file?"
                )


    product_info_tag = general_info_tag.find("Product_Info")
    if product_info_tag is None:
        raise rsgislib.RSGISPyException(
            "Product Info Tag is None - is this a Sentinel-2 L2A header"
        )
    out_header_dict["Product_Info"] = dict()
    prod_start_time_str = product_info_tag.find("PRODUCT_START_TIME").text.strip()
    prod_start_time_str = prod_start_time_str.replace("Z", "")
    prod_start_time = datetime.datetime.strptime(
        prod_start_time_str, "%Y-%m-%dT%H:%M:%S.%f"
    )
    out_header_dict["Product_Info"]["PRODUCT_START_TIME"] = prod_start_time
    prod_stop_time_str = product_info_tag.find("PRODUCT_STOP_TIME").text.strip()
    prod_stop_time_str = prod_stop_time_str.replace("Z", "")
    prod_stop_time = datetime.datetime.strptime(
        prod_stop_time_str, "%Y-%m-%dT%H:%M:%S.%f"
    )
    out_header_dict["Product_Info"]["PRODUCT_STOP_TIME"] = prod_stop_time
    out_header_dict["Product_Info"]["PRODUCT_URI"] = product_info_tag.find(
        "PRODUCT_URI"
    ).text.strip()
    out_header_dict["Product_Info"]["PROCESSING_LEVEL"] = product_info_tag.find(
        "PROCESSING_LEVEL"
    ).text.strip()
    out_header_dict["Product_Info"]["PRODUCT_TYPE"] = product_info_tag.find(
        "PRODUCT_TYPE"
    ).text.strip()
    out_header_dict["Product_Info"]["PROCESSING_BASELINE"] = product_info_tag.find(
        "PROCESSING_BASELINE"
    ).text.strip()
    gen_time_str = product_info_tag.find("GENERATION_TIME").text.strip()
    gen_time_str = gen_time_str.replace("Z", "")
    gen_time = datetime.datetime.strptime(gen_time_str, "%Y-%m-%dT%H:%M:%S.%f")
    out_header_dict["Product_Info"]["GENERATION_TIME"] = gen_time
    out_header_dict["Product_Info"]["PREVIEW_IMAGE_URL"] = product_info_tag.find(
        "PREVIEW_IMAGE_URL"
    ).text.strip()
    out_header_dict["Product_Info"]["PREVIEW_GEO_INFO"] = product_info_tag.find(
        "PREVIEW_GEO_INFO"
    ).text.strip()

    data_take_tag = product_info_tag.find("Datatake")
    if data_take_tag is None:
        raise rsgislib.RSGISPyException(
            "Data Take Tag is None - is this a Sentinel-2 L2A header"
        )
    out_header_dict["Product_Info"]["datatake"] = dict()
    out_header_dict["Product_Info"]["datatake"]["datatakeIdentifier"] = (
        data_take_tag.attrib["datatakeIdentifier"].strip()
    )
    out_header_dict["Product_Info"]["datatake"]["SPACECRAFT_NAME"] = data_take_tag.find(
        "SPACECRAFT_NAME"
    ).text.strip()
    out_header_dict["Product_Info"]["datatake"]["DATATAKE_TYPE"] = data_take_tag.find(
        "DATATAKE_TYPE"
    ).text.strip()
    datatake_sense_time_str = data_take_tag.find("DATATAKE_SENSING_START").text.strip()
    datatake_sense_time_str = datatake_sense_time_str.replace("Z", "")
    datatake_sense_time = datetime.datetime.strptime(
        datatake_sense_time_str, "%Y-%m-%dT%H:%M:%S.%f"
    )
    out_header_dict["Product_Info"]["datatake"][
        "DATATAKE_SENSING_START"
    ] = datatake_sense_time
    out_header_dict["Product_Info"]["datatake"]["SENSING_ORBIT_NUMBER"] = (
        data_take_tag.find("SENSING_ORBIT_NUMBER").text.strip()
    )
    out_header_dict["Product_Info"]["datatake"]["SENSING_ORBIT_DIRECTION"] = (
        data_take_tag.find("SENSING_ORBIT_DIRECTION").text.strip()
    )

    query_options_tag = product_info_tag.find("Query_Options")
    if query_options_tag is None:
        raise rsgislib.RSGISPyException(
            "Query Options Tag is None - is this a Sentinel-2 L2A header"
        )
    out_header_dict["Product_Info"]["Query_Options"] = dict()
    out_header_dict["Product_Info"]["Query_Options"]["PRODUCT_FORMAT"] = (
        query_options_tag.find("PRODUCT_FORMAT").text.strip()
    )

    product_organisation_tag = product_info_tag.find("Product_Organisation")
    if product_organisation_tag is None:
        raise rsgislib.RSGISPyException(
            "Product Organisation Tag is None - is this a Sentinel-2 L2A header"
        )
    out_header_dict["Product_Info"]["Product_Organisation"] = dict()

    granule_list_tag = product_organisation_tag.find("Granule_List")
    if granule_list_tag is None:
        raise rsgislib.RSGISPyException(
            "Granule list Tag is None - is this a Sentinel-2 L2A header"
        )
    out_header_dict["Product_Info"]["Product_Organisation"]["Granule_List"] = list()

    for granule_list_child in granule_list_tag:
        if granule_list_child.tag == "Granule":
            lcl_granule_dict = dict()
            lcl_granule_dict["datastripIdentifier"] = granule_list_child.attrib[
                "datastripIdentifier"
            ].strip()
            lcl_granule_dict["granuleIdentifier"] = granule_list_child.attrib[
                "granuleIdentifier"
            ].strip()
            lcl_granule_dict["imageFormat"] = granule_list_child.attrib[
                "imageFormat"
            ].strip()

            lcl_granule_dict["IMAGE_FILES"] = list()
            for granule_child in granule_list_child:
                if granule_child.tag == "IMAGE_FILE":
                    lcl_granule_dict["IMAGE_FILES"].append(granule_child.text.strip())

            out_header_dict["Product_Info"]["Product_Organisation"][
                "Granule_List"
            ].append(lcl_granule_dict)

    product_image_char_tag = general_info_tag.find("Product_Image_Characteristics")
    if product_image_char_tag is None:
        raise rsgislib.RSGISPyException(
            "Product Image Characteristics Tag is None - is this a Sentinel-2 L2A header"
        )
    out_header_dict["Product_Image_Characteristics"] = dict()
    out_header_dict["Product_Image_Characteristics"]["Special_Values"] = dict()
    out_header_dict["Product_Image_Characteristics"]["Image_Display_Order"] = dict()
    out_header_dict["Product_Image_Characteristics"]["Quantification_values"] = dict()
    out_header_dict["Product_Image_Characteristics"]["Reflectance_Conversion"] = dict()
    out_header_dict["Product_Image_Characteristics"]["Reflectance_Conversion"][
        "Solar_Irradiance"
    ] = dict()
    out_header_dict["Product_Image_Characteristics"][
        "Spectral_Information_List"
    ] = dict()
    out_header_dict["Product_Image_Characteristics"]["Physical_Gains"] = dict()
    out_header_dict["Product_Image_Characteristics"]["Scene_Classification"] = dict()
    out_header_dict["Band_LUT"] = dict()
    out_header_dict["Band_LUT"]["Physical_Band"] = dict()
    out_header_dict["Band_LUT"]["Band_ID"] = dict()

    for product_image_char_child in product_image_char_tag:
        if product_image_char_child.tag == "Special_Values":
            special_val_name = product_image_char_child.find(
                "SPECIAL_VALUE_TEXT"
            ).text.strip()
            special_val = int(
                product_image_char_child.find("SPECIAL_VALUE_INDEX").text.strip()
            )
            out_header_dict["Product_Image_Characteristics"]["Special_Values"][
                special_val_name
            ] = special_val
        elif product_image_char_child.tag == "Image_Display_Order":
            out_header_dict["Product_Image_Characteristics"]["Image_Display_Order"][
                "RED_CHANNEL"
            ] = int(product_image_char_child.find("RED_CHANNEL").text.strip())
            out_header_dict["Product_Image_Characteristics"]["Image_Display_Order"][
                "GREEN_CHANNEL"
            ] = int(product_image_char_child.find("GREEN_CHANNEL").text.strip())
            out_header_dict["Product_Image_Characteristics"]["Image_Display_Order"][
                "BLUE_CHANNEL"
            ] = int(product_image_char_child.find("BLUE_CHANNEL").text.strip())
        elif product_image_char_child.tag == "QUANTIFICATION_VALUES_LIST":
            out_header_dict["Product_Image_Characteristics"]["Quantification_values"][
                "BOA_QUANTIFICATION_VALUE"
            ] = int(
                product_image_char_child.find("BOA_QUANTIFICATION_VALUE").text.strip()
            )
            out_header_dict["Product_Image_Characteristics"]["Quantification_values"][
                "AOT_QUANTIFICATION_VALUE"
            ] = float(
                product_image_char_child.find("AOT_QUANTIFICATION_VALUE").text.strip()
            )
            out_header_dict["Product_Image_Characteristics"]["Quantification_values"][
                "WVP_QUANTIFICATION_VALUE"
            ] = float(
                product_image_char_child.find("WVP_QUANTIFICATION_VALUE").text.strip()
            )
        elif product_image_char_child.tag == "Reflectance_Conversion":
            out_header_dict["Product_Image_Characteristics"]["Reflectance_Conversion"][
                "U"
            ] = float(product_image_char_child.find("U").text.strip())
            for solar_irr_child in product_image_char_child.find(
                "Solar_Irradiance_List"
            ):
                if solar_irr_child.tag == "SOLAR_IRRADIANCE":
                    solar_irr_band = int(solar_irr_child.attrib["bandId"].strip())
                    solar_irr_val = float(solar_irr_child.text.strip())
                    out_header_dict["Product_Image_Characteristics"][
                        "Reflectance_Conversion"
                    ]["Solar_Irradiance"][solar_irr_band] = solar_irr_val
        elif product_image_char_child.tag == "Spectral_Information_List":
            for spec_info_child in product_image_char_child:
                if spec_info_child.tag == "Spectral_Information":
                    spec_info_band_id = int(spec_info_child.attrib["bandId"].strip())
                    spec_info_phys_band = spec_info_child.attrib["physicalBand"].strip()
                    out_header_dict["Band_LUT"]["Physical_Band"][
                        spec_info_phys_band
                    ] = spec_info_band_id
                    out_header_dict["Band_LUT"]["Band_ID"][
                        spec_info_band_id
                    ] = spec_info_phys_band
                    out_header_dict["Product_Image_Characteristics"][
                        "Spectral_Information_List"
                    ][spec_info_band_id] = dict()
                    out_header_dict["Product_Image_Characteristics"][
                        "Spectral_Information_List"
                    ][spec_info_band_id]["RESOLUTION"] = int(
                        spec_info_child.find("RESOLUTION").text.strip()
                    )
                    wavelength_tag = spec_info_child.find("Wavelength")
                    if wavelength_tag is not None:
                        out_header_dict["Product_Image_Characteristics"][
                            "Spectral_Information_List"
                        ][spec_info_band_id]["Wavelength"] = dict()
                        out_header_dict["Product_Image_Characteristics"][
                            "Spectral_Information_List"
                        ][spec_info_band_id]["Wavelength"]["MIN"] = float(
                            wavelength_tag.find("MIN").text.strip()
                        )
                        out_header_dict["Product_Image_Characteristics"][
                            "Spectral_Information_List"
                        ][spec_info_band_id]["Wavelength"]["MAX"] = float(
                            wavelength_tag.find("MAX").text.strip()
                        )
                        out_header_dict["Product_Image_Characteristics"][
                            "Spectral_Information_List"
                        ][spec_info_band_id]["Wavelength"]["CENTRAL"] = float(
                            wavelength_tag.find("CENTRAL").text.strip()
                        )
                    spec_resp_tag = spec_info_child.find("Spectral_Response")
                    if spec_resp_tag is not None:
                        out_header_dict["Product_Image_Characteristics"][
                            "Spectral_Information_List"
                        ][spec_info_band_id]["Spectral_Response"] = dict()
                        out_header_dict["Product_Image_Characteristics"][
                            "Spectral_Information_List"
                        ][spec_info_band_id]["Spectral_Response"]["STEP"] = float(
                            spec_resp_tag.find("STEP").text.strip()
                        )
                        out_header_dict["Product_Image_Characteristics"][
                            "Spectral_Information_List"
                        ][spec_info_band_id]["Spectral_Response"]["Values"] = list()
                        spec_resp_vals_str = spec_resp_tag.find("VALUES").text.strip()
                        spec_resp_vals = spec_resp_vals_str.split(" ")
                        for spec_resp_val in spec_resp_vals:
                            out_header_dict["Product_Image_Characteristics"][
                                "Spectral_Information_List"
                            ][spec_info_band_id]["Spectral_Response"]["Values"].append(
                                float(spec_resp_val)
                            )
        elif product_image_char_child.tag == "PHYSICAL_GAINS":
            phys_gain_band = int(product_image_char_child.attrib["bandId"].strip())
            phys_gain_val = float(product_image_char_child.text.strip())
            out_header_dict["Product_Image_Characteristics"]["Physical_Gains"][
                phys_gain_band
            ] = phys_gain_val
        elif product_image_char_child.tag == "Scene_Classification_List":
            for scn_class_child in product_image_char_child:
                if scn_class_child.tag == "Scene_Classification_ID":
                    cls_name = scn_class_child.find(
                        "SCENE_CLASSIFICATION_TEXT"
                    ).text.strip()
                    cls_val = scn_class_child.find(
                        "SCENE_CLASSIFICATION_INDEX"
                    ).text.strip()
                    out_header_dict["Product_Image_Characteristics"][
                        "Scene_Classification"
                    ][cls_name] = cls_val
        else:
            print(
                "Ignoring tag ({}) as do not recognise".format(
                    product_image_char_child.tag
                )
            )

    return out_header_dict
