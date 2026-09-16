import random
from uuid import uuid4
from ._types import (
    WorldConfig, TerrainType, ResourceType, Position, Region,
    Building, BuildingType, Resource, Agent, Market,
    Event, EventType, Needs, Personality, Skills, Inventory,
    Relationships, City, Organization
)
AgentId = str


def generate_terrain(width: int, height: int, seed: int | None = None) -> list[list[TerrainType]]:
    """Generate a 2D terrain map using cellular automata."""
    if seed is not None:
        random.seed(seed)
    
    # Start with random terrain
    grid = [[random.choice(list(TerrainType)) for _ in range(height)] for _ in range(width)]
    
    # Apply cellular automata smoothing for more natural boundaries
    for _ in range(3):
        new_grid = [row[:] for row in grid]
        for x in range(width):
            for y in range(height):
                count = 0
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        nx, ny = (x + dx) % width, (y + dy) % height
                        if nx < 0: nx += width
                        if ny < 0: ny += height
                        if grid[nx][ny] in [TerrainType.FOREST, TerrainType.MOUNTAIN]:
                            count += 1
                new_grid[x][y] = TerrainType.FOREST if count > 4 else TerrainType.PLAINS
        grid = new_grid
    
    return grid


def generate_resources(
    terrain: list[list[TerrainType]], 
    width: int, 
    height: int, 
    seed: int | None = None
) -> list[Resource]:
    """Place resources based on terrain type."""
    if seed is not None:
        random.seed(seed)
    
    resources: list[Resource] = []
    
    for x in range(width):
        for y in range(height):
            tile = terrain[x][y]
            pos = Position(x, y)
            
            if tile == TerrainType.FOREST:
                resources.append(Resource(
                    id=str(uuid4()),
                    type=ResourceType.WOOD,
                    amount=random.randint(50, 200),
                    maxAmount=200,
                    position=pos,
                    regionId=f"region-{x}-{y}"
                ))
            elif tile == TerrainType.MOUNTAIN:
                resources.append(Resource(
                    id=str(uuid4()),
                    type=ResourceType.IRON,
                    amount=random.randint(20, 80),
                    maxAmount=80,
                    position=pos,
                    regionId=f"region-{x}-{y}"
                ))
            elif tile == TerrainType.DESERT:
                resources.append(Resource(
                    id=str(uuid4()),
                    type=ResourceType.STONE,
                    amount=random.randint(30, 100),
                    maxAmount=100,
                    position=pos,
                    regionId=f"region-{x}-{y}"
                ))
            elif tile == TerrainType.PLAINS:
                resources.append(Resource(
                    id=str(uuid4()),
                    type=ResourceType.FOOD,
                    amount=random.randint(40, 150),
                    maxAmount=150,
                    position=pos,
                    regionId=f"region-{x}-{y}"
                ))
            elif tile == TerrainType.RIVER:
                resources.append(Resource(
                    id=str(uuid4()),
                    type=ResourceType.WATER,
                    amount=random.randint(60, 120),
                    maxAmount=120,
                    position=pos,
                    regionId=f"region-{x}-{y}"
                ))
    
    return resources


def generate_regions(
    width: int, 
    height: int, 
    seed: int | None = None
) -> list[Region]:
    """Generate regions from terrain."""
    if seed is not None:
        random.seed(seed)
    
    terrain = generate_terrain(width, height, seed)
    regions: list[Region] = []
    
    for x in range(width):
        for y in range(height):
            terrain_type = terrain[x][y]
            
            # Determine resources based on terrain
            resource_types: list[ResourceType] = []
            if terrain_type == TerrainType.FOREST:
                resource_types = [ResourceType.WOOD]
            elif terrain_type == TerrainType.MOUNTAIN:
                resource_types = [ResourceType.IRON]
            elif terrain_type == TerrainType.DESERT:
                resource_types = [ResourceType.STONE]
            elif terrain_type == TerrainType.PLAINS:
                resource_types = [ResourceType.FOOD]
            elif terrain_type == TerrainType.RIVER:
                resource_types = [ResourceType.WATER]
            
            regions.append(Region(
                id=f"region-{x}-{y}",
                name=f"Region {x},{y}",
                position=Position(x, y),
                terrain=terrain_type,
                resources=resource_types,
                complexity=random.randint(1, 3)
            ))
    
    return regions


def generate_cities(
    regions: list[Region], 
    numCities: int = 3
) -> list[City]:
    """Generate cities from regions."""
    cities: list[City] = []
    city_regions = random.sample(regions, min(numCities, len(regions)))
    
    for region in city_regions:
        # Determine building types based on terrain
        building_types: list[BuildingType] = []
        if region.terrain == TerrainType.FOREST:
            building_types = [BuildingType.LUMBER_CAMP, BuildingType.MARKET]
        elif region.terrain == TerrainType.MOUNTAIN:
            building_types = [BuildingType.MINE, BuildingType.WORKSHOP]
        elif region.terrain == TerrainType.DESERT:
            building_types = [BuildingType.QUARRY]
        elif region.terrain == TerrainType.PLAINS:
            building_types = [BuildingType.FARM, BuildingType.MARKET]
        elif region.terrain == TerrainType.RIVER:
            building_types = [BuildingType.FARM]
        
        # Add a market always
        if BuildingType.MARKET not in building_types:
            building_types.insert(0, BuildingType.MARKET)
        
        buildings: list[Building] = []
        for i, btype in enumerate(building_types):
            pos_x = (i * 10) % max(region.position.x, 1)
            buildings.append(Building(
                id=str(uuid4()),
                type=btype,
                regionId=region.id,
                position=Position(x=pos_x, y=i),
                level=1,
                resourcesProduced=[],
                resourcesConsumed=[],
                capacity=0
            ))
        
        cities.append(City(
            id=str(uuid4()),
            name=f"City-{region.id}",
            regionId=region.id,
            population=random.randint(100, 500),
            buildings=[b.id for b in buildings],
            resources=[],
            position=Position(x=region.position.x * 10 or 10, y=region.position.y * 10 or 10)
        ))
    
    return cities


def generate_world(config: WorldConfig) -> dict:
    """Generate a complete world given a config."""
    random.seed(config.seed)
    
    regions = generate_regions(config.width, config.height, config.seed)
    resources = generate_resources(
        [[regions[i * config.width + j].terrain for j in range(config.height)] 
         for i in range(config.width)],
        config.width, config.height, config.seed
    )
    
    cities = generate_cities(regions, numCities=3)
    
    # Create markets for each region
    markets: list[Market] = []
    for region in regions:
        markets.append(Market(
            id=f"market-{region.id}",
            regionId=region.id
        ))
    
# Create multiple agents
    agents: list[Agent] = []
    dispositions = ["friendly", "neutral", "hostile"]
    for i in range(5):
        disp = random.choice(dispositions)
        agents.append(Agent(
            id=f"agent-{i}",
            position=Position(
                random.randint(0, config.width - 1),
                random.randint(0, config.height - 1)
            ),
            personality=Personality(
                traits={"openness": random.random(), "conscientiousness": random.random(),
                        "extraversion": random.random(), "agreeableness": random.random(),
                        "neuroticism": random.random()},
                disposition=disp,
                riskTolerance=random.random(),
                altruism=random.random()
            ),
            needs=Needs(),
            skills=Skills(values={}),
            inventory=Inventory(),
            relationships=Relationships(values={}),
            organization=None,
            health=1.0,
            energy=1.0,
        ))

    # Create organizations
    organizations: list[Organization] = []
    org_id = f"org-main-{config.seed}"
    organizations.append(Organization(
        id=org_id, name="Main Guild", leader_id="agent-0",
        organization_type="guild", members=["agent-0"]
    ))
    # Assign organization to agents
    for i, agent in enumerate(agents):
        if i == 0:
            agent.organization = org_id

    return {
        "config": config,
        "regions": regions,
        "resources": resources,
        "cities": cities,
        "markets": markets,
        "agents": agents,
        "agent": agents[0] if agents else None,
        "organizations": organizations,
        "events": []
    }