# © Crown-owned copyright 2025, Defence Science and Technology Laboratory UK
"""PrimAITE game - Encapsulates the simulation and agents."""
from typing import Dict, List, Optional, Union

import numpy as np
from pydantic import BaseModel, ConfigDict

from primaite import DEFAULT_BANDWIDTH, getLogger
from primaite.game.agent.interface import AbstractAgent, ProxyAgent
from primaite.game.agent.observations import NICObservation
from primaite.game.agent.rewards import SharedReward
from primaite.game.science import graph_has_cycle, topological_sort
from primaite.simulator import SIM_OUTPUT
from primaite.simulator.network.creation import NetworkNodeAdder
from primaite.simulator.network.hardware.base import NetworkInterface, Node, NodeOperatingState, UserManager
from primaite.simulator.network.hardware.nodes.host.host_node import NIC
from primaite.simulator.network.hardware.nodes.network.firewall import Firewall  # noqa: F401
from primaite.simulator.network.hardware.nodes.network.switch import Switch
from primaite.simulator.network.hardware.nodes.network.wireless_router import WirelessRouter
from primaite.simulator.network.nmne import NMNEConfig
from primaite.simulator.sim_container import Simulation
from primaite.simulator.system.applications.application import Application
from primaite.simulator.system.applications.database_client import DatabaseClient  # noqa: F401
from primaite.simulator.system.applications.red_applications.c2.c2_beacon import C2Beacon  # noqa: F401
from primaite.simulator.system.applications.red_applications.c2.c2_server import C2Server  # noqa: F401
from primaite.simulator.system.applications.red_applications.data_manipulation_bot import (  # noqa: F401
    DataManipulationBot,
)
from primaite.simulator.system.applications.red_applications.dos_bot import DoSBot  # noqa: F401
from primaite.simulator.system.applications.red_applications.ransomware_script import RansomwareScript  # noqa: F401
from primaite.simulator.system.applications.web_browser import WebBrowser  # noqa: F401
from primaite.simulator.system.services.database.database_service import DatabaseService
from primaite.simulator.system.services.dns.dns_client import DNSClient
from primaite.simulator.system.services.dns.dns_server import DNSServer
from primaite.simulator.system.services.ftp.ftp_client import FTPClient
from primaite.simulator.system.services.ftp.ftp_server import FTPServer
from primaite.simulator.system.services.ntp.ntp_client import NTPClient
from primaite.simulator.system.services.ntp.ntp_server import NTPServer
from primaite.simulator.system.services.service import Service
from primaite.simulator.system.services.terminal.terminal import Terminal
from primaite.simulator.system.services.web_server.web_server import WebServer
from primaite.simulator.system.software import Software
from primaite.utils.validation.ip_protocol import IPProtocol
from primaite.utils.validation.port import Port, PORT_LOOKUP

_LOGGER = getLogger(__name__)

SERVICE_TYPES_MAPPING = {
    "dns-client": DNSClient,
    "dns-server": DNSServer,
    "database-service": DatabaseService,
    "web-server": WebServer,
    "ftp-client": FTPClient,
    "ftp-server": FTPServer,
    "ntp-client": NTPClient,
    "ntp-server": NTPServer,
    "terminal": Terminal,
}
"""List of available services that can be installed on nodes in the PrimAITE Simulation."""


class PrimaiteGameOptions(BaseModel):
    """
    Global options which are applicable to all of the agents in the game.

    Currently this is used to restrict which ports and protocols exist in the world of the simulation.
    """

    model_config = ConfigDict(extra="forbid")

    seed: int = None
    """Random number seed for RNGs."""
    generate_seed_value: bool = False
    """Internally generated seed value."""
    max_episode_length: int = 256
    """Maximum number of episodes for the PrimAITE game."""
    ports: List[Port]
    """A whitelist of available ports in the simulation."""
    protocols: List[IPProtocol]
    """A whitelist of available protocols in the simulation."""
    thresholds: Optional[Dict] = {}
    """A dict containing the thresholds used for determining what is acceptable during observations."""


class PrimaiteGame:
    """
    Primaite game encapsulates the simulation and agents which interact with it.

    Provides main logic loop for the game. However, it does not provide policy training, or a gymnasium environment.
    """

    def __init__(self):
        """Initialise a PrimaiteGame object."""
        self.simulation: Simulation = Simulation()
        """Simulation object with which the agents will interact."""

        self.agents: Dict[str, AbstractAgent] = {}
        """Mapping from agent name to agent object."""

        self.rl_agents: Dict[str, ProxyAgent] = {}
        """Subset of agents which are intended for reinforcement learning."""

        self.step_counter: int = 0
        """Current timestep within the episode."""

        self.options: PrimaiteGameOptions
        """Special options that apply for the entire game."""

        self.save_step_metadata: bool = False
        """Whether to save the RL agents' action, environment state, and other data at every single step."""

        self._reward_calculation_order: List[str] = [name for name in self.agents]
        """Agent order for reward evaluation, as some rewards can be dependent on other agents' rewards."""

    def step(self):
        """
        Perform one step of the simulation/agent loop.

        This is the main loop of the game. It corresponds to one timestep in the simulation, and one action from each
        agent. The steps are as follows:
            1. The simulation state is updated.
            2. The simulation state is sent to each agent.
            3. Each agent converts the state to an observation and calculates a reward.
            4. Each agent chooses an action based on the observation.
            5. Each agent converts the action to a request.
            6. The simulation applies the requests.

        Warning: This method should only be used with scripted agents. For RL agents, the environment that the agent
        interacts with should implement a step method that calls methods used by this method. For example, if using a
        single-agent gym, make sure to update the ProxyAgent's action with the action before calling
        ``self.apply_agent_actions()``.
        """
        _LOGGER.debug(f"Stepping. Step counter: {self.step_counter}")

        self.pre_timestep()

        if self.step_counter == 0:
            state = self.get_sim_state()
            for agent in self.agents.values():
                agent.update_observation(state=state)
        # Apply all actions to simulation as requests
        self.apply_agent_actions()

        # Advance timestep
        self.advance_timestep()

        # Get the current state of the simulation
        sim_state = self.get_sim_state()

        # Update agents' observations and rewards based on the current state, and the response from the last action
        self.update_agents(state=sim_state)

    def get_sim_state(self) -> Dict:
        """Get the current state of the simulation."""
        return self.simulation.describe_state()

    def update_agents(self, state: Dict) -> None:
        """Update agents' observations and rewards based on the current state."""
        for agent_name in self._reward_calculation_order:
            agent = self.agents[agent_name]
            if self.step_counter > 0:  # can't get reward before first action
                agent.update_reward(state=state)
                agent.save_reward_to_history()
            agent.update_observation(state=state)  # order of this doesn't matter so just use reward order
            agent.reward_function.total_reward += agent.reward_function.current_reward

    def apply_agent_actions(self) -> None:
        """Apply all actions to simulation as requests."""
        for _, agent in self.agents.items():
            obs = agent.observation_manager.current_observation
            action_choice, parameters = agent.get_action(obs, timestep=self.step_counter)
            if SIM_OUTPUT.save_agent_logs:
                agent.logger.debug(f"Chosen Action: {action_choice}")
            request = agent.format_request(action_choice, parameters)
            response = self.simulation.apply_request(request)
            agent.process_action_response(
                timestep=self.step_counter,
                action=action_choice,
                parameters=parameters,
                request=request,
                response=response,
                observation=obs,
            )

    def pre_timestep(self) -> None:
        """Apply any pre-timestep logic that helps make sure we have the correct observations."""
        self.simulation.pre_timestep(self.step_counter)

    def advance_timestep(self) -> None:
        """Advance timestep."""
        self.step_counter += 1
        _LOGGER.debug(f"Advancing timestep to {self.step_counter} ")
        self.update_agent_loggers()
        self.simulation.apply_timestep(self.step_counter)

    def update_agent_loggers(self) -> None:
        """Updates Agent Loggers with new timestep."""
        for agent in self.agents.values():
            agent.logger.update_timestep(self.step_counter)

    def calculate_truncated(self) -> bool:
        """Calculate whether the episode is truncated."""
        current_step = self.step_counter
        max_steps = self.options.max_episode_length
        if current_step >= max_steps:
            return True
        return False

    def action_mask(self, agent_name: str) -> np.ndarray:
        """
        Return the action mask for the agent.

        This is a boolean list corresponding to the agent's action space. A False entry means this action cannot be
        performed during this step.

        :return: Action mask
        :rtype: List[bool]
        """
        agent = self.agents[agent_name]
        mask = [True] * len(agent.action_manager.action_map)
        for i, action in agent.action_manager.action_map.items():
            request = agent.action_manager.form_request(action_identifier=action[0], action_options=action[1])
            mask[i] = self.simulation._request_manager.check_valid(request, {})
        return np.asarray(mask, dtype=np.int8)

    def close(self) -> None:
        """Close the game, this will close the simulation."""
        return NotImplemented

    def setup_for_episode(self, episode: int) -> None:
        """Perform any final configuration of components to make them ready for the game to start."""
        self.simulation.setup_for_episode(episode=episode)

    @classmethod
    def from_config(cls, cfg: Dict) -> "PrimaiteGame":
        """Create a PrimaiteGame object from a config dictionary.

        The config dictionary should have the following top-level keys:
        1. io_settings: options for logging data during training
        2. game_config: options for the game itself, such as agents.
        3. simulation: defines the network topology and the initial state of the simulation.

        The specification for each of the three major areas is described in a separate documentation page.
        # TODO: create documentation page and add links to it here.

        :param cfg: The config dictionary.
        :type cfg: dict
        :return: A PrimaiteGame object.
        :rtype: PrimaiteGame
        """
        game = cls()
        game.options = PrimaiteGameOptions(**cfg["game"])
        game.save_step_metadata = cfg.get("io_settings", {}).get("save_step_metadata") or False

        # 1. create simulation
        sim = game.simulation
        net = sim.network

        simulation_config = cfg.get("simulation", {})
        defaults_config = cfg.get("defaults", {})
        network_config = simulation_config.get("network", {})
        airspace_cfg = network_config.get("airspace", {})
        frequency_max_capacity_mbps_cfg = airspace_cfg.get("frequency_max_capacity_mbps", {})
        net.airspace.set_frequency_max_capacity_mbps(frequency_max_capacity_mbps_cfg)

        nodes_cfg = network_config.get("nodes", [])
        links_cfg = network_config.get("links", [])
        node_sets_cfg = network_config.get("node_sets", [])
        # Set the NMNE capture config
        NetworkInterface.nmne_config = NMNEConfig(**network_config.get("nmne_config", {}))
        NICObservation.capture_nmne = NMNEConfig(**network_config.get("nmne_config", {})).capture_nmne

        for node_cfg in nodes_cfg:
            n_type = node_cfg["type"]

            new_node = None
            if n_type in Node._registry:
                n_class = Node._registry[n_type]
                if issubclass(n_class, WirelessRouter):
                    new_node = n_class.from_config(config=node_cfg, airspace=net.airspace)
                else:
                    new_node = Node._registry[n_type].from_config(config=node_cfg)
            else:
                msg = f"invalid node type {n_type} in config"
                _LOGGER.error(msg)
                raise ValueError(msg)

            # TODO: handle simulation defaults more cleanly
            if "node_start_up_duration" in defaults_config:
                new_node.config.start_up_duration = defaults_config["node_startup_duration"]
            if "node_shut_down_duration" in defaults_config:
                new_node.config.shut_down_duration = defaults_config["node_shut_down_duration"]
            if "node_scan_duration" in defaults_config:
                new_node.config.node_scan_duration = defaults_config["node_scan_duration"]
            if "folder_scan_duration" in defaults_config:
                new_node.file_system._default_folder_scan_duration = defaults_config["folder_scan_duration"]
            if "folder_restore_duration" in defaults_config:
                new_node.file_system._default_folder_restore_duration = defaults_config["folder_restore_duration"]

            if "users" in node_cfg and new_node.software_manager.software.get("user-manager"):
                user_manager: UserManager = new_node.software_manager.software["user-manager"]  # noqa

                for user_cfg in node_cfg["users"]:
                    user_manager.add_user(**user_cfg, bypass_can_perform_action=True)

            def _set_software_listen_on_ports(software: Union[Software, Service], software_cfg: Dict):
                """Set listener ports on software."""
                listen_on_ports = []
                for port_id in set(software_cfg.get("options", {}).get("listen_on_ports", [])):
                    port = None
                    if isinstance(port_id, int):
                        port = port_id
                    elif isinstance(port_id, str):
                        port = PORT_LOOKUP[port_id]
                    if port:
                        listen_on_ports.append(port)
                software.listen_on_ports = set(listen_on_ports)

            if "services" in node_cfg:
                for service_cfg in node_cfg["services"]:
                    new_service = None
                    service_type = service_cfg["type"]

                    service_class = None
                    # Handle extended services
                    if service_type.lower() in Service._registry:
                        service_class = Service._registry[service_type.lower()]
                    elif service_type in SERVICE_TYPES_MAPPING:
                        service_class = SERVICE_TYPES_MAPPING[service_type]

                    if service_class is not None:
                        _LOGGER.debug(f"installing {service_type} on node {new_node.config.hostname}")
                        new_node.software_manager.install(service_class, software_config=service_cfg.get("options", {}))
                        new_service = new_node.software_manager.software[service_type]

                        # fixing duration for the service
                        if "fixing_duration" in service_cfg.get("options", {}):
                            new_service.config.fixing_duration = service_cfg["options"]["fixing_duration"]

                        _set_software_listen_on_ports(new_service, service_cfg)
                        # start the service
                        new_service.start()
                    else:
                        msg = f"Configuration contains an invalid service type: {service_type}"
                        _LOGGER.error(msg)
                        raise ValueError(msg)

                    # TODO: handle simulation defaults more cleanly
                    if "service_fix_duration" in defaults_config:
                        new_service.config.fixing_duration = defaults_config["service_fix_duration"]
                    if "service_restart_duration" in defaults_config:
                        new_service.restart_duration = defaults_config["service_restart_duration"]
                    if "service_install_duration" in defaults_config:
                        new_service.install_duration = defaults_config["service_install_duration"]

            if "applications" in node_cfg:
                for application_cfg in node_cfg["applications"]:
                    new_application = None
                    application_type = application_cfg["type"]

                    if application_type in Application._registry:
                        application_class = Application._registry[application_type]
                        application_options = application_cfg.get("options", {})
                        application_options["type"] = application_type
                        new_node.software_manager.install(application_class, software_config=application_options)
                        new_application = new_node.software_manager.software[application_type]  # grab the instance

                    else:
                        msg = f"Configuration contains an invalid application type: {application_type}"
                        _LOGGER.error(msg)
                        raise ValueError(msg)

                    # run the application
                    new_application.run()

            if "network_interfaces" in node_cfg:
                for nic_num, nic_cfg in node_cfg["network_interfaces"].items():
                    new_node.connect_nic(NIC(ip_address=nic_cfg["ip_address"], subnet_mask=nic_cfg["subnet_mask"]))

            # temporarily set to 0 so all nodes are initially on
            new_node.config.start_up_duration = 0
            new_node.config.shut_down_duration = 0

            net.add_node(new_node)
            # run through the power on step if the node is to be turned on at the start
            if new_node.operating_state == NodeOperatingState.ON:
                new_node.power_on()

            # set start up and shut down duration
            new_node.config.start_up_duration = int(node_cfg.get("start_up_duration", 3))
            new_node.config.shut_down_duration = int(node_cfg.get("shut_down_duration", 3))

        # 1.1 Create Node Sets
        for node_set_cfg in node_sets_cfg:
            NetworkNodeAdder.from_config(node_set_cfg, network=net)

        # 2. create links between nodes
        for link_cfg in links_cfg:
            node_a = net.get_node_by_hostname(link_cfg["endpoint_a_hostname"])
            node_b = net.get_node_by_hostname(link_cfg["endpoint_b_hostname"])
            bandwidth = link_cfg.get("bandwidth", DEFAULT_BANDWIDTH)  # default value if not configured

            if isinstance(node_a, Switch):
                endpoint_a = node_a.network_interface[link_cfg["endpoint_a_port"]]
            else:
                endpoint_a = node_a.network_interface[link_cfg["endpoint_a_port"]]
            if isinstance(node_b, Switch):
                endpoint_b = node_b.network_interface[link_cfg["endpoint_b_port"]]
            else:
                endpoint_b = node_b.network_interface[link_cfg["endpoint_b_port"]]
            net.connect(endpoint_a=endpoint_a, endpoint_b=endpoint_b, bandwidth=bandwidth)

        # 3. create agents
        agents_cfg = cfg.get("agents", [])

        for agent_cfg in agents_cfg:
            agent_cfg = {**agent_cfg, "thresholds": game.options.thresholds}
            new_agent = AbstractAgent.from_config(agent_cfg)
            game.agents[agent_cfg["ref"]] = new_agent
            if isinstance(new_agent, ProxyAgent):
                game.rl_agents[agent_cfg["ref"]] = new_agent

        # Validate that if any agents are sharing rewards, they aren't forming an infinite loop.
        game.setup_reward_sharing()

        game.update_agents(game.get_sim_state())
        return game

    def setup_reward_sharing(self):
        """Do necessary setup to enable reward sharing between agents.

        This method ensures that there are no cycles in the reward sharing. A cycle would be for example if agent_1
        depends on agent_2 and agent_2 depends on agent_1. It would cause an infinite loop.

        Also, SharedReward requires us to pass it a callback method that will provide the reward of the agent who is
        sharing their reward. This callback is provided by this setup method.

        Finally, this method sorts the agents in order in which rewards will be evaluated to make sure that any rewards
        that rely on the value of another reward are evaluated later.

        :raises RuntimeError: If the reward sharing is specified with a cyclic dependency.
        """
        # construct dependency graph in the reward sharing between agents.
        graph = {}
        for name, agent in self.agents.items():
            graph[name] = set()
            for comp, weight in agent.reward_function.reward_components:
                if isinstance(comp, SharedReward):
                    comp: SharedReward
                    graph[name].add(comp.config.agent_name)

                    # while constructing the graph, we might as well set up the reward sharing itself.
                    comp.callback = lambda agent_name: self.agents[agent_name].reward_function.current_reward

        # make sure the graph is acyclic. Otherwise we will enter an infinite loop of reward sharing.
        if graph_has_cycle(graph):
            raise RuntimeError(
                (
                    "Detected cycle in agent reward sharing. Check the agent reward function ",
                    "configuration: reward sharing can only go one way.",
                )
            )

        # sort the agents so the rewards that depend on other rewards are always evaluated later
        self._reward_calculation_order = topological_sort(graph)
