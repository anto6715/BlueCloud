from abc import ABC, abstractmethod


class InputStrategy(ABC):
    """
    The Strategy interface declares operations common to all supported versions
    of some algorithm.

    The Context uses this interface to call the algorithm defined by Concrete Strategies.
    """

    @abstractmethod
    def get_wd(self, workingDomain, dataset):
        """
        @param
        @param workingDomain: dict with spatial/time information:
                lonLat: list of list, the internal list has the format:  [[minLon , maxLon], [minLat , maxLat]]
                depth: depth range in string format: [minDepth, maxDepth]
                time: list of two strings that represent a time range: [YYYY-MM-DDThh:mm:ssZ, YYYY-MM-DDThh:mm:ssZ]
        """
        pass