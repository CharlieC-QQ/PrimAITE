# © Crown-owned copyright 2025, Defence Science and Technology Laboratory UK
"""yaml example.

agents:
  - name: agent_1
    action_space:
      actions:
        - do_nothing
        - node_service_start
        - node_service_stop
      action_map:
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from gymnasium import spaces

# from primaite.game.game import PrimaiteGame # TODO: Breaks things
from primaite.game.agent.actions.abstract import AbstractAction
from primaite.interface.request import RequestFormat

__all__ = ("DoNothingAction", "ActionManager")


class DoNothingAction(AbstractAction, identifier="do_nothing"):
    """Do Nothing Action."""

    class ConfigSchema(AbstractAction.ConfigSchema):
        """Configuration Schema for do_nothingAction."""

        type: str = "do_nothing"

    @classmethod
    def form_request(cls, config: ConfigSchema) -> RequestFormat:
        """Return the action formatted as a request which can be ingested by the PrimAITE simulation."""
        return ["do_nothing"]


class ActionManager:
    """Class which manages the action space for an agent."""

    def __init__(self, act_map: Optional[Dict[int, Dict]] = None) -> None:
        """Init method for ActionManager.

        :param act_map: Action map which maps integers to actions. Used for restricting the set of possible actions.
        :type act_map: Optional[Dict[int, Dict]]
        """
        self.action_map: Dict[int, Tuple[str, Dict]] = {}
        """
        Action mapping that converts an integer to a specific action and parameter choice.

        For example :
        {0: ("node_service_scan", {node_name:"client_1", service_name:"WebBrowser"})}
        """
        # allows restricting set of possible actions - TODO: Refactor to be a list?
        if act_map is None:
            # raise RuntimeError("Action map must be specified in the config file.")
            pass
        else:
            self.action_map = {i: (a["action"], a["options"]) for i, a in act_map.items()}
        # make sure all numbers between 0 and N are represented as dict keys in action map
        assert all([i in self.action_map.keys() for i in range(len(self.action_map))])

    def get_action(self, action: int) -> Tuple[str, Dict]:
        """Produce action in CAOS format."""
        """the agent chooses an action (as an integer), this is converted into an action in CAOS format"""
        """The CAOS format is basically a action identifier, followed by parameters stored in a dictionary"""
        act_identifier, act_options = self.action_map[action]
        return act_identifier, act_options

    def form_request(self, action_identifier: str, action_options: Dict) -> RequestFormat:
        """Take action in CAOS format and use the execution definition to change it into PrimAITE request format."""
        act_class = AbstractAction._registry[action_identifier]
        config = act_class.ConfigSchema(**action_options)
        return act_class.form_request(config=config)

    @property
    def space(self) -> spaces.Space:
        """Return the gymnasium action space for this agent."""
        return spaces.Discrete(len(self.action_map))

    @classmethod
    def from_config(cls, cfg: Dict) -> "ActionManager":
        """
        Construct an ActionManager from a config dictionary.

        The action space config supports must contain the following key:
            ``action_map`` - List of actions available to the agent, formatted as a dictionary where the key is the
            action number between 0 - N, and the value is the CAOS-formatted action.

        :param cfg: The action space config.
        :type cfg: Dict
        :return: The constructed ActionManager.
        :rtype: ActionManager
        """
        return cls(**cfg.get("options", {}), act_map=cfg.get("action_map"))
