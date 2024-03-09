from download.interface.iinput import InputStrategy


class InputContext:
    """
        The Context defines the interface of interest to clients.
        """

    def __init__(self, strategy: InputStrategy) -> None:
        """
        Usually, the Context accepts a strategy through the constructor, but
        also provides a setter to change it at runtime.
        """

        self._strategy = strategy

    @property
    def strategy(self) -> InputStrategy:
        """
        The Context maintains a reference to one of the Strategy objects. The
        Context does not know the concrete class of a strategy. It should work
        with all interface via the Strategy interface.
        """

        return self._strategy

    @strategy.setter
    def strategy(self, strategy: InputStrategy) -> None:
        """
        Usually, the Context allows replacing a Strategy object at runtime.
        """

        self._strategy = strategy

    def get_wd(self, workingDomain, dataset) -> dict:
        """
        @param workingDomain: dict with spatial/time information:
                lonLat: list of list, the internal list has the format:  [[minLon , maxLon], [minLat , maxLat]]
                depth: depth range in string format: [minDepth, maxDepth]
                time: list of two strings that represent a time range: [YYYY-MM-DDThh:mm:ssZ, YYYY-MM-DDThh:mm:ssZ]
        """
        return self._strategy.get_wd(workingDomain, dataset)