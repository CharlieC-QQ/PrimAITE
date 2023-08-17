from abc import abstractmethod
from enum import Enum
from typing import Any, Dict, List

from primaite.simulator.system.software import IOSoftware


class ServiceOperatingState(Enum):
    """Enumeration of Service Operating States."""

    RUNNING = 1
    "The service is currently running."
    STOPPED = 2
    "The service is not running."
    INSTALLING = 3
    "The service is being installed or updated."
    RESTARTING = 4
    "The service is in the process of restarting."
    PAUSED = 5
    "The service is temporarily paused."
    DISABLED = 6
    "The service is disabled and cannot be started."


class Service(IOSoftware):
    """
    Represents a Service in the simulation environment.

    Services are programs that run in the background and may perform input/output operations.
    """

    operating_state: ServiceOperatingState
    "The current operating state of the Service."

    @abstractmethod
    def describe_state(self) -> Dict:
        """
        Produce a dictionary describing the current state of this object.

        Please see :py:meth:`primaite.simulator.core.SimComponent.describe_state` for a more detailed explanation.

        :return: Current state of this object and child objects.
        :rtype: Dict
        """
        pass

    def apply_action(self, action: List[str]) -> None:
        """
        Applies a list of actions to the Service.

        :param action: A list of actions to apply.
        """
        pass

    def reset_component_for_episode(self, episode: int):
        """
        Resets the Service component for a new episode.

        This method ensures the Service is ready for a new episode, including resetting any
        stateful properties or statistics, and clearing any message queues.
        """
        pass

    def send(self, payload: Any, session_id: str, **kwargs) -> bool:
        """
        Sends a payload to the SessionManager.

        The specifics of how the payload is processed and whether a response payload
        is generated should be implemented in subclasses.

        :param payload: The payload to send.
        :return: True if successful, False otherwise.
        """
        pass

    def receive(self, payload: Any, session_id: str, **kwargs) -> bool:
        """
        Receives a payload from the SessionManager.

        The specifics of how the payload is processed and whether a response payload
        is generated should be implemented in subclasses.

        :param payload: The payload to receive.
        :return: True if successful, False otherwise.
        """
        pass
