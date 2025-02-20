#! /usr/bin/env python
############################################################################
#  tiledsegsingle.py
#
#  Copyright 2016 RSGISLib.
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
# Purpose:  Provide functionality to perform the shepherd segmentation
#           algorithm using a tiled implementation but only with a single
#           thread of execution (i.e., it will not used mulitple cores/processors)
#
# Author: Pete Bunting
# Email: petebunting@mac.com
# Date: 4/3/2016
# Version: 1.1
#
# History:
# Version 1.0 - Created.
#
###########################################################################

import glob
import os
import json
import shutil

from osgeo import gdal
from rios import rat

import rsgislib
from rsgislib.imageutils import tilingutils
from rsgislib.segmentation import shepherdseg
from rsgislib import rastergis
from rsgislib import imageutils
from rsgislib import segmentation


class RSGISTiledShepherdSegmentationSingleThread(object):
    """
    A class for running the tiled version of the Shepherd et al (2019) segmentation algorithm.
    This can process larger images than the single scene version with a smaller
    memory footprint.

    Shepherd, J. D., Bunting, P., & Dymond, J. R. (2019). Operational Large-Scale Segmentation of Imagery Based on Iterative Elimination. Remote Sensing, 11(6), 658. http://doi.org/10.3390/rs11060658

    This version can only used a single thread for execution.

    It is not intended that this class will be directly used. Please use the
    function perform_tiled_segmentation to call this functionality.

    """

    def findSegStatsFiles(self, tileImg, segStatsInfo):
        gdalDS = gdal.Open(tileImg, gdal.GA_ReadOnly)
        geotransform = gdalDS.GetGeoTransform()
        if not geotransform is None:
            xMin = geotransform[0]
            yMax = geotransform[3]

            xRes = geotransform[1]
            yRes = geotransform[5]

            width = gdalDS.RasterXSize * xRes
            if yRes < 0:
                yRes = yRes * (-1)
            height = gdalDS.RasterYSize * yRes
            xMax = xMin + width
            yMin = xMax - height

            xCen = xMin + (width / 2)
            yCen = yMin + (height / 2)
        gdalDS = None

        first = True
        minDist = 0.0
        minKCenFile = ""
        minStchStatsFile = ""
        for tileName in segStatsInfo:
            tileXCen = segStatsInfo[tileName]["CENTRE_PT"]["X"]
            tileYCen = segStatsInfo[tileName]["CENTRE_PT"]["Y"]
            dist = ((tileXCen - xCen) * (tileXCen - xCen)) + (
                (tileYCen - yCen) * (tileYCen - yCen)
            )
            if first:
                minKCenFile = segStatsInfo[tileName]["KCENTRES"]
                minStchStatsFile = segStatsInfo[tileName]["STRETCHSTATS"]
                minDist = dist
                first = False
            elif dist < minDist:
                minKCenFile = segStatsInfo[tileName]["KCENTRES"]
                minStchStatsFile = segStatsInfo[tileName]["STRETCHSTATS"]
                minDist = dist

        return minKCenFile, minStchStatsFile

    def performStage1Tiling(
        self,
        inputImage,
        tileShp,
        tilesRat,
        tilesBase,
        tilesMetaDIR,
        tilesImgDIR,
        tmpDIR,
        width,
        height,
        validDataThreshold,
    ):
        tilingutils.createMinDataTiles(
            inputImage,
            tileShp,
            tilesRat,
            width,
            height,
            validDataThreshold,
            None,
            False,
            True,
            tmpDIR,
        )
        tilingutils.createTileMaskImagesFromClumps(
            tilesRat, tilesBase, tilesMetaDIR, "KEA"
        )
        dataType = rsgislib.imageutils.get_rsgislib_datatype_from_img(inputImage)
        tilingutils.createTilesFromMasks(
            inputImage, tilesBase, tilesMetaDIR, tilesImgDIR, dataType, "KEA"
        )

    def performStage1TilesSegmentation(
        self,
        tilesImgDIR,
        stage1TilesSegsDIR,
        tmpDIR,
        tilesBase,
        tileSegInfoJSON,
        strchStatsBase,
        kCentresBase,
        numClustersVal,
        minPxlsVal,
        distThresVal,
        bandsVal,
        samplingVal,
        kmMaxIterVal,
    ):
        imgTiles = glob.glob(os.path.join(tilesImgDIR, tilesBase + "*.kea"))
        tileStatsFiles = dict()
        for imgTile in imgTiles:
            baseName = os.path.splitext(os.path.basename(imgTile))[0]
            tileID = baseName.split("_")[-1]
            clumpsFile = os.path.join(stage1TilesSegsDIR, baseName + "_segs.kea")
            tmpStatsJSON = os.path.join(tilesImgDIR, baseName + "_segstats.json")
            strchStatsOutFile = strchStatsBase + "_" + tileID + ".txt"
            kCentresOutFile = kCentresBase + "_" + tileID
            print(clumpsFile)
            shepherdseg.runShepherdSegmentation(
                imgTile,
                clumpsFile,
                outputMeanImg=None,
                tmpath=os.path.join(tmpDIR, tileID + "_segstemp"),
                gdalformat="KEA",
                noStats=False,
                noStretch=False,
                noDelete=False,
                numClusters=numClustersVal,
                minPxls=minPxlsVal,
                distThres=distThresVal,
                bands=bandsVal,
                sampling=samplingVal,
                kmMaxIter=kmMaxIterVal,
                processInMem=False,
                saveProcessStats=True,
                imgStretchStats=strchStatsOutFile,
                kMeansCentres=kCentresOutFile,
                imgStatsJSONFile=tmpStatsJSON,
            )

            with open(tmpStatsJSON, "r") as f:
                jsonStrData = f.read()
            segStatsInfo = json.loads(jsonStrData)
            tileStatsFiles[baseName] = segStatsInfo
            rsgislib.tools.filetools.delete_file_silent(tmpStatsJSON)

        with open(tileSegInfoJSON, "w") as outfile:
            json.dump(
                tileStatsFiles,
                outfile,
                sort_keys=True,
                indent=4,
                separators=(",", ": "),
                ensure_ascii=False,
            )

    def defineStage1Boundaries(self, tilesImgDIR, stage1TilesSegBordersDIR, tilesBase):
        segTiles = glob.glob(os.path.join(tilesImgDIR, tilesBase + "*_segs.kea"))
        for segTile in segTiles:
            baseName = os.path.splitext(os.path.basename(segTile))[0]
            borderMaskFile = os.path.join(
                stage1TilesSegBordersDIR, baseName + "_segsborder.kea"
            )
            rastergis.defineBorderClumps(segTile, "BoundaryClumps")
            rastergis.export_col_to_gdal_img(
                segTile, borderMaskFile, "KEA", rsgislib.TYPE_8UINT, "BoundaryClumps"
            )

    def mergeStage1TilesToOutput(
        self,
        inputImage,
        tilesSegsDIR,
        tilesSegsBordersDIR,
        tilesBase,
        clumpsImage,
        bordersImage,
    ):
        segTiles = glob.glob(os.path.join(tilesSegsDIR, tilesBase + "*_segs.kea"))
        imageutils.create_copy_img(
            inputImage, clumpsImage, 1, 0, "KEA", rsgislib.TYPE_32UINT
        )
        segmentation.merge_clump_images(segTiles, clumpsImage)
        rastergis.pop_rat_img_stats(clumpsImage, True, True)

        tileBorders = glob.glob(
            os.path.join(tilesSegsBordersDIR, tilesBase + "*_segsborder.kea")
        )
        imageutils.create_copy_img(
            inputImage, bordersImage, 1, 0, "KEA", rsgislib.TYPE_8UINT
        )
        imageutils.includeImages(bordersImage, tileBorders)
        rastergis.pop_rat_img_stats(bordersImage, True, True)

    def performStage2Tiling(
        self,
        inputImage,
        tileShp,
        tilesRat,
        tilesBase,
        tilesMetaDIR,
        tilesImgDIR,
        tmpDIR,
        width,
        height,
        validDataThreshold,
        bordersImage,
    ):
        tilingutils.createMinDataTiles(
            inputImage,
            tileShp,
            tilesRat,
            width,
            height,
            validDataThreshold,
            bordersImage,
            True,
            True,
            tmpDIR,
        )
        tilingutils.createTileMaskImagesFromClumps(
            tilesRat, tilesBase, tilesMetaDIR, "KEA"
        )
        dataType = rsgislib.imageutils.get_rsgislib_datatype_from_img(inputImage)
        tilingutils.createTilesFromMasks(
            inputImage, tilesBase, tilesMetaDIR, tilesImgDIR, dataType, "KEA"
        )

    def performStage2TilesSegmentation(
        self,
        tilesImgDIR,
        tilesMaskedDIR,
        tilesSegsDIR,
        tilesSegBordersDIR,
        tmpDIR,
        tilesBase,
        s1BordersImage,
        segStatsInfo,
        minPxlsVal,
        distThresVal,
        bandsVal,
    ):
        imgTiles = glob.glob(os.path.join(tilesImgDIR, tilesBase + "*.kea"))
        for imgTile in imgTiles:
            baseName = os.path.splitext(os.path.basename(imgTile))[0]
            maskedFile = os.path.join(tilesMaskedDIR, baseName + "_masked.kea")
            dataType = rsgislib.imageutils.get_rsgislib_datatype_from_img(imgTile)
            imageutils.mask_img(
                imgTile, s1BordersImage, maskedFile, "KEA", dataType, 0, 0
            )

        imgTiles = glob.glob(os.path.join(tilesMaskedDIR, tilesBase + "*_masked.kea"))
        for imgTile in imgTiles:
            baseName = os.path.splitext(os.path.basename(imgTile))[0]
            clumpsFile = os.path.join(tilesSegsDIR, baseName + "_segs.kea")
            kMeansCentres, imgStretchStats = self.findSegStatsFiles(
                imgTile, segStatsInfo
            )
            shepherdseg.runShepherdSegmentationPreCalcdStats(
                imgTile,
                clumpsFile,
                kMeansCentres,
                imgStretchStats,
                outputMeanImg=None,
                tmpath=os.path.join(tmpDIR, baseName + "_segstemp"),
                gdalformat="KEA",
                noStats=False,
                noStretch=False,
                noDelete=False,
                minPxls=minPxlsVal,
                distThres=distThresVal,
                bands=bandsVal,
                processInMem=False,
            )

        segTiles = glob.glob(os.path.join(tilesSegsDIR, tilesBase + "*_segs.kea"))
        for segTile in segTiles:
            baseName = os.path.splitext(os.path.basename(segTile))[0]
            borderMaskFile = os.path.join(
                tilesSegBordersDIR, baseName + "_segsborder.kea"
            )
            rastergis.defineBorderClumps(segTile, "BoundaryClumps")
            rastergis.export_col_to_gdal_img(
                segTile, borderMaskFile, "KEA", rsgislib.TYPE_8UINT, "BoundaryClumps"
            )

    def mergeStage2TilesToOutput(
        self, clumpsImage, tilesSegsDIR, tilesSegBordersDIR, tilesBase, s2BordersImage
    ):
        segTiles = glob.glob(os.path.join(tilesSegsDIR, tilesBase + "*_segs.kea"))
        segmentation.merge_clump_images(segTiles, clumpsImage)
        rastergis.pop_rat_img_stats(clumpsImage, True, True)

        tileBorders = glob.glob(
            os.path.join(tilesSegBordersDIR, tilesBase + "*_segsborder.kea")
        )
        imageutils.create_copy_img(
            clumpsImage, s2BordersImage, 1, 0, "KEA", rsgislib.TYPE_8UINT
        )
        imageutils.includeImages(s2BordersImage, tileBorders)

    def createStage3ImageSubsets(
        self,
        inputImage,
        s2BordersImage,
        s3BordersClumps,
        subsetImgsDIR,
        subsetImgsMaskedDIR,
        subImgBaseName,
        minSize,
    ):
        segmentation.clump(s2BordersImage, s3BordersClumps, "KEA", True, 0)
        rastergis.pop_rat_img_stats(s3BordersClumps, True, True)

        rastergis.spatialExtent(
            s3BordersClumps,
            "minXX",
            "minXY",
            "maxXX",
            "maxXY",
            "minYX",
            "minYY",
            "maxYX",
            "maxYY",
        )

        dataType = rsgislib.imageutils.get_rsgislib_datatype_from_img(inputImage)

        ratDS = gdal.Open(s3BordersClumps, gdal.GA_Update)
        minX = rat.readColumn(ratDS, "minXX")
        maxX = rat.readColumn(ratDS, "maxXX")
        minY = rat.readColumn(ratDS, "minYY")
        maxY = rat.readColumn(ratDS, "maxYY")
        Histogram = rat.readColumn(ratDS, "Histogram")
        for i in range(minX.shape[0]):
            if i > 0:
                subImage = os.path.join(subsetImgsDIR, subImgBaseName + str(i) + ".kea")
                # print( "[" + str(minX[i]) + ", " + str(maxX[i]) + "][" + str(minY[i]) + ", " + str(maxY[i]) + "]" )
                imageutils.subsetbbox(
                    inputImage,
                    subImage,
                    "KEA",
                    dataType,
                    minX[i],
                    maxX[i],
                    minY[i],
                    maxY[i],
                )
                if Histogram[i] > minSize:
                    maskedFile = os.path.join(
                        subsetImgsMaskedDIR, subImgBaseName + str(i) + "_masked.kea"
                    )
                else:
                    maskedFile = os.path.join(
                        subsetImgsMaskedDIR, subImgBaseName + str(i) + "_burn.kea"
                    )
                imageutils.mask_img(
                    subImage, s2BordersImage, maskedFile, "KEA", dataType, 0, 0
                )
                rastergis.pop_rat_img_stats(maskedFile, True, False)
        ratDS = None

    def performStage3SubsetsSegmentation(
        self,
        subsetImgsMaskedDIR,
        subsetSegsDIR,
        tmpDIR,
        subImgBaseName,
        segStatsInfo,
        minPxlsVal,
        distThresVal,
        bandsVal,
    ):
        imgTiles = glob.glob(
            os.path.join(subsetImgsMaskedDIR, subImgBaseName + "*_masked.kea")
        )
        for imgTile in imgTiles:
            baseName = os.path.splitext(os.path.basename(imgTile))[0]
            clumpsFile = os.path.join(subsetSegsDIR, baseName + "_segs.kea")
            kMeansCentres, imgStretchStats = self.findSegStatsFiles(
                imgTile, segStatsInfo
            )
            shepherdseg.runShepherdSegmentationPreCalcdStats(
                imgTile,
                clumpsFile,
                kMeansCentres,
                imgStretchStats,
                outputMeanImg=None,
                tmpath=os.path.join(tmpDIR, baseName + "_segstemp"),
                gdalformat="KEA",
                noStats=False,
                noStretch=False,
                noDelete=False,
                minPxls=minPxlsVal,
                distThres=distThresVal,
                bands=bandsVal,
                processInMem=False,
            )

    def mergeStage3TilesToOutput(
        self, clumpsImage, subsetSegsDIR, subsetImgsMaskedDIR, subImgBaseName
    ):
        burnTiles = glob.glob(
            os.path.join(subsetImgsMaskedDIR, subImgBaseName + "*_burn.kea")
        )
        if len(burnTiles) > 0:
            segmentation.merge_clump_images(burnTiles, clumpsImage)

        segTiles = glob.glob(os.path.join(subsetSegsDIR, subImgBaseName + "*_segs.kea"))
        segmentation.merge_clump_images(segTiles, clumpsImage)
        rastergis.pop_rat_img_stats(clumpsImage, True, True)


def perform_tiled_segmentation(
    input_img,
    clumps_img,
    tmp_dir="segtmp",
    tile_width=2000,
    tile_height=2000,
    valid_data_threshold=0.3,
    num_clusters=60,
    min_pxls=100,
    dist_thres=100,
    bands=None,
    sampling=100,
    km_max_iter=200,
):
    """
    Utility function to call the segmentation algorithm of Shepherd et al. (2019) using the tiled process outlined in Clewley et al (2015).

    :param input_img: is a string containing the name of the input file.
    :param clumps_img: is a string containing the name of the output clump file.
    :param tmpath: is a file path for intermediate files (default is to create a directory 'segtmp'). If path does current not exist then it will be created and deleted afterwards.
    :param tile_width: is an int specifying the width of the tiles used for processing (Default 2000)
    :param tile_height: is an int specifying the height of the tiles used for processing (Default 2000)
    :param valid_data_threshold: is a float (value between 0 - 1) used to specify the amount of valid image pixels (i.e., not a no data value of zero) are within a tile. Tiles failing to meet this threshold are merged with ones which do (Default 0.3).
    :param num_clusters: is an int which specifies the number of clusters within the KMeans clustering (default = 60).
    :param min_pxls: is an int which specifies the minimum number pixels within a segments (default = 100).
    :param dist_thres: specifies the distance threshold for joining the segments (default = 100, set to large number to turn off this option).
    :param bands: is an array providing a subset of image bands to use (default is None to use all bands).
    :param sampling: specify the subsampling of the image for the data used within the KMeans (default = 100; 1 == no subsampling).
    :param km_max_iter: maximum iterations for KMeans (Default 200).

    .. code:: python

        from rsgislib.segmentation import tiledsegsingle

        inputImage = 'LS5TM_20110428_sref_submask_osgb.kea'
        clumpsImage = 'LS5TM_20110428_sref_submask_osgb_clumps.kea'

        tiledsegsingle.perform_tiled_segmentation(inputImage, clumpsImage, tmpDIR='rsgislibsegtmp', tileWidth=2000, tileHeight=2000, validDataThreshold=0.3, numClusters=60, minPxls=100, distThres=100, bands=[4,5,3], sampling=100, kmMaxIter=200)

    """
    import rsgislib.tools.utils
    import rsgislib.tools.filetools

    createdTmp = False
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)
        createdTmp = True
    uidStr = rsgislib.tools.utils.uid_generator()

    baseName = os.path.splitext(os.path.basename(input_img))[0] + "_" + uidStr

    tileSegInfo = os.path.join(tmp_dir, baseName + "_seginfo.json")
    segStatsDIR = os.path.join(tmp_dir, "segStats_" + uidStr)
    strchStatsBase = os.path.join(segStatsDIR, baseName + "_stch")
    kCentresBase = os.path.join(segStatsDIR, baseName + "_kcentres")
    if not os.path.exists(segStatsDIR):
        os.makedirs(segStatsDIR)

    tiledSegObj = RSGISTiledShepherdSegmentationSingleThread()

    ######################## STAGE 1 #######################
    # Stage 1 Parameters (Internal)
    stage1TileShp = os.path.join(tmp_dir, baseName + "_S1Tiles.shp")
    stage1TileRAT = os.path.join(tmp_dir, baseName + "_S1Tiles.kea")
    stage1TilesBase = baseName + "_S1Tile"
    stage1TilesImgDIR = os.path.join(tmp_dir, "s1tilesimgs_" + uidStr)
    stage1TilesMetaDIR = os.path.join(tmp_dir, "s1tilesmeta_" + uidStr)
    stage1TilesSegsDIR = os.path.join(tmp_dir, "s1tilessegs_" + uidStr)
    stage1TilesSegBordersDIR = os.path.join(tmp_dir, "s1tilessegborders_" + uidStr)
    stage1BordersImage = os.path.join(tmp_dir, baseName + "_S1Borders.kea")

    if not os.path.exists(stage1TilesImgDIR):
        os.makedirs(stage1TilesImgDIR)
    if not os.path.exists(stage1TilesSegsDIR):
        os.makedirs(stage1TilesSegsDIR)
    if not os.path.exists(stage1TilesSegBordersDIR):
        os.makedirs(stage1TilesSegBordersDIR)
    if not os.path.exists(stage1TilesMetaDIR):
        os.makedirs(stage1TilesMetaDIR)

    # Initial Tiling
    tiledSegObj.performStage1Tiling(
        input_img,
        stage1TileShp,
        stage1TileRAT,
        stage1TilesBase,
        stage1TilesMetaDIR,
        stage1TilesImgDIR,
        os.path.join(tmp_dir, "s1tilingtemp"),
        tile_width,
        tile_height,
        valid_data_threshold,
    )

    # Perform Segmentation
    tiledSegObj.performStage1TilesSegmentation(
        stage1TilesImgDIR,
        stage1TilesSegsDIR,
        tmp_dir,
        stage1TilesBase,
        tileSegInfo,
        strchStatsBase,
        kCentresBase,
        num_clusters,
        min_pxls,
        dist_thres,
        bands,
        sampling,
        km_max_iter,
    )

    # Define Boundaries
    tiledSegObj.defineStage1Boundaries(
        stage1TilesSegsDIR, stage1TilesSegBordersDIR, stage1TilesBase
    )

    # Merge the Initial Tiles
    tiledSegObj.mergeStage1TilesToOutput(
        input_img,
        stage1TilesSegsDIR,
        stage1TilesSegBordersDIR,
        stage1TilesBase,
        clumps_img,
        stage1BordersImage,
    )

    shutil.rmtree(stage1TilesImgDIR)
    shutil.rmtree(stage1TilesSegsDIR)
    shutil.rmtree(stage1TilesSegBordersDIR)
    shutil.rmtree(stage1TilesMetaDIR)
    ########################################################

    with open(tileSegInfo, "r") as f:
        jsonStrData = f.read()
    segStatsInfo = json.loads(jsonStrData)

    ######################## STAGE 2 #######################
    # Stage 2 Parameters (Internal)
    stage2TileShp = os.path.join(tmp_dir, baseName + "_S2Tiles.shp")
    stage2TileRAT = os.path.join(tmp_dir, baseName + "_S2Tiles.kea")
    stage2TilesBase = baseName + "_S2Tile"
    stage2TilesImgDIR = os.path.join(tmp_dir, "s2tilesimg_" + uidStr)
    stage2TilesMetaDIR = os.path.join(tmp_dir, "s2tilesmeta_" + uidStr)
    stage2TilesImgMaskedDIR = os.path.join(tmp_dir, "s2tilesimgmask_" + uidStr)
    stage2TilesSegsDIR = os.path.join(tmp_dir, "s2tilessegs_" + uidStr)
    stage2TilesSegBordersDIR = os.path.join(tmp_dir, "s2tilessegborders_" + uidStr)
    stage2BordersImage = os.path.join(tmp_dir, baseName + "_S2Borders.kea")

    if not os.path.exists(stage2TilesImgDIR):
        os.makedirs(stage2TilesImgDIR)
    if not os.path.exists(stage2TilesMetaDIR):
        os.makedirs(stage2TilesMetaDIR)
    if not os.path.exists(stage2TilesImgMaskedDIR):
        os.makedirs(stage2TilesImgMaskedDIR)
    if not os.path.exists(stage2TilesSegsDIR):
        os.makedirs(stage2TilesSegsDIR)
    if not os.path.exists(stage2TilesSegBordersDIR):
        os.makedirs(stage2TilesSegBordersDIR)

    # Perform offset tiling
    tiledSegObj.performStage2Tiling(
        input_img,
        stage2TileShp,
        stage2TileRAT,
        stage2TilesBase,
        stage2TilesMetaDIR,
        stage2TilesImgDIR,
        os.path.join(tmp_dir, "s2tilingtemp"),
        tile_width,
        tile_height,
        valid_data_threshold,
        stage1BordersImage,
    )

    # Perform Segmentation of the Offset Tiles
    tiledSegObj.performStage2TilesSegmentation(
        stage2TilesImgDIR,
        stage2TilesImgMaskedDIR,
        stage2TilesSegsDIR,
        stage2TilesSegBordersDIR,
        tmp_dir,
        stage2TilesBase,
        stage1BordersImage,
        segStatsInfo,
        min_pxls,
        dist_thres,
        bands,
    )

    # Merge in the next set of boundaries
    tiledSegObj.mergeStage2TilesToOutput(
        clumps_img,
        stage2TilesSegsDIR,
        stage2TilesSegBordersDIR,
        stage2TilesBase,
        stage2BordersImage,
    )

    shutil.rmtree(stage2TilesImgDIR)
    shutil.rmtree(stage2TilesMetaDIR)
    shutil.rmtree(stage2TilesImgMaskedDIR)
    shutil.rmtree(stage2TilesSegsDIR)
    shutil.rmtree(stage2TilesSegBordersDIR)
    ########################################################

    ######################## STAGE 3 #######################
    # Stage 3 Parameters (Internal)
    stage3BordersClumps = os.path.join(tmp_dir, baseName + "_S3BordersClumps.kea")
    stage3SubsetsDIR = os.path.join(tmp_dir, "s3subsetimgs_" + uidStr)
    stage3SubsetsMaskedDIR = os.path.join(tmp_dir, "s3subsetimgsmask_" + uidStr)
    stage3SubsetsSegsDIR = os.path.join(tmp_dir, "s3subsetsegs_" + uidStr)
    stage3Base = baseName + "_S3Subset"

    if not os.path.exists(stage3SubsetsDIR):
        os.makedirs(stage3SubsetsDIR)
    if not os.path.exists(stage3SubsetsMaskedDIR):
        os.makedirs(stage3SubsetsMaskedDIR)
    if not os.path.exists(stage3SubsetsSegsDIR):
        os.makedirs(stage3SubsetsSegsDIR)

    # Create the final boundary image subsets
    tiledSegObj.createStage3ImageSubsets(
        input_img,
        stage2BordersImage,
        stage3BordersClumps,
        stage3SubsetsDIR,
        stage3SubsetsMaskedDIR,
        stage3Base,
        min_pxls,
    )

    # Perform Segmentation of the stage 3 regions
    tiledSegObj.performStage3SubsetsSegmentation(
        stage3SubsetsMaskedDIR,
        stage3SubsetsSegsDIR,
        tmp_dir,
        stage3Base,
        segStatsInfo,
        min_pxls,
        dist_thres,
        bands,
    )

    # Merge the stage 3 regions into the final clumps image
    tiledSegObj.mergeStage3TilesToOutput(
        clumps_img, stage3SubsetsSegsDIR, stage3SubsetsMaskedDIR, stage3Base
    )

    shutil.rmtree(stage3SubsetsDIR)
    shutil.rmtree(stage3SubsetsMaskedDIR)
    shutil.rmtree(stage3SubsetsSegsDIR)
    ########################################################

    shutil.rmtree(segStatsDIR)
    rsgislib.tools.filetools.delete_file_with_basename(stage1BordersImage)
    rsgislib.tools.filetools.delete_file_with_basename(stage2BordersImage)
    rsgislib.tools.filetools.delete_file_with_basename(stage3BordersClumps)
    rsgislib.tools.filetools.delete_file_with_basename(stage1TileShp)
    rsgislib.tools.filetools.delete_file_with_basename(stage1TileRAT)
    rsgislib.tools.filetools.delete_file_with_basename(stage2TileShp)
    rsgislib.tools.filetools.delete_file_with_basename(stage2TileRAT)
    rsgislib.tools.filetools.delete_file_silent(tileSegInfo)
    if createdTmp:
        shutil.rmtree(tmp_dir)
