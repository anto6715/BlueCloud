import logging
import time
from OceanPatternsIndicator.utils.data_loader_utils import load_data
from OceanPatternsIndicator.utils.model_train_utils import train_model
from OceanPatternsIndicator.utils.prediction_utils import predict, robustness, quantiles, generate_plots


def get_args():
    """
    Extract arguments from command line

    Returns
    -------
    parse.parse_args(): dict of the arguments

    """
    import argparse

    parse = argparse.ArgumentParser(description="Ocean patterns method")
    parse.add_argument('k', type=int, help="number of clusters K")
    parse.add_argument('file_name', type=str, help='input dataset')
    parse.add_argument('var_name_ds', type=str, help='name of variable in dataset')
    parse.add_argument('var_name_mdl', type=str, help='name of variable in model')

    return parse.parse_args()


def main_fit_predict(args):
    var_name_ds = args['var_name']
    var_name_mdl = args['var_name']
    features_in_ds = {var_name_mdl: var_name_ds}
    k = args['k']
    file_name = './datasets/*.nc'
    arguments_str = f"file_name: {file_name} " \
                    f"var_name_ds: {var_name_ds} " \
                    f"var_name_mdl: {var_name_mdl} "
    logging.info(f"Ocean patterns fit predict method launched with the following arguments:\n {arguments_str}")

    # ---------------- Load data --------------- #
    logging.info("loading the dataset")
    start_time = time.time()
    ds, first_date, coord_dict = load_data(file_name=file_name, var_name_ds=var_name_ds)
    z_dim = coord_dict['depth']
    load_time = time.time() - start_time
    logging.info("load finished in " + str(load_time) + "sec")

    # --------- train model -------------- #
    logging.info("starting computation")
    start_time = time.time()
    m = train_model(k=k, ds=ds, var_name_mdl=var_name_mdl, var_name_ds=var_name_ds, z_dim=z_dim)
    train_time = time.time() - start_time
    logging.info("training finished in " + str(train_time) + "sec")

    # ----------- predict ----------- #
    logging.info("Starting predictions and plots")
    start_time = time.time()
    ds = predict(m=m, ds=ds, var_name_mdl=var_name_mdl, var_name_ds=var_name_ds, z_dim=z_dim)
    ds = robustness(m=m, ds=ds, features_in_ds=features_in_ds, z_dim=z_dim, first_date=first_date)
    ds = quantiles(ds=ds, m=m, var_name_ds=var_name_ds)
    generate_plots(m=m, ds=ds, var_name_ds=var_name_ds, first_date=first_date)
    predict_time = time.time() - start_time
    logging.info("prediction and plots finished in " + str(predict_time) + "sec")
    # save model
    m.to_netcdf('model.nc')
    logging.info("model saved")


if __name__ == '__main__':
    args = get_args()
    main_fit_predict(args)
