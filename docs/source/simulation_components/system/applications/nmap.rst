.. only:: comment

    © Crown-owned copyright 2025, Defence Science and Technology Laboratory UK

.. _NMAP:

NMAP
####

Overview
========

The NMAP application is used to simulate network scanning activities. NMAP is a powerful tool that helps in discovering
hosts and services on a network. It provides functionalities such as ping scans to discover active hosts and port scans
to detect open ports on those hosts.

The NMAP application is essential for network administrators and security professionals to map out a network's
structure, identify active devices, and find potential vulnerabilities by discovering open ports and running services.
However, it is also a tool frequently used by attackers during the reconnaissance stage of a cyber attack to gather
information about the target network.

Scan Type
=========

Ping Scan
^^^^^^^^^

A ping scan is used to identify which hosts on a network are active and reachable. This is achieved by sending ICMP
Echo Request packets (ping) to the target IP addresses. If a host responds with an ICMP Echo Reply, it is considered
active. Ping scans are useful for quickly mapping out live hosts in a network.

Port Scan
^^^^^^^^^

A port scan is used to detect open ports on a target host or range of hosts. Open ports can indicate running services
that might be exploitable or require securing. Port scans help in understanding the services available on a network and
identifying potential entry points for attacks. There are three types of port scans based on the scope:

- **Horizontal Port Scan**: This scan targets a specific port across a range of IP addresses. It helps in identifying
  which hosts have a particular service running.

- **Vertical Port Scan**: This scan targets multiple ports on a single IP address. It provides detailed information
  about the services running on a specific host.

- **Box Scan**: This combines both horizontal and vertical scans, targeting multiple ports across multiple IP addresses.
  It gives a comprehensive view of the network's service landscape.

Example Usage
^^^^^^^^^^^^^

The network we use for these examples is defined below:

.. code-block:: python

    from ipaddress import IPv4Network

    from primaite.simulator.network.container import Network
    from primaite.simulator.network.hardware.nodes.host.computer import Computer
    from primaite.simulator.network.hardware.nodes.network.router import Router
    from primaite.simulator.network.hardware.nodes.network.switch import Switch
    from primaite.simulator.system.applications.nmap import NMAP
    from primaite.simulator.system.services.database.database_service import DatabaseService

    # Initialize the network
    network = Network()

    # Set up the router
    router = Router(hostname="router", start_up_duration=0)
    router.power_on()
    router.configure_port(port=1, ip_address="192.168.1.1", subnet_mask="255.255.255.0")

    # Set up PC 1
    pc_1 = Computer(config = {
        "hostname":"pc_1",
        "ip_address":"192.168.1.11",
        "subnet_mask":"255.255.255.0",
        "default_gateway":"192.168.1.1",
        "start_up_duration":0,
        }
    )
    pc_1.power_on()

    # Set up PC 2
    pc_2 = Computer(config = {
        "hostname":"pc_2",
        "ip_address":"192.168.1.12",
        "subnet_mask":"255.255.255.0",
        "default_gateway":"192.168.1.1",
        "start_up_duration":0,
        }
    )
    pc_2.power_on()
    pc_2.software_manager.install(DatabaseService)
    pc_2.software_manager.software["DatabaseService"].start() # start the postgres server

    # Set up PC 3
    pc_3 = Computer(config = {
        "hostname";"pc_3",
        "ip_address":"192.168.1.13",
        "subnet_mask":"255.255.255.0",
        "default_gateway":"192.168.1.1",
        "start_up_duration":0
    )
    # Don't power on PC 3

    # Set up the switch
    switch = Switch(config={"hostname":"switch", "start_up_duration":0})
    switch.power_on()

    # Connect devices
    network.connect(router.network_interface[1], switch.network_interface[24])
    network.connect(switch.network_interface[1], pc_1.network_interface[1])
    network.connect(switch.network_interface[2], pc_2.network_interface[1])
    network.connect(switch.network_interface[3], pc_3.network_interface[1])


    pc_1_nmap: NMAP = pc_1.software_manager.software["NMAP"]


Ping Scan
^^^^^^^^^

Perform a ping scan to find active hosts in the `192.168.1.0/24` subnet:

.. code-block:: python
   :caption: Ping Scan Code

    active_hosts = pc_1_nmap.ping_scan(target_ip_address=IPv4Network("192.168.1.0/24"))

.. code-block:: python
   :caption: Ping Scan Return Value

    [
        IPv4Address('192.168.1.11'),
        IPv4Address('192.168.1.12'),
        IPv4Address('192.168.1.1')
    ]

.. code-block:: text
   :caption: Ping Scan Output

    +-------------------------+
    |   pc_1 NMAP Ping Scan   |
    +--------------+----------+
    | IP Address   | Can Ping |
    +--------------+----------+
    | 192.168.1.1  | True     |
    | 192.168.1.11 | True     |
    | 192.168.1.12 | True     |
    +--------------+----------+

Horizontal Port Scan
^^^^^^^^^^^^^^^^^^^^

Perform a horizontal port scan on port 5432 across multiple IP addresses:

.. code-block:: python
   :caption: Horizontal Port Scan Code

    horizontal_scan_results = pc_1_nmap.port_scan(
        target_ip_address=[IPv4Address("192.168.1.12"), IPv4Address("192.168.1.13")],
        target_port=Port(5432 )
    )

.. code-block:: python
   :caption: Horizontal Port Scan Return Value

   {
      IPv4Address('192.168.1.12'): {
         <PROTOCOL_LOOKUP["TCP"]: 'tcp'>: [
            <PORT_LOOKUP["POSTGRES_SERVER"]: 5432>
         ]
      }
   }

.. code-block:: text
   :caption: Horizontal Port Scan Output

   +--------------------------------------------------+
   |         pc_1 NMAP Port Scan (Horizontal)         |
   +--------------+------+-----------------+----------+
   | IP Address   | Port | Name            | Protocol |
   +--------------+------+-----------------+----------+
   | 192.168.1.12 | 5432 | POSTGRES_SERVER | TCP      |
   +--------------+------+-----------------+----------+

Vertical Post Scan
^^^^^^^^^^^^^^^^^^

Perform a vertical port scan on multiple ports on a single IP address:

.. code-block:: python
   :caption: Vertical Port Scan Code

   vertical_scan_results = pc_1_nmap.port_scan(
       target_ip_address=[IPv4Address("192.168.1.12")],
       target_port=[21, 22, 80, 443]
   )

.. code-block:: python
   :caption: Vertical Port Scan Return Value

   {
      IPv4Address('192.168.1.12'): {
         <PROTOCOL_LOOKUP["TCP"]: 'tcp'>: [
            <PORT_LOOKUP["FTP"]: 21>,
            <PORT_LOOKUP["HTTP"]: 80>
         ]
      }
   }

.. code-block:: text
   :caption: Vertical Port Scan Output

   +---------------------------------------+
   |     pc_1 NMAP Port Scan (Vertical)    |
   +--------------+------+------+----------+
   | IP Address   | Port | Name | Protocol |
   +--------------+------+------+----------+
   | 192.168.1.12 | 21   | FTP  | TCP      |
   | 192.168.1.12 | 80   | HTTP | TCP      |
   +--------------+------+------+----------+

Box Scan
^^^^^^^^

Perform a box scan on multiple ports across multiple IP addresses:

.. code-block:: python
   :caption: Box Port Scan Code

   # Power PC 3 on before performing the box scan
   pc_3.power_on()


   box_scan_results = pc_1_nmap.port_scan(
       target_ip_address=[IPv4Address("192.168.1.12"), IPv4Address("192.168.1.13")],
       target_port=[21, 22, 80, 443]
   )

.. code-block:: python
   :caption: Box Port Scan Return Value

   {
      IPv4Address('192.168.1.13'): {
         <PROTOCOL_LOOKUP["TCP"]: 'tcp'>: [
            <PORT_LOOKUP["FTP"]: 21>,
            <PORT_LOOKUP["HTTP"]: 80>
         ]
      },
      IPv4Address('192.168.1.12'): {
         <PROTOCOL_LOOKUP["TCP"]: 'tcp'>: [
            <PORT_LOOKUP["FTP"]: 21>,
            <PORT_LOOKUP["HTTP"]: 80>
         ]
      }
   }

.. code-block:: text
   :caption: Box Port Scan Output

   +---------------------------------------+
   |       pc_1 NMAP Port Scan (Box)       |
   +--------------+------+------+----------+
   | IP Address   | Port | Name | Protocol |
   +--------------+------+------+----------+
   | 192.168.1.12 | 21   | FTP  | TCP      |
   | 192.168.1.12 | 80   | HTTP | TCP      |
   | 192.168.1.13 | 21   | FTP  | TCP      |
   | 192.168.1.13 | 80   | HTTP | TCP      |
   +--------------+------+------+----------+

Full Box Scan
^^^^^^^^^^^^^

Perform a full box scan on all ports, over both TCP and UDP, on a whole subnet:

.. code-block:: python
   :caption: Box Port Scan Code

   # Power PC 3 on before performing the full box scan
   pc_3.power_on()


   full_box_scan_results = pc_1_nmap.port_scan(
       target_ip_address=IPv4Network("192.168.1.0/24"),
   )

.. code-block:: python
   :caption: Box Port Scan Return Value

   {
      IPv4Address('192.168.1.11'): {
         <PROTOCOL_LOOKUP["UDP"]: 'udp'>: [
            <PORT_LOOKUP["ARP"]: 219>
         ]
      },
      IPv4Address('192.168.1.1'): {
         <PROTOCOL_LOOKUP["UDP"]: 'udp'>: [
            <PORT_LOOKUP["ARP"]: 219>
         ]
      },
      IPv4Address('192.168.1.12'): {
         <PROTOCOL_LOOKUP["TCP"]: 'tcp'>: [
            <PORT_LOOKUP["HTTP"]: 80>,
            <PORT_LOOKUP["DNS"]: 53>,
            <PORT_LOOKUP["POSTGRES_SERVER"]: 5432>,
            <PORT_LOOKUP["FTP"]: 21>
         ],
         <PROTOCOL_LOOKUP["UDP"]: 'udp'>: [
            <PORT_LOOKUP["NTP"]: 123>,
            <PORT_LOOKUP["ARP"]: 219>
         ]
      },
      IPv4Address('192.168.1.13'): {
         <PROTOCOL_LOOKUP["TCP"]: 'tcp'>: [
            <PORT_LOOKUP["HTTP"]: 80>,
            <PORT_LOOKUP["DNS"]: 53>,
            <PORT_LOOKUP["FTP"]: 21>
         ],
         <PROTOCOL_LOOKUP["UDP"]: 'udp'>: [
            <PORT_LOOKUP["NTP"]: 123>,
            <PORT_LOOKUP["ARP"]: 219>
         ]
      }
   }

.. code-block:: text
   :caption: Box Port Scan Output

   +--------------------------------------------------+
   |          pc_1 NMAP Port Scan (Box)               |
   +--------------+------+-----------------+----------+
   | IP Address   | Port | Name            | Protocol |
   +--------------+------+-----------------+----------+
   | 192.168.1.1  | 219  | ARP             | UDP      |
   | 192.168.1.11 | 219  | ARP             | UDP      |
   | 192.168.1.12 | 21   | FTP             | TCP      |
   | 192.168.1.12 | 53   | DNS             | TCP      |
   | 192.168.1.12 | 80   | HTTP            | TCP      |
   | 192.168.1.12 | 123  | NTP             | UDP      |
   | 192.168.1.12 | 219  | ARP             | UDP      |
   | 192.168.1.12 | 5432 | POSTGRES_SERVER | TCP      |
   | 192.168.1.13 | 21   | FTP             | TCP      |
   | 192.168.1.13 | 53   | DNS             | TCP      |
   | 192.168.1.13 | 80   | HTTP            | TCP      |
   | 192.168.1.13 | 123  | NTP             | UDP      |
   | 192.168.1.13 | 219  | ARP             | UDP      |
   +--------------+------+-----------------+----------+


``Common Attributes``
"""""""""""""""""""""

See :ref:`Common Configuration`
