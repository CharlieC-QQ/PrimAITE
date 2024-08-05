# © Crown-owned copyright 2024, Defence Science and Technology Laboratory UK
from ipaddress import IPv4Address
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
from primaite.simulator.system.applications.application import ApplicationOperatingState
from primaite.simulator.system.applications.red_applications.c2.c2_beacon import C2Beacon
from primaite.simulator.system.applications.red_applications.c2.c2_server import C2Server
from primaite.simulator.system.applications.red_applications.ransomware_script import RansomwareScript
from primaite.simulator.system.services.dns.dns_server import DNSServer
from primaite.simulator.system.services.web_server.web_server import WebServer


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
    node_a.software_manager.install(software_class=C2Server)

    node_b = Computer(hostname="node_b", ip_address="192.168.0.11", subnet_mask="255.255.255.0", start_up_duration=0)
    node_b.software_manager.install(software_class=C2Beacon)
    node_b.power_on()
    network.connect(node_a.network_interface[1], node_b.network_interface[1])

    return network


def test_c2_suite_setup_receive(basic_network):
    """Test that C2 Beacon can successfully establish connection with the C2 Server."""
    network: Network = basic_network
    computer_a: Computer = network.get_node_by_hostname("node_a")
    c2_server: C2Server = computer_a.software_manager.software.get("C2Server")

    computer_b: Computer = network.get_node_by_hostname("node_b")
    c2_beacon: C2Beacon = computer_b.software_manager.software.get("C2Beacon")

    # Assert that the c2 beacon configure correctly.
    c2_beacon.configure(c2_server_ip_address="192.168.0.10")
    assert c2_beacon.c2_remote_connection == IPv4Address("192.168.0.10")

    c2_server.run()
    c2_beacon.establish()

    # Asserting that the c2 beacon has established a c2 connection
    assert c2_beacon.c2_connection_active is True

    # Asserting that the c2 server has established a c2 connection.
    assert c2_server.c2_connection_active is True
    assert c2_server.c2_remote_connection == IPv4Address("192.168.0.11")


def test_c2_suite_keep_alive_inactivity(basic_network):
    """Tests that C2 Beacon disconnects from the C2 Server after inactivity."""
    network: Network = basic_network
    computer_a: Computer = network.get_node_by_hostname("node_a")
    c2_server: C2Server = computer_a.software_manager.software.get("C2Server")

    computer_b: Computer = network.get_node_by_hostname("node_b")
    c2_beacon: C2Beacon = computer_b.software_manager.software.get("C2Beacon")

    # Initial config (#TODO: Make this a function)
    c2_beacon.configure(c2_server_ip_address="192.168.0.10", keep_alive_frequency=2)
    c2_server.run()
    c2_beacon.establish()

    c2_beacon.apply_timestep(0)
    assert c2_beacon.keep_alive_inactivity == 1

    # Keep Alive successfully sent and received upon the 2nd timestep.
    c2_beacon.apply_timestep(1)
    assert c2_beacon.keep_alive_inactivity == 0
    assert c2_beacon.c2_connection_active == True

    # Now we turn off the c2 server (Thus preventing a keep alive)
    c2_server.close()
    c2_beacon.apply_timestep(2)
    c2_beacon.apply_timestep(3)
    assert c2_beacon.keep_alive_inactivity == 2
    assert c2_beacon.c2_connection_active == False
    assert c2_beacon.health_state_actual == ApplicationOperatingState.CLOSED


# TODO: Flesh out these tests.
def test_c2_suite_configure_via_actions(basic_network):
    """Tests that a red agent is able to configure the c2 beacon and c2 server via Actions."""
    # Setting up the network:
    network: Network = basic_network
    computer_a: Computer = network.get_node_by_hostname("node_a")
    c2_server: C2Server = computer_a.software_manager.software.get("C2Server")

    computer_b: Computer = network.get_node_by_hostname("node_b")
    c2_beacon: C2Beacon = computer_b.software_manager.software.get("C2Beacon")

    # Testing Via Requests:
    network.apply_request(["node", "node_a", "application", "C2Server", "run"])

    c2_beacon_config = {
        "c2_server_ip_address": "192.168.0.10",
        "keep_alive_frequency": 5,
        "masquerade_protocol": IPProtocol.TCP,
        "masquerade_port": Port.HTTP,
    }

    network.apply_request(["node", "node_b", "application", "C2Beacon", "configure", c2_beacon_config])
    network.apply_request(["node", "node_b", "application", "C2Beacon", "execute"])

    assert c2_beacon.c2_connection_active is True
    assert c2_server.c2_connection_active is True
    assert c2_server.c2_remote_connection == IPv4Address("192.168.0.11")

    # Testing Via Agents:
    # TODO:


def test_c2_suite_configure_ransomware(basic_network):
    """Tests that a red agent is able to configure ransomware via C2 Server Actions."""
    # Setting up the network:
    network: Network = basic_network
    computer_a: Computer = network.get_node_by_hostname("node_a")
    c2_server: C2Server = computer_a.software_manager.software.get("C2Server")

    computer_b: Computer = network.get_node_by_hostname("node_b")
    c2_beacon: C2Beacon = computer_b.software_manager.software.get("C2Beacon")

    c2_beacon.configure(c2_server_ip_address="192.168.0.10", keep_alive_frequency=2)
    c2_server.run()
    c2_beacon.establish()

    # Testing Via Requests:
    computer_b.software_manager.install(software_class=RansomwareScript)
    ransomware_config = {"server_ip_address": "1.1.1.1"}
    network.apply_request(["node", "node_a", "application", "C2Server", "ransomware_configure", ransomware_config])

    ransomware_script: RansomwareScript = computer_b.software_manager.software["RansomwareScript"]

    assert ransomware_script.server_ip_address == "1.1.1.1"

    # Testing Via Agents:
    # TODO:


def test_c2_suite_terminal(basic_network):
    """Tests that a red agent is able to execute terminal commands via C2 Server Actions."""


@pytest.fixture(scope="function")
def acl_network() -> Network:
    # 0: Pull out the network
    network = Network()

    # 1: Set up network hardware
    # 1.1: Configure the router
    router = Router(hostname="router", num_ports=3, start_up_duration=0)
    router.power_on()
    router.configure_port(port=1, ip_address="10.0.1.1", subnet_mask="255.255.255.0")
    router.configure_port(port=2, ip_address="10.0.2.1", subnet_mask="255.255.255.0")

    # 1.2: Create and connect switches
    switch_1 = Switch(hostname="switch_1", num_ports=6, start_up_duration=0)
    switch_1.power_on()
    network.connect(endpoint_a=router.network_interface[1], endpoint_b=switch_1.network_interface[6])
    router.enable_port(1)
    switch_2 = Switch(hostname="switch_2", num_ports=6, start_up_duration=0)
    switch_2.power_on()
    network.connect(endpoint_a=router.network_interface[2], endpoint_b=switch_2.network_interface[6])
    router.enable_port(2)

    # 1.3: Create and connect computer
    client_1 = Computer(
        hostname="client_1",
        ip_address="10.0.1.2",
        subnet_mask="255.255.255.0",
        default_gateway="10.0.1.1",
        start_up_duration=0,
    )
    client_1.power_on()
    client_1.software_manager.install(software_class=C2Server)
    network.connect(
        endpoint_a=client_1.network_interface[1],
        endpoint_b=switch_1.network_interface[1],
    )

    client_2 = Computer(
        hostname="client_2",
        ip_address="10.0.1.3",
        subnet_mask="255.255.255.0",
        default_gateway="10.0.1.1",
        start_up_duration=0,
    )
    client_2.power_on()
    client_2.software_manager.install(software_class=C2Beacon)
    network.connect(endpoint_a=client_2.network_interface[1], endpoint_b=switch_2.network_interface[1])

    # 1.4: Create and connect servers
    server_1 = Server(
        hostname="server_1",
        ip_address="10.0.2.2",
        subnet_mask="255.255.255.0",
        default_gateway="10.0.2.1",
        start_up_duration=0,
    )
    server_1.power_on()
    network.connect(endpoint_a=server_1.network_interface[1], endpoint_b=switch_2.network_interface[1])

    server_2 = Server(
        hostname="server_2",
        ip_address="10.0.2.3",
        subnet_mask="255.255.255.0",
        default_gateway="10.0.2.1",
        start_up_duration=0,
    )
    server_2.power_on()
    network.connect(endpoint_a=server_2.network_interface[1], endpoint_b=switch_2.network_interface[2])

    return network


# TODO: Fix this test: Not sure why this isn't working


def test_c2_suite_acl_block(acl_network):
    """Tests that C2 Beacon disconnects from the C2 Server after blocking ACL rules."""
    network: Network = acl_network
    computer_a: Computer = network.get_node_by_hostname("client_1")
    c2_server: C2Server = computer_a.software_manager.software.get("C2Server")

    computer_b: Computer = network.get_node_by_hostname("client_2")
    c2_beacon: C2Beacon = computer_b.software_manager.software.get("C2Beacon")

    router: Router = network.get_node_by_hostname("router")

    network.apply_timestep(0)
    # Initial config (#TODO: Make this a function)
    c2_beacon.configure(c2_server_ip_address="10.0.1.2", keep_alive_frequency=2)

    c2_server.run()
    c2_beacon.establish()

    assert c2_beacon.keep_alive_inactivity == 0
    assert c2_beacon.c2_connection_active == True
    assert c2_server.c2_connection_active == True

    # Now we add a HTTP blocking acl (Thus preventing a keep alive)
    router.acl.add_rule(action=ACLAction.DENY, src_port=Port.HTTP, dst_port=Port.HTTP, position=1)

    c2_beacon.apply_timestep(1)
    c2_beacon.apply_timestep(2)
    assert c2_beacon.keep_alive_inactivity == 2
    assert c2_beacon.c2_connection_active == False
    assert c2_beacon.health_state_actual == ApplicationOperatingState.CLOSED


def test_c2_suite_launch_ransomware(basic_network):
    """Tests that a red agent is able to launch ransomware via C2 Server Actions."""
