import pytest

from microovn_rebuilder.remote import _CONNECTORS, ConnectorException, create_connector


@pytest.mark.parametrize(
    "bad_spec", ["foo", "foo,bar", "lxd:vm1,ssh:vm2", "foo:vm1,foo:vm2"]
)
def test_create_connector_invalid_spec(bad_spec):
    with pytest.raises(ConnectorException):
        create_connector(bad_spec)


@pytest.mark.parametrize("connector_type", ["lxd", "ssh"])
def test_create_connector(mocker, connector_type):
    expected_remotes = ["vm1", "vm2"]
    expected_type = _CONNECTORS[connector_type]
    mock_initialize = mocker.patch.object(expected_type, "initialize")

    connector = create_connector(f"{connector_type}:vm1,{connector_type}:vm2")

    assert isinstance(connector, expected_type)
    assert connector.remotes == expected_remotes
    mock_initialize.assert_called_once()
