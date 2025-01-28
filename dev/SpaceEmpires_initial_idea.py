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
        self.weighted_scores = {
            'economy': 0.0,
            'military': 0.0,
            'industry': 0.0
        }
        self.sectors = []
        self.resources = []
        self.shipyards = []
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

    def update(self):
            self.run_scoring_and_state_check()

    def run_scoring_and_state_check(self):
        raw_scores = self.calculate_raw_scores()
        emergencies = self.check_emergencies(raw_scores)
        self.check_state_change(raw_scores)
        self.weighted_scores = self.apply_weights(raw_scores, emergencies)        

    def calculate_raw_scores(self):
        economy_score = self.calculate_raw_economy_score()
        total_desired_defense_threatscore = sum(self.calculate_sector_threatscore(sector) for sector in self.sectors)
        military_score = self.calculate_raw_military_score(total_desired_defense_threatscore)
        industry_score = self.calculate_raw_industry_score()
        return (economy_score, military_score, industry_score)

    def calculate_raw_economy_score(self):
        return sum(self.calculate_resource_score(resource) for resource in self.resources) / len(self.resources)

    def calculate_resource_score(self, resource):
        weights = self.resource_weights
        availability = sum(sector.resource_amount for sector in self.sectors) / len(self.sectors)
        extraction_rate = sum(ship.threatscore for ship in self.ships if ship.type == "Miner")
        transport_efficiency = sum(ship.load_capacity for ship in self.ships if ship.type == "Transport")
        demand = sum(demand.demand_amount for demand in self.resources if demand.resource_type == resource.type)
        on_hand = resource.stockpile / demand
        saturation = sum(market.supply for market in self.markets if market.resource_type == resource.type) / (len(self.markets) * resource.market_capacity_threshold)

        return (availability * weights['availability'] + 
            on_hand * weights['on_hand'] + 
            extraction_rate * weights['extraction'] +
            transport_efficiency * weights['transport'] + 
            demand * weights['demand'] + 
            saturation * weights['saturation'])

    def calculate_sector_desired_threatscore(self, sector):
        resource_value = self.get_resource_value(sector.resources)
        strategic_value = self.sector_strategicValue['border'] if sector.isborder else self.sector_strategicValue['core']
        economic_value = sum(station.price * 2 if station.iswharf or station.isshipyard else station.price for station in sector.stations)
        pirate_activity = sector.pirate_activity
        total_value = resource_value + strategic_value + economic_value + pirate_activity
        return total_value / self.valuePerSectorThreatscorePerSector

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
        defensive_ship_threatscore = sum(ship.threatscore for ship in self.ships if ship.is_defensive)
        offensive_ship_threatscore = sum(ship.threatscore for ship in self.ships if ship.is_offensive or ship.is_scout)
        station_threatscore = sum(station.threatscore for station in self.stations)
        
        return {
            'defensive': defensive_ship_threatscore,
            'offensive': offensive_ship_threatscore,
            'stations': station_threatscore
        }

    def calculate_raw_industry_score(self):
        ship_scores = [self.ship_type_score(ship_type) for ship_type in self.shipyards]
        station_score = self.station_building_score()
        return (sum(ship_scores) / len(ship_scores) if ship_scores else 0) * station_score

    def ship_type_score(self, ship_type):
        demand = sum(need.amount for need in self.resources if need.ship_type == ship_type.type)
        production_capacity = sum(yard.capacity for yard in self.shipyards if yard.produces == ship_type.type) / (len(self.shipyards) * ship_type.max_yard_capacity)
        current_production = len([ship for ship in self.ships if ship.type == ship_type.type and ship.status == "Building"])
        upgrade_potential = sum(upgrade.benefit for upgrade in self.resources if upgrade.ship_type == ship_type.type) / len(self.ships)

        return ((current_production / demand if demand > 0 else 1) * production_capacity * (1 + upgrade_potential * 0.1))

    def station_building_score(self):
        demand = sum(station.demand for station in self.stations if station.status == "Planned")
        construction_ships = sum(ship.efficiency for ship in self.ships if ship.type == "Construction")
        resource_availability = sum(resource.amount for resource in self.resources if resource.is_build_material) / sum(resource.required for resource in self.stations if resource.is_build_material)
        construction_speed = sum(station.time_to_build for station in self.stations if station.status == "Building") / (len([station for station in self.stations if station.status == "Building"]) * 10)  # Assuming 10 units as min build time

        return (demand / (demand + construction_ships)) * resource_availability * construction_speed

    def check_emergencies(self, scores):
        threshhold = self.score_emergency_threshholds

        economy_score, military_score, industry_score = scores
        return {
            'economy': economy_score < threshhold['economy'],
            'military': military_score < threshhold['military'],
            'industry': industry_score < threshhold['industry']
        }

    def apply_weights(self, scores, emergencies):
        weights = self.score_weights
        emergency_weights = self.score_emergency_weights
        economy_score, military_score, industry_score = scores
        weights = {
            'economy': weights['economy'] if not emergencies['economy'] else emergency_weights['economy'],
            'military': weights['military'] if not emergencies['military'] else emergency_weights['military'],
            'industry': weights['industry'] if not emergencies['industry'] else emergency_weights['industry']
        }
        # state affects scores (simplified)
        if self.state == State.WAR_INVADE:
            economy_score *= 0.8
            military_score *= 1.2
            industry_score *= 0.8
        elif self.state == State.WAR_DEFENSE:
            economy_score *= 0.8
            military_score *= 1.2
            industry_score *= 1.0
        elif self.state == State.WAR_CONSOLIDATE:
            economy_score *= 1.0
            military_score *= 1.2
            industry_score *= 1.2
        elif self.state == State.DEFENSE:
            economy_score *= 1.0
            military_score *= 1.2
            industry_score *= 1.0
        elif self.state == State.CONSOLIDATE:
            economy_score *= 1.2
            military_score *= 1.0
            industry_score *= 1.2
        elif self.state == State.EXPANSION:
            economy_score *= 1.0
            military_score *= 1.0
            industry_score *= 1.2

        return {
            'economy': economy_score * weights['economy'],
            'military': military_score * weights['military'],
            'industry': industry_score * weights['industry']
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

    def run_turn(self):
        economy, military, industry = self.update_scores()
        self.update_state(economy, military, industry)
        build_order = self.prioritize_build_order()