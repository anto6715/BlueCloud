import os
import json
import sys

from download.contexts.input_ctx import InputContext
from download.contexts.download_ctx import DownloadContext
from download.wekeo import in_hda, hda
from download.storagehubfacility import in_sthub, sthub

workingDomain_attrs = ['lonLat', 'time']
workingDomain_attrs_optional = ['depth']


def get_infrastructure(dataset):
    actual_dir = os.path.dirname(__file__)
    with open(actual_dir + '/config/dataset_infrastructures.json') as json_file:
        dataset_infrastructures = json.load(json_file)
    if dataset in dataset_infrastructures:
        infrastructure = dataset_infrastructures[dataset]['infrastructure']
    else:
        raise Exception("Can't find dataset: " + dataset + ' in catalogue')

    return infrastructure


class Daccess:
    def __init__(self, dataset: str, fields: list, output_dir=None, hda_key="", time_freq="m"):
        """
        @param dataset: source dataset
        @param fields: cf standard name used to represent a variable
        @param output_dir: output directory
        @param hda_key: key to access to hda service, leave "" if you want to use bluecloud proxy
        @param return_type: if netCDF4 return a netCDF4.Dataset, if str return the output filename
        """
        self.fields = fields
        self.outDir = output_dir
        self.hdaKey = hda_key

        # select the right strategy in according to the selected dataset
        self.dataset = dataset
        self._infrastructure = get_infrastructure(dataset)

        # select the right input/download interface
        if self._infrastructure == 'WEKEO':
            print("Downloading from MEDSEA_MULTIYEAR_PHY_006_004")
            self.input_ctx = InputContext(in_hda.InHDA())
            self.download_ctx = DownloadContext(hda.HDA(self.hdaKey, self.outDir))
        elif self._infrastructure == 'STHUB':
            print("Downloading from Storage Hub Facility")
            self.input_ctx = InputContext(in_sthub.InStHub(time_freq=time_freq))
            self.download_ctx = DownloadContext(sthub.StHub(self.dataset, self.outDir))
        else:
            raise Exception('Infrastructure: ' + self._infrastructure + ' not supported')

    def download(self, daccess_working_domain: dict, **kwargs):
        """
        @param daccess_working_domain: dict with spatial/time information:
                lonLat: list of list, the internal list has the format:  [minLon , maxLon, minLat , maxLat]
                depth: depth range in string format: [minDepth, maxDepth]
                time: list of two strings that represent a time range: [YYYY-MM-DDThh:mm:ssZ, YYYY-MM-DDThh:mm:ssZ]
        @return: store netCDF file in download directory
            """

        wd_validation(daccess_working_domain)
        # fix the working_domain format in according to the selected download strategy
        working_domain = self.input_ctx.get_wd(daccess_working_domain, self.dataset)
        return self.download_ctx.download(self.dataset, working_domain, self.fields, **kwargs)


def wd_validation(workingDomain):
    """
    This function check if workingDomain is valid
    @param workingDomain: dict with spatial/time information:
                lonLat: list of list, the internal list has the format:  [minLon , maxLon, minLat , maxLat]
                depth: depth range in string format: [minDepth, maxDepth]
                time: list of two strings that represent a time range: [YYYY-MM-DDThh:mm:ssZ, YYYY-MM-DDThh:mm:ssZ]
    @return: True if workingDomain is valid
    """
    for wd_attr in workingDomain_attrs:
        if wd_attr not in workingDomain:
            raise Exception("Can't find " + wd_attr + ' in workingDomain: ' + str(workingDomain))
    for wd_attr_opt in workingDomain_attrs_optional:
        if wd_attr_opt not in workingDomain:
            print("WARNING: ", wd_attr_opt, ' not found')

    # lonLat check
    lonLat = workingDomain['lonLat']
    if len(lonLat) != 4:
        raise Exception("Wrong size for lonLat, please check it: " + str(lonLat))
    elif not float_int_check(lonLat):
        raise Exception("Type error in lonLat")

    # depth check
    if 'depth' in workingDomain:
        depth = workingDomain['depth']
        if len(depth) != 2:
            raise Exception("Wrong size for depth, please check it: " + str(depth))
        elif not float_int_check(depth):
            raise Exception("Type error in depth")

    # time check
    time = workingDomain['time']
    # if len(time) != 2:
    #     raise Exception("Wrong size for lonLat, please check it: " + str(time))


def float_int_check(elements):
    for x in elements:
        if not isinstance(x, float) and not isinstance(x, int):
            print("ERROR found no float or int type: ", x)
            print("ERROR lonLat value must be float or int, please check it: ", elements)
            return False
    return True
