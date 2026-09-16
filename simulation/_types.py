from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple
import random
import uuid

AgentId = str


class TerrainType(Enum):
    FOREST = "forest"
    MOUNTAIN = "mountain"
    DESERT = "desert"
    RIVER = "river"
    PLAINS = "plains"
    CITY = "city"
    OCEAN = "ocean"


class ResourceType(Enum):
    WOOD = "wood"
    STONE = "stone"
    IRON = "iron"
    FOOD = "food"
    WATER = "water"
    ENERGY = "energy"


class BuildingType(Enum):
    FARM = "farm"
    MINE = "mine"
    LUMBER_CAMP = "lumber_camp"
    QUARRY = "quarry"
    MARKET = "market"
    BARRACKS = "barracks"
    WORKSHOP = "workshop"
    PALACE = "palace"
    TEMPLE = "temple"


class EventType:
    BIRTH = "birth"
    DEATH = "death"
    TRADE = "trade"
    CONFLICT = "conflict"
    MOVE = "move"
    BUILD = "build"
    RESEARCH = "research"
    RESOURCE_DEPLETION = "resource_depletion"
    PRICE_CHANGE = "price_change"
    ELECTION = "election"
    TREATY = "treaty"
    WAR = "war"
    MINE_COLLAPSE = "mine_collapse"
    FLOOD = "flood"
    FAMINE = "famine"


@dataclass
class Position:
    x: int
    y: int


@dataclass
class WorldConfig:
    width: int
    height: int
    seed: Optional[int] = None

    def __post_init__(self):
        if self.width < 10 or self.width > 100:
            raise ValueError("World width must be between 10 and 100")
        if self.height < 10 or self.height > 100:
            raise ValueError("World height must be between 10 and 100")


@dataclass
class Region:
    id: str
    name: str
    position: Position
    terrain: TerrainType
    resources: List[ResourceType]
    complexity: int = 1


@dataclass
class Building:
    id: str
    type: BuildingType
    regionId: str
    position: Position
    level: int = 1
    resourcesProduced: List[ResourceType] = field(default_factory=list)
    resourcesConsumed: List[ResourceType] = field(default_factory=list)
    capacity: int = 0


@dataclass
class Resource:
    id: str
    type: ResourceType
    amount: int
    maxAmount: int
    position: Position
    regionId: str


@dataclass
class Personality:
    traits: Dict[str, float] = field(default_factory=dict)
    disposition: str = "neutral"  # friendly, neutral, hostile
    riskTolerance: float = 0.5
    altruism: float = 0.5


@dataclass
class Needs:
    hunger: float = 1.0
    thirst: float = 1.0
    rest: float = 1.0
    social: float = 1.0
    safety: float = 1.0


@dataclass
class Skills:
    values: Dict[str, float] = field(default_factory=dict)


@dataclass
class Inventory:
    resources: Dict[ResourceType, int] = field(default_factory=dict)
    capacity: int = 100


@dataclass
class Relationships:
    values: Dict[str, float] = field(default_factory=dict)  # agent_id -> -1 to 1


@dataclass
class Agent:
    id: str
    position: Position
    personality: Personality
    needs: Needs
    skills: Skills
    inventory: Inventory
    relationships: Relationships
    organization: Optional[str] = None
    health: float = 1.0
    energy: float = 1.0


@dataclass
class Market:
    id: str
    regionId: str
    supplies: Dict[ResourceType, int] = field(default_factory=dict)
    demands: Dict[ResourceType, int] = field(default_factory=dict)
    prices: Dict[ResourceType, float] = field(default_factory=lambda: {
        r: 1.0 for r in ResourceType
    })


@dataclass
class City:
    id: str
    name: str
    regionId: str
    population: int
    buildings: List[str] = field(default_factory=list)
    resources: List[ResourceType] = field(default_factory=list)
    position: Position = field(default_factory=Position)


@dataclass
class Event:
    id: str
    timestamp: int
    type: str
    source: Optional[str] = None
    target: Optional[str] = None
    data: Dict[str, object] = field(default_factory=dict)
    propagated: bool = False
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "type": self.type,
            "source": self.source,
            "target": self.target,
            "data": self.data,
            "propagated": self.propagated
        }