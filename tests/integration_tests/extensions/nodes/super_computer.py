# © Crown-owned copyright 2025, Defence Science and Technology Laboratory UK
from typing import ClassVar, Dict, Literal

from primaite.simulator.network.hardware.nodes.host.host_node import HostNode, NIC
from primaite.simulator.system.services.ftp.ftp_client import FTPClient
from primaite.utils.validation.ipv4_address import IPV4Address


class SuperComputer(HostNode, discriminator="supercomputer"):
    """
    A basic Computer class.

    Example:
        >>> pc_a = Computer(
            hostname="pc_a",
            ip_address="192.168.1.10",
            subnet_mask="255.255.255.0",
            default_gateway="192.168.1.1"
        )
        >>> pc_a.power_on()

    Instances of computer come 'pre-packaged' with the following:

    * Core Functionality:
        * Packet Capture
        * Sys Log
    * Services:
        * ARP Service
        * ICMP Service
        * DNS Client
        * FTP Client
        * NTP Client
    * Applications:
        * Web Browser
    """

    class ConfigSchema(HostNode.ConfigSchema):
        type: Literal["supercomputer"] = "supercomputer"

    SYSTEM_SOFTWARE: ClassVar[Dict] = {**HostNode.SYSTEM_SOFTWARE, "ftp-client": FTPClient}

    def __init__(self, **kwargs):
        print("--- Extended Component: SuperComputer ---")
        super().__init__(**kwargs)

    pass
