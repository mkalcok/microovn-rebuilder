import argparse
from copy import deepcopy
from unittest.mock import MagicMock, call, mock_open

import pytest

from microovn_rebuilder import cli
from microovn_rebuilder.cli import NOT_FOUND_TS
from microovn_rebuilder.remote import BaseConnector, ConnectorException
from microovn_rebuilder.target import ConfigException


@pytest.mark.parametrize("timestamp", [1, NOT_FOUND_TS])
def test_get_file_timestamps(mocker, timestamp, default_targets):
    if timestamp == NOT_FOUND_TS:
        mocker.patch.object(cli.os.path, "getmtime", side_effect=OSError)
    else:
        mocker.patch.object(cli.os.path, "getmtime", return_value=timestamp)

    target_ts = cli.get_file_timestamps(default_targets)
    for target, ts in target_ts.items():
        assert ts == timestamp


def test_get_changed_targets_no_changes(default_targets):
    old_ts = {target: 1 for target in default_targets}
    new_ts = deepcopy(old_ts)

    changed_targets = cli.get_changed_targets(old_ts, new_ts)

    assert len(changed_targets) == 0


def test_get_changed_targets_with_changes(default_targets):
    old_ts = {target: 1 for target in default_targets}
    new_ts = {target: 2 for target in default_targets}

    changed_targets = cli.get_changed_targets(old_ts, new_ts)
    assert changed_targets == default_targets


def test_get_changed_targets_file_removed(default_targets):
    old_ts = {target: 1 for target in default_targets}
    new_ts = {target: NOT_FOUND_TS for target in default_targets}

    changed_targets = cli.get_changed_targets(old_ts, new_ts)
    assert len(changed_targets) == 0


def test_update_targets(default_targets):
    connector_mock = MagicMock(spec=BaseConnector)
    cli.update_targets(default_targets, connector_mock)
    connector_mock.update.assert_has_calls([call(target) for target in default_targets])


@pytest.mark.parametrize("targets_changed", [True, False])
def test_watch(mocker, default_targets, local_ovn_path, targets_changed):
    initial_ts_1 = MagicMock(spec=set)
    initial_ts_2 = MagicMock(spec=set)
    current_ts_1 = MagicMock(spec=set)
    current_ts_2 = MagicMock(spec=set)

    first_run_ts = [initial_ts_1, current_ts_1]
    second_run_ts = [initial_ts_2, current_ts_2]
    # Since 'watch' is a function with infinite loop, we'll raise KeyboardInterrupt on the third pass
    get_ts_returns = [*first_run_ts, *second_run_ts, KeyboardInterrupt]

    concurrent_build_jobs = 10
    connector = MagicMock(spec=BaseConnector)

    mock_get_file_timestamps = mocker.patch.object(
        cli, "get_file_timestamps", side_effect=get_ts_returns
    )
    mocker.patch("builtins.input")
    mock_rebuild = mocker.patch.object(cli, "rebuild", return_value=True)
    mock_update_targets = mocker.patch.object(cli, "update_targets")
    mock_print = mocker.patch("builtins.print")

    mock_get_changed_targets = mocker.patch.object(cli, "get_changed_targets")
    changed_targets = None
    if targets_changed:
        changed_targets = default_targets
        mock_get_changed_targets.return_value = changed_targets
    else:
        mock_get_changed_targets.return_value = set()

    cli.watch(default_targets, connector, local_ovn_path, concurrent_build_jobs)

    # get_file_timestamps is called two times per loop, we loop twice and on the
    # third run we raise KeyboardInterrupt to break loop.
    mock_get_file_timestamps.assert_has_calls(
        [call(default_targets) for _ in range((2 * 2) + 1)]
    )
    mock_rebuild.assert_has_calls(
        [call(local_ovn_path, concurrent_build_jobs) for _ in range(2)]
    )
    mock_get_changed_targets.assert_has_calls(
        [call(*first_run_ts), call(*second_run_ts)]
    )

    if targets_changed:
        mock_update_targets.assert_has_calls(
            [call(changed_targets, connector) for _ in range(2)]
        )
        mock_print.assert_has_calls([call()])
    else:
        mock_update_targets.assert_not_called()
        print_calls = [call("[local] No changes in watched files") for _ in range(2)]
        print_calls.append(call())
        mock_print.assert_has_calls([call()])


def test_watch_rebuild_failed(mocker, default_targets, local_ovn_path):
    mock_get_file_timestamps = mocker.patch.object(cli, "get_file_timestamps")
    mock_get_changed_targets = mocker.patch.object(cli, "get_changed_targets")
    mock_update_targets = mocker.patch.object(cli, "update_targets")
    mocker.patch("builtins.input")

    # Throwing in KeyboardInterrupt from the second call to break infinite loop in 'watch'
    mock_rebuild = mocker.patch.object(
        cli, "rebuild", side_effect=[False, KeyboardInterrupt]
    )

    concurrent_build_jobs = 10
    connector = MagicMock(spec=BaseConnector)

    cli.watch(default_targets, connector, local_ovn_path, concurrent_build_jobs)

    mock_rebuild.assert_has_calls([call(local_ovn_path, concurrent_build_jobs)])

    # After rebuild returns False, no updates should occur.
    mock_get_changed_targets.assert_not_called()
    mock_update_targets.assert_not_called()


def test_main_parse_config_fail(mocker):
    mock_args = MagicMock(spec=argparse.Namespace)
    mock_args.config = MagicMock()
    mock_args.ovn_src = MagicMock()
    mock_args.remote_path = MagicMock()

    mock_watch = mocker.patch.object(cli, "watch")
    mock_create_connector = mocker.patch.object(cli, "create_connector")
    mock_arg_parse = mocker.patch.object(cli, "parse_args", return_value=mock_args)
    mock_exception = ConfigException()
    mock_parse_config = mocker.patch.object(
        cli, "parse_config", side_effect=mock_exception
    )
    mock_print = mocker.patch("builtins.print")

    with pytest.raises(SystemExit):
        cli.main()

    mock_arg_parse.assert_called_once()
    mock_parse_config.assert_called_with(
        mock_args.config, mock_args.ovn_src, mock_args.remote_path
    )
    mock_print.assert_called_with(mock_exception)

    mock_create_connector.assert_not_called()
    mock_watch.assert_not_called()


def test_main_connector_fail(mocker, default_targets):
    mock_args = MagicMock(spec=argparse.Namespace)
    mock_args.config = MagicMock()
    mock_args.ovn_src = MagicMock()
    mock_args.remote_path = MagicMock()
    mock_args.hosts = MagicMock()
    mock_arg_parse = mocker.patch.object(cli, "parse_args", return_value=mock_args)

    mock_parse_config = mocker.patch.object(
        cli, "parse_config", return_value=default_targets
    )

    mock_exception = ConnectorException()
    mock_connector = MagicMock(spec=BaseConnector)
    mock_connector.check_remote.side_effect = mock_exception
    mock_create_connector = mocker.patch.object(
        cli, "create_connector", return_value=mock_connector
    )

    mock_watch = mocker.patch.object(cli, "watch")
    mock_print = mocker.patch("builtins.print")

    with pytest.raises(SystemExit):
        cli.main()

    mock_arg_parse.assert_called_once()
    mock_parse_config.assert_called_with(
        mock_args.config, mock_args.ovn_src, mock_args.remote_path
    )
    mock_create_connector.assert_called_once_with(mock_args.hosts)
    mock_connector.check_remote.assert_called_once_with(mock_args.remote_path)

    mock_print.assert_called_with(
        f"Failed to create connection to remote host: {mock_exception}"
    )

    mock_watch.assert_not_called()


def test_main_ok(mocker, default_targets):
    mock_args = MagicMock(spec=argparse.Namespace)
    mock_args.config = MagicMock()
    mock_args.ovn_src = MagicMock()
    mock_args.remote_path = MagicMock()
    mock_args.hosts = MagicMock()
    mock_args.jobs = MagicMock()
    mock_arg_parse = mocker.patch.object(cli, "parse_args", return_value=mock_args)

    mock_parse_config = mocker.patch.object(
        cli, "parse_config", return_value=default_targets
    )

    mock_connector = MagicMock(spec=BaseConnector)
    mock_create_connector = mocker.patch.object(
        cli, "create_connector", return_value=mock_connector
    )

    mock_watch = mocker.patch.object(cli, "watch")
    mock_print = mocker.patch("builtins.print")

    cli.main()

    mock_arg_parse.assert_called_once()
    mock_parse_config.assert_called_with(
        mock_args.config, mock_args.ovn_src, mock_args.remote_path
    )
    mock_create_connector.assert_called_once_with(mock_args.hosts)
    mock_connector.check_remote.assert_called_once_with(mock_args.remote_path)

    mock_watch.assert_called_with(
        default_targets, mock_connector, mock_args.ovn_src, mock_args.jobs
    )
