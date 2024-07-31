# © Crown-owned copyright 2024, Defence Science and Technology Laboratory UK
from typing import Tuple

import pytest

from primaite.game.agent.interface import ProxyAgent
from primaite.game.game import PrimaiteGame
from primaite.simulator.network.container import Network
from primaite.simulator.network.hardware.nodes.host.computer import Computer
from primaite.simulator.network.hardware.nodes.host.server import Server
from primaite.simulator.network.hardware.nodes.network.router import ACLAction, Router
from primaite.simulator.network.hardware.nodes.network.switch import Switch
from primaite.simulator.network.transmission.network_layer import IPProtocol
from primaite.simulator.network.transmission.transport_layer import Port
from primaite.simulator.system.services.dns.dns_server import DNSServer
from primaite.simulator.system.services.service import ServiceOperatingState
from primaite.simulator.system.services.web_server.web_server import WebServer
from primaite.simulator.system.applications.red_applications.c2.c2_beacon import C2Beacon
from primaite.simulator.system.applications.red_applications.c2.c2_server import C2Server

# TODO: Update these tests.

@pytest.fixture(scope="function")
def c2_server_on_computer() -> Tuple[C2Beacon, Computer]:
    computer: Computer = Computer(
        hostname="node_a", ip_address="192.168.0.10", subnet_mask="255.255.255.0", start_up_duration=0
    )
    computer.power_on()
    c2_beacon = computer.software_manager.software.get("C2Beacon")

    return [c2_beacon, computer]

@pytest.fixture(scope="function")
def c2_server_on_computer() -> Tuple[C2Server, Computer]:
    computer: Computer = Computer(
        hostname="node_b", ip_address="192.168.0.11", subnet_mask="255.255.255.0", start_up_duration=0
    )
    computer.power_on()
    c2_server = computer.software_manager.software.get("C2Server")

    return [c2_server, computer]



@pytest.fixture(scope="function")
def basic_network() -> Network:
    network = Network()
    node_a = Computer(hostname="node_a", ip_address="192.168.0.10", subnet_mask="255.255.255.0", start_up_duration=0)
    node_a.power_on()
    node_a.software_manager.get_open_ports()

    node_b = Computer(hostname="node_b", ip_address="192.168.0.11", subnet_mask="255.255.255.0", start_up_duration=0)
    node_b.power_on()
    network.connect(node_a.network_interface[1], node_b.network_interface[1])

    return network