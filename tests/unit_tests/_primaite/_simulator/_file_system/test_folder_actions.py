from typing import Tuple

import pytest

from primaite.simulator.file_system.file_system import File, FileSystem, Folder
from primaite.simulator.file_system.file_system_item_abc import FileSystemItemHealthStatus


@pytest.fixture(scope="function")
def populated_file_system(file_system) -> Tuple[FileSystem, Folder, File]:
    """Create a file system with a folder and file."""
    folder = file_system.create_folder(folder_name="test_folder")
    file = file_system.create_file(folder_name="test_folder", file_name="test_file.txt")

    return file_system, folder, file


def test_folder_scan_request(populated_file_system):
    """Test that an agent can request a folder scan."""
    fs, folder, file = populated_file_system
    fs.create_file(file_name="test_file2.txt", folder_name="test_folder")

    file1: File = folder.get_file_by_id(file_uuid=list(folder.files)[1])
    file2: File = folder.get_file_by_id(file_uuid=list(folder.files)[0])

    folder.corrupt()
    assert folder.health_status == FileSystemItemHealthStatus.CORRUPT
    assert folder.visible_health_status == FileSystemItemHealthStatus.GOOD
    assert file1.visible_health_status == FileSystemItemHealthStatus.GOOD
    assert file2.visible_health_status == FileSystemItemHealthStatus.GOOD

    fs.apply_request(request=["folder", folder.uuid, "scan"])

    folder.apply_timestep(timestep=0)

    assert folder.health_status == FileSystemItemHealthStatus.CORRUPT
    assert folder.visible_health_status == FileSystemItemHealthStatus.GOOD
    assert file1.visible_health_status == FileSystemItemHealthStatus.GOOD
    assert file2.visible_health_status == FileSystemItemHealthStatus.GOOD

    folder.apply_timestep(timestep=1)
    folder.apply_timestep(timestep=2)

    assert folder.health_status == FileSystemItemHealthStatus.CORRUPT
    assert folder.visible_health_status == FileSystemItemHealthStatus.CORRUPT
    assert file1.visible_health_status == FileSystemItemHealthStatus.CORRUPT
    assert file2.visible_health_status == FileSystemItemHealthStatus.CORRUPT


def test_folder_checkhash_request(populated_file_system):
    """Test that an agent can request a folder hash check."""
    fs, folder, file = populated_file_system

    fs.apply_request(request=["folder", folder.uuid, "checkhash"])

    assert folder.health_status == FileSystemItemHealthStatus.GOOD
    file.sim_size = 0

    fs.apply_request(request=["folder", folder.uuid, "checkhash"])
    assert folder.health_status == FileSystemItemHealthStatus.CORRUPT


def test_folder_repair_request(populated_file_system):
    """Test that an agent can request a folder repair."""
    fs, folder, file = populated_file_system

    folder.corrupt()
    assert file.health_status == FileSystemItemHealthStatus.CORRUPT
    assert folder.health_status == FileSystemItemHealthStatus.CORRUPT

    fs.apply_request(request=["folder", folder.uuid, "repair"])
    assert file.health_status == FileSystemItemHealthStatus.GOOD
    assert folder.health_status == FileSystemItemHealthStatus.GOOD


def test_folder_restore_request(populated_file_system):
    """Test that an agent can request that a folder can be restored."""
    fs, folder, file = populated_file_system
    assert fs.get_folder_by_id(folder_uuid=folder.uuid) is not None
    assert fs.get_file_by_id(folder_uuid=folder.uuid, file_uuid=file.uuid) is not None

    # delete folder
    fs.apply_request(request=["delete", "folder", folder.uuid])
    assert fs.get_folder(folder_name=folder.name) is None
    assert fs.get_folder_by_id(folder_uuid=folder.uuid, include_deleted=True).deleted is True

    assert fs.get_file(folder_name=folder.name, file_name=file.name) is None
    assert fs.get_file_by_id(folder_uuid=folder.uuid, file_uuid=file.uuid, include_deleted=True).deleted is True

    # restore folder
    fs.apply_request(request=["restore", "folder", folder.uuid])
    fs.apply_timestep(timestep=0)
    assert fs.get_folder(folder_name=folder.name) is not None
    assert (
        fs.get_folder_by_id(folder_uuid=folder.uuid, include_deleted=True).health_status
        == FileSystemItemHealthStatus.RESTORING
    )
    assert fs.get_folder_by_id(folder_uuid=folder.uuid, include_deleted=True).deleted is False

    assert fs.get_file(folder_name=folder.name, file_name=file.name) is None
    assert fs.get_file_by_id(folder_uuid=folder.uuid, file_uuid=file.uuid, include_deleted=True).deleted is True

    fs.apply_timestep(timestep=1)
    fs.apply_timestep(timestep=2)

    assert fs.get_file(folder_name=folder.name, file_name=file.name) is not None
    assert (
        fs.get_file(folder_name=folder.name, file_name=file.name).health_status
        is not FileSystemItemHealthStatus.RESTORING
    )
    assert fs.get_file(folder_name=folder.name, file_name=file.name).deleted is False

    assert fs.get_file(folder_name=folder.name, file_name=file.name) is not None
    assert fs.get_file_by_id(folder_uuid=folder.uuid, file_uuid=file.uuid, include_deleted=True).deleted is False

    # corrupt folder
    fs.apply_request(request=["folder", folder.uuid, "corrupt"])
    assert fs.get_folder(folder_name=folder.name).health_status == FileSystemItemHealthStatus.CORRUPT
    assert fs.get_file(folder_name=folder.name, file_name=file.name).health_status == FileSystemItemHealthStatus.CORRUPT

    # restore folder
    fs.apply_request(request=["restore", "folder", folder.uuid])
    fs.apply_timestep(timestep=0)
    assert fs.get_folder(folder_name=folder.name).health_status == FileSystemItemHealthStatus.RESTORING
    assert fs.get_file(folder_name=folder.name, file_name=file.name).health_status == FileSystemItemHealthStatus.CORRUPT

    fs.apply_timestep(timestep=1)
    fs.apply_timestep(timestep=2)

    assert fs.get_file(folder_name=folder.name, file_name=file.name) is not None
    assert (
        fs.get_file(folder_name=folder.name, file_name=file.name).health_status
        is not FileSystemItemHealthStatus.RESTORING
    )
    assert fs.get_file(folder_name=folder.name, file_name=file.name).deleted is False

    assert fs.get_file(folder_name=folder.name, file_name=file.name) is not None
    assert fs.get_file_by_id(folder_uuid=folder.uuid, file_uuid=file.uuid, include_deleted=True).deleted is False


def test_folder_corrupt_request(populated_file_system):
    """Test that an agent can request a folder corruption."""
    fs, folder, file = populated_file_system
    fs.apply_request(request=["folder", folder.uuid, "corrupt"])
    assert file.health_status == FileSystemItemHealthStatus.CORRUPT
    assert folder.health_status == FileSystemItemHealthStatus.CORRUPT


def test_deleted_folder_and_its_files_cannot_be_interacted_with(populated_file_system):
    """Test that actions cannot affect deleted folder and its child files."""
    fs, folder, file = populated_file_system
    assert fs.get_file(folder_name=folder.name, file_name=file.name) is not None

    fs.apply_request(request=["file", file.uuid, "corrupt"])
    assert fs.get_file(folder_name=folder.name, file_name=file.name).health_status == FileSystemItemHealthStatus.CORRUPT

    fs.apply_request(request=["delete", "folder", folder.uuid])
    assert fs.get_file(folder_name=folder.name, file_name=file.name) is None

    fs.apply_request(request=["file", file.uuid, "repair"])

    deleted_folder = fs.deleted_folders.get(folder.uuid)
    deleted_file = deleted_folder.deleted_files.get(file.uuid)

    assert deleted_file.health_status is not FileSystemItemHealthStatus.GOOD
