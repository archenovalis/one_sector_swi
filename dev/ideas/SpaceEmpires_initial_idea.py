import enum

class State(enum.Enum):
    EXPANSION = 1
    CONSOLIDATE = 2
    DEFENSE = 3
    WAR_INVADE = 4
    WAR_DEFENSE = 5
    WAR_CONSOLIDATE = 6

class FactionManager:
    def __init__(self):
        self.state = State.CONSOLIDATE
        self.previous_state = self.state
        self.pirate_activity = 0
        self.weighted_scores = {
            'economy': 0.0,
            'military': 0.0,
            'industry': 0.0
        }
        self.sectors = []
        self.resources = {}
        self.ships = []
        self.stations = []
        self.score_weights = {
            'economy': 0.4,
            'military': 0.3,
            'industry': 0.3
        }
        self.score_emergency_threshholds = {
            'economy': 0.2,
            'military': 0.1,
            'industry': 0.1
        }
        self.score_emergency_weights = {
            'economy': 0.7,
            'military': 0.7,
            'industry': 0.7
        }
        # state weights
        self.state_weights = {
            State.WAR_INVADE: {'economy': 0.8, 'military': 1.2, 'industry': 0.8},
            State.WAR_DEFENSE: {'economy': 0.8, 'military': 1.2, 'industry': 1.0},
            State.WAR_CONSOLIDATE: {'economy': 1.0, 'military': 1.2, 'industry': 1.2},
            State.EXPANSION: {'economy': 1.0, 'military': 1.0, 'industry': 1.2},
            State.CONSOLIDATE: {'economy': 1.2, 'military': 1.0, 'industry': 1.2},
            State.DEFENSE: {'economy': 1.0, 'military': 1.2, 'industry': 1.0}
        }
        self.resource_weights = {
            'availability': 0.3,
            'on_hand': 0.2,
            'extraction_rate': 0.2,
            'transport_efficiency': 0.1,
            'demand': 0.1,
            'saturation': 0.1
        }
        self.military_weights = {
            'scouts': 0.1,
            'stations': 0.6,
            'defensive': 0.4,
            'offensive': 0.3,
        }
        self.state_threshholds = {
            'eco_expansion': 0.7,
            'eco_consolidation': 0.5,
            'ind_expansion': 0.5,
            'ind_consolidation': 0.3,
            'mil_expansion': 0.5,
            'mil_defense': 0.3,
            'mil_invade': 0.7
        }
        self.sector_strategicValue = {
            'border': 400,
            'core': 200,
            'primary': 400,  # Additional value for sectors with shipyards or wharfs
            'gates': [50, 100, 300, 600]
        }
        self.sectorValuePerThreatscorePerSector = 100

    def update(self):
        # Updates all scores and checks for state changes
        self.run_scoring_and_state_check()

    def run_scoring_and_state_check(self):
        raw_scores = self.calculate_raw_scores()
        emergencies = self.check_emergencies(raw_scores)
        self.check_state_change(raw_scores)
        self.weighted_scores = self.apply_weights(raw_scores, emergencies)        

    def calculate_raw_scores(self):
        # Calculate total defense needed across all sectors
        total_desired_defense_threatscore = sum(self.calculate_sector_desired_threatscore(sector) for sector in self.sectors)
        
        economy_score = self.calculate_raw_economy_score()
        military_score = self.calculate_raw_military_score(total_desired_defense_threatscore)
        industry_score = self.calculate_raw_industry_score()
        return (economy_score, military_score, industry_score)

    def calculate_raw_economy_score(self):
        # Average score of all resources, aligning with the economy score concept
        return sum(self.calculate_resource_score(resource) for resource in self.resources.values()) / len(self.resources) if self.resources else 0

    def calculate_resource_score(self, resource):
        weights = self.resource_weights
        availability = sum(sector.resource_amount for sector in self.sectors)
        extraction_rate = sum(ship.threatscore for ship in self.ships if ship.type == "Miner")
        # Incorporate pirate activity to affect transport efficiency
        transport_efficiency = sum(ship.load_capacity for ship in self.ships if ship.type == "Transport") * (1-self.pirate_activity)
        
        # Flatten list of demands and on_hand resources from all stations
        demand = sum(resource.amount for station in self.stations for moduleResource in station.productionModules for resource in moduleResource.resources if resource.type == resource.type)
        on_hand = sum(resource.amount for station in self.stations for stationResource in station.resources if stationResource.type == resource.type)
        saturation = on_hand / demand if demand > 0 else 0

        # Update resource stats
        if resource.type not in self.resources:
            self.resources[resource.type] = {
                'demand': 0,
                'on_hand': 0,
                'saturation': None
            }
        self.resources[resource.type]['demand'] += demand
        self.resources[resource.type]['on_hand'] += on_hand
        self.resources[resource.type]['saturation'] = (self.resources[resource.type]['saturation'] + saturation) / 2 if self.resources[resource.type]['saturation'] is not None else saturation

        return (availability * weights['availability'] + 
                on_hand * weights['on_hand'] + 
                extraction_rate * weights['extraction_rate'] +
                transport_efficiency * weights['transport_efficiency'] + 
                demand * weights['demand'] + 
                saturation * weights['saturation'])

    def calculate_sector_desired_threatscore(self, sector):
        # Calculates strategic importance of a sector for military scoring
        resource_value = self.get_resource_value(sector.resources)
        strategic_value = self.get_strategic_value(sector)
        economic_value = sum(station.price * 2 if station.iswharf or station.isshipyard else station.price for station in sector.stations)
        
        # Pirate activity affects both economy and military scores
        pirate_activity = sector.pirate_activity  # Number of ships destroyed by pirates / total number of non-military ships assigned to sector
        self.pirate_activity = (self.pirate_activity + pirate_activity) / 2 if self.pirate_activity > 0 else pirate_activity
        
        total_value = resource_value + strategic_value + economic_value + pirate_activity
        return total_value / self.sectorValuePerThreatscorePerSector

    def get_resource_value(self, resources):
        # Calculates resource value based on available resources
        return sum(resource.amount * resource.demand for resource in resources) if resources else 0

    def get_strategic_value(self, sector):
        # Calculates strategic value based on sector type and infrastructure
        value = self.sector_strategicValue['core'] if not sector.isborder else self.sector_strategicValue['border']
        if sector.hasWharf or sector.hasShipyard:
            value += self.sector_strategicValue['primary']
        if sector.numGates > 0:
            value += self.sector_strategicValue['gates'][min(sector.numGates - 1, 3)]
        return value

    @staticmethod
    def normalize(value, min_value, max_value):
        return (value - min_value) / (max_value - min_value) if max_value > min_value else 1

    def calculate_raw_military_score(self, total_desired_defense_threatscore):
        raw_scores = self.calculate_raw_military_threatscore()
        weighted_scores = {
            'defensive': raw_scores['defensive'] * self.military_weights['defensive'],
            'offensive': raw_scores['offensive'] * self.military_weights['offensive'],
            'stations': raw_scores['stations'] * self.military_weights['stations']
        }
        combined_score = sum(weighted_scores.values())
        
        return self.normalize(combined_score, 0, total_desired_defense_threatscore)

    def calculate_raw_military_threatscore(self):
        # Calculates military strength based on ship and station threat scores
        return {
            'defensive': sum(ship.threatscore for ship in self.ships if ship.is_defensive),
            'offensive': sum(ship.threatscore for ship in self.ships if ship.is_offensive or ship.is_scout),
            'stations': sum(station.threatscore for station in self.stations)
        }

    def calculate_raw_industry_score(self):
        # Adjusts for ship and station construction capabilities
        ship_scores = [self.ship_type_score(ship_type) for ship_type in self.shipyards]
        station_score = self.station_building_score()
        return (sum(ship_scores) / len(ship_scores) if ship_scores else 0) * station_score if station_score else 0

    def ship_type_score(self, ship_type):
        # fix thix
        demand = sum(need.amount for need in self.shipQueue if need.get('ship_type', None) == ship_type.type)
        production_capacity = sum(yard.capacity for yard in self.shipyards if yard.produces == ship_type.type) / (len(self.shipyards) * ship_type.max_yard_capacity)
        downtime = 1 - (ship_type.downtimePercent)

        return (demand / production_capacity if production_capacity > 0 else 0) * downtime

    def station_building_score(self):
        # Scoring for station construction, focusing on demand vs. construction capability
        demand = sum(station.demand for station in self.stations if station.status == "Planned")
        construction_ships = sum(ship.efficiency for ship in self.ships if ship.type == "Construction")
        downtime = 1 - sum(ship.downtimePercent for ship in self.ships if ship.type == "Construction") / len(self.ships)

        return (demand / (demand + construction_ships)) * downtime if demand + construction_ships > 0 else 0

    def check_emergencies(self, scores):
        # Determines if an emergency state should be declared for each sector
        threshhold = self.score_emergency_threshholds
        economy_score, military_score, industry_score = scores
        return {
            'economy': economy_score < threshhold['economy'],
            'military': military_score < threshhold['military'],
            'industry': industry_score < threshhold['industry']
        }

    def apply_weights(self, scores, emergencies):
        weights = self.score_weights
        stateWeights = self.state_weights[self.state]
        emergency_weights = self.score_emergency_weights
        economy_score, military_score, industry_score = scores

        return {
            'economy': economy_score * (weights['economy'] if not emergencies['economy'] else emergency_weights['economy']) * stateWeights['economy'],
            'military': military_score * (weights['military'] if not emergencies['military'] else emergency_weights['military'])  * stateWeights['military'],
            'industry': industry_score * (weights['industry'] if not emergencies['industry'] else emergency_weights['industry'])  * stateWeights['industry']
        }

    def check_state_change(self, scores):
        economy_score, military_score, industry_score = scores
        threshholds = self.state_threshholds

        if self.state == State.EXPANSION:
            if military_score < threshholds['mil_defense']:
                self.state = State.DEFENSE
            elif economy_score < threshholds['eco_consolidation'] or industry_score < threshholds['ind_consolidation']:
                self.state = State.CONSOLIDATE
        
        elif self.state == State.CONSOLIDATE:
            if military_score < threshholds['mil_defense']:
                self.state = State.DEFENSE
            elif economy_score > threshholds['eco_expansion'] and industry_score > threshholds['ind_expansion'] and military_score > threshholds['mil_expansion']:
                self.state = State.EXPANSION

        elif self.state == State.DEFENSE:
            if economy_score > threshholds['eco_expansion'] and industry_score > threshholds['ind_expansion'] and military_score > threshholds['mil_expansion']:
                self.state = State.EXPANSION
            elif military_score > threshholds['mil_consolidation']:
                self.state = State.CONSOLIDATE

        elif self.state == State.WAR_INVADE:
            if military_score < threshholds['mil_defense']:
                self.state = State.WAR_DEFENSE
            elif economy_score < threshholds['eco_consolidation'] or industry_score < threshholds['ind_consolidation']:
                self.state = State.WAR_CONSOLIDATE

        elif self.state == State.WAR_DEFENSE:
            if economy_score < threshholds['eco_consolidation'] or industry_score < threshholds['ind_consolidation']:
                self.state = State.WAR_CONSOLIDATE
            elif military_score > threshholds['mil_invade']:
                self.state = State.WAR_INVADE

        elif self.state == State.WAR_CONSOLIDATE:
            if military_score < threshholds['mil_defense']:
                self.state = State.WAR_DEFENSE
            elif military_score > threshholds['mil_invade'] and economy_score > threshholds['eco_consolidation'] and industry_score > threshholds['ind_consolidation']:
                self.state = State.WAR_INVADE

        if self.state != self.previous_state:
            self.notify_state_change(self.previous_state, self.state)
            self.previous_state = self.state

    def prioritize_build_order(self):
        # Returns a list of priorities based on current state
        if self.state == State.EXPANSION:
            return ['Construction Ship', 'Wharf', 'Miner (Solid)', 'Miner (Fluid)']
        elif self.state == State.CONSOLIDATE:
            return ['Factory', 'Trade Station', 'Transport (Container)']
        elif self.state == State.DEFENSE:
            return ['Defense Station', 'Defensive Ship', 'Scout']
        elif self.state == State.WAR_INVADE:
            return ['Offensive Ship', 'Scout', 'Defensive Ship']
        elif self.state == State.WAR_DEFENSE:
            return ['Defensive Ship', 'Defense Station', 'Scout']
        elif self.state == State.WAR_CONSOLIDATE:
            return ['Offensive Ship', 'Defensive Ship', 'Factory']
