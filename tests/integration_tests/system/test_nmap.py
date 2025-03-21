# © Crown-owned copyright 2025, Defence Science and Technology Laboratory UK
from enum import Enum
from ipaddress import IPv4Address, IPv4Network

import yaml

from primaite.game.game import PrimaiteGame
from primaite.simulator.system.applications.nmap import NMAP
from primaite.utils.validation.ip_protocol import PROTOCOL_LOOKUP
from primaite.utils.validation.port import PORT_LOOKUP
from tests import TEST_ASSETS_ROOT


def test_ping_scan_all_on(example_network):
    network = example_network

    client_1 = network.get_node_by_hostname("client_1")
    client_1_nmap: NMAP = client_1.software_manager.software["nmap"]  # noqa

    expected_result = [IPv4Address("192.168.1.10"), IPv4Address("192.168.1.14")]
    actual_result = client_1_nmap.ping_scan(target_ip_address=["192.168.1.10", "192.168.1.14"])

    assert sorted(actual_result) == sorted(expected_result)


def test_ping_scan_all_on_full_network(example_network):
    network = example_network

    client_1 = network.get_node_by_hostname("client_1")
    client_1_nmap: NMAP = client_1.software_manager.software["nmap"]  # noqa

    expected_result = [IPv4Address("192.168.1.1"), IPv4Address("192.168.1.10"), IPv4Address("192.168.1.14")]
    actual_result = client_1_nmap.ping_scan(target_ip_address=IPv4Network("192.168.1.0/24"))

    assert sorted(actual_result) == sorted(expected_result)


def test_ping_scan_some_on(example_network):
    network = example_network

    client_1 = network.get_node_by_hostname("client_1")
    client_1_nmap: NMAP = client_1.software_manager.software["nmap"]  # noqa

    network.get_node_by_hostname("server_2").power_off()

    expected_result = [IPv4Address("192.168.1.1"), IPv4Address("192.168.1.10")]
    actual_result = client_1_nmap.ping_scan(target_ip_address=IPv4Network("192.168.1.0/24"))

    assert sorted(actual_result) == sorted(expected_result)


def test_ping_scan_all_off(example_network):
    network = example_network

    client_1 = network.get_node_by_hostname("client_1")
    client_1_nmap: NMAP = client_1.software_manager.software["nmap"]  # noqa

    network.get_node_by_hostname("server_1").power_off()
    network.get_node_by_hostname("server_2").power_off()

    expected_result = []
    actual_result = client_1_nmap.ping_scan(target_ip_address=["192.168.1.10", "192.168.1.14"])

    assert sorted(actual_result) == sorted(expected_result)


def test_port_scan_one_node_one_port(example_network):
    network = example_network

    client_1 = network.get_node_by_hostname("client_1")
    client_1_nmap: NMAP = client_1.software_manager.software["nmap"]  # noqa

    client_2 = network.get_node_by_hostname("client_2")

    actual_result = client_1_nmap.port_scan(
        target_ip_address=client_2.network_interface[1].ip_address,
        target_port=PORT_LOOKUP["DNS"],
        target_protocol=PROTOCOL_LOOKUP["TCP"],
    )

    expected_result = {IPv4Address("192.168.10.22"): {PROTOCOL_LOOKUP["TCP"]: [PORT_LOOKUP["DNS"]]}}

    assert actual_result == expected_result


def sort_dict(d):
    """Recursively sorts a dictionary."""
    if isinstance(d, dict):
        return {k: sort_dict(v) for k, v in sorted(d.items(), key=lambda item: str(item[0]))}
    elif isinstance(d, list):
        return sorted(d, key=lambda item: str(item) if isinstance(item, Enum) else item)
    elif isinstance(d, Enum):
        return str(d)
    else:
        return d


def test_port_scan_full_subnet_all_ports_and_protocols(example_network):
    network = example_network

    client_1 = network.get_node_by_hostname("client_1")
    client_1_nmap: NMAP = client_1.software_manager.software["nmap"]  # noqa

    actual_result = client_1_nmap.port_scan(
        target_ip_address=IPv4Network("192.168.10.0/24"),
        target_port=[
            PORT_LOOKUP["ARP"],
            PORT_LOOKUP["HTTP"],
            PORT_LOOKUP["FTP"],
            PORT_LOOKUP["DNS"],
            PORT_LOOKUP["NTP"],
        ],
    )

    expected_result = {
        IPv4Address("192.168.10.1"): {PROTOCOL_LOOKUP["UDP"]: [PORT_LOOKUP["ARP"]]},
        IPv4Address("192.168.10.22"): {
            PROTOCOL_LOOKUP["TCP"]: [PORT_LOOKUP["HTTP"], PORT_LOOKUP["FTP"], PORT_LOOKUP["DNS"]],
            PROTOCOL_LOOKUP["UDP"]: [PORT_LOOKUP["ARP"], PORT_LOOKUP["NTP"]],
        },
    }

    assert sort_dict(actual_result) == sort_dict(expected_result)


def test_network_service_recon_all_ports_and_protocols(example_network):
    network = example_network

    client_1 = network.get_node_by_hostname("client_1")
    client_1_nmap: NMAP = client_1.software_manager.software["nmap"]  # noqa

    actual_result = client_1_nmap.network_service_recon(
        target_ip_address=IPv4Network("192.168.10.0/24"),
        target_port=PORT_LOOKUP["HTTP"],
        target_protocol=PROTOCOL_LOOKUP["TCP"],
    )

    expected_result = {IPv4Address("192.168.10.22"): {PROTOCOL_LOOKUP["TCP"]: [PORT_LOOKUP["HTTP"]]}}

    assert sort_dict(actual_result) == sort_dict(expected_result)


def test_ping_scan_red_agent():
    with open(TEST_ASSETS_ROOT / "configs/nmap_ping_scan_red_agent_config.yaml", "r") as file:
        cfg = yaml.safe_load(file)

    game = PrimaiteGame.from_config(cfg)

    game.step()

    expected_result = ["192.168.1.1", "192.168.1.10", "192.168.1.14"]

    action_history = game.agents["client_1_red_nmap"].history
    assert len(action_history) == 1
    actual_result = action_history[0].response.data["live_hosts"]

    assert sorted(actual_result) == sorted(expected_result)


def test_port_scan_red_agent():
    with open(TEST_ASSETS_ROOT / "configs/nmap_port_scan_red_agent_config.yaml", "r") as file:
        cfg = yaml.safe_load(file)

    game = PrimaiteGame.from_config(cfg)

    game.step()

    expected_result = {
        "192.168.10.1": {"udp": [219]},
        "192.168.10.22": {
            "tcp": [80, 21, 53],
            "udp": [219, 123],
        },
    }

    action_history = game.agents["client_1_red_nmap"].history
    assert len(action_history) == 1
    actual_result = action_history[0].response.data

    assert sorted(actual_result) == sorted(expected_result)


def test_network_service_recon_red_agent():
    with open(TEST_ASSETS_ROOT / "configs/nmap_network_service_recon_red_agent_config.yaml", "r") as file:
        cfg = yaml.safe_load(file)

    game = PrimaiteGame.from_config(cfg)

    game.step()

    expected_result = {"192.168.10.22": {"tcp": [80]}}

    action_history = game.agents["client_1_red_nmap"].history
    assert len(action_history) == 1
    actual_result = action_history[0].response.data

    assert sorted(actual_result) == sorted(expected_result)
