from primaite.simulator.network.container import Network
from primaite.simulator.network.hardware.base import NIC
from primaite.simulator.network.hardware.nodes.computer import Computer
from primaite.simulator.network.hardware.nodes.router import ACLAction, Router
from primaite.simulator.network.hardware.nodes.server import Server
from primaite.simulator.network.hardware.nodes.switch import Switch
from primaite.simulator.network.transmission.network_layer import IPProtocol
from primaite.simulator.network.transmission.transport_layer import Port


def client_server_routed() -> Network:
    """
    A basic Client/Server Network routed between subnets.

    +------------+      +------------+      +------------+      +------------+      +------------+
    |            |      |            |      |            |      |            |      |            |
    |  client_1  +------+  switch_2  +------+  router_1  +------+  switch_1  +------+  server_1  |
    |            |      |            |      |            |      |            |      |            |
    +------------+      +------------+      +------------+      +------------+      +------------+

    IP Table:

    """
    network = Network()

    # Router 1
    router_1 = Router(hostname="router_1", num_ports=3)
    router_1.power_on()
    router_1.configure_port(port=1, ip_address="192.168.1.1", subnet_mask="255.255.255.0")
    router_1.configure_port(port=2, ip_address="192.168.2.1", subnet_mask="255.255.255.0")

    # Switch 1
    switch_1 = Switch(hostname="switch_1", num_ports=6)
    switch_1.power_on()
    network.connect(endpoint_a=router_1.ethernet_ports[1], endpoint_b=switch_1.switch_ports[6])
    router_1.enable_port(1)

    # Switch 2
    switch_2 = Switch(hostname="switch_2", num_ports=6)
    switch_2.power_on()
    network.connect(endpoint_a=router_1.ethernet_ports[2], endpoint_b=switch_2.switch_ports[6])
    router_1.enable_port(2)

    # Client 1
    client_1 = Computer(
        hostname="client_1", ip_address="192.168.2.2", subnet_mask="255.255.255.0", default_gateway="192.168.2.1"
    )
    client_1.power_on()
    network.connect(endpoint_b=client_1.ethernet_port[1], endpoint_a=switch_2.switch_ports[1])

    # Server 1
    server_1 = Server(
        hostname="server_1", ip_address="192.168.1.2", subnet_mask="255.255.255.0", default_gateway="192.168.1.1"
    )
    server_1.power_on()
    network.connect(endpoint_b=server_1.ethernet_port[1], endpoint_a=switch_1.switch_ports[1])

    router_1.acl.add_rule(action=ACLAction.PERMIT, src_port=Port.ARP, dst_port=Port.ARP, position=22)

    router_1.acl.add_rule(action=ACLAction.PERMIT, protocol=IPProtocol.ICMP, position=23)

    return network


def arcd_uc2_network() -> Network:
    """
    Models the ARCD Use Case 2 Network.

                                                                                    +------------+
                                                                                    |  domain_   |
                                                                       +------------+ controller |
                                                                       |            |            |
                                                                       |            +------------+
                                                                       |
                                                                       |
    +------------+                                                     |            +------------+
    |            |                                                     |            |            |
    |  client_1  +---------+                                           |  +---------+ web_server |
    |            |         |                                           |  |         |            |
    +------------+         |                                           |  |         +------------+
                        +--+---------+      +------------+      +------+--+--+
                        |            |      |            |      |            |
                        |  switch_2  +------+  router_1  +------+  switch_1  |
                        |            |      |            |      |            |
                        +--+------+--+      +------------+      +--+---+--+--+
    +------------+         |      |                                |   |  |         +------------+
    |            |         |      |                                |   |  |         |  database  |
    |  client_2  +---------+      |                                |   |  +---------+  _server   |
    |            |                |                                |   |            |            |
    +------------+                |                                |   |            +------------+
                                  |         +------------+         |   |
                                  |         |  security  |         |   |
                                  +---------+   _suite   +---------+   |            +------------+
                                            |            |             |            |  backup_   |
                                            +------------+             +------------+  server    |
                                                                                    |            |
                                                                                    +------------+



    """
    network = Network()

    # Router 1
    router_1 = Router(hostname="router_1", num_ports=5)
    router_1.power_on()
    router_1.configure_port(port=1, ip_address="192.168.1.1", subnet_mask="255.255.255.0")
    router_1.configure_port(port=2, ip_address="192.168.10.1", subnet_mask="255.255.255.0")

    # Switch 1
    switch_1 = Switch(hostname="switch_1", num_ports=8)
    switch_1.power_on()
    network.connect(endpoint_a=router_1.ethernet_ports[1], endpoint_b=switch_1.switch_ports[8])
    router_1.enable_port(1)

    # Switch 2
    switch_2 = Switch(hostname="switch_2", num_ports=8)
    switch_2.power_on()
    network.connect(endpoint_a=router_1.ethernet_ports[2], endpoint_b=switch_2.switch_ports[8])
    router_1.enable_port(2)

    # Client 1
    client_1 = Computer(
        hostname="client_1", ip_address="192.168.10.21", subnet_mask="255.255.255.0", default_gateway="192.168.10.1"
    )
    client_1.power_on()
    network.connect(endpoint_b=client_1.ethernet_port[1], endpoint_a=switch_2.switch_ports[1])

    # Client 2
    client_2 = Computer(
        hostname="client_2", ip_address="192.168.10.22", subnet_mask="255.255.255.0", default_gateway="192.168.10.1"
    )
    client_2.power_on()
    network.connect(endpoint_b=client_2.ethernet_port[1], endpoint_a=switch_2.switch_ports[2])

    # Domain Controller
    domain_controller = Server(
        hostname="domain_controller",
        ip_address="192.168.1.10",
        subnet_mask="255.255.255.0",
        default_gateway="192.168.1.1",
    )
    domain_controller.power_on()
    network.connect(endpoint_b=domain_controller.ethernet_port[1], endpoint_a=switch_1.switch_ports[1])

    # Web Server
    web_server = Server(
        hostname="web_server", ip_address="192.168.1.12", subnet_mask="255.255.255.0", default_gateway="192.168.1.1"
    )
    web_server.power_on()
    network.connect(endpoint_b=web_server.ethernet_port[1], endpoint_a=switch_1.switch_ports[2])

    # Database Server
    database_server = Server(
        hostname="database_server",
        ip_address="192.168.1.14",
        subnet_mask="255.255.255.0",
        default_gateway="192.168.1.1",
    )
    database_server.power_on()
    network.connect(endpoint_b=database_server.ethernet_port[1], endpoint_a=switch_1.switch_ports[3])

    # Backup Server
    backup_server = Server(
        hostname="backup_server", ip_address="192.168.1.16", subnet_mask="255.255.255.0", default_gateway="192.168.1.1"
    )
    backup_server.power_on()
    network.connect(endpoint_b=backup_server.ethernet_port[1], endpoint_a=switch_1.switch_ports[4])

    # Security Suite
    security_suite = Server(
        hostname="security_suite",
        ip_address="192.168.1.110",
        subnet_mask="255.255.255.0",
        default_gateway="192.168.1.1",
    )
    security_suite.power_on()
    network.connect(endpoint_b=security_suite.ethernet_port[1], endpoint_a=switch_1.switch_ports[7])
    security_suite.connect_nic(NIC(ip_address="192.168.10.110", subnet_mask="255.255.255.0"))
    network.connect(endpoint_b=security_suite.ethernet_port[2], endpoint_a=switch_2.switch_ports[7])

    router_1.acl.add_rule(action=ACLAction.PERMIT, src_port=Port.ARP, dst_port=Port.ARP, position=22)

    router_1.acl.add_rule(action=ACLAction.PERMIT, protocol=IPProtocol.ICMP, position=23)

    return network
