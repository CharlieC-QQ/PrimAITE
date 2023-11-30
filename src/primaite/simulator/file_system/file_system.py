from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict, Optional

from prettytable import MARKDOWN, PrettyTable

from primaite import getLogger
from primaite.simulator.core import RequestManager, RequestType, SimComponent
from primaite.simulator.file_system.file import File
from primaite.simulator.file_system.file_type import FileType
from primaite.simulator.file_system.folder import Folder
from primaite.simulator.system.core.sys_log import SysLog

_LOGGER = getLogger(__name__)


class FileSystem(SimComponent):
    """Class that contains all the simulation File System."""

    folders: Dict[str, Folder] = {}
    "List containing all the folders in the file system."
    deleted_folders: Dict[str, Folder] = {}
    "List containing all the folders that have been deleted."
    _folders_by_name: Dict[str, Folder] = {}
    sys_log: SysLog
    "Instance of SysLog used to create system logs."
    sim_root: Path
    "Root path of the simulation."

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure a default root folder
        if not self.folders:
            self.create_folder("root")

    def set_original_state(self):
        """Sets the original state."""
        _LOGGER.debug(f"Setting FileSystem original state on node {self.sys_log.hostname}")
        for folder in self.folders.values():
            folder.set_original_state()
        # Capture a list of all 'original' file uuids
        original_keys = list(self.folders.keys())
        vals_to_include = {"sim_root"}
        self._original_state.update(self.model_dump(include=vals_to_include))
        self._original_state["original_folder_uuids"] = original_keys

    def reset_component_for_episode(self, episode: int):
        """Reset the original state of the SimComponent."""
        _LOGGER.debug(f"Resetting FileSystem state on node {self.sys_log.hostname}")
        # Move any 'original' folder that have been deleted back to folders
        original_folder_uuids = self._original_state["original_folder_uuids"]
        for uuid in original_folder_uuids:
            if uuid in self.deleted_folders:
                self.folders[uuid] = self.deleted_folders.pop(uuid)

        # Clear any other deleted folders that aren't original (have been created by agent)
        self.deleted_folders.clear()

        # Now clear all non-original folders created by agent
        current_folder_uuids = list(self.folders.keys())
        for uuid in current_folder_uuids:
            if uuid not in original_folder_uuids:
                self.folders.pop(uuid)

        # Now reset all remaining folders
        for folder in self.folders.values():
            folder.reset_component_for_episode(episode)
        super().reset_component_for_episode(episode)

    def _init_request_manager(self) -> RequestManager:
        rm = super()._init_request_manager()

        self._delete_manager = RequestManager()
        self._delete_manager.add_request(
            name="file",
            request_type=RequestType(
                func=lambda request, context: self.delete_file_by_id(folder_uuid=request[0], file_uuid=request[1])
            ),
        )
        self._delete_manager.add_request(
            name="folder",
            request_type=RequestType(func=lambda request, context: self.delete_folder_by_id(folder_uuid=request[0])),
        )
        rm.add_request(
            name="delete",
            request_type=RequestType(func=self._delete_manager),
        )

        self._restore_manager = RequestManager()
        self._restore_manager.add_request(
            name="file",
            request_type=RequestType(
                func=lambda request, context: self.restore_file(folder_uuid=request[0], file_uuid=request[1])
            ),
        )
        self._restore_manager.add_request(
            name="folder",
            request_type=RequestType(func=lambda request, context: self.restore_folder(folder_uuid=request[0])),
        )
        rm.add_request(
            name="restore",
            request_type=RequestType(func=self._restore_manager),
        )

        self._folder_request_manager = RequestManager()
        rm.add_request("folder", RequestType(func=self._folder_request_manager))

        self._file_request_manager = RequestManager()
        rm.add_request("file", RequestType(func=self._file_request_manager))

        return rm

    @property
    def size(self) -> int:
        """
        Calculate and return the total size of all folders in the file system.

        :return: The sum of the sizes of all folders in the file system.
        """
        return sum(folder.size for folder in self.folders.values())

    def show(self, markdown: bool = False, full: bool = False):
        """
        Prints a table of the FileSystem, displaying either just folders or full files.

        :param markdown: Flag indicating if output should be in markdown format.
        :param full: Flag indicating if to show full files.
        """
        headers = ["Folder", "Size", "Deleted"]
        if full:
            headers[0] = "File Path"
        table = PrettyTable(headers)
        if markdown:
            table.set_style(MARKDOWN)
        table.align = "l"
        table.title = f"{self.sys_log.hostname} File System"
        folders = {**self.folders, **self.deleted_folders}
        for folder in folders.values():
            if not full:
                table.add_row([folder.name, folder.size_str, folder.deleted])
            else:
                files = {**folder.files, **folder.deleted_files}
                if not files:
                    table.add_row([folder.name, folder.size_str, folder.deleted])
                else:
                    for file in files.values():
                        table.add_row([file.path, file.size_str, file.deleted])
        if full:
            print(table.get_string(sortby="File Path"))
        else:
            print(table.get_string(sortby="Folder"))

    ###############################################################
    # Folder methods
    ###############################################################
    def create_folder(self, folder_name: str) -> Folder:
        """
        Creates a Folder and adds it to the list of folders.

        :param folder_name: The name of the folder.
        """
        # check if folder with name already exists
        if self.get_folder(folder_name):
            raise Exception(f"Cannot create folder as it already exists: {folder_name}")

        folder = Folder(name=folder_name, sys_log=self.sys_log)

        self.folders[folder.uuid] = folder
        self._folders_by_name[folder.name] = folder
        self._folder_request_manager.add_request(
            name=folder.uuid, request_type=RequestType(func=folder._request_manager)
        )
        return folder

    def delete_folder(self, folder_name: str):
        """
        Deletes a folder, removes it from the folders list and removes any child folders and files.

        :param folder_name: The name of the folder.
        """
        if folder_name == "root":
            self.sys_log.warning("Cannot delete the root folder.")
            return
        folder = self._folders_by_name.get(folder_name)
        if folder:
            # set folder to deleted state
            folder.delete()

            # remove from folder list
            self.folders.pop(folder.uuid)
            self._folders_by_name.pop(folder.name)

            # add to deleted list
            folder.remove_all_files()

            self.deleted_folders[folder.uuid] = folder
            self.sys_log.info(f"Deleted folder /{folder.name} and its contents")
        else:
            _LOGGER.debug(f"Cannot delete folder as it does not exist: {folder_name}")

    def delete_folder_by_id(self, folder_uuid: str):
        """
        Deletes a folder via its uuid.

        :param: folder_uuid: UUID of the folder to delete
        """
        folder = self.get_folder_by_id(folder_uuid=folder_uuid)
        self.delete_folder(folder_name=folder.name)

    def get_folder(self, folder_name: str) -> Optional[Folder]:
        """
        Get a folder by its name if it exists.

        :param folder_name: The folder name.
        :return: The matching Folder.
        """
        return self._folders_by_name.get(folder_name)

    def get_folder_by_id(self, folder_uuid: str, include_deleted: bool = False) -> Optional[Folder]:
        """
        Get a folder by its uuid if it exists.

        :param: folder_uuid: The folder uuid.
        :param: include_deleted: If true, the deleted folders will also be checked
        :return: The matching Folder.
        """
        if include_deleted:
            folder = self.deleted_folders.get(folder_uuid)
            if folder:
                return folder

        return self.folders.get(folder_uuid)

    ###############################################################
    # File methods
    ###############################################################

    def create_file(
        self,
        file_name: str,
        size: Optional[int] = None,
        file_type: Optional[FileType] = None,
        folder_name: Optional[str] = None,
        real: bool = False,
    ) -> File:
        """
        Creates a File and adds it to the list of files.

        :param file_name: The file name.
        :param size: The size the file takes on disk in bytes.
        :param file_type: The type of the file.
        :param folder_name: The folder to add the file to.
        :param real: "Indicates whether the File is actually a real file in the Node sim fs output."
        """
        if folder_name:
            # check if file with name already exists
            folder = self._folders_by_name.get(folder_name)
            # If not then create it
            if not folder:
                folder = self.create_folder(folder_name)
        else:
            # Use root folder if folder_name not supplied
            folder = self._folders_by_name["root"]

        # Create the file and add it to the folder
        file = File(
            name=file_name,
            sim_size=size,
            file_type=file_type,
            folder_id=folder.uuid,
            folder_name=folder.name,
            real=real,
            sim_path=self.sim_root if real else None,
            sim_root=self.sim_root,
            sys_log=self.sys_log,
        )
        folder.add_file(file)
        self._file_request_manager.add_request(name=file.uuid, request_type=RequestType(func=file._request_manager))
        return file

    def get_file(self, folder_name: str, file_name: str) -> Optional[File]:
        """
        Retrieve a file by its name from a specific folder.

        :param folder_name: The name of the folder where the file resides.
        :param file_name: The name of the file to be retrieved, including its extension.
        :return: An instance of File if it exists, otherwise `None`.
        """
        folder = self.get_folder(folder_name)
        if folder:
            return folder.get_file(file_name)
        self.sys_log.info(f"File not found /{folder_name}/{file_name}")

    def get_file_by_id(
        self, file_uuid: str, folder_uuid: Optional[str] = None, include_deleted: Optional[bool] = False
    ) -> Optional[File]:
        """
        Retrieve a file by its uuid from a specific folder.

        :param: file_uuid: The uuid of the folder where the file resides.
        :param: folder_uuid: The uuid of the file to be retrieved, including its extension.
        :param: include_deleted: If true, the deleted files will also be checked
        :return: An instance of File if it exists, otherwise `None`.
        """
        folder = self.get_folder_by_id(folder_uuid=folder_uuid, include_deleted=include_deleted)

        if folder:
            return folder.get_file_by_id(file_uuid=file_uuid, include_deleted=include_deleted)

        # iterate through every folder looking for file
        file = None

        for folder_id in self.folders:
            folder = self.folders.get(folder_id)
            res = folder.get_file_by_id(file_uuid=file_uuid, include_deleted=True)
            if res:
                file = res

        if include_deleted:
            for folder_id in self.deleted_folders:
                folder = self.deleted_folders.get(folder_id)
                res = folder.get_file_by_id(file_uuid=file_uuid, include_deleted=True)
                if res:
                    file = res

        return file

    def delete_file(self, folder_name: str, file_name: str):
        """
        Delete a file by its name from a specific folder.

        :param folder_name: The name of the folder containing the file.
        :param file_name: The name of the file to be deleted, including its extension.
        """
        folder = self.get_folder(folder_name)
        if folder:
            file = folder.get_file(file_name)
            if file:
                folder.remove_file(file)

    def delete_file_by_id(self, folder_uuid: str, file_uuid: str):
        """
        Deletes a file via its uuid.

        :param: folder_uuid: UUID of the folder the file belongs to
        :param: file_uuid: UUID of the file to delete
        """
        folder = self.get_folder_by_id(folder_uuid=folder_uuid)

        if folder:
            file = folder.get_file_by_id(file_uuid=file_uuid)

            if file:
                self.delete_file(folder_name=folder.name, file_name=file.name)
            else:
                self.sys_log.error(f"Unable to delete file that does not exist. (id: {file_uuid})")

    def move_file(self, src_folder_name: str, src_file_name: str, dst_folder_name: str):
        """
        Move a file from one folder to another.

        :param src_folder_name: The name of the source folder containing the file.
        :param src_file_name: The name of the file to be moved.
        :param dst_folder_name: The name of the destination folder.
        """
        file = self.get_file(folder_name=src_folder_name, file_name=src_file_name)
        if file:
            src_folder = file.folder

            # remove file from src
            src_folder.remove_file(file)
            dst_folder = self.get_folder(folder_name=dst_folder_name)
            if not dst_folder:
                dst_folder = self.create_folder(dst_folder_name)
            # add file to dst
            dst_folder.add_file(file)
            if file.real:
                old_sim_path = file.sim_path
                file.sim_path = file.sim_root / file.path
                file.sim_path.parent.mkdir(exist_ok=True)
                shutil.move(old_sim_path, file.sim_path)

    def copy_file(self, src_folder_name: str, src_file_name: str, dst_folder_name: str):
        """
        Copy a file from one folder to another.

        :param src_folder_name: The name of the source folder containing the file.
        :param src_file_name: The name of the file to be copied.
        :param dst_folder_name: The name of the destination folder.
        """
        file = self.get_file(folder_name=src_folder_name, file_name=src_file_name)
        if file:
            # check that dest folder exists
            dst_folder = self.get_folder(folder_name=dst_folder_name)
            if not dst_folder:
                # create dest folder
                dst_folder = self.create_folder(dst_folder_name)

            file_copy = File(
                folder_id=dst_folder.uuid,
                folder_name=dst_folder.name,
                **file.model_dump(exclude={"uuid", "folder_id", "folder_name", "sim_path"}),
            )
            dst_folder.add_file(file_copy, force=True)

            if file.real:
                file_copy.sim_path.parent.mkdir(exist_ok=True)
                shutil.copy2(file.sim_path, file_copy.sim_path)
        else:
            self.sys_log.error(f"Unable to copy file. {src_file_name} does not exist.")

    def describe_state(self) -> Dict:
        """
        Produce a dictionary describing the current state of this object.

        :return: Current state of this object and child objects.
        """
        state = super().describe_state()
        state["folders"] = {folder.name: folder.describe_state() for folder in self.folders.values()}
        state["deleted_folders"] = {folder.name: folder.describe_state() for folder in self.deleted_folders.values()}
        return state

    def apply_timestep(self, timestep: int) -> None:
        """Apply time step to FileSystem and its child folders and files."""
        super().apply_timestep(timestep=timestep)

        # apply timestep to folders
        for folder_id in self.folders:
            self.folders[folder_id].apply_timestep(timestep=timestep)

    ###############################################################
    # Agent actions
    ###############################################################

    def scan(self, instant_scan: bool = False):
        """
        Scan all the folders (and child files) in the file system.

        :param: instant_scan: If True, the scan is completed instantly and ignores scan duration. Default False.
        """
        for folder_id in self.folders:
            self.folders[folder_id].scan(instant_scan=instant_scan)

    def reveal_to_red(self, instant_scan: bool = False):
        """
        Reveals all the folders (and child files) in the file system to the red agent.

        :param: instant_scan: If True, the scan is completed instantly and ignores scan duration. Default False.
        """
        for folder_id in self.folders:
            self.folders[folder_id].reveal_to_red(instant_scan=instant_scan)

    def restore_folder(self, folder_uuid: str):
        """
        Restore a folder.

        Checks the current folder's status and applies the correct fix for the folder.

        :param: folder_uuid: id of the folder to restore
        :type: folder_uuid: str
        """
        folder = self.get_folder_by_id(folder_uuid=folder_uuid, include_deleted=True)

        if folder is None:
            self.sys_log.error(f"Unable to restore folder with uuid {folder_uuid}. Folder does not exist.")
            return

        folder.restore()
        self.folders[folder.uuid] = folder
        self._folders_by_name[folder.name] = folder

        if folder.deleted:
            self.deleted_folders.pop(folder.uuid)

    def restore_file(self, folder_uuid: str, file_uuid: str):
        """
        Restore a file.

        Checks the current file's status and applies the correct fix for the file.

        :param: folder_uuid: id of the folder where the file is stored
        :type: folder_uuid: str

        :param: file_uuid: id of the file to restore
        :type: file_uuid: str
        """
        folder = self.get_folder_by_id(folder_uuid=folder_uuid, include_deleted=True)

        if folder:
            file = folder.get_file_by_id(file_uuid=file_uuid, include_deleted=True)

            if file is None:
                self.sys_log.error(f"Unable to restore file with uuid {file_uuid}. File does not exist.")
                return

            folder.restore_file(file_uuid=file_uuid)
