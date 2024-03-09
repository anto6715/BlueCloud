import warnings
import os
from download.wekeo import functions as hdaf, dataset_access as db
from download.interface.idownload import DownloadStrategy
import time
from download import utils
import netCDF4
import sys

warnings.filterwarnings('ignore')


def rm(filename):
    if os.path.exists(filename):
        os.remove(filename)


def get_outfile(field, date):
    """
    @param field: field desired
    @param date: the date of output file
    @return: the output filename that depends from variables and date
    """
    from download import utils
    type_file = utils.get_type_file(field)
    date_pattern = date[0:4] + date[5:7]
    return date_pattern + '_mm-HDA--' + type_file + '-Mfs-MED_re'


def get_filename_from_string_template(string_template):
    from download import utils

    ID_PRODUCT, type_file, YYYYMM, depth_tmp, lonLat_tmp = string_template.split('%')

    field = utils.get_field(type_file)
    time = YYYYMM[0:4] + '-' + YYYYMM[4:6]

    return get_outfile(field[0], time)


def load_file_from_filesystem(output_file, return_type):
    import netCDF4

    if not os.path.exists(output_file):
        raise Exception("ERROR Can't load {}: it doesn't exists on filesystem".format(output_file))

    if return_type == "netCDF4":  # if downloaded previously and rm_file == False
        nc_file = netCDF4.Dataset(output_file, mode='r')
    elif return_type == "str":
        nc_file = output_file
    else:
        raise Exception("Return type '{}' unknown".format(return_type))
    return nc_file


class HDA(DownloadStrategy):
    def __init__(self, api_key: str, outdir=None):
        """
        @param outdir: directory where store the output
        @param api_key: key to access to WeKeo API
        """
        self.dataset = db.Dataset()
        # api_key = generate_api_key(user_name, password)
        if len(api_key) == 0:
            self.bluecoud_proxy = True
            # raise Exception("API key not valid")
        else:
            self.bluecoud_proxy = False
        self.api_key = api_key
        print('Your API key is: ' + self.api_key)
        self.outdir = utils.init_dl_dir(outdir)

        ##### hda_init initialization #####
        self.hdaInit = dict()
        self.hdaInit['dataset_id'] = None
        self.hdaInit['download_dir_path'] = None
        self.hda = None

        ##### hda_token initialization #####
        self.accessToken = dict()
        self.accessToken['time'] = None

    def accept_term_cond(self):
        if self.hda is None:
            raise Exception("Can't accept term and conditions without hda init")
        if 'isTandCAccepted' not in self.hda:
            self.hda = hdaf.acceptTandC(self.hda)
        else:
            print("Terms and Conditions already accepted")

    def get_token(self):
        if self.hda is None:
            raise Exception("Can't request token without hda init")

        # if self.hda has just been initialized
        if 'access_token' not in self.hda:
            self.hda = hdaf.get_access_token(self.hda, self.bluecoud_proxy)
            self.accessToken['time'] = time.time()
        # if self.hda has just initialized check is validity
        elif self.accessToken['time'] is not None:
            time_now = time.time()
            # token is valid for an hour, check if it's still valid
            if time_now - self.accessToken['time'] > 3600:
                self.hda = hdaf.get_access_token(self.hda)  # request a new valid token
                self.accessToken['time'] = time.time()
            else:
                print('Token still valid')

    def hda_init(self, dataset_id, download_dir_path):
        # With `dataset_id`, `api_key` and `download_dir_path`,
        # you can initialise the dictionary with the function [init](./hda_api_functions.ipynb#init).
        if dataset_id == self.hdaInit['dataset_id'] and download_dir_path == self.hdaInit['download_dir_path']:
            print("Dataset with id:", dataset_id, "already initialized")
            pass  # already initialized
        else:
            self.hdaInit['dataset_id'] = dataset_id
            self.hdaInit['download_dir_path'] = download_dir_path
            self.hda = hdaf.init(dataset_id, self.api_key, download_dir_path)

    def download(self, dataset, working_domain, fields, in_memory=False, rm_file=True, max_attempt=5,
                 return_type="netCDF4"):
        """
        @param in_memory: if True the function return a netCDF4.Dataset in memory.
            NOTE: if select True, the file will be not masked
        @param rm_file: if True the downloaded files will be deleted once they are loaded into memory
        @param dataset: source dataset
        @param working_domain: dict with
            lonLat: list of float with the template: [minLon, minLat, maxLon, maxLat]
            depth: depth range in string format: [minDepth, maxDepth]
            time: time range in string iso format: [YYYY-MM-DDThh:mm:ssZ, YYYY-MM-DDThh:mm:ssZ]
        @param fields: cf standard name used to represent a variable
        @return: download in outdir the correct netCDF file/s or return a netCDF4 in memory
        """
        time = working_domain['time']
        # pair list: first element is the dataset type, second element is the variable to download from dataset

        map_dataset_with_variables_and_outfile = self.extract_map_dataset_with_var_and_outfile(dataset, fields, time)

        nc_files = list()
        for dataset_field, variables_outfile in map_dataset_with_variables_and_outfile.items():
            nc_file = self.get_file_from_hda(dataset, dataset_field, variables_outfile, in_memory, rm_file,
                                             max_attempt, working_domain, return_type)
            nc_files.append(nc_file)

        # nc_file is useful when call download using string_template, in this case you need
        # to know the path and the name of the single file that will be downloaded
        return nc_files

    def extract_map_dataset_with_var_and_outfile(self, dataset, fields, time):
        map_dataset_with_variables_and_outfile = dict()
        for field in fields:
            field_var = self.dataset.get_var_from_cf_std_name(dataset, field)
            for var in field_var:
                dataset_field = self.dataset.get_dataset_field_from_variable(dataset, var)
                if dataset_field not in map_dataset_with_variables_and_outfile:
                    map_dataset_with_variables_and_outfile[dataset_field] = dict()
                    map_dataset_with_variables_and_outfile[dataset_field]['variables'] = list()
                    map_dataset_with_variables_and_outfile[dataset_field]['outfile'] = list()
                map_dataset_with_variables_and_outfile[dataset_field]['variables'].append(var)
                outfile = get_outfile(field, time[0])
                if outfile not in map_dataset_with_variables_and_outfile[dataset_field]['outfile']:
                    if len(map_dataset_with_variables_and_outfile[dataset_field]['outfile']) > 1:
                        raise Exception("Can't associate more than 1 outfile to dataset field: " + dataset_field)
                    else:
                        map_dataset_with_variables_and_outfile[dataset_field]['outfile'].append(outfile)
        return map_dataset_with_variables_and_outfile

    def get_file_from_hda(self, dataset, dataset_field, variables_outfile, in_memory, rm_file, max_attempt,
                          working_domain, return_type):
        lonLat = working_domain['lonLat']
        depth = working_domain['depth']
        time = working_domain['time']
        outfile = variables_outfile['outfile'][0]

        output_file = self.outdir + '/' + outfile + '.nc'
        if os.path.exists(output_file):
            nc_file = load_file_from_filesystem(output_file, return_type)
        else:
            variables_to_download = variables_outfile['variables']
            dataset_id = self.dataset.get_dataset_id(dataset, dataset_field)
            data_json_request = self.dataset.get_data(dataset, dataset_field, variables_to_download, lonLat, depth,
                                                      time)
            nc_file = self.download_from_hda(dataset_id, data_json_request, output_file, in_memory, max_attempt,
                                             return_type)
        if rm_file:
            rm(output_file)

        return nc_file

    def download_from_hda(self, dataset_id, data, output_file, in_memory, max_attempt, return_type):
        attempt = 0
        file_is_downloaded = False
        nc_file = None
        while attempt < max_attempt and not file_is_downloaded:

            # Once initialised, you can request an access token with the function
            try:
                self.hda_init(dataset_id, self.outdir)
                self.get_token()
                # You might need to accept the Terms and Conditions
                self.accept_term_cond()

                # launch your data request and your request is assigned a `job ID`
                hda_dict = hdaf.get_job_id(self.hda, data)

                # The next step is to gather a list of file names available, based on your assigned `job ID`
                hda_dict = hdaf.get_results_list(hda_dict)

                # The next step is to create an `order ID` for each file name to be downloaded
                hda_dict = hdaf.get_order_ids(hda_dict)

                hdaf.download_data(hda_dict, user_filename=output_file, in_memory=in_memory,
                                   dl_status=False)
                nc_file = load_file_from_filesystem(output_file, return_type)
                file_is_downloaded = True
            except Exception as e:
                import sys
                print(e, file=sys.stderr)
                attempt += 1
                handle_network_error(output_file, attempt, max_attempt)
        if nc_file is None:
            raise Exception("ERROR an unknown error happened when try to download: " + output_file)
        return nc_file


def handle_network_error(output_file, attempt, max_attempt):
    if attempt >= max_attempt:
        raise ConnectionError("ERROR An error occurs while download input file")
    else:
        wait_to_restart_connection(attempt, output_file)


def wait_to_restart_connection(attempt, output_file):
    print("A network error occurred, download attempt number {} failed, try to download again within 60 seconds..."
          .format(attempt), file=sys.stderr)
    rm(output_file)
    time.sleep(60)
