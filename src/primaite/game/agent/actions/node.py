# © Crown-owned copyright 2025, Defence Science and Technology Laboratory UK
"""Actions for interacting with nodes on the network."""
from abc import ABC, abstractmethod
from typing import ClassVar, List, Literal, Optional, Union

from primaite.game.agent.actions.manager import AbstractAction
from primaite.interface.request import RequestFormat
from primaite.utils.validation.ip_protocol import IPProtocol
from primaite.utils.validation.port import Port

__all__ = (
    "NodeOSScanAction",
    "NodeShutdownAction",
    "NodeStartupAction",
    "NodeResetAction",
    "NodeNMAPPingScanAction",
    "NodeNMAPPortScanAction",
    "NodeNetworkServiceReconAction",
)


class NodeAbstractAction(AbstractAction, ABC):
    """
    Abstract base class for node actions.

    Any action which applies to a node and uses node_name as its only parameter can inherit from this base class.
    """

    class ConfigSchema(AbstractAction.ConfigSchema, ABC):
        """Base Configuration schema for Node actions."""

        node_name: str
        verb: ClassVar[str]

    @classmethod
    def form_request(cls, config: ConfigSchema) -> RequestFormat:
        """Return the action formatted as a request which can be ingested by the PrimAITE simulation."""
        return ["network", "node", config.node_name, config.verb]


class NodeOSScanAction(AbstractAction, discriminator="node-os-scan"):
    """Action which scans a node's OS."""

    class ConfigSchema(AbstractAction.ConfigSchema, ABC):
        """Base Configuration schema for Node actions."""

        node_name: str

    @classmethod
    def form_request(cls, config: ConfigSchema) -> RequestFormat:
        """Return the action formatted as a request which can be ingested by the PrimAITE simulation."""
        return ["network", "node", config.node_name, "os", "scan"]


class NodeShutdownAction(NodeAbstractAction, discriminator="node-shutdown"):
    """Action which shuts down a node."""

    config: "NodeShutdownAction.ConfigSchema"

    class ConfigSchema(NodeAbstractAction.ConfigSchema):
        """Configuration schema for NodeShutdownAction."""

        verb: ClassVar[str] = "shutdown"


class NodeStartupAction(NodeAbstractAction, discriminator="node-startup"):
    """Action which starts up a node."""

    config: "NodeStartupAction.ConfigSchema"

    class ConfigSchema(NodeAbstractAction.ConfigSchema):
        """Configuration schema for NodeStartupAction."""

        verb: ClassVar[str] = "startup"


class NodeResetAction(NodeAbstractAction, discriminator="node-reset"):
    """Action which resets a node."""

    config: "NodeResetAction.ConfigSchema"

    class ConfigSchema(NodeAbstractAction.ConfigSchema):
        """Configuration schema for NodeResetAction."""

        verb: ClassVar[str] = "reset"


class NodeNMAPAbstractAction(AbstractAction, ABC):
    """Base class for NodeNMAP actions."""

    class ConfigSchema(AbstractAction.ConfigSchema, ABC):
        """Base Configuration Schema for NodeNMAP actions."""

        target_ip_address: Union[str, List[str]]
        show: bool = False
        source_node: str

    @classmethod
    @abstractmethod
    def form_request(cls, config: ConfigSchema) -> RequestFormat:
        # NMAP action requests don't share a common format for their requests
        # This is just a placeholder to ensure the method is defined.
        pass


class NodeNMAPPingScanAction(NodeNMAPAbstractAction, discriminator="node-nmap-ping-scan"):
    """Action which performs an nmap ping scan."""

    config: "NodeNMAPPingScanAction.ConfigSchema"

    @classmethod
    def form_request(cls, config: "NodeNMAPPingScanAction.ConfigSchema") -> RequestFormat:
        """Return the action formatted as a request which can be ingested by the PrimAITE simulation."""
        return [
            "network",
            "node",
            config.source_node,
            "application",
            "nmap",
            "ping_scan",
            {"target_ip_address": config.target_ip_address, "show": config.show},
        ]


class NodeNMAPPortScanAction(NodeNMAPAbstractAction, discriminator="node-nmap-port-scan"):
    """Action which performs an nmap port scan."""

    config: "NodeNMAPPortScanAction.ConfigSchema"

    class ConfigSchema(NodeNMAPAbstractAction.ConfigSchema):
        """Configuration Schema for NodeNMAPPortScanAction."""

        source_node: str
        target_protocol: Optional[Union[IPProtocol, List[IPProtocol]]] = None
        target_port: Optional[Union[Port, List[Port]]] = None
        show: Optional[bool] = (False,)

    @classmethod
    def form_request(cls, config: ConfigSchema) -> RequestFormat:
        """Return the action formatted as a request which can be ingested by the PrimAITE simulation."""
        return [
            "network",
            "node",
            config.source_node,
            "application",
            "nmap",
            "port_scan",
            {
                "target_ip_address": config.target_ip_address,
                "target_port": config.target_port,
                "target_protocol": config.target_protocol,
                "show": config.show,
            },
        ]


class NodeNetworkServiceReconAction(NodeNMAPAbstractAction, discriminator="node-network-service-recon"):
    """Action which performs an nmap network service recon (ping scan followed by port scan)."""

    class ConfigSchema(NodeNMAPAbstractAction.ConfigSchema):
        """Configuration schema for NodeNetworkServiceReconAction."""

        target_protocol: Optional[Union[IPProtocol, List[IPProtocol]]] = None
        target_port: Optional[Union[Port, List[Port]]] = None
        show: Optional[bool] = (False,)

    @classmethod
    def form_request(cls, config: ConfigSchema) -> RequestFormat:
        """Return the action formatted as a request which can be ingested by the PrimAITE simulation."""
        return [
            "network",
            "node",
            config.source_node,
            "application",
            "nmap",
            "network_service_recon",
            {
                "target_ip_address": config.target_ip_address,
                "target_port": config.target_port,
                "target_protocol": config.target_protocol,
                "show": config.show,
            },
        ]


class NodeAccountsAddUserAction(AbstractAction, discriminator="node-account-add-user"):
    class ConfigSchema(AbstractAction.ConfigSchema):
        type: Literal["node-account-add-user"] = "node-account-add-user"
        node_name: str
        username: str
        password: str
        is_admin: bool

    @classmethod
    @staticmethod
    def form_request(config: ConfigSchema) -> RequestFormat:
        return [
            "network",
            "node",
            config.node_name,
            "service",
            "user-manager",
            "add_user",
            config.username,
            config.password,
            config.is_admin,
        ]


class NodeAccountsDisableUserAction(AbstractAction, discriminator="node-account-disable-user"):
    class ConfigSchema(AbstractAction.ConfigSchema):
        type: Literal["node-account-disable-user"] = "node-account-disable-user"
        node_name: str
        username: str

    @classmethod
    @staticmethod
    def form_request(config: ConfigSchema) -> RequestFormat:
        return [
            "network",
            "node",
            config.node_name,
            "service",
            "user-manager",
            "disable_user",
            config.username,
        ]


class NodeSendLocalCommandAction(AbstractAction, discriminator="node-send-local-command"):
    class ConfigSchema(AbstractAction.ConfigSchema):
        type: Literal["node-send-local-command"] = "node-send-local-command"
        node_name: str
        username: str
        password: str
        command: RequestFormat

    @staticmethod
    def form_request(config: ConfigSchema) -> RequestFormat:
        return [
            "network",
            "node",
            config.node_name,
            "service",
            "terminal",
            "send_local_command",
            config.username,
            config.password,
            {"command": config.command},
        ]
