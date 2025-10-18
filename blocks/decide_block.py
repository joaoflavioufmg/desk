# =====================================================================
# FILE: blocks/decide_block.py
# =====================================================================
from core.base_block import BaseBlock
from core.entity import Entity, EventLogger
from typing import  Optional, Callable
import simpy
import random

# =====================================================================
# FILE: blocks/decide_block.py
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

