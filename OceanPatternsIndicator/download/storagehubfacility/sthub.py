import sys
import time

from download.storagehubfacility import storagehubfacility as sthubf, check_json
from download.interface.idownload import DownloadStrategy
from download.storagehubfacility import dataset_access as db
import json
from download import utils
import os


def wait_to_restart_connection(attempt, output_file):
    print("A network error occurred, download attempt number {} failed, try to download again within 60 seconds..."
          .format(attempt), file=sys.stderr)
    rm(output_file)
    time.sleep(60)


def handle_network_error(output_file, attempt, max_attempt):
    if attempt >= max_attempt:
        raise ConnectionError("ERROR An error occurs while download input file")
    else:
        wait_to_restart_connection(attempt, output_file)


def get_outfile(field, date):
    """
    @param field: cf standard name used to represent a variable
    @param date: the date of output file
    @return: the output filename that depends from variables and date
    """
    from download import utils
    type_file = utils.get_type_file(field)
    date_pattern = date[0:4] + date[5:7]
    return date_pattern + '_mm-INGV--' + type_file + '-MFSs4b3-MED-fv04.00'


def get_filename_from_string_template(string_template):
    from download import utils

    ID_PRODUCT, type_file, YYYYMM, depth_tmp, lonLat_tmp = string_template.split('%')

    field = utils.get_field(type_file)
    time = YYYYMM[0:4] + '-' + YYYYMM[4:6]

    return get_outfile(field[0], time)


def rm(filename):
    if os.path.exists(filename):
        os.remove(filename)


def download_from_sthub(file_to_download, output_file, in_memory, max_attempt, dl_status, return_type):
    item_id = file_to_download[0]
    item_size = file_to_download[2]
    myshfo = sthubf.StorageHubFacility(operation="Download", ItemId=item_id, localFile=output_file, itemSize=item_size)

    attempt = 0
    file_is_downloaded = False
    while attempt < max_attempt and not file_is_downloaded:
        try:
            # in_memory false as default -> the file is written on disk as output_file
            nc_file = myshfo.main(in_memory=in_memory, dl_status=dl_status)     # return None if in_memory == False
            if not in_memory:  # need to load manually the file if in_memory is False
                nc_file = load_file_from_filesystem(output_file, return_type)
            file_is_downloaded = True
        except Exception as e:
            import sys
            print(e, file=sys.stderr)
            attempt += 1
            handle_network_error(output_file, attempt, max_attempt)

    return nc_file


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


class StHub(DownloadStrategy):
    def __init__(self, dataset_id, outdir=None):
        """
        @param outdir: directory where store the output
        """
        self.outdir = utils.init_dl_dir(outdir)
        self.dataset_id = dataset_id
        self.dataset = db.Dataset()
        self.dataset_files = self.retrieve_file_available_on_workspace()  # list of (id, name_file) pairs

    def retrieve_file_available_on_workspace(self, attempt=0, max_attempt=5):
        if attempt < max_attempt:
            try:
                # create ouFile that contains all the file of the selected dataset on sthub
                self.generate_dataset_outfile()
                dataset_outfile = json.load(open('outFile'))
                complete_list = check_json.get_id(dataset_outfile)
            except:
                attempt += 1
                print("A network error occurred,"
                      "storage hub information retrieval attempt {}, try again within 60 seconds..."
                      .format(attempt), file=sys.stderr)
                time.sleep(60)
                complete_list = self.retrieve_file_available_on_workspace(attempt=attempt)
            return complete_list
        else:
            raise ConnectionError("ERROR An error occurs while download input file")

    def generate_dataset_outfile(self):
        print("START ItemChildren")
        dir_id = self.dataset.get_dir_id(self.dataset_id)
        myshfo = sthubf.StorageHubFacility(operation="ItemChildren", ItemId=dir_id)
        myshfo.main()

    def find_files_to_download(self, dataset, fields, working_domain):
        file_types = self.find_file_types_associated_to_dataset(dataset, fields)
        files_to_download = filter_dataset(self.dataset_files, working_domain, file_types)
        if len(files_to_download) == 0:
            raise Exception("No file available to download in the selected domain")
        else:
            return files_to_download

    def find_file_types_associated_to_dataset(self, dataset, field_list):
        file_type_list = list()
        for field in field_list:
            var_name_list = self.dataset.get_var_from_cf_std_name(dataset, field)
            for var_name in var_name_list:
                file_type = self.dataset.get_dataset_field_from_variable(dataset, var_name)
                if file_type not in file_type_list:
                    file_type_list.append(file_type)
        if len(file_type_list) == 0:
            raise Exception("Can't find a file type associated to the dataset: {} for the fields: {}"
                            .format(dataset, ','.join(field_list)))
        return file_type_list

    def get_file_from_sthub_workspace(self, file_to_download, in_memory, rm_file, max_attempt, return_type,
                                      dl_status=False):
        output_file = self.get_output_file(file_to_download)    # path of output file on disk
        if os.path.exists(output_file):
            nc_file = load_file_from_filesystem(output_file, return_type)
        else:
            nc_file = download_from_sthub(file_to_download, output_file, in_memory, max_attempt, dl_status, return_type)

        if rm_file:
            rm(output_file)     # remove the file on disk, keep it only in memory
        return nc_file

    def get_output_file(self, file_to_download):
        filename = file_to_download[1]
        output_file = self.outdir + "/" + filename
        return output_file

    def download(self, dataset, working_domain, fields, in_memory=False, rm_file=True, max_attempt=5,
                 return_type="netCDF4"):
        """
        @param in_memory: if True the function return a netCDF4.Dataset in memory
        @param rm_file: if True the downloaded files will be deleted once they are loaded into memory
        @param dataset: source dataset
        @param working_domain: dict with
            lonLat: not used
            depth: not used
            time: date in string format: [YYYYMM]
        @param fields: cf standard name used to represent a variable
        @return: download in outdir the correct netCDF file/s
        """
        nc_files = list()
        file_to_download_list = self.find_files_to_download(dataset, fields, working_domain)
        for file_to_download in file_to_download_list:
            nc_file = self.get_file_from_sthub_workspace(file_to_download, in_memory, rm_file, max_attempt, return_type)
            nc_files.append(nc_file)

        return nc_files


def filter_dataset(file_list, working_domain, file_types):
    """
    This function filters the input list and return a new list with the file with
    the type of files desired
    @param file_types: pattern that identifies the type of files
    @param working_domain: dict with time information:
            time: date in string format: [YYYYMM]
    @param file_list: list containing (id, file_name) pairs to be filtered
    @return: list that contains only files of desired type
    """

    time = working_domain['time']
    filtered_list = list()
    for file in file_list:
        for file_type in file_types:
            if file_type in file[1]:
                for t in time:
                    if t + '01_m' in file[1]:   # med pattern: YYYYMM01_m*
                        if file not in filtered_list:
                            filtered_list.append(file)
                    elif t + '.nc' in file[1]:  # glo pattern: *_YYYYMM.nc
                        if file not in filtered_list:
                            filtered_list.append(file)
                    elif t in file[1]:
                        if file not in filtered_list:   # wind dataset pattern: *YYYYMM_YYYYMM.nc
                            filtered_list.append(file)
                    break

    return filtered_list
