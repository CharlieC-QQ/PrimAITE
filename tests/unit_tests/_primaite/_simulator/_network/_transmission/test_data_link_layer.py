# © Crown-owned copyright 2025, Defence Science and Technology Laboratory UK
import pytest

from primaite.simulator.network.protocols.icmp import ICMPPacket
from primaite.simulator.network.transmission.data_link_layer import EthernetHeader, Frame
from primaite.simulator.network.transmission.network_layer import IPPacket, Precedence
from primaite.simulator.network.transmission.primaite_layer import AgentSource, DataStatus
from primaite.simulator.network.transmission.transport_layer import TCPFlags, TCPHeader, UDPHeader
from primaite.utils.validation.ip_protocol import PROTOCOL_LOOKUP
from primaite.utils.validation.port import PORT_LOOKUP


def test_frame_minimal_instantiation():
    """Tests that the minimum frame (TCP SYN) using default values."""
    frame = Frame(
        ethernet=EthernetHeader(src_mac_addr="aa:bb:cc:dd:ee:ff", dst_mac_addr="11:22:33:44:55:66"),
        ip=IPPacket(src_ip_address="192.168.0.10", dst_ip_address="192.168.0.20"),
        tcp=TCPHeader(
            src_port=8080,
            dst_port=80,
        ),
    )

    # Check network layer default values
    assert frame.ip.protocol == PROTOCOL_LOOKUP["TCP"]
    assert frame.ip.ttl == 64
    assert frame.ip.precedence == Precedence.ROUTINE

    # Check transport layer default values
    assert frame.tcp.flags == [TCPFlags.SYN]

    # Check primaite custom header default values
    assert frame.primaite.agent_source == AgentSource.GREEN
    assert frame.primaite.data_status == DataStatus.GOOD

    # Check that model can be dumped down to json and returned as size in Bytes
    assert frame.size


def test_frame_creation_fails_tcp_without_header():
    """Tests Frame creation fails if the IPProtocol is TCP but there is no TCPHeader."""
    with pytest.raises(ValueError):
        Frame(
            ethernet=EthernetHeader(src_mac_addr="aa:bb:cc:dd:ee:ff", dst_mac_addr="11:22:33:44:55:66"),
            ip=IPPacket(src_ip_address="192.168.0.10", dst_ip_address="192.168.0.20", protocol=PROTOCOL_LOOKUP["TCP"]),
        )


def test_frame_creation_fails_udp_without_header():
    """Tests Frame creation fails if the IPProtocol is UDP but there is no UDPHeader."""
    with pytest.raises(ValueError):
        Frame(
            ethernet=EthernetHeader(src_mac_addr="aa:bb:cc:dd:ee:ff", dst_mac_addr="11:22:33:44:55:66"),
            ip=IPPacket(src_ip_address="192.168.0.10", dst_ip_address="192.168.0.20", protocol=PROTOCOL_LOOKUP["UDP"]),
        )


def test_frame_creation_fails_tcp_with_udp_header():
    """Tests Frame creation fails if the IPProtocol is TCP but there is a UDPHeader."""
    with pytest.raises(ValueError):
        Frame(
            ethernet=EthernetHeader(src_mac_addr="aa:bb:cc:dd:ee:ff", dst_mac_addr="11:22:33:44:55:66"),
            ip=IPPacket(src_ip_address="192.168.0.10", dst_ip_address="192.168.0.20", protocol=PROTOCOL_LOOKUP["TCP"]),
            udp=UDPHeader(src_port=8080, dst_port=80),
        )


def test_frame_creation_fails_udp_with_tcp_header():
    """Tests Frame creation fails if the IPProtocol is UDP but there is a TCPHeader."""
    with pytest.raises(ValueError):
        Frame(
            ethernet=EthernetHeader(src_mac_addr="aa:bb:cc:dd:ee:ff", dst_mac_addr="11:22:33:44:55:66"),
            ip=IPPacket(src_ip_address="192.168.0.10", dst_ip_address="192.168.0.20", protocol=PROTOCOL_LOOKUP["UDP"]),
            udp=TCPHeader(src_port=8080, dst_port=80),
        )


def test_icmp_frame_creation():
    """Tests Frame creation for ICMP."""
    frame = Frame(
        ethernet=EthernetHeader(src_mac_addr="aa:bb:cc:dd:ee:ff", dst_mac_addr="11:22:33:44:55:66"),
        ip=IPPacket(src_ip_address="192.168.0.10", dst_ip_address="192.168.0.20", protocol=PROTOCOL_LOOKUP["ICMP"]),
        icmp=ICMPPacket(),
    )
    assert frame


def test_icmp_frame_creation_fails_without_icmp_header():
    """Tests Frame creation for ICMP."""
    with pytest.raises(ValueError):
        Frame(
            ethernet=EthernetHeader(src_mac_addr="aa:bb:cc:dd:ee:ff", dst_mac_addr="11:22:33:44:55:66"),
            ip=IPPacket(src_ip_address="192.168.0.10", dst_ip_address="192.168.0.20", protocol=PROTOCOL_LOOKUP["ICMP"]),
        )
