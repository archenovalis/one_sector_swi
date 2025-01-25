class State:
    EXPANSION = "Expansion"
    CONSOLIDATION = "Consolidation"
    DEFENSE = "Defense"
    WAR = "War"

# Constants for thresholds
ECON_THRESHOLD_EXPANSION = 0.7
ECON_THRESHOLD_CONSOLIDATION = 0.5
MIL_THRESHOLD_BASELINE = 0.3
MIL_THRESHOLD_DEFENSE = 0.5
MIL_THRESHOLD_WAR = 0.8

# Constants for weights and factors
MAX_LOGISTICS_SCORE = 100
MAX_TRADE_IMPACT = 10
PIRACY_RISK_FACTOR = 0.1
MAX_EXTRACTOR_EFFICIENCY = 1000

class Empire:
    def __init__(self):
        self.state = State.EXPANSION
        self.sectors = []
        self.resources = []
        self.shipyards = []
        self.ships = []
        self.stations = []
        self.trade_routes = []
        self.markets = []
        self.trades = []
        self.supply_routes = []
        self.espionage_agents = []
        self.recon_missions = []

    def update_scores(self):
        economy_score = self.calculate_economy_score()
        military_score = self.calculate_military_score()
        industry_score = self.calculate_industry_score()

        # state affects scores (simplified)
        if self.state == State.WAR:
            economy_score *= 0.8  # Economy less important in war
            military_score *= 1.2  # Military more important

        return economy_score, military_score, industry_score

    def calculate_economy_score(self):
        return sum(self.calculate_resource_score(resource) for resource in self.resources) / len(self.resources) if self.resources else 0

    def calculate_resource_score(self, resource):
        availability = sum(sector.resource_amount for sector in self.sectors) / len(self.sectors)
        on_hand = min(resource.stockpile, resource.max_storage)
        extraction_rate = sum(extractor.efficiency for extractor in self.resources if extractor.resource_type == resource.type) / (len(self.resources) * MAX_EXTRACTOR_EFFICIENCY)
        transport_efficiency = sum(ship.load_capacity for ship in self.ships if ship.type == "Transport") / (sum(route.distance for route in self.trade_routes) * PIRACY_RISK_FACTOR)
        demand = sum(demand.demand_amount for demand in self.resources if demand.resource_type == resource.type) + sum(trade.demand for trade in self.trades if trade.resource_type == resource.type) - sum(trade.demand for trade in self.trades if trade.is_import)
        saturation = sum(market.supply for market in self.markets if market.resource_type == resource.type) / (len(self.markets) * resource.market_capacity_threshold)
        trade_impact = (sum(trade.bonus for trade in self.trades if trade.is_positive) - sum(trade.penalty for trade in self.trades if trade.is_negative)) / MAX_TRADE_IMPACT

        # adjust weights based on state or strategy
        return (availability * 0.3 + on_hand * 0.2 + extraction_rate * 0.2 + transport_efficiency * 0.1 + 
                demand * 0.1 + (1 - saturation) * 0.1) * (1 + trade_impact)

    def calculate_military_score(self):
        defensive_structures = sum(station.defense_value for station in self.stations if station.is_defensive)
        defensive_ships = sum(ship.defense_power for ship in self.ships if ship.is_defensive)
        offensive_ships = sum(ship.attack_power for ship in self.ships if ship.is_offensive)
        logistics = sum(route.security for route in self.supply_routes) / (len(self.supply_routes) * MAX_LOGISTICS_SCORE)
        intelligence = (sum(spy.success_rate for spy in self.espionage_agents) + sum(recon.effectiveness for recon in self.recon_missions)) / (len(self.espionage_agents) + len(self.recon_missions))

        return (defensive_structures * 0.4 + defensive_ships * 0.3 + offensive_ships * 0.5) * (1 + logistics * 0.1 + intelligence * 0.1)

    def calculate_industry_score(self):
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

    def update_state(self, economy_score, military_score, industry_score):
        if self.state == State.EXPANSION:
            if economy_score < ECON_THRESHOLD_CONSOLIDATION or industry_score < ECON_THRESHOLD_CONSOLIDATION:
                self.state = State.CONSOLIDATION
            elif military_score < MIL_THRESHOLD_DEFENSE:
                self.state = State.DEFENSE
        
        elif self.state == State.CONSOLIDATION:
            if economy_score > ECON_THRESHOLD_EXPANSION and industry_score > ECON_THRESHOLD_EXPANSION:
                self.state = State.EXPANSION
            elif military_score < MIL_THRESHOLD_DEFENSE:
                self.state = State.DEFENSE

        elif self.state == State.DEFENSE:
            if military_score > MIL_THRESHOLD_WAR:
                self.state = State.WAR
            elif military_score > MIL_THRESHOLD_BASELINE:
                self.state = State.CONSOLIDATION

        elif self.state == State.WAR:
            if military_score < MIL_THRESHOLD_DEFENSE:
                self.state = State.DEFENSE

    def prioritize_build_order(self):
        if self.state == State.EXPANSION:
            return ["Exploration", "Mining", "Manufacturing"]
        elif self.state == State.CONSOLIDATION:
            return ["Upgrade", "Defense", "Manufacturing"]
        elif self.state == State.DEFENSE:
            return ["Defense", "Intelligence", "Logistics"]
        elif self.state == State.WAR:
            return ["Offensive", "Defense", "Logistics"]

    def run_turn(self):
        economy, military, industry = self.update_scores()
        self.update_state(economy, military, industry)
        build_order = self.prioritize_build_order()
        # implement the actual building logic based on build_order
        print(f"State: {self.state}, Economy: {economy}, Military: {military}, Industry: {industry}")
        print(f"Build Priority: {build_order}")