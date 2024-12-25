import argparse
import os
import sys
from typing import Dict, Set

from microovn_rebuilder.ovn import rebuild
from microovn_rebuilder.remote import BaseConnector, ConnectorException, create_connector
from microovn_rebuilder.target import ConfigException, Target, parse_config

NOT_FOUND_TS = float(-1)


def get_file_timestamps(targets: Set[Target]) -> Dict[Target, float]:
    """Retrieve the last modified timestamps of WATCHED_FILES."""
    timestamps = {}
    for target in targets:
        try:
            timestamps[target] = os.path.getmtime(target.local_path)
        except OSError:
            timestamps[target] = NOT_FOUND_TS

    return timestamps


def get_changed_targets(
    initial_ts: Dict[Target, float], current_ts: Dict[Target, float]
) -> Set[Target]:
    need_restart = set()
    for target, ts in current_ts.items():
        if ts == NOT_FOUND_TS:
            continue

        if ts != initial_ts[target]:
            need_restart.add(target)

    return need_restart


def update_targets(targets: Set[Target], connector: BaseConnector) -> None:
    for target in targets:
        connector.update(target)


def watch(
    targets: Set[Target], connector: BaseConnector, ovn_dir: str, jobs: int
) -> None:
    while True:
        try:
            initial_timestamps = get_file_timestamps(targets)
            input("Press 'Enter' to rebuild and deploy OVN. (Ctrl-C for exit)")
            if not rebuild(ovn_dir, jobs):
                continue
            current_timestamps = get_file_timestamps(targets)

            need_restart = get_changed_targets(initial_timestamps, current_timestamps)
            if need_restart:
                update_targets(need_restart, connector)
            else:
                print("[local] No changes in watched files")
        except KeyboardInterrupt:
            print()
            connector.teardown()
            break


def parse_args() -> argparse.Namespace:  # pragma: no cover
    parser = argparse.ArgumentParser(description="Monitor file changes.")
    parser.add_argument("-c", "--config", required=True, help="Path to config file")
    parser.add_argument(
        "-o",
        "--ovn-src",
        type=str,
        help="Path to local OVN source directory. (default: current directory)",
        default="./",
    )
    parser.add_argument(
        "-r",
        "--remote-path",
        type=str,
        help="Path to the unsquashed snap on remote host. (default: /root/squashfs-root/)",
        default="/root/squashfs-root/",
    )
    parser.add_argument(
        "-H",
        "--hosts",
        type=str,
        required=True,
        help="Comma-separated list of remote host to which changes will be synced. For "
        "details on supported connectors and their syntax, please see "
        "documentation. Generally, the format is:"
        "'<connection_type>:<remote_host>'",
    )
    parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=os.cpu_count(),
        help="Number of parallel jobs directly passed to 'make' when building OVN. (defaults to cpu count)",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        targets = parse_config(args.config, args.ovn_src, args.remote_path)
    except ConfigException as exc:
        print(exc)
        sys.exit(1)

    try:
        connector = create_connector(args.hosts)
        connector.check_remote(args.remote_path)
    except ConnectorException as exc:
        print(f"Failed to create connection to remote host: {exc}")
        sys.exit(1)

    watch(targets, connector, args.ovn_src, args.jobs)


if __name__ == "__main__":  # pragma: no cover
    main()
