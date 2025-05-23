# © Crown-owned copyright 2025, Defence Science and Technology Laboratory UK
from primaite.simulator.system.applications.application import ApplicationOperatingState
from primaite.simulator.system.software import SoftwareHealthState


def test_scan(application):
    assert application.operating_state == ApplicationOperatingState.CLOSED
    assert application.health_state_visible == SoftwareHealthState.UNUSED

    application.run()
    assert application.operating_state == ApplicationOperatingState.RUNNING
    assert application.health_state_visible == SoftwareHealthState.UNUSED

    application.scan()
    assert application.operating_state == ApplicationOperatingState.RUNNING
    assert application.health_state_visible == SoftwareHealthState.GOOD


def test_run_application(application):
    assert application.operating_state == ApplicationOperatingState.CLOSED
    assert application.health_state_actual == SoftwareHealthState.GOOD

    application.run()
    assert application.operating_state == ApplicationOperatingState.RUNNING
    assert application.health_state_actual == SoftwareHealthState.GOOD


def test_close_application(application):
    application.run()
    assert application.operating_state == ApplicationOperatingState.RUNNING
    assert application.health_state_actual == SoftwareHealthState.GOOD

    application.close()
    assert application.operating_state == ApplicationOperatingState.CLOSED
    assert application.health_state_actual == SoftwareHealthState.GOOD


def test_application_describe_states(application):
    assert application.operating_state == ApplicationOperatingState.CLOSED
    assert application.health_state_actual == SoftwareHealthState.GOOD

    assert SoftwareHealthState.GOOD.value == application.describe_state().get("health_state_actual")

    application.run()
    assert SoftwareHealthState.GOOD.value == application.describe_state().get("health_state_actual")

    application.set_health_state(SoftwareHealthState.COMPROMISED)
    assert SoftwareHealthState.COMPROMISED.value == application.describe_state().get("health_state_actual")

    application.fix()
    assert SoftwareHealthState.FIXING.value == application.describe_state().get("health_state_actual")
