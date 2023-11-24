from abc import abstractmethod
from enum import Enum
from typing import Any, Dict, Set

from primaite import getLogger
from primaite.simulator.system.software import IOSoftware, SoftwareHealthState

_LOGGER = getLogger(__name__)


class ApplicationOperatingState(Enum):
    """Enumeration of Application Operating States."""

    RUNNING = 1
    "The application is running."
    CLOSED = 2
    "The application is closed or not running."
    INSTALLING = 3
    "The application is being installed or updated."


class Application(IOSoftware):
    """
    Represents an Application in the simulation environment.

    Applications are user-facing programs that may perform input/output operations.
    """

    operating_state: ApplicationOperatingState = ApplicationOperatingState.CLOSED
    "The current operating state of the Application."
    execution_control_status: str = "manual"
    "Control status of the application's execution. It could be 'manual' or 'automatic'."
    num_executions: int = 0
    "The number of times the application has been executed. Default is 0."
    groups: Set[str] = set()
    "The set of groups to which the application belongs."

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.health_state_visible = SoftwareHealthState.UNUSED
        self.health_state_actual = SoftwareHealthState.UNUSED

    @abstractmethod
    def describe_state(self) -> Dict:
        """
        Produce a dictionary describing the current state of this object.

        Please see :py:meth:`primaite.simulator.core.SimComponent.describe_state` for a more detailed explanation.

        :return: Current state of this object and child objects.
        :rtype: Dict
        """
        state = super().describe_state()
        state.update(
            {
                "operating_state": self.operating_state.value,
                "execution_control_status": self.execution_control_status,
                "num_executions": self.num_executions,
                "groups": list(self.groups),
            }
        )
        return state

    def _can_perform_action(self) -> bool:
        """
        Checks if the application can perform actions.

        This is done by checking if the application is operating properly or the node it is installed
        in is operational.

        Returns true if the software can perform actions.
        """
        if not super()._can_perform_action():
            return False

        if self.operating_state is not self.operating_state.RUNNING:
            # service is not running
            _LOGGER.error(f"Cannot perform action: {self.name} is {self.operating_state.name}")
            return False

        return True

    def run(self) -> None:
        """Open the Application."""
        if not super()._can_perform_action():
            return

        if self.operating_state == ApplicationOperatingState.CLOSED:
            self.sys_log.info(f"Running Application {self.name}")
            self.operating_state = ApplicationOperatingState.RUNNING

    def close(self) -> None:
        """Close the Application."""
        if self.operating_state == ApplicationOperatingState.RUNNING:
            self.sys_log.info(f"Closed Application{self.name}")
            self.operating_state = ApplicationOperatingState.CLOSED

    def install(self) -> None:
        """Install Application."""
        if self._can_perform_action():
            return

        super().install()
        if self.operating_state == ApplicationOperatingState.CLOSED:
            self.sys_log.info(f"Installing Application {self.name}")
            self.operating_state = ApplicationOperatingState.INSTALLING

    def reset_component_for_episode(self, episode: int):
        """
        Resets the Application component for a new episode.

        This method ensures the Application is ready for a new episode, including resetting any
        stateful properties or statistics, and clearing any message queues.
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
        return super().receive(payload=payload, session_id=session_id, **kwargs)
