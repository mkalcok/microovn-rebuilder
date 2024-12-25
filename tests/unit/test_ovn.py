from subprocess import CompletedProcess
from unittest.mock import MagicMock, call

import pytest

from microovn_rebuilder import ovn


@pytest.mark.parametrize("build_rc", [0, 1])
def test_rebuild_pass(mocker, build_rc, local_ovn_path):
    mock_result = MagicMock(autospec=CompletedProcess)
    mock_result.returncode = build_rc
    mock_result.stdout = b"STDOUT"
    mock_result.stderr = b"STDERR"

    mock_print = mocker.patch("builtins.print")
    mock_run = mocker.patch.object(ovn.subprocess, "run", return_value=mock_result)
    parallel_jobs = 10

    build_success = ovn.rebuild(local_ovn_path, parallel_jobs)

    assert build_success == (not bool(build_rc))
    mock_run.assert_called_once_with(
        ["make", f"-j{parallel_jobs}"], cwd=local_ovn_path, capture_output=True
    )

    if not build_success:
        mock_print.assert_has_calls(
            [
                call(mock_result.stdout.decode("utf-8")),
                call(mock_result.stderr.decode("utf-8")),
            ]
        )
