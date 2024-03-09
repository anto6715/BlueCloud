from abc import ABC, abstractmethod


class DownloadStrategy(ABC):
    """
    The Strategy interface declares operations common to all supported versions
    of some algorithm.

    The Context uses this interface to call the algorithm defined by Concrete Strategies.
    """

    @abstractmethod
    def download(self, dataset, working_domain, fields,
                 in_memory=False, rm_file=False, max_attempt=5, return_type="netCDF4"):
        """
        @param dataset: source dataset
        @param working_domain: dict with spatial/time information, each strategy defines its own format
        @param fields: field/s desired (is recommended to use cf_standard_name)
        @param in_memory: if True, try to download the file directly in memory -> it's not fully supported
        @param rm_file: if True, remove file from disk after load it in memory
        @param max_attempt: maximum number of download attempt in case of errors
        @param return_type: if netCDF4 return a netCDF4.Dataset, if str return the output filename
                            if is str, please disable rm_file and in_memory
        """
        pass
