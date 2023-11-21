from ipaddress import IPv4Address
from typing import Dict, Optional

from primaite import getLogger
from primaite.simulator.network.protocols.ntp import NTPPacket, NTPRequest
from primaite.simulator.network.transmission.network_layer import IPProtocol
from primaite.simulator.network.transmission.transport_layer import Port
from primaite.simulator.system.services.service import Service, ServiceOperatingState

_LOGGER = getLogger(__name__)


class NTPClient(Service):
    """Represents a NTP client as a service."""

    ip_addr: Optional[IPv4Address] = None
    ntp_server: Optional[IPv4Address] = None
    "The NTP server the client sends requests to."

    def __init__(self, **kwargs):
        kwargs["name"] = "NTPClient"
        kwargs["port"] = Port.NTP
        kwargs["protocol"] = IPProtocol.UDP
        super().__init__(**kwargs)
        self.start()

    def describe_state(self) -> Dict:
        """
        Describes the current state of the software.

        The specifics of the software's state, including its health, criticality,
        and any other pertinent information, should be implemented in subclasses.

        :return: A dictionary containing key-value pairs representing the current state
        of the software.
        :rtype: Dict
        """
        state = super().describe_state()
        return state

    def reset_component_for_episode(self, episode: int):
        """
        Resets the Service component for a new episode.

        This method ensures the Service is ready for a new episode, including resetting any
        stateful properties or statistics, and clearing any message queues.
        """
        pass

    def send(
        self,
        payload: NTPPacket,
        session_id: Optional[str] = None,
        dest_ip_address: IPv4Address = ntp_server,
        dest_port: [Port] = Port.NTP,
        **kwargs,
    ) -> bool:
        """Requests NTP data from NTP server.

        :param payload: The payload to be sent.
        :param session_id: The Session ID the payload is to originate from. Optional.
        :param dest_ip_address: The ip address of the payload destination.
        :param dest_port: The port of the payload destination.

        :return: True if successful, False otherwise.
        """
        self.sys_log.info(f"{self.name}: Sending NTP request {payload.ntp_request.ntp_client}")

        return super().send(
            payload=payload,
            dest_ip_address=dest_ip_address,
            dest_port=dest_port,
            session_id=session_id,
            **kwargs,
        )

    def receive(
        self,
        payload: NTPPacket,
        session_id: Optional[str] = None,
        **kwargs,
    ) -> bool:
        """Receives time data from server.

        :param payload: The payload to be sent.
        :param session_id: The Session ID the payload is to originate from. Optional.
        :return: True if successful, False otherwise.
        """
        if not (isinstance(payload, NTPPacket) and payload.ntp_request.ntp_client):
            _LOGGER.debug(f"{payload} is not a NTPPacket")
            return False
        if payload.ntp_reply.ntp_datetime:
            self.sys_log.info(
                f"{self.name}: Received time \
                              update from NTP server{payload.ntp_reply.ntp_datetime}"
            )
            return True

    def apply_timestep(self, timestep: int) -> None:
        """
        For each timestep request the time from the NTP server.

        In this instance, if any multi-timestep processes are currently
        occurring (such as restarting or installation), then they are brought one step closer to
        being finished.

        :param timestep: The current timestep number. (Amount of time since simulation episode began)
        :type timestep: int
        """
        super().apply_timestep(timestep)
        if self.operating_state == ServiceOperatingState.RUNNING:
            # request time from server
            ntp_request = NTPRequest(ntp_client=self.ip_addr)
            ntp_server_packet = NTPPacket(ntp_request=ntp_request)
            self.send(payload=ntp_server_packet)
            return True
        else:
            self.sys_log.debug(f"{self.name} ntp client not running")
            return False
