import json
import time

from download import daccess
import sys
import os
import logging
import traceback
from DM_BIC_method import main_bic_computation
from DM_FIT_PRED_method import main_fit_predict
from DM_FIT_method import main_model_fit
from DM_predict_method import main_predict

import datetime
from tools import json_builder
from tools import time_utils
from dateutil.tz import tzutc


def get_args():
    """
    Extract arguments from command line

    Returns
    -------
    parse.parse_args(): dict of the arguments

    """
    import argparse

    parse = argparse.ArgumentParser(description="Ocean patterns method")
    parse.add_argument('parameters_string', type=str, help="string with all param")
    return parse.parse_args()


def get_time_range(start_date, end_date):
    """
    format date for wekeo API request
    Parameters
    ----------
    start_date : string as follow: yyyy-mm
    end_date : string as follow: yyyy-mm

    Returns
    -------
    date: list of string as follow: ['yyyy-mm-ddT00:00:00', 'yyyy-mm-ddT00:00:00']
    """
    return [f"{start_date[:4]}-{start_date[5:]}-01T00:00:00", f"{end_date[:4]}-{end_date[5:]}-28T00:00:00"]


def download_data(param):
    """
    download dataset using wekeo harmonized data api (HDA)
    Parameters
    ----------
    param : dictionary as follow:
    {
        'id_output_type': 'FIT_PRED',
        'id_field': 'sea_water_potential_temperature',
        'k': 6,
        'working_domain': {
            'box': [ [lon_min, lat_min, lon_max, lat_max ] ], #list of boxes of same format as wekeo API
            'd': [[10, 300]]
            },
        'start_time': '2018-01',
        'end_time': '2018-12',
        'data_source': 'MEDSEA_MULTIYEAR_PHY_006_004'
    }
    """
    # ------------ parameter declaration ------------ #
    dataset = param['data_source'][0]   # data_source is a list of str

    fields = [param['id_field']]

    # ------------ file download ------------ #
    dcs = daccess.Daccess(dataset, fields)
    time_range_list = time_utils.get_time_range_wd(param['start_time'], param['end_time'])
    daccess_working_domain = dict()
    daccess_working_domain['depth'] = param['working_domain']['depth_layers'][0].copy()
    daccess_working_domain['lonLat'] = param['working_domain']['box'][0].copy()
    for time_range in time_range_list:
        daccess_working_domain['time'] = time_range
        logging.info(daccess_working_domain)
        dcs.download(daccess_working_domain, rm_file=False)


def get_var_name(source, cf_std_name):
    """
    get var name in dataset using the standard name and the dataset
    Parameters
    ----------
    source : string, source dataset
    cf_std_name : cf standard name of the variable

    Returns
    -------
    string: name of the variable in dataset
    """
    actual_dir = os.path.dirname(__file__)
    with open('./download/config/dataset_infrastructures.json') as json_infra:
        infra = json.load(json_infra)
        if infra[source]['infrastructure'] == "WEKEO" :
            config_path = './download/config/wekeo_dataset.json'
        elif infra[source]['infrastructure'] == "STHUB" :
            config_path = './download/config/sthub_dataset.json'

    with open(config_path) as json_file:
        data = json.load(json_file)
    return data[source]['cf-standard-name_variable'][cf_std_name][0]


def main():
    # noinspection PyArgumentList
    logging.basicConfig(
        format='[%(levelname)s] %(asctime)s %(message)s',
        datefmt='%m/%d/%Y %I:%M:%S %p',
        level=logging.INFO,
        handlers=[
            logging.FileHandler("OceanPatterns.log"),
            logging.StreamHandler()
        ]
    )
    exec_log = json_builder.get_exec_log()
    main_start_time = time.time()
    args = get_args()
    param = args.parameters_string.replace("\'", "\"")
    param_dict = json.loads(param)
    logging.info(f"Ocean patterns launched with the following arguments:\n {param_dict}")
    try:
        start_time = time.time()
        download_data(param_dict)
        download_time = time.time() - start_time
        logging.info("download finished in " + str(download_time) + "sec")

    except Exception as e:
        logging.error(e)
        err_log = json_builder.LogError(-1, str(e))
        error_exit(err_log, exec_log)
    try:
        param_dict['var_name'] = get_var_name(param_dict['data_source'][0], param_dict['id_field'])
        param_dict['file'] = './indir/*.nc'
        if param_dict['id_output_type'] == "BIC":
            logging.info("launching BIC")
            main_bic_computation(param_dict)
        elif param_dict['id_output_type'] == "FIT":
            logging.info("launching fit")
            main_model_fit(param_dict)
        elif param_dict['id_output_type'] == "PRED":
            logging.info("launching pred")
            main_predict(param_dict)
        elif param_dict['id_output_type'] == "FIT_PRED":
            logging.info("launching fit-predict")
            main_fit_predict(param_dict)
    except Exception as e:
        logging.error("".join(traceback.TracebackException.from_exception(e).format()))
        err_log = json_builder.LogError(-2, str(e))
        error_exit(err_log, exec_log)

    # ----------- create all outputs if doesn't exist --------------- #
    list_outputs = ['output.json', 'bic.png', 'vertical_struct.png', 'vertical_struct_comp.png', 'spatial_dist_freq.png',
                    'robustness.png', 'pie_chart.png', 'temporal_dist_months.png', 'temporal_dist_season.png',
                    'predicted_dataset.nc', 'model.nc']
    for file in list_outputs:
        if not os.path.exists(file):
            open(file, 'w').close()

    logging.info(f"execution finished in {time.time() - main_start_time}")
    # Save info in json file
    with open("OceanPatterns.log") as logs:
        for line in logs.readlines():
            exec_log.add_message(line)
    os.remove("OceanPatterns.log")
    err_log = json_builder.LogError(0, "Execution Done")
    end_time = get_iso_timestamp()
    json_builder.write_json(error=err_log.__dict__,
                            exec_info=exec_log.__dict__['messages'],
                            end_time=end_time)


def error_exit(err_log, exec_log):
    """
    This function is called if there's an error occurs, it write in log_err the code error with
    a relative message, then copy some mock files in order to avoid bluecloud to terminate with error
    """
    list_outputs = ['output.json', 'bic.png', 'vertical_struct.png', 'vertical_struct_comp.png',
                    'spatial_dist_freq.png',
                    'robustness.png', 'pie_chart.png', 'temporal_dist_months.png', 'temporal_dist_season.png',
                    'predicted_dataset.nc', 'model.nc']
    for file in list_outputs:
        if not os.path.exists(file):
            open(file, 'w').close()
    with open("OceanPatterns.log") as logs:
        for line in logs.readlines():
            exec_log.add_message(line)
    os.remove("OceanPatterns.log")
    end_time = get_iso_timestamp()
    json_builder.write_json(error=err_log.__dict__,
                            exec_info=exec_log.__dict__['messages'],
                            end_time=end_time)
    exit(0)


def get_iso_timestamp():
    isots = datetime.datetime.now(tz=tzutc()).replace(microsecond=0).isoformat()
    return isots


if __name__ == '__main__':
    main()
