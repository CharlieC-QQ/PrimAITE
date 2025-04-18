# © Crown-owned copyright 2025, Defence Science and Technology Laboratory UK
"""Actions for interacting with network interfact cards (NICs) on network hosts."""
from abc import ABC
from typing import ClassVar

from primaite.game.agent.actions.manager import AbstractAction
from primaite.interface.request import RequestFormat

__all__ = ("HostNICEnableAction", "HostNICDisableAction")


class HostNICAbstractAction(AbstractAction, ABC):
    """
    Abstract base class for NIC actions.

    Any action which applies to a NIC and uses node_name and nic_num as its only two parameters can inherit from this
    base class.
    """

    class ConfigSchema(AbstractAction.ConfigSchema, ABC):
        """Base Configuration schema for HostNIC actions."""

        node_name: str
        nic_num: int
        verb: ClassVar[str]

    @classmethod
    def form_request(cls, config: ConfigSchema) -> RequestFormat:
        """Return the action formatted as a request which can be ingested by the PrimAITE simulation."""
        if config.node_name is None or config.nic_num is None:
            return ["do-nothing"]
        return [
            "network",
            "node",
            config.node_name,
            "network_interface",
            config.nic_num,
            config.verb,
        ]


class HostNICEnableAction(HostNICAbstractAction, discriminator="host-nic-enable"):
    """Action which enables a NIC."""

    config: "HostNICEnableAction.ConfigSchema"

    class ConfigSchema(HostNICAbstractAction.ConfigSchema):
        """Configuration schema for HostNICEnableAction."""

        verb: ClassVar[str] = "enable"


class HostNICDisableAction(HostNICAbstractAction, discriminator="host-nic-disable"):
    """Action which disables a NIC."""

    config: "HostNICDisableAction.ConfigSchema"

    class ConfigSchema(HostNICAbstractAction.ConfigSchema):
        """Configuration schema for HostNICDisableAction."""

        verb: ClassVar[str] = "disable"
