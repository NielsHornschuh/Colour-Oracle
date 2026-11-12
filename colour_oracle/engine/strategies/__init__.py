"""Het register van strategieën. Voeg een eigen strategie toe door hier een regel bij te zetten."""

from colour_oracle.engine.strategies.markov import MarkovStrategy
from colour_oracle.engine.strategies.frequency import FrequencyStrategy
from colour_oracle.engine.strategies.random_baseline import RandomStrategy
from colour_oracle.engine.strategies.streak import StreakStrategy
from colour_oracle.engine.strategies.step import StepStrategy
from colour_oracle.engine.strategies.lag import LagStrategy
from colour_oracle.engine.strategies.reaction import ReactionStrategy
from colour_oracle.engine.strategies.position import PositionStrategy
from colour_oracle.engine.strategies.pair import PairStrategy


# Koppelt elke sleutel uit ACTIVE_STRATEGIES aan zijn klasse
STRATEGY_CLASSES = {
    "colours": MarkovStrategy,
    "bias": FrequencyStrategy,
    "random": RandomStrategy,
    "streak": StreakStrategy,
    "step": StepStrategy,
    "lag": LagStrategy,
    "reaction": ReactionStrategy,
    "position": PositionStrategy,
    "pair": PairStrategy,
}
