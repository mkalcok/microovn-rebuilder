import dataclasses
from pathlib import Path
from typing import List, Optional, Set

import yaml


@dataclasses.dataclass(eq=True, frozen=True)
class Target:
    local_rel_path: str
    remote_rel_path: str

    local_base_path: str
    remote_base_path: str = "/root/squashfs-root/"

    service: Optional[str] = None
    pre_exec: Optional[str] = None

    @property
    def local_path(self) -> Path:
        return Path(self.local_base_path, self.local_rel_path)

    @property
    def remote_path(self) -> Path:
        return Path(self.remote_base_path, self.remote_rel_path)


class ConfigException(Exception):
    pass


def parse_config(
    cfg_path: str, local_base_path: str, remote_base_path: str
) -> Set[Target]:
    targets = set()
    try:
        with open(cfg_path, "r") as f:
            yaml_config = yaml.safe_load(f)
    except OSError as exc:
        raise ConfigException(f"Cannot open config file {cfg_path}: {exc}") from exc

    try:
        cfg_targets = yaml_config["targets"]
    except KeyError:
        raise ConfigException(f"No targets found in config file: {cfg_path}")

    if not isinstance(cfg_targets, List):
        raise ConfigException(
            f"'targets' must be non-empty list (config file: {cfg_path})"
        )
    try:
        for target in cfg_targets:
            targets.add(
                Target(
                    local_rel_path=target["local_path"],
                    remote_rel_path=target["remote_path"],
                    local_base_path=local_base_path,
                    remote_base_path=remote_base_path,
                    service=target.get("service", None),
                    pre_exec=target.get("pre_exec", None),
                )
            )
    except KeyError as exc:
        raise ConfigException(
            f"One of the 'targets' in config file '{cfg_path}' is missing key: {exc.args[1]}"
        ) from exc

    if not targets:
        raise ConfigException(f"No targets found in config file: {cfg_path}")

    return targets
