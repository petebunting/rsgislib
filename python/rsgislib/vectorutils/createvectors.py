#!/usr/bin/env python
"""
Tools for creating vector layers.
"""

import os
from typing import Dict, List, Tuple, Union

from osgeo import gdal, ogr, osr
import numpy

import rsgislib

TQDM_AVAIL = True
try:
    import tqdm
except ImportError:
    import rios.cuiprogress

    TQDM_AVAIL = False

gdal.UseExceptions()


def polygonise_raster_to_vec_lyr(
    out_vec_file: str,
    out_vec_lyr: str,
    out_format: str,
    input_img: str,
    img_band: int = 1,
    mask_img: str = None,
    mask_band: int = 1,
    replace_file: bool = True,
    replace_lyr: bool = True,
    pxl_val_fieldname: str = "PXLVAL",
    use_8_conn: bool = False,
):
    """
    A utility to polygonise a raster to a OGR vector layer.

    :param out_vec_file: is a string specifying the output vector file path. If it
                         exists it will be deleted and overwritten.
    :param out_vec_lyr: is a string with the name of the vector layer.
    :param out_format: is a string with the driver
    :param input_img: is a string specifying the input image file to be polygonised
    :param img_band: is an int specifying the image band to be
                     polygonised. (default = 1)
    :param mask_img: is an optional string mask file specifying a no data
                     mask (default = None)
    :param mask_band: is an int specifying the image band to be used the
                      mask (default = 1)
    :param replace_file: is a boolean specifying whether the vector file should be
                         replaced (i.e., overwritten). Default=True.
    :param replace_lyr: is a boolean specifying whether the vector layer should be
                        replaced (i.e., overwritten). Default=True.
    :param pxl_val_fieldname: is a string to specify the name of the output column
                              representing the pixel value within the input image.
    :param use_8_conn: is a bool specifying whether 8 connectedness or 4 connectedness
                       should be used (4 is RSGISLib/GDAL default)

    """
    gdalImgDS = gdal.Open(input_img)
    imgBand = gdalImgDS.GetRasterBand(img_band)
    imgsrs = osr.SpatialReference()
    imgsrs.ImportFromWkt(gdalImgDS.GetProjectionRef())

    gdalImgMaskDS = None
    imgMaskBand = None
    if mask_img is not None:
        gdalImgMaskDS = gdal.Open(mask_img)
        imgMaskBand = gdalImgMaskDS.GetRasterBand(mask_band)

    if os.path.exists(out_vec_file) and (not replace_file):
        vecDS = gdal.OpenEx(out_vec_file, gdal.GA_Update)
    else:
        outdriver = ogr.GetDriverByName(out_format)
        if os.path.exists(out_vec_file):
            outdriver.DeleteDataSource(out_format)
        vecDS = outdriver.CreateDataSource(out_vec_file)

    if vecDS is None:
        raise rsgislib.RSGISPyException(
            "Could not open or create '{}'".format(out_vec_file)
        )

    lcl_options = []
    if replace_lyr:
        lcl_options = ["OVERWRITE=YES"]

    out_lyr_obj = vecDS.CreateLayer(out_vec_lyr, srs=imgsrs, options=lcl_options)
    if out_lyr_obj is None:
        raise rsgislib.RSGISPyException(
            "Could not create layer: {}".format(out_vec_lyr)
        )

    newField = ogr.FieldDefn(pxl_val_fieldname, ogr.OFTInteger)
    out_lyr_obj.CreateField(newField)
    dstFieldIdx = out_lyr_obj.GetLayerDefn().GetFieldIndex(pxl_val_fieldname)

    try:
        import tqdm

        pbar = tqdm.tqdm(total=100)
        callback = lambda *args, **kw: pbar.update()
    except:
        callback = gdal.TermProgress

    options = list()
    if use_8_conn:
        options.append("8CONNECTED=8")

    print("Polygonising...")
    gdal.Polygonize(
        imgBand, imgMaskBand, out_lyr_obj, dstFieldIdx, options, callback=callback
    )
    print("Completed")
    out_lyr_obj.SyncToDisk()
    vecDS = None
    gdalImgDS = None
    if mask_img is not None:
        gdalImgMaskDS = None


def vectorise_pxls_to_pts(
    input_img: str,
    img_band: int,
    img_msk_val: int,
    out_vec_file: str,
    out_vec_lyr: str = None,
    out_format: str = "GPKG",
    out_epsg_code: int = None,
    del_exist_vec: bool = False,
):
    """
    Function which creates a new output vector file for the pixels within the input
    image file with the value specified. Pixel locations will be the centroid of
    the pixel

    :param input_img: the input image
    :param img_band: the band within the image to use
    :param img_msk_val: the image value selecting the pixels to be converted to points
    :param out_vec_file: Output vector file
    :param out_vec_lyr: output vector layer name.
    :param out_format: output file format (default GPKG).
    :param out_epsg_code: optionally provide an EPSG code for the output layer. If None
                          then taken from input image.
    :param del_exist_vec: remove output file if it exists.

    """
    import geopandas
    from rios import applier

    import rsgislib.imageutils
    import rsgislib.vectorutils

    if TQDM_AVAIL:
        progress_bar = rsgislib.TQDMProgressBar()
    else:
        progress_bar = rios.cuiprogress.GDALProgressBar()

    if os.path.exists(out_vec_file):
        if del_exist_vec:
            rsgislib.vectorutils.delete_vector_file(out_vec_file)
        else:
            raise rsgislib.RSGISPyException(
                "The output vector file ({}) already exists, "
                "remove it and re-run.".format(out_vec_file)
            )

    if out_epsg_code is None:
        out_epsg_code = rsgislib.imageutils.get_epsg_proj_from_img(input_img)

    if out_epsg_code is None:
        raise rsgislib.RSGISPyException(
            "The output ESPG code is None - tried to read from input image and "
            "returned None. Suggest providing the EPSG code to the function."
        )

    pt_x_lst = list()
    pt_y_lst = list()

    infiles = applier.FilenameAssociations()
    infiles.image = input_img
    outfiles = applier.FilenameAssociations()
    otherargs = applier.OtherInputs()
    otherargs.img_band = img_band
    otherargs.img_msk_val = img_msk_val
    otherargs.pt_x_lst = pt_x_lst
    otherargs.pt_y_lst = pt_y_lst
    aControls = applier.ApplierControls()
    aControls.progress = progress_bar

    def _getXYPxlLocs(info, inputs, outputs, otherargs):
        """
        This is an internal rios function
        """
        x_block, y_block = info.getBlockCoordArrays()
        msk_data = inputs.image[0, ...].flatten()
        x_block = x_block.flatten()
        y_block = y_block.flatten()

        x_block = x_block[msk_data == otherargs.img_msk_val]
        y_block = y_block[msk_data == otherargs.img_msk_val]

        otherargs.pt_x_lst.extend(x_block.tolist())
        otherargs.pt_y_lst.extend(y_block.tolist())

    applier.apply(_getXYPxlLocs, infiles, outfiles, otherargs, controls=aControls)

    if len(pt_x_lst) > 0:
        gdf = geopandas.GeoDataFrame(
            geometry=geopandas.points_from_xy(pt_x_lst, pt_y_lst),
            crs="EPSG:{}".format(out_epsg_code),
        )

        if out_format == "GPKG":
            if out_vec_lyr is None:
                raise rsgislib.RSGISPyException(
                    "If output format is GPKG then an output layer is required."
                )
            gdf.to_file(out_vec_file, layer=out_vec_lyr, driver=out_format)
        else:
            gdf.to_file(out_vec_file, driver=out_format)


def extract_image_footprint(
    input_img: str,
    out_vec_file: str,
    out_vec_lyr: str,
    out_format: str = "GPKG",
    tmp_dir: str = "tmp",
    reproj_to: str = None,
    no_data_val: float = None,
):
    """
    A function to extract an image footprint as a vector.

    :param input_img: the input image file for which the footprint will be extracted.
    :param out_vec_file: output vector file path and name.
    :param out_vec_lyr: output vector layer name.
    :param tmp_dir: temp directory which will be used during processing. It will be
                    created and deleted once processing complete.
    :param reproj_to: optional if not None then an ogr2ogr command will be
                      run and the input here is what is to go into the ogr2ogr
                      command after -t_srs. E.g., -t_srs epsg:4326
    """
    gdal.UseExceptions()
    import rsgislib.imageutils
    import rsgislib.tools.filetools
    import rsgislib.tools.utils
    import rsgislib.vectorattrs
    import rsgislib.vectorutils

    if not rsgislib.tools.filetools.does_path_exists_or_creatable(out_vec_file):
        raise rsgislib.RSGISPyException(
            f"Output file path is not creatable: {out_vec_file}"
        )

    uid_str = rsgislib.tools.utils.uid_generator()

    created_tmp = False
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)
        created_tmp = True

    in_img_base = os.path.splitext(os.path.basename(input_img))[0]

    valid_out_img = os.path.join(tmp_dir, f"{in_img_base}_{uid_str}_validimg.tif")
    if no_data_val is None:
        no_data_val = rsgislib.imageutils.get_img_no_data_value(input_img)

    if no_data_val is None:
        raise rsgislib.RSGISPyException("A no data value has not been specified.")
    rsgislib.imageutils.gen_valid_mask(
        input_img, valid_out_img, gdalformat="GTIFF", no_data_val=no_data_val
    )

    out_vec_tmp_file = out_vec_file
    if reproj_to is not None:
        out_vec_tmp_file = os.path.join(
            tmp_dir, f"{in_img_base}_{uid_str}_initVecOut.gpkg"
        )

    polygonise_raster_to_vec_lyr(
        out_vec_tmp_file, out_vec_lyr, out_format, valid_out_img, 1, valid_out_img, 1
    )

    ds = gdal.OpenEx(out_vec_tmp_file, gdal.OF_READONLY)
    if ds is None:
        raise rsgislib.RSGISPyException("Could not open '" + out_vec_tmp_file + "'")

    lyr = ds.GetLayerByName(out_vec_lyr)
    if lyr is None:
        raise rsgislib.RSGISPyException("Could not find layer '" + out_vec_lyr + "'")
    num_feats = lyr.GetFeatureCount()
    lyr = None
    ds = None

    file_name = []
    for i in range(num_feats):
        file_name.append(os.path.basename(input_img))
    rsgislib.vectorattrs.write_vec_column(
        out_vec_tmp_file, out_vec_lyr, "FileName", ogr.OFTString, file_name
    )

    if reproj_to is not None:
        if os.path.exists(out_vec_file):
            rsgislib.vectorutils.delete_vector_file(out_vec_file)

        cmd = [
            "ogr2ogr",
            "-f",
            out_format,
            "-t_srs",
            reproj_to,
            out_vec_file,
            out_vec_tmp_file,
        ]
        print(cmd)
        try:
            import subprocess

            subprocess.run(cmd, check=True)
        except OSError as e:
            raise rsgislib.RSGISPyException(
                "Could not re-projection vector file: {}".format(cmd)
            )

    if created_tmp:
        import shutil

        shutil.rmtree(tmp_dir)
    else:
        if reproj_to is not None:
            driver = ogr.GetDriverByName(out_format)
            driver.DeleteDataSource(out_vec_tmp_file)


def create_poly_vec_for_lst_bboxs(
    csv_file,
    out_vec_file,
    out_vec_lyr,
    out_format,
    epsg_code,
    min_x_col=0,
    max_x_col=1,
    min_y_col=2,
    max_y_col=3,
    ignore_rows=0,
    del_exist_vec=False,
):
    """
    This function takes a CSV file of bounding boxes (1 per line) and creates a
    polygon vector layer.

    :param csv_file: input CSV file.
    :param out_vec_file: output vector file
    :param out_vec_file: output vector layer
    :param out_format: output vector file format (e.g., GPKG)
    :param epsg_code: EPSG code specifying the projection of the data
                     (4326 is WSG84 Lat/Long).
    :param min_x_col: The index (starting at 0) for the column within the CSV file
                    for the minimum X coordinate.
    :param max_x_col: The index (starting at 0) for the column within the CSV file
                    for the maximum X coordinate.
    :param min_y_col: The index (starting at 0) for the column within the CSV file
                    for the minimum Y coordinate.
    :param max_y_col: The index (starting at 0) for the column within the CSV file
                    for the maximum Y coordinate.
    :param ignore_rows: The number of rows to ignore from the start of the CSV
                        file (i.e., column headings)
    :param del_exist_vec: If the output file already exists delete it before proceeding.
    """
    gdal.UseExceptions()
    try:
        if os.path.exists(out_vec_file):
            if del_exist_vec:
                driver = ogr.GetDriverByName(out_format)
                driver.DeleteDataSource(out_vec_file)
            else:
                raise rsgislib.RSGISPyException("Output file already exists")
        # Create the output Driver
        outDriver = ogr.GetDriverByName(out_format)
        # create the spatial reference, WGS84
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(int(epsg_code))
        # Create the output Shapefile
        outDataSource = outDriver.CreateDataSource(out_vec_file)
        outLayer = outDataSource.CreateLayer(out_vec_lyr, srs, geom_type=ogr.wkbPolygon)
        # Get the output Layer's Feature Definition
        featureDefn = outLayer.GetLayerDefn()

        dataFile = open(csv_file, "r")
        rowCount = 0
        for line in dataFile:
            if rowCount >= ignore_rows:
                line = line.strip()
                if line != "":
                    comps = line.split(",")
                    # Get values from CSV file.
                    minX = float(comps[min_x_col])
                    maxX = float(comps[max_x_col])
                    minY = float(comps[min_y_col])
                    maxY = float(comps[max_y_col])
                    # Create Linear Ring
                    ring = ogr.Geometry(ogr.wkbLinearRing)
                    ring.AddPoint(minX, maxY)
                    ring.AddPoint(maxX, maxY)
                    ring.AddPoint(maxX, minY)
                    ring.AddPoint(minX, minY)
                    ring.AddPoint(minX, maxY)
                    # Create polygon.
                    poly = ogr.Geometry(ogr.wkbPolygon)
                    poly.AddGeometry(ring)
                    # Add to output shapefile.
                    outFeature = ogr.Feature(featureDefn)
                    outFeature.SetGeometry(poly)
                    outLayer.CreateFeature(outFeature)
                    outFeature = None
            rowCount = rowCount + 1
        dataFile.close()
        outDataSource = None
    except Exception as e:
        raise e


def define_grid(
    bbox: Union[Tuple[float, float, float, float], List[float]],
    x_size: float,
    y_size: float,
    in_epsg_code: int,
    out_vec_file: str,
    out_vec_lyr: str,
    out_format: str = "GPKG",
    out_epsg_code: int = None,
    utm_grid: bool = False,
    utm_hemi: bool = False,
):
    """
    Define a grid of bounding boxes for a specified bounding box. The output grid can
    be in a different projection to the inputted bounding box. Where a UTM grid is
    required and there are multiple UTM zones then the layer name will be appended
    with utmXX[n|s]. Note. this only works with formats such as GPKG which support
    multiple layers. A shapefile which only supports 1 layer will not work.

    :param bbox: a bounding box (xMin, xMax, yMin, yMax)
    :param x_size: Output grid size in X axis. If out_epsg_code or utm_grid defined
                   then the grid size needs to be in the output unit.
    :param y_size: Output grid size in Y axis. If out_epsg_code or utm_grid defined
                   then the grid size needs to be in the output unit.
    :param in_epsg_code: EPSG code for the projection of the bbox
    :param out_vec_file: output vector file.
    :param out_vec_lyr: output vector layer name.
    :param out_format: output vector file format (see OGR codes). Default is GPKG.
    :param out_epsg_code: if provided the output grid is reprojected to the projection
                          defined by this EPSG code. (note. the grid size needs to
                          the in the unit of this projection). Default is None.
    :param utm_grid: provide the output grid in UTM projection where grid might go
                     across multiple UTM zones. Default is False. grid size unit
                     should be metres.
    :param utm_hemi: if outputting a UTM projected grid then decided whether to use
                     hemispheres or otherwise. If False then everything will be
                     projected northern hemisphere (e.g., as with landsat or
                     sentinel-2). Default is False.
    """
    import rsgislib.tools.geometrytools
    import rsgislib.tools.utm

    if (out_epsg_code is not None) and utm_grid:
        raise rsgislib.RSGISPyException(
            "Cannot specify both new output projection and UTM grid."
        )
    elif utm_grid:
        wgs84_bbox = bbox
        if in_epsg_code != 4326:
            in_proj_obj = osr.SpatialReference()
            in_proj_obj.ImportFromEPSG(in_epsg_code)
            out_proj_obj = osr.SpatialReference()
            out_proj_obj.ImportFromEPSG(4326)
            wgs84_bbox = rsgislib.tools.geometrytools.reproj_bbox(
                bbox, in_proj_obj, out_proj_obj
            )

        multi_zones = False
        if (wgs84_bbox[0] < -180) and (wgs84_bbox[1] < -180):
            wgs84_bbox = [
                360 + wgs84_bbox[0],
                360 + wgs84_bbox[1],
                wgs84_bbox[2],
                wgs84_bbox[3],
            ]
        elif (wgs84_bbox[0] > 180) and (wgs84_bbox[1] > 180):
            wgs84_bbox = [
                360 - wgs84_bbox[0],
                360 - wgs84_bbox[1],
                wgs84_bbox[2],
                wgs84_bbox[3],
            ]
        elif (wgs84_bbox[0] < -180) or (wgs84_bbox[0] > 180):
            multi_zones = True

        if not multi_zones:
            utm_tl = rsgislib.tools.utm.from_latlon(wgs84_bbox[3], wgs84_bbox[0])
            utm_tr = rsgislib.tools.utm.from_latlon(wgs84_bbox[3], wgs84_bbox[1])
            utm_br = rsgislib.tools.utm.from_latlon(wgs84_bbox[2], wgs84_bbox[1])
            utm_bl = rsgislib.tools.utm.from_latlon(wgs84_bbox[2], wgs84_bbox[0])

            utm_top_hemi = "N"
            if utm_hemi and (wgs84_bbox[3] < 0):
                utm_top_hemi = "S"

        if (not multi_zones) and (utm_tl[2] == utm_tr[2] == utm_br[2] == utm_bl[2]):
            utm_zone = utm_tl[2]

            utm_proj_epsg = rsgislib.tools.utm.epsg_for_utm(utm_zone, utm_top_hemi)

            define_grid(
                bbox,
                x_size,
                y_size,
                in_epsg_code,
                out_vec_file,
                out_vec_lyr,
                out_format=out_format,
                out_epsg_code=utm_proj_epsg,
                utm_grid=False,
                utm_hemi=False,
            )
        else:
            multi_zones = True

            utm_zone_bboxs = []
            if wgs84_bbox[0] < -180:
                wgs84_bbox_W = [-180, wgs84_bbox[1], wgs84_bbox[2], wgs84_bbox[3]]
                wgs84_bbox_E = [360 + wgs84_bbox[1], 180, wgs84_bbox[2], wgs84_bbox[3]]

                utm_zone_bboxs = (
                    utm_zone_bboxs
                    + rsgislib.tools.utm.split_wgs84_bbox_utm_zones(wgs84_bbox_W)
                )
                utm_zone_bboxs = (
                    utm_zone_bboxs
                    + rsgislib.tools.utm.split_wgs84_bbox_utm_zones(wgs84_bbox_E)
                )

            elif wgs84_bbox[0] > 180:
                wgs84_bbox_W = [wgs84_bbox[0], 180, wgs84_bbox[2], wgs84_bbox[3]]
                wgs84_bbox_E = [-180, 360 - wgs84_bbox[1], wgs84_bbox[2], wgs84_bbox[3]]

                utm_zone_bboxs = (
                    utm_zone_bboxs
                    + rsgislib.tools.utm.split_wgs84_bbox_utm_zones(wgs84_bbox_W)
                )
                utm_zone_bboxs = (
                    utm_zone_bboxs
                    + rsgislib.tools.utm.split_wgs84_bbox_utm_zones(wgs84_bbox_E)
                )

            else:
                utm_zone_bboxs = rsgislib.tools.utm.split_wgs84_bbox_utm_zones(
                    wgs84_bbox
                )

            in_proj_obj = osr.SpatialReference()
            in_proj_obj.ImportFromEPSG(4326)

            first = True
            for zone_roi in utm_zone_bboxs:
                utm_top_hemi = "N"
                if utm_hemi:
                    if zone_roi[1][3] < 0:
                        utm_top_hemi = "S"

                utm_proj_epsg = int(
                    rsgislib.tools.utm.epsg_for_utm(zone_roi[0], utm_top_hemi)
                )

                out_proj_obj = osr.SpatialReference()
                out_proj_obj.ImportFromEPSG(utm_proj_epsg)

                utm_bbox = rsgislib.tools.geometrytools.reproj_bbox(
                    zone_roi[1], in_proj_obj, out_proj_obj
                )
                bboxs = rsgislib.tools.geometrytools.get_bbox_grid(
                    utm_bbox, x_size, y_size
                )

                utm_out_vec_lyr = out_vec_lyr + "_utm{0}{1}".format(
                    zone_roi[0], utm_top_hemi.lower()
                )
                create_poly_vec_bboxs(
                    out_vec_file,
                    utm_out_vec_lyr,
                    out_format,
                    utm_proj_epsg,
                    bboxs,
                    overwrite=first,
                )
                first = False
    else:
        if out_epsg_code is not None:
            in_proj_obj = osr.SpatialReference()
            in_proj_obj.ImportFromEPSG(in_epsg_code)
            out_proj_obj = osr.SpatialReference()
            out_proj_obj.ImportFromEPSG(out_epsg_code)
            proj_bbox = rsgislib.tools.geometrytools.reproj_bbox(
                bbox, in_proj_obj, out_proj_obj
            )
        else:
            proj_bbox = bbox

        bboxs = rsgislib.tools.geometrytools.get_bbox_grid(proj_bbox, x_size, y_size)

        if out_epsg_code is None:
            create_poly_vec_bboxs(
                out_vec_file, out_vec_lyr, out_format, in_epsg_code, bboxs
            )
        else:
            create_poly_vec_bboxs(
                out_vec_file, out_vec_lyr, out_format, out_epsg_code, bboxs
            )


def create_poly_vec_bboxs(
    vec_file: str,
    vec_lyr: str,
    out_format: str,
    epsg_code: int,
    bboxs: List[Union[Tuple[float, float, float, float], List[float]]],
    atts: Dict[str, List] = None,
    att_types: Dict[str, List] = None,
    overwrite: bool = True,
):
    """
    This function creates a set of polygons for a set of bounding boxes.
    When creating an attribute the available data types are ogr.OFTString,
    ogr.OFTInteger, ogr.OFTReal

    :param vec_file: output vector file/path
    :param vec_lyr: output vector layer
    :param out_format: the output vector layer type.
    :param epsg_code: EPSG code specifying the projection of the data (e.g.,
                      4326 is WSG84 Lat/Long).
    :param bboxs: is a list of bounding boxes ([xMin, xMax, yMin, yMax]) to be
                  saved to the output vector.
    :param atts: is a dict of lists of attributes with the same length as the bboxs
                 list. The dict should be named the same as the attTypes['names'] list.
    :param att_types: is a dict with a list of attribute names (attTypes['names']) and
                     types (attTypes['types']). The list must be the same length as
                     one another and the number of atts. Example type: ogr.OFTString
    :param overwrite: overwrite the vector file specified if it exists. Use False
                      for GPKG where you want to add multiple layers.
    """
    try:
        gdal.UseExceptions()

        if os.path.exists(vec_file) and (not overwrite):
            # Open the output file.
            out_data_source = gdal.OpenEx(vec_file, gdal.GA_Update)
        else:
            # Create the output Driver
            out_driver = ogr.GetDriverByName(out_format)
            # Create the output vector file
            out_data_source = out_driver.CreateDataSource(vec_file)

        # create the spatial reference
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(int(epsg_code))
        out_layer = out_data_source.CreateLayer(vec_lyr, srs, geom_type=ogr.wkbPolygon)

        add_atts = False
        if (atts is not None) and (att_types is not None):
            n_atts = 0
            if "names" not in att_types:
                raise rsgislib.RSGISPyException(
                    'attTypes must include a list for "names"'
                )
            n_atts = len(att_types["names"])
            if "types" not in att_types:
                raise rsgislib.RSGISPyException(
                    'attTypes must include a list for "types"'
                )
            if n_atts != len(att_types["types"]):
                raise rsgislib.RSGISPyException(
                    'attTypes "names" and "types" lists must be the same length.'
                )
            for i in range(n_atts):
                if att_types["names"][i] not in atts:
                    raise rsgislib.RSGISPyException(
                        '"{}" is not within atts'.format(att_types["names"][i])
                    )
                if len(atts[att_types["names"][i]]) != len(bboxs):
                    raise rsgislib.RSGISPyException(
                        '"{}" in atts does not have the same len as bboxs'.format(
                            att_types["names"][i]
                        )
                    )

            for i in range(n_atts):
                field_defn = ogr.FieldDefn(att_types["names"][i], att_types["types"][i])
                if out_layer.CreateField(field_defn) != 0:
                    raise rsgislib.RSGISPyException(
                        "Creating '" + att_types["names"][i] + "' field failed.\n"
                    )
            add_atts = True
        elif not ((atts is None) and (att_types is None)):
            raise rsgislib.RSGISPyException(
                "If atts or attTypes is not None then the other should also not be "
                "none and equalivent in length."
            )

        # Get the output Layer's Feature Definition
        feature_defn = out_layer.GetLayerDefn()

        open_transaction = False
        for n in range(len(bboxs)):
            if not open_transaction:
                out_layer.StartTransaction()
                open_transaction = True

            bbox = bboxs[n]
            # Create Linear Ring
            ring = ogr.Geometry(ogr.wkbLinearRing)
            ring.AddPoint(bbox[0], bbox[3])
            ring.AddPoint(bbox[1], bbox[3])
            ring.AddPoint(bbox[1], bbox[2])
            ring.AddPoint(bbox[0], bbox[2])
            ring.AddPoint(bbox[0], bbox[3])
            # Create polygon.
            poly = ogr.Geometry(ogr.wkbPolygon)
            poly.AddGeometry(ring)
            # Add to output shapefile.
            out_feature = ogr.Feature(feature_defn)
            out_feature.SetGeometry(poly)
            if add_atts:
                # Add Attributes
                for i in range(n_atts):
                    out_feature.SetField(
                        att_types["names"][i], atts[att_types["names"][i]][n]
                    )
            out_layer.CreateFeature(out_feature)
            out_feature = None
            if ((n % 20000) == 0) and open_transaction:
                out_layer.CommitTransaction()
                open_transaction = False

        if open_transaction:
            out_layer.CommitTransaction()
            open_transaction = False
        out_data_source = None
    except Exception as e:
        raise e


def write_pts_to_vec(
    out_vec_file: str,
    out_vec_lyr: str,
    out_format: str,
    epsg_code: int,
    pts_x: List[float],
    pts_y: List[float],
    atts: Dict[str, List] = None,
    att_types: Dict[str, List] = None,
    replace: bool = True,
    file_opts: List[str] = [],
    lyr_opts: List[str] = [],
):
    """
    This function creates a set of polygons for a set of bounding boxes.
    When creating an attribute the available data types are ogr.OFTString,
    ogr.OFTInteger, ogr.OFTReal

    :param out_vec_file: output vector file/path
    :param out_vec_lyr: output vector layer
    :param out_format: the output vector layer type.
    :param epsg_code: EPSG code specifying the projection of the data
                      (e.g., 4326 is WSG84 Lat/Long).
    :param pts_x: is a list of x coordinates.
    :param pts_y: is a list of y coordinates.
    :param atts: is a dict of lists of attributes with the same length as the
                 ptsX & ptsY lists. The dict should be named the same as the
                 attTypes['names'] list.
    :param att_types: is a dict with a list of attribute names (attTypes['names'])
                      and types (attTypes['types']). The list must be the same length
                      as one another and the number of atts. Example type: ogr.OFTString
    :param replace: if the output vector file exists overwrite.
    :param file_opts: Options passed when creating the file. Default: [].
                      Common value might be ["OVERWRITE=YES"]
    :param lyr_opts: Options passed when create the layer Default: []. Common value
                     might be ["OVERWRITE=YES"]
    """
    from osgeo import gdal, ogr, osr

    import rsgislib.vectorutils

    try:
        if len(pts_x) != len(pts_y):
            raise rsgislib.RSGISPyException(
                "The X and Y coordinates lists are not the same length."
            )
        nPts = len(pts_x)

        gdal.UseExceptions()

        if os.path.exists(out_vec_file) and (not replace):
            vecDS = gdal.OpenEx(out_vec_file, gdal.GA_Update)
        else:
            if os.path.exists(out_vec_file):
                rsgislib.vectorutils.delete_vector_file(out_vec_file)
            outdriver = ogr.GetDriverByName(out_format)
            vecDS = outdriver.CreateDataSource(out_vec_file, options=file_opts)

        srs = osr.SpatialReference()
        srs.ImportFromEPSG(int(epsg_code))
        outLayer = vecDS.CreateLayer(
            out_vec_lyr, srs, geom_type=ogr.wkbPoint, options=lyr_opts
        )

        addAtts = False
        if (atts is not None) and (att_types is not None):
            nAtts = 0
            if "names" not in att_types:
                raise rsgislib.RSGISPyException(
                    'attTypes must include a list for "names"'
                )
            nAtts = len(att_types["names"])
            if "types" not in att_types:
                raise rsgislib.RSGISPyException(
                    'attTypes must include a list for "types"'
                )
            if nAtts != len(att_types["types"]):
                raise rsgislib.RSGISPyException(
                    'attTypes "names" and "types" lists must be the same length.'
                )
            for i in range(nAtts):
                if att_types["names"][i] not in atts:
                    raise rsgislib.RSGISPyException(
                        '"{}" is not within atts'.format(att_types["names"][i])
                    )
                if len(atts[att_types["names"][i]]) != len(pts_x):
                    raise rsgislib.RSGISPyException(
                        '"{}" in atts does not have the same len as pts_x'.format(
                            att_types["names"][i]
                        )
                    )

            for i in range(nAtts):
                field_defn = ogr.FieldDefn(att_types["names"][i], att_types["types"][i])
                if outLayer.CreateField(field_defn) != 0:
                    raise rsgislib.RSGISPyException(
                        "Creating '" + att_types["names"][i] + "' field failed.\n"
                    )
            addAtts = True
        elif not ((atts is None) and (att_types is None)):
            raise rsgislib.RSGISPyException(
                "If atts or attTypes is not None then the other should also "
                "not be none and equivlent in length."
            )

        # Get the output Layer's Feature Definition
        featureDefn = outLayer.GetLayerDefn()

        openTransaction = False
        for n in range(nPts):
            if not openTransaction:
                outLayer.StartTransaction()
                openTransaction = True
            # Create Point
            pt = ogr.Geometry(ogr.wkbPoint)
            pt.AddPoint(float(pts_x[n]), float(pts_y[n]))
            # Add to output shapefile.
            outFeature = ogr.Feature(featureDefn)
            outFeature.SetGeometry(pt)
            if addAtts:
                # Add Attributes
                for i in range(nAtts):
                    outFeature.SetField(
                        att_types["names"][i], atts[att_types["names"][i]][n]
                    )
            outLayer.CreateFeature(outFeature)
            outFeature = None
            if ((n % 20000) == 0) and openTransaction:
                outLayer.CommitTransaction()
                openTransaction = False

        if openTransaction:
            outLayer.CommitTransaction()
            openTransaction = False
        vecDS = None
    except Exception as e:
        raise e


def create_bboxs_for_pts(
    vec_file: str,
    vec_lyr: str,
    bbox_width: float,
    bbox_height: float,
    out_vec_file: str,
    out_vec_lyr: str,
    out_format: str = "GPKG",
    del_exist_vec: bool = False,
    epsg_code: int = None,
):
    """
    A function which takes a set of points (from the input vector layer) and creates
    a set of boxes with the same height and width, one for each point.

    Note, the geometry type for the input vector layer must be points.

    :param vec_file: the input vector file/path
    :param vec_lyr: the name of the input vector layer.
    :param bbox_width: width (in the units of the projection) for the output boxes
    :param bbox_height: height (in the units of the projection) for the output boxes
    :param out_vec_file: output vector file/path
    :param out_vec_lyr: output vector layer name
    :param out_format: output vector format.
    :param del_exist_vec: If the output file already exists delete it before proceeding.
    :param epsg_code: if not well defined specify the EPSG code for the projection.

    """
    import rsgislib.vectorutils

    if os.path.exists(out_vec_file):
        if del_exist_vec:
            rsgislib.vectorutils.delete_vector_file(out_vec_file)
        else:
            raise rsgislib.RSGISPyException(
                "The output vector file ({}) already exists, "
                "remove it and re-run.".format(out_vec_file)
            )

    h_width = bbox_width / 2.0
    h_height = bbox_height / 2.0

    vec_ds_obj = gdal.OpenEx(vec_file, gdal.OF_VECTOR)
    if vec_ds_obj is None:
        raise rsgislib.RSGISPyException("The input vector file could not be opened.")
    vec_lyr_obj = vec_ds_obj.GetLayer(vec_lyr)
    if vec_lyr_obj is None:
        raise rsgislib.RSGISPyException("The input vector layer could not be opened.")
    if epsg_code is None:
        epsg_code = rsgislib.vectorutils.get_proj_epsg_from_vec(vec_file, vec_lyr)

    n_feats = vec_lyr_obj.GetFeatureCount(True)
    pbar = tqdm.tqdm(total=n_feats)

    counter = 0
    in_feature = vec_lyr_obj.GetNextFeature()
    out_bboxs = list()
    while in_feature:
        geom = in_feature.GetGeometryRef()
        if geom is not None:
            pt_x = geom.GetX()
            pt_y = geom.GetY()

            x_min = pt_x - h_width
            x_max = pt_x + h_width
            y_min = pt_y - h_height
            y_max = pt_y + h_height

            out_bboxs.append((x_min, x_max, y_min, y_max))

        in_feature = vec_lyr_obj.GetNextFeature()
        counter = counter + 1
        pbar.update(1)

    pbar.close()
    vec_ds_obj = None

    create_poly_vec_bboxs(
        out_vec_file,
        out_vec_lyr,
        out_format,
        epsg_code,
        out_bboxs,
        atts=None,
        att_types=None,
        overwrite=False,
    )


def create_wgs84_vector_grid(
    out_vec_file: str,
    out_vec_lyr: str,
    out_format: str,
    grid_x: float,
    grid_y: float,
    bbox: List[float],
    overlap: float = None,
    tile_names_col: str = "tile_names",
    tile_name_prefix: str = "",
):
    """
    A function which creates a regular grid across a defined area using the
    WGS84 (EPSG:4326) projection.

    :param out_vec_file: output vector file
    :param out_vec_lyr: output vector layer name
    :param out_format: the output vector file format.
    :param grid_x: the size in the x axis of the grid cells (in degrees).
    :param grid_y: the size in the y axis of the grid cells (in degrees).
    :param bbox: the area for which cells will be defined (MinX, MaxX, MinY, MaxY).
    :param overlap: the overlap added to each grid cell. If None then no overlap applied.
    :param tile_names_col: The output column name for the tile names.
    :param tile_name_prefix: A prefix for the tile names.

    """
    import math

    import rsgislib.tools.projection
    import rsgislib.vectorattrs

    epsg_code = 4326
    min_x = float(bbox[0])
    max_x = float(bbox[1])
    min_y = float(bbox[2])
    max_y = float(bbox[3])
    grid_x = float(grid_x)
    grid_y = float(grid_y)

    n_x_cells = math.floor((max_x - min_x) / grid_x)
    x_remain = (max_x - min_x) - (grid_x * n_x_cells)

    n_y_cells = math.floor((max_y - min_y) / grid_y)
    y_remain = (max_y - min_y) - (grid_y * n_y_cells)

    print("Cells: [{0}, {1}]".format(n_x_cells, n_y_cells))

    bboxs = []
    tile_names = []
    for i in range(n_y_cells):
        c_max_y = max_y - (i * grid_y)
        c_min_y = c_max_y - grid_y
        for j in range(n_x_cells):
            c_min_x = min_x + (j * grid_x)
            c_max_x = c_min_x + grid_x
            lat_lon_str_name = rsgislib.tools.projection.get_deg_coord_as_str(
                lat=c_min_x, lon=c_max_y, n_chars=4
            )
            tile_names.append(f"{tile_name_prefix}{lat_lon_str_name}")
            if overlap is None:
                bboxs.append((c_min_x, c_max_x, c_min_y, c_max_y))
            else:
                bboxs.append(
                    (
                        c_min_x - overlap,
                        c_max_x + overlap,
                        c_min_y - overlap,
                        c_max_y + overlap,
                    )
                )
        if x_remain > 0:
            c_min_x = min_x + (n_x_cells * grid_x)
            c_max_x = c_min_x + x_remain
            lat_lon_str_name = rsgislib.tools.projection.get_deg_coord_as_str(
                lat=c_min_x, lon=c_max_y, n_chars=4
            )
            tile_names.append(f"{tile_name_prefix}{lat_lon_str_name}")
            if overlap is None:
                bboxs.append((c_min_x, c_max_x, c_min_y, c_max_y))
            else:
                bboxs.append(
                    (
                        c_min_x - overlap,
                        c_max_x + overlap,
                        c_min_y - overlap,
                        c_max_y + overlap,
                    )
                )
    if y_remain > 0:
        c_max_y = max_y - (n_y_cells * grid_y)
        c_min_y = c_max_y - y_remain
        for j in range(n_x_cells):
            c_min_x = min_x + (j * grid_x)
            c_max_x = c_min_x + grid_x
            lat_lon_str_name = rsgislib.tools.projection.get_deg_coord_as_str(
                lat=c_min_x, lon=c_max_y, n_chars=4
            )
            tile_names.append(f"{tile_name_prefix}{lat_lon_str_name}")
            if overlap is None:
                bboxs.append((c_min_x, c_max_x, c_min_y, c_max_y))
            else:
                bboxs.append(
                    (
                        c_min_x - overlap,
                        c_max_x + overlap,
                        c_min_y - overlap,
                        c_max_y + overlap,
                    )
                )
        if x_remain > 0:
            c_min_x = min_x + (n_x_cells * grid_x)
            c_max_x = c_min_x + x_remain
            lat_lon_str_name = rsgislib.tools.projection.get_deg_coord_as_str(
                lat=c_min_x, lon=c_max_y, n_chars=4
            )
            tile_names.append(f"{tile_name_prefix}{lat_lon_str_name}")
            if overlap is None:
                bboxs.append((c_min_x, c_max_x, c_min_y, c_max_y))
            else:
                bboxs.append(
                    (
                        c_min_x - overlap,
                        c_max_x + overlap,
                        c_min_y - overlap,
                        c_max_y + overlap,
                    )
                )

    for bbox in bboxs:
        if bbox[2] < -180:
            bbox[2] = -180
        if bbox[3] > 180:
            bbox[3] = 180

    create_poly_vec_bboxs(out_vec_file, out_vec_lyr, out_format, epsg_code, bboxs)
    rsgislib.vectorattrs.write_vec_column(
        out_vec_file, out_vec_lyr, tile_names_col, ogr.OFTString, tile_names
    )


def create_vec_for_image(
    input_imgs: List,
    output_dir: str,
    out_format: str = "GeoJSON",
    geometry_type: int = rsgislib.GEOM_PT,
    out_name_replace: Dict = None,
    out_file_ext: str = None,
    del_exist_vec: bool = False,
):
    """
    A function which creates a simple (dummy) vector layer for each input images.
    This function is intended to save time creating vector layers where a vector
    layer is needed for a set of images but digitising some information.

    A single geometry is added to the layer, for a point this is the image centre,
    for a line this is from the TL to BR and for a polygon this is the bbox.

    :param input_imgs: a list of input images.
    :param output_dir: a directory where the output vector layers will be created
    :param out_format: the output format for the vector layers (Default: GeoJSON)
    :param geometry_type: the geometry type of the vector layers (rsgislib.GEOM_PT,
                          rsgislib.GEOM_LINE or rsgislib.GEOM_POLY)
                          Default: rsgislib.GEOM_PT
    :param out_name_replace: a dictionary of replacement values for editing the input
                             image file names. If None (default) then ignored. For
                             example, {"_ortho", ""} will remove '_ortho' from the
                             input file names.
    :param out_file_ext: the output extension for the output files (e.g., geojson)
                         If None (Default) then this will be created.
    :param del_exist_vec: delete the vector files if they already exist (Default: False)

    """
    import tqdm
    from osgeo import ogr, osr

    import rsgislib.imageutils
    import rsgislib.tools.filetools
    import rsgislib.vectorutils

    if out_file_ext is None:
        out_file_ext = rsgislib.vectorutils.get_file_vec_extension(out_format)

    out_geom_type = ogr.wkbPoint
    if geometry_type == rsgislib.GEOM_PT:
        out_geom_type = ogr.wkbPoint
    elif geometry_type == rsgislib.GEOM_LINE:
        out_geom_type = ogr.wkbLineString
    elif geometry_type == rsgislib.GEOM_POLY:
        out_geom_type = ogr.wkbPolygon
    else:
        raise rsgislib.RSGISPyException(
            "Input geometry type was not recognised - only support "
            "rsgislib.GEOM_PT, rsgislib.GEOM_LINE, rsgislib.GEOM_POLY"
        )

    # Create the output driver
    out_driver = ogr.GetDriverByName(out_format)

    for img in tqdm.tqdm(input_imgs):
        basename = rsgislib.tools.filetools.get_file_basename(img, check_valid=True)
        if out_name_replace is not None:
            for rpl_in_str in out_name_replace:
                basename = basename.replace(rpl_in_str, out_name_replace[rpl_in_str])

        out_vec_file = os.path.join(output_dir, f"{basename}.{out_file_ext}")
        out_vec_lyr = basename

        if os.path.exists(out_vec_file):
            if del_exist_vec:
                driver = ogr.GetDriverByName(out_format)
                driver.DeleteDataSource(out_vec_file)
            else:
                raise rsgislib.RSGISPyException("Output file already exists")

        # create the spatial reference
        img_epsg = rsgislib.imageutils.get_epsg_proj_from_img(img)
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(int(img_epsg))

        # Create the output vector source and layer
        out_ds_obj = out_driver.CreateDataSource(out_vec_file)
        out_lyr_obj = out_ds_obj.CreateLayer(out_vec_lyr, srs, geom_type=out_geom_type)
        # Get the output Layer's Feature Definition
        feat_defn_obj = out_lyr_obj.GetLayerDefn()

        img_bbox = rsgislib.imageutils.get_img_bbox(img)

        if geometry_type == rsgislib.GEOM_PT:
            x_pt = img_bbox[0] + ((img_bbox[1] - img_bbox[0]) / 2)
            y_pt = img_bbox[2] + ((img_bbox[3] - img_bbox[2]) / 2)
            geom = ogr.Geometry(ogr.wkbPoint)
            geom.AddPoint(x_pt, y_pt)
        elif geometry_type == rsgislib.GEOM_LINE:
            geom = ogr.Geometry(ogr.wkbLineString)
            geom.AddPoint(img_bbox[0], img_bbox[3])
            geom.AddPoint(img_bbox[1], img_bbox[2])
        elif geometry_type == rsgislib.GEOM_POLY:
            ring = ogr.Geometry(ogr.wkbLinearRing)
            ring.AddPoint(img_bbox[0], img_bbox[3])
            ring.AddPoint(img_bbox[1], img_bbox[3])
            ring.AddPoint(img_bbox[1], img_bbox[2])
            ring.AddPoint(img_bbox[0], img_bbox[2])
            ring.AddPoint(img_bbox[0], img_bbox[3])
            geom = ogr.Geometry(ogr.wkbPolygon)
            geom.AddGeometry(ring)
        else:
            raise rsgislib.RSGISPyException("Do not recognise geometry type")

        out_feat_obj = ogr.Feature(feat_defn_obj)
        out_feat_obj.SetGeometry(geom)
        out_lyr_obj.CreateFeature(out_feat_obj)
        out_feat_obj = None
        out_lyr_obj.SyncToDisk()
        out_ds_obj = None


def create_hex_grid_bbox(
    bbox: Union[Tuple[float, float, float, float], List[float]],
    bbox_epsg: int,
    hex_scale: int,
    out_vec_file: str,
    out_vec_lyr: str,
    out_format: str,
):
    """
    A function which uses the h3 library (https://uber.github.io/h3-py/intro.html)
    to create a hexagon grid for the region of interest specified by the bbox.

    :param bbox: the bbox (xMin, xMax, yMin, yMax) defining the region of interest.
    :param bbox_epsg: the epsg code for the bbox.
    :param hex_scale: the scale of the hexagons produced. A lower number will produce
                      few hexagons. The scale is an integer value.
    :param out_vec_file: The output vector file name and path
    :param out_vec_lyr: The output vector layer name.
    :param out_format: The output vector file format (e.g., GPKG or GeoJSON).

    """
    import geopandas
    import h3
    from shapely.geometry import Polygon
    import shapely

    import rsgislib.tools.geometrytools

    if bbox_epsg != 4326:
        bbox_wgs84 = rsgislib.tools.geometrytools.reproj_bbox_epsg(
            bbox, bbox_epsg, 4326
        )
    else:
        bbox_wgs84 = bbox

    bbox_poly = rsgislib.tools.geometrytools.get_bbox_geojson_poly(bbox_wgs84)

    hexs = h3.h3shape_to_cells(h3.geo_to_h3shape(bbox_poly), hex_scale)

    polygonise = lambda hex_id: Polygon(h3.cell_to_boundary(hex_id))

    all_polys = geopandas.GeoSeries(
        list(map(polygonise, hexs)), index=hexs, crs="EPSG:4326"
    )
    print("{} hexagons have been created.".format(all_polys.shape[0]))

    if all_polys.shape[0] > 0:
        h3_all = geopandas.GeoDataFrame(
            {"geometry": all_polys, "hex_id": all_polys.index}, crs=all_polys.crs
        )
        h3_all["geometry"] = h3_all.geometry.map(
            lambda polygon: shapely.ops.transform(lambda x, y: (y, x), polygon)
        )

        if bbox_epsg != 4326:
            h3_all = h3_all.to_crs(f"EPSG:{bbox_epsg}")

        if out_format == "GPKG":
            h3_all.to_file(out_vec_file, layer=out_vec_lyr, driver=out_format)
        else:
            h3_all.to_file(out_vec_file, driver=out_format)
    else:
        print("No file created as there were no hexagons created")


def create_hex_grid_poly(poly_series, hex_scale: int):
    """
    A function which creates a set of hexagons using the h3 library
    (https://uber.github.io/h3-py/intro.html) for the polygon provided
    as a geoseries. The geoseries must have a length of 1. Used by
    the function create_hex_grid_polys. The polygon must be in EPSG:4326
    (WGS84) projection.

    :param poly_series: polygon provided as geopandas
    :param hex_scale: 1 - 8 is probably appropriate.
    :return: geopandas dataframe with hexagons.

    """
    import geopandas
    import shapely
    import h3
    from shapely.geometry import MultiPolygon, Polygon

    geom = poly_series.geometry

    if geom.has_z:
        if geom.geom_type == "Polygon":
            lines = [xy[:2] for xy in list(geom.exterior.coords)]
            geom = Polygon(lines)
        elif geom.geom_type == "MultiPolygon":
            new_multi_p = []
            for ap in geom:
                lines = [xy[:2] for xy in list(ap.exterior.coords)]
                new_p = Polygon(lines)
                new_multi_p.append(new_p)
            geom = MultiPolygon(new_multi_p)

    hexs = h3.h3shape_to_cells(h3.geo_to_h3shape(geom.__geo_interface__), hex_scale)

    polygonise = lambda hex_id: Polygon(h3.cell_to_boundary(hex_id))

    all_polys = geopandas.GeoSeries(
        list(map(polygonise, hexs)), index=hexs, crs="EPSG:4326"
    )

    if all_polys.shape[0] > 0:
        h3_all = geopandas.GeoDataFrame(
            {"geometry": all_polys, "hex_id": all_polys.index}, crs=all_polys.crs
        )
        h3_all["geometry"] = h3_all.geometry.map(
            lambda polygon: shapely.ops.transform(lambda x, y: (y, x), polygon)
        )
    else:
        h3_all = None
    return h3_all


def create_hex_grid_polys(
    vec_in_file: str,
    vec_in_lyr: str,
    hex_scale: int,
    out_vec_file: str,
    out_vec_lyr: str,
    out_format: str,
):
    """
    A function which uses the h3 library (https://uber.github.io/h3-py/intro.html)
    to create a hexagon grid for the region of interest provided by polygon(s) in
    the input vector layer. If the input layer is not EPSG:4326 (WGS84) it will
    be reprojected and the resulting hexagon grid reprojected back to the projection
    of the input vector layer.

    :param vec_in_file: Input vector file
    :param vec_in_lyr: Input vector layer name
    :param hex_scale: the scale of the hexagons produced. A lower number will produce
                      few hexagons. The scale is an integer value.
    :param out_vec_file: The output vector file name and path
    :param out_vec_lyr: The output vector layer name.
    :param out_format: The output vector file format (e.g., GPKG or GeoJSON).

    """
    import geopandas
    import pandas

    polys_gpdf = geopandas.read_file(vec_in_file, layer=vec_in_lyr)
    crs_in_obj = polys_gpdf.crs

    reproj_poly = False
    if crs_in_obj.to_epsg() != 4326:
        print("Reprojecting to EPSG:4326")
        polys_gpdf = polys_gpdf.to_crs(f"EPSG:4326")
        reproj_poly = True

    hex_lst = list()
    for i in tqdm.tqdm(range(len(polys_gpdf))):
        hex_tmp_gpdf = create_hex_grid_poly(polys_gpdf.iloc[i], hex_scale)
        if hex_tmp_gpdf is not None:
            hex_lst.append(hex_tmp_gpdf)

    if len(hex_lst) > 0:
        hex_gpdf = pandas.concat(hex_lst)

        if len(hex_gpdf) > 0:
            if reproj_poly:
                print("Reproject hexagon output")
                hex_gpdf = hex_gpdf.to_crs(crs_in_obj)

            print("Output Vector File")
            if out_format == "GPKG":
                hex_gpdf.to_file(out_vec_file, layer=out_vec_lyr, driver=out_format)
            else:
                hex_gpdf.to_file(out_vec_file, driver=out_format)


def create_random_pts_in_radius(
    centre_x: float,
    centre_y: float,
    radius: float,
    n_pts: int,
    epsg_code: int,
    out_vec_file: str,
    out_vec_lyr: str,
    out_format: str = "GPKG",
    rnd_seed: int = None,
    n_pts_multi_bbox: float = 3,
):
    """
    A function which generates a set of random points within a radius from the
    defined centre point and exports to a vector file. The output vector is
    populated with the distance and angle from the centre to the individual points.
    Note, that the distance and angle calculate is only valid for a projected
    coordinate system (i.e., is it not valid for lat/lon).

    :param centre_x: The x coordinate of the centre point
    :param centre_y: The y coordinate of the centre point
    :param radius: the radius (in unit of coordinate system) defining the
                   region of interest
    :param n_pts: the number of points to be generated.
    :param epsg_code: the EPSG code for the projection of the points.
    :param out_vec_file: the output file path and name.
    :param out_vec_lyr: the output layer name.
    :param out_format: the output file format (Default: GeoJSON)
    :param rnd_seed: the seed for the random generator.
    :param n_pts_multi_bbox: the multiplier used to define the number of points
                             generated within the bbox of the circle which is then
                             subset. 3 should always be enough but lowing to 2
                             will reduce the memory footprint and speed up runtime.
                             In rare cases you might need to increase this if an
                             insufficient number of points were found within the
                             radius specified.

    """
    import numpy
    import geopandas

    # Set the random seed.
    numpy.random.seed(seed=rnd_seed)

    # Define Boundary Box
    bbox = [centre_x - radius, centre_x + radius, centre_y - radius, centre_y + radius]

    # Create more than needed points within the bbox.
    x_coords = numpy.random.uniform(bbox[0], bbox[1], int(n_pts * n_pts_multi_bbox))
    y_coords = numpy.random.uniform(bbox[2], bbox[3], int(n_pts * n_pts_multi_bbox))

    # Calculate the distance from the centre to all the points.
    dist = numpy.sqrt((x_coords - centre_x) ** 2 + (y_coords - centre_y) ** 2)

    # Subset the points to those which are within the radius specified.
    x_coords = x_coords[dist <= radius]
    y_coords = y_coords[dist <= radius]

    # Check there are enough points within the radius
    n_coords_in_rad = y_coords.shape[0]
    if n_coords_in_rad < n_pts:
        raise Exception(
            "An insufficient number of points are within the radius; "
            "increase n_pts_multi_bbox."
        )

    # Find the indices to subset the points to the number required.
    sel_coords = numpy.random.choice(
        numpy.arange(n_coords_in_rad), size=n_pts, replace=False
    )

    # Subset the points to the number required.
    x_coords = x_coords[sel_coords]
    y_coords = y_coords[sel_coords]

    # Create geopandas dataframe with the points.
    data_gdf = geopandas.GeoDataFrame(
        geometry=geopandas.points_from_xy(x=x_coords, y=y_coords), crs=epsg_code
    )

    # Add coordinates as attributes to the points
    data_gdf["x_coords"] = x_coords
    data_gdf["y_coords"] = y_coords

    # Calculate the distance from the centre to each of the points
    data_gdf["dist"] = numpy.sqrt(
        (x_coords - centre_x) ** 2 + (y_coords - centre_y) ** 2
    )

    # Calculate the angle from the centre to each of the points
    angles = numpy.rad2deg(numpy.arctan2(y_coords - centre_y, x_coords - centre_x))

    # Reorientates the angle so 0 is north.
    angles_secs = numpy.zeros_like(angles)
    angles_secs[numpy.logical_and((angles >= 0), (angles <= 90))] = 1
    angles_secs[angles > 90] = 2
    angles_secs[angles < 0] = 3

    angles[angles_secs == 1] = angles[angles_secs == 1] - 90.0
    angles[angles_secs == 1] *= -1
    angles[angles_secs == 2] = angles[angles_secs == 2] - 180.0
    angles[angles_secs == 2] *= -1
    angles[angles_secs == 2] += 270.0
    angles[angles_secs == 3] *= -1
    angles[angles_secs == 3] += 90.0

    data_gdf["angle"] = angles

    # Export the points
    if out_format == "GPKG":
        if out_vec_lyr is None:
            import rsgislib.tools.filetools

            out_vec_lyr = rsgislib.tools.filetools.get_file_basename(
                out_vec_file, check_valid=True
            )
        data_gdf.to_file(out_vec_file, layer=out_vec_lyr, driver=out_format)
    else:
        data_gdf.to_file(out_vec_file, driver=out_format)


def create_lines_vec(
    vec_file: str,
    vec_lyr: str,
    out_format: str,
    epsg_code: int,
    lines: List[List[Tuple[float, float]]],
    overwrite: bool = True,
):
    """
    This function creates a set of lines from a list of points.

    :param vec_file: output vector file/path
    :param vec_lyr: output vector layer
    :param out_format: the output vector layer type.
    :param epsg_code: EPSG code specifying the projection of the data (e.g.,
                      4326 is WSG84 Lat/Long).
    :param lines: is a list of lines where each line is defined as a list
                  of tuples (X, Y).
    :param overwrite: overwrite the vector file specified if it exists. Use False
                      for GPKG where you want to add multiple layers.
    """
    import rsgislib.vectorutils

    gdal.UseExceptions()

    if os.path.exists(vec_file) and (not overwrite):
        # Open the output file.
        out_data_source = gdal.OpenEx(vec_file, gdal.GA_Update)
    else:
        if os.path.exists(vec_file):
            rsgislib.vectorutils.delete_vector_file(vec_file, feedback=False)

        # Create the output Driver
        out_driver = ogr.GetDriverByName(out_format)
        # Create the output vector file
        out_data_source = out_driver.CreateDataSource(vec_file)

    # create the spatial reference
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(int(epsg_code))
    out_layer = out_data_source.CreateLayer(vec_lyr, srs, geom_type=ogr.wkbLineString)

    field_defn = ogr.FieldDefn("line_id", ogr.OFTInteger)
    if out_layer.CreateField(field_defn) != 0:
        raise rsgislib.RSGISPyException("Creating 'line_id' field failed.")

    # Get the output Layer's Feature Definition
    feature_defn = out_layer.GetLayerDefn()

    open_transaction = False
    for n in range(len(lines)):
        if not open_transaction:
            out_layer.StartTransaction()
            open_transaction = True

        # Create Line
        line_geom = ogr.Geometry(ogr.wkbLineString)
        for pt in lines[n]:
            line_geom.AddPoint(pt[0], pt[1])

        # Add to output vector layer.
        out_feature = ogr.Feature(feature_defn)
        out_feature.SetGeometry(line_geom)
        out_feature.SetField("line_id", n + 1)
        out_layer.CreateFeature(out_feature)
        out_feature = None
        if ((n % 20000) == 0) and open_transaction:
            out_layer.CommitTransaction()
            open_transaction = False

    if open_transaction:
        out_layer.CommitTransaction()
        open_transaction = False
    out_data_source = None


def create_img_transects(
    input_img: str,
    out_vec_file: str,
    out_vec_lyr: str,
    x_intervals: List[float] = None,
    y_intervals: List[float] = None,
    out_format: str = "GPKG",
):
    """
    A function which will create transects across an image in both X and Y axis'.
    To specify the transect using the x_intervals and y_intervals parameters.
    These are lists of values between 0 and 1 where a value of 0.5 is halfway
    along the axis.  Therefore, an input of [0.25, 0.5, 0.75] will create
    transects for the axis specified at a quarter, half and three-quarters of
    the way along the axis. You must specify at least one or x_intervals or
    y_intervals.

    :param input_img: The input image path
    :param out_vec_file: the output vector path
    :param out_vec_lyr: the output vector layer name
    :param x_intervals: the list of intervals for the X axis (values between 0-1).
                        If None then the axis is ignored.
    :param y_intervals: the list of intervals for the Y axis (values between 0-1).
                        If None then the axis is ignored.
    :param out_format: the output vector format (Default: GPKG)

    """
    import rsgislib.imageutils
    import numpy

    if (x_intervals is None) and (y_intervals is None):
        raise rsgislib.RSGISPyException(
            "You need to provided a list of values for at "
            "least one of x_intervals or y_intervals"
        )

    if x_intervals is not None:
        x_intervals = numpy.array(x_intervals)
        for val in x_intervals:
            if (val < 0) or (val > 1):
                raise rsgislib.RSGISPyException("Interval values must be between 0-1")

    if y_intervals is not None:
        y_intervals = numpy.array(y_intervals)
        for val in y_intervals:
            if (val < 0) or (val > 1):
                raise rsgislib.RSGISPyException("Interval values must be between 0-1")

    img_bbox = rsgislib.imageutils.get_img_bbox(input_img)
    img_epsg = rsgislib.imageutils.get_epsg_proj_from_img(input_img)

    img_width = img_bbox[1] - img_bbox[0]
    img_height = img_bbox[3] - img_bbox[2]

    out_lines_lst = list()
    if x_intervals is not None:
        x_splits = img_width * x_intervals
        for x_pos in x_splits:
            out_lines_lst.append(
                [(img_bbox[0] + x_pos, img_bbox[2]), (img_bbox[0] + x_pos, img_bbox[3])]
            )

    if y_intervals is not None:
        y_splits = img_height * y_intervals
        for y_pos in y_splits:
            out_lines_lst.append(
                [(img_bbox[0], img_bbox[2] + y_pos), (img_bbox[1], img_bbox[2] + y_pos)]
            )

    create_lines_vec(
        vec_file=out_vec_file,
        vec_lyr=out_vec_lyr,
        out_format=out_format,
        epsg_code=img_epsg,
        lines=out_lines_lst,
        overwrite=True,
    )


def create_random_pts_in_bbox(
    bbox: Union[Tuple[float, float, float, float], List[float]],
    n_pts: int,
    epsg_code: int,
    out_vec_file: str,
    out_vec_lyr: str,
    out_format: str = "GPKG",
    rnd_seed: int = None,
):
    """
    A function which generates a set of random points within a boundary
    box.

    :param bbox: The bounding box the points ([xMin, xMax, yMin, yMax])
    :param n_pts: the number of points to be generated.
    :param epsg_code: the EPSG code for the projection of the points.
    :param out_vec_file: the output file path and name.
    :param out_vec_lyr: the output layer name.
    :param out_format: the output file format (Default: GeoJSON)
    :param rnd_seed: the seed for the random generator.

    """
    import numpy
    import geopandas

    # Set the random seed.
    numpy.random.seed(seed=rnd_seed)

    # Create more than needed points within the bbox.
    x_coords = numpy.random.uniform(bbox[0], bbox[1], n_pts)
    y_coords = numpy.random.uniform(bbox[2], bbox[3], n_pts)

    # Create geopandas dataframe with the points.
    data_gdf = geopandas.GeoDataFrame(
        geometry=geopandas.points_from_xy(x=x_coords, y=y_coords), crs=epsg_code
    )

    # Export the points
    if out_format == "GPKG":
        if out_vec_lyr is None:
            import rsgislib.tools.filetools

            out_vec_lyr = rsgislib.tools.filetools.get_file_basename(
                out_vec_file, check_valid=True
            )
        data_gdf.to_file(out_vec_file, layer=out_vec_lyr, driver=out_format)
    else:
        data_gdf.to_file(out_vec_file, driver=out_format)


def create_binary_random_pt_smpls(
    input_img: str,
    n_smpls: int,
    out_vec_file: str,
    out_vec_lyr: str,
    out_format: str = "GPKG",
    rnd_seed: int = None,
    img_band: int = 1,
    pt_name: str = None,
):
    """
    A function which generates a set of random points within a binary mask. The
    samples are only selected within pixels which have a value of 1.

    :param input_img: Input image path.
    :param n_smpls: The number of points to be generated - if larger than the
                    number of pixels (with a value == 1) then all the pixels will
                    be outputted.
    :param out_vec_file: Output file name and path
    :param out_vec_lyr: Output layer name
    :param out_format: Output vector format. Default: GPKG
    :param rnd_seed: A random seed for generating the random selection of the points.
    :param img_band: The band number to be sampled.
    :param pt_name: If not None then a 'name' column is added to the output vector
                    and all the points have the value within pt_name (e.g., class
                    names)

    """
    import secrets
    import pandas
    import geopandas
    import rsgislib.imageutils

    img_bbox = rsgislib.imageutils.get_img_bbox(input_img)
    img_min_x = img_bbox[0]
    img_max_y = img_bbox[3]

    img_res_x, img_res_y = rsgislib.imageutils.get_img_res(input_img, abs_vals=True)
    x_size, y_size = rsgislib.imageutils.get_img_size(input_img)
    img_epsg = rsgislib.imageutils.get_epsg_proj_from_img(input_img)

    if rnd_seed is None:
        rnd_seed = secrets.randbits(128)
    else:
        rnd_seed = abs(rnd_seed)

    rng = numpy.random.default_rng(rnd_seed)

    image_ds = gdal.Open(input_img, gdal.GA_ReadOnly)
    if image_ds is None:
        raise rsgislib.RSGISPyException(
            "Could not open the input image file: '{}'".format(input_img)
        )
    image_band = image_ds.GetRasterBand(img_band)
    if image_band is None:
        raise rsgislib.RSGISPyException("The image band wasn't opened")

    img_data = image_band.ReadAsArray()
    image_ds = None

    n_out_smpls = n_smpls
    n_bin_pxls = numpy.sum(img_data == 1)
    if n_bin_pxls < n_out_smpls:
        n_out_smpls = n_bin_pxls

    x_coords = img_min_x + (numpy.arange(x_size) + 0.5) * img_res_x
    y_coords = img_max_y - (numpy.arange(y_size) + 0.5) * img_res_y
    x_grid, y_grid = numpy.meshgrid(x_coords, y_coords)

    img_data_flat = img_data.flatten()
    x_grid_flat = x_grid.flatten()
    y_grid_flat = y_grid.flatten()

    x_grid_flat_mskd = x_grid_flat[img_data_flat == 1]
    y_grid_flat_mskd = y_grid_flat[img_data_flat == 1]

    if n_out_smpls < x_grid_flat_mskd.shape[0]:
        indices = rng.choice(len(x_grid_flat_mskd), size=n_out_smpls, replace=False)

        x_coords_arr = x_grid_flat_mskd[indices]
        y_coords_arr = y_grid_flat_mskd[indices]

    else:
        x_coords_arr = x_grid_flat_mskd
        y_coords_arr = y_grid_flat_mskd

    pt_names = list()

    data_dict = dict()
    data_dict["tmp_x"] = x_coords_arr
    data_dict["tmp_y"] = y_coords_arr
    data_df = pandas.DataFrame(data=data_dict)

    pts_gdf = geopandas.GeoDataFrame(
        data_df,
        geometry=geopandas.points_from_xy(data_df.tmp_x, data_df.tmp_y),
        crs=f"EPSG:{img_epsg}",
    )
    pts_gdf = pts_gdf.drop(columns=["tmp_x", "tmp_y"])
    pts_gdf["ID"] = numpy.arange(1, len(pts_gdf) + 1, 1)
    if pt_name is not None:
        pts_gdf["name"] = pt_name

    if out_format == "GPKG":
        pts_gdf.to_file(out_vec_file, layer=out_vec_lyr, driver=out_format)
    else:
        pts_gdf.to_file(out_vec_file, driver=out_format)
