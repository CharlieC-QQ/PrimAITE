# © Crown-owned copyright 2025, Defence Science and Technology Laboratory UK
import pytest
from pydantic import ValidationError

from primaite.interface.request import RequestResponse


def test_creating_response_object():
    """Test that we can create a response object with given parameters."""
    r1 = RequestResponse(status="success", data={"test_data": 1, "other_data": 2})
    r2 = RequestResponse(status="unreachable")
    r3 = RequestResponse(data={"test_data": "is_good"})
    r4 = RequestResponse()
    assert isinstance(r1, RequestResponse)
    assert isinstance(r2, RequestResponse)
    assert isinstance(r3, RequestResponse)
    assert isinstance(r4, RequestResponse)


def test_creating_response_from_boolean():
    """Test that we can build a response with a single boolean."""
    r1 = RequestResponse.from_bool(True)
    assert r1.status == "success"

    r2 = RequestResponse.from_bool(False)
    assert r2.status == "failure"


@pytest.mark.skip("Disable validation due to performance hit.")
def test_response_from_invalid_options():
    """Test that we get a validation error if a non-boolean is passed."""
    with pytest.raises(ValidationError):
        r3 = RequestResponse.from_bool(1)
    with pytest.raises(ValidationError):
        r4 = RequestResponse.from_bool("good")
    with pytest.raises(ValidationError):
        r5 = RequestResponse.from_bool({"data": True})
