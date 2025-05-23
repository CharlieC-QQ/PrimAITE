# © Crown-owned copyright 2025, Defence Science and Technology Laboratory UK
"""Database service."""
from ipaddress import IPv4Address
from typing import Any, Dict, List, Literal, Optional, Union
from uuid import uuid4

from pydantic import Field

from primaite import getLogger
from primaite.simulator.file_system.file_system import File
from primaite.simulator.file_system.file_system_item_abc import FileSystemItemHealthStatus
from primaite.simulator.file_system.folder import Folder
from primaite.simulator.system.core.software_manager import SoftwareManager
from primaite.simulator.system.services.ftp.ftp_client import FTPClient
from primaite.simulator.system.services.service import Service, ServiceOperatingState
from primaite.simulator.system.software import SoftwareHealthState
from primaite.utils.validation.ip_protocol import PROTOCOL_LOOKUP
from primaite.utils.validation.port import PORT_LOOKUP

_LOGGER = getLogger(__name__)


class DatabaseService(Service, discriminator="database-service"):
    """
    A class for simulating a generic SQL Server service.

    This class inherits from the `Service` class and provides methods to simulate a SQL database.
    """

    class ConfigSchema(Service.ConfigSchema):
        """ConfigSchema for DatabaseService."""

        type: str = "database-service"
        backup_server_ip: Optional[IPv4Address] = None
        db_password: Optional[str] = None
        """Password that needs to be provided by clients if they want to connect to the DatabaseService."""

    config: ConfigSchema = Field(default_factory=lambda: DatabaseService.ConfigSchema())

    backup_server_ip: IPv4Address = None
    """IP address of the backup server."""

    latest_backup_directory: str = None
    """Directory of latest backup."""

    latest_backup_file_name: str = None
    """File name of latest backup."""

    def __init__(self, **kwargs):
        kwargs["name"] = "database-service"
        kwargs["port"] = PORT_LOOKUP["POSTGRES_SERVER"]
        kwargs["protocol"] = PROTOCOL_LOOKUP["TCP"]
        super().__init__(**kwargs)
        self._create_db_file()
        self.backup_server_ip = self.config.backup_server_ip

    @property
    def password(self) -> Optional[str]:
        """Convenience property for accessing the password."""
        return self.config.db_password

    @password.setter
    def password(self, val: str) -> None:
        self.config.db_password = val

    def install(self):
        """
        Perform first-time setup of the DatabaseService.

        Installs an instance of FTPClient on the Node to enable database backup if it isn't installed already.
        """
        super().install()

        if not self.parent.software_manager.software.get("ftp-client"):
            self.parent.sys_log.info(f"{self.name}: Installing FTPClient to enable database backups")
            self.parent.software_manager.install(FTPClient)

    def configure_backup(self, backup_server: IPv4Address):
        """
        Set up the database backup.

        :param: backup_server_ip: The IP address of the backup server
        """
        self.backup_server_ip = backup_server

    def backup_database(self) -> bool:
        """Create a backup of the database to the configured backup server."""
        # check if this action can be performed
        if not self._can_perform_action():
            return False

        # check if the backup server was configured
        if self.backup_server_ip is None:
            self.sys_log.warning(f"{self.name} - {self.sys_log.hostname}: not configured.")
            return False

        software_manager: SoftwareManager = self.software_manager
        ftp_client_service: FTPClient = software_manager.software.get("ftp-client")

        if not ftp_client_service:
            self.sys_log.error(
                f"{self.name}: Failed to perform database backup as the FTPClient software is not installed"
            )
            return False

        # send backup copy of database file to FTP server
        if not self.db_file:
            self.sys_log.error(f"{self.name}: Attempted to backup database file but it doesn't exist.")
            return False

        response = ftp_client_service.send_file(
            dest_ip_address=self.backup_server_ip,
            src_file_name=self.db_file.name,
            src_folder_name="database",
            dest_folder_name=str(self.uuid),
            dest_file_name="database.db",
        )

        if response:
            return True

        self.sys_log.error("Unable to create database backup.")
        return False

    def restore_backup(self) -> bool:
        """Restore a backup from backup server."""
        # check if this action can be performed
        if not self._can_perform_action():
            return False

        software_manager: SoftwareManager = self.software_manager
        ftp_client_service: FTPClient = software_manager.software.get("ftp-client")

        if not ftp_client_service:
            self.sys_log.error(
                f"{self.name}: Failed to restore database backup as the FTPClient software is not installed"
            )
            return False

        # retrieve backup file from backup server
        response = ftp_client_service.request_file(
            src_folder_name=str(self.uuid),
            src_file_name="database.db",
            dest_folder_name="downloads",
            dest_file_name="database.db",
            dest_ip_address=self.backup_server_ip,
        )

        if not response:
            self.sys_log.error("Unable to restore database backup.")
            return False

        old_visible_state = SoftwareHealthState.GOOD

        # get db file regardless of whether or not it was deleted
        db_file = self.file_system.get_file(folder_name="database", file_name="database.db", include_deleted=True)

        if db_file is None:
            self.sys_log.warning("Database file not initialised.")
            return False

        # if the file was deleted, get the old visible health state
        if db_file.deleted:
            old_visible_state = db_file.visible_health_status
        else:
            old_visible_state = self.db_file.visible_health_status
            self.file_system.delete_file(folder_name="database", file_name="database.db")

        # replace db file
        self.file_system.copy_file(src_folder_name="downloads", src_file_name="database.db", dst_folder_name="database")

        if self.db_file is None:
            self.sys_log.error("Copying database backup failed.")
            return False

        self.db_file.visible_health_status = old_visible_state
        self.set_health_state(SoftwareHealthState.GOOD)

        return True

    def _create_db_file(self):
        """Creates the Simulation File and sqlite file in the file system."""
        self.file_system.create_file(folder_name="database", file_name="database.db")

    @property
    def db_file(self) -> File:
        """Returns the database file."""
        return self.file_system.get_file(folder_name="database", file_name="database.db")

    def _return_database_folder(self) -> Folder:
        """Returns the database folder."""
        return self.file_system.get_folder_by_id(self.db_file.folder_id)

    def _generate_connection_id(self) -> str:
        """Generate a unique connection ID."""
        return str(uuid4())

    def _process_connect(
        self,
        src_ip: IPv4Address,
        connection_request_id: str,
        password: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Union[int, Dict[str, bool]]]:
        """Process an incoming connection request.

        :param connection_id: A unique identifier for the connection
        :type connection_id: str
        :param password: Supplied password. It must match self.password for connection success, defaults to None
        :type password: Optional[str], optional
        :return: Response to connection request containing success info.
        :rtype: Dict[str, Union[int, Dict[str, bool]]]
        """
        self.sys_log.info(f"{self.name}: Processing new connection request ({connection_request_id}) from {src_ip}")
        status_code = 500  # Default internal server error
        connection_id = None
        if self.operating_state == ServiceOperatingState.RUNNING:
            status_code = 503  # service unavailable
            if self.health_state_actual == SoftwareHealthState.OVERWHELMED:
                self.sys_log.info(
                    f"{self.name}: Connection request ({connection_request_id}) from {src_ip} declined, service is at "
                    f"capacity."
                )
            if self.health_state_actual in [
                SoftwareHealthState.GOOD,
                SoftwareHealthState.FIXING,
                SoftwareHealthState.COMPROMISED,
            ]:
                if self.config.db_password == password:
                    status_code = 200  # ok
                    connection_id = self._generate_connection_id()
                    # try to create connection
                    if not self.add_connection(connection_id=connection_id, session_id=session_id):
                        status_code = 500
                        self.sys_log.info(
                            f"{self.name}: Connection request ({connection_request_id}) from {src_ip} declined, "
                            f"returning status code 500"
                        )
                else:
                    status_code = 401  # Unauthorised
                    self.sys_log.info(
                        f"{self.name}: Connection request ({connection_request_id}) from {src_ip} unauthorised "
                        f"(incorrect password), returning status code 401"
                    )
        else:
            status_code = 404  # service not found
        return {
            "status_code": status_code,
            "type": "connect_response",
            "response": status_code == 200,
            "connection_id": connection_id,
            "connection_request_id": connection_request_id,
        }

    def _process_sql(
        self,
        query: Literal["SELECT", "DELETE", "INSERT", "ENCRYPT"],
        query_id: str,
        connection_id: Optional[str] = None,
    ) -> Dict[str, Union[int, List[Any]]]:
        """
        Executes the given SQL query and returns the result.

        Possible queries:
        - SELECT : returns the data
        - DELETE : deletes the data
        - INSERT : inserts the data
        - ENCRYPT : corrupts the data

        :param query: The SQL query to be executed.
        :return: Dictionary containing status code and data fetched.
        """
        self.sys_log.info(f"{self.name}: Running {query}")

        if not self.db_file:
            self.sys_log.error(f"{self.name}: Failed to run {query} because the database file is missing.")
            return {"status_code": 404, "type": "sql", "data": False}

        if self.health_state_actual is not SoftwareHealthState.GOOD:
            self.sys_log.error(f"{self.name}: Failed to run {query} because the database service is unavailable.")
            return {"status_code": 500, "type": "sql", "data": False}

        if query == "SELECT":
            if self.db_file.health_status == FileSystemItemHealthStatus.CORRUPT:
                return {
                    "status_code": 200,
                    "type": "sql",
                    "data": False,
                    "uuid": query_id,
                    "connection_id": connection_id,
                }
            elif self.db_file.health_status == FileSystemItemHealthStatus.GOOD:
                return {
                    "status_code": 200,
                    "type": "sql",
                    "data": True,
                    "uuid": query_id,
                    "connection_id": connection_id,
                }
            else:
                return {"status_code": 404, "type": "sql", "data": False}
        elif query == "DELETE":
            self.db_file.health_status = FileSystemItemHealthStatus.COMPROMISED
            return {
                "status_code": 200,
                "type": "sql",
                "data": False,
                "uuid": query_id,
                "connection_id": connection_id,
            }
        elif query == "ENCRYPT":
            self.file_system.num_file_creations += 1
            self.db_file.health_status = FileSystemItemHealthStatus.CORRUPT
            self.db_file.num_access += 1
            database_folder = self._return_database_folder()
            database_folder.health_status = FileSystemItemHealthStatus.CORRUPT
            self.file_system.num_file_deletions += 1
            return {
                "status_code": 200,
                "type": "sql",
                "data": False,
                "uuid": query_id,
                "connection_id": connection_id,
            }
        elif query == "INSERT":
            if self.health_state_actual == SoftwareHealthState.GOOD:
                return {
                    "status_code": 200,
                    "type": "sql",
                    "data": False,
                    "uuid": query_id,
                    "connection_id": connection_id,
                }
            else:
                return {"status_code": 404, "type": "sql", "data": False}
        elif query == "SELECT * FROM pg_stat_activity":
            # Check if the connection is active.
            if self.health_state_actual == SoftwareHealthState.GOOD:
                return {
                    "status_code": 200,
                    "type": "sql",
                    "data": False,
                    "uuid": query_id,
                    "connection_id": connection_id,
                }
            else:
                return {"status_code": 401, "data": False}
        else:
            # Invalid query
            self.sys_log.warning(f"{self.name}: Invalid {query}")
            return {"status_code": 500, "data": False}

    def describe_state(self) -> Dict:
        """
        Produce a dictionary describing the current state of this object.

        Please see :py:meth:`primaite.simulator.core.SimComponent.describe_state` for a more detailed explanation.

        :return: Current state of this object and child objects.
        :rtype: Dict
        """
        return super().describe_state()

    def receive(self, payload: Any, session_id: str, **kwargs) -> bool:
        """
        Processes the incoming SQL payload and sends the result back.

        :param payload: The SQL query to be executed.
        :param session_id: The session identifier.
        :return: True if the Status Code is 200, otherwise False.
        """
        result = {"status_code": 500, "data": []}
        # if server service is down, return error
        if not self._can_perform_action():
            return False

        if isinstance(payload, dict) and payload.get("type"):
            if payload["type"] == "connect_request":
                src_ip = kwargs.get("frame").ip.src_ip_address
                result = self._process_connect(
                    src_ip=src_ip,
                    password=payload.get("password"),
                    connection_request_id=payload.get("connection_request_id"),
                    session_id=session_id,
                )
            elif payload["type"] == "disconnect":
                if payload["connection_id"] in self.connections:
                    connection_id = payload["connection_id"]
                    connected_ip_address = self.connections[connection_id]["ip_address"]
                    frame = kwargs.get("frame")
                    if connected_ip_address == frame.ip.src_ip_address:
                        self.sys_log.info(
                            f"{self.name}: Received disconnect command for {connection_id=} from {connected_ip_address}"
                        )
                        self.terminate_connection(connection_id=payload["connection_id"], send_disconnect=False)
                    else:
                        self.sys_log.warning(
                            f"{self.name}: Ignoring disconnect command for {connection_id=} as the command source "
                            f"({frame.ip.src_ip_address}) doesn't match the connection source ({connected_ip_address})"
                        )
            elif payload["type"] == "sql":
                if payload.get("connection_id") in self.connections:
                    result = self._process_sql(
                        query=payload["sql"], query_id=payload["uuid"], connection_id=payload["connection_id"]
                    )
                else:
                    result = {"status_code": 401, "type": "sql"}
        else:
            self.sys_log.info(f"{self.name}: Ignoring payload as it is not a Database payload")
        self.send(payload=result, session_id=session_id)
        return True

    def send(self, payload: Any, session_id: str, **kwargs) -> bool:
        """
        Send a SQL response back down to the SessionManager.

        :param payload: The SQL query results.
        :param session_id: The session identifier.
        :return: True if the Status Code is 200, otherwise False.
        """
        software_manager: SoftwareManager = self.software_manager
        software_manager.send_payload_to_session_manager(payload=payload, session_id=session_id)

        return payload["status_code"] == 200

    def apply_timestep(self, timestep: int) -> None:
        """
        Apply a single timestep of simulation dynamics to this service.

        Here at the first step, the database backup is created, in addition to normal service update logic.
        """
        if timestep == 1:
            self.backup_database()
        return super().apply_timestep(timestep)

    def _update_fix_status(self) -> None:
        """Perform a database restore when the FIXING countdown is finished."""
        super()._update_fix_status()
        if self._fixing_countdown is None:
            self.restore_backup()
