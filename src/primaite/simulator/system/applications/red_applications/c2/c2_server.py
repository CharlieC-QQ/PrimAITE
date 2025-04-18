# © Crown-owned copyright 2025, Defence Science and Technology Laboratory UK
from typing import Dict, Optional

from prettytable import MARKDOWN, PrettyTable
from pydantic import Field, validate_call

from primaite.interface.request import RequestFormat, RequestResponse
from primaite.simulator.core import RequestManager, RequestType
from primaite.simulator.network.protocols.masquerade import C2Packet
from primaite.simulator.system.applications.red_applications.c2 import (
    CommandOpts,
    ExfilOpts,
    RansomwareOpts,
    TerminalOpts,
)
from primaite.simulator.system.applications.red_applications.c2.abstract_c2 import AbstractC2, C2Command, C2Payload


class C2Server(AbstractC2, discriminator="c2-server"):
    """
    C2 Server Application.

    Represents a vendor generic C2 Server used in conjunction with the C2 beacon
    to simulate malicious communications and infrastructure within primAITE.

    The C2 Server must be installed and be in a running state before it's able to receive
    red agent actions and send commands to the C2 beacon.

    Extends the Abstract C2 application to include the following:

    1. Sending commands to the C2 Beacon. (Command input)
    2. Parsing terminal RequestResponses back to the Agent.

    Please refer to the Command-and-Control notebook for an in-depth example of the C2 Suite.
    """

    class ConfigSchema(AbstractC2.ConfigSchema):
        """ConfigSchema for C2Server."""

        type: str = "c2-server"

    config: ConfigSchema = Field(default_factory=lambda: C2Server.ConfigSchema())

    current_command_output: RequestResponse = None
    """The Request Response by the last command send. This attribute is updated by the method _handle_command_output."""

    def _init_request_manager(self) -> RequestManager:
        """
        Initialise the request manager.

        More information in user guide and docstring for SimComponent._init_request_manager.
        """
        rm = super()._init_request_manager()

        def _configure_ransomware_action(request: RequestFormat, context: Dict) -> RequestResponse:
            """Requests - Sends a RANSOMWARE_CONFIGURE C2Command to the C2 Beacon with the given parameters.

            :param request: Request with one element containing a dict of parameters for the configure method.
            :type request: RequestFormat
            :param context: additional context for resolving this action, currently unused
            :type context: dict
            :return: RequestResponse object with a success code reflecting whether the configuration could be applied.
            :rtype: RequestResponse
            """
            command_payload = {
                "server_ip_address": request[-1].get("server_ip_address"),
                "payload": request[-1].get("payload"),
            }
            return self.send_command(given_command=C2Command.RANSOMWARE_CONFIGURE, command_options=command_payload)

        def _launch_ransomware_action(request: RequestFormat, context: Dict) -> RequestResponse:
            """Agent Action - Sends a RANSOMWARE_LAUNCH C2Command to the C2 Beacon with the given parameters.

            :param request: Request with one element containing a dict of parameters for the configure method.
            :type request: RequestFormat
            :param context: additional context for resolving this action, currently unused
            :type context: dict
            :return: RequestResponse object with a success code reflecting whether the ransomware was launched.
            :rtype: RequestResponse
            """
            return self.send_command(given_command=C2Command.RANSOMWARE_LAUNCH, command_options={})

        def _data_exfiltration_action(request: RequestFormat, context: Dict) -> RequestResponse:
            """Agent Action - Sends a Data Exfiltration C2Command to the C2 Beacon with the given parameters.

            :param request: Request with one element containing a dict of parameters for the configure method.
            :type request: RequestFormat
            :param context: additional context for resolving this action, currently unused
            :type context: dict
            :return: RequestResponse object with a success code reflecting whether the ransomware was launched.
            :rtype: RequestResponse
            """
            command_payload = request[-1]
            return self.send_command(given_command=C2Command.DATA_EXFILTRATION, command_options=command_payload)

        def _remote_terminal_action(request: RequestFormat, context: Dict) -> RequestResponse:
            """Agent Action - Sends a TERMINAL C2Command to the C2 Beacon with the given parameters.

            :param request: Request with one element containing a dict of parameters for the configure method.
            :type request: RequestFormat
            :param context: additional context for resolving this action, currently unused
            :type context: dict
            :return: RequestResponse object with a success code reflecting whether the ransomware was launched.
            :rtype: RequestResponse
            """
            command_payload = request[-1]
            return self.send_command(given_command=C2Command.TERMINAL, command_options=command_payload)

        rm.add_request(
            name="ransomware_configure",
            request_type=RequestType(func=_configure_ransomware_action),
        )
        rm.add_request(
            name="ransomware_launch",
            request_type=RequestType(func=_launch_ransomware_action),
        )
        rm.add_request(
            name="terminal_command",
            request_type=RequestType(func=_remote_terminal_action),
        )
        rm.add_request(
            name="exfiltrate",
            request_type=RequestType(func=_data_exfiltration_action),
        )
        return rm

    def __init__(self, **kwargs):
        kwargs["name"] = "c2-server"
        super().__init__(**kwargs)
        self.run()

    def _handle_command_output(self, payload: C2Packet) -> bool:
        """
        Handles the parsing of C2 Command Output from C2 Traffic (Masquerade Packets).

        Parses the Request Response from the given C2Packet's payload attribute (Inherited from Data packet).
        This RequestResponse is then stored in the C2 Server class attribute self.current_command_output.

        If the payload attribute does not contain a RequestResponse, then an error will be raised in syslog and
        the self.current_command_output is updated to reflect the error.

        :param payload: The OUTPUT C2 Payload
        :type payload: C2Packet
        :return: Returns True if the self.current_command_output was updated, false otherwise.
        :rtype Bool:
        """
        self.sys_log.info(f"{self.name}: Received command response from C2 Beacon: {payload}.")
        command_output = payload.payload
        if not isinstance(command_output, RequestResponse):
            self.sys_log.warning(f"{self.name}: C2 Server received invalid command response: {command_output}.")
            self.current_command_output = RequestResponse(
                status="failure", data={"Reason": "Received unexpected C2 Response."}
            )
            return False

        self.current_command_output = command_output
        return True

    def _handle_keep_alive(self, payload: C2Packet, session_id: Optional[str]) -> bool:
        """
        Handles receiving and sending keep alive payloads. This method is only called if we receive a keep alive.

        Abstract method inherited from abstract C2.

        In the C2 Server implementation of this method the following logic is performed:

        1. The ``self.c2_connection_active`` is set to True. (Indicates that we're received a connection)
        2. The received keep alive (Payload parameter) is then resolved by _resolve_keep_alive.
        3. After the keep alive is resolved, a keep alive is sent back to confirm connection.

        This is because the C2 Server is the listener and thus will only ever receive packets from
        the C2 Beacon rather than the other way around.

        The C2 Beacon/Server communication is akin to that of a real-world reverse shells.

        Returns False if a keep alive was unable to be sent.
        Returns True if a keep alive was successfully sent or already has been sent this timestep.

        :param payload: The Keep Alive payload received.
        :type payload: C2Packet
        :param session_id: The transport session_id that the payload originates from.
        :type session_id: str
        :return: True if the keep alive was successfully handled, false otherwise.
        :rtype: Bool
        """
        self.sys_log.info(f"{self.name}: Keep Alive Received. Attempting to resolve the remote connection details.")

        self.c2_connection_active = True  # Sets the connection to active
        self.c2_session = self.software_manager.session_manager.sessions_by_uuid[session_id]

        if self._resolve_keep_alive(payload, session_id) == False:
            self.sys_log.warning(f"{self.name}: Keep Alive Could not be resolved correctly. Refusing Keep Alive.")
            return False

        self.sys_log.info(f"{self.name}: Remote connection successfully established: {self.c2_remote_connection}.")
        self.sys_log.debug(f"{self.name}: Attempting to send Keep Alive response back to {self.c2_remote_connection}.")

        # If this method returns true then we have sent successfully sent a keep alive response back.
        return self._send_keep_alive(session_id)

    @validate_call
    def send_command(self, given_command: C2Command, command_options: Dict) -> RequestResponse:
        """
        Sends a C2 command to the C2 Beacon using the given parameters.

        C2 Command           | Command Synopsis
        ---------------------|------------------------
        RANSOMWARE_CONFIGURE | Configures an installed ransomware script based on the passed parameters.
        RANSOMWARE_LAUNCH    | Launches the installed ransomware script.
        DATA_EXFILTRATION    | Utilises the FTP Service to exfiltrate data back to the C2 Server.
        TERMINAL             | Executes a command via the terminal installed on the C2 Beacons Host.

        Currently, these commands leverage the pre-existing capability of other applications.
        However, the commands are sent via the network rather than the game layer which
        grants more opportunity to the blue agent to prevent attacks.

        Additionally, future editions of primAITE may expand the C2 repertoire to allow for
        more complex red agent behaviour such as establishing further fall back channels
        or introduce red applications that are only installable via C2 Servers. (T1105)

        For more information on the impact of these commands please refer to the terminal
        and the ransomware applications.

        :param given_command: The C2 command to be sent to the C2 Beacon.
        :type given_command: C2Command.
        :param command_options: The relevant C2 Beacon parameters.
        :type command_options: Dict
        :return: Returns the Request Response of the C2 Beacon's host terminal service execute method.
        :rtype: RequestResponse
        """
        if not isinstance(given_command, C2Command):
            self.sys_log.warning(f"{self.name}: Received unexpected C2 command. Unable to send command.")
            return RequestResponse(
                status="failure", data={"Reason": "Received unexpected C2Command. Unable to send command."}
            )

        connection_status: tuple[bool, RequestResponse] = self._check_connection()

        if connection_status[0] is False:
            return connection_status[1]

        setup_success, command_options = self._command_setup(given_command, command_options)

        if setup_success is False:
            self.sys_log.warning(
                f"{self.name}: Failed to perform necessary C2 Server setup for given command: {given_command}."
            )
            return RequestResponse(
                status="failure", data={"Reason": "Failed to perform necessary C2 Server setup for given command."}
            )

        self.sys_log.info(f"{self.name}: Attempting to send command {given_command}.")
        command_packet = self._craft_packet(
            c2_payload=C2Payload.INPUT, c2_command=given_command, command_options=command_options.model_dump()
        )

        if self.send(
            payload=command_packet,
            dest_ip_address=self.c2_remote_connection,
            session_id=self.c2_session.uuid,
            dest_port=self.config.masquerade_port,
            ip_protocol=self.config.masquerade_protocol,
        ):
            self.sys_log.info(f"{self.name}: Successfully sent {given_command}.")
            self.sys_log.info(f"{self.name}: Awaiting command response {given_command}.")

        # If the command output was handled currently, the self.current_command_output will contain the RequestResponse.
        if self.current_command_output is None:
            return RequestResponse(
                status="failure", data={"Reason": "Command sent to the C2 Beacon but no response was ever received."}
            )
        return self.current_command_output

    def _command_setup(self, given_command: C2Command, command_options: dict) -> tuple[bool, CommandOpts]:
        """
        Performs any necessary C2 Server setup needed to perform certain commands.

        This includes any option validation and any other required setup.

        The following table details any C2 Server prequisites for following commands.

        C2 Command           | Command Service/Application Requirements
        ---------------------|-----------------------------------------
        RANSOMWARE_CONFIGURE | N/A
        RANSOMWARE_LAUNCH    | N/A
        DATA_EXFILTRATION    | FTP Server & File system folder
        TERMINAL             | N/A

        Currently, only the data exfiltration command require the C2 Server
        to perform any necessary setup. Specifically, the Data Exfiltration command requires
        the C2 Server to have an running FTP Server service as well as a folder for
        storing any exfiltrated data.

        :param given_command: Any C2 Command.
        :type given_command: C2Command.
        :param command_options: The relevant command parameters.
        :type command_options: Dict
        :returns: Tuple containing a success bool if the setup was successful and the validated c2 opts.
        :rtype: tuple[bool, CommandOpts]
        """
        server_setup_success: bool = True

        if given_command == C2Command.DATA_EXFILTRATION:  # Data exfiltration setup
            # Validating command options
            command_options = ExfilOpts.model_validate(command_options)
            if self._host_ftp_server is None:
                self.sys_log.warning(f"{self.name}: Unable to setup the FTP Server for data exfiltration")
                server_setup_success = False

            if self.get_exfiltration_folder(command_options.exfiltration_folder_name) is None:
                self.sys_log.warning(f"{self.name}: Unable to create a folder for storing exfiltration data.")
                server_setup_success = False

        if given_command == C2Command.TERMINAL:
            # Validating command options
            command_options = TerminalOpts.model_validate(command_options)

        if given_command == C2Command.RANSOMWARE_CONFIGURE:
            # Validating command options
            command_options = RansomwareOpts.model_validate(command_options)

        if given_command == C2Command.RANSOMWARE_LAUNCH:
            # Validating command options
            command_options = CommandOpts.model_validate(command_options)

        return [server_setup_success, command_options]

    def _confirm_remote_connection(self, timestep: int) -> bool:
        """Checks the suitability of the current C2 Beacon connection.

        Inherited Abstract Method.

        If a C2 Server has not received a keep alive within the current set
        keep alive frequency (self._keep_alive_frequency) then the C2 beacons
        connection is considered dead and any commands will be rejected.

        This method is called on each timestep (Called by .apply_timestep)

        :param timestep: The current timestep of the simulation.
        :type timestep: Int
        :return: Returns False if the C2 beacon is considered dead. Otherwise True.
        :rtype bool:
        """
        if self.keep_alive_inactivity > self.config.keep_alive_frequency:
            self.sys_log.info(f"{self.name}: C2 Beacon connection considered dead due to inactivity.")
            self.sys_log.debug(
                f"{self.name}: Did not receive expected keep alive connection from {self.c2_remote_connection}"
                f"{self.name}: Expected at timestep: {timestep} due to frequency: {self.config.keep_alive_frequency}"
                f"{self.name}: Last Keep Alive received at {(timestep - self.keep_alive_inactivity)}"
            )
            self._reset_c2_connection()
            return False
        return True

    # Abstract method inherited from abstract C2.
    # C2 Servers do not currently receive any input commands from the C2 beacon.
    def _handle_command_input(self, payload: C2Packet) -> None:
        """Defining this method (Abstract method inherited from abstract C2) in order to instantiate the class.

        C2 Servers currently do not receive input commands coming from the C2 Beacons.

        :param payload: The incoming C2Packet
        :type payload: C2Packet.
        """
        self.sys_log.warning(f"{self.name}: C2 Server received an unexpected INPUT payload: {payload}")
        pass

    def show(self, markdown: bool = False):
        """
        Prints a table of the current C2 attributes on a C2 Server.

        Displays the current values of the following C2 attributes:

        ``C2 Connection Active``:
        If the C2 Server has established connection with a C2 Beacon.

        ``C2 Remote Connection``:
        The IP of the C2 Beacon. (Configured by upon receiving a keep alive.)

        ``Current Masquerade Protocol``:
        The current protocol that the C2 Traffic is using. (e.g TCP/UDP)

        ``Current Masquerade Port``:
        The current port that the C2 Traffic is using. (e.g HTTP (Port 80))

        :param markdown: If True, outputs the table in markdown format. Default is False.
        """
        table = PrettyTable(
            ["C2 Connection Active", "C2 Remote Connection", "Current Masquerade Protocol", "Current Masquerade Port"]
        )
        if markdown:
            table.set_style(MARKDOWN)
        table.align = "l"
        table.title = f"{self.name} Running Status"
        table.add_row(
            [
                self.c2_connection_active,
                self.c2_remote_connection,
                self.config.masquerade_protocol,
                self.config.masquerade_port,
            ]
        )
        print(table)
