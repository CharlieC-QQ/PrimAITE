# © Crown-owned copyright 2025, Defence Science and Technology Laboratory UK
"""Actions for manipulating Access Control Lists (ACLs)."""
from __future__ import annotations

from abc import ABC
from typing import Literal, Union

from primaite.game.agent.actions.manager import AbstractAction
from primaite.interface.request import RequestFormat
from primaite.utils.validation.ip_protocol import IPProtocol
from primaite.utils.validation.ipv4_address import IPV4Address
from primaite.utils.validation.port import Port

__all__ = (
    "RouterACLAddRuleAction",
    "RouterACLRemoveRuleAction",
    "FirewallACLAddRuleAction",
    "FirewallACLRemoveRuleAction",
)


class ACLAddRuleAbstractAction(AbstractAction, ABC):
    """Base abstract class for ACL add rule actions."""

    class ConfigSchema(AbstractAction.ConfigSchema, ABC):
        """Configuration Schema base for ACL add rule abstract actions."""

        src_ip: Union[IPV4Address, Literal["ALL"]]
        protocol_name: Union[IPProtocol, Literal["ALL"]]
        permission: Literal["PERMIT", "DENY"]
        position: int
        dst_ip: Union[IPV4Address, Literal["ALL"]]
        src_port: Union[Port, Literal["ALL"]]
        dst_port: Union[Port, Literal["ALL"]]
        src_wildcard: Union[IPV4Address, Literal["NONE"]]
        dst_wildcard: Union[IPV4Address, Literal["NONE"]]


class ACLRemoveRuleAbstractAction(AbstractAction, ABC):
    """Base abstract class for acl remove rule actions."""

    class ConfigSchema(AbstractAction.ConfigSchema, ABC):
        """Configuration Schema base for ACL remove rule abstract actions."""

        position: int


class RouterACLAddRuleAction(ACLAddRuleAbstractAction, discriminator="router-acl-add-rule"):
    """Action which adds a rule to a router's acl."""

    config: "RouterACLAddRuleAction.ConfigSchema"

    class ConfigSchema(ACLAddRuleAbstractAction.ConfigSchema):
        """Configuration Schema for RouterACLAddRuleAction."""

        target_router: str

    @classmethod
    def form_request(cls, config: ConfigSchema) -> RequestFormat:
        """Return the action formatted as a request which can be ingested by the PrimAITE simulation."""
        return [
            "network",
            "node",
            config.target_router,
            "acl",
            "add_rule",
            config.permission,
            config.protocol_name,
            str(config.src_ip),
            str(config.src_wildcard),
            config.src_port,
            str(config.dst_ip),
            str(config.dst_wildcard),
            config.dst_port,
            config.position,
        ]


class RouterACLRemoveRuleAction(ACLRemoveRuleAbstractAction, discriminator="router-acl-remove-rule"):
    """Action which removes a rule from a router's acl."""

    config: "RouterACLRemoveRuleAction.ConfigSchema"

    class ConfigSchema(ACLRemoveRuleAbstractAction.ConfigSchema):
        """Configuration schema for RouterACLRemoveRuleAction."""

        target_router: str

    @classmethod
    def form_request(cls, config: ConfigSchema) -> RequestFormat:
        """Return the action formatted as a request which can be ingested by the PrimAITE simulation."""
        return ["network", "node", config.target_router, "acl", "remove_rule", config.position]


class FirewallACLAddRuleAction(ACLAddRuleAbstractAction, discriminator="firewall-acl-add-rule"):
    """Action which adds a rule to a firewall port's acl."""

    config: "FirewallACLAddRuleAction.ConfigSchema"

    class ConfigSchema(ACLAddRuleAbstractAction.ConfigSchema):
        """Configuration schema for FirewallACLAddRuleAction."""

        target_firewall_nodename: str
        firewall_port_name: str
        firewall_port_direction: str

    @classmethod
    def form_request(cls, config: ConfigSchema) -> RequestFormat:
        """Return the action formatted as a request which can be ingested by the PrimAITE simulation."""
        return [
            "network",
            "node",
            config.target_firewall_nodename,
            config.firewall_port_name,
            config.firewall_port_direction,
            "acl",
            "add_rule",
            config.permission,
            config.protocol_name,
            str(config.src_ip),
            str(config.src_wildcard),
            config.src_port,
            str(config.dst_ip),
            str(config.dst_wildcard),
            config.dst_port,
            config.position,
        ]


class FirewallACLRemoveRuleAction(ACLRemoveRuleAbstractAction, discriminator="firewall-acl-remove-rule"):
    """Action which removes a rule from a firewall port's acl."""

    config: "FirewallACLRemoveRuleAction.ConfigSchema"

    class ConfigSchema(ACLRemoveRuleAbstractAction.ConfigSchema):
        """Configuration schema for FirewallACLRemoveRuleAction."""

        target_firewall_nodename: str
        firewall_port_name: str
        firewall_port_direction: str

    @classmethod
    def form_request(cls, config: ConfigSchema) -> RequestFormat:
        """Return the action formatted as a request which can be ingested by the PrimAITE simulation."""
        return [
            "network",
            "node",
            config.target_firewall_nodename,
            config.firewall_port_name,
            config.firewall_port_direction,
            "acl",
            "remove_rule",
            config.position,
        ]
