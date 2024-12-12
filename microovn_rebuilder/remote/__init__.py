from .base import BaseConnector, ConnectorException
from .lxd import LXDConnector

_CONNECTORS = {"lxd": LXDConnector}


def create_connector(remote_spec: str) -> BaseConnector:
    remotes = []
    types = set()
    for spec in remote_spec.split(","):
        connector_type, found, remote = spec.partition(":")
        if not found:
            raise ConnectorException(
                f"'{spec}' is not valid remote specification. Expected format is '<remote_type>:<remote_address>'"
            )

        remotes.append(remote)
        types.add(connector_type)

    if len(types) != 1:
        raise ConnectorException(
            f"'{remote_spec}' is not valid remote specification. All remotes must be of the same type'"
        )

    connector_type = types.pop()
    connector = _CONNECTORS.get(connector_type)
    if connector is None:
        raise ConnectorException(
            f"{connector_type} is not a valid connector type. Available types: {", ".join(_CONNECTORS.keys())}"
        )

    return connector(remotes)
