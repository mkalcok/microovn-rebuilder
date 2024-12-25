from pathlib import Path

import pytest

from microovn_rebuilder.target import ConfigException, Target, parse_config


@pytest.mark.parametrize("remote_path", ["/non/default", None])
def test_target_class(remote_path):
    kwargs = {
        "local_rel_path": "ovn/utils/ovn-northd",
        "remote_rel_path": "bin/ovn-northd",
        "local_base_path": "/home/",
        "service": "ovn-northd",
    }
    if remote_path is not None:
        kwargs["remote_base_path"] = remote_path
        expected_remote_base_path = remote_path
    else:
        expected_remote_base_path = remote_path or "/root/squashfs-root/"

    target = Target(**kwargs)

    assert target.local_path == Path(target.local_base_path, target.local_rel_path)
    assert target.remote_path == Path(expected_remote_base_path, target.remote_rel_path)


def test_parse_config_no_file(local_ovn_path, remote_deployment_path):
    with pytest.raises(ConfigException):
        parse_config(
            "/surely/this/path/does/not/exist", local_ovn_path, remote_deployment_path
        )


@pytest.mark.parametrize(
    "config_data",
    [
        "{}",  # No targets
        "targets: foo",  # wrong data type for "targets"
        "targets: []",  # empty target list
        'targets: [{"local_path": "/home/ovn"}]',  # target missing required fields
    ],
)
def test_parse_config_target_parsing_err(
    mocker, local_ovn_path, remote_deployment_path, config_data
):
    mocker.patch("builtins.open", mocker.mock_open(read_data=config_data))
    with pytest.raises(ConfigException):
        parse_config("/dev/null", local_ovn_path, remote_deployment_path)
