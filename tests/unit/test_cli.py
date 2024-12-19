from copy import deepcopy
from unittest.mock import MagicMock, call

import pytest

from microovn_rebuilder.cli import NOT_FOUND_TS
from microovn_rebuilder.remote import BaseConnector
from microovn_rebuilder import cli

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

def test_watch(mocker, default_targets):
    initial_ts_1 = MagicMock(spec=set)
    initial_ts_2 = MagicMock(spec=set)
    current_ts_1 = MagicMock(spec=set)
    current_ts_2 = MagicMock(spec=set)
    get_ts_returns = [initial_ts_1, current_ts_1, initial_ts_2, current_ts_2]

    concurrent_build_jobs = 10

    mock_get_file_timestamps = mocker.patch.object(cli, "get_file_timestamps", side_effect=get_ts_returns)
    mock_input = mocker.patch("builtins.input")
    mock_rebuild = mocker.patch.object(cli, "rebuild")
    mock_get_changed_targets = mocker.patch.object(cli, "get_changed_targets")
    