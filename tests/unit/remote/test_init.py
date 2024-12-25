import pytest

from microovn_rebuilder.remote import _CONNECTORS, ConnectorException, create_connector


@pytest.mark.parametrize(
    "bad_spec", ["foo", "foo,bar", "lxd:vm1,ssh:vm2", "foo:vm1,foo:vm2"]
)
def test_create_connector_invalid_spec(bad_spec):
    with pytest.raises(ConnectorException):
        create_connector(bad_spec)


def test_create_connector():
    connector = create_connector("lxd:vm1,lxd:vm2")
    expected_remotes = ["vm1", "vm2"]
    expected_type = _CONNECTORS["lxd"]

    assert isinstance(connector, expected_type)
    assert connector.remotes == expected_remotes
