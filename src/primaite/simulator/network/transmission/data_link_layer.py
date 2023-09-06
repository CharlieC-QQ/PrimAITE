from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel

from primaite import getLogger
from primaite.simulator.network.protocols.arp import ARPPacket
from primaite.simulator.network.protocols.dns import DNSPacket
from primaite.simulator.network.transmission.network_layer import ICMPPacket, IPPacket, IPProtocol
from primaite.simulator.network.transmission.primaite_layer import PrimaiteHeader
from primaite.simulator.network.transmission.transport_layer import TCPHeader, UDPHeader
from primaite.simulator.network.utils import convert_bytes_to_megabits

_LOGGER = getLogger(__name__)


class EthernetHeader(BaseModel):
    """
    Represents the Ethernet layer of a network frame.

    :param src_mac_addr: Source MAC address.
    :param dst_mac_addr: Destination MAC address.

    :Example:

    >>> ethernet = EthernetHeader(
    ...     src_mac_addr='AA:BB:CC:DD:EE:FF',
    ...     dst_mac_addr='11:22:33:44:55:66'
    ... )
    """

    src_mac_addr: str
    "Source MAC address."
    dst_mac_addr: str
    "Destination MAC address."


class Frame(BaseModel):
    """
    Represents a complete network frame with all layers.

    :param ethernet: Ethernet layer.
    :param ip: IP layer.
    :param tcp: TCP layer.
    :param payload: Payload data in the frame.

    :Example:

    >>> from ipaddress import IPv4Address
    >>> frame=Frame(
    ...     ethernet=EthernetHeader(
    ...         src_mac_addr='AA:BB:CC:DD:EE:FF',
    ...         dst_mac_addr='11:22:33:44:55:66'
    ...     ),
    ...     ip=IPPacket(
    ...         src_ip_address=IPv4Address('192.168.0.1'),
    ...         dst_ip_address=IPv4Address('10.0.0.1'),
    ...     ),
    ...     tcp=TCPHeader(
    ...         src_port=8080,
    ...         dst_port=80,
    ...     ),
    ...     payload=b"Hello, World!"
    ... )
    """

    def __init__(self, **kwargs):
        if kwargs.get("tcp") and kwargs.get("udp"):
            msg = "Network Frame cannot have both a TCP header and a UDP header"
            _LOGGER.error(msg)
            raise ValueError(msg)
        if kwargs["ip"].protocol == IPProtocol.TCP and not kwargs.get("tcp"):
            msg = "Cannot build a Frame using the TCP IP Protocol without a TCPHeader"
            _LOGGER.error(msg)
            raise ValueError(msg)
        if kwargs["ip"].protocol == IPProtocol.UDP and not kwargs.get("UDP"):
            msg = "Cannot build a Frame using the UDP IP Protocol without a UDPHeader"
            _LOGGER.error(msg)
            raise ValueError(msg)
        if kwargs["ip"].protocol == IPProtocol.ICMP and not kwargs.get("icmp"):
            msg = "Cannot build a Frame using the ICMP IP Protocol without a ICMPPacket"
            _LOGGER.error(msg)
            raise ValueError(msg)
        kwargs["primaite"] = PrimaiteHeader()

        super().__init__(**kwargs)

    ethernet: EthernetHeader
    "Ethernet header."
    ip: IPPacket
    "IP packet."
    tcp: Optional[TCPHeader] = None
    "TCP header."
    udp: Optional[UDPHeader] = None
    "UDP header."
    icmp: Optional[ICMPPacket] = None
    "ICMP header."
    arp: Optional[ARPPacket] = None
    "ARP packet."
    dns: Optional[DNSPacket] = None
    "DNS packet."
    primaite: PrimaiteHeader
    "PrimAITE header."
    payload: Optional[Any] = None
    "Raw data payload."
    sent_timestamp: Optional[datetime] = None
    "The time the Frame was sent from the original source NIC."
    received_timestamp: Optional[datetime] = None
    "The time the Frame was received at the final destination NIC."

    def decrement_ttl(self):
        """Decrement the IPPacket ttl by 1."""
        self.ip.ttl -= 1

    @property
    def can_transmit(self) -> bool:
        """Informs whether the Frame can transmit based on the IPPacket tll being >= 1."""
        return self.ip.ttl >= 1

    def set_sent_timestamp(self):
        """Set the sent_timestamp."""
        if not self.sent_timestamp:
            self.sent_timestamp = datetime.now()

    def set_received_timestamp(self):
        """Set the received_timestamp."""
        if not self.received_timestamp:
            self.received_timestamp = datetime.now()

    def transmission_duration(self) -> int:
        """The transmission duration in milliseconds."""
        delta = self.received_timestamp - self.sent_timestamp
        return int(delta.microseconds / 1000)

    @property
    def size(self) -> float:  # noqa - Keep it as MBits as this is how they're expressed
        """The size of the Frame in Bytes."""
        return float(len(self.model_dump_json().encode("utf-8")))

    @property
    def size_Mbits(self) -> float:  # noqa - Keep it as MBits as this is how they're expressed
        """The daa transfer size of the Frame in Mbits."""
        return convert_bytes_to_megabits(self.size)
