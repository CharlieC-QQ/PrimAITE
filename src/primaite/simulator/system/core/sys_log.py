import logging
from pathlib import Path

from prettytable import MARKDOWN, PrettyTable

from primaite.simulator import TEMP_SIM_OUTPUT


class _NotJSONFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Determines if a log message does not start and end with '{' and '}' (i.e., it is not a JSON-like message).

        :param record: LogRecord object containing all the information pertinent to the event being logged.
        :return: True if log message is not JSON-like, False otherwise.
        """
        return not record.getMessage().startswith("{") and not record.getMessage().endswith("}")


class SysLog:
    """
    A SysLog class is a simple logger dedicated to managing and writing system logs for a Node.

    Each log message is written to a file located at: <simulation output directory>/<hostname>/<hostname>_sys.log
    """

    def __init__(self, hostname: str):
        """
        Constructs a SysLog instance for a given hostname.

        :param hostname: The hostname associated with the system logs being recorded.
        """
        self.hostname = hostname
        self._setup_logger()

    def _setup_logger(self):
        """
        Configures the logger for this SysLog instance.

        The logger is set to the DEBUG level, and is equipped with a handler that writes to a file and filters out
        JSON-like messages.
        """
        log_path = self._get_log_path()

        file_handler = logging.FileHandler(filename=log_path)
        file_handler.setLevel(logging.DEBUG)

        log_format = "%(asctime)s::%(levelname)s::%(message)s"
        file_handler.setFormatter(logging.Formatter(log_format))

        self.logger = logging.getLogger(f"{self.hostname}_sys_log")
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(file_handler)

        self.logger.addFilter(_NotJSONFilter())

    def show(self, last_n: int = 10, markdown: bool = False):
        """
        Print the Node Sys Log as a table.

        Generate and print PrettyTable instance that shows the Nodes Sys Log, with columns Timestamp, Level,
        and Massage.

        :param markdown: Use Markdown style in table output. Defaults to False.
        """
        table = PrettyTable(["Timestamp", "Level", "Message"])
        if markdown:
            table.set_style(MARKDOWN)
        table.align = "l"
        table.title = f"{self.hostname} Sys Log"
        if self._get_log_path().exists():
            with open(self._get_log_path()) as file:
                lines = file.readlines()
            for line in lines[-last_n:]:
                table.add_row(line.strip().split("::"))
        print(table)

    def _get_log_path(self) -> Path:
        """
        Constructs the path for the log file based on the hostname.

        :return: Path object representing the location of the log file.
        """
        root = TEMP_SIM_OUTPUT / self.hostname
        root.mkdir(exist_ok=True, parents=True)
        return root / f"{self.hostname}_sys.log"

    def debug(self, msg: str):
        """
        Logs a message with the DEBUG level.

        :param msg: The message to be logged.
        """
        self.logger.debug(msg)

    def info(self, msg: str):
        """
        Logs a message with the INFO level.

        :param msg: The message to be logged.
        """
        self.logger.info(msg)

    def warning(self, msg: str):
        """
        Logs a message with the WARNING level.

        :param msg: The message to be logged.
        """
        self.logger.warning(msg)

    def error(self, msg: str):
        """
        Logs a message with the ERROR level.

        :param msg: The message to be logged.
        """
        self.logger.error(msg)

    def critical(self, msg: str):
        """
        Logs a message with the CRITICAL level.

        :param msg: The message to be logged.
        """
        self.logger.critical(msg)
