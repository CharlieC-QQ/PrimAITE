# © Crown-owned copyright 2025, Defence Science and Technology Laboratory UK
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from primaite.simulator import SIM_OUTPUT


class _JSONFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter logs that start and end with '{' and '}' (JSON-like messages)."""
        return record.getMessage().startswith("{") and record.getMessage().endswith("}")


class PacketCapture:
    """
    Represents a PacketCapture component on a Node in the simulation environment.

    PacketCapture is a service that logs Frames as json strings; It's Wireshark for PrimAITE.

    The PCAPs are logged to: <simulation output directory>/<hostname>/<hostname>_<ip address>_pcap.log
    """

    _logger_instances: List[logging.Logger] = []

    def __init__(
        self,
        hostname: str,
        ip_address: Optional[str] = None,
        port_num: Optional[int] = None,
        port_name: Optional[str] = None,
    ):
        """
        Initialize the PacketCapture process.

        :param hostname: The hostname for which PCAP logs are being recorded.
        :param ip_address: The IP address associated with the PCAP logs.
        """
        self.hostname: str = hostname
        "The hostname for which PCAP logs are being recorded."
        self.ip_address: str = ip_address
        "The IP address associated with the PCAP logs."
        self.port_num = port_num
        "The interface num on the Node."

        self.port_name = port_name
        "The interface name on the Node."

        self.inbound_logger = None
        self.outbound_logger = None

        self.current_episode: int = 1

        if SIM_OUTPUT.save_pcap_logs:
            self.setup_logger(outbound=False)
            self.setup_logger(outbound=True)

    def setup_logger(self, outbound: bool = False):
        """Set up the logger configuration."""
        log_path = self._get_log_path(outbound)

        file_handler = logging.FileHandler(filename=log_path)
        file_handler.setLevel(60)  # Custom log level > CRITICAL to prevent any unwanted standard DEBUG-CRITICAL logs

        log_format = "%(message)s"
        file_handler.setFormatter(logging.Formatter(log_format))

        if outbound:
            self.outbound_logger = logging.getLogger(self._get_logger_name(outbound))
            PacketCapture._logger_instances.append(self.outbound_logger)
            logger = self.outbound_logger
        else:
            self.inbound_logger = logging.getLogger(self._get_logger_name(outbound))
            logger = self.inbound_logger
            PacketCapture._logger_instances.append(self.inbound_logger)

        logger.setLevel(60)  # Custom log level > CRITICAL to prevent any unwanted standard DEBUG-CRITICAL logs
        logger.addHandler(file_handler)

        logger.addFilter(_JSONFilter())

    def read(self) -> List[Dict[str, Any]]:
        """
        Read packet capture logs and return them as a list of dictionaries.

        :return: List of frames captured, represented as dictionaries.
        """
        frames = []
        with open(self._get_log_path(), "r") as file:
            while line := file.readline():
                frames.append(json.loads(line.rstrip()))
        return frames

    def _get_logger_name(self, outbound: bool = False) -> str:
        """Get PCAP the logger name."""
        if self.port_name:
            return f"{self.hostname}_{self.port_name}_{'outbound' if outbound else 'inbound'}_pcap"
        if self.ip_address:
            return f"{self.hostname}_{self.ip_address}_{'outbound' if outbound else 'inbound'}_pcap"
        if self.port_num:
            return f"{self.hostname}_port-{self.port_num}_{'outbound' if outbound else 'inbound'}_pcap"
        return f"{self.hostname}_{'outbound' if outbound else 'inbound'}_pcap"

    def _get_log_path(self, outbound: bool = False) -> Path:
        """Get the path for the log file."""
        root = SIM_OUTPUT.path / f"episode_{self.current_episode}" / self.hostname
        root.mkdir(exist_ok=True, parents=True)
        return root / f"{self._get_logger_name(outbound)}.log"

    def capture_inbound(self, frame):  # noqa - I'll have a circular import and cant use if TYPE_CHECKING ;(
        """
        Capture an inbound Frame and log it.

        :param frame: The PCAP frame to capture.
        """
        if SIM_OUTPUT.save_pcap_logs:
            msg = frame.model_dump_json()
            self.inbound_logger.log(level=60, msg=msg)  # Log at custom log level > CRITICAL

    def capture_outbound(self, frame):  # noqa - I'll have a circular import and cant use if TYPE_CHECKING ;(
        """
        Capture an outbound Frame and log it.

        :param frame: The PCAP frame to capture.
        """
        if SIM_OUTPUT.save_pcap_logs:
            msg = frame.model_dump_json()
            self.outbound_logger.log(level=60, msg=msg)  # Log at custom log level > CRITICAL

    @staticmethod
    def clear():
        """Close all open PCAP file handlers."""
        for logger in PacketCapture._logger_instances:
            handlers = logger.handlers[:]
            for handler in handlers:
                logger.removeHandler(handler)
                handler.close()
        PacketCapture._logger_instances = []
