from typing import Dict

from primaite.simulator.file_system.file_system_file_type import FileSystemFileType
from primaite.simulator.network.hardware.base import Node
from primaite.simulator.system.services.service import Service


class DatabaseService(Service):
    """TODO."""

    def describe_state(self) -> Dict:
        """TODO."""
        return super().describe_state()

    def install(self) -> None:
        """Perform first time install on a node, creating necessary files."""
        super().install()
        assert isinstance(self.parent, Node), "Database install can only happen after the db service is added to a node"
        self._setup_files()

    def _setup_files(
        self,
        db_size: int = 1000,
        use_secondary_db_file: bool = False,
        secondary_db_size: int = 300,
        folder_name: str = "database",
    ):
        """Set up files that are required by the database on the parent host.

        :param db_size: Initial file size of the main database file, defaults to 1000
        :type db_size: int, optional
        :param use_secondary_db_file: Whether to use a secondary database file, defaults to False
        :type use_secondary_db_file: bool, optional
        :param secondary_db_size: Size of the secondary db file, defaults to None
        :type secondary_db_size: int, optional
        :param folder_name: Name of the folder which will be setup to hold the db files, defaults to "database"
        :type folder_name: str, optional
        """
        # note that this parent.file_system.create_folder call in the future will be authenticated by using permissions
        # handler. This permission will be granted based on service account given to the database service.
        self.parent: Node
        folder = self.parent.file_system.create_folder(folder_name)
        self.parent.file_system.create_file("db_primary_store", db_size, FileSystemFileType.MDF, folder=folder)
        self.parent.file_system.create_file("db_transaction_log", "1", FileSystemFileType.LDF, folder=folder)
        if use_secondary_db_file:
            self.parent.file_system.create_file(
                "db_secondary_store", secondary_db_size, FileSystemFileType.NDF, folder=folder
            )
