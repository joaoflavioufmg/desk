# =====================================================================
# FILE: blocks/decide_block.py (REFACTORED)
# =====================================================================
class DecideBlock(BaseBlock):
    """
    DECIDE block - route entities based on conditions, probabilities, or time.
    
    Supports three decision types:
    1. "probability" - Route based on probability distribution
    2. "condition" - Route based on entity attributes
    3. "time_condition" - Route based on simulation time (NEW)
    """
    
    def __init__(self, name: str, env: simpy.Environment, 
                 decision_type: str = "probability",
                 event_logger: EventLogger = None):
        super().__init__(name, env, event_logger)
        self.decision_type = decision_type  # "probability", "condition", or "time_condition"
        self.routes = {}  # Will store route options
        self.decision_counts = {}
        
    def add_route(self, route_name: str, 
                  next_block: 'BaseBlock',
                  probability: Optional[float] = None,
                  condition: Optional[Callable[[Entity], bool]] = None,
                  time_condition: Optional[Callable[[float], bool]] = None):
        """
        Add a routing option.
        
        Args:
            route_name: Name of the route
            next_block: Target block for this route
            probability: Probability for this route (for "probability" type)
            condition: Function that takes Entity and returns bool (for "condition" type)
            time_condition: Function that takes current_time (float) and returns bool (for "time_condition" type)
        
        Examples:
            # Probability-based routing
            decide.add_route("high_priority", block1, probability=0.3)
            
            # Entity condition-based routing
            decide.add_route("vip", block2, condition=lambda e: e.priority == 0)
            
            # Time-based routing (NEW)
            decide.add_route("day_shift", block3, 
                           time_condition=lambda t: (t % 1440) < 720)  # First 12 hours of day
            decide.add_route("night_shift", block4,
                           time_condition=lambda t: (t % 1440) >= 720)  # Last 12 hours of day
        """
        self.routes[route_name] = {
            'block': next_block,
            'probability': probability,
            'condition': condition,
            'time_condition': time_condition
        }
        self.decision_counts[route_name] = 0
        
    def process_entity(self, entity: Entity):
        """Route entity based on decision type."""
        entity.route_history.append(self.name)
        
        chosen_route = None
        
        if self.decision_type == "probability":
            chosen_route = self._choose_by_probability()
        elif self.decision_type == "condition":
            chosen_route = self._choose_by_condition(entity)
        elif self.decision_type == "time_condition":
            chosen_route = self._choose_by_time_condition()
        else:
            raise ValueError(f"Invalid decision type: {self.decision_type}")
            
        if chosen_route and chosen_route in self.routes:
            self.decision_counts[chosen_route] += 1
            next_block = self.routes[chosen_route]['block']
            entity.add_attribute(f"{self.name}_decision", chosen_route)

            # Log decision as an event
            if self.event_logger:
                self.event_logger.log_event(
                    case_id=entity.id,
                    activity=f"{self.name}_{chosen_route}",
                    timestamp=self.env.now,
                    lifecycle='complete',
                    decision=chosen_route,
                    decision_time=self.env.now  # NEW: Include time in log
                )

            yield from next_block.process_entity(entity)
        else:
            # No valid route found - entity exits
            yield self.env.timeout(0)

    def _choose_by_probability(self) -> Optional[str]:
        """Choose route based on probabilities."""
        rand = random.random()
        cumulative = 0.0
        
        for route_name, route_info in self.routes.items():
            prob = route_info.get('probability', 0)
            cumulative += prob
            if rand <= cumulative:
                return route_name
                
        return None
        
    def _choose_by_condition(self, entity: Entity) -> Optional[str]:
        """Choose route based on entity conditions."""
        for route_name, route_info in self.routes.items():
            condition = route_info.get('condition')
            if condition and condition(entity):
                return route_name
                
        return None
    
    def _choose_by_time_condition(self) -> Optional[str]:
        """
        Choose route based on simulation time conditions (NEW).
        
        Routes are evaluated in order until one matches.
        Returns the first route whose time_condition evaluates to True.
        """
        current_time = self.env.now
        
        for route_name, route_info in self.routes.items():
            time_condition = route_info.get('time_condition')
            if time_condition and time_condition(current_time):
                return route_name
                
        return None


# =====================================================================
# USAGE EXAMPLES
# =====================================================================

# Example 1: Time-of-day routing (24-hour cycle)
def example_time_of_day_routing():
    """Route entities to different resources based on time of day."""
    
    HOURS = 60  # minutes
    
    model = SimulationModel()
    event_logger = EventLogger()
    
    # Resources for different shifts
    day_staff = model.add_resource("day_staff", 5, "regular")
    night_staff = model.add_resource("night_staff", 2, "regular")
    
    # Create arrivals
    arrivals = CreateBlock(
        "Arrivals", model.env,
        inter_arrival_time=lambda: random.expovariate(1/10),
        event_logger=event_logger
    )
    
    # Time-based shift routing
    shift_router = DecideBlock(
        "Shift_Router", model.env,
        decision_type="time_condition",
        event_logger=event_logger
    )
    
    # Day shift: 6 AM to 10 PM (360 to 1320 minutes in a 24-hour cycle)
    shift_router.add_route(
        "day_shift",
        next_block=None,  # Will be connected later
        time_condition=lambda t: 360 <= (t % (24*HOURS)) < 1320
    )
    
    # Night shift: 10 PM to 6 AM (1320 to 360 minutes)
    shift_router.add_route(
        "night_shift",
        next_block=None,  # Will be connected later
        time_condition=lambda t: (t % (24*HOURS)) < 360 or (t % (24*HOURS)) >= 1320
    )
    
    # Create processing blocks
    day_service = ProcessBlock(
        "Day_Service", model.env,
        resource=day_staff,
        delay_time=lambda: random.uniform(5, 15),
        event_logger=event_logger
    )
    
    night_service = ProcessBlock(
        "Night_Service", model.env,
        resource=night_staff,
        delay_time=lambda: random.uniform(5, 15),
        event_logger=event_logger
    )
    
    dispose = DisposeBlock("Dispose", model.env, event_logger=event_logger)
    
    # Connect blocks
    arrivals.connect_to(shift_router)
    shift_router.routes["day_shift"]["block"] = day_service
    shift_router.routes["night_shift"]["block"] = night_service
    day_service.connect_to(dispose)
    night_service.connect_to(dispose)
    
    model.add_block(arrivals)
    model.add_block(shift_router)
    model.add_block(day_service)
    model.add_block(night_service)
    model.add_block(dispose)
    
    return model


# Example 2: Weekly schedule routing (7-day cycle)
def example_weekly_schedule_routing():
    """Route entities differently on weekdays vs weekends."""
    
    DAYS = 1440  # minutes per day
    
    model = SimulationModel()
    event_logger = EventLogger()
    
    # Time-based weekday/weekend routing
    schedule_router = DecideBlock(
        "Schedule_Router", model.env,
        decision_type="time_condition",
        event_logger=event_logger
    )
    
    # Weekday: Monday (day 0) to Friday (day 4)
    schedule_router.add_route(
        "weekday",
        next_block=None,
        time_condition=lambda t: (int(t / DAYS) % 7) < 5
    )
    
    # Weekend: Saturday (day 5) and Sunday (day 6)
    schedule_router.add_route(
        "weekend",
        next_block=None,
        time_condition=lambda t: (int(t / DAYS) % 7) >= 5
    )
    
    return model


# Example 3: Seasonal routing (yearly cycle)
def example_seasonal_routing():
    """Route entities based on seasons (quarters of the year)."""
    
    DAYS = 1440
    QUARTER = 91 * DAYS  # Approximately 91 days per quarter
    YEAR = 365 * DAYS
    
    model = SimulationModel()
    event_logger = EventLogger()
    
    seasonal_router = DecideBlock(
        "Seasonal_Router", model.env,
        decision_type="time_condition",
        event_logger=event_logger
    )
    
    # Q1: Winter (days 0-90)
    seasonal_router.add_route(
        "winter",
        next_block=None,
        time_condition=lambda t: (t % YEAR) < QUARTER
    )
    
    # Q2: Spring (days 91-181)
    seasonal_router.add_route(
        "spring",
        next_block=None,
        time_condition=lambda t: QUARTER <= (t % YEAR) < 2*QUARTER
    )
    
    # Q3: Summer (days 182-272)
    seasonal_router.add_route(
        "summer",
        next_block=None,
        time_condition=lambda t: 2*QUARTER <= (t % YEAR) < 3*QUARTER
    )
    
    # Q4: Fall (days 273-365)
    seasonal_router.add_route(
        "fall",
        next_block=None,
        time_condition=lambda t: (t % YEAR) >= 3*QUARTER
    )
    
    return model


# Example 4: Peak hours routing (multiple time windows per day)
def example_peak_hours_routing():
    """Route entities to express lane during peak hours."""
    
    HOURS = 60
    DAY = 24 * HOURS
    
    model = SimulationModel()
    event_logger = EventLogger()
    
    peak_router = DecideBlock(
        "Peak_Hours_Router", model.env,
        decision_type="time_condition",
        event_logger=event_logger
    )
    
    def is_peak_hour(t):
        """Check if current time is during peak hours (8-10 AM or 5-7 PM)."""
        time_of_day = t % DAY
        morning_peak = 8*HOURS <= time_of_day < 10*HOURS
        evening_peak = 17*HOURS <= time_of_day < 19*HOURS
        return morning_peak or evening_peak
    
    # Express lane during peak hours
    peak_router.add_route(
        "express_lane",
        next_block=None,
        time_condition=is_peak_hour
    )
    
    # Regular lane during off-peak
    peak_router.add_route(
        "regular_lane",
        next_block=None,
        time_condition=lambda t: not is_peak_hour(t)
    )
    
    return model


# Example 5: Hybrid routing (time + entity conditions)
def example_hybrid_routing():
    """
    Combine time-based and entity-based routing.
    
    Use multiple DecideBlocks in sequence to implement complex logic.
    """
    
    HOURS = 60
    
    model = SimulationModel()
    event_logger = EventLogger()
    
    # First decision: Check time
    time_router = DecideBlock(
        "Time_Router", model.env,
        decision_type="time_condition",
        event_logger=event_logger
    )
    
    # Second decision: Check entity priority (for day shift)
    day_priority_router = DecideBlock(
        "Day_Priority_Router", model.env,
        decision_type="condition",
        event_logger=event_logger
    )
    
    # Third decision: Check entity priority (for night shift)
    night_priority_router = DecideBlock(
        "Night_Priority_Router", model.env,
        decision_type="condition",
        event_logger=event_logger
    )
    
    # Time-based routing
    time_router.add_route(
        "day_shift",
        next_block=day_priority_router,
        time_condition=lambda t: (t % (24*HOURS)) < 12*HOURS
    )
    
    time_router.add_route(
        "night_shift",
        next_block=night_priority_router,
        time_condition=lambda t: (t % (24*HOURS)) >= 12*HOURS
    )
    
    # Entity-based routing (day)
    day_priority_router.add_route(
        "day_urgent",
        next_block=None,
        condition=lambda e: e.priority <= 1
    )
    
    day_priority_router.add_route(
        "day_regular",
        next_block=None,
        condition=lambda e: e.priority > 1
    )
    
    # Entity-based routing (night)
    night_priority_router.add_route(
        "night_urgent",
        next_block=None,
        condition=lambda e: e.priority <= 1
    )
    
    night_priority_router.add_route(
        "night_regular",
        next_block=None,
        condition=lambda e: e.priority > 1
    )
    
    return model


# =====================================================================
# HELPER FUNCTIONS FOR COMMON TIME CONDITIONS
# =====================================================================

class TimeConditions:
    """Collection of common time-based condition functions."""
    
    @staticmethod
    def time_of_day(start_hour: int, end_hour: int, time_unit: int = 60):
        """
        Create condition for time-of-day window.
        
        Args:
            start_hour: Start hour (0-23)
            end_hour: End hour (0-23)
            time_unit: Minutes per hour (default 60)
        
        Returns:
            Condition function
        """
        start_min = start_hour * time_unit
        end_min = end_hour * time_unit
        day_length = 24 * time_unit
        
        return lambda t: start_min <= (t % day_length) < end_min
    
    @staticmethod
    def day_of_week(days: list, time_unit_day: int = 1440):
        """
        Create condition for specific days of week.
        
        Args:
            days: List of day numbers (0=Monday, 6=Sunday)
            time_unit_day: Minutes per day (default 1440)
        
        Returns:
            Condition function
        """
        week_length = 7 * time_unit_day
        return lambda t: (int(t / time_unit_day) % 7) in days
    
    @staticmethod
    def business_hours(time_unit: int = 60):
        """
        Business hours: Monday-Friday, 9 AM - 5 PM.
        
        Args:
            time_unit: Minutes per hour
        
        Returns:
            Condition function
        """
        day_unit = 24 * time_unit
        
        def is_business_hours(t):
            day_of_week = (int(t / day_unit) % 7)
            time_of_day = t % day_unit
            
            is_weekday = day_of_week < 5  # Monday-Friday
            is_work_hours = 9*time_unit <= time_of_day < 17*time_unit
            
            return is_weekday and is_work_hours
        
        return is_business_hours
    
    @staticmethod
    def time_window(start_time: float, end_time: float):
        """
        Create condition for absolute time window.
        
        Args:
            start_time: Absolute start time
            end_time: Absolute end time
        
        Returns:
            Condition function
        """
        return lambda t: start_time <= t < end_time
    
    @staticmethod
    def periodic_window(period: float, window_start: float, window_duration: float):
        """
        Create condition for periodic time windows.
        
        Args:
            period: Length of one complete period
            window_start: Start of window within period
            window_duration: Duration of window
        
        Returns:
            Condition function
        """
        window_end = window_start + window_duration
        return lambda t: window_start <= (t % period) < window_end


# =====================================================================
# COMPLETE WORKING EXAMPLE
# =====================================================================

def complete_hospital_example_with_shifts():
    """Complete hospital example with day/night shift routing."""
    
    HOURS = 60
    DAYS = 1440
    
    # Create model
    model = SimulationModel()
    event_logger = EventLogger()
    
    # Resources (different capacities for shifts)
    day_doctors = model.add_resource("day_doctors", 5, "priority")
    night_doctors = model.add_resource("night_doctors", 2, "priority")
    
    # Patient arrivals
    def patient_severity():
        return random.choices([0, 1, 2, 3, 4], 
                            weights=[0.1, 0.2, 0.3, 0.3, 0.1])[0]
    
    arrivals = CreateBlock(
        "Arrivals", model.env,
        inter_arrival_time=lambda: random.expovariate(1/15),
        entity_prefix="Patient",
        priority_generator=patient_severity,
        event_logger=event_logger
    )
    
    # Shift router (time-based)
    shift_router = DecideBlock(
        "Shift_Router", model.env,
        decision_type="time_condition",
        event_logger=event_logger
    )
    
    # Day shift: 7 AM to 7 PM
    shift_router.add_route(
        "day_shift",
        next_block=None,
        time_condition=TimeConditions.time_of_day(7, 19, HOURS)
    )
    
    # Night shift: 7 PM to 7 AM
    shift_router.add_route(
        "night_shift",
        next_block=None,
        time_condition=lambda t: not TimeConditions.time_of_day(7, 19, HOURS)(t)
    )
    
    # Processing blocks
    day_treatment = ProcessBlock(
        "Day_Treatment", model.env,
        resource=day_doctors,
        delay_time=lambda: random.uniform(10, 30),
        event_logger=event_logger
    )
    day_treatment.set_resource_name('day_doctors')
    
    night_treatment = ProcessBlock(
        "Night_Treatment", model.env,
        resource=night_doctors,
        delay_time=lambda: random.uniform(10, 30),
        event_logger=event_logger
    )
    night_treatment.set_resource_name('night_doctors')
    
    discharge = DisposeBlock("Discharge", model.env, event_logger=event_logger)
    
    # Connect blocks
    arrivals.connect_to(shift_router)
    shift_router.routes["day_shift"]["block"] = day_treatment
    shift_router.routes["night_shift"]["block"] = night_treatment
    day_treatment.connect_to(discharge)
    night_treatment.connect_to(discharge)
    
    # Add to model
    for block in [arrivals, shift_router, day_treatment, night_treatment, discharge]:
        model.add_block(block)
    
    # Run simulation (3 days)
    model.run_simulation(
        until=3*DAYS,
        seed=123,
        warm_up_period=0.5*DAYS
    )
    
    # Report results
    reporter = SimulationReporter(model)
    reporter.print_results()
    
    # Show routing statistics
    print("\n" + "="*60)
    print("SHIFT ROUTING STATISTICS:")
    print("="*60)
    for route, count in shift_router.decision_counts.items():
        total = sum(shift_router.decision_counts.values())
        percentage = (count/total*100) if total > 0 else 0
        print(f"{route}: {count} patients ({percentage:.1f}%)")
    
    return model, event_logger


if __name__ == "__main__":
    print("Running complete hospital example with shift-based routing...")
    model, logger = complete_hospital_example_with_shifts()