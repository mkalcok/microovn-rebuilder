import os
from typing import Dict, List

from paramiko import SSHClient, SSHException

from microovn_rebuilder.remote.base import BaseConnector, ConnectorException
from microovn_rebuilder.target import Target


class SSHConnector(BaseConnector):
    def __init__(self, remotes: List[str]) -> None:
        super().__init__(remotes=remotes)

        self.connections: Dict[str, SSHClient] = {}

    def initialize(self) -> None:
        for remote in self.remotes:
            username, found, host = remote.partition("@")
            try:
                ssh = SSHClient()
                ssh.load_system_host_keys()
                if found:
                    ssh.connect(hostname=host, username=username)
                else:
                    ssh.connect(hostname=remote)
                self.connections[remote] = ssh
            except SSHException as exc:
                raise ConnectorException(
                    f"Failed to connect to {remote}: {exc}"
                ) from exc

    def update(self, target: Target) -> None:
        for remote, ssh in self.connections.items():
            try:
                with ssh.open_sftp() as sftp:
                    local_stat = os.stat(str(target.local_path))
                    print(
                        f"{os.linesep}[{remote}] Removing remote file {target.remote_path}"
                    )
                    sftp.remove(str(target.remote_path))

                    print(
                        f"[{remote}] Uploading file {target.local_path} to {target.remote_path}"
                    )
                    sftp.put(target.local_path, str(target.remote_path))
                    sftp.chmod(str(target.remote_path), local_stat.st_mode)
                if target.service:
                    print(f"[{remote}] Restarting {target.service}")
                    self._run_command(ssh, remote, f"snap restart {target.service}")
            except SSHException as exc:
                raise ConnectorException(
                    f"[{remote}] Failed to upload file: {exc}"
                ) from exc

    def check_remote(self, remote_dst: str) -> None:
        for remote, ssh in self.connections.items():
            self._run_command(ssh, remote, f"test -d {remote_dst}")

    @staticmethod
    def _run_command(ssh: SSHClient, remote: str, command: str) -> None:
        try:
            _, stdout, stderr = ssh.exec_command(command)
            ret_code = stdout.channel.recv_exit_status()
            if ret_code != 0:
                error = stderr.read().decode("utf-8")
                raise ConnectorException(
                    f"[{remote}] Failed to execute command: {error}]"
                )
        except SSHException as exc:
            raise ConnectorException(
                f"[{remote}] Failed to execute command: {exc}"
            ) from exc

    def teardown(self) -> None:
        for host, ssh in self.connections.items():
            ssh.close()
        self.connections.clear()
