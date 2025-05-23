# © Crown-owned copyright 2025, Defence Science and Technology Laboratory UK
import json
from typing import List

import pytest
import yaml

from primaite.game.agent.observations import ApplicationObservation, ObservationManager, ServiceObservation
from primaite.game.agent.observations.file_system_observations import FileObservation, FolderObservation
from primaite.game.agent.observations.host_observations import HostObservation


class TestFileSystemRequiresScan:
    @pytest.mark.parametrize(
        ("yaml_option_string", "expected_val"),
        (
            ("file_system_requires_scan: true", True),
            ("file_system_requires_scan: false", False),
            (" ", True),
        ),
    )
    def test_obs_config(self, yaml_option_string, expected_val):
        """Check that the default behaviour is to set FileSystemRequiresScan to True."""
        obs_cfg_yaml = f"""
      type: custom
      options:
        components:
          - type: nodes
            label: NODES
            options:
              hosts:
                - hostname: domain_controller
                - hostname: web_server
                  services:
                    - service_name: web-server
                - hostname: database_server
                  folders:
                    - folder_name: database
                      files:
                      - file_name: database.db
                - hostname: backup_server
                - hostname: security_suite
                - hostname: client_1
                - hostname: client_2
              num_services: 1
              num_applications: 0
              num_folders: 1
              num_files: 1
              num_nics: 2
              include_num_access: false
              {yaml_option_string}
              include_nmne: true
              monitored_traffic:
                icmp:
                    - NONE
                tcp:
                    - DNS
              routers:
                - hostname: router_1
              num_ports: 0
              ip_list:
                - 192.168.1.10
                - 192.168.1.12
                - 192.168.1.14
                - 192.168.1.16
                - 192.168.1.110
                - 192.168.10.21
                - 192.168.10.22
                - 192.168.10.110
              wildcard_list:
                - 0.0.0.1
              port_list:
                - HTTP
                - POSTGRES_SERVER
              protocol_list:
                - ICMP
                - TCP
                - UDP
              num_rules: 10

          - type: links
            label: LINKS
            options:
              link_references:
                - router_1:eth-1<->switch_1:eth-8
                - router_1:eth-2<->switch_2:eth-8
                - switch_1:eth-1<->domain_controller:eth-1
                - switch_1:eth-2<->web_server:eth-1
                - switch_1:eth-3<->database_server:eth-1
                - switch_1:eth-4<->backup_server:eth-1
                - switch_1:eth-7<->security_suite:eth-1
                - switch_2:eth-1<->client_1:eth-1
                - switch_2:eth-2<->client_2:eth-1
                - switch_2:eth-7<->security_suite:eth-2
          - type: "none"
            label: ICS
            options: {{}}

        """

        cfg = yaml.safe_load(obs_cfg_yaml)
        manager = ObservationManager(config=cfg)

        hosts: List[HostObservation] = manager.obs.components["NODES"].hosts
        for i, host in enumerate(hosts):
            folders: List[FolderObservation] = host.folders
            for j, folder in enumerate(folders):
                assert folder.file_system_requires_scan == expected_val  # Make sure folders require scan by default
                files: List[FileObservation] = folder.files
                for k, file in enumerate(files):
                    assert file.file_system_requires_scan == expected_val

    def test_file_require_scan(self):
        file_state = {"health_status": 3, "visible_status": 1}

        obs_requiring_scan = FileObservation([], include_num_access=False, file_system_requires_scan=True)
        assert obs_requiring_scan.observe(file_state)["health_status"] == 1

        obs_not_requiring_scan = FileObservation([], include_num_access=False, file_system_requires_scan=False)
        assert obs_not_requiring_scan.observe(file_state)["health_status"] == 3

    def test_folder_require_scan(self):
        folder_state = {"health_status": 3, "visible_status": 1, "scanned_this_step": False}

        obs_requiring_scan = FolderObservation(
            [], files=[], num_files=0, include_num_access=False, file_system_requires_scan=True
        )
        assert obs_requiring_scan.observe(folder_state)["health_status"] == 0

        obs_not_requiring_scan = FolderObservation(
            [], files=[], num_files=0, include_num_access=False, file_system_requires_scan=False
        )
        assert obs_not_requiring_scan.observe(folder_state)["health_status"] == 3

        folder_state = {"health_status": 3, "visible_status": 1, "scanned_this_step": True}
        obs_requiring_scan = FolderObservation(
            [], files=[], num_files=0, include_num_access=False, file_system_requires_scan=True
        )
        assert obs_requiring_scan.observe(folder_state)["health_status"] == 1


class TestServicesRequiresScan:
    @pytest.mark.parametrize(
        ("yaml_option_string", "expected_val"),
        (
            ("services_requires_scan: true", True),
            ("services_requires_scan: false", False),
            (" ", True),
        ),
    )
    def test_obs_config(self, yaml_option_string, expected_val):
        """Check that the default behaviour is to set service_requires_scan to True."""
        obs_cfg_yaml = f"""
      type: custom
      options:
        components:
          - type: nodes
            label: NODES
            options:
              hosts:
                - hostname: domain_controller
                - hostname: web_server
                  services:
                    - service_name: web-server
                    - service_name: dns-client
                - hostname: database_server
                  folders:
                    - folder_name: database
                      files:
                      - file_name: database.db
                - hostname: backup_server
                  services:
                    - service_name: ftp-server
                - hostname: security_suite
                - hostname: client_1
                - hostname: client_2
              num_services: 3
              num_applications: 0
              num_folders: 1
              num_files: 1
              num_nics: 2
              include_num_access: false
              {yaml_option_string}
              include_nmne: true
              monitored_traffic:
                icmp:
                    - NONE
                tcp:
                    - DNS
              routers:
                - hostname: router_1
              num_ports: 0
              ip_list:
                - 192.168.1.10
                - 192.168.1.12
                - 192.168.1.14
                - 192.168.1.16
                - 192.168.1.110
                - 192.168.10.21
                - 192.168.10.22
                - 192.168.10.110
              wildcard_list:
                - 0.0.0.1
              port_list:
                - 80
                - 5432
              protocol_list:
                - ICMP
                - TCP
                - UDP
              num_rules: 10

          - type: links
            label: LINKS
            options:
              link_references:
                - router_1:eth-1<->switch_1:eth-8
                - router_1:eth-2<->switch_2:eth-8
                - switch_1:eth-1<->domain_controller:eth-1
                - switch_1:eth-2<->web_server:eth-1
                - switch_1:eth-3<->database_server:eth-1
                - switch_1:eth-4<->backup_server:eth-1
                - switch_1:eth-7<->security_suite:eth-1
                - switch_2:eth-1<->client_1:eth-1
                - switch_2:eth-2<->client_2:eth-1
                - switch_2:eth-7<->security_suite:eth-2
          - type: none
            label: ICS
            options: {{}}

        """

        cfg = yaml.safe_load(obs_cfg_yaml)
        manager = ObservationManager.from_config(cfg)

        hosts: List[HostObservation] = manager.obs.components["NODES"].hosts
        for i, host in enumerate(hosts):
            services: List[ServiceObservation] = host.services
            for j, service in enumerate(services):
                val = service.services_requires_scan
                print(f"host {i} service {j} {val}")
                assert val == expected_val  # Make sure services require scan by default

    def test_services_requires_scan(self):
        state = {"health_state_actual": 3, "health_state_visible": 1, "operating_state": 1}

        obs_requiring_scan = ServiceObservation([], services_requires_scan=True)
        assert obs_requiring_scan.observe(state)["health_status"] == 1  # should be visible value

        obs_not_requiring_scan = ServiceObservation([], services_requires_scan=False)
        assert obs_not_requiring_scan.observe(state)["health_status"] == 3  # should be actual value


class TestApplicationsRequiresScan:
    @pytest.mark.parametrize(
        ("yaml_option_string", "expected_val"),
        (
            ("applications_requires_scan: true", True),
            ("applications_requires_scan: false", False),
            (" ", True),
        ),
    )
    def test_obs_config(self, yaml_option_string, expected_val):
        """Check that the default behaviour is to set applications_requires_scan to True."""
        obs_cfg_yaml = f"""
      type: custom
      options:
        components:
          - type: nodes
            label: NODES
            options:
              hosts:
                - hostname: domain_controller
                - hostname: web_server
                - hostname: database_server
                  folders:
                    - folder_name: database
                      files:
                      - file_name: database.db
                - hostname: backup_server
                - hostname: security_suite
                - hostname: client_1
                  applications:
                    - application_name: web-browser
                - hostname: client_2
                  applications:
                    - application_name: web-browser
                    - application_name: database-client
              num_services: 0
              num_applications: 3
              num_folders: 1
              num_files: 1
              num_nics: 2
              include_num_access: false
              {yaml_option_string}
              include_nmne: true
              monitored_traffic:
                icmp:
                    - NONE
                tcp:
                    - DNS
              routers:
                - hostname: router_1
              num_ports: 0
              ip_list:
                - 192.168.1.10
                - 192.168.1.12
                - 192.168.1.14
                - 192.168.1.16
                - 192.168.1.110
                - 192.168.10.21
                - 192.168.10.22
                - 192.168.10.110
              wildcard_list:
                - 0.0.0.1
              port_list:
                - 80
                - 5432
              protocol_list:
                - ICMP
                - TCP
                - UDP
              num_rules: 10

          - type: links
            label: LINKS
            options:
              link_references:
                - router_1:eth-1<->switch_1:eth-8
                - router_1:eth-2<->switch_2:eth-8
                - switch_1:eth-1<->domain_controller:eth-1
                - switch_1:eth-2<->web_server:eth-1
                - switch_1:eth-3<->database_server:eth-1
                - switch_1:eth-4<->backup_server:eth-1
                - switch_1:eth-7<->security_suite:eth-1
                - switch_2:eth-1<->client_1:eth-1
                - switch_2:eth-2<->client_2:eth-1
                - switch_2:eth-7<->security_suite:eth-2
          - type: none
            label: ICS
            options: {{}}

        """

        cfg = yaml.safe_load(obs_cfg_yaml)
        manager = ObservationManager.from_config(cfg)

        hosts: List[HostObservation] = manager.obs.components["NODES"].hosts
        for i, host in enumerate(hosts):
            services: List[ServiceObservation] = host.services
            for j, service in enumerate(services):
                val = service.services_requires_scan
                print(f"host {i} service {j} {val}")
                assert val == expected_val  # Make sure applications require scan by default

    def test_applications_requires_scan(self):
        state = {"health_state_actual": 3, "health_state_visible": 1, "operating_state": 1, "num_executions": 1}

        obs_requiring_scan = ApplicationObservation([], applications_requires_scan=True)
        assert obs_requiring_scan.observe(state)["health_status"] == 1  # should be visible value

        obs_not_requiring_scan = ApplicationObservation([], applications_requires_scan=False)
        assert obs_not_requiring_scan.observe(state)["health_status"] == 3  # should be actual value
