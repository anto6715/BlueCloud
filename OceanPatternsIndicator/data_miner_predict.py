import sys
import xarray as xr
import numpy as np
import pyxpcm
from pyxpcm.models import pcm
import Plotter
from Plotter import Plotter
import dask
import dask.array as da


def get_args():
    import argparse

    parse = argparse.ArgumentParser(description="Ocean patterns method")
    parse.add_argument('model', type=str, help="input model")
    parse.add_argument('file_name', type=str, help='input dataset')

    return parse.parse_args()


def load_data(file_name):
    ds = xr.open_dataset('../datasets/' + file_name)
    ds['depth'] = -np.abs(ds['depth'].values)
    ds.depth.attrs['axis'] = 'Z'
    return ds


def load_model(model_path):
    m = pyxpcm.load_netcdf(model_path)
    return m


def predict(m, ds, var_name_mdl, var_name_ds, z_dim):
    features_in_ds = {var_name_mdl: var_name_ds}
    m.predict(ds, features=features_in_ds, dim=z_dim, inplace=True)
    m.predict_proba(ds, features=features_in_ds, dim=z_dim, inplace=True)
    ds = ds.pyxpcm.quantile(m, q=[0.05, 0.5, 0.95], of=var_name_ds, outname=var_name_ds + '_Q', keep_attrs=True,
                            inplace=True)
    ds.pyxpcm.robustness(m, inplace=True)
    ds.pyxpcm.robustness_digit(m, inplace=True)
    return ds


def generate_plots(m, ds, var_name_ds):
    file_ext = 'data_miner'
    P = Plotter(ds, m)
    # plot profiles by class
    P.vertical_structure(q_variable=var_name_ds + '_Q', sharey=True, xlabel='Temperature (°C)')
    P.save_BlueCloud('dataminer_out/vertical_struc.png')
    # plot profiles by quantile
    P.vertical_structure_comp(q_variable=var_name_ds + '_Q', plot_q='all', xlabel='Temperature (°C)', ylim=[-1000, 0])
    P.save_BlueCloud('dataminer_out/vertical_struc_comp.png')
    # spacial distribution
    P.spatial_distribution(time_slice='most_freq_label')
    P.save_BlueCloud('dataminer_out/spatial_distr_freq.png')
    # robustness
    # P.plot_robustness(time_slice="2018-08") # can't use it because it requires a time_slice
    # P.save_BlueCloud('dataminer_out/robustness_EX.png')
    # pie chart of the classes distribution
    P.pie_classes()
    P.save_BlueCloud('dataminer_out/pie_chart.png')
    # temporal distribution (monthly)
    P.temporal_distribution(time_bins='month')
    P.save_BlueCloud('dataminer_out/temporal_distr_months.png')
    # temporal distribution (seasonally)
    P.temporal_distribution(time_bins='season')
    P.save_BlueCloud('dataminer_out/temporal_distr_season.png')
    # save data
    ds.to_netcdf('dataminer_out/predicted_dataset.nc', format='NETCDF4')


def main():
    z_dim = 'depth'
    var_name_ds = 'thetao'  # name in dataset
    var_name_mdl = 'temperature'  # name in model
    args = get_args()
    model_path = args.model
    file_name = args.file_name
    ds = load_data(file_name)
    m = load_model(model_path=model_path)
    ds = predict(m=m, ds=ds, var_name_mdl=var_name_mdl, var_name_ds=var_name_ds, z_dim=z_dim)
    generate_plots(m=m, ds=ds, var_name_ds=var_name_ds)


if __name__ == '__main__':
    main()
