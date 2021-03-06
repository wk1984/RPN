import os
from mpl_toolkits.basemap import Basemap

from crcm5.mh_domains import default_domains
from domains.grid_config import GridConfig
import netCDF4 as nc
from rpn.rpn import RPN
import matplotlib.pyplot as plt
import numpy as np

__author__ = "huziy"
__date__ = "$Aug 20, 2011 1:45:02 PM$"


# LAM projection specification
# 1st point - center of the grid
# 2nd point - 90 degrees to the East along the new equator?



def convert(nc_path='directions_africa_dx0.44deg.nc', out_path=None, gc=None, do_plots=False):
    """
    :param out_path:
    :type nc_path: string
    :type gc: GridConfig
    gc - holds grid parameters
    """
    ds = nc.Dataset(nc_path)

    ncnametorpnname = {'flow_direction_value': 'fldr', 'slope': 'slop',
                       'channel_length': 'leng', 'accumulation_area': 'facc',
                       "lake_fraction": "lkfr", "lake_outlet": "lkou",
                       "drainage_density": "dd"
                       }
    if out_path is None:
        rObj = RPN(os.path.basename(nc_path)[:-2] + "rpn", mode='w')
    else:
        rObj = RPN(out_path, mode='w')

    #
    ig = []

    # params
    dx = gc.dx
    dy = gc.dy
    iref = gc.iref  # no need to do -1, doing it later in the formulas
    jref = gc.jref
    xref = gc.xref  # rotated longitude
    yref = gc.yref  # rotated latitude

    # projection parameters
    if hasattr(gc, "rll"):
        lon1 = gc.rll.lon1
        lat1 = gc.rll.lat1

        lon2 = gc.rll.lon2
        lat2 = gc.rll.lat2
    else:
        raise Exception(
            "You are trying to use an outdated version of the GridConfig class, Please switch to the one where projection info is bundled into the rll field")

    ni = gc.ni
    nj = gc.nj
    x = np.zeros((ni, 1))
    x[:, 0] = [xref + (i - iref + 1) * dx for i in range(ni)]

    y = np.zeros((1, nj))
    y[0, :] = [yref + (j - jref + 1) * dy for j in range(nj)]

    # write coordinates
    rObj.write_2D_field(name="^^", grid_type="E", data=y, typ_var="X", level=0, ip=list(range(100, 103)),
                        lon1=lon1, lat1=lat1, lon2=lon2, lat2=lat2, label="Routing")

    rObj.write_2D_field(name=">>", grid_type="E", data=x, typ_var="X", level=0, ip=list(range(100, 103)),
                        lon1=lon1, lat1=lat1, lon2=lon2, lat2=lat2, label="Routing")

    info = rObj.get_current_info()
    ip_xy = info["ip"]
    ig = ip_xy + [0]
    print("ig = ", ig)

    slope_data = None
    flowdir_data = None
    for ncName, rpnName in ncnametorpnname.items():
        data = ds.variables[ncName][:]
        grid_type = 'Z'
        rObj.write_2D_field(name=rpnName, level=1, data=data,
                            grid_type=grid_type, ig=ig, label="Routing")
        if ncName == "slope":
            slope_data = data
        if ncName == "flow_direction_value":
            flowdir_data = data
    rObj.close()


    if do_plots:
        ind = (flowdir_data > 0) & (slope_data < 0)
        print(flowdir_data[ind], slope_data[ind])
        assert np.all(~ind)

        channel_length = ds.variables['channel_length'][:]
        acc_area = ds.variables['accumulation_area'][:]
        slope = ds.variables['slope'][:]
        fldr = ds.variables['flow_direction_value'][:]

        lons = ds.variables["lon"][:]
        lats = ds.variables["lat"][:]

        basemap = Basemap()
        [x, y] = basemap(lons, lats)

        plt.figure()
        acc_area = np.ma.masked_where((acc_area < 0), acc_area)
        # basemap.drawcoastlines(linewidth = 0.1)
        # basemap.pcolormesh(x, y, acc_area)
        plt.pcolormesh(acc_area.transpose())

        plt.colorbar()
        plt.title('accumulation area')
        # plt.xlim(x.min(), x.max())
        # plt.ylim(y.min(), y.max())
        plt.savefig("accumulation_area.png")

        plt.figure()
        channel_length = np.ma.masked_where(channel_length < 0, channel_length)
        plt.pcolormesh(channel_length.transpose())
        print("channel_length limits", channel_length.min(), channel_length.max())
        plt.colorbar()
        plt.title('channel length')
        plt.savefig("channel_length.png")

        plt.figure()
        slope = np.ma.masked_where(slope < 0, slope)
        plt.pcolormesh(slope.transpose())
        plt.colorbar()
        plt.title('slope')
        plt.savefig("slope.png")

        plt.figure()
        a2 = 11.0
        a3 = 0.43
        a4 = 1.0
        indx = np.where((slope >= 0) & (channel_length >= 0))
        x = np.zeros(slope.shape)
        x = np.ma.masked_where(slope < 0, x)
        x[indx] = (a2 + a3 * acc_area[indx] ** a4) * channel_length[indx]
        plt.pcolormesh(x.transpose())
        plt.colorbar()

        plt.savefig("bankfull_store.png")
        print(list(ds.variables.keys()))

        plt.figure()
        print('fldr where slope is negative')
        print(np.all(fldr[slope < 0] == -1))
        fldr = np.ma.masked_where(fldr < 0, fldr)
        plt.pcolormesh(fldr.transpose())
        plt.colorbar()
        plt.title('fldr')

        print(fldr.shape)
        fldr = fldr[10:-10, 10:-10]
        channel_length = channel_length[10:-10, 10:-10]
        slope = slope[10:-10, 10:-10]
        plt.savefig("fldr.png")

        print(len(fldr[fldr == 0]))

        plt.close("all")
    pass


import application_properties

if __name__ == "__main__":
    application_properties.set_current_directory()
    # convert(nc_path="directions_qc_dx0.1deg260x260.nc")
    # convert(nc_path="/home/huziy/skynet3_exec1/hydrosheds/directions_qc_dx0.1deg_2.nc")
    # convert(nc_path="/home/huziy/skynet3_rech1/Netbeans Projects/Java/DDM/directions_qc_dx0.5deg_2.nc")
    # convert(nc_path="/home/huziy/skynet3_rech1/Netbeans Projects/Java/DDM/directions_qc_dx0.5deg_86x86.v3.nc")
    # convert(nc_path="/home/huziy/skynet3_rech1/Netbeans Projects/Java/DDM/directions_qc_dx0.5deg_86x86.v4.nc")
    # convert(nc_path="/home/huziy/skynet3_rech1/Netbeans Projects/Java/DDM/directions_qc_dx0.1deg_3.nc")
    # convert(nc_path="/home/huziy/skynet3_rech1/Netbeans Projects/Java/DDM/directions_qc_dx0.1deg_4.nc")

    # gc = GridConfig.get_default_for_resolution(res = 0.1)
    # convert(nc_path="/home/huziy/skynet3_rech1/Netbeans Projects/Java/DDM/directions_with_drainage_density/directions_qc_dx0.1deg_4.nc",
    #    gc=gc, out_path="directions_0.1deg_with_dd.rpn")


    # params taken from gemclim settings
    params = dict(
        dx=0.1, dy=0.1,
        lon1=180, lat1=0.0,
        lon2=-84, lat2=1.0,
        iref=105, jref=100,
        ni=210, nj=130,
        xref=276.0, yref=48.0
    )

    gc = GridConfig(**params)
    # convert(
    #     nc_path="/skynet3_rech1/huziy/hydrosheds/directions_great_lakes_210_130_0.1deg.nc",
    #     gc=gc, out_path="directions_0.1deg_GL.rpn")

    # convert(
    #     nc_path="/RESCUE/skynet3_rech1/huziy/Netbeans Projects/Java/DDM/directions_great_lakes_210_130_0.1deg_v2.nc",
    #     gc=gc, out_path="/RESCUE/skynet3_rech1/huziy/GLK_exps_geophysical_fields/directions_0.1deg_GL_v2.rpn")



    # Extended Northeastern North America
    # params_gl_ext = dict(
    #     dx=0.1, dy=0.1,
    #     lon1=180, lat1=0.0,
    #     lon2=-84, lat2=1.0,
    #     iref=135, jref=120,
    #     ni=440, nj=260,
    #     xref=276.0, yref=48.0
    # )
    # gc_gl_ext = GridConfig(**params_gl_ext)
    #
    # convert(nc_path="/RESCUE/skynet3_rech1/huziy/Netbeans Projects/Java/DDM/directions_440x260_GL+NENA_0.1deg.nc",
    #         gc=gc_gl_ext, out_path="/HOME/huziy/directions_440x260_GL+NENA_0.1deg.rpn")


    # Extended Northeastern North America
    # params_gl_ext = dict(
    #     dx=0.1, dy=0.1,
    #     lon1=180, lat1=0.0,
    #     lon2=-84, lat2=1.0,
    #     iref=135, jref=120,
    #     ni=452, nj=260,
    #     xref=276.0, yref=48.0
    # )
    # gc_gl_ext = GridConfig(**params_gl_ext)
    # convert(nc_path="/RESCUE/skynet3_rech1/huziy/Netbeans Projects/Java/DDM/directions_452x260_GL+NENA_0.1deg.nc",
    #         gc=gc_gl_ext, out_path="/HOME/huziy/directions_452x260_GL+NENA_0.1deg.rpn")

    # CORDEX NA at 0.44 deg resolution
    # convert(nc_path="/RESCUE/skynet3_rech1/huziy/Netbeans Projects/Java/DDM/directions_na_0.44deg_CORDEX.nc",
    #         gc=default_domains.gc_cordex_044)



    # Cordex North America
    # convert(nc_path="/RESCUE/skynet3_rech1/huziy/Netbeans Projects/Java/DDM/directions_na_0.44deg_CORDEX.nc",
    #         gc=default_domains.gc_cordex_na_044)

    # PanArctic 0.5 deg
    convert(nc_path="/RESCUE/skynet3_rech1/huziy/Netbeans Projects/Java/DDM/directions_arctic_0.5deg_Bernardo.nc",
            gc=default_domains.gc_panarctic_05)


    print(default_domains.bc_mh_022)

    if False:
        # convert(nc_path="/RESCUE/skynet3_rech1/huziy/Netbeans Projects/Java/DDM/directions_bc-mh_0.44deg.nc", gc=default_domains.bc_mh_044)
        convert(nc_path="/RESCUE/skynet3_rech1/huziy/Netbeans Projects/Java/DDM/directions_bc-mh_0.22deg.nc", gc=default_domains.bc_mh_022)
        convert(nc_path="/RESCUE/skynet3_rech1/huziy/Netbeans Projects/Java/DDM/directions_bc-mh_0.11deg.nc", gc=default_domains.bc_mh_011)


    print("Hello World")
