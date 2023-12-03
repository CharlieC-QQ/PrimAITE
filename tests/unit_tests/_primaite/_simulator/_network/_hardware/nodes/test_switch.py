import pytest

from primaite.simulator.network.hardware.node_operating_state import NodeOperatingState
from primaite.simulator.network.hardware.nodes.switch import Switch


@pytest.fixture(scope="function")
def switch() -> Switch:
    switch: Switch = Switch(hostname="switch_1", num_ports=8, operating_state=NodeOperatingState.ON)
    switch.show()
    return switch


def test_describe_state(switch):
    state = switch.describe_state()
    assert len(state.get("ports")) is 8
    assert state.get("num_ports") is 8
