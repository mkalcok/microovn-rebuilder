from pathlib import Path
from typing import Set

import pytest
import microovn_rebuilder
from microovn_rebuilder.target import Target, parse_config


@pytest.fixture(scope="session")
def config_file() -> str:
    return str(Path(microovn_rebuilder.__file__).parent.parent / "default_config.yaml")

@pytest.fixture(scope="session")
def local_ovn_path() -> str:
    return "/tmp/foo/ovn"

@pytest.fixture(scope="session")
def remote_deployment_path() -> str:
    return "/tmp/foo/squashfs-root"

@pytest.fixture(scope="session")
def default_targets(config_file: str, local_ovn_path: str, remote_deployment_path: str) -> Set[Target]:
    return parse_config(config_file, local_ovn_path, remote_deployment_path)
