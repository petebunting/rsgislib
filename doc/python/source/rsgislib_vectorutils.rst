RSGISLib Vector Utils Module
=================================


Vector Attributes
--------------------
.. autofunction:: rsgislib.vectorutils.vector_maths
.. autofunction:: rsgislib.vectorutils.copy_rat_cols_to_vector_lyr
.. autofunction:: rsgislib.vectorutils.match_closest_vec_pts
.. autoclass:: rsgislib.vectorutils.VecColVar
    :members:

Vector Projections
----------------------
.. autofunction:: rsgislib.vectorutils.get_proj_wkt_from_vec
.. autofunction:: rsgislib.vectorutils.get_proj_epsg_from_vec
.. autofunction:: rsgislib.vectorutils.redefine_vec_lyr_proj
.. autofunction:: rsgislib.vectorutils.reproj_vec_lyr_gp


Create Vectors
----------------
.. autofunction:: rsgislib.vectorutils.createvectors.polygonise_raster_to_vec_lyr
.. autofunction:: rsgislib.vectorutils.createvectors.vectorise_pxls_to_pts
.. autofunction:: rsgislib.vectorutils.createvectors.extract_image_footprint
.. autofunction:: rsgislib.vectorutils.createvectors.create_poly_vec_for_lst_bboxs
.. autofunction:: rsgislib.vectorutils.createvectors.define_grid
.. autofunction:: rsgislib.vectorutils.createvectors.create_wgs84_vector_grid
.. autofunction:: rsgislib.vectorutils.createvectors.create_poly_vec_bboxs
.. autofunction:: rsgislib.vectorutils.createvectors.write_pts_to_vec
.. autofunction:: rsgislib.vectorutils.createvectors.create_bboxs_for_pts
.. autofunction:: rsgislib.vectorutils.create_lines_of_points
.. autofunction:: rsgislib.vectorutils.createvectors.create_random_pts_in_radius
.. autofunction:: rsgislib.vectorutils.createvectors.create_random_pts_in_bbox
.. autofunction:: rsgislib.vectorutils.create_copy_vector_lyr
.. autofunction:: rsgislib.vectorutils.createvectors.create_vec_for_image
.. autofunction:: rsgislib.vectorutils.createvectors.create_hex_grid_bbox
.. autofunction:: rsgislib.vectorutils.createvectors.create_hex_grid_polys
.. autofunction:: rsgislib.vectorutils.createvectors.create_lines_vec
.. autofunction:: rsgislib.vectorutils.createvectors.create_img_transects
.. autofunction:: rsgislib.vectorutils.createvectors.create_binary_random_pt_smpls


Vector I/O
----------------
.. autofunction:: rsgislib.vectorutils.open_gdal_vec_lyr
.. autofunction:: rsgislib.vectorutils.read_vec_lyr_to_mem
.. autofunction:: rsgislib.vectorutils.get_mem_vec_lyr_subset
.. autofunction:: rsgislib.vectorutils.write_vec_lyr_to_file
.. autofunction:: rsgislib.vectorutils.vector_translate
.. autofunction:: rsgislib.vectorutils.reproj_vector_layer
.. autofunction:: rsgislib.vectorutils.reproj_vec_lyr_obj
.. autofunction:: rsgislib.vectorutils.reproj_wgs84_vec_to_utm


Create Rasters
-------------------
.. autofunction:: rsgislib.vectorutils.createrasters.rasterise_vec_lyr
.. autofunction:: rsgislib.vectorutils.createrasters.rasterise_vec_lyr_obj
.. autofunction:: rsgislib.vectorutils.createrasters.copy_vec_to_rat
.. autofunction:: rsgislib.vectorutils.createrasters.create_vector_range_lut_score_img
.. autofunction:: rsgislib.vectorutils.createrasters.create_vector_lst_lut_score_img
.. autofunction:: rsgislib.vectorutils.createrasters.create_dist_zones_to_vec_layer


Merge Vectors
---------------
.. autofunction:: rsgislib.vectorutils.merge_vectors_to_gpkg
.. autofunction:: rsgislib.vectorutils.merge_vector_lyrs_to_gpkg
.. autofunction:: rsgislib.vectorutils.merge_vectors_to_gpkg_ind_lyrs
.. autofunction:: rsgislib.vectorutils.merge_vector_layers
.. autofunction:: rsgislib.vectorutils.merge_vector_files
.. autofunction:: rsgislib.vectorutils.merge_utm_vecs_wgs84
.. autofunction:: rsgislib.vectorutils.merge_to_multi_layer_vec
.. autoclass:: rsgislib.vectorutils.VecLayersInfoObj
    :members:


Vector Select / Subset
-----------------------
.. autofunction:: rsgislib.vectorutils.spatial_select_gp
.. autofunction:: rsgislib.vectorutils.get_att_lst_select_feats
.. autofunction:: rsgislib.vectorutils.get_att_lst_select_feats_lyr_objs
.. autofunction:: rsgislib.vectorutils.get_att_lst_select_bbox_feats
.. autofunction:: rsgislib.vectorutils.get_att_lst_select_bbox_feats_lyr_objs
.. autofunction:: rsgislib.vectorutils.select_intersect_feats
.. autofunction:: rsgislib.vectorutils.export_spatial_select_feats
.. autofunction:: rsgislib.vectorutils.subset_envs_vec_lyr_obj
.. autofunction:: rsgislib.vectorutils.subset_veclyr_to_featboxs
.. autofunction:: rsgislib.vectorutils.spatial_select
.. autofunction:: rsgislib.vectorutils.subset_by_attribute
.. autofunction:: rsgislib.vectorutils.select_feats_str_search
.. autofunction:: rsgislib.vectorutils.drop_rows_by_attribute
.. autofunction:: rsgislib.vectorutils.drop_rows_by_multi_attributes
.. autofunction:: rsgislib.vectorutils.rm_feat_att_duplicates
.. autofunction:: rsgislib.vectorutils.spatial_select_bbox
.. autofunction:: rsgislib.vectorutils.vec_lyr_random_subset


Vector Split
---------------
.. autofunction:: rsgislib.vectorutils.split_vec_lyr
.. autofunction:: rsgislib.vectorutils.split_by_attribute
.. autofunction:: rsgislib.vectorutils.split_feats_to_mlyrs
.. autofunction:: rsgislib.vectorutils.create_n_random_subsets
.. autofunction:: rsgislib.vectorutils.split_vec_lyr_random_subset
.. autofunction:: rsgislib.vectorutils.create_train_test_smpls


Vector Geometry
----------------
.. autofunction:: rsgislib.vectorutils.geopd_check_polys_wgs84_bounds_geometry


Vector / Raster Tests
----------------------
.. autofunction:: rsgislib.vectorutils.does_vmsk_img_intersect


Vector Info
-------------
.. autofunction:: rsgislib.vectorutils.get_vec_feat_count
.. autofunction:: rsgislib.vectorutils.count_feats_per_att_val
.. autofunction:: rsgislib.vectorutils.get_vec_lyrs_lst
.. autofunction:: rsgislib.vectorutils.get_vec_layer_extent
.. autofunction:: rsgislib.vectorutils.get_vec_lyr_cols
.. autofunction:: rsgislib.vectorutils.get_ogr_vec_col_datatype_from_gdal_rat_col_datatype
.. autofunction:: rsgislib.vectorutils.get_vec_lyr_geom_type
.. autofunction:: rsgislib.vectorutils.get_geom_type_name


Vectors Utilities
-------------------
.. autofunction:: rsgislib.vectorutils.check_validate_geometries
.. autofunction:: rsgislib.vectorutils.delete_vector_file



* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
