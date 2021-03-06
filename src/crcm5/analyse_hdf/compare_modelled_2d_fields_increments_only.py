from collections import OrderedDict
from datetime import datetime
import os
from matplotlib.font_manager import FontProperties
from matplotlib.ticker import ScalarFormatter

from mpl_toolkits.basemap import maskoceans
from matplotlib import gridspec
from matplotlib.axes import Axes
from matplotlib.colorbar import Colorbar
from matplotlib.colors import LogNorm
from matplotlib.figure import Figure
from scipy.stats import ttest_ind
from tables import NoSuchNodeError

from crcm5 import infovar
from crcm5.analyse_hdf import common_plot_params as cpp
from util.number_formatting import ordinal


__author__ = 'huziy'

from crcm5.analyse_hdf import do_analysis_using_pytables as analysis
import matplotlib.pyplot as plt
import numpy as np
from crcm5.analyse_hdf import common_plot_params
from matplotlib import cm


images_folder = "/home/huziy/skynet3_rech1/Netbeans Projects/Python/RPN/images_for_lake-river_paper"
cache_folder = os.path.join(images_folder, "cache")


def compare_annual_mean_fields(paths=None, labels=None, varnames=None):
    compare(paths=paths, varnames=varnames, labels=labels, months_of_interest=list(range(1, 13)))


def _offset_multiplier(colorbar):
    ax = colorbar.ax

    title = ax.get_title()
    ax.set_title("{0}\n\n\n\n".format(title))


def compare(paths=None, path_to_control_data=None, control_label="",
            labels=None, varnames=None, levels=None, months_of_interest=None,
            start_year=None, end_year=None):
    """
    Comparing 2D fields
    :param paths: paths to the simulation results
    :param varnames:
    :param labels: Display name for each simulation (number of labels should
     be equal to the number of paths)
    :param path_to_control_data: the path with which the comparison done i.e. a in the following
     formula
            delta = (x - a)/a * 100%

     generates one image file per variable (in the folder images_for_lake-river_paper):
        compare_varname_<control_label>_<label1>_..._<labeln>_startyear_endyear.png

    """
    # get coordinate data  (assumes that all the variables and runs have the same coordinates)
    lons2d, lats2d, basemap = analysis.get_basemap_from_hdf(file_path=path_to_control_data)
    x, y = basemap(lons2d, lats2d)

    lake_fraction = analysis.get_array_from_file(path=path_to_control_data, var_name="lake_fraction")

    if lake_fraction is None:
        lake_fraction = np.zeros(lons2d.shape)

    ncolors = 10
    # +1 to include white
    diff_cmap = cm.get_cmap("RdBu_r", ncolors + 1)

    for var_name, level in zip(varnames, levels):
        sfmt = infovar.get_colorbar_formatter(var_name)
        control_means = analysis.get_mean_2d_fields_for_months(path=path_to_control_data, var_name=var_name,
                                                               months=months_of_interest,
                                                               start_year=start_year, end_year=end_year,
                                                               level=level)

        control_mean = np.mean(control_means, axis=0)
        fig = plt.figure()
        assert isinstance(fig, Figure)
        gs = gridspec.GridSpec(2, len(paths) + 1, wspace=0.5)

        # plot the control
        ax = fig.add_subplot(gs[0, 0])
        assert isinstance(ax, Axes)
        ax.set_title("{0}".format(control_label))
        ax.set_ylabel("Mean: $X_{0}$")
        to_plot = infovar.get_to_plot(var_name, control_mean,
                                      lake_fraction=lake_fraction, mask_oceans=True, lons=lons2d, lats=lats2d)
        # determine colorabr extent and spacing
        field_cmap, field_norm = infovar.get_colormap_and_norm_for(var_name, to_plot, ncolors=ncolors)

        basemap.pcolormesh(x, y, to_plot, cmap=field_cmap, norm=field_norm)
        cb = basemap.colorbar(format=sfmt)

        assert isinstance(cb, Colorbar)
        # cb.ax.set_ylabel(infovar.get_units(var_name))
        units = infovar.get_units(var_name)

        info = "Variable:" \
               "\n{0}" \
               "\nPeriod: {1}-{2}" \
               "\nMonths: {3}" \
               "\nUnits: {4}"

        info = info.format(infovar.get_long_name(var_name), start_year, end_year,
                           ",".join([datetime(2001, m, 1).strftime("%b") for m in months_of_interest]), units)

        ax.annotate(info, xy=(0.1, 0.3), xycoords="figure fraction")

        sel_axes = [ax]

        for the_path, the_label, column in zip(paths, labels, list(range(1, len(paths) + 1))):

            means_for_years = analysis.get_mean_2d_fields_for_months(path=the_path, var_name=var_name,
                                                                     months=months_of_interest,
                                                                     start_year=start_year, end_year=end_year)
            the_mean = np.mean(means_for_years, axis=0)

            # plot the mean value
            ax = fig.add_subplot(gs[0, column])
            sel_axes.append(ax)
            ax.set_title("{0}".format(the_label))
            to_plot = infovar.get_to_plot(var_name, the_mean, lake_fraction=lake_fraction,
                                          mask_oceans=True, lons=lons2d, lats=lats2d)

            basemap.pcolormesh(x, y, to_plot, cmap=field_cmap, norm=field_norm)
            ax.set_ylabel("Mean: $X_{0}$".format(column))
            cb = basemap.colorbar(format=sfmt)
            # cb.ax.set_ylabel(infovar.get_units(var_name))

            # plot the difference
            ax = fig.add_subplot(gs[1, column])
            sel_axes.append(ax)
            ax.set_ylabel("$X_{0} - X_0$".format(column))

            # #Mask only if the previous plot (means) is masked
            thediff = the_mean - control_mean

            if hasattr(to_plot, "mask"):
                to_plot = np.ma.masked_where(to_plot.mask, thediff)
            else:
                to_plot = thediff

            if var_name == "PR":  # convert to mm/day
                to_plot = infovar.get_to_plot(var_name, to_plot, mask_oceans=False)

            vmin = np.ma.min(to_plot)
            vmax = np.ma.max(to_plot)

            d = max(abs(vmin), abs(vmax))
            vmin = -d
            vmax = d

            field_norm, bounds, vmn_nice, vmx_nice = infovar.get_boundary_norm(vmin, vmax, diff_cmap.N,
                                                                               exclude_zero=False)
            basemap.pcolormesh(x, y, to_plot, cmap=diff_cmap, norm=field_norm, vmin=vmn_nice, vmax=vmx_nice)

            cb = basemap.colorbar(format=sfmt)

            t, pval = ttest_ind(means_for_years, control_means, axis=0)
            sig = pval < 0.1
            basemap.contourf(x, y, sig.astype(int), nlevels=2, hatches=["+", None], colors="none")

            # cb.ax.set_ylabel(infovar.get_units(var_name))

        # plot coastlines
        for the_ax in sel_axes:
            basemap.drawcoastlines(ax=the_ax, linewidth=common_plot_params.COASTLINE_WIDTH)

        # depends on the compared simulations and the months of interest
        fig_file_name = "compare_{0}_{1}_{2}_months-{3}.jpeg".format(var_name, control_label,
                                                                     "_".join(labels),
                                                                     "-".join([str(m) for m in months_of_interest]))
        figpath = os.path.join(images_folder, fig_file_name)
        fig.savefig(figpath, dpi=cpp.FIG_SAVE_DPI, bbox_inches="tight")
        plt.close(fig)


def plot_all_seasons_for_a_var_as_panel():
    # TODO:
    pass


def plot_differences_for_a_var_as_panel():
    # TODO:
    pass


def get_num_days(month_list):
    import calendar

    days = 0
    for m in month_list:
        days += calendar.monthrange(2001, m)[1]

    # Take a leap year into account
    if 2 in month_list:
        days += 0.25

    return days


class DomainProperties(object):
    # The class for holding properties of the simulation domain
    def __init__(self):
        self.lons2d = None
        self.lats2d = None
        self.basemap = None
        self.lake_fraction = None
        self.x = None
        self.y = None


    def get_lon_lat_and_basemap(self):
        return self.lons2d, self.lats2d, self.basemap


def _plot_row(axes, data, sim_label, var_name, increments=False,
              domain_props=None, season_list=None, significance=None):
    # data is a dict of season -> field
    # the field is a control mean in the case of the control mean
    # and the difference between the modified simulation and the control mean in the case of the modified simulation

    exclude_0_from_diff_colorbar = False

    assert isinstance(domain_props, DomainProperties)
    print("plotting row for {0}; increments = ({1})".format(var_name, increments))

    lons2d, lats2d, basemap = domain_props.get_lon_lat_and_basemap()
    x, y = domain_props.x, domain_props.y

    vmin = None
    vmax = None
    # determine vmin and vmax for the row
    for season, field in data.items():
        # field = _get_to_plot(var_name, field, lake_fraction=domain_props.lake_fraction, lons=lons2d, lats = lats2d)
        min_current, max_current = np.percentile(field[~field.mask], 1), np.percentile(field[~field.mask], 99)
        if vmin is None or min_current < vmin:
            vmin = min_current

        if vmax is None or max_current > vmax:
            vmax = max_current

    ncolors = 13 if exclude_0_from_diff_colorbar else 10
    bounds = None
    if increments:
        # +1 to include white
        if vmin * vmax >= 0:
            if vmin >= 0:
                field_cmap = cm.get_cmap("YlOrBr_r", ncolors)
            else:
                field_cmap = cm.get_cmap("YlGnBu_r", ncolors)
            field_norm, bounds, bounds_min, bounds_max = infovar.get_boundary_norm(vmin, vmax, ncolors,
                                                                                   exclude_zero=exclude_0_from_diff_colorbar,
                                                                                   varname=var_name,
                                                                                   difference=increments)
        else:
            field_cmap = cm.get_cmap("RdBu_r", ncolors)
            d = max(abs(vmin), abs(vmax))
            field_norm, bounds, bounds_min, bounds_max = infovar.get_boundary_norm(-d, d, ncolors,
                                                                                   exclude_zero=exclude_0_from_diff_colorbar,
                                                                                   varname=var_name,
                                                                                   difference=increments)
    else:
        # determine colorabr extent and spacing
        field_cmap, field_norm = infovar.get_colormap_and_norm_for(var_name, vmin=vmin, vmax=vmax, ncolors=ncolors)
    print("vmin = {0}; vmax = {1}".format(vmin, vmax))

    col = 0
    # axes[0].set_ylabel(sim_label)
    im = None
    for season in season_list:
        field = data[season]
        ax = axes[col]
        if not increments:
            # since the increments go below
            ax.set_title(season)
        else:
            mean_val = float("{0:.1e}".format(field.mean()))
            sf = ScalarFormatter(useMathText=True)
            sf.set_powerlimits((-2, 3))
            # ax.set_title(r"$\Delta_{\rm mean} = " + sf.format_data(mean_val) + " $")

        basemap.drawmapboundary(ax=ax, fill_color="gray")
        im = basemap.pcolormesh(x, y, field, norm=field_norm, cmap=field_cmap, ax=ax)
        basemap.drawcoastlines(ax=ax, linewidth=cpp.COASTLINE_WIDTH)

        if significance is not None:
            cs = basemap.contourf(x, y, significance[season], levels=[0, 0.5, 1],
                                  colors="none",
                                  hatches=[None, ".."],
                                  ax=ax)

            # basemap.contour(x, y, significance[season], levels = [0.5, ], ax = ax,
            # linewidths = 0.5, colors="k")

            if col == 0 and False:
                # create a legend for the contour set
                artists, labels = cs.legend_elements()
                ax.legend([artists[-1], ], ["Significant changes \n with (p = 0.1)", ],
                          handleheight=0.5, fontsize="x-small")

        col += 1

    # plot the common colorbar
    if isinstance(field_norm, LogNorm):
        cb = plt.colorbar(im, cax=axes[-1])
    else:
        cb = plt.colorbar(im, cax=axes[-1], extend="both", ticks=bounds)

    cb.ax.set_title(infovar.get_units(var_name))


def plot_control_and_differences_in_one_panel_for_all_seasons_for_all_vars(
        varnames=None, levels=None,
        season_to_months=None,
        start_year=None,
        end_year=None):
    season_list = list(season_to_months.keys())

    pvalue_max = 0.1

    # crcm5-r vs crcm5-hcd-r
    # control_path = "/skynet3_rech1/huziy/hdf_store/quebec_0.1_crcm5-r_spinup.hdf"
    # control_label = "CRCM5-R"
    # paths = ["/skynet3_rech1/huziy/hdf_store/quebec_0.1_crcm5-hcd-r_spinup2.hdf", ]
    # labels = ["CRCM5-HCD-R"]

    # crcm5-hcd-rl vs crcm5-hcd-r
    # control_path = "/skynet3_rech1/huziy/hdf_store/quebec_0.1_crcm5-hcd-r_spinup2.hdf"
    # control_label = "CRCM5-HCD-R"
    # paths = ["/skynet3_rech1/huziy/hdf_store/quebec_0.1_crcm5-hcd-rl_spinup.hdf", ]
    # labels = ["CRCM5-HCD-RL"]

    # compare simulations with and without interflow
    # control_path = "/skynet3_rech1/huziy/hdf_store/quebec_0.1_crcm5-hcd-rl_spinup.hdf"
    # control_label = "CRCM5-HCD-RL"
    #
    # paths = ["/skynet3_rech1/huziy/hdf_store/quebec_0.1_crcm5-hcd-rl-intfl_do_not_discard_small.hdf", ]
    # labels = ["CRCM5-HCD-RL-INTFL"]

    # very high hydr cond
    # control_path = "/skynet3_rech1/huziy/hdf_store/quebec_0.1_crcm5-hcd-rl-intfl_do_not_discard_small.hdf"
    # control_label = "CRCM5-HCD-RL-INTFL"
    ##
    # paths = ["/skynet3_rech1/huziy/hdf_store/quebec_0.1_crcm5-hcd-rl-intfl_sani-10000.hdf", ]
    # labels = ["CRCM5-HCD-RL-INTFL-sani=10000"]

    # Interflow effect
    # control_path = "/skynet3_rech1/huziy/hdf_store/quebec_0.1_crcm5-hcd-rl_spinup.hdf"
    # control_label = "CRCM5-HCD-RL"
    # ##
    # paths = ["/skynet3_rech1/huziy/hdf_store/quebec_0.1_crcm5-hcd-rl-intfl_spinup_ITFS.hdf5", ]
    # labels = ["ITFS"]


    # total lake effect
    # control_path = "/skynet3_rech1/huziy/hdf_store/quebec_0.1_crcm5-r.hdf5"
    # control_label = "CRCM5-NL"
    #
    # paths = ["/skynet3_rech1/huziy/hdf_store/quebec_0.1_crcm5-hcd-rl.hdf5", ]
    # labels = ["CRCM5-L2", ]



    # lake effect (lake-atm interactions)
    # control_path = "/skynet3_rech1/huziy/hdf_store/quebec_0.1_crcm5-r.hdf5"
    # control_label = "CRCM5-R"
    #
    # paths = ["/skynet3_rech1/huziy/hdf_store/quebec_0.1_crcm5-hcd-r.hdf5", ]
    # labels = ["CRCM5-HCD-R", ]

    # lake effect (lake-river interactions)
    # control_path = "/skynet3_rech1/huziy/hdf_store/quebec_0.1_crcm5-hcd-r.hdf5"
    # control_label = "CRCM5-L1"
    #
    # paths = ["/skynet3_rech1/huziy/hdf_store/quebec_0.1_crcm5-hcd-rl.hdf5", ]
    # labels = ["CRCM5-HCD-L2", ]


    # interflow effect ()
    control_path = "/skynet3_rech1/huziy/hdf_store/quebec_0.1_crcm5-hcd-rl.hdf5"
    control_label = "CRCM5-L2"

    paths = ["/skynet3_rech1/huziy/hdf_store/quebec_0.1_crcm5-hcd-rl-intfl_ITFS.hdf5", ]
    labels = ["CRCM5-L2I", ]


    # paths = ["/skynet3_rech1/huziy/hdf_store/quebec_0.1_crcm5-hcd-rl-intfl_ITFS_avoid_truncation1979-1989.hdf5", ]
    # labels = ["CRCM5-HCD-RL-INTFb", ]



    # interflow effect (avoid truncation and bigger slopes)
    # control_path = "/skynet3_rech1/huziy/hdf_store/quebec_0.1_crcm5-hcd-rl-intfl_ITFS.hdf5"
    # control_label = "CRCM5-HCD-RL-INTF"
    #
    # paths = ["/skynet3_rech1/huziy/hdf_store/quebec_0.1_crcm5-hcd-rl-intfl_ITFS_avoid_truncation1979-1989.hdf5", ]
    # labels = ["CRCM5-HCD-RL-INTF-improved", ]
    #

    row_labels = [
        r"{} vs {}".format(s, control_label) for s in labels
    ]
    print(labels)

    # varnames = ["QQ", ]
    # levels = [None, ]

    assert len(levels) == len(varnames)

    lons2d, lats2d, basemap = analysis.get_basemap_from_hdf(file_path=control_path)
    x, y = basemap(lons2d, lats2d)
    # save the domain properties for reuse
    domain_props = DomainProperties()
    domain_props.basemap = basemap
    domain_props.lons2d = lons2d
    domain_props.lats2d = lats2d
    domain_props.x = x
    domain_props.y = y

    lake_fraction = analysis.get_array_from_file(path=control_path, var_name=infovar.HDF_LAKE_FRACTION_NAME)
    dpth_to_bedrock = analysis.get_array_from_file(path=control_path, var_name=infovar.HDF_DEPTH_TO_BEDROCK_NAME)

    assert dpth_to_bedrock is not None


    if lake_fraction is None:
        lake_fraction = np.zeros(lons2d.shape)

    ncolors = 10
    # +1 to include white
    diff_cmap = cm.get_cmap("RdBu", ncolors + 1)


    # Do the plotting for each variable
    fig = plt.figure()
    assert isinstance(fig, Figure)

    # plot the control data
    ncols = len(season_list) + 1  # +1 is for the colorbar
    gs = gridspec.GridSpec(len(varnames), ncols, width_ratios=[1.0, ] * (ncols - 1) + [0.07], top=0.95)


    lev_width_3d = np.ones(dpth_to_bedrock.shape + infovar.soil_layer_widths_26_to_60.shape)
    lev_width_3d *= infovar.soil_layer_widths_26_to_60[np.newaxis, np.newaxis, :]
    lev_bot_3d = lev_width_3d.cumsum(axis=2)

    correction = -lev_bot_3d + dpth_to_bedrock[:, :, np.newaxis]
    # Apply the correction only at points where the layer bottom is lower than
    # the bedrock
    lev_width_3d[correction < 0] += correction[correction < 0]
    lev_width_3d[lev_width_3d < 0] = 0


    # plot the plots one file per variable
    for var_name, level, the_row in zip(varnames, levels, list(range(len(varnames)))):
        sfmt = infovar.get_colorbar_formatter(var_name)
        season_to_control_mean = {}
        label_to_season_to_difference = {}
        label_to_season_to_significance = {}

        try:
            # Calculate the difference for each season, and save the results to dictionaries
            # to access later when plotting
            for season, months_of_interest in season_to_months.items():
                print("working on season: {0}".format(season))

                control_means = analysis.get_mean_2d_fields_for_months(path=control_path, var_name=var_name,
                                                                       months=months_of_interest,
                                                                       start_year=start_year, end_year=end_year,
                                                                       level=level)

                control_mean = np.mean(control_means, axis=0)

                control_mean = infovar.get_to_plot(var_name, control_mean,
                                                   lake_fraction=domain_props.lake_fraction,
                                                   lons=lons2d, lats=lats2d, level_width_m=lev_width_3d[:, :, level])

                # multiply by the number of days in a season for PR and TRAF to convert them into mm from mm/day
                if var_name in ["PR", "TRAF", "TDRA"]:
                    control_mean *= get_num_days(months_of_interest)
                    infovar.change_units_to(varnames=[var_name, ], new_units=r"${\rm mm}$")

                season_to_control_mean[season] = control_mean

                print("calculated mean from {0}".format(control_path))

                # calculate the difference for each simulation
                for the_path, the_label in zip(paths, row_labels):
                    modified_means = analysis.get_mean_2d_fields_for_months(path=the_path, var_name=var_name,
                                                                            months=months_of_interest,
                                                                            start_year=start_year, end_year=end_year,
                                                                            level=level)

                    tval, pval = ttest_ind(modified_means, control_means, axis=0, equal_var=False)
                    significance = ((pval <= pvalue_max) & (~control_mean.mask)).astype(int)
                    print("pval ranges: {} to {}".format(pval.min(), pval.max()))

                    modified_mean = np.mean(modified_means, axis=0)
                    if the_label not in label_to_season_to_difference:
                        label_to_season_to_difference[the_label] = OrderedDict()
                        label_to_season_to_significance[the_label] = OrderedDict()

                    modified_mean = infovar.get_to_plot(var_name, modified_mean,
                                                        lake_fraction=domain_props.lake_fraction, lons=lons2d,
                                                        lats=lats2d, level_width_m=lev_width_3d[:, :, level])

                    # multiply by the number of days in a season for PR and TRAF to convert them into mm from mm/day
                    if var_name in ["PR", "TRAF", "TDRA"]:
                        modified_mean *= get_num_days(months_of_interest)

                    diff_vals = modified_mean - control_mean

                    print("diff ranges: min: {0};  max: {1}".format(diff_vals.min(), diff_vals.max()))
                    label_to_season_to_difference[the_label][season] = diff_vals
                    label_to_season_to_significance[the_label][season] = significance

                    print("Calculated mean and diff from {0}".format(the_path))
        except NoSuchNodeError:
            print("Could not find {0}, skipping...".format(var_name))
            continue





        for the_label, data in label_to_season_to_difference.items():
            axes = []
            for col in range(ncols):
                axes.append(fig.add_subplot(gs[the_row, col]))

            # Set season titles
            if the_row == 0:
                for the_season, ax in zip(season_list, axes):
                    ax.set_title(the_season)


            _plot_row(axes, data, the_label, var_name, increments=True, domain_props=domain_props,
                      season_list=season_list, significance=label_to_season_to_significance[the_label])

            var_label = infovar.get_long_display_label_for_var(var_name)
            if var_name in ["I1"]:
                var_label = "{}\n{} layer".format(var_label, ordinal(level + 1))

            axes[0].set_ylabel(var_label)

    fig.suptitle("({}) vs ({})".format(labels[0], control_label), font_properties=FontProperties(weight="bold"))
    folderpath = os.path.join(images_folder, "seasonal_mean_maps/{0}_vs_{1}_for_{2}_{3}-{4}".format(
        "_".join(labels), control_label, "-".join(list(season_to_months.keys())), start_year, end_year))

    if not os.path.isdir(folderpath):
        os.mkdir(folderpath)

    imname = "{0}_{1}.png".format("-".join(varnames), "_".join(labels + [control_label]))
    impath = os.path.join(folderpath, imname)
    fig.savefig(impath, bbox_inches="tight")


def main():
    import application_properties

    application_properties.set_current_directory()
    import time

    t0 = time.clock()
    # study_interflow_effect()
    print("Execution time: {0} seconds".format(time.clock() - t0))


if __name__ == "__main__":
    main()
