# © Crown-owned copyright 2025, Defence Science and Technology Laboratory UK
from enum import IntEnum
from ipaddress import IPv4Address
from typing import Dict, Optional

from pydantic import Field

from primaite import getLogger
from primaite.game.science import simulate_trial
from primaite.interface.request import RequestResponse
from primaite.simulator.core import RequestManager, RequestType
from primaite.simulator.system.applications.application import Application
from primaite.simulator.system.applications.database_client import DatabaseClient, DatabaseClientConnection
from primaite.utils.validation.ip_protocol import PROTOCOL_LOOKUP
from primaite.utils.validation.ipv4_address import IPV4Address
from primaite.utils.validation.port import PORT_LOOKUP

_LOGGER = getLogger(__name__)


class DataManipulationAttackStage(IntEnum):
    """
    Enumeration representing different stages of a data manipulation attack.

    This enumeration defines the various stages a data manipulation attack can be in during its lifecycle in the
    simulation. Each stage represents a specific phase in the attack process.
    """

    NOT_STARTED = 0
    "Indicates that the attack has not started yet."
    LOGON = 1
    "The stage where logon procedures are simulated."
    PORT_SCAN = 2
    "Represents the stage of performing a horizontal port scan on the target."
    ATTACKING = 3
    "Stage of actively attacking the target."
    SUCCEEDED = 4
    "Indicates the attack has been successfully completed."
    FAILED = 5
    "Signifies that the attack has failed."


class DataManipulationBot(Application, discriminator="data-manipulation-bot"):
    """A bot that simulates a script which performs a SQL injection attack."""

    class ConfigSchema(Application.ConfigSchema):
        """Configuration schema for DataManipulationBot."""

        type: str = "data-manipulation-bot"
        server_ip: Optional[IPV4Address] = None
        server_password: Optional[str] = None
        payload: str = "DELETE"
        port_scan_p_of_success: float = 0.1
        data_manipulation_p_of_success: float = 0.1
        repeat: bool = True

    config: "DataManipulationBot.ConfigSchema" = Field(default_factory=lambda: DataManipulationBot.ConfigSchema())

    payload: Optional[str] = None
    port_scan_p_of_success: float = 0.1
    data_manipulation_p_of_success: float = 0.1

    attack_stage: DataManipulationAttackStage = DataManipulationAttackStage.NOT_STARTED
    repeat: bool = False
    "Whether to repeat attacking once finished."

    def __init__(self, **kwargs):
        kwargs["name"] = "data-manipulation-bot"
        kwargs["port"] = PORT_LOOKUP["NONE"]
        kwargs["protocol"] = PROTOCOL_LOOKUP["NONE"]

        super().__init__(**kwargs)
        self._db_connection: Optional[DatabaseClientConnection] = None

        self.server_ip_address = self.config.server_ip
        self.server_password = self.config.server_password
        self.payload = self.config.payload
        self.port_scan_p_of_success = self.config.port_scan_p_of_success
        self.data_manipulation_p_of_success = self.config.data_manipulation_p_of_success
        self.repeat = self.config.repeat

    def describe_state(self) -> Dict:
        """
        Produce a dictionary describing the current state of this object.

        Please see :py:meth:`primaite.simulator.core.SimComponent.describe_state` for a more detailed explanation.

        :return: Current state of this object and child objects.
        :rtype: Dict
        """
        state = super().describe_state()
        return state

    @property
    def _host_db_client(self) -> DatabaseClient:
        """Return the database client that is installed on the same machine as the DataManipulationBot."""
        db_client = self.software_manager.software.get("database-client")
        if db_client is None:
            self.sys_log.warning(f"{self.__class__.__name__} cannot find a database client on its host.")
        return db_client

    def _init_request_manager(self) -> RequestManager:
        """
        Initialise the request manager.

        More information in user guide and docstring for SimComponent._init_request_manager.
        """
        rm = super()._init_request_manager()

        rm.add_request(
            name="execute",
            request_type=RequestType(func=lambda request, context: RequestResponse.from_bool(self.attack())),
        )

        return rm

    def configure(
        self,
        server_ip_address: IPv4Address,
        server_password: Optional[str] = None,
        payload: Optional[str] = None,
        port_scan_p_of_success: float = 0.1,
        data_manipulation_p_of_success: float = 0.1,
        repeat: bool = True,
    ):
        """
        Configure the DataManipulatorBot to communicate with a DatabaseService.

        :param server_ip_address: The IP address of the Node the DatabaseService is on.
        :param server_password: The password on the DatabaseService.
        :param payload: The data manipulation query payload.
        :param port_scan_p_of_success: The probability of success for the port scan stage.
        :param data_manipulation_p_of_success: The probability of success for the data manipulation stage.
        :param repeat: Whether to repeat attacking once finished.
        """
        self.server_ip_address = server_ip_address
        self.server_password = server_password
        self.payload = payload
        self.port_scan_p_of_success = port_scan_p_of_success
        self.data_manipulation_p_of_success = data_manipulation_p_of_success
        self.repeat = repeat
        self.sys_log.info(
            f"{self.name}: Configured the {self.name} with {server_ip_address=}, {payload=}, {server_password=}, "
            f"{repeat=}."
        )

    def _logon(self):
        """
        Simulate the logon process as the initial stage of the attack.

        Advances the attack stage to `LOGON` if successful.
        """
        if self.attack_stage == DataManipulationAttackStage.NOT_STARTED:
            # Bypass this stage as we're not dealing with logon for now
            self.sys_log.debug(f"{self.name}: ")
            self.attack_stage = DataManipulationAttackStage.LOGON

    def _perform_port_scan(self, p_of_success: Optional[float] = 0.1):
        """
        Perform a simulated port scan to check for open SQL ports.

        Advances the attack stage to `PORT_SCAN` if successful.

        :param p_of_success: Probability of successful port scan, by default 0.1.
        """
        if self.attack_stage == DataManipulationAttackStage.LOGON:
            # perform a port scan to identify that the SQL port is open on the server
            if simulate_trial(p_of_success):
                self.sys_log.info(f"{self.name}: Performing port scan")
                # perform the port scan
                port_is_open = True  # Temporary; later we can implement NMAP port scan.
                if port_is_open:
                    self.sys_log.debug(f"{self.name}: ")
                    self.attack_stage = DataManipulationAttackStage.PORT_SCAN

    def _establish_db_connection(self) -> bool:
        """Establish a db connection to the Database Server."""
        self._db_connection = self._host_db_client.get_new_connection()
        return True if self._db_connection else False

    def _perform_data_manipulation(self, p_of_success: Optional[float] = 0.1):
        """
        Execute the data manipulation attack on the target.

        Advances the attack stage to `COMPLETE` if successful, or 'FAILED' if unsuccessful.

        :param p_of_success: Probability of successfully performing data manipulation, by default 0.1.
        """
        if self._host_db_client is None:
            self.attack_stage = DataManipulationAttackStage.FAILED
            return

        self._host_db_client.server_ip_address = self.server_ip_address
        self._host_db_client.server_password = self.server_password
        if self.attack_stage == DataManipulationAttackStage.PORT_SCAN:
            # perform the actual data manipulation attack
            if simulate_trial(p_of_success):
                self.sys_log.info(f"{self.name}: Performing data manipulation")
                # perform the attack
                if not self._db_connection:
                    self._establish_db_connection()
                if self._db_connection:
                    attack_successful = self._db_connection.query(self.payload)
                    self.sys_log.info(f"{self.name} payload delivered: {self.payload}")
                    if attack_successful:
                        self.sys_log.info(f"{self.name}: Data manipulation successful")
                        self.attack_stage = DataManipulationAttackStage.SUCCEEDED
                    else:
                        self.sys_log.warning(f"{self.name}: Data manipulation failed")
                        self.attack_stage = DataManipulationAttackStage.FAILED

    def run(self):
        """
        Run the Data Manipulation Bot.

        Calls the parent classes execute method before starting the application loop.
        """
        super().run()

    def attack(self) -> bool:
        """Perform the attack steps after opening the application."""
        if not self._can_perform_action():
            self.sys_log.warning(
                "Data manipulation application attempted to execute but it cannot perform actions right now."
            )
            self.run()

        self.num_executions += 1
        return self._application_loop()

    def _application_loop(self) -> bool:
        """
        The main application loop of the bot, handling the attack process.

        This is the core loop where the bot sequentially goes through the stages of the attack.
        """
        if not self._can_perform_action():
            return False
        if self.server_ip_address and self.payload:
            self.sys_log.debug(f"{self.name}: Running")
            self._logon()
            self._perform_port_scan(p_of_success=self.port_scan_p_of_success)
            self._perform_data_manipulation(p_of_success=self.data_manipulation_p_of_success)

            if self.repeat and self.attack_stage in (
                DataManipulationAttackStage.SUCCEEDED,
                DataManipulationAttackStage.FAILED,
            ):
                self.attack_stage = DataManipulationAttackStage.NOT_STARTED

            return True

        else:
            self.sys_log.warning(f"{self.name}: Failed to start as it requires both a target_ip_address and payload.")
            return False

    def apply_timestep(self, timestep: int) -> None:
        """
        Apply a timestep to the bot, triggering the application loop.

        :param timestep: The timestep value to update the bot's state.
        """
        pass
