# =====================================================================
# FILE: core/BaseBlock.py
# =====================================================================
from abc import ABC, abstractmethod
from typing import Any, Optional
import simpy
from .entity import Entity, EventLogger

# =====================================================================
# FILE: core/BaseBlock.py
# =====================================================================
class BaseBlock(ABC):
    """Abstract base class for all blocks."""
    
    def __init__(self, name: str, env: simpy.Environment, event_logger: EventLogger = None):
        self.name = name
        self.env = env
        self.next_block: Optional['BaseBlock'] = None
        self.statistics = {}
        self.event_logger = event_logger
        self.attributes_to_assign = {}  # NEW: Generic attribute assignment

    def assign_attributes(self, **attributes):
        """
        Configure attributes to assign to entities passing through this block.
        
        Args:
            **attributes: Key-value pairs where values can be:
                - Fixed values (int, float, str)
                - Callable functions that return values
        
        Example:
            block.assign_attributes(
                cost=100,
                revenue=lambda: random.uniform(200, 300),
                category="outpatient"
            )
        """
        self.attributes_to_assign = attributes
    
    def _apply_attributes(self, entity: Entity):
        """Apply configured attributes to entity."""
        for attr_name, attr_value in self.attributes_to_assign.items():
            if callable(attr_value):
                value = attr_value()
            else:
                value = attr_value
            
            entity.add_attribute(f"{self.name}_{attr_name}", value)
        
    def connect_to(self, next_block: 'BaseBlock'):
        """Connect this block to the next block in the flow."""
        self.next_block = next_block
        
    @abstractmethod
    def process_entity(self, entity: Entity):
        """Process an entity through this block. Must be implemented by subclasses."""
        pass

    def log_start(self, entity: Entity, resource_name: str = None):
        """Log activity start."""
        if self.event_logger:
            self.event_logger.log_event(
                case_id=entity.id,
                activity=self.name,
                timestamp=self.env.now,
                lifecycle='start',
                resource=resource_name,
                priority=entity.priority
            )
    
    def log_complete(self, entity: Entity, resource_name: str = None):
        """Log activity completion."""
        if self.event_logger:
            self.event_logger.log_event(
                case_id=entity.id,
                activity=self.name,
                timestamp=self.env.now,
                lifecycle='complete',
                resource=resource_name,
                priority=entity.priority
            )
        
    def send_to_next(self, entity: Entity):
        """Send entity to the next connected block."""
        if self.next_block:
            yield from self.next_block.process_entity(entity)
        else:
            # Entity exits the system
            yield self.env.timeout(0)
            
    def update_statistics(self, key: str, value: Any):
        """Update block statistics."""
        self.statistics[key] = value