# © Crown-owned copyright 2024, Defence Science and Technology Laboratory UK
from typing import Dict, Optional

from prettytable import MARKDOWN, PrettyTable
from pydantic import validate_call

from primaite.interface.request import RequestFormat, RequestResponse
from primaite.simulator.core import RequestManager, RequestType
from primaite.simulator.network.protocols.masquerade import MasqueradePacket
from primaite.simulator.system.applications.red_applications.c2.abstract_c2 import AbstractC2, C2Command, C2Payload


class C2Server(AbstractC2, identifier="C2Server"):
    """
    C2 Server Application.

    Represents a vendor generic C2 Server is used in conjunction with the C2 beacon
    to simulate malicious communications and infrastructure within primAITE.

    The C2 Server must be installed and be in a running state before it's able to receive
    red agent actions and send commands to the C2 beacon.

    Extends the Abstract C2 application to include the following:

    1. Sending commands to the C2 Beacon. (Command input)
    2. Parsing terminal RequestResponses back to the Agent.
    """

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
            ransomware_config = {
                "server_ip_address": request[-1].get("server_ip_address"),
                "payload": request[-1].get("payload"),
            }
            return self._send_command(given_command=C2Command.RANSOMWARE_CONFIGURE, command_options=ransomware_config)

        def _launch_ransomware_action(request: RequestFormat, context: Dict) -> RequestResponse:
            """Agent Action - Sends a RANSOMWARE_LAUNCH C2Command to the C2 Beacon with the given parameters.

            :param request: Request with one element containing a dict of parameters for the configure method.
            :type request: RequestFormat
            :param context: additional context for resolving this action, currently unused
            :type context: dict
            :return: RequestResponse object with a success code reflecting whether the ransomware was launched.
            :rtype: RequestResponse
            """
            return self._send_command(given_command=C2Command.RANSOMWARE_LAUNCH, command_options={})

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
            return self._send_command(given_command=C2Command.TERMINAL, command_options=command_payload)

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
        return rm

    def __init__(self, **kwargs):
        kwargs["name"] = "C2Server"
        super().__init__(**kwargs)

    def _handle_command_output(self, payload: MasqueradePacket) -> bool:
        """
        Handles the parsing of C2 Command Output from C2 Traffic (Masquerade Packets).

        Parses the Request Response within MasqueradePacket's payload attribute (Inherited from Data packet).
        The class attribute self.current_command_output is then set to this Request Response.

        If the payload attribute does not contain a RequestResponse, then an error will be raised in syslog and
        the self.current_command_output is updated to reflect the error.

        :param payload: The OUTPUT C2 Payload
        :type payload: MasqueradePacket
        :return: Returns True if the self.current_command_output is currently updated, false otherwise.
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

    def _handle_keep_alive(self, payload: MasqueradePacket, session_id: Optional[str]) -> bool:
        """
        Handles receiving and sending keep alive payloads. This method is only called if we receive a keep alive.

        In the C2 Server implementation of this method the c2 connection active boolean
        is set to true and the keep alive inactivity is reset after receiving one keep alive.

        This is because the C2 Server is the listener and thus will only ever receive packets from
        the C2 Beacon rather than the other way around. (The C2 Beacon is akin to a reverse shell)

        Returns False if a keep alive was unable to be sent.
        Returns True if a keep alive was successfully sent or already has been sent this timestep.

        :param payload: The Keep Alive payload received.
        :type payload: MasqueradePacket
        :param session_id: The transport session_id that the payload is originating from.
        :type session_id: str
        :return: True if successfully handled, false otherwise.
        :rtype: Bool
        """
        self.sys_log.info(f"{self.name}: Keep Alive Received. Attempting to resolve the remote connection details.")

        self.c2_connection_active = True  # Sets the connection to active
        self.current_c2_session = self.software_manager.session_manager.sessions_by_uuid[session_id]

        if self._resolve_keep_alive(payload, session_id) == False:
            self.sys_log.warning(f"{self.name}: Keep Alive Could not be resolved correctly. Refusing Keep Alive.")
            return False

        # If this method returns true then we have sent successfully sent a keep alive.
        self.sys_log.info(f"{self.name}: Remote connection successfully established: {self.c2_remote_connection}.")
        self.sys_log.debug(f"{self.name}: Attempting to send Keep Alive response back to {self.c2_remote_connection}.")

        return self._send_keep_alive(session_id)

    @validate_call
    def _send_command(self, given_command: C2Command, command_options: Dict) -> RequestResponse:
        """
        Sends a command to the C2 Beacon.

        Currently, these commands leverage the pre-existing capability of other applications.
        However, the commands are sent via the network rather than the game layer which
        grants more opportunity to the blue agent to prevent attacks.

        Additionally, future editions of primAITE may expand the C2 repertoire to allow for
        more complex red agent behaviour such as file extraction, establishing further fall back channels
        or introduce red applications that are only installable via C2 Servers. (T1105)

        C2 Command           | Meaning
        ---------------------|------------------------
        RANSOMWARE_CONFIGURE | Configures an installed ransomware script based on the passed parameters.
        RANSOMWARE_LAUNCH    | Launches the installed ransomware script.
        TERMINAL             | Executes a command via the terminal installed on the C2 Beacons Host.

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

        if self._can_perform_network_action == False:
            self.sys_log.warning(f"{self.name}: Unable to make leverage networking resources. Rejecting Command.")
            return RequestResponse(
                status="failure", data={"Reason": "Unable to access networking resources. Unable to send command."}
            )

        if self.c2_remote_connection is False:
            self.sys_log.warning(f"{self.name}: C2 Beacon has yet to establish connection. Rejecting command.")
            return RequestResponse(
                status="failure", data={"Reason": "C2 Beacon has yet to establish connection. Unable to send command."}
            )

        if self.current_c2_session is None:
            self.sys_log.warning(f"{self.name}: C2 Beacon cannot be reached. Rejecting command.")
            return RequestResponse(
                status="failure", data={"Reason": "C2 Beacon cannot be reached. Unable to send command."}
            )

        self.sys_log.info(f"{self.name}: Attempting to send command {given_command}.")
        command_packet = self._craft_packet(given_command=given_command, command_options=command_options)

        if self.send(
            payload=command_packet,
            dest_ip_address=self.c2_remote_connection,
            session_id=self.current_c2_session.uuid,
            dest_port=self.current_masquerade_port,
            ip_protocol=self.current_masquerade_protocol,
        ):
            self.sys_log.info(f"{self.name}: Successfully sent {given_command}.")
            self.sys_log.info(f"{self.name}: Awaiting command response {given_command}.")

        # If the command output was handled currently, the self.current_command_output will contain the RequestResponse.
        return self.current_command_output

    # TODO: Probably could move this as a class method in MasqueradePacket.
    def _craft_packet(self, given_command: C2Command, command_options: Dict) -> MasqueradePacket:
        """
        Creates and returns a Masquerade Packet using the arguments given.

        Creates Masquerade Packet with a payload_type INPUT C2Payload.

        :param given_command: The C2 command to be sent to the C2 Beacon.
        :type given_command: C2Command.
        :param command_options: The relevant C2 Beacon parameters.F
        :type command_options: Dict
        :return: Returns the construct MasqueradePacket
        :rtype: MasqueradePacket
        """
        constructed_packet = MasqueradePacket(
            masquerade_protocol=self.current_masquerade_protocol,
            masquerade_port=self.current_masquerade_port,
            payload_type=C2Payload.INPUT,
            command=given_command,
            payload=command_options,
        )
        return constructed_packet

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
                self.current_masquerade_protocol,
                self.current_masquerade_port,
            ]
        )
        print(table)

    # Abstract method inherited from abstract C2 - Not currently utilised.
    def _handle_command_input(self, payload: MasqueradePacket) -> None:
        """Defining this method (Abstract method inherited from abstract C2) in order to instantiate the class.

        C2 Servers currently do not receive input commands coming from the C2 Beacons.

        :param payload: The incoming MasqueradePacket
        :type payload: MasqueradePacket.
        """
        self.sys_log.warning(f"{self.name}: C2 Server received an unexpected INPUT payload: {payload}")
        pass
