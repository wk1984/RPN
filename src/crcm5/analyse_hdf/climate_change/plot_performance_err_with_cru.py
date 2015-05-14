from collections import OrderedDict
from pathlib import Path
from matplotlib import cm
from matplotlib.gridspec import GridSpec
from matplotlib.ticker import MaxNLocator
from mpl_toolkits.basemap import maskoceans
from crcm5 import infovar
from crcm5.analyse_hdf.run_config import RunConfig
from cru.temperature import CRUDataManager
from swe import SweDataManager
from util import plot_utils

from crcm5.analyse_hdf import do_analysis_using_pytables as analysis
from util.geo import quebec_info
from util.geo.basemap_info import BasemapInfo
from util.seasons_info import DEFAULT_SEASON_TO_MONTHS
import numpy as np

__author__ = 'huziy'

# Folder where images generated by the script will go
img_folder = Path("cc_paper/performane_error_with_cru")

BASIN_BOUNDARIES_SHP = quebec_info.BASIN_BOUNDARIES_FILE_LATLON

import matplotlib.pyplot as plt


def aggregate_array(in_arr, nagg_x=2, nagg_y=2):
    """


    :type in_arr: numpy.ndarray
    :type nagg_y: int
    """
    from skimage.util import view_as_blocks

    return view_as_blocks(in_arr, (nagg_x, nagg_y)).mean(axis=2).mean(axis=2)



def plot_seasonal_mean_biases(season_to_error_field=None, varname="", basemap_info=None, axes_list=None):
    assert isinstance(basemap_info, BasemapInfo)

    cmap = cm.get_cmap("RdBu_r", 20)


    # Set to False if you want the limits to be recalculated from data
    manual_limits = True

    d = max([np.percentile(np.abs(field[~field.mask]), 95) for s, field in season_to_error_field.items()])

    if manual_limits and varname in ["PR", "TT", "I5"]:
        if varname == "PR":
            d = 3
        if varname == "TT":
            d = 7
        if varname == "I5":
            d = 100

    clevs = MaxNLocator(nbins=cmap.N, symmetric=True).tick_values(-d, d)

    fig = None
    fig_path = None
    if axes_list is None:
        fig_path = img_folder.joinpath("{}.png".format(varname))
        fig = plt.figure()

    nrows = 2
    ncols = 2
    gs = GridSpec(nrows, ncols=ncols + 1, width_ratios=[1, 1, 0.05])

    xx, yy = basemap_info.get_proj_xy()

    cs = None
    for i, season in enumerate(season_to_error_field):
        row = i // ncols
        col = i % ncols

        if axes_list is None:
            ax = fig.add_subplot(gs[row, col])
        else:
            ax = axes_list[i]

        cs = basemap_info.basemap.contourf(xx, yy, season_to_error_field[season][:], ax=ax, cmap=cmap, levels=clevs,
                                           extend="both")
        basemap_info.basemap.drawcoastlines(ax=ax)
        ax.set_title(season)
        if i == 0:
            ax.set_ylabel(infovar.get_display_label_for_var(varname=varname))
        # basemap_info.basemap.colorbar(cs)
        basemap_info.basemap.readshapefile(BASIN_BOUNDARIES_SHP[:-4], "basin", ax=ax)

    cax = fig.add_subplot(gs[:, -1]) if axes_list is None else axes_list[-1]
    cax.set_title(infovar.get_units(var_name=varname))
    plt.colorbar(cs, cax=cax)

    if axes_list is None:
        with fig_path.open("wb") as figfile:
            fig.savefig(figfile, format="png", bbox_inches="tight")

        plt.close(fig)


def compare_vars(vname_model="TT", vname_obs="tmp", r_config=None,
                 season_to_months=None,
                 obs_path=None, nx_agg=5, ny_agg=5, bmp_info_agg=None, axes_list=None):
    """

    :param vname_model:
    :param vname_obs:
    :param r_config:
    :param season_to_months:
    :param obs_path:
    :param nx_agg:
    :param ny_agg:
    :param bmp_info_agg:
    :param axes_list: if it is None the plots for each variable is done in separate figures
    """
    seasonal_clim_fields_model = analysis.get_seasonal_climatology_for_runconfig(run_config=r_config,
                                                                                 varname=vname_model, level=0,
                                                                                 season_to_months=season_to_months)

    season_to_clim_fields_model_agg = OrderedDict()
    for season, field in seasonal_clim_fields_model.items():
        print(field.shape)
        season_to_clim_fields_model_agg[season] = aggregate_array(field, nagg_x=nx_agg, nagg_y=ny_agg)
        if vname_model == "PR":
            season_to_clim_fields_model_agg[season] *= 1.0e3 * 24 * 3600

    if vname_obs in ["SWE", ]:
        cru = SweDataManager(path=obs_path, var_name=vname_obs)
    elif obs_path is None:
        cru = CRUDataManager(var_name=vname_obs)
    else:
        cru = CRUDataManager(var_name=vname_obs, path=obs_path)

    seasonal_clim_fields_obs = cru.get_seasonal_means(season_name_to_months=season_to_months,
                                                      start_year=r_config.start_year,
                                                      end_year=r_config.end_year)

    seasonal_clim_fields_obs_interp = OrderedDict()
    for season, cru_field in seasonal_clim_fields_obs.items():
        seasonal_clim_fields_obs_interp[season] = cru.interpolate_data_to(cru_field,
                                                                          lons2d=bmp_info_agg.lons,
                                                                          lats2d=bmp_info_agg.lats, nneighbours=1)

        # assert hasattr(seasonal_clim_fields_obs_interp[season], "mask")

    season_to_err = OrderedDict()
    for season in seasonal_clim_fields_obs_interp:
        season_to_err[season] = season_to_clim_fields_model_agg[season] - seasonal_clim_fields_obs_interp[season]

        if vname_model in ["I5"]:
            lons = bmp_info_agg.lons.copy()
            lons[lons > 180] -= 360
            season_to_err[season] = maskoceans(lons, bmp_info_agg.lats, season_to_err[season])

    plot_seasonal_mean_biases(season_to_error_field=season_to_err, varname=vname_model, basemap_info=bmp_info_agg,
                              axes_list=axes_list)


def main():

    season_to_months = DEFAULT_SEASON_TO_MONTHS

    r_config = RunConfig(
        data_path="/RESCUE/skynet3_rech1/huziy/hdf_store/quebec_0.1_crcm5-hcd-rl.hdf5",
        start_year=1980, end_year=2009, label="CRCM5-L"
    )

    # Number of points for aggregation
    nx_agg = 5
    ny_agg = 5

    bmp_info = analysis.get_basemap_info_from_hdf(file_path=r_config.data_path)

    bmp_info_agg = bmp_info.get_aggregated(nagg_x=nx_agg, nagg_y=ny_agg)


    # Validate temperature and precip
    model_vars = ["TT", "PR"]
    obs_vars = ["tmp", "pre"]
    obs_paths = [
        "/HOME/data/Validation/CRU_TS_3.1/Original_files_gzipped/cru_ts_3_10.1901.2009.tmp.dat.nc",
        "/HOME/data/Validation/CRU_TS_3.1/Original_files_gzipped/cru_ts_3_10.1901.2009.pre.dat.nc"
    ]

    plot_all_vars_in_one_fig = True

    fig = None
    gs = None
    row_axes = None
    ncols = None
    if plot_all_vars_in_one_fig:
        plot_utils.apply_plot_params(font_size=12, width_pt=None, width_cm=25, height_cm=12)
        fig = plt.figure()
        ncols = len(season_to_months) + 1
        gs = GridSpec(len(model_vars), ncols, width_ratios=(ncols - 1) * [1., ] + [0.05, ])
    else:
        plot_utils.apply_plot_params(font_size=12, width_pt=None, width_cm=25, height_cm=25)


    row = 0
    for mname, oname, opath in zip(model_vars, obs_vars, obs_paths):

        if plot_all_vars_in_one_fig:
            row_axes = [fig.add_subplot(gs[row, col]) for col in range(ncols)]

        compare_vars(vname_model=mname, vname_obs=oname, r_config=r_config,
                     season_to_months=season_to_months,
                     nx_agg=nx_agg, ny_agg=ny_agg, bmp_info_agg=bmp_info_agg,
                     obs_path=opath, axes_list=row_axes)

        row += 1

    # Save the figure if necessary
    if plot_all_vars_in_one_fig:
        fig_path = img_folder.joinpath("{}.png".format("_".join(model_vars)))
        with fig_path.open("wb") as figfile:
            fig.savefig(figfile, format="png", bbox_inches="tight")

        plt.close(fig)


def main_wrapper():
    print("Comparing with CRU ...")
    import application_properties

    application_properties.set_current_directory()

    if not img_folder.is_dir():
        img_folder.mkdir(parents=True)

    #
    main()



if __name__ == '__main__':
    main_wrapper()