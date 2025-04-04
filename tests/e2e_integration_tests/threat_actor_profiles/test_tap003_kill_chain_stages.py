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
from primaite.game.agent.scripted_agents.TAP003 import InsiderKillChain, TAP003
from primaite.session.environment import PrimaiteGymEnv
from primaite.simulator.network.hardware.nodes.network.firewall import Firewall
from primaite.simulator.network.hardware.nodes.network.router import ACLAction, Router

# Defining constants.

START_STEP = 1  # The starting step of the agent.
FREQUENCY = 2  # The frequency of kill chain stage progression (E.g it's next attempt at "attacking").
VARIANCE = 0  # The timestep variance between kill chain progression (E.g Next timestep = Frequency +/- variance)
REPEAT_KILL_CHAIN = False  # Should the TAP repeat the kill chain after success/failure?
REPEAT_KILL_CHAIN_STAGES = False  # Should the TAP restart from it's previous stage on failure?
KILL_CHAIN_PROBABILITY = 1  # Blank probability for agent 'success'
ATTACK_AGENT_INDEX = 32


def uc7_tap003_env() -> PrimaiteGymEnv:
    """Setups the UC7 TAP003 Game with a 1 timestep start_step, frequency of 2 and probabilities set to 1 as well"""
    with open(_EXAMPLE_CFG / "uc7_config_tap003.yaml", mode="r") as uc7_config:
        cfg = yaml.safe_load(uc7_config)
        cfg["io_settings"]["save_sys_logs"] = False
        cfg["io_settings"]["save_agent_logs"] = True
        cfg["agents"][ATTACK_AGENT_INDEX]["agent_settings"]["start_step"] = START_STEP
        cfg["agents"][ATTACK_AGENT_INDEX]["agent_settings"]["frequency"] = FREQUENCY
        cfg["agents"][ATTACK_AGENT_INDEX]["agent_settings"]["variance"] = VARIANCE
        cfg["agents"][ATTACK_AGENT_INDEX]["agent_settings"]["repeat_kill_chain"] = REPEAT_KILL_CHAIN_STAGES
        cfg["agents"][ATTACK_AGENT_INDEX]["agent_settings"]["repeat_kill_chain_stages"] = REPEAT_KILL_CHAIN_STAGES
        cfg["agents"][ATTACK_AGENT_INDEX]["agent_settings"]["kill_chain"]["MANIPULATION"][
            "probability"
        ] = KILL_CHAIN_PROBABILITY
        cfg["agents"][ATTACK_AGENT_INDEX]["agent_settings"]["kill_chain"]["ACCESS"][
            "probability"
        ] = KILL_CHAIN_PROBABILITY
        cfg["agents"][ATTACK_AGENT_INDEX]["agent_settings"]["kill_chain"]["PLANNING"][
            "probability"
        ] = KILL_CHAIN_PROBABILITY
        cfg["agents"][ATTACK_AGENT_INDEX]["agent_settings"]["kill_chain"]["EXPLOIT"][
            "probability"
        ] = KILL_CHAIN_PROBABILITY
    env = PrimaiteGymEnv(env_config=cfg)
    return env


def environment_step(i: int, env: PrimaiteGymEnv) -> PrimaiteGymEnv:
    """Carries out i (given parameter) steps in the environment.."""
    for x in range(i):
        env.step(0)
    return env


def test_tap003_kill_chain_stage_reconnaissance():
    """Tests the successful/failed handlers in the reconnaissance stage in the Insider Kill Chain InsiderKillChain"""

    # Instantiating the relevant simulation/game objects:
    env = uc7_tap003_env()
    tap003: TAP003 = env.game.agents["attacker"]
    assert tap003.current_kill_chain_stage == BaseKillChain.NOT_STARTED

    # Frequency is set to two steps
    env = environment_step(i=2, env=env)

    # Testing that TAP003 Enters into the expected kill chain stages
    assert tap003.current_kill_chain_stage.name == InsiderKillChain.RECONNAISSANCE.name


def test_tap003_kill_chain_stage_planning():
    """Tests the successful/failed handlers in the planning stage in the Insider Kill Chain (TAP003)"""
    env = uc7_tap003_env()
    tap003: TAP003 = env.game.agents["attacker"]

    assert tap003.current_kill_chain_stage == BaseKillChain.NOT_STARTED

    env = environment_step(i=2, env=env)

    assert tap003.current_kill_chain_stage.name == InsiderKillChain.RECONNAISSANCE.name
    assert tap003.next_kill_chain_stage.name == InsiderKillChain.PLANNING.name

    env = environment_step(i=2, env=env)

    # Testing that TAP003 Enters into the expected kill chain stages
    assert tap003.current_kill_chain_stage.name == InsiderKillChain.PLANNING.name
    assert tap003.next_kill_chain_stage.name == InsiderKillChain.ACCESS.name

    env = environment_step(i=2, env=env)

    # Testing that the stage successful - TAP003 has loaded it's starting network knowledge into it's network knowledge.

    # At this point TAP003 will parse it's starting network knowledge config into it's a private attribute (`network_knowledge`)
    assert (
        tap003.network_knowledge["credentials"]
        == tap003.config.agent_settings.kill_chain.PLANNING.starting_network_knowledge["credentials"]
    )


def test_tap003_kill_chain_stage_access():
    """Tests the successful/failed handlers in the access stage in the InsiderKillChain"""
    env = uc7_tap003_env()
    tap003: TAP003 = env.game.agents["attacker"]

    assert tap003.current_kill_chain_stage == BaseKillChain.NOT_STARTED

    env = environment_step(i=2, env=env)

    assert tap003.current_kill_chain_stage.name == InsiderKillChain.RECONNAISSANCE.name
    assert tap003.next_kill_chain_stage.name == InsiderKillChain.PLANNING.name

    env = environment_step(i=2, env=env)

    assert tap003.current_kill_chain_stage.name == InsiderKillChain.PLANNING.name
    assert tap003.next_kill_chain_stage.name == InsiderKillChain.ACCESS.name

    env = environment_step(i=2, env=env)

    assert tap003.current_kill_chain_stage.name == InsiderKillChain.ACCESS.name
    assert tap003.next_kill_chain_stage.name == InsiderKillChain.MANIPULATION.name


def test_tap003_kill_chain_stage_manipulation():
    """Tests the successful/failed handlers in the manipulation stage in the InsiderKillChain"""
    env = uc7_tap003_env()
    tap003: TAP003 = env.game.agents["attacker"]

    assert tap003.current_kill_chain_stage == BaseKillChain.NOT_STARTED

    env = environment_step(i=2, env=env)

    assert tap003.current_kill_chain_stage.name == InsiderKillChain.RECONNAISSANCE.name
    assert tap003.next_kill_chain_stage.name == InsiderKillChain.PLANNING.name

    env = environment_step(i=2, env=env)

    assert tap003.current_kill_chain_stage.name == InsiderKillChain.PLANNING.name
    assert tap003.next_kill_chain_stage.name == InsiderKillChain.ACCESS.name

    env = environment_step(i=2, env=env)

    assert tap003.current_kill_chain_stage.name == InsiderKillChain.ACCESS.name
    assert tap003.next_kill_chain_stage.name == InsiderKillChain.MANIPULATION.name

    env = environment_step(i=2, env=env)

    assert tap003.current_kill_chain_stage.name == InsiderKillChain.MANIPULATION.name

    # Testing that the stage successfully impacted the simulation - Accounts Altered
    env = environment_step(i=5, env=env)
    st_intra_prv_rt_dr_1: Router = env.game.simulation.network.get_node_by_hostname("ST_INTRA-PRV-RT-DR-1")
    assert tap003.current_kill_chain_stage.name == InsiderKillChain.MANIPULATION.name
    assert st_intra_prv_rt_dr_1.user_manager.admins["admin"].password == "red_pass"

    env = environment_step(i=5, env=env)
    st_intra_prv_rt_cr: Router = env.game.simulation.network.get_node_by_hostname("ST_INTRA-PRV-RT-CR")
    assert tap003.current_kill_chain_stage.name == InsiderKillChain.MANIPULATION.name
    assert st_intra_prv_rt_cr.user_manager.admins["admin"].password == "red_pass"

    env = environment_step(i=5, env=env)
    rem_pub_rt_dr: Router = env.game.simulation.network.get_node_by_hostname("REM-PUB-RT-DR")
    assert rem_pub_rt_dr.user_manager.admins["admin"].password == "red_pass"


def test_tap003_kill_chain_stage_exploit():
    """Tests the successful/failed handlers in the exploit stage in the InsiderKillChain"""

    env = uc7_tap003_env()
    tap003: TAP003 = env.game.agents["attacker"]
    # The TAP003's Target Router/Firewall
    st_intra_prv_rt_dr_1: Router = env.game.simulation.network.get_node_by_hostname("ST_INTRA-PRV-RT-DR-1")
    st_intra_prv_rt_cr: Router = env.game.simulation.network.get_node_by_hostname("ST_INTRA-PRV-RT-CR")
    rem_pub_rt_dr: Router = env.game.simulation.network.get_node_by_hostname("REM-PUB-RT-DR")

    assert tap003.current_kill_chain_stage == BaseKillChain.NOT_STARTED

    env = environment_step(i=2, env=env)

    assert tap003.current_kill_chain_stage.name == InsiderKillChain.RECONNAISSANCE.name
    assert tap003.next_kill_chain_stage.name == InsiderKillChain.PLANNING.name

    env = environment_step(i=2, env=env)

    assert tap003.current_kill_chain_stage.name == InsiderKillChain.PLANNING.name
    assert tap003.next_kill_chain_stage.name == InsiderKillChain.ACCESS.name

    env = environment_step(i=2, env=env)

    assert tap003.current_kill_chain_stage.name == InsiderKillChain.ACCESS.name
    assert tap003.next_kill_chain_stage.name == InsiderKillChain.MANIPULATION.name

    env = environment_step(i=16, env=env)

    assert tap003.current_kill_chain_stage.name == InsiderKillChain.EXPLOIT.name

    # Testing that the stage successfully impacted the simulation - Malicious ACL Added:
    for _ in range(14):
        env.step(0)

    # Tests that the ACL has been added and that the action is deny.
    st_intra_prv_rt_dr_1_acl_list = st_intra_prv_rt_dr_1.acl
    assert st_intra_prv_rt_dr_1_acl_list.acl[1].action != None
    assert st_intra_prv_rt_dr_1_acl_list.acl[1].action == ACLAction.DENY

    st_intra_prv_rt_cr_acl_list = st_intra_prv_rt_cr.acl
    assert st_intra_prv_rt_cr_acl_list.acl[1].action != None
    assert st_intra_prv_rt_cr_acl_list.acl[1].action == ACLAction.DENY

    rem_pub_rt_dr_acl_list = rem_pub_rt_dr.acl
    assert rem_pub_rt_dr_acl_list.acl[1].action != None
    assert rem_pub_rt_dr_acl_list.acl[1].action == ACLAction.DENY
