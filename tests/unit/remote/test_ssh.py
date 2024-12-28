from os import stat_result
from unittest.mock import MagicMock, call

import pytest
from paramiko.channel import ChannelFile, ChannelStderrFile
from paramiko.client import SSHClient
from paramiko.sftp_client import SFTPClient
from paramiko.ssh_exception import SSHException

from microovn_rebuilder.remote import ConnectorException, SSHConnector
from microovn_rebuilder.target import Target
from tests.unit.conftest import default_targets


def test_initialize(mocker):
    expected_remotes = {
        "vm1": MagicMock(autospec=SSHClient),
        "root@vm2": MagicMock(autospec=SSHClient),
    }
    mocker.patch(
        "microovn_rebuilder.remote.ssh.SSHClient",
        side_effect=list(expected_remotes.values()),
    )

    connector = SSHConnector(list(expected_remotes.keys()))
    connector.initialize()

    expected_remotes["vm1"].connect.assert_called_once_with(hostname="vm1")
    expected_remotes["root@vm2"].connect.assert_called_once_with(
        hostname="vm2", username="root"
    )
    assert connector.connections == expected_remotes


def test_initialize_fail(mocker):
    mocker.patch("microovn_rebuilder.remote.ssh.SSHClient", side_effect=SSHException())

    connector = SSHConnector(["vm1", "vm2"])
    with pytest.raises(ConnectorException):
        connector.initialize()


def test_update_ssh_err(mocker, ssh_connector, default_targets):
    target = list(default_targets)[0]
    mocker.patch("microovn_rebuilder.remote.ssh.os.stat")

    for connection in ssh_connector.connections.values():
        connection.open_sftp.side_effect = SSHException

    with pytest.raises(ConnectorException):
        ssh_connector.update(target)


def test_update(mocker, ssh_connector, default_targets):
    for target in default_targets:
        file_stats = MagicMock(autospec=stat_result)
        mocker.patch("microovn_rebuilder.remote.ssh.os.stat", return_value=file_stats)

        expected_run_commands = []
        for remote, client in ssh_connector.connections.items():
            if target.service:
                expected_run_commands.append(
                    call(client, remote, f"snap restart {target.service}")
                )
        mock_run_command = mocker.patch.object(ssh_connector, "_run_command")

        mock_sftp_ctx = []
        mock_sftps = []
        for connection in ssh_connector.connections.values():
            sftp = MagicMock(autospec=SFTPClient)
            sftp_ctx = MagicMock(autospec=SFTPClient)
            sftp_ctx.__enter__ = MagicMock(return_value=sftp)

            connection.open_sftp.return_value = sftp_ctx
            mock_sftp_ctx.append(sftp_ctx)
            mock_sftps.append(sftp)

        ssh_connector.update(target)

        for sftp in mock_sftps:
            sftp.remove.assert_called_once_with(str(target.remote_path))
            sftp.put.assert_called_once_with(target.local_path, str(target.remote_path))
            sftp.chmod.assert_called_once_with(
                str(target.remote_path), file_stats.st_mode
            )

        mock_run_command.assert_has_calls(expected_run_commands)


def test_check_remote(mocker, ssh_connector, remote_deployment_path):
    mock_run_command = mocker.patch.object(ssh_connector, "_run_command")

    expected_calls = []
    for remote, client in ssh_connector.connections.items():
        expected_calls.append(call(client, remote, f"test -d {remote_deployment_path}"))

    ssh_connector.check_remote(remote_deployment_path)
    mock_run_command.assert_has_calls(expected_calls)


def test_run_command_rc_zero(ssh_connector):
    remote, client = next(iter(ssh_connector.connections.items()))
    mock_stdout = MagicMock(autospec=ChannelFile)
    mock_stdout.channel.recv_exit_status.return_value = 0
    client.exec_command.return_value = (None, mock_stdout, None)

    ssh_connector._run_command(client, remote, "foo")

    client.exec_command.assert_called_once_with("foo")


def test_run_command_rc_one(ssh_connector):
    remote, client = next(iter(ssh_connector.connections.items()))
    mock_stderr = MagicMock(autospec=ChannelStderrFile)
    mock_stdout = MagicMock(autospec=ChannelFile)
    mock_stdout.channel.recv_exit_status.return_value = 1
    client.exec_command.return_value = (None, mock_stdout, mock_stderr)

    with pytest.raises(ConnectorException):
        ssh_connector._run_command(client, remote, "foo")

    client.exec_command.assert_called_once_with("foo")


def test_run_command_ssh_err(ssh_connector):
    remote, client = next(iter(ssh_connector.connections.items()))
    client.exec_command.side_effect = SSHException()

    with pytest.raises(ConnectorException):
        ssh_connector._run_command(client, remote, "foo")

    client.exec_command.assert_called_once_with("foo")


def test_teardown(ssh_connector):
    assert len(ssh_connector.connections) != 0

    ssh_connector.teardown()

    ssh_clients = [client for client in ssh_connector.connections.values()]
    assert len(ssh_connector.connections) == 0
    for client in ssh_clients:
        client.close.assert_called_once()
