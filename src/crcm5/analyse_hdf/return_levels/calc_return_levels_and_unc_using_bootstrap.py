import hashlib
from multiprocessing.pool import Pool
from pathlib import Path
import pickle
import time
import itertools as itt
from mpldatacursor import datacursor

import numpy as np

from crcm5.analyse_hdf import do_analysis_using_pytables as analysis
from crcm5.analyse_hdf.return_levels.extreme_commons import ExtremeProperties
from gev_dist.gevfit import do_gevfit_for_a_point


__author__ = 'huziy'


def get_return_levels_and_unc_using_bootstrap(rconfig, varname="STFL"):
    """
    return the extreme properties object result
        where result.return_lev_dict are all the return levels for a given simulation
              result.std_dict - are all the standard deviations from the bootstrap
    :param rconfig:
    :param varname:
    """
    result = ExtremeProperties()

    proc_pool = Pool(processes=20)
    all_bootstrap_indices = None

    for extr_type, months in ExtremeProperties.extreme_type_to_month_of_interest.items():

        result.return_lev_dict[extr_type] = {}
        result.std_dict[extr_type] = {}

        return_periods = ExtremeProperties.extreme_type_to_return_periods[extr_type].copy()

        # Do not do the calculations for the cached return periods
        cached_periods = []
        for return_period in list(return_periods):
            # Construct the name of the cache file
            cache_file = get_cache_file_name(rconfig, months=months,
                                             ret_period=return_period,
                                             extreme_type=extr_type,
                                             varname=varname)

            p = Path(cache_file)

            if p.is_file():
                cached_periods.append(return_period)
                return_periods.remove(return_period)

                cache_levs, cache_stds = pickle.load(p.open("rb"))
                print("Using cache from {}".format(str(p)))

                result.return_lev_dict[extr_type][return_period] = cache_levs
                result.std_dict[extr_type][return_period] = cache_stds

        # Do not do anything if the return levels for all periods are cached
        # for this type of extreme events
        if len(return_periods) == 0:
            continue

        # 3D array of annual extremes for each grid point
        t0 = time.clock()
        ext_values = analysis.get_annual_extrema(rconfig=rconfig, varname=varname,
                                                 months_of_interest=months,
                                                 n_avg_days=ExtremeProperties.extreme_type_to_n_agv_days[extr_type],
                                                 high_flow=ExtremeProperties.high == extr_type)

        print("Got extreme values for {}-{} in {}s".format(rconfig.start_year, rconfig.end_year, time.clock() - t0))

        nx, ny = ext_values.shape[1:]

        result.return_lev_dict[extr_type].update({k: -np.ones((nx, ny)) for k in return_periods})
        result.std_dict[extr_type].update({k: -np.ones((nx, ny)) for k in return_periods})


        import matplotlib.pyplot as plt
        plt.figure()

        # to_plot = ext_values[0].transpose().copy()
        # to_plot = np.ma.masked_where(to_plot >= 0, to_plot)
        # qm = plt.pcolormesh(to_plot)
        # datacursor(qm)
        # plt.colorbar()
        # plt.show()

        ext_values = np.where(ext_values >= 0, ext_values, 0)


        if all_bootstrap_indices is None:
            np.random.seed(seed=ExtremeProperties.seed)
            all_bootstrap_indices = np.array([np.random.random_integers(0, ext_values.shape[0] - 1, ext_values.shape[0])
                                              for _ in range(ExtremeProperties.nbootstrap)])





        # Probably needs to be optimized ...
        for i in range(nx):
            input_data = zip(ext_values[:, i, :].transpose(), itt.repeat(extr_type, ny),
                             itt.repeat(return_periods, ny), itt.repeat(all_bootstrap_indices, ny))

            ret_level_and_std_pairs = proc_pool.map(do_gevfit_for_a_point_single_arg, input_data)

            ret_levels, std_deviations = zip(*ret_level_and_std_pairs)

            for return_period in return_periods:
                result.return_lev_dict[extr_type][return_period][i, :] = [ret_levels[j][return_period] for j in range(ny)]
                result.std_dict[extr_type][return_period][i, :] = [std_deviations[j][return_period] for j in range(ny)]


            # Show the progress
            if i % 10 == 0:
                print("progress {}/{}".format(i, nx))


        # Save the computed return levels and standard deviations to the cache file
        for return_period in return_periods:
            # Construct the name of the cache file
            cache_file = get_cache_file_name(rconfig, months=months,
                                             ret_period=return_period,
                                             extreme_type=extr_type)

            p = Path(cache_file)

            to_save = [
                result.return_lev_dict[extr_type][return_period],
                result.std_dict[extr_type][return_period]
            ]

            pickle.dump(to_save, p.open("wb"))

    return result





def get_cache_file_name(rconfig, months=None, ret_period=2,
                        extreme_type="high", varname="STFL"):
    months_str = "-".join([str(m) for m in months])
    path_hash = hashlib.sha1(rconfig.data_path.encode()).hexdigest()
    return "RL_STD_{}_{}_{}-{}_{}_{}_{}.bin".format(varname,
                                                    extreme_type, rconfig.start_year,
                                                    rconfig.end_year, path_hash,
                                                    months_str, ret_period)


def do_gevfit_for_a_point_single_arg(arg):
    """
    Just a convenience stub function used to make it easier to call by multiprocessing pool
    :param arg:
    :return:
    """
    all_bs_indices = None
    if len(arg) == 3:
        extremes, extr_type, ret_periods = arg
    else:
        extremes, extr_type, ret_periods, all_bs_indices = arg

    # The delayed function to be called in parallel
    return do_gevfit_for_a_point(extremes,
                                 extreme_type=extr_type,
                                 return_periods=ret_periods, all_indices=all_bs_indices)
