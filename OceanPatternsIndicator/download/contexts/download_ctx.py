from download.interface.idownload import DownloadStrategy


class DownloadContext:
    """
        The Context defines the interface of interest to clients.
        """

    def __init__(self, strategy: DownloadStrategy) -> None:
        """
        Usually, the Context accepts a strategy through the constructor, but
        also provides a setter to change it at runtime.
        """

        self._strategy = strategy

    @property
    def strategy(self) -> DownloadStrategy:
        """
        The Context maintains a reference to one of the Strategy objects. The
        Context does not know the concrete class of a strategy. It should work
        with all interface via the Strategy interface.
        """

        return self._strategy

    @strategy.setter
    def strategy(self, strategy: DownloadStrategy) -> None:
        """
        Usually, the Context allows replacing a Strategy object at runtime.
        """

        self._strategy = strategy

    def download(self, *args, **kwargs):
        return self._strategy.download(*args, **kwargs)
