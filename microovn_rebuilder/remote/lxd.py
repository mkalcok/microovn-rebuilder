import os
import subprocess
from subprocess import CompletedProcess

from microovn_rebuilder.remote.base import BaseConnector, ConnectorException
from microovn_rebuilder.target import Target


class LXDConnector(BaseConnector):

    def update(self, target: Target) -> None:
        for remote in self.remotes:
            print(f"{os.linesep}[{remote}] Removing remote file {target.remote_path}")
            result = self._run_command(
                "lxc", "file", "delete", f"{remote}{target.remote_path}"
            )
            self._check_cmd_result(result, f"[{remote}] Failed to remove remote file")

            print(
                f"[{remote}] Uploading file {target.local_path} to {target.remote_path}"
            )
            result = self._run_command(
                "lxc", "file", "push", target.local_path, f"{remote}{target.remote_path}"
            )
            self._check_cmd_result(result, f"[{remote}] Failed to upload file")

            print(f"[{remote}] Restarting {target.service}")
            result = self._run_command(
                "lxc", "exec", remote, "snap", "restart", target.service
            )
            self._check_cmd_result(result, f"[{remote}] Failed to restart service")

    def check_remote(self, remote_dst: str) -> None:
        for remote in self.remotes:
            result = self._run_command(
                "lxc", "exec", remote, "--", "test", "-d", remote_dst
            )
            self._check_cmd_result(
                result,
                f"[{remote}] Remote directory '{remote_dst}' does not exist on LXC instance {remote}",
            )

    @staticmethod
    def _run_command(*args) -> CompletedProcess:
        return subprocess.run(args, capture_output=True)

    @staticmethod
    def _check_cmd_result(result: CompletedProcess, err_msg: str) -> None:
        if result.returncode != 0:
            additional_err = f"{result.stderr.decode("utf-8")}" or ""
            raise ConnectorException(f"{err_msg}: {additional_err}".rstrip())
