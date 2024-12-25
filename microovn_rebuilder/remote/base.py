from abc import ABC, abstractmethod
from typing import List

from microovn_rebuilder.target import Target


class ConnectorException(Exception):
    pass


class BaseConnector(ABC):

    def __init__(self, remotes: List[str]) -> None:
        self.remotes = remotes

    @abstractmethod
    def initialize(self) -> None:
        pass  # pragma: no cover

    @abstractmethod
    def teardown(self) -> None:
        pass  # pragma: no cover

    @abstractmethod
    def check_remote(self, remote_dst: str) -> None:
        pass  # pragma: no cover

    @abstractmethod
    def update(self, target: Target) -> None:
        pass  # pragma: no cover
