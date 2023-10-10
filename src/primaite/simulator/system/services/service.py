from enum import Enum
from typing import Dict, Optional

from primaite import getLogger
from primaite.simulator.core import RequestManager, RequestType
from primaite.simulator.system.software import IOSoftware

_LOGGER = getLogger(__name__)


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

    operating_state: ServiceOperatingState = ServiceOperatingState.STOPPED
    "The current operating state of the Service."

    visible_operating_state: ServiceOperatingState = ServiceOperatingState.STOPPED
    "The visible operating state of the service."

    restart_duration: int = 5
    "How many timesteps does it take to restart this service."
    _restart_countdown: Optional[int] = None
    "If currently restarting, how many timesteps remain until the restart is finished."

    def _init_request_manager(self) -> RequestManager:
        am = super()._init_request_manager()
        am.add_request("scan", RequestType(func=lambda request, context: self.scan()))
        am.add_request("stop", RequestType(func=lambda request, context: self.stop()))
        am.add_request("start", RequestType(func=lambda request, context: self.start()))
        am.add_request("pause", RequestType(func=lambda request, context: self.pause()))
        am.add_request("resume", RequestType(func=lambda request, context: self.resume()))
        am.add_request("restart", RequestType(func=lambda request, context: self.restart()))
        am.add_request("disable", RequestType(func=lambda request, context: self.disable()))
        am.add_request("enable", RequestType(func=lambda request, context: self.enable()))
        return am

    def describe_state(self) -> Dict:
        """
        Produce a dictionary describing the current state of this object.

        Please see :py:meth:`primaite.simulator.core.SimComponent.describe_state` for a more detailed explanation.

        :return: Current state of this object and child objects.
        :rtype: Dict
        """
        state = super().describe_state()
        state.update({"operating_state": self.operating_state.name})
        return state

    def reset_component_for_episode(self, episode: int):
        """
        Resets the Service component for a new episode.

        This method ensures the Service is ready for a new episode, including resetting any
        stateful properties or statistics, and clearing any message queues.
        """
        pass

    def scan(self) -> None:
        """Update the service visible states."""
        # update parent states
        super().scan()

        # update the visible operating state
        self.visible_operating_state = self.operating_state

    def stop(self) -> None:
        """Stop the service."""
        if self.operating_state in [ServiceOperatingState.RUNNING, ServiceOperatingState.PAUSED]:
            self.sys_log.info(f"Stopping service {self.name}")
            self.operating_state = ServiceOperatingState.STOPPED

    def start(self, **kwargs) -> None:
        """Start the service."""
        if self.operating_state == ServiceOperatingState.STOPPED:
            self.sys_log.info(f"Starting service {self.name}")
            self.operating_state = ServiceOperatingState.RUNNING

    def pause(self) -> None:
        """Pause the service."""
        if self.operating_state == ServiceOperatingState.RUNNING:
            self.sys_log.info(f"Pausing service {self.name}")
            self.operating_state = ServiceOperatingState.PAUSED

    def resume(self) -> None:
        """Resume paused service."""
        if self.operating_state == ServiceOperatingState.PAUSED:
            self.sys_log.info(f"Resuming service {self.name}")
            self.operating_state = ServiceOperatingState.RUNNING

    def restart(self) -> None:
        """Restart running service."""
        if self.operating_state in [ServiceOperatingState.RUNNING, ServiceOperatingState.PAUSED]:
            self.sys_log.info(f"Pausing service {self.name}")
            self.operating_state = ServiceOperatingState.RESTARTING
            self.restart_countdown = self.restarting_duration

    def disable(self) -> None:
        """Disable the service."""
        self.sys_log.info(f"Disabling Application {self.name}")
        self.operating_state = ServiceOperatingState.DISABLED

    def enable(self) -> None:
        """Enable the disabled service."""
        if self.operating_state == ServiceOperatingState.DISABLED:
            self.sys_log.info(f"Enabling Application {self.name}")
            self.operating_state = ServiceOperatingState.STOPPED

    def apply_timestep(self, timestep: int) -> None:
        """
        Apply a single timestep of simulation dynamics to this service.

        In this instance, if any multi-timestep processes are currently occurring (such as restarting or installation),
        then they are brought one step closer to being finished.

        :param timestep: The current timestep number. (Amount of time since simulation episode began)
        :type timestep: int
        """
        super().apply_timestep(timestep)
        if self.operating_state == ServiceOperatingState.RESTARTING:
            if self.restart_countdown <= 0:
                _LOGGER.debug(f"Restarting finished for service {self.name}")
                self.operating_state = ServiceOperatingState.RUNNING
            self.restart_countdown -= 1
