#!/usr/bin/env python
"""
The tools.mapping module contains functions for making maps with geospatial data.
"""

import math
import os
import shutil
from typing import Dict, List, Union, Tuple

import geopandas
import matplotlib.cm
import matplotlib.colors
import matplotlib.pyplot as plt
import numpy
from matplotlib_scalebar.scalebar import ScaleBar

import rsgislib
import rsgislib.imageutils
import rsgislib.tools.plotting
import rsgislib.tools.projection


def calc_y_fig_size(bbox: List[float], fig_x_size=Union[int, float]) -> float:
    """
    A function which calculates the y axis size give the bbox and x axis size
    and the BBOX for the area to be mapped. This is useful so the map fills
    the whole area rather than having lots of white space in the resulting
    figure image file.

    :param bbox: the (MinX, MaxX, MinY, MaxY) for the region of interest.
    :param fig_x_size: the size for the figure in the x axis.
    :return: the figure size in the y axis.

    """
    x_bbox_size = bbox[1] - bbox[0]
    y_bbox_size = bbox[3] - bbox[2]
    bbox_xy_ratio = y_bbox_size / x_bbox_size
    fig_y_size = fig_x_size * bbox_xy_ratio
    return fig_y_size


def define_axis_extent(ax: plt.axis, bbox: List[float]):
    """
    A function which defines the limits of the axis using the same bbox
    as the other mapping functions.

    Note. this function was written and is probably mainly used for defining
    the axis limits when experimenting with the size/shape of the axis when
    laying out multiple axes. However, it could be used to change the axis
    limits from what the other functions have defined.

    :param ax: The matplotlib axis for the limits to be set.
    :param bbox: a bbox (MinX, MaxX, MinY, MaxY) to define the region of interest.

    """
    ax.set_aspect("equal", adjustable="datalim")
    ax.set_xlim([bbox[0], bbox[1]])
    ax.set_ylim([bbox[2], bbox[3]])
    ax.ticklabel_format(useOffset=False, style="plain")


def define_map_tick_spacing(ax: plt.axis, tick_spacing: float):
    """
    A function which defines the tick spacing on both axis of the map.

    If projection is WGS84 (EPSG:4326) then a tick spacing of 0.1 would
    provide ticks every 0.1 degrees while if using UTM then a tick spacing
    of 1000 will give a tick every 1km.

    :param ax: The matplotlib axis for the tick spacing to be defined.
    :param tick_spacing: the spacing between the ticks.

    """
    import matplotlib.ticker as ticker

    ax.xaxis.set_major_locator(ticker.MultipleLocator(tick_spacing))
    ax.yaxis.set_major_locator(ticker.MultipleLocator(tick_spacing))
    ax.ticklabel_format(useOffset=False, style="plain")


def get_overview_info(
    roi_bbox: List[float],
    roi_epsg: int = 4236,
    overview_buf: int = 30,
    out_epsg: int = 4236,
) -> (List[float], List[float]):
    """
    A function which uses the BBOX for the extent of the map being drawn to create
    the a BBOX for and centre point which can be used within the add_overview_maps
    function to add an overview map to an axis.

    :param roi_bbox: the region of interest (ROI) bbox (MinX, MaxX, MinY, MaxY)
                     representing the area for the which the map is being drawn
                     for.
    :param roi_epsg: the project (as an EPSG code) for the coordinates provided in
                     the roi_bbox.
    :param overview_buf: the buffer used to specify the overview area. This is taken
                         from the centre point of the roi_bbox.
    :return: the overview bbox (MinX, MaxX, MinY, MaxY) and point (X, Y)

    """
    import rsgislib.tools.geometrytools

    if roi_epsg != out_epsg:
        roi_proj_bbox = rsgislib.tools.geometrytools.reproj_bbox_epsg(
            roi_bbox, roi_epsg, out_epsg
        )
    else:
        roi_proj_bbox = roi_bbox

    c_pt_x = roi_proj_bbox[0] + ((roi_proj_bbox[1] - roi_proj_bbox[0]) / 2)
    c_pt_y = roi_proj_bbox[2] + ((roi_proj_bbox[3] - roi_proj_bbox[2]) / 2)
    over_min_x = c_pt_x - overview_buf
    over_max_x = c_pt_x + overview_buf
    over_min_y = c_pt_y - overview_buf
    over_max_y = c_pt_y + overview_buf

    return [over_min_x, over_max_x, over_min_y, over_max_y], [c_pt_x, c_pt_y]


def add_overview_maps(
    ax: plt.axis,
    overview_lyr: geopandas.GeoDataFrame,
    overview_bbox: List[float],
    overview_pt: List[float] = None,
    over_size_x: float = 0.1,
    over_size_y: float = 0.1,
    over_x_off: float = 0.0,
    over_y_off: float = 0.0,
    pt_clr="red",
    pt_size=10,
    fill_clr="white",
    line_clr="black",
    line_width=0.25,
) -> plt.axis:
    """
    Add an overview map in the top-left corner of the map.

    :param ax: The matplotlib axis to which to add the overview map.
    :param overview_lyr: The geopandas layer to used used for the overview map
                         usually this would be a global vector layer of the countries
                         but could be anything.
    :param overview_bbox: the bbox (MinX, MaxX, MinY, MaxY) for the area to be shown
                          within the overview map.
    :param overview_pt: an optional point (X, Y) to displayed on the overview map.
    :param over_size_x: the size of the overview map in the x-axis
    :param over_size_y: the size of the overview map in the y-axis
    :param over_x_off: the x-axis offset for the overmap position
    :param over_y_off: the y-axis offset for the overmap position
    :param pt_clr: the colour of the point (if specified). Default: Red.
    :param pt_size: the size of the point (if specified). Default: 10.
    :param fill_clr: the colour used to fill the polygons within the overview layer.
                     Default: white
    :param line_clr: the colour of the lines of the overview layer. Default: black
    :param line_width: the line width of the lines of the overview layer. Default: 0.25
    :return: return the matplotlib axis for the overview map.

    """
    ax_over = ax.inset_axes(
        [over_x_off, ((1.0 - over_size_y) + over_y_off), over_size_x, over_size_y]
    )
    ax_over.set_xticks([])
    ax_over.set_yticks([])
    overview_lyr.plot(
        ax=ax_over, color=fill_clr, edgecolor=line_clr, linewidth=line_width, alpha=1
    )
    if overview_pt is not None:
        ax_over.scatter(overview_pt[0], overview_pt[1], color=pt_clr, s=pt_size)
    ax_over.set_xlim([overview_bbox[0], overview_bbox[1]])
    ax_over.set_ylim([overview_bbox[2], overview_bbox[3]])
    return ax_over


def add_contextily_basemap(
    ax: plt.axis,
    epsg_crs: int,
    cx_src,
    cx_zoom_lvl: Union[int, str] = "auto",
    cx_attribution: Union[str, bool] = None,
    cx_att_size: int = 8,
):
    """
    A function which adds a contextily (https://contextily.readthedocs.io)
    basemap (e.g., open street map) to an matplotlib axis. This function is
    generally used to add a base map underneath other layers (e.g., after using
    one of the other mapping functions such as create_vec_lyr_map).

    Note. this function must be called after you have added the other layers
    to the axis as those will define the spatial extent of the axis.

    :param ax: The matplotlib axis to which to add the base map.
    :param epsg_crs: An epsg code for the projection being used for the map. The
                     contextily basemap will be warped to this projection.
    :param cx_src: the contextily basemap (e.g., contextily.providers.OpenTopoMap)
    :param cx_zoom_lvl: the zoom level of the basemap to be used. Default: auto
    :param cx_attribution: The attribution of the map, if None then the default
                           attribution will be used. If a string is provided then
                           this will be used. If False is used then no attribution
                           will be outputted. Default: None
    :param cx_att_size: the font size of the attribution. Default: 8

    """
    import contextily

    if cx_zoom_lvl is None:
        cx_zoom_lvl = "auto"

    contextily.add_basemap(
        ax,
        zoom=cx_zoom_lvl,
        crs=f"epsg:{epsg_crs}",
        source=cx_src,
        attribution=cx_attribution,
        attribution_size=cx_att_size,
    )


def create_wmts_img_map(
    ax: plt.axis,
    wmts_url: str,
    wmts_lyr: str,
    bbox: List[float],
    bbox_epsg: int,
    wmts_zoom_level: int = None,
    title_str: str = None,
    show_scale_bar: bool = True,
    use_grid: bool = False,
    show_map_axis: bool = True,
    tmp_dir: str = None,
    wmts_epsg: int = None,
    scale_bar_loc: str = "upper right",
):
    """
    A function which downloading image from a WMTS service and adding it

    :param ax: The matplotlib axis to which to add the WMTS image to.
    :param wmts_url: The url for the WMTS service
    :param wmts_lyr: the layer within the WMTS to use.
    :param bbox: The bbox (MinX, MaxX, MinY, MaxY) specifying the
                 spatial region to be displayed.
    :param bbox_epsg: the EPSG code of the inputted bbox, with will be the epsg
                      for the outputted map.
    :param wmts_zoom_level: Optionally, the zoom level from the WMTS. If None
                            then automatically defined.
    :param title_str: an optional title for the map (Default: None)
    :param show_scale_bar: boolean specifying whether a scale bar should be added to
                           the axis. Default: False
    :param use_grid: boolean specifying whether a grid should be added to the axis.
                     Default: False
    :param show_map_axis: boolean specifying whether the axes should be shown
                          Default: False
    :param tmp_dir: Optionally, a temporary directory for some intermediate files.
                    If not specified, a tmp dir is created and removed in the local
                    path from where the script is run from.
    :param wmts_epsg: Provide the epsg code for the WMTS layer (probably 3857) if
                      the code can't automatically find it.
    :param scale_bar_loc: the location on the plot of the scale bar. Options defined
                          by the matplotlib-scalebar module. But must be one of:
                          upper right, upper left, lower left, lower right, right,
                          center left, center right, lower center, upper center
                          or center. Default: upper right

    """
    import rsgislib.tools.utils
    from rsgislib.tools import wmts_tools

    uid_str = rsgislib.tools.utils.uid_generator()
    create_tmp_dir = False
    if tmp_dir is None:
        tmp_dir = f"tmp_{uid_str}"
        if not os.path.exists(tmp_dir):
            os.mkdir(tmp_dir)
            create_tmp_dir = True

    wmts_tmp_img = os.path.join(tmp_dir, f"wmts_tmp_img_{uid_str}.kea")
    wmts_tools.get_wmts_as_img(
        wmts_url,
        wmts_lyr,
        bbox,
        bbox_epsg=bbox_epsg,
        output_img=wmts_tmp_img,
        gdalformat="KEA",
        zoom_level=wmts_zoom_level,
        tmp_dir=tmp_dir,
        wmts_epsg=wmts_epsg,
    )

    img_data, img_coords = rsgislib.tools.plotting.get_gdal_raster_mpl_imshow(
        wmts_tmp_img, bands=[1, 2, 3]
    )

    ax.imshow(img_data, extent=img_coords)
    ax.set_xlim([bbox[0], bbox[1]])
    ax.set_ylim([bbox[2], bbox[3]])
    ax.set_aspect("equal", adjustable="datalim")

    if use_grid:
        ax.grid()

    if not show_map_axis:
        ax.set_axis_off()
        ax.set_axis_off()

    if show_scale_bar:
        distance_meters = 1
        if bbox_epsg == 4326:
            distance_meters = rsgislib.tools.projection.great_circle_distance(
                wgs84_p1=[bbox[0], bbox[3]], wgs84_p2=[bbox[0] + 1, bbox[3]]
            )

        ax.add_artist(ScaleBar(distance_meters, location=scale_bar_loc))

    if title_str is not None:
        ax.title.set_text(title_str)

    # Delete the downloaded image file.
    rsgislib.imageutils.delete_gdal_layer(wmts_tmp_img)

    # If created remove the tmp directory
    if create_tmp_dir:
        shutil.rmtree(tmp_dir)


def draw_bboxes_to_axis(
    ax: plt.axis,
    bboxes: List[List[float]],
    bbox_labels: List[str] = None,
    rect_clr: str = "black",
    line_width: float = 1,
    fill_rect: bool = False,
    clr_alpha: float = 1.0,
    lbl_font_size=12,
    lbl_font_weight="normal",
    lbl_font_clr="black",
    lbl_pos: str = "centre",
    lbl_pos_buf: float = 0.0,
    lbl_fill_clr: str = None,
    lbl_padding: float = 3.0,
):
    """
    This function can be used to draw a set of rectangles to an axis, where typically
    the bboxes specify subset regions or areas of interest you are trying to highlight
    to the person viewing the map.

    :param ax: The matplotlib axis to which the bboxes will be drawn
    :param bboxes: a list of bboxes (MinX, MaxX, MinY, MaxY) to be drawn on the axis.
    :param bbox_labels: An optional list of labels for the bboxes
    :param rect_clr: the colour for the bbox regions.
    :param line_width: the width of the lines for the bboxes
    :param fill_rect: boolean specifying whether to fill the bbox
                      regions (Default: False)
    :param clr_alpha: the alpha value for the bbox regions (Default: 1.0)
    :param lbl_font_size: the font size (Default: 12).
    :param lbl_font_weight: the weight of the font (i.e., normal or bold)
    :param lbl_font_clr: the colour of the text (Default: black)
    :param lbl_pos: Options: [None, above, below, left, right]. Default: None (centre)

    """
    from matplotlib.patches import Rectangle

    if bbox_labels is not None:
        if len(bboxes) != len(bbox_labels):
            raise rsgislib.RSGISPyException(
                "If labels are provided then the list length must be the same as bboxes."
            )

    for i, bbox in enumerate(bboxes):
        width = bbox[1] - bbox[0]
        height = bbox[3] - bbox[2]
        bl_x = bbox[0]
        bl_y = bbox[2]
        rect = Rectangle(
            (bl_x, bl_y),
            width,
            height,
            fill=fill_rect,
            color=rect_clr,
            linewidth=line_width,
            alpha=clr_alpha,
        )
        ax.add_patch(rect)
        if bbox_labels is not None:
            cx = bl_x + width / 2
            cy = bl_y + height / 2

            ha_val = "center"
            va_val = "center"

            if lbl_pos is not None:
                if lbl_pos.lower() == "above":
                    cy = bl_y + height + lbl_pos_buf
                    va_val = "bottom"
                elif lbl_pos.lower() == "below":
                    cy = bl_y - lbl_pos_buf
                    va_val = "top"
                elif lbl_pos.lower() == "left":
                    cx = bl_x - lbl_pos_buf
                    ha_val = "right"
                elif lbl_pos.lower() == "right":
                    cx = bl_x + width + lbl_pos_buf
                    ha_val = "left"

            if lbl_fill_clr is not None:
                ax.annotate(
                    bbox_labels[i],
                    (cx, cy),
                    color=lbl_font_clr,
                    weight=lbl_font_weight,
                    fontsize=lbl_font_size,
                    ha=ha_val,
                    va=va_val,
                    bbox=dict(
                        facecolor=lbl_fill_clr, edgecolor="none", pad=lbl_padding
                    ),
                )
            else:
                ax.annotate(
                    bbox_labels[i],
                    (cx, cy),
                    color=lbl_font_clr,
                    weight=lbl_font_weight,
                    fontsize=lbl_font_size,
                    ha=ha_val,
                    va=va_val,
                )


def add_axis_label(
    ax: plt.axis,
    lbl_text: str,
    lbl_font_clr: str = "black",
    lbl_font_weight: str = "normal",
    lbl_font_size: int = 12,
    fill_clr: str = "white",
    padding: float = 3.0,
):
    """
    This function adds a label in the top-left corner of the axis. This function
    would typically be used if you want to label a number of axes (e.g., a, b, c, etc.)

    :param ax: The matplotlib axis to which the label will be added.
    :param lbl_text: the label text to be written.
    :param lbl_font_clr: the colour of the text (Default: black)
    :param lbl_font_weight: the weight of the font (i.e., normal or bold)
    :param lbl_font_size: the font size (Default: 12).
    :param fill_clr: the colour the label area will be filled with (Default: white)
    :param padding: the amount of padding around the text (Default: 3.0)

    """
    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()

    ax.text(
        xmin,
        ymax,
        lbl_text,
        color=lbl_font_clr,
        weight=lbl_font_weight,
        fontsize=lbl_font_size,
        ha="left",
        va="top",
        bbox=dict(facecolor=fill_clr, edgecolor="none", pad=padding),
    )


def create_vec_lyr_map(
    ax: plt.axis,
    gp_vecs: Union[geopandas.GeoDataFrame, List[geopandas.GeoDataFrame]],
    bbox: List[float],
    title_str: str = None,
    vec_fill_clrs: Union[str, List[str]] = "grey",
    vec_line_clrs: Union[str, List[str]] = "black",
    vec_line_widths: Union[float, List[float]] = 0.25,
    vec_fill_alphas: Union[float, List[float]] = 1.0,
    vec_markersize: Union[str, float] = None,
    show_scale_bar: bool = True,
    use_grid: bool = False,
    show_map_axis: bool = True,
    sub_in_vec: bool = False,
    clip_vec_bbox: bool = True,
    scale_bar_loc: str = "upper right",
    plot_zorders: Union[float, List[float]] = 1,
):
    """
    A function which adds vector layer(s) to a matplotlib axis. This function
    takes either a single or list of geopandas dataframes to be displayed on
    the axis.

    Note. if only the vector outlines are required (i.e., no colour fill of
    the polygons) then use the boundary i.e., gp_df_lyr.boundary

    :param ax: The matplotlib axis to which to add the vector layer.
    :param gp_vecs: either a geopandas dataframe or list of geopandas dataframes.
                    Note. all the dataframes must be the same projection.
    :param bbox: a bbox (MinX, MaxX, MinY, MaxY) for the region to be displayed
    :param title_str: an optional title for the map (Default: None)
    :param vec_fill_clrs: either a single string or list of strings with the colours
                          for filling the vectors. (Default: grey)
    :param vec_line_clrs: either a single string or list of strings with the colours
                          for the vector lines. (Default: black)
    :param vec_line_widths: either a single float or list of floats for the line width
                            to be used for the vector layer(s). (Default: 0.25)
    :param vec_fill_alphas: either a single float or list of floats for the alpha
                            value(s) for the vector layers. (Default: 1)
    :parma vec_markersize: if the vector layer has point geometries then this variable
                           allows the size of the points to be defined as either a
                           constant (float) or using column from the vector layer
                           (string).
    :param show_scale_bar: boolean specifying whether a scale bar should be added to
                           the axis. Default: False
    :param use_grid: boolean specifying whether a grid should be added to the axis.
                     Default: False
    :param show_map_axis: boolean specifying whether the axes should be shown
                          Default: False
    :param sub_in_vec: boolean specifying whether the vector layer should be
                       spatially subset before displaying as for large vector
                       layers this can make the processing much faster.
                       Default: False
    :param clip_vec_bbox: boolean specifying whether a bbox should be clipped to a
                          polygon defined by the bbox. Default: True
    :param scale_bar_loc: the location on the plot of the scale bar. Options defined
                          by the matplotlib-scalebar module. But must be one of:
                          upper right, upper left, lower left, lower right, right,
                          center left, center right, lower center, upper center
                          or center. Default: upper right
    :param plot_zorders: the drawing order of artists is determined by their
                        zorder attribute, which is a floating point number.
                        Artists with higher zorder are drawn on top.
                        https://matplotlib.org/stable/gallery/misc/zorder_demo.html

    """
    n_vec_lyrs = 1
    if isinstance(gp_vecs, list):
        n_vec_lyrs = len(gp_vecs)
    else:
        # Create list of one
        gp_vecs = [gp_vecs]

    if clip_vec_bbox:
        import shapely.geometry

        bbox_poly = shapely.geometry.box(
            min(bbox[0], bbox[1]),  # min_x
            min(bbox[2], bbox[3]),  # min_y
            max(bbox[0], bbox[1]),  # max_x
            max(bbox[2], bbox[3]),  # max_y
        )

        clip_poly_gdf = geopandas.GeoDataFrame(
            [1], geometry=[bbox_poly], crs=gp_vecs[0].crs
        )

    for i, gp_vec in enumerate(gp_vecs):
        if sub_in_vec:
            min_x_sub = math.floor(bbox[0] - 4)
            max_x_sub = math.ceil(bbox[1] + 4)
            min_y_sub = math.floor(bbox[2] - 4)
            max_y_sub = math.ceil(bbox[3] + 4)
            gp_vec_sub = gp_vec.cx[min_x_sub:max_x_sub, min_y_sub:max_y_sub]
        else:
            gp_vec_sub = gp_vec

        if clip_vec_bbox:
            gp_vec_sub = gp_vec_sub.clip(clip_poly_gdf)

        if isinstance(vec_fill_clrs, list):
            if len(vec_fill_clrs) != n_vec_lyrs:
                raise rsgislib.RSGISPyException(
                    "Number of fill colours not same as number of vector layers"
                )
            vec_fill_clr = vec_fill_clrs[i]
        else:
            vec_fill_clr = vec_fill_clrs

        if isinstance(vec_line_clrs, list):
            if len(vec_line_clrs) != n_vec_lyrs:
                raise rsgislib.RSGISPyException(
                    "Number of line colours not same as number of vector layers"
                )
            vec_line_clr = vec_line_clrs[i]
        else:
            vec_line_clr = vec_line_clrs

        if isinstance(vec_line_widths, list):
            if len(vec_line_widths) != n_vec_lyrs:
                raise rsgislib.RSGISPyException(
                    "Number of line widths not same as number of vector layers"
                )
            vec_line_width = vec_line_widths[i]
        else:
            vec_line_width = vec_line_widths

        if isinstance(vec_fill_alphas, list):
            if len(vec_fill_alphas) != n_vec_lyrs:
                raise rsgislib.RSGISPyException(
                    "Number of fill alphas not same as number of vector layers"
                )
            vec_fill_alpha = vec_fill_alphas[i]
        else:
            vec_fill_alpha = vec_fill_alphas

        if isinstance(plot_zorders, list):
            if len(plot_zorders) != n_vec_lyrs:
                raise rsgislib.RSGISPyException(
                    "Number of fill colours not same as number of vector layers"
                )
            plot_zorder = plot_zorders[i]
        else:
            plot_zorder = plot_zorders

        gp_vec_sub.plot(
            ax=ax,
            color=vec_fill_clr,
            edgecolor=vec_line_clr,
            linewidth=vec_line_width,
            alpha=vec_fill_alpha,
            markersize=vec_markersize,
            zorder=plot_zorder,
        )
    ax.set_xlim([bbox[0], bbox[1]])
    ax.set_ylim([bbox[2], bbox[3]])
    ax.set_aspect("equal", adjustable="datalim")
    ax.ticklabel_format(useOffset=False, style="plain")

    if use_grid:
        ax.grid()

    if not show_map_axis:
        ax.set_axis_off()
        ax.set_axis_off()

    if show_scale_bar:
        distance_meters = 1
        vec_crs = str(gp_vecs[0].crs)
        vec_epsg = int(vec_crs.split(":")[1])
        if vec_epsg == 4326:
            distance_meters = rsgislib.tools.projection.great_circle_distance(
                wgs84_p1=[bbox[0], bbox[3]], wgs84_p2=[bbox[0] + 1, bbox[3]]
            )
        ax.add_artist(ScaleBar(distance_meters, location=scale_bar_loc))

    if title_str is not None:
        ax.title.set_text(title_str)


def create_raster_img_map(
    ax: plt.axis,
    input_img: str,
    img_bands: List[int],
    img_stch: int,
    bbox: List[float] = None,
    title_str: str = None,
    show_scale_bar: bool = True,
    use_grid: bool = False,
    show_map_axis: bool = True,
    img_no_data_val: float = None,
    no_data_out_clr: Tuple[float, float, float] = None,
    stch_min_max_vals: Union[Dict, List[Dict]] = None,
    stch_n_stdevs: float = 2.0,
    img_alpha: float = 1.0,
    scale_bar_loc: str = "upper right",
    plot_zorder: float = 1,
):
    """
    A function which displays a stretched raster layer onto the axis provided.

    :param ax: The matplotlib axis to which to add the image to.
    :param input_img: the file path for the input image
    :param img_bands: a list of bands (either 1 or 3) to be used for display.
                      Note, band numbering starts at 1.
    :param img_stch: the stretch used for the input image.
                     Options are: rsgislib.IMG_STRETCH_XXXX
    :param bbox: An optional bbox (MinX, MaxX, MinY, MaxY) specifying the
                 spatial region to be displayed. If None then the whole image
                 bbox will be used.
    :param title_str: an optional title for the map (Default: None)
    :param show_scale_bar: boolean specifying whether a scale bar should be added to
                           the axis. Default: False
    :param use_grid: boolean specifying whether a grid should be added to the axis.
                     Default: False
    :param show_map_axis: boolean specifying whether the axes should be shown
                          Default: False
    :param img_no_data_val: a float with the no data value for the input image.
                            if None then the no data value will be read from the
                            input image.
    :param stch_min_max_vals: If using the rsgislib.IMG_STRETCH_USER stretch then
                              these are the user specified min and max values for
                              the stretch.
                              See rsgislib.tools.plotting.manual_stretch_np_arr
    :param stch_n_stdevs: If using the rsgislib.IMG_STRETCH_STDEV stretch then
                          this is the number of standard deviations parameters.
                          See rsgislib.tools.plotting.stdev_stretch_np_arr
    :param img_alpha: If less than one then the input_img data will have an alpha
                      (transparency) applied. Default: 1
    :param scale_bar_loc: the location on the plot of the scale bar. Options defined
                          by the matplotlib-scalebar module. But must be one of:
                          upper right, upper left, lower left, lower right, right,
                          center left, center right, lower center, upper center
                          or center. Default: upper right
    :param plot_zorder: the drawing order of artists is determined by their
                        zorder attribute, which is a floating point number.
                        Artists with higher zorder are drawn on top.
                        https://matplotlib.org/stable/gallery/misc/zorder_demo.html

    """
    if bbox is None:
        bbox = rsgislib.imageutils.get_img_bbox(input_img)

    if img_no_data_val is None:
        img_no_data_val = rsgislib.imageutils.get_img_no_data_value(input_img)

    img_data, img_coords = rsgislib.tools.plotting.get_gdal_raster_mpl_imshow(
        input_img, bands=img_bands, bbox=bbox
    )

    if img_stch == rsgislib.IMG_STRETCH_USER:
        if stch_min_max_vals is None:
            raise rsgislib.RSGISPyException(
                "Manual stretch requires user parameters to be passed"
            )
        img_data_strch = rsgislib.tools.plotting.manual_stretch_np_arr(
            img_data,
            min_max_vals=stch_min_max_vals,
            no_data_val=img_no_data_val,
            no_data_clr=no_data_out_clr,
        )
    elif img_stch == rsgislib.IMG_STRETCH_LINEAR:
        img_data_strch = rsgislib.tools.plotting.linear_stretch_np_arr(
            img_data,
            no_data_val=img_no_data_val,
            no_data_clr=no_data_out_clr,
        )
    elif img_stch == rsgislib.IMG_STRETCH_STDEV:
        img_data_strch = rsgislib.tools.plotting.stdev_stretch_np_arr(
            img_data,
            n_stdevs=stch_n_stdevs,
            no_data_val=img_no_data_val,
            no_data_clr=no_data_out_clr,
        )
    elif img_stch == rsgislib.IMG_STRETCH_CUMULATIVE:
        img_data_strch = rsgislib.tools.plotting.cumulative_stretch_np_arr(
            img_data,
            no_data_val=img_no_data_val,
            no_data_clr=no_data_out_clr,
        )
    else:
        print("No stretch is being used - is this what you intended?!")
        img_data_strch = img_data

    clr_map = None
    if len(img_bands) == 1:
        clr_map = "gist_gray"

    ax.imshow(
        img_data_strch,
        cmap=clr_map,
        extent=img_coords,
        alpha=img_alpha,
        zorder=plot_zorder,
    )
    ax.set_xlim([img_coords[0], img_coords[1]])
    ax.set_ylim([img_coords[2], img_coords[3]])
    ax.set_aspect("equal", adjustable="datalim")
    ax.ticklabel_format(useOffset=False, style="plain")

    if use_grid:
        ax.grid()

    if not show_map_axis:
        ax.set_axis_off()
        ax.set_axis_off()

    if show_scale_bar:
        distance_meters = 1
        img_epsg = rsgislib.imageutils.get_epsg_proj_from_img(input_img)
        if img_epsg == 4326:
            distance_meters = rsgislib.tools.projection.great_circle_distance(
                wgs84_p1=[bbox[0], bbox[3]], wgs84_p2=[bbox[0] + 1, bbox[3]]
            )

        ax.add_artist(ScaleBar(distance_meters, location=scale_bar_loc))

    if title_str is not None:
        ax.title.set_text(title_str)


def create_thematic_raster_map(
    ax: plt.axis,
    input_img: Union[str, List],
    bbox: List[float] = None,
    title_str: str = None,
    alpha_backgd: bool = True,
    img_alpha: float = 1.0,
    ctab_alpha: bool = True,
    show_scale_bar: bool = True,
    use_grid: bool = False,
    show_map_axis: bool = True,
    scale_bar_loc: str = "upper right",
    plot_zorders: Union[float, List[float]] = 1,
):
    """
    A function which displays a thematic raster layer onto the axis provided
    where the colours are read from the colour table of the input image.

    :param ax: The matplotlib axis to which to add the image to.
    :param input_img: the file path for the input image
    :param bbox: An optional bbox (MinX, MaxX, MinY, MaxY) specifying the
                 spatial region to be displayed. If None then the whole image
                 bbox will be used.
    :param title_str: an optional title for the map (Default: None)
    :param alpha_backgd: boolean specifying that the background (i.e., 0)
                         value will be transparent and not shown.
    :param img_alpha: a float specifying the alpha transparency value for all the image
                      layers provided. Default: 1.0 (i.e., not transparent)
    :param ctab_alpha: boolean specifying that the alpha values from the colour
                       table should be used to display the image (Default: True)
    :param show_scale_bar: boolean specifying whether a scale bar should be added to
                           the axis. Default: False
    :param use_grid: boolean specifying whether a grid should be added to the axis.
                     Default: False
    :param show_map_axis: boolean specifying whether the axes should be shown
                          Default: False
    :param scale_bar_loc: the location on the plot of the scale bar. Options defined
                          by the matplotlib-scalebar module. But must be one of:
                          upper right, upper left, lower left, lower right, right,
                          center left, center right, lower center, upper center
                          or center. Default: upper right
    :param plot_zorders: the drawing order of artists is determined by their
                        zorder attribute, which is a floating point number.
                        Artists with higher zorder are drawn on top.
                        https://matplotlib.org/stable/gallery/misc/zorder_demo.html

    """
    input_imgs = list()
    if isinstance(input_img, str):
        input_imgs.append(input_img)
    else:
        input_imgs = input_img

    if isinstance(plot_zorders, list):
        if len(plot_zorders) != len(input_imgs):
            raise rsgislib.RSGISPyException(
                "The number of zorders provided does not match the number of input images."
            )
    else:
        tmp_plot_zorder = plot_zorders
        plot_zorders = list()
        for input_img in input_imgs:
            plot_zorders.append(tmp_plot_zorder)

    if bbox is None:
        bbox = rsgislib.imageutils.get_img_bbox(input_imgs[0])

    img_data_arr_scns = list()
    img_coords_scns = list()
    lgd_patches_scns = list()
    lcl_plot_zorders = list()
    for i, input_img in enumerate(input_imgs):
        (
            img_data_arr,
            img_coords,
            lgd_patches,
        ) = rsgislib.tools.plotting.get_gdal_thematic_raster_mpl_imshow(
            input_img,
            band=1,
            bbox=bbox,
            alpha_lyr=alpha_backgd,
            ctab_alpha=ctab_alpha,
        )
        img_data_arr_scns.append(img_data_arr)
        img_coords_scns.append(img_coords)
        lgd_patches_scns.append(lgd_patches)
        lcl_plot_zorders.append(plot_zorders[i])

    ax.set_xlim([img_coords_scns[0][0], img_coords_scns[0][1]])
    ax.set_ylim([img_coords_scns[0][2], img_coords_scns[0][3]])
    ax.set_aspect("equal", adjustable="datalim")
    ax.ticklabel_format(useOffset=False, style="plain")

    for img_data_arr, img_coords, plot_zorder in zip(
        img_data_arr_scns, img_coords_scns, lcl_plot_zorders
    ):
        ax.imshow(img_data_arr, extent=img_coords, alpha=img_alpha, zorder=plot_zorder)

    if use_grid:
        ax.grid()

    if not show_map_axis:
        ax.set_axis_off()
        ax.set_axis_off()

    if show_scale_bar:
        distance_meters = 1
        img_epsg = rsgislib.imageutils.get_epsg_proj_from_img(input_img)
        if img_epsg == 4326:
            distance_meters = rsgislib.tools.projection.great_circle_distance(
                wgs84_p1=[bbox[0], bbox[3]], wgs84_p2=[bbox[0] + 1, bbox[3]]
            )
        ax.add_artist(ScaleBar(distance_meters, location=scale_bar_loc))

    if title_str is not None:
        ax.title.set_text(title_str)


def create_choropleth_vec_lyr_map(
    ax: plt.axis,
    gp_vec: geopandas.GeoDataFrame,
    vec_col: str,
    bbox: List[float],
    title_str: str = None,
    vec_fill_cmap: matplotlib.colors.Colormap = None,
    vec_var_norm: matplotlib.colors.Normalize = None,
    vec_line_clr: str = "black",
    vec_line_width: float = 0.25,
    vec_fill_alpha: float = 1.0,
    vec_markersize: Union[str, float] = None,
    show_scale_bar: bool = True,
    use_grid: bool = False,
    show_map_axis: bool = True,
    sub_in_vec: bool = False,
    clip_vec_bbox: bool = True,
    scale_bar_loc: str = "upper right",
    plot_zorder: float = 1,
):
    """
    A function which adds a vector layer to a matplotlib axis. This function
    takes a single geopandas dataframe to be displayed on the axis.

    Note. this function uses a variable from the attribute table to colour
    the features creating a choropleth map.

    :param ax: The matplotlib axis to which to add the vector layer.
    :param gp_vec: geopandas dataframe to be displayed
    :param vec_col: the column within the dataframe to be displayed.
    :param bbox: a bbox (MinX, MaxX, MinY, MaxY) for the region to be displayed
    :param title_str: an optional title for the map (Default: None)
    :param vec_fill_cmap: a matplotlib colour map used to visualise the choropleth map.
                          If None (Default) then the viridis colour map will be used.
    :param vec_var_norm: a matplotlib normalisation used to visualise the choropleth
                         map. If None (Default) then no normalisation will be applied.
    :param vec_line_clrs: either a single string or list of strings with the colours
                          for the vector lines. (Default: black)
    :param vec_line_widths: either a single float or list of floats for the line width
                            to be used for the vector layer(s). (Default: 0.25)
    :param vec_fill_alphas: either a single float or list of floats for the alpha
                            value(s) for the vector layers. (Default: 1)
    :param vec_markersize: if the vector layer has point geometries then this variable
                           allows the size of the points to be defined as either a
                           constant (float) or using column from the vector layer
                           (string).
    :param show_scale_bar: boolean specifying whether a scale bar should be added to
                           the axis. Default: False
    :param use_grid: boolean specifying whether a grid should be added to the axis.
                     Default: False
    :param show_map_axis: boolean specifying whether the axes should be shown
                          Default: False
    :param sub_in_vec: boolean specifying whether the vector layer should be
                       spatially subset before displaying as for large vector
                       layers this can make the processing much faster.
                       Default: False
    :param clip_vec_bbox: boolean specifying whether a bbox should be clipped to a
                          polygon defined by the bbox. Default: True
    :param scale_bar_loc: the location on the plot of the scale bar. Options defined
                          by the matplotlib-scalebar module. But must be one of:
                          upper right, upper left, lower left, lower right, right,
                          center left, center right, lower center, upper center
                          or center. Default: upper right
    :param plot_zorder: the drawing order of artists is determined by their
                        zorder attribute, which is a floating point number.
                        Artists with higher zorder are drawn on top.
                        https://matplotlib.org/stable/gallery/misc/zorder_demo.html

    """
    if vec_fill_cmap is None:
        vec_fill_cmap = matplotlib.cm.get_cmap("viridis")

    if sub_in_vec:
        min_x_sub = math.floor(bbox[0] - 4)
        max_x_sub = math.ceil(bbox[1] + 4)
        min_y_sub = math.floor(bbox[2] - 4)
        max_y_sub = math.ceil(bbox[3] + 4)
        gp_vec_sub = gp_vec.cx[min_x_sub:max_x_sub, min_y_sub:max_y_sub]
    else:
        gp_vec_sub = gp_vec

    if clip_vec_bbox:
        import shapely.geometry

        bbox_poly = shapely.geometry.box(
            min(bbox[0], bbox[1]),  # min_x
            min(bbox[2], bbox[3]),  # min_y
            max(bbox[0], bbox[1]),  # max_x
            max(bbox[2], bbox[3]),  # max_y
        )

        clip_poly_gdf = geopandas.GeoDataFrame(
            [1], geometry=[bbox_poly], crs=gp_vec_sub.crs
        )
        gp_vec_sub = gp_vec_sub.clip(clip_poly_gdf)

    gp_vec_sub.plot(
        column=vec_col,
        ax=ax,
        cmap=vec_fill_cmap,
        norm=vec_var_norm,
        edgecolor=vec_line_clr,
        linewidth=vec_line_width,
        alpha=vec_fill_alpha,
        markersize=vec_markersize,
        zorder=plot_zorder,
    )
    ax.set_xlim([bbox[0], bbox[1]])
    ax.set_ylim([bbox[2], bbox[3]])
    ax.set_aspect("equal", adjustable="datalim")
    ax.ticklabel_format(useOffset=False, style="plain")

    if use_grid:
        ax.grid()

    if not show_map_axis:
        ax.set_axis_off()
        ax.set_axis_off()

    if show_scale_bar:
        distance_meters = 1
        vec_crs = str(gp_vec.crs)
        vec_epsg = int(vec_crs.split(":")[1])
        if vec_epsg == 4326:
            distance_meters = rsgislib.tools.projection.great_circle_distance(
                wgs84_p1=[bbox[0], bbox[3]], wgs84_p2=[bbox[0] + 1, bbox[3]]
            )
        ax.add_artist(ScaleBar(distance_meters, location=scale_bar_loc))

    if title_str is not None:
        ax.title.set_text(title_str)


def create_raster_cmap_img_map(
    ax: plt.axis,
    input_img: str,
    img_band: int,
    bbox: List[float] = None,
    title_str: str = None,
    show_scale_bar: bool = True,
    use_grid: bool = False,
    show_map_axis: bool = True,
    cmap_name: str = "viridis",
    norm_img_vals: bool = False,
    use_log_norm: bool = False,
    norm_vmin: float = None,
    norm_vmax: float = None,
    vals_under_white: bool = False,
    print_norm_vals: bool = False,
    scale_bar_loc: str = "upper right",
    plot_zorder: float = 1,
):
    """
    A function which displays a single band raster layer onto the axis provided
    using a colour bar.

    Colour bar information is returned. Note to add the colour bar to your plot
    you'll want to use code such as:

    c_cmap, c_norm =  mapping.create_raster_cmap_img_map(...)
    fig.colorbar(matplotlib.cm.ScalarMappable(norm=c_norm, cmap=c_cmap),
                 label='Some Data', ax=ax1)

    :param ax: The matplotlib axis to which to add the image to.
    :param input_img: the file path for the input image
    :param img_band: the image band within the file to be displayed.
                     Note, band numbering starts at 1.
    :param bbox: An optional bbox (MinX, MaxX, MinY, MaxY) specifying the
                 spatial region to be displayed. If None then the whole image
                 bbox will be used.
    :param title_str: an optional title for the map (Default: None)
    :param show_scale_bar: boolean specifying whether a scale bar should be added to
                           the axis. Default: False
    :param use_grid: boolean specifying whether a grid should be added to the axis.
                     Default: False
    :param show_map_axis: boolean specifying whether the axes should be shown
                          Default: False
    :param cmap_name: The name of the colour bar to use for the density plot
                      Default: viridis
    :param norm_img_vals: Boolean specifying whether the colour bar values should be
                          normalised. Default: False
    :param use_log_norm: Specify whether to use log normalisation for the plot
                         instead of linear. (Default: False)
    :param norm_vmin: the minimum value for the normalisation (default: None).
                      If None then the minimum value will be calculated from the data.
    :param norm_vmax: the maximum value for the normalisation (default: None).
                      If None then the maximum value will be calculated from the data.
    :param vals_under_white: Set pixels with values less than norm_vmin to white
                             (i.e., mask / ignore). Can be useful if visualising
                             counts or density estimates.
    :param print_norm_vals: boolean specifying to print the normalisation min / max
                            values. This is useful for debugging and finding a range
                            of values before manually setting across a set of images.
    :param scale_bar_loc: the location on the plot of the scale bar. Options defined
                          by the matplotlib-scalebar module. But must be one of:
                          upper right, upper left, lower left, lower right, right,
                          center left, center right, lower center, upper center
                          or center. Default: upper right
    :param plot_zorder: the drawing order of artists is determined by their
                        zorder attribute, which is a floating point number.
                        Artists with higher zorder are drawn on top.
                        https://matplotlib.org/stable/gallery/misc/zorder_demo.html
    :return: The colour map and normalisation so a colour bar can be created.
             (c_cmap, c_norm)

    """
    if bbox is None:
        bbox = rsgislib.imageutils.get_img_bbox(input_img)

    img_data, img_coords = rsgislib.tools.plotting.get_gdal_raster_mpl_imshow(
        input_img, bands=[img_band], bbox=bbox
    )

    c_cmap = plt.get_cmap(cmap_name).copy()
    if norm_img_vals:
        if norm_vmin is None:
            norm_vmin = numpy.min(img_data)
        if norm_vmax is None:
            norm_vmax = numpy.max(img_data)

        if vals_under_white:
            matplotlib.colors.Colormap.set_under(c_cmap, color="white")

        if use_log_norm:
            c_norm = matplotlib.colors.LogNorm(vmin=norm_vmin, vmax=norm_vmax)
        else:
            c_norm = matplotlib.colors.Normalize(vmin=norm_vmin, vmax=norm_vmax)

        if print_norm_vals:
            print(f"{norm_vmin} - {norm_vmax}")
    else:
        c_norm = None

    ax.imshow(img_data, extent=img_coords, cmap=c_cmap, norm=c_norm, zorder=plot_zorder)
    ax.set_xlim([img_coords[0], img_coords[1]])
    ax.set_ylim([img_coords[2], img_coords[3]])
    ax.set_aspect("equal", adjustable="datalim")
    ax.ticklabel_format(useOffset=False, style="plain")

    if use_grid:
        ax.grid()

    if not show_map_axis:
        ax.set_axis_off()
        ax.set_axis_off()

    if show_scale_bar:
        distance_meters = 1
        img_epsg = rsgislib.imageutils.get_epsg_proj_from_img(input_img)
        if img_epsg == 4326:
            distance_meters = rsgislib.tools.projection.great_circle_distance(
                wgs84_p1=[bbox[0], bbox[3]], wgs84_p2=[bbox[0] + 1, bbox[3]]
            )

        ax.add_artist(ScaleBar(distance_meters, location=scale_bar_loc))

    if title_str is not None:
        ax.title.set_text(title_str)

    return c_cmap, c_norm


def create_vec_pt_density_map(
    ax: plt.axis,
    gp_vec: geopandas.GeoDataFrame,
    bbox: List[float],
    title_str: str = None,
    cmap_name: str = "viridis",
    use_log_norm: bool = False,
    density_norm_vmin: float = 1,
    density_norm_vmax: float = None,
    density_dpi: int = 72,
    show_scale_bar: bool = True,
    use_grid: bool = False,
    show_map_axis: bool = True,
    sub_in_vec: bool = False,
    clip_vec_bbox: bool = True,
    scale_bar_loc: str = "upper right",
    plot_zorder: float = 1,
):
    """
    A function which adds a vector layer(s) to a matplotlib axis as a density plot.
    Therefore, the vector layer needs to a points layer.

    Note. there are geopandas functions to calculate centroids or representative
    points if your dataset is not a points file.

    Colour bar information is returned. Note to add the colour bar to your plot
    you'll want to use code such as:

    c_cmap, c_norm =  mapping.create_vec_pt_density_map(...)
    fig.colorbar(matplotlib.cm.ScalarMappable(norm=c_norm, cmap=c_cmap),
                 label='Some Data', ax=ax1)

    :param ax: The matplotlib axis to which to add the vector layer. Note, the axis
               must be created with the option projection='scatter_density' which
               requires the mpl_scatter_density module to be available.
    :param gp_vec: a geopandas dataframe with the data - must be a points geometry
                   type.
    :param bbox: a bbox (MinX, MaxX, MinY, MaxY) for the region to be displayed
    :param title_str: an optional title for the map (Default: None)
    :param cmap_name: either a single string or list of strings with the colours
                          for filling the vectors. (Default: grey)
    :param norm_img_vals: Boolean specifying whether the colour bar values should be
                          normalised. Default: False
    :param use_log_norm: Specify whether to use log normalisation for the plot
                         instead of linear. (Default: False)
    :param density_norm_vmin: the minimum value for the normalisation (default: 1).
    :param density_norm_vmax: the maximum value for the normalisation (default: None).
                              If None then the maximum value will be automatically
                              defined.
    :param density_dpi: the dots per inch used for displaying the density plot. The
                        lower the value the large the bins (pixels) used for defining
                        the density plot.
    :param show_scale_bar: boolean specifying whether a scale bar should be added to
                           the axis. Default: False
    :param use_grid: boolean specifying whether a grid should be added to the axis.
                     Default: False
    :param show_map_axis: boolean specifying whether the axes should be shown
                          Default: False
    :param sub_in_vec: boolean specifying whether the vector layer should be
                       spatially subset before displaying as for large vector
                       layers this can make the processing much faster.
                       Default: False
    :param clip_vec_bbox: boolean specifying whether a bbox should be clipped to a
                          polygon defined by the bbox. Default: True
    :param scale_bar_loc: the location on the plot of the scale bar. Options defined
                          by the matplotlib-scalebar module. But must be one of:
                          upper right, upper left, lower left, lower right, right,
                          center left, center right, lower center, upper center
                          or center. Default: upper right
    :param plot_zorder: the drawing order of artists is determined by their
                        zorder attribute, which is a floating point number.
                        Artists with higher zorder are drawn on top.
                        https://matplotlib.org/stable/gallery/misc/zorder_demo.html
    :return: The colour map and normalisation so a colour bar can be created.
             (c_cmap, c_norm)

    """
    # Import to ensure the module is available.
    import mpl_scatter_density

    if sub_in_vec:
        min_x_sub = math.floor(bbox[0] - 4)
        max_x_sub = math.ceil(bbox[1] + 4)
        min_y_sub = math.floor(bbox[2] - 4)
        max_y_sub = math.ceil(bbox[3] + 4)
        gp_vec_sub = gp_vec.cx[min_x_sub:max_x_sub, min_y_sub:max_y_sub]
    else:
        gp_vec_sub = gp_vec

    if clip_vec_bbox:
        import shapely.geometry

        bbox_poly = shapely.geometry.box(
            min(bbox[0], bbox[1]),  # min_x
            min(bbox[2], bbox[3]),  # min_y
            max(bbox[0], bbox[1]),  # max_x
            max(bbox[2], bbox[3]),  # max_y
        )

        clip_poly_gdf = geopandas.GeoDataFrame(
            [1], geometry=[bbox_poly], crs=gp_vec_sub.crs
        )
        gp_vec_sub = gp_vec_sub.clip(clip_poly_gdf)

    c_cmap = plt.get_cmap(cmap_name).copy()
    # Make any values below normalisation transparent so background can be seen.
    matplotlib.colors.Colormap.set_under(c_cmap, color=[1, 1, 1, 0])

    if use_log_norm:
        c_norm = matplotlib.colors.LogNorm(
            vmin=density_norm_vmin, vmax=density_norm_vmax
        )
    else:
        c_norm = matplotlib.colors.Normalize(
            vmin=density_norm_vmin, vmax=density_norm_vmax
        )

    density_info = ax.scatter_density(
        gp_vec_sub["geometry"].x,
        gp_vec_sub["geometry"].y,
        dpi=density_dpi,
        norm=c_norm,
        cmap=c_cmap,
        zorder=plot_zorder,
    )

    ax.set_xlim([bbox[0], bbox[1]])
    ax.set_ylim([bbox[2], bbox[3]])
    ax.set_aspect("equal", adjustable="datalim")
    ax.ticklabel_format(useOffset=False, style="plain")

    if use_grid:
        ax.grid()

    if not show_map_axis:
        ax.set_axis_off()
        ax.set_axis_off()

    if show_scale_bar:
        distance_meters = 1
        vec_crs = str(gp_vec.crs)
        vec_epsg = int(vec_crs.split(":")[1])
        if vec_epsg == 4326:
            distance_meters = rsgislib.tools.projection.great_circle_distance(
                wgs84_p1=[bbox[0], bbox[3]], wgs84_p2=[bbox[0] + 1, bbox[3]]
            )
        ax.add_artist(ScaleBar(distance_meters, location=scale_bar_loc))

    if title_str is not None:
        ax.title.set_text(title_str)

    return c_cmap, c_norm
    # return density_info
