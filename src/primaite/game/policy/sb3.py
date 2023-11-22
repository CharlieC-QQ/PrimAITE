"""Stable baselines 3 policy."""
from pathlib import Path
from typing import Literal, Optional, Type, TYPE_CHECKING, Union

from stable_baselines3 import A2C, PPO
from stable_baselines3.a2c import MlpPolicy as A2C_MLP
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.evaluation import evaluate_policy
from stable_baselines3.ppo import MlpPolicy as PPO_MLP

from primaite.game.policy.policy import PolicyABC

if TYPE_CHECKING:
    from primaite.game.game import PrimaiteGame, TrainingOptions


class SB3Policy(PolicyABC, identifier="SB3"):
    """Single agent RL policy using stable baselines 3."""

    def __init__(self, session: "PrimaiteGame", algorithm: Literal["PPO", "A2C"], seed: Optional[int] = None):
        """Initialize a stable baselines 3 policy."""
        super().__init__(session=session)

        self._agent_class: Type[Union[PPO, A2C]]
        if algorithm == "PPO":
            self._agent_class = PPO
            policy = PPO_MLP
        elif algorithm == "A2C":
            self._agent_class = A2C
            policy = A2C_MLP
        else:
            raise ValueError(f"Unknown algorithm `{algorithm}` for stable_baselines3 policy")
        self._agent = self._agent_class(
            policy=policy,
            env=self.session.env,
            n_steps=128,  # this is not the number of steps in an episode, but the number of steps in a batch
            seed=seed,
        )

    def learn(self, n_episodes: int, timesteps_per_episode: int) -> None:
        """Train the agent."""
        if self.session.io_manager.settings.save_checkpoints:
            checkpoint_callback = CheckpointCallback(
                save_freq=timesteps_per_episode * self.session.io_manager.settings.checkpoint_interval,
                save_path=self.session.io_manager.generate_model_save_path("sb3"),
                name_prefix="sb3_model",
            )
        else:
            checkpoint_callback = None
        self._agent.learn(total_timesteps=n_episodes * timesteps_per_episode, callback=checkpoint_callback)

    def eval(self, n_episodes: int, deterministic: bool) -> None:
        """Evaluate the agent."""
        reward_data = evaluate_policy(
            self._agent,
            self.session.env,
            n_eval_episodes=n_episodes,
            deterministic=deterministic,
            return_episode_rewards=True,
        )
        print(reward_data)

    def save(self, save_path: Path) -> None:
        """
        Save the current policy parameters.

        Warning: The recommended way to save model checkpoints is to use a callback within the `learn()` method. Please
        refer to https://stable-baselines3.readthedocs.io/en/master/guide/callbacks.html for more information.
        Therefore, this method is only used to save the final model.
        """
        self._agent.save(save_path)

    def load(self, model_path: Path) -> None:
        """Load agent from a checkpoint."""
        self._agent = self._agent_class.load(model_path, env=self.session.env)

    @classmethod
    def from_config(cls, config: "TrainingOptions", session: "PrimaiteGame") -> "SB3Policy":
        """Create an agent from config file."""
        return cls(session=session, algorithm=config.rl_algorithm, seed=config.seed)
