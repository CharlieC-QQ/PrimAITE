# © Crown-owned copyright 2025, Defence Science and Technology Laboratory UK
import pytest
import yaml

from primaite.config.load import _EXAMPLE_CFG
from primaite.game.agent.scripted_agents.abstract_tap import (
    AbstractTAP,
    BaseKillChain,
    KillChainOptions,
    KillChainStageOptions,
    KillChainStageProgress,
)
from primaite.game.agent.scripted_agents.TAP001 import MobileMalwareKillChain, TAP001
from primaite.game.agent.scripted_agents.TAP003 import InsiderKillChain, TAP003
from primaite.session.environment import PrimaiteGymEnv

# Defining constants.

START_STEP = 1  # The starting step of the agent.
FREQUENCY = 2  # The frequency of kill chain stage progression (E.g it's next attempt at "attacking").
VARIANCE = 0  # The timestep variance between kill chain progression (E.g Next timestep = Frequency +/- variance)
ATTACK_AGENT_INDEX = 32


def uc7_tap003_env(**kwargs) -> PrimaiteGymEnv:
    """Setups the UC7 TAP003 Game with a 1 timestep start_step, frequency of 2 and probabilities set to 1 as well"""
    with open(_EXAMPLE_CFG / "uc7_config_tap003.yaml", mode="r") as uc7_config:
        cfg = yaml.safe_load(uc7_config)
        cfg["io_settings"]["save_sys_logs"] = False
        cfg["agents"][ATTACK_AGENT_INDEX]["agent_settings"]["start_step"] = START_STEP
        cfg["agents"][ATTACK_AGENT_INDEX]["agent_settings"]["frequency"] = FREQUENCY
        cfg["agents"][ATTACK_AGENT_INDEX]["agent_settings"]["variance"] = VARIANCE
        cfg["agents"][ATTACK_AGENT_INDEX]["agent_settings"]["repeat_kill_chain"] = kwargs["repeat_kill_chain"]
        cfg["agents"][ATTACK_AGENT_INDEX]["agent_settings"]["repeat_kill_chain_stages"] = kwargs[
            "repeat_kill_chain_stages"
        ]
        cfg["agents"][ATTACK_AGENT_INDEX]["agent_settings"]["kill_chain"]["MANIPULATION"]["probability"] = kwargs[
            "manipulation_probability"
        ]
        cfg["agents"][ATTACK_AGENT_INDEX]["agent_settings"]["kill_chain"]["ACCESS"]["probability"] = kwargs[
            "access_probability"
        ]
        cfg["agents"][ATTACK_AGENT_INDEX]["agent_settings"]["kill_chain"]["PLANNING"]["probability"] = kwargs[
            "planning_probability"
        ]
    env = PrimaiteGymEnv(env_config=cfg)
    return env


def test_tap003_repeating_kill_chain():
    """Tests to check that TAP003 repeats it's kill chain after success"""
    env = uc7_tap003_env(
        repeat_kill_chain=True,
        repeat_kill_chain_stages=True,
        manipulation_probability=1,
        access_probability=1,
        planning_probability=1,
    )
    tap003: TAP003 = env.game.agents["attacker"]
    for _ in range(40):  # This for loop should never actually fully complete.
        if tap003.current_kill_chain_stage == BaseKillChain.SUCCEEDED:
            break
        env.step(0)

    # Catches if the above for loop fully completes.
    # This test uses a probability of 1 for all stages and a variance of 2 timesteps
    # Thus the for loop above should never fail.
    # If this occurs then there is an error somewhere in either:
    # 1. The TAP Logic
    # 2. Failing Agent Actions are causing the TAP to fail. (See tap_return_handler).
    if tap003.current_kill_chain_stage != BaseKillChain.SUCCEEDED:
        pytest.fail("Attacker Never Reached SUCCEEDED - Please evaluate current TAP Logic.")

    # Stepping twice for the succeeded logic to kick in:
    env.step(0)
    env.step(0)

    assert tap003.current_kill_chain_stage.name == InsiderKillChain.RECONNAISSANCE.name
    assert tap003.next_kill_chain_stage.name == InsiderKillChain.PLANNING.name


def test_tap003_repeating_kill_chain_stages():
    """Tests to check that TAP003 repeats it's kill chain after failing a kill chain stage."""
    env = uc7_tap003_env(
        repeat_kill_chain=True,
        repeat_kill_chain_stages=True,
        manipulation_probability=1,
        # access_probability 0 = Will never be able to perform the access stage and progress to Manipulation.
        access_probability=0,
        planning_probability=1,
    )
    tap003: TAP003 = env.game.agents["attacker"]
    env.step(0)  # Skipping not started
    env.step(0)  # Successful on the first stage
    assert tap003.current_kill_chain_stage.name == InsiderKillChain.RECONNAISSANCE.name
    assert tap003.next_kill_chain_stage.name == InsiderKillChain.PLANNING.name
    env.step(0)  # Successful progression to the second stage
    env.step(0)
    assert tap003.current_kill_chain_stage.name == InsiderKillChain.PLANNING.name
    assert tap003.next_kill_chain_stage.name == InsiderKillChain.ACCESS.name
    env.step(0)  # Successfully moved onto access.
    env.step(0)
    assert tap003.current_kill_chain_stage.name == InsiderKillChain.ACCESS.name
    assert tap003.next_kill_chain_stage.name == InsiderKillChain.MANIPULATION.name
    env.step(0)  # Failure to progress past the third stage.
    env.step(0)
    assert tap003.current_kill_chain_stage.name == InsiderKillChain.ACCESS.name
    assert tap003.next_kill_chain_stage.name == InsiderKillChain.MANIPULATION.name
