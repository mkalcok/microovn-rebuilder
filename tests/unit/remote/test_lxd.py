import subprocess
from unittest import mock
from unittest.mock import MagicMock, call

import pytest

from microovn_rebuilder.remote import ConnectorException, lxd


def test_update(mocker, lxd_connector, default_targets):
    target = list(default_targets)[0]
    mock_run_result = MagicMock(spec=subprocess.CompletedProcess)
    mock_run_cmd = mocker.patch.object(
        lxd_connector, "_run_command", return_value=mock_run_result
    )
    mock_check_cmd = mocker.patch.object(lxd_connector, "_check_cmd_result")

    expected_run_calls = []
    expected_check_calls = []
    for remote in lxd_connector.remotes:
        expected_run_calls.append(
            call("lxc", "file", "delete", f"{remote}{target.remote_path}")
        )
        expected_check_calls.append(
            call(mock_run_result, f"[{remote}] Failed to remove remote file")
        )

        expected_run_calls.append(
            call(
                "lxc", "file", "push", target.local_path, f"{remote}{target.remote_path}"
            )
        )
        expected_check_calls.append(
            call(mock_run_result, f"[{remote}] Failed to upload file")
        )

        expected_run_calls.append(
            call("lxc", "exec", remote, "snap", "restart", target.service)
        )
        expected_check_calls.append(
            call(mock_run_result, f"[{remote}] Failed to restart service")
        )

    lxd_connector.update(target)

    mock_run_cmd.assert_has_calls(expected_run_calls)
    mock_check_cmd.assert_has_calls(expected_check_calls)


def test_check_remote(mocker, lxd_connector, remote_deployment_path):
    mock_run_result = MagicMock(spec=subprocess.CompletedProcess)
    mock_run_command = mocker.patch.object(
        lxd_connector, "_run_command", return_value=mock_run_result
    )
    mock_check_cmd_result = mocker.patch.object(lxd_connector, "_check_cmd_result")

    expected_run_calls = []
    expected_check_calls = []
    for remote in lxd_connector.remotes:
        expected_run_calls.append(
            call("lxc", "exec", remote, "--", "test", "-d", remote_deployment_path)
        )
        expected_check_calls.append(
            call(
                mock_run_result,
                f"[{remote}] Remote directory '{remote_deployment_path}' does not exist on LXC instance {remote}",
            )
        )

    lxd_connector.check_remote(remote_deployment_path)

    mock_run_command.assert_has_calls(expected_run_calls)
    mock_check_cmd_result.assert_has_calls(expected_check_calls)


def test_run_command(mocker, lxd_connector):
    mock_run = mocker.patch.object(lxd.subprocess, "run")
    cmd = ["/bin/foo", "bar"]
    lxd_connector._run_command(*cmd)

    mock_run.assert_called_once_with(tuple(cmd), capture_output=True)


def test_check_cmd_result_no_error(lxd_connector):
    result = MagicMock(autospec=subprocess.CompletedProcess)
    result.returncode = 0

    assert lxd_connector._check_cmd_result(result, "extra message") is None


def test_check_cmd_result_error(lxd_connector):
    result = MagicMock(autospec=subprocess.CompletedProcess)
    result.returncode = 1

    with pytest.raises(ConnectorException) as exc:
        extra_msg = "error details foo"
        lxd_connector._check_cmd_result(result, extra_msg)

    assert extra_msg in str(exc.value)
