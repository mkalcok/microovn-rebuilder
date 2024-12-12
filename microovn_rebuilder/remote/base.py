from abc import ABC, abstractmethod
from typing import List

from microovn_rebuilder.target import Target


class ConnectorException(Exception):
    pass


class BaseConnector(ABC):

    def __init__(self, remotes: List[str]) -> None:
        self.remotes = remotes

    @abstractmethod
    def check_remote(self, remote_dst: List[str]) -> None:
        pass

    @abstractmethod
    def update(self, target: Target) -> None:
        pass
