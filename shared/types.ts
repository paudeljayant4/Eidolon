export type TerrainType = 
  | 'forest' 
  | 'mountain' 
  | 'desert' 
  | 'river' 
  | 'plains' 
  | 'city' 
  | 'ocean'

export type ResourceType = 
  | 'wood' 
  | 'stone' 
  | 'iron' 
  | 'food' 
  | 'water' 
  | 'energy'

export enum BuildingType {
  Farm = 'farm',
  Mine = 'mine',
  LumberCamp = 'lumber_camp',
  Quarry = 'quarry',
  Market = 'market',
  Barracks = 'barracks',
  Workshop = 'workshop',
  Palace = 'palace',
  Temple = 'temple',
}

export enum ResourceTrigger {
  Wood = 'wood',
  Stone = 'stone',
  Iron = 'iron',
  Food = 'food',
  Water = 'water',
  Energy = 'energy',
}

export interface Position {
  x: number
  y: number
}

export interface WorldConfig {
  width: number
  height: number
  seed?: number
}

export interface Region {
  id: string
  name: string
  position: Position
  terrain: TerrainType
  resources: ResourceType[]
  complexity: number
}

export interface City {
  id: string
  name: string
  regionId: string
  population: number
  buildings: string[] // Building IDs
  resources: ResourceType[]
  position: Position
}

export interface Building {
  id: string
  type: BuildingType
  regionId: string
  position: Position
  level: number
  resourcesProduced: ResourceType[]
  resourcesConsumed: ResourceType[]
  capacity: number
}

export interface Resource {
  id: string
  type: ResourceType
  amount: number
  maxAmount: number
  position: Position
  regionId: string
}

export interface AgentId = string

export interface Agent {
  id: AgentId
  position: Position
  personality: Personality
  needs: Needs
  skills: Skills
  inventory: Inventory
  relationships: Relationships
  organization?: string
  health: number
  energy: number
}

export interface Personality {
  traits: Record<string, number> // Big Five or custom traits
  disposition: 'friendly' | 'neutral' | 'hostile'
  riskTolerance: number
  altruism: number
}

export interface Needs {
  hunger: number
  thirst: number
  rest: number
  social: number
  safety: number
}

export interface Skills {
  [skill: string]: number
}

export interface Inventory {
  resources: Record<ResourceType, number>
  capacity: number
}

export interface Relationships {
  [agentId: string]: number // -1 (hostile) to 1 (friendly)
}

export interface Organization {
  id: string
  name: string
  type: 'guild' | 'company' | 'party' | 'faction'
  members: AgentId[]
  goals: string[]
  pooledResources: Record<ResourceType, number>
  headquarters?: string
}

export interface Market {
  id: string
  regionId: string
  supplies: Record<ResourceType, number>
  demands: Record<ResourceType, number>
  prices: Record<ResourceType, number>
}

export interface Event {
  id: string
  timestamp: number
  type: EventType
  source?: string
  target?: string
  data: Record<string, unknown>
  propagated: boolean
}

export enum EventType {
  Birth = 'birth',
  Death = 'death',
  Trade = 'trade',
  Conflict = 'conflict',
  Move = 'move',
  Build = 'build',
  Research = 'research',
  ResourceDepletion = 'resource_depletion',
  PriceChange = 'price_change',
  Election = 'election',
  Treaty = 'treaty',
  War = 'war',
  MineCollapse = 'mine_collapse',
  Flood = 'flood',
  Famine = 'famine',
}