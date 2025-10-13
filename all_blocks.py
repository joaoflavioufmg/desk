# All_blocks.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Union, Optional, List, Callable, Tuple
from dataclasses import dataclass, field
import sys
import simpy
import numpy as np
import scipy.stats as stats
import matplotlib.pyplot as plt
import pandas as pd
import random
import time
import math
import statistics
import itertools
import seaborn as sns

from blocks import dispose_block



# =====================================================================
# FILE: core/entity.py
# =====================================================================
@dataclass
class Entity:
    """Represents an entity flowing through the simulation."""
    id: str
    creation_time: float
    data: Dict[str, Any] = field(default_factory=dict)
    route_history: List[str] = field(default_factory=list)
    priority: int = 0  # Lower numbers = higher priority (0 = highest)
    
    def add_attribute(self, key: str, value: Any):
        self.data[key] = value
    
    def get_attribute(self, key: str, default=None):
        return self.data.get(key, default)


class EventLogger:
    """Logs events in BupaR format during simulation."""
    
    def __init__(self):
        self.events = []
    
    def log_event(self, case_id: str, activity: str, timestamp: float, 
                  lifecycle: str, resource: str = None, **attributes):
        """Log a single event."""
        event = {
            'case_id': case_id,
            'activity': activity,
            'timestamp': timestamp,
            'lifecycle': lifecycle,
            'resource': resource
        }
        event.update(attributes)
        self.events.append(event)
    
    def get_dataframe(self) -> pd.DataFrame:
        """Return events as a pandas DataFrame."""
        df = pd.DataFrame(self.events)
        df = df.sort_values(['case_id', 'timestamp']).reset_index(drop=True)
        return df
    
    def export_to_csv(self, filename: str = "event_log_bupar.csv"):
        """Export to CSV in BupaR format."""
        df = self.get_dataframe()
        df.to_csv(filename, index=False)
        print(f"Event log exported to {filename}")
        print(f"Total events: {len(df)}")
        print(f"Total cases: {df['case_id'].nunique()}")
        return df


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


# =====================================================================
# FILE: blocks/create_block.py
# =====================================================================
class CreateBlock(BaseBlock):
    """CREATE block - generates entities into the system."""
    
    def __init__(self, name: str, env: simpy.Environment, 
             inter_arrival_time: Callable[[], float],
             entity_prefix: str = "Entity",
             max_arrivals: Optional[int] = None,
             first_creation: float = 0.0,
             priority_generator: Optional[Callable[[], int]] = None,
             event_logger: EventLogger = None):
        # Call parent class init FIRST with event_logger
        super().__init__(name, env, event_logger)
        # NOW we can safely set other attributes
        self.inter_arrival_time = inter_arrival_time
        self.entity_prefix = entity_prefix
        self.max_arrivals = max_arrivals
        self.first_creation = first_creation
        self.entities_created = 0
        self.priority_generator = priority_generator
        
    def start_generation(self):
        """Start the entity generation process."""
        return self.env.process(self._generation_process())
        
    def _generation_process(self):
        """Internal process for generating entities."""
        if self.first_creation > 0:
            yield self.env.timeout(self.first_creation)
            
        while True:
            if self.max_arrivals and self.entities_created >= self.max_arrivals:
                break
                
            entity = Entity(
                id=f"{self.entity_prefix}_{self.entities_created}",
                creation_time=self.env.now,
                data={},
                route_history=[],
                priority=self.priority_generator() if self.priority_generator else 0
            )
            
            self.entities_created += 1
            entity.route_history.append(self.name)
            
            # Log creation as an event
            if self.event_logger:
                self.event_logger.log_event(
                    case_id=entity.id,
                    activity="Arrival",
                    timestamp=self.env.now,
                    lifecycle='complete',
                    priority=entity.priority
                )
            
            if self.next_block:
                self.env.process(self.next_block.process_entity(entity))
                
            yield self.env.timeout(self.inter_arrival_time())
            
    def process_entity(self, entity: Entity):
        """CREATE blocks don't process incoming entities."""
        raise NotImplementedError("CREATE blocks generate entities, they don't process them")



# =====================================================================
# FILE: blocks/process_block.py
# =====================================================================
class ProcessBlock(BaseBlock):
    """PROCESS block - seize resource, delay, release resource."""
    
    def __init__(self, name: str, env: simpy.Environment,
                 resource: simpy.Resource,
                 delay_time: Callable[[], float],
                 resource_units: int = 1,
                 event_logger: EventLogger = None):
        super().__init__(name, env, event_logger)
        self.resource = resource
        self.delay_time = delay_time
        self.resource_units = resource_units
        self.entities_processed = 0
        self.total_delay_time = 0.0
        self.total_queue_time = 0.0
        self.resource_data = []  # (time, in_service, queue_length)
        self.max_queue_length = 0
        self.max_in_service = 0

        # Store resource name for logging
        self.resource_name = None

    def set_resource_name(self, name: str):
        """Set the resource name for event logging."""
        self.resource_name = name     


    # def process_entity(self, entity: Entity):
    #     """Process an entity through seize-delay-release WITH DEBUGGING."""
    #     entity.route_history.append(self.name)
        
    #     self._monitor_resource()
    #     # Log queue start
    #     queue_start = self.env.now
        
    #     # # DEBUG: Check resource state BEFORE seizing
    #     # print(f"[t={self.env.now:.2f}] BEFORE seize - resource.count={self.resource.count}, queue={len(self.resource.queue)}")
        
    #     # Seize resource (with priority if it's a PriorityResource)
    #     if hasattr(self.resource, 'request'):
    #         if isinstance(self.resource, simpy.PriorityResource):
    #             req = self.resource.request(priority=entity.priority)
    #         else:
    #             req = self.resource.request()
    #     else:
    #         req = self.resource.request()
            
    #     with req:
    #         yield req  # Wait for resource

    #         # # DEBUG: Check resource state AFTER seizing
    #         # print(f"[t={self.env.now:.2f}] AFTER seize - resource.count={self.resource.count}, queue={len(self.resource.queue)}")
            
    #         # # Record state after seizing
    #         # current_queue_length = len(self.resource.queue)
    #         # current_in_service = self.resource.count
    #         # data_point = (self.env.now, current_in_service, current_queue_length)
    #         # self.resource_data.append(data_point)
    #         # # print(f"[t={self.env.now:.2f}] RECORDED: {data_point}")
            
    #         # self.max_queue_length = max(self.max_queue_length, current_queue_length)
    #         # self.max_in_service = max(self.max_in_service, current_in_service)
    #         self._monitor_resource()

    #         # Log activity start
    #         self.log_start(entity, self.resource_name)         
                        
    #         # Record queue time
    #         queue_time = self.env.now - queue_start
    #         self.total_queue_time += queue_time
    #         entity.add_attribute(f"{self.name}_queue_time", queue_time)
            
    #         # Process (delay)
    #         if hasattr(self.env, 'model') and hasattr(self.env.model, 'safe_delay_time'):
    #             delay = self.env.model.safe_delay_time(self.delay_time)
    #         else:
    #             delay = max(0.0, self.delay_time())

    #         # print(f"[t={self.env.now:.2f}] PROCESSING for {delay:.2f} time units...")
    #         yield self.env.timeout(delay)

    #         self._monitor_resource()
            
    #         # print(f"[t={self.env.now:.2f}] BEFORE release - resource.count={self.resource.count}, queue={len(self.resource.queue)}")
            
    #         # Update statistics
    #         self.entities_processed += 1
    #         self.total_delay_time += delay
    #         entity.add_attribute(f"{self.name}_service_time", delay)

    #         # NEW: Apply configured attributes (e.g., cost, revenue)
    #         self._apply_attributes(entity)
            
    #         # Log activity complete
    #         self.log_complete(entity, self.resource_name)            
            
    #     # # Monitor resource state AFTER release
    #     # # print(f"[t={self.env.now:.2f}] AFTER release - resource.count={self.resource.count}, queue={len(self.resource.queue)}")
    #     # current_queue_length = len(self.resource.queue)
    #     # current_in_service = self.resource.count
    #     # data_point = (self.env.now, current_in_service, current_queue_length)
    #     # self.resource_data.append(data_point)
    #     # # print(f"[t={self.env.now:.2f}] RECORDED: {data_point}")
        
    #     # self.max_queue_length = max(self.max_queue_length, current_queue_length)
    #     # self.max_in_service = max(self.max_in_service, current_in_service)
    #     self._monitor_resource()

    #     # Send to next block
    #     yield from self.send_to_next(entity)

    # #######################################################################################
    # def process_entity(self, entity: Entity):
    #     """Process an entity through seize-delay-release with multiple-unit support."""
    #     entity.route_history.append(self.name)
        
    #     self._monitor_resource()

    #     queue_start = self.env.now

    #     # Create list of requests according to resource_units
    #     requests = []
    #     for _ in range(self.resource_units):
    #         if isinstance(self.resource, simpy.PreemptiveResource):
    #             req = self.resource.request(preempt=True) # Enable preemption                    
    #         elif isinstance(self.resource, simpy.PriorityResource):
    #             req = self.resource.request(priority=entity.priority) # Enable prioritization
    #         else:
    #             req = self.resource.request()
    #         requests.append(req)

    #     acquired = []
    #     try:
    #         # Acquire all requested units atomically
    #         yield simpy.AllOf(self.env, requests)
    #         acquired = requests

    #         self._monitor_resource()

    #         self.log_start(entity, self.resource_name)

    #         # Record queue time
    #         queue_time = self.env.now - queue_start
    #         self.total_queue_time += queue_time
    #         entity.add_attribute(f"{self.name}_queue_time", queue_time)

    #         # Delay (service)
    #         if hasattr(self.env, 'model') and hasattr(self.env.model, 'safe_delay_time'):
    #             delay = self.env.model.safe_delay_time(self.delay_time)
    #         else:
    #             delay = max(0.0, self.delay_time())

    #         yield self.env.timeout(delay)

    #         # Update stats
    #         self.entities_processed += 1
    #         self.total_delay_time += delay
    #         entity.add_attribute(f"{self.name}_service_time", delay)

    #         self._apply_attributes(entity)
    #         self.log_complete(entity, self.resource_name)

    #     finally:
    #         # Release all acquired units
    #         for req in acquired:
    #             try:
    #                 self.resource.release(req)
    #             except:
    #                 pass
    #         self._monitor_resource()

    #     self._monitor_resource()
    #     # Continue flow
    #     yield from self.send_to_next(entity)
    # #########################################################################
    def process_entity(self, entity: Entity):
        """Process an entity through seize-delay-release with preemption support."""
        entity.route_history.append(self.name)
        
        self._monitor_resource()

        # 🔄 RETRY LOOP - handles preemption during acquisition OR service
        while True:
            queue_start = self.env.now

            # Create list of requests according to resource_units
            requests = []
            for _ in range(self.resource_units):
                if isinstance(self.resource, simpy.PreemptiveResource):
                    # req = self.resource.request(priority=entity.priority, preempt=True)
                    # ⚠️ KEY FIX: Use preempt=False during request
                    # Preemption will still occur during service timeout
                    req = self.resource.request(priority=entity.priority, preempt=False)
                elif isinstance(self.resource, simpy.PriorityResource):
                    req = self.resource.request(priority=entity.priority)
                else:
                    req = self.resource.request()
                requests.append(req)

            acquired = []
            try:
                # ⚠️ ACQUISITION - can be preempted here too!
                yield simpy.AllOf(self.env, requests)
                acquired = requests

                self._monitor_resource()
                self.log_start(entity, self.resource_name)

                # Record queue time
                queue_time = self.env.now - queue_start
                self.total_queue_time += queue_time
                entity.add_attribute(f"{self.name}_queue_time", queue_time)

                # ⚠️ SERVICE - can be preempted here
                if hasattr(self.env, 'model') and hasattr(self.env.model, 'safe_delay_time'):
                    delay = self.env.model.safe_delay_time(self.delay_time)
                else:
                    delay = max(0.0, self.delay_time())

                yield self.env.timeout(delay)
                
                # ✅ SUCCESS - completed without interruption
                self.entities_processed += 1
                self.total_delay_time += delay
                entity.add_attribute(f"{self.name}_service_time", delay)
                
                self._apply_attributes(entity)
                self.log_complete(entity, self.resource_name)
                
                break  # Exit retry loop - we're done!
                
            except simpy.Interrupt as interrupt:
                # 🚨 PREEMPTED (during acquisition or service)
                if self.event_logger:
                    # Determine if interrupted during service or acquisition
                    lifecycle = 'interrupt' if acquired else 'interrupt_queue'
                    
                    self.event_logger.log_event(
                        case_id=entity.id,
                        activity=self.name,
                        timestamp=self.env.now,
                        lifecycle=lifecycle,
                        resource=self.resource_name,
                        priority=entity.priority
                    )
                
                # Resources will be released in finally block
                # Loop continues to retry from the beginning
                continue

            finally:
                # 🔓 Always release all acquired units
                for req in acquired:
                    try:
                        self.resource.release(req)
                    except:
                        pass
                self._monitor_resource()

        self._monitor_resource()
        # Continue to next block
        yield from self.send_to_next(entity)


    def _monitor_resource(self):
        """Monitor resource state for statistics."""
        current_queue_length = len(self.resource.queue)
        current_in_service = self.resource.count
        
        self.max_queue_length = max(self.max_queue_length, current_queue_length)
        self.max_in_service = max(self.max_in_service, current_in_service)
        
        # Always collect data for warm-up analysis, but mark post-warmup data
        data_point = (self.env.now, current_in_service, current_queue_length)
        self.resource_data.append(data_point)


class MultiProcessBlock(BaseBlock):
    """PROCESS block that can seize multiple resources simultaneously."""
    
    def __init__(self, name: str, env: simpy.Environment,
                 resource_requirements: Dict[simpy.Resource, int],
                 delay_time: Callable[[], float],
                 event_logger: EventLogger = None):
        """
        Args:
            resource_requirements: Dict mapping resources to units needed
                                 e.g., {nurses: 1, doctors: 1, pharmacy_staff: 1}
            delay_time: Function returning service time
        """
        super().__init__(name, env, event_logger)
        self.resource_requirements = resource_requirements
        self.delay_time = delay_time
        self.entities_processed = 0
        self.resource_names = {}
        self.total_delay_time = 0.0
        self.total_queue_time = 0.0
        self.resource_data = {}  # Dict of resource -> [(time, in_service, queue_length)]
        self.max_metrics = {}    # Dict of resource -> {max_queue, max_service}
        
        # Initialize monitoring for each resource
        for resource in resource_requirements.keys():
            self.resource_data[resource] = []
            self.max_metrics[resource] = {'max_queue_length': 0, 'max_in_service': 0}
        
    def set_resource_names(self, resource_names: Dict[simpy.Resource, str]):
        """Set resource names for logging."""
        self.resource_names = resource_names


    def process_entity(self, entity: Entity):
        """Process entity through multi-resource seize-delay-release."""
        entity.route_history.append(self.name)
        
        # Record queue entry time
        queue_start = self.env.now
        
        # Monitor all resources before seizing
        self._monitor_all_resources()
        
        
        while True:  # Loop for retry on preemption
            # Create all resource requests with their resources
            requests = []
            for resource, units in self.resource_requirements.items():
                for _ in range(units):
                    if isinstance(resource, simpy.PreemptiveResource):
                        req = resource.request(preempt=True) # Enable preemption
                    elif isinstance(resource, simpy.PriorityResource):
                        req = resource.request(priority=entity.priority)
                    else:
                        req = resource.request()
                    requests.append((resource, req))
        
        # =====================================================================
        # # Acquire all resources sequentially but hold them all
        # acquired_resources = []
        # try:
        #     # IMPORTANT: Unpack the (resource, req) tuple here and yield ONLY the req (which is the SimPy event).
        #     # If you mistakenly loop with 'for req in requests: yield req', it would yield the tuple instead,
        #     # causing the "Invalid yield value" error with the (Resource, Request) tuple.
        #     for resource, req in requests:
        #         yield req
        #         acquired_resources.append((resource, req))
            
            
        #     # Log activity start with all resources
        #     resources_str = ", ".join([self.resource_names.get(r, "Unknown") 
        #                               for r, _ in acquired_resources])
        #     self.log_start(entity, resources_str)
        # =====================================================================

        # ======================= START: CODE CORRECTION =======================
        # # Store all requests for the finally block to release them.
        # acquired_resources = requests 
        
        # # Create a list of just the request events to wait for.
        # request_events = [req for _, req in requests]

            acquired_resources = []
            try:
                # # Atomically wait for ALL resources to be available.
                # # This is the key change that prevents deadlock.
                # yield self.env.all_of(request_events)
                
                # ...OR..
                # Acquire all resources simultaneously
                yield simpy.AllOf(self.env, [req for _, req in requests])
                acquired_resources = requests
                
                # The original sequential acquisition loop is removed.
                # for resource, req in requests:
                #     yield req
                #     acquired_resources.append((resource, req))
                
                # Log activity start with all resources
                resources_str = ", ".join([self.resource_names.get(r, "Unknown") 
                                        for r, _ in acquired_resources])
                self.log_start(entity, resources_str)
        # ======================== END: CODE CORRECTION ========================


                # Record queue time and monitor state after seizing all
                queue_time = self.env.now - queue_start
                self.total_queue_time += queue_time
                entity.add_attribute(f"{self.name}_queue_time", queue_time)
                self._monitor_all_resources()
                
                # Process (delay) - all resources are now held (use safe delay time)
                # #############################################################
                # Para Evitar erros de dados negativos no modelo
                # #############################################################
                # delay = self.delay_time()
                if hasattr(self.env, 'model') and hasattr(self.env.model, 'safe_delay_time'):
                    # If the model has the safe_delay_time method, use it
                    delay = self.env.model.safe_delay_time(self.delay_time)
                else:
                    # Fallback: ensure non-negative manually
                    delay = max(0.0, self.delay_time())

                # yield self.env.timeout(delay)

                try:    
                    yield self.env.timeout(delay)
                except simpy.Interrupt:
                    # Preempted: log, release, and retry
                    if self.event_logger:
                        self.event_logger.log_event(
                            case_id=entity.id,
                            activity=self.name,
                            timestamp=self.env.now,
                            lifecycle='interrupt',
                            resource=resources_str,
                            priority=entity.priority
                        )
                    continue  # Retry seizure from the top
                
                # Update statistics
                self.entities_processed += 1
                self.total_delay_time += delay
                entity.add_attribute(f"{self.name}_service_time", delay)

                # NEW: Apply configured attributes (e.g., cost, revenue)
                self._apply_attributes(entity)

                # Log activity complete
                self.log_complete(entity, resources_str) 

                break  # Success, exit retry loop

            finally:
                # Release all acquired resources
                for resource, req in acquired_resources:
                    resource.release(req)
                
                # Monitor resources after release
                self._monitor_all_resources()
        
        # Send to next block
        yield from self.send_to_next(entity)
    

    def _monitor_all_resources(self):
        """Monitor state of all resources."""
        for resource in self.resource_requirements.keys():
            current_queue_length = len(resource.queue)
            current_in_service = resource.count
            
            # Update max metrics
            self.max_metrics[resource]['max_queue_length'] = max(
                self.max_metrics[resource]['max_queue_length'], 
                current_queue_length
            )
            self.max_metrics[resource]['max_in_service'] = max(
                self.max_metrics[resource]['max_in_service'], 
                current_in_service
            )
            
            # Store data point
            data_point = (self.env.now, current_in_service, current_queue_length)
            self.resource_data[resource].append(data_point)


# =====================================================================
# FILE: blocks/decide_block.py
# =====================================================================
class DecideBlock(BaseBlock):
    """DECIDE block - route entities based on conditions or probabilities."""
    
    def __init__(self, name: str, env: simpy.Environment, 
                 decision_type: str = "probability",
                 event_logger: EventLogger = None):
        super().__init__(name, env, event_logger)
        self.decision_type = decision_type  # "probability" or "condition"
        self.routes = {}  # Will store route options
        self.decision_counts = {}
        
    def add_route(self, route_name: str, 
                  next_block: 'BaseBlock',
                  probability: Optional[float] = None,
                  condition: Optional[Callable[[Entity], bool]] = None):
        """Add a routing option."""
        self.routes[route_name] = {
            'block': next_block,
            'probability': probability,
            'condition': condition
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
                    decision=chosen_route
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
        """Choose route based on conditions."""
        for route_name, route_info in self.routes.items():
            condition = route_info.get('condition')
            if condition and condition(entity):
                return route_name
                
        return None


# =====================================================================
# FILE: blocks/dispose_block.py
# =====================================================================
class DisposeBlock(BaseBlock):
    """DISPOSE block - removes entities from system and collects statistics."""
    
    def __init__(self, name: str, env: simpy.Environment, event_logger: EventLogger = None):
        super().__init__(name, env, event_logger)
        self.entities_disposed = 0
        self.total_system_time = 0.0
        self.disposed_entities = []
        
    def process_entity(self, entity: Entity):
        """Dispose of entity and collect final statistics."""
        entity.route_history.append(self.name)
        
        # Always collect entity data for plotting, but only count for statistics after warm-up
        system_time = self.env.now - entity.creation_time
        entity.add_attribute("system_time", system_time)
        entity.add_attribute("disposal_time", self.env.now)

        # NEW: Apply configured attributes (e.g., revenue)
        self._apply_attributes(entity)

        self.disposed_entities.append(entity)  # Always keep for plotting
        
        # Only count for official statistics after warm-up period
        if self.env.now >= getattr(self.env, 'warm_up_period', 0):
            self.total_system_time += system_time
            self.entities_disposed += 1

        # Log disposal
        if self.event_logger:
            self.event_logger.log_event(
                case_id=entity.id,
                activity="Discharge",
                timestamp=self.env.now,
                lifecycle='complete',
                system_time=system_time
            )
        
        # Entity is disposed - no further processing
        yield self.env.timeout(0)
        
    def get_average_system_time(self):
        """Get average system time for disposed entities."""
        if self.entities_disposed > 0:
            return self.total_system_time / self.entities_disposed
        return 0.0


# =====================================================================
# FILE: core/simulation_model.py
# =====================================================================
class SimulationModel:
    """
    Core simulation model orchestration.
    
    Responsibilities:
    - Manage simulation environment
    - Manage blocks and resources
    - Run simulation with warm-up handling
    - Provide basic results access
    
    Does NOT handle:
    - Metrics calculation (see analytics.metrics)
    - Plotting (see analytics.plotting)
    - Stability analysis (see validation.stability)
    - Warm-up analysis (see validation.warmup)
    """
    
    def __init__(self):
        self.env = simpy.Environment()
        self.env.model = self  # For safe_delay_time access
        self.blocks: Dict[str, 'BaseBlock'] = {}
        self.resources: Dict[str, Union[
            simpy.Resource, 
            simpy.PriorityResource, 
            simpy.PreemptiveResource]] = {}
        self.create_blocks: List['CreateBlock'] = []
        self.dispose_blocks: List['DisposeBlock'] = []
        self.stability_result: Optional[float] = None
        self.warm_up_period: float = 0.0
        self.is_warm_up_complete: bool = False

    def validate_resources(self, raise_on_error: bool = True) -> bool:
        """
        Validate resource configuration before running simulation.
        
        Checks for:
        - Resource units exceeding capacity (CRITICAL)
        - Unregistered resources
        - Resource type mismatches
        - Potential deadlocks
        
        Args:
            raise_on_error: If True, raise exception on errors; 
                          if False, return False
            
        Returns:
            True if validation passes, False otherwise
            
        Raises:
            ResourceValidationError: If critical errors found and raise_on_error=True
        """        
        
        validator = ResourceValidator(self)
        return validator.validate_all(raise_on_error=raise_on_error)

    def add_resource(self, name: str, capacity: int, 
                    resource_type: str = "regular") -> Union[simpy.Resource, 
                                                            simpy.PriorityResource]:
        """
        Add a resource to the model.
        
        Args:
            name: Resource name
            capacity: Resource capacity
            resource_type: "regular" or "priority"
            
        Returns:
            The created resource object
        """
        if resource_type == "preemptive":
            resource = simpy.PreemptiveResource(self.env, capacity=capacity)
        elif resource_type == "priority":
            resource = simpy.PriorityResource(self.env, capacity)
        else:
            resource = simpy.Resource(self.env, capacity)
        
        self.resources[name] = resource
        return resource
    
    def add_block(self, block: 'BaseBlock'):
        """Add a block to the model."""
        # from blocks.create_block import CreateBlock
        # from blocks.dispose_block import DisposeBlock
        
        self.blocks[block.name] = block
        
        # Track special block types
        if isinstance(block, CreateBlock):
            self.create_blocks.append(block)
        elif isinstance(block, DisposeBlock):
            self.dispose_blocks.append(block)
    
    def connect_blocks(self, from_block_name: str, to_block_name: str):
        """Connect two blocks in sequence."""
        if from_block_name not in self.blocks or to_block_name not in self.blocks:
            raise ValueError(f"Block not found: {from_block_name} or {to_block_name}")
        
        self.blocks[from_block_name].connect_to(self.blocks[to_block_name])
    
    def set_warm_up_period(self, warm_up_time: float):
        """Set the warm-up period for the simulation."""
        self.warm_up_period = warm_up_time
        self.env.warm_up_period = warm_up_time
    
    def safe_delay_time(self, delay_function: Callable[[], float]) -> float:
        """
        Ensure delay times are non-negative.
        
        Wraps delay functions to replace negative values with 0,
        preventing simulation errors from statistical distributions
        that may generate negative values.
        
        Args:
            delay_function: Function returning delay time
            
        Returns:
            Non-negative delay time
        """
        delay = delay_function()
        return max(0.0, delay)
    
    def run_simulation(self, validate_resources: bool = True,  # NEW parameter
                      until: Optional[float] = None, 
                      seed: Optional[int] = None,
                      warm_up_period: float = 0.0,
                      check_stability: bool = False):
        """
        Run the simulation.
        
        Args:
            until: Simulation end time (None = run until no events)
            seed: Random seed for reproducibility
            warm_up_period: Warm-up period duration
            check_stability: Whether to check system stability before running
        """
        if validate_resources:
            self.validate_resources(raise_on_error=True)
        
        # Validate stopping condition
        self._validate_stopping_condition(until)
        
        if seed:
            import random
            random.seed(seed)
        
        # Set warm-up period
        if warm_up_period > 0:
            self.set_warm_up_period(warm_up_period)
            self.env.process(self._warm_up_monitor())
        
        # Check stability if requested
        if check_stability:
            # from validation.stability import StabilityAnalyzer
            analyzer = StabilityAnalyzer(self)
            self.stability_result = analyzer.check_system_stability()
            
            if self.stability_result >= 1.0:
                print("✅ Sistema estavel detectado, executando simulacao completa...")
            else:
                print("🚨 Sistema instavel detectado! Executando mesmo assim...")
        
        # Start all CREATE blocks
        for create_block in self.create_blocks:
            create_block.start_generation()
        
        # Run simulation
        self.env.run(until=until)
    
    def _validate_stopping_condition(self, until: Optional[float]):
        """Validate that simulation has a stopping condition."""
        has_time_limit = until is not None
        has_entity_limit = any(
            hasattr(cb, 'max_arrivals') and cb.max_arrivals is not None
            for cb in self.create_blocks
        )
        
        if not has_time_limit and not has_entity_limit:
            print("\n" + "=" * 70)
            print("ERRO CRITICO: SIMULACAO SEM CONDICAO DE PARADA DEFINIDA!")
            print("=" * 70)
            print("A simulacao nao possui criterio de termino e executaria infinitamente.")
            print("\nVoce DEVE especificar pelo menos UMA das seguintes condicoes:")
            print("  1. Tempo de simulacao: run_simulation(until=<tempo>)")
            print("  2. Numero maximo de chegadas: CreateBlock(..., max_arrivals=<n>)")
            print("\nExemplos validos:")
            print("  • model.run_simulation(until=1000)")
            print("  • CreateBlock(..., max_arrivals=500)")
            print("  • Ambos: until=1000 E max_arrivals=500")
            print("\nEXECUCAO ABORTADA para prevenir loop infinito.")
            print("=" * 70)
            sys.exit(1)
        
        if not has_time_limit and has_entity_limit:
            max_entities = max(
                cb.max_arrivals for cb in self.create_blocks
                if hasattr(cb, 'max_arrivals') and cb.max_arrivals is not None
            )
            print(f"\nAVISO: Simulacao limitada apenas por numero de entidades "
                  f"({max_entities}).")
            print("Tempo de execucao pode ser muito longo se sistema congestionado.")
            print("Recomenda-se tambem definir limite de tempo com until=<valor>\n")
    
    def _warm_up_monitor(self):
        """Monitor warm-up period completion."""
        if self.warm_up_period > 0:
            yield self.env.timeout(self.warm_up_period)
            self.is_warm_up_complete = True
            self._clear_warm_up_statistics()
    
    def _clear_warm_up_statistics(self):
        """Clear statistics collected during warm-up."""
        # from blocks.process_block import ProcessBlock, MultiProcessBlock
        
        # Reset DisposeBlock counters (keep data for plotting)
        for dispose_block in self.dispose_blocks:
            dispose_block.entities_disposed = 0
            dispose_block.total_system_time = 0.0
        
        # Reset ProcessBlock stats
        for block in self.blocks.values():
            if isinstance(block, (ProcessBlock, MultiProcessBlock)):
                block.entities_processed = 0
                block.total_delay_time = 0.0
                block.total_queue_time = 0.0
                
                if isinstance(block, ProcessBlock):
                    block.max_queue_length = 0
                    block.max_in_service = 0
                elif isinstance(block, MultiProcessBlock):
                    for metrics in block.max_metrics.values():
                        metrics['max_queue_length'] = 0
                        metrics['max_in_service'] = 0


    # @property
    # def entity_count(self) -> int:
    #     """Total entities disposed (post warm-up)."""
    #     return sum(block.entities_disposed for block in self.dispose_blocks)
    @property
    def entity_count(self) -> int:
        """Total entities disposed (post warm-up)."""
        disposed_sum = sum(block.entities_disposed for block in self.dispose_blocks)
        if disposed_sum > 0:
            return disposed_sum
        return sum(block.entities_created for block in self.create_blocks)
        
    
    @property
    def overall_throughput(self) -> float:
        """Overall system throughput (entities per time unit)."""
        effective_time = self.env.now - self.warm_up_period
        if effective_time > 0:
            return self.entity_count / effective_time
        return 0
    
    def get_results(self) -> Dict[str, Any]:
        """
        Get basic simulation results.
        
        For detailed metrics, use:
        - analytics.metrics.MetricsCollector
        - analytics.reporting.SimulationReporter
        """
        results = {
            'simulation_time': self.env.now,
            'warm_up_period': self.warm_up_period,
            'entity_count': self.entity_count,
            'throughput': self.overall_throughput,
            'blocks': {}
        }
        
        for block_name, block in self.blocks.items():
            results['blocks'][block_name] = {
                'type': type(block).__name__,
                'statistics': block.statistics
            }
            
            if hasattr(block, 'entities_processed'):
                results['blocks'][block_name]['entities_processed'] = block.entities_processed
            if hasattr(block, 'entities_created'):
                results['blocks'][block_name]['entities_created'] = block.entities_created
            if hasattr(block, 'entities_disposed'):
                results['blocks'][block_name]['entities_disposed'] = block.entities_disposed
            if hasattr(block, 'decision_counts'):
                results['blocks'][block_name]['decision_counts'] = block.decision_counts
        
        return results  



# =====================================================================
# FILE: config/simulation_config.py
# =====================================================================
@dataclass
class SimulationConfig:
    """Configuration for simulation run."""
    duration: float
    warm_up_period: float = 0.0
    seed: Optional[int] = None
    check_stability: bool = False
    
    def validate(self):
        """Validate configuration."""
        if self.duration <= 0:
            raise ValueError("Duration must be positive")
        if self.warm_up_period < 0:
            raise ValueError("Warm-up period cannot be negative")
        if self.warm_up_period >= self.duration:
            raise ValueError("Warm-up period must be less than duration")



# =====================================================================
# FILE: validation/stability.py
# =====================================================================
class StabilityAnalyzer:
    """Analyzes system stability and capacity."""
    
    def __init__(self, model):
        self.model = model
    
    def check_system_stability(self, sample_size: int = 1000) -> float:
        """
        Verify if system is mathematically stable.
        
        Args:
            sample_size: Number of samples for statistical estimation
            
        Returns:
            Stability index (>1.0 = stable, <1.0 = unstable)
        """
        print("\n🔍 VERIFICACAO DE ESTABILIDADE DO SISTEMA:")
        print("=" * 50)
        
        # Calculate arrival rate
        total_arrival_rate = self._calculate_arrival_rate(sample_size)
        print(f"📊 Taxa total de chegada estimada: "
              f"{total_arrival_rate * 60:.1f} entidades/hora")
        
        # Find bottleneck resource
        bottleneck_rate, bottleneck_resource = self._find_bottleneck(sample_size)
        system_capacity = bottleneck_rate
        
        print(f"📊 CAPACIDADE DO SISTEMA (gargalo em {bottleneck_resource}): "
              f"{system_capacity * 60:.1f} entidades/hora")
        
        # Calculate stability index
        stability = (system_capacity / total_arrival_rate 
                    if total_arrival_rate > 0 else float('inf'))
        print(f"🎯 INDICE DE ESTABILIDADE: {stability:.2f}")
        
        self._print_stability_assessment(stability)
        print("=" * 50)
        
        return stability
    
    def _calculate_arrival_rate(self, sample_size: int) -> float:
        """Calculate total system arrival rate."""
        total_arrival_rate = 0
        
        for create_block in self.model.create_blocks:
            samples = [create_block.inter_arrival_time() 
                      for _ in range(sample_size)]
            avg_interarrival = statistics.mean(samples)
            arrival_rate = 1 / avg_interarrival if avg_interarrival > 0 else 0
            total_arrival_rate += arrival_rate
            print(f"Taxa de chegada ({create_block.name}): "
                  f"{arrival_rate:.2f} entidades/min "
                  f"({arrival_rate*60:.1f}/h)")
        
        return total_arrival_rate
    
    def _find_bottleneck(self, sample_size: int) -> tuple:
        """
        Find bottleneck resource (lowest capacity).
        
        Returns:
            (bottleneck_rate, bottleneck_resource_name)
        """
        # from blocks.process_block import ProcessBlock, MultiProcessBlock
        
        bottleneck_rate = float('inf')
        bottleneck_resource = None
        
        # Group process blocks by resource
        resource_process_blocks = self._group_process_blocks_by_resource()
        
        for resource_name, process_blocks in resource_process_blocks.items():
            if resource_name in self.model.resources:
                resource = self.model.resources[resource_name]
                
                # Find slowest process block for this resource
                slowest_rate = self._calculate_resource_rate(
                    process_blocks, sample_size)
                
                # Resource capacity = capacity × service rate
                resource_capacity = resource.capacity * slowest_rate
                resource_type = ("Priority" if isinstance(resource, 
                                simpy.PriorityResource) else 
                                "Preemptive" if isinstance(self.resource, simpy.PreemptiveResource) 
                                else "Regular")
                
                print(f"  📋 {resource_name} ({resource_type}): "
                      f"{resource.capacity} × {slowest_rate:.3f}/min = "
                      f"{resource_capacity:.3f}/min ({resource_capacity * 60:.1f}/h)")
                
                if resource_capacity < bottleneck_rate:
                    bottleneck_rate = resource_capacity
                    bottleneck_resource = resource_name
        
        return bottleneck_rate, bottleneck_resource
    
    def _group_process_blocks_by_resource(self) -> Dict[str, List]:
        """Group process blocks by the resources they use."""
        # from blocks.process_block import ProcessBlock, MultiProcessBlock
        
        resource_process_blocks = {}
        
        for block in self.model.blocks.values():
            if isinstance(block, ProcessBlock):
                resource_name = self._find_resource_name(block.resource)
                if resource_name:
                    if resource_name not in resource_process_blocks:
                        resource_process_blocks[resource_name] = []
                    resource_process_blocks[resource_name].append(block)
                    
            elif isinstance(block, MultiProcessBlock):
                for resource, units_required in block.resource_requirements.items():
                    resource_name = self._find_resource_name(resource)
                    if resource_name:
                        if resource_name not in resource_process_blocks:
                            resource_process_blocks[resource_name] = []
                        resource_process_blocks[resource_name].append(
                            (block, units_required))
        
        return resource_process_blocks
    
    def _find_resource_name(self, resource_obj) -> str:
        """Find resource name from object."""
        for name, res in self.model.resources.items():
            if res == resource_obj:
                return name
        return None
    
    def _calculate_resource_rate(self, process_blocks: List, 
                                 sample_size: int) -> float:
        """Calculate effective service rate for a resource."""
        # from blocks.process_block import MultiProcessBlock
        
        slowest_rate = float('inf')
        
        for item in process_blocks:
            if isinstance(item, tuple):  # MultiProcessBlock with units
                process_block, units_required = item
                samples = [process_block.delay_time() 
                          for _ in range(sample_size)]
                avg_service_time = statistics.mean(samples)
                service_rate = (1 / avg_service_time 
                              if avg_service_time > 0 else 0)
                effective_rate = service_rate / units_required
            else:  # Regular ProcessBlock
                process_block = item
                samples = [process_block.delay_time() 
                          for _ in range(sample_size)]
                avg_service_time = statistics.mean(samples)
                service_rate = (1 / avg_service_time 
                              if avg_service_time > 0 else 0)
                effective_rate = service_rate
            
            if effective_rate < slowest_rate:
                slowest_rate = effective_rate
        
        return slowest_rate
    
    def _print_stability_assessment(self, stability: float):
        """Print assessment of stability index."""
        if stability > 1.2:
            print("✅ Sistema SUPER dimensionado (capacidade >> demanda)")
        elif stability > 1.05:
            print("✅ Sistema estavel (capacidade > demanda)")
        elif stability > 0.95:
            print("⚠️ Sistema NO LIMITE (capacidade ≈ demanda) - cuidado!")
        elif stability > 0.8:
            print("🚨 Sistema INSTAVEL (demanda > capacidade)")
        else:
            print("💥 COLAPSO IMINENTE (demanda >> capacidade)")



# =====================================================================
# FILE: validation/warmup.py
# =====================================================================
class WarmUpAnalyzer:
    """Analyzes warm-up period requirements."""
    
    def __init__(self, model):
        self.model = model
    
    def analyze_warm_up_period(self):
        """Analyze data to suggest adequate warm-up period."""
        # from blocks.process_block import ProcessBlock, MultiProcessBlock
        
        print("\n🔍 ANALISE DE WARM-UP:")
        print("=" * 50)
        
        resource_blocks = self._group_blocks_by_resource()
        
        for resource_name, blocks in resource_blocks.items():
            all_data = self._collect_resource_data(resource_name, blocks)
            
            if not all_data or len(all_data) < 100:
                continue
            
            all_data.sort(key=lambda x: x[0])
            capacity = self.model.resources[resource_name].capacity
            
            # Calculate utilization over time
            times = [point[0] for point in all_data]
            utilizations = [point[1] / capacity for point in all_data]
            
            # Find stabilization point
            stabilization_time = self._find_stabilization_point(
                times, utilizations)
            
            print(f"📋 {resource_name}:")
            if stabilization_time:
                print(f"   Estabilizacao detectada em: t={stabilization_time:.1f}")
                print(f"   Warm-up sugerido: {stabilization_time * 1.2:.1f} "
                      f"(20% de margem)")
            else:
                print("   Sistema pode nao ter estabilizado completamente")
            
            # Calculate final utilization
            final_utilizations = utilizations[-min(100, len(utilizations)//4):]
            avg_final_util = np.mean(final_utilizations) * 100
            print(f"   Utilizacao final media: {avg_final_util:.1f}%")
        
        print("\nRECOMENDACOES:")
        print("• Observe os graficos para identificar quando a utilizacao se estabiliza")
        print("• O periodo de warm-up deve ser pelo menos ate o ponto de estabilizacao")
        print("• Use 20-30% de margem adicional sobre o tempo de estabilizacao")
        print("• Sistemas complexos podem precisar de warm-up mais longo")
        print("=" * 50)
    
    def _group_blocks_by_resource(self) -> dict:
        """Group process blocks by resource."""
        # from blocks.process_block import ProcessBlock, MultiProcessBlock
        
        resource_blocks = {}
        
        for block in self.model.blocks.values():
            if isinstance(block, ProcessBlock):
                resource_name = self._find_resource_name(block.resource)
                if resource_name:
                    if resource_name not in resource_blocks:
                        resource_blocks[resource_name] = []
                    resource_blocks[resource_name].append(block)
                    
            elif isinstance(block, MultiProcessBlock):
                for res in block.resource_requirements.keys():
                    resource_name = self._find_resource_name(res)
                    if resource_name:
                        if resource_name not in resource_blocks:
                            resource_blocks[resource_name] = []
                        resource_blocks[resource_name].append(block)
        
        return resource_blocks
    
    def _find_resource_name(self, resource_obj) -> str:
        """Find resource name from object."""
        for name, res in self.model.resources.items():
            if res == resource_obj:
                return name
        return None
    
    def _collect_resource_data(self, resource_name: str, blocks: List) -> List:
        """Collect resource data from blocks."""
        # from blocks.process_block import ProcessBlock, MultiProcessBlock
        
        all_data = []
        for block in blocks:
            if isinstance(block, ProcessBlock):
                all_data.extend(block.resource_data)
            elif isinstance(block, MultiProcessBlock):
                resource_obj = self.model.resources[resource_name]
                if resource_obj in block.resource_data:
                    all_data.extend(block.resource_data[resource_obj])
        
        return all_data
    
    def _find_stabilization_point(self, times: List[float], 
                                  utilizations: List[float]) -> float:
        """Find when variance stabilizes (system reaches steady state)."""
        window_size = min(50, len(utilizations) // 4)
        variances = []
        variance_times = []
        
        for i in range(window_size, len(utilizations) - window_size):
            window = utilizations[i-window_size:i+window_size]
            variance = np.var(window)
            variances.append(variance)
            variance_times.append(times[i])
        
        if not variances:
            return None
        
        # Find when variance stabilizes (< 50% of initial variance)
        initial_variance = np.mean(variances[:min(20, len(variances))])
        stabilization_threshold = initial_variance * 0.5
        
        for i, var in enumerate(variances):
            if var < stabilization_threshold:
                # Verify it stays stable
                stable_period = variances[i:i+min(20, len(variances)-i)]
                if (len(stable_period) >= 10 and 
                    all(v < stabilization_threshold for v in stable_period)):
                    return variance_times[i]
        
        return None



# =====================================================================
# FILE: analytics/metrics.py
# =====================================================================
class MetricsCollector:
    """Collects and calculates metrics from a completed simulation."""
    
    def __init__(self, model):
        """
        Initialize metrics collector.
        
        Args:
            model: SimulationModel instance with completed simulation
        """
        self.model = model
    
    def get_entity_metrics_summary(self) -> Dict[str, Any]:
        """
        Calculate entity-level metrics (time in system, by activity).
        
        Returns:
            Dictionary containing system time and per-activity metrics
        """
        if not self.model.dispose_blocks:
            return {'tempo_medio_sistema': 0, 'atividades': {}}
        
        # Collect only post-warm-up disposed entities
        post_warmup_entities = [
            e for dispose_block in self.model.dispose_blocks
            for e in dispose_block.disposed_entities
            if e.get_attribute('disposal_time', 0) >= self.model.warm_up_period
        ]
        
        if not post_warmup_entities:
            return {'tempo_medio_sistema': 0, 'atividades': {}}
        
        # Calculate system time
        system_times = [entity.get_attribute('system_time', 0) 
                       for entity in post_warmup_entities]
        
        # Group metrics by activity
        activity_queue_times = {}
        activity_service_times = {}
        activity_system_times = {}
        
        for entity in post_warmup_entities:
            for key, value in entity.data.items():
                # Skip None or nan values
                if value is None or (isinstance(value, float) and math.isnan(value)):
                    continue
                    
                if key.endswith('_queue_time'):
                    activity_name = key.replace('_queue_time', '')
                    if activity_name not in activity_queue_times:
                        activity_queue_times[activity_name] = []
                    activity_queue_times[activity_name].append(value)
                    
                elif key.endswith('_service_time'):
                    activity_name = key.replace('_service_time', '')
                    if activity_name not in activity_service_times:
                        activity_service_times[activity_name] = []
                    activity_service_times[activity_name].append(value)
        
        # Calculate system time for each activity
        all_activities = set(list(activity_queue_times.keys()) + 
                           list(activity_service_times.keys()))
        
        for activity_name in all_activities:
            queue_times = activity_queue_times.get(activity_name, [])
            service_times = activity_service_times.get(activity_name, [])
            
            activity_system_times[activity_name] = []
            min_length = min(len(queue_times), len(service_times))
            
            for i in range(min_length):
                system_time = queue_times[i] + service_times[i]
                activity_system_times[activity_name].append(system_time)
        
        # Build summary
        summary = {
            'tempo_medio_sistema': statistics.mean(system_times) if system_times else 0,
            'atividades': {}
        }
        
        for activity_name in all_activities:
            qt = activity_queue_times.get(activity_name, [])
            st = activity_service_times.get(activity_name, [])
            sys_t = activity_system_times.get(activity_name, [])
            
            summary['atividades'][activity_name] = {
                'tempo_medio_fila': statistics.mean(qt) if len(qt) > 0 else 0,
                'tempo_medio_atendimento': statistics.mean(st) if len(st) > 0 else 0,
                'tempo_medio_sistema': statistics.mean(sys_t) if len(sys_t) > 0 else 0
            }
        
        return summary
    
    def get_resource_metrics_summary(self) -> Dict[str, Any]:
        """
        Calculate resource-level metrics (utilization, queue lengths).
        
        Returns:
            Dictionary mapping resource names to their metrics
        """
        # from blocks.process_block import ProcessBlock, MultiProcessBlock
        
        summary = {}
        
        # Group ProcessBlocks by resource
        resource_blocks = self._group_blocks_by_resource()
        
        for resource_name, blocks in resource_blocks.items():
            if resource_name in self.model.resources:
                resource = self.model.resources[resource_name]
                resource_obj = resource
                
                # Combine data from all blocks using this resource
                combined_data = []
                max_queue_length = 0
                max_in_service = 0
                
                for block in blocks:
                    if isinstance(block, ProcessBlock):
                        combined_data.extend(block.resource_data)
                        max_queue_length = max(max_queue_length, block.max_queue_length)
                        max_in_service = max(max_in_service, block.max_in_service)
                    elif isinstance(block, MultiProcessBlock):
                        if resource_obj in block.resource_data:
                            combined_data.extend(block.resource_data[resource_obj])
                            metrics = block.max_metrics[resource_obj]
                            max_queue_length = max(max_queue_length, 
                                                  metrics['max_queue_length'])
                            max_in_service = max(max_in_service, 
                                                metrics['max_in_service'])
                
                # Deduplicate data points by time
                combined_data = self._deduplicate_resource_data(combined_data)
                
                # Calculate metrics
                if combined_data:
                    avg_queue = self._calculate_time_weighted_avg(
                        combined_data, lambda x: x[2])
                    avg_in_service = self._calculate_time_weighted_avg(
                        combined_data, lambda x: x[1])
                    utilization = (avg_in_service / resource.capacity 
                                 if resource.capacity > 0 else 0)
                    
                    busy_time, idle_time = self._calculate_busy_idle_time(
                        combined_data, resource)
                else:
                    avg_queue = 0
                    avg_in_service = 0
                    utilization = 0
                    busy_time = 0
                    idle_time = self.model.env.now - self.model.warm_up_period
                
                effective_time = self.model.env.now - self.model.warm_up_period
                
                summary[resource_name] = {
                    'numero_medio_fila': avg_queue,
                    'numero_medio_atendimento': avg_in_service,
                    'numero_medio_sistema': avg_queue + avg_in_service,
                    'taxa_utilizacao': utilization,
                    'maximo_fila': max_queue_length,
                    'maximo_atendimento': max_in_service,
                    'maximo_sistema': max_queue_length + max_in_service,
                    'tempo_ocupado': busy_time,
                    'tempo_ocioso': idle_time,
                    'percentual_ocupacao': ((busy_time / effective_time * 100) 
                                           if effective_time > 0 else 0),
                    'percentual_ociosidade': ((idle_time / effective_time * 100) 
                                             if effective_time > 0 else 0)
                }
        
        return summary
    
    def _group_blocks_by_resource(self) -> Dict[str, List]:
        """Group ProcessBlocks by the resources they use."""
        # from blocks.process_block import ProcessBlock, MultiProcessBlock
        
        resource_blocks = {}
        
        for block in self.model.blocks.values():
            if isinstance(block, ProcessBlock):
                resource_name = self._find_resource_name(block.resource)
                if resource_name:
                    if resource_name not in resource_blocks:
                        resource_blocks[resource_name] = []
                    resource_blocks[resource_name].append(block)
                    
            elif isinstance(block, MultiProcessBlock):
                for resource in block.resource_requirements.keys():
                    resource_name = self._find_resource_name(resource)
                    if resource_name:
                        if resource_name not in resource_blocks:
                            resource_blocks[resource_name] = []
                        resource_blocks[resource_name].append(block)
        
        return resource_blocks
    
    def _find_resource_name(self, resource_obj) -> str:
        """Find resource name from resource object."""
        for res_name, res in self.model.resources.items():
            if res == resource_obj:
                return res_name
        return None
    
    def _deduplicate_resource_data(self, data: List[Tuple]) -> List[Tuple]:
        """Deduplicate resource data points by timestamp."""
        if not data:
            return []
        
        data.sort(key=lambda x: x[0])
        from itertools import groupby
        
        unique_data = []
        for timestamp, group in groupby(data, key=lambda x: x[0]):
            group_list = list(group)
            unique_data.append(group_list[-1])  # Keep last state at timestamp
        
        return unique_data
    
    def _calculate_time_weighted_avg(self, data: List[Tuple], 
                                     extractor: Callable) -> float:
        """Calculate time-weighted average from resource data."""
        if not data:
            return 0
        
        data.sort(key=lambda x: x[0])
        effective_time = self.model.env.now - self.model.warm_up_period
        
        if effective_time <= 0:
            return 0
        
        area = 0
        prev_time = self.model.warm_up_period
        
        # Find initial value at warm-up boundary
        pre_warmup_data = [point for point in data 
                          if point[0] <= self.model.warm_up_period]
        post_warmup_data = [point for point in data 
                           if point[0] > self.model.warm_up_period]
        
        if pre_warmup_data:
            prev_value = extractor(pre_warmup_data[-1])
        else:
            prev_value = 0
        
        # Process all post-warmup data points
        for point in post_warmup_data:
            time = point[0]
            area += prev_value * (time - prev_time)
            prev_time = time
            prev_value = extractor(point)
        
        # Add final interval
        area += prev_value * (self.model.env.now - prev_time)
        
        return area / effective_time if effective_time > 0 else 0
    
    def _calculate_busy_idle_time(self, data: List[Tuple], 
                                  resource) -> Tuple[float, float]:
        """Calculate busy and idle time for a resource."""
        busy_time = 0
        idle_time = 0
        prev_time = self.model.warm_up_period
        prev_count = 0
        
        post_warmup_data = [p for p in data if p[0] >= self.model.warm_up_period]
        
        if post_warmup_data:
            prev_count = post_warmup_data[0][1]
            prev_time = post_warmup_data[0][0]
            
            for time, count, qlen in post_warmup_data[1:]:
                time_interval = time - prev_time
                if prev_count > 0:
                    busy_time += time_interval
                else:
                    idle_time += time_interval
                prev_time = time
                prev_count = count
            
            final_interval = self.model.env.now - prev_time
            if prev_count > 0:
                busy_time += final_interval
            else:
                idle_time += final_interval
        else:
            idle_time = self.model.env.now - self.model.warm_up_period
        
        return busy_time, idle_time


# =====================================================================
# FILE: analytics/wip_metrics.py
# =====================================================================
class WIPTracker:
    """
    Tracks Work-in-Process (WIP) metrics during simulation.
    
    WIP is tracked by monitoring entity creation and disposal events,
    providing time-weighted statistics on system occupancy.
    """
    
    def __init__(self, model):
        """
        Initialize WIP tracker.
        
        Args:
            model: SimulationModel instance
        """
        self.model = model
        self.wip_data = []  # List of (time, wip_count) tuples
        self._last_update_time = 0
        self._current_wip = 0
    
    def get_wip_summary(self) -> Dict[str, Any]:
        """
        Calculate WIP statistics from simulation data.
        
        Returns:
            Dictionary with WIP metrics including time-weighted average
        """
        # Build WIP timeline from entity creation/disposal events
        wip_timeline = self._build_wip_timeline()
        
        if not wip_timeline:
            return self._empty_wip_summary()
        
        # Calculate time-weighted average WIP
        avg_wip = self._calculate_time_weighted_wip(wip_timeline)
        
        # Calculate max WIP
        max_wip = max(count for _, count in wip_timeline)
        
        # Get final WIP (entities still in system)
        final_wip = wip_timeline[-1][1] if wip_timeline else 0
        # if sum(block.entities_disposed for block in self.dispose_blocks) == 0:
        #     final_wip = sum(block.entities_created for block in self.create_blocks)
        # else:
        #     final_wip = wip_timeline[-1][1] if wip_timeline else 0
        
        return {
            'average_wip': avg_wip,
            'max_wip': max_wip,
            'final_wip': final_wip,
            'wip_timeline': wip_timeline
        }
    
    # def _build_wip_timeline(self) -> List[Tuple[float, int]]:
    #     """
    #     Build WIP timeline from entity creation and disposal events.
        
    #     Returns:
    #         List of (time, wip_count) tuples
    #     """
    #     events = []
        
    #     # Add creation events (+1 to WIP)
    #     for create_block in self.model.create_blocks:
    #         # Entities are created at specific times based on inter-arrival
    #         # We need to reconstruct this from disposed entities
    #         pass
        
    #     # Add disposal events (-1 from WIP)
    #     for dispose_block in self.model.dispose_blocks:
    #         for entity in dispose_block.disposed_entities:
    #             creation_time = entity.creation_time
    #             disposal_time = entity.get_attribute('disposal_time', self.model.env.now)
                
    #             events.append((creation_time, +1))  # Entity enters system
    #             events.append((disposal_time, -1))  # Entity exits system
        
    #     # Sort events by time
    #     events.sort(key=lambda x: x[0])
        
    #     # Build timeline
    #     timeline = []
    #     current_wip = 0
        
    #     for time, change in events:
    #         current_wip += change
    #         timeline.append((time, current_wip))
        
    #     return timeline

    def _build_wip_timeline(self) -> List[Tuple[float, int]]:
        """
        Build WIP timeline from entity creation and disposal events.
        
        Returns:
            List of (time, wip_count) tuples
        """
        # Get event_logger
        event_logger = None
        for block in self.model.blocks.values():
            if hasattr(block, 'event_logger') and block.event_logger is not None:
                event_logger = block.event_logger
                break

        events = []
        if event_logger is None:
            # Fall back to disposed entities
            total_disposed = sum(b.entities_disposed for b in self.model.dispose_blocks)
            if total_disposed == 0:
                total_created = sum(c.entities_created for c in self.model.create_blocks)
                timeline = [(0.0, 0)]
                if total_created > 0:
                    timeline.append((self.model.env.now, total_created))
                return timeline
            else:
                for dispose_block in self.model.dispose_blocks:
                    for entity in dispose_block.disposed_entities:
                        creation_time = entity.creation_time
                        disposal_time = entity.get_attribute('disposal_time', self.model.env.now)
                        events.append((creation_time, +1))
                        events.append((disposal_time, -1))
        else:
            # Use event log
            df = event_logger.get_dataframe()
            grouped = df[df['activity'].isin(['Arrival', 'Discharge'])].groupby('case_id')
            for case_id, case_df in grouped:
                arrival_row = case_df[case_df['activity'] == 'Arrival']
                discharge_row = case_df[case_df['activity'] == 'Discharge']
                if not arrival_row.empty:
                    arrival_time = arrival_row['timestamp'].values[0]
                    events.append((arrival_time, +1))
                    if not discharge_row.empty:
                        discharge_time = discharge_row['timestamp'].values[0]
                        events.append((discharge_time, -1))

        # Sort events
        events.sort(key=lambda x: (x[0], x[1]))

        # Build timeline
        timeline = []
        current_wip = 0
        for time, change in events:
            current_wip += change
            timeline.append((time, current_wip))

        # Add final point if needed
        now = self.model.env.now
        if timeline and timeline[-1][0] < now:
            timeline.append((now, current_wip))
        elif not timeline:
            timeline = [(0.0, 0), (now, 0)]

        return timeline
    
    def _calculate_time_weighted_wip(self, timeline: List[Tuple[float, int]]) -> float:
        """
        Calculate time-weighted average WIP.
        
        Args:
            timeline: List of (time, wip_count) tuples
            
        Returns:
            Time-weighted average WIP
        """
        if not timeline:
            return 0.0
        
        # Filter to post-warm-up period
        warm_up = self.model.warm_up_period
        post_warmup_timeline = [(t, w) for t, w in timeline if t >= warm_up]
        
        if not post_warmup_timeline:
            return 0.0
        
        # Calculate time-weighted average
        total_area = 0.0
        prev_time = warm_up
        
        # Get initial WIP at warm-up boundary
        pre_warmup = [w for t, w in timeline if t <= warm_up]
        prev_wip = pre_warmup[-1] if pre_warmup else 0
        
        for time, wip in post_warmup_timeline:
            # Add rectangle area: width × height
            total_area += prev_wip * (time - prev_time)
            prev_time = time
            prev_wip = wip
        
        # Add final interval to simulation end
        total_area += prev_wip * (self.model.env.now - prev_time)
        
        # Divide by total time
        effective_time = self.model.env.now - warm_up
        
        return total_area / effective_time if effective_time > 0 else 0.0
    
    def _empty_wip_summary(self) -> Dict[str, Any]:
        """Return empty WIP summary."""
        return {
            'average_wip': 0,
            'max_wip': 0,
            'final_wip': 0,
            'wip_timeline': []
        }
    
    # def get_system_time_summary(self) -> Dict[str, Any]:
    #     """
    #     Calculate total time in system statistics.
        
    #     Returns:
    #         Dictionary with system time metrics
    #     """
    #     if not self.model.dispose_blocks:
    #         return self._empty_system_time_summary()
        
    #     # Get post-warm-up entities
    #     post_warmup_entities = [
    #         e for dispose_block in self.model.dispose_blocks
    #         for e in dispose_block.disposed_entities
    #         if e.get_attribute('disposal_time', 0) >= self.model.warm_up_period
    #     ]
        
    #     if not post_warmup_entities:
    #         return self._empty_system_time_summary()
        
    #     # Calculate system times
    #     system_times = [e.get_attribute('system_time', 0) for e in post_warmup_entities]
        
    #     return {
    #         'average_system_time': np.mean(system_times),
    #         'std_system_time': np.std(system_times),
    #         'min_system_time': np.min(system_times),
    #         'max_system_time': np.max(system_times),
    #         'median_system_time': np.median(system_times),
    #         'num_entities': len(system_times)
    #     }

    def get_system_time_summary(self) -> Dict[str, Any]:
        """
        Calculate total time in system statistics.
        
        Returns:
            Dictionary with system time metrics
        """
        if not self.model.dispose_blocks:
            return self._empty_system_time_summary()
        
        # Calculate total disposed entities
        total_disposed = sum(len(dispose_block.disposed_entities) for dispose_block in self.model.dispose_blocks)
        
        if total_disposed > 0:
            # Original logic for when there are disposed entities
            post_warmup_entities = [
                e for dispose_block in self.model.dispose_blocks
                for e in dispose_block.disposed_entities
                if e.get_attribute('disposal_time', 0) >= self.model.warm_up_period
            ]
            
            if not post_warmup_entities:
                return self._empty_system_time_summary()
            
            system_times = [e.get_attribute('system_time', 0) for e in post_warmup_entities]
        else:
            # Find event_logger
            event_logger = None
            for block in self.model.blocks.values():
                if hasattr(block, 'event_logger') and block.event_logger is not None:
                    event_logger = block.event_logger
                    break
            
            if event_logger is None:
                # If no logger and no disposed, return empty
                return self._empty_system_time_summary()
            
            # Use event log to get creation times
            df = event_logger.get_dataframe()
            arrival_df = df[df['activity'] == 'Arrival']
            
            # Filter post-warmup creations
            post_warmup_arrivals = arrival_df[arrival_df['timestamp'] >= self.model.warm_up_period]
            
            if post_warmup_arrivals.empty:
                return self._empty_system_time_summary()
            
            now = self.model.env.now
            system_times = [now - timestamp for timestamp in post_warmup_arrivals['timestamp']]
        
        return {
            'average_system_time': np.mean(system_times),
            'std_system_time': np.std(system_times),
            'min_system_time': np.min(system_times),
            'max_system_time': np.max(system_times),
            'median_system_time': np.median(system_times),
            'num_entities': len(system_times)
        }
    
    def _empty_system_time_summary(self) -> Dict[str, Any]:
        """Return empty system time summary."""
        return {
            'average_system_time': 0,
            'std_system_time': 0,
            'min_system_time': 0,
            'max_system_time': 0,
            'median_system_time': 0,
            'num_entities': 0
        }
    
    def plot_wip_over_time(self):
        """Plot WIP evolution over time."""
        wip_summary = self.get_wip_summary()
        timeline = wip_summary['wip_timeline']
        
        if not timeline:
            print("No WIP data available to plot.")
            return

        # --- START MODIFICATION ---
        final_time = self.model.env.now        
        # 1. Ensure the timeline extends to the end of the simulation for plotting
        if timeline[-1][0] < final_time:
            # Append a point at the final time with the final WIP count
            final_wip_count = timeline[-1][1]
            timeline.append((final_time, final_wip_count))
        # --- END MODIFICATION ---
        
        times = [t for t, _ in timeline]
        wips = [w for _, w in timeline]
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Plot as step function
        ax.step(times, wips, where='post', linewidth=2, color='steelblue', label='WIP')
        
        # Add average line
        ax.axhline(y=wip_summary['average_wip'], color='red', linestyle='--', 
                  linewidth=2, label=f"Average WIP: {wip_summary['average_wip']:.2f}")
        
        # Mark warm-up period
        if self.model.warm_up_period > 0:
            ax.axvline(x=self.model.warm_up_period, color='orange', linestyle='--',
                      linewidth=2, label=f"Warm-up end (t={self.model.warm_up_period})")
            ax.axvspan(0, self.model.warm_up_period, alpha=0.2, color='orange')

        # ✅ NEW: Annotate final WIP if > 0
        final_wip = wip_summary['final_wip']
        if final_wip >= 0:
            ax.annotate(
                f'Final WIP: {final_wip}\n(entities still in system)',
                xy=(self.model.env.now, final_wip),
                xytext=(self.model.env.now * 0.8, final_wip * 1.2),
                arrowprops=dict(arrowstyle='->', color='red', lw=2),
                fontsize=10,
                bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7)
            )
        
        ax.set_xlabel('Simulation Time', fontsize=12, fontweight='bold')
        ax.set_ylabel('Work in Process (WIP)', fontsize=12, fontweight='bold')
        ax.set_title('Work in Process Over Time', fontsize=14, fontweight='bold')
        ax.legend(loc='best', framealpha=0.9)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
    
    def plot_system_time_distribution(self):
        """Plot distribution of total time in system."""
        if not self.model.dispose_blocks:
            print("No system time data available to plot.")
            return
        
        # Get post-warm-up entities
        post_warmup_entities = [
            e for dispose_block in self.model.dispose_blocks
            for e in dispose_block.disposed_entities
            if e.get_attribute('disposal_time', 0) >= self.model.warm_up_period
        ]
        
        if not post_warmup_entities:
            print("No post-warm-up entities to plot.")
            return
        
        system_times = [e.get_attribute('system_time', 0) for e in post_warmup_entities]
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
        
        # Histogram
        ax1.hist(system_times, bins=30, color='skyblue', edgecolor='black', alpha=0.7)
        ax1.axvline(x=np.mean(system_times), color='red', linestyle='--', 
                   linewidth=2, label=f'Mean: {np.mean(system_times):.2f}')
        ax1.axvline(x=np.median(system_times), color='green', linestyle='--',
                   linewidth=2, label=f'Median: {np.median(system_times):.2f}')
        ax1.set_xlabel('Total Time in System', fontsize=11, fontweight='bold')
        ax1.set_ylabel('Frequency', fontsize=11, fontweight='bold')
        ax1.set_title('System Time Distribution', fontsize=12, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Box plot
        ax2.boxplot(system_times, vert=True, patch_artist=True,
                   boxprops=dict(facecolor='lightblue', alpha=0.7))
        ax2.set_ylabel('Total Time in System', fontsize=11, fontweight='bold')
        ax2.set_title('System Time Box Plot', fontsize=12, fontweight='bold')
        ax2.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        plt.show()



# =====================================================================
# FILE: validation/resource_validator.py
# =====================================================================
class ResourceValidationError(Exception):
    """Raised when resource configuration is invalid."""
    """
    Resource configuration validation for simulation models.
    Validates that:
    - Resource units requested don't exceed capacity
    - Resources exist before being used
    - No duplicate resource names
    - Valid resource types
    - Consistent resource usage across blocks
    """
    # print(">>> VALIVAÇÃO DE RECURSOS!")
    pass


# =====================================================================
# FILE: validation/resource_validator.py
# =====================================================================
class ResourceValidator:
    """
    Validates resource configurations in simulation models.
    
    Performs comprehensive checks to catch configuration errors before
    simulation runtime, providing clear error messages for fixes.
    """
    
    def __init__(self, model):
        """
        Initialize resource validator.
        
        Args:
            model: SimulationModel instance to validate
        """
        self.model = model
        self.errors = []
        self.warnings = []
    
    def validate_all(self, raise_on_error: bool = True) -> bool:
        """
        Run all validation checks.
        
        Args:
            raise_on_error: If True, raise exception on errors; if False, return status
            
        Returns:
            True if all validations pass, False otherwise
            
        Raises:
            ResourceValidationError: If validation fails and raise_on_error=True
        """
        self.errors = []
        self.warnings = []
        
        # Run all validation checks
        self._validate_resource_definitions()
        self._validate_resource_units()
        self._validate_resource_references()
        self._validate_resource_types()
        self._validate_multi_resource_blocks()
        
        # Print results
        self._print_validation_results()
        
        # Handle errors
        if self.errors:
            if raise_on_error:
                error_msg = self._format_error_message()
                raise ResourceValidationError(error_msg)
            return False
        
        return True
    
    def _validate_resource_definitions(self):
        """Check for duplicate resource names and invalid capacities."""
        seen_names = set()
        
        for name, resource in self.model.resources.items():
            # Check for duplicates (shouldn't happen with dict, but check anyway)
            if name in seen_names:
                self.errors.append(
                    f"DUPLICATE RESOURCE: '{name}' is defined multiple times"
                )
            seen_names.add(name)
            
            # Check capacity
            if resource.capacity <= 0:
                self.errors.append(
                    f"INVALID CAPACITY: Resource '{name}' has capacity "
                    f"{resource.capacity} (must be > 0)"
                )
            
            # Warning for very high capacity
            if resource.capacity > 1000:
                self.warnings.append(
                    f"HIGH CAPACITY: Resource '{name}' has unusually high capacity "
                    f"({resource.capacity}). Is this intentional?"
                )
    
    def _validate_resource_units(self):
        """Validate that resource units don't exceed capacity."""
        # from blocks.process_block import ProcessBlock, MultiProcessBlock
        
        for block_name, block in self.model.blocks.items():
            if isinstance(block, ProcessBlock):
                self._validate_single_resource_block(block_name, block)
            elif isinstance(block, MultiProcessBlock):
                self._validate_multi_resource_block_units(block_name, block)
    
    def _validate_single_resource_block(self, block_name: str, block):
        """Validate ProcessBlock resource configuration."""
        resource = block.resource
        units_requested = getattr(block, 'resource_units', 1)
        
        # Find resource name
        resource_name = self._find_resource_name(resource)
        
        if resource_name:
            capacity = resource.capacity
            
            # CRITICAL ERROR: Units exceed capacity
            if units_requested > capacity:
                self.errors.append(
                    f"RESOURCE OVERALLOCATION: Block '{block_name}' requests "
                    f"{units_requested} units of '{resource_name}', but capacity is "
                    f"only {capacity}. This will cause DEADLOCK!"
                )
            
            # WARNING: Using full capacity (might cause bottleneck)
            elif units_requested == capacity:
                self.warnings.append(
                    f"FULL RESOURCE USE: Block '{block_name}' uses ALL {capacity} "
                    f"units of '{resource_name}'. This may create a bottleneck."
                )
            
            # WARNING: Units > 50% of capacity
            elif units_requested > capacity * 0.5:
                utilization_pct = (units_requested / capacity) * 100
                self.warnings.append(
                    f"HIGH RESOURCE USE: Block '{block_name}' uses {units_requested} "
                    f"of {capacity} units ({utilization_pct:.0f}%) of '{resource_name}'. "
                    f"Consider if this is appropriate."
                )
        else:
            self.errors.append(
                f"UNKNOWN RESOURCE: Block '{block_name}' uses a resource that "
                f"is not registered in the model"
            )
    
    def _validate_multi_resource_block_units(self, block_name: str, block):
        """Validate MultiProcessBlock resource requirements."""
        for resource, units_requested in block.resource_requirements.items():
            resource_name = self._find_resource_name(resource)
            
            if resource_name:
                capacity = resource.capacity
                
                # CRITICAL ERROR: Units exceed capacity
                if units_requested > capacity:
                    self.errors.append(
                        f"RESOURCE OVERALLOCATION: Block '{block_name}' requests "
                        f"{units_requested} units of '{resource_name}', but capacity is "
                        f"only {capacity}. This will cause DEADLOCK!"
                    )
                
                # WARNING: Using full capacity
                elif units_requested == capacity:
                    self.warnings.append(
                        f"FULL RESOURCE USE: Block '{block_name}' uses ALL {capacity} "
                        f"units of '{resource_name}'. Combined with other resources, "
                        f"this may create significant bottleneck."
                    )
            else:
                self.errors.append(
                    f"UNKNOWN RESOURCE: Block '{block_name}' uses a resource that "
                    f"is not registered in the model"
                )
    
    def _validate_resource_references(self):
        """Check that all referenced resources exist."""
        # from blocks.process_block import ProcessBlock, MultiProcessBlock
        
        registered_resources = set(self.model.resources.values())
        
        for block_name, block in self.model.blocks.items():
            if isinstance(block, ProcessBlock):
                if block.resource not in registered_resources:
                    self.errors.append(
                        f"UNREGISTERED RESOURCE: Block '{block_name}' uses a resource "
                        f"that was not added via model.add_resource()"
                    )
            
            elif isinstance(block, MultiProcessBlock):
                for resource in block.resource_requirements.keys():
                    if resource not in registered_resources:
                        self.errors.append(
                            f"UNREGISTERED RESOURCE: Block '{block_name}' uses a resource "
                            f"that was not added via model.add_resource()"
                        )
    
    def _validate_resource_types(self):
        """Validate resource types (Regular vs Priority vs Preemptive)."""
        # from blocks.process_block import ProcessBlock, MultiProcessBlock
        
        for block_name, block in self.model.blocks.items():
            if isinstance(block, (ProcessBlock, MultiProcessBlock)):
                resources = []
                
                if isinstance(block, ProcessBlock):
                    resources = [block.resource]
                else:
                    resources = list(block.resource_requirements.keys())
                
                for resource in resources:
                    resource_name = self._find_resource_name(resource)
                    
                    if resource_name:
                        # Check if resource type matches usage
                        if isinstance(resource, simpy.PriorityResource):
                            # Priority resource should be used with priority entities
                            if not self._has_priority_generator():
                                self.warnings.append(
                                    f"PRIORITY MISMATCH: Resource '{resource_name}' is "
                                    f"PriorityResource but no entities have priorities. "
                                    f"Consider using regular Resource instead."
                                )
                        
                        # Check for PreemptiveResource (if supported)
                        if isinstance(resource, simpy.PreemptiveResource):
                            self.warnings.append(
                                f"PREEMPTIVE RESOURCE: '{resource_name}' is PreemptiveResource. "
                                f"Ensure your code handles preemption correctly."
                            )
    
    def _validate_multi_resource_blocks(self):
        """Validate blocks that require multiple resources simultaneously."""
        # from blocks.process_block import MultiProcessBlock
        
        for block_name, block in self.model.blocks.items():
            if isinstance(block, MultiProcessBlock):
                total_units = sum(block.resource_requirements.values())
                
                # WARNING: Requesting many resources
                if total_units > 5:
                    self.warnings.append(
                        f"COMPLEX RESOURCE REQUIREMENTS: Block '{block_name}' "
                        f"requires {total_units} total resource units across "
                        f"{len(block.resource_requirements)} resources. "
                        f"This may increase chance of deadlock."
                    )
                
                # Check for potential deadlock with other multi-resource blocks
                self._check_circular_dependencies(block_name, block)
    
    def _check_circular_dependencies(self, block_name: str, block):
        """
        Check for potential circular dependencies in resource requirements.
        
        This is a simplified check - full deadlock detection is complex.
        """
        # from blocks.process_block import MultiProcessBlock
        
        block_resources = set(block.resource_requirements.keys())
        
        for other_name, other_block in self.model.blocks.items():
            if other_name == block_name:
                continue
            
            if isinstance(other_block, MultiProcessBlock):
                other_resources = set(other_block.resource_requirements.keys())
                
                # If blocks share resources, potential for deadlock
                if block_resources.intersection(other_resources):
                    self.warnings.append(
                        f"SHARED RESOURCES: Blocks '{block_name}' and '{other_name}' "
                        f"both require some of the same resources. This could lead to "
                        f"deadlock if not carefully designed. Review the model logic."
                    )
                    break  # Only warn once per block
    
    def _has_priority_generator(self) -> bool:
        """Check if any CreateBlock has priority generator."""
        # from blocks.create_block import CreateBlock
        
        for block in self.model.blocks.values():
            if isinstance(block, CreateBlock):
                if block.priority_generator is not None:
                    return True
        return False
    
    def _find_resource_name(self, resource_obj) -> Optional[str]:
        """Find resource name from resource object."""
        for name, res in self.model.resources.items():
            if res == resource_obj:
                return name
        return None
    
    def _print_validation_results(self):
        """Print validation results with color coding."""
        if not self.errors and not self.warnings:
            print("\n" + "=" * 70)
            print("RESOURCE VALIDATION: ALL CHECKS PASSED")
            print("=" * 70)
            return
        
        print("\n" + "=" * 70)
        print("RESOURCE VALIDATION RESULTS")
        print("=" * 70)
        
        if self.errors:
            print(f"\nCRITICAL ERRORS FOUND: {len(self.errors)}")
            print("-" * 70)
            for i, error in enumerate(self.errors, 1):
                print(f"{i}. {error}")
        
        if self.warnings:
            print(f"\nWARNINGS: {len(self.warnings)}")
            print("-" * 70)
            for i, warning in enumerate(self.warnings, 1):
                print(f"{i}. {warning}")
        
        print("=" * 70)
    
    def _format_error_message(self) -> str:
        """Format errors into exception message."""
        msg = f"\n{len(self.errors)} CRITICAL RESOURCE CONFIGURATION ERROR(S) FOUND:\n\n"
        for i, error in enumerate(self.errors, 1):
            msg += f"{i}. {error}\n"
        msg += "\nFIX THESE ERRORS BEFORE RUNNING SIMULATION!"
        return msg
    
    def print_resource_summary(self):
        """Print summary of all resources and their usage."""
        # from blocks.process_block import ProcessBlock, MultiProcessBlock
        
        print("\n" + "=" * 70)
        print("RESOURCE CONFIGURATION SUMMARY")
        print("=" * 70)
        
        for name, resource in sorted(self.model.resources.items()):
            capacity = resource.capacity
            resource_type = self._get_resource_type_name(resource)
            
            print(f"\nResource: {name}")
            print(f"  Type: {resource_type}")
            print(f"  Capacity: {capacity} units")
            
            # Find blocks using this resource
            using_blocks = []
            total_max_usage = 0
            
            for block_name, block in self.model.blocks.items():
                if isinstance(block, ProcessBlock):
                    if block.resource == resource:
                        units = getattr(block, 'resource_units', 1)
                        using_blocks.append((block_name, units))
                        total_max_usage = max(total_max_usage, units)
                
                elif isinstance(block, MultiProcessBlock):
                    if resource in block.resource_requirements:
                        units = block.resource_requirements[resource]
                        using_blocks.append((block_name, units))
                        total_max_usage = max(total_max_usage, units)
            
            if using_blocks:
                print(f"  Used by {len(using_blocks)} block(s):")
                for block_name, units in using_blocks:
                    pct = (units / capacity * 100) if capacity > 0 else 0
                    print(f"    - {block_name}: {units} units ({pct:.0f}% of capacity)")
                
                print(f"  Maximum single allocation: {total_max_usage} units "
                      f"({total_max_usage/capacity*100:.0f}% of capacity)")
            else:
                print(f"  WARNING: Resource not used by any block!")
        
        print("=" * 70)
    
    def _get_resource_type_name(self, resource) -> str:
        """Get human-readable resource type name."""
        if isinstance(resource, simpy.PreemptiveResource):
            return "PreemptiveResource"
        elif isinstance(resource, simpy.PriorityResource):
            return "PriorityResource"
        elif isinstance(resource, simpy.Resource):
            return "Resource"
        else:
            return "Unknown"



# =====================================================================
# FILE: analytics/reporting.py
# =====================================================================
class SimulationReporter:
    """Generates formatted reports from simulation results."""
    
    def __init__(self, model):
        self.model = model
        self.metrics = MetricsCollector(model)
        self.wip_tracker = None  # NEW: Lazy loaded
        self.HOURS = 60  # Time conversion (base: minutes)
        self.DAYS = 1440
        self.YEARS = 525600

    def _get_wip_tracker(self):
        """Lazy load WIP tracker."""
        if self.wip_tracker is None:
            # from analytics.wip_metrics import WIPTracker
            self.wip_tracker = WIPTracker(self.model)
        return self.wip_tracker

    
    def _print_wip_metrics(self):
        """Print WIP and system time metrics."""
        wip_tracker = self._get_wip_tracker()
        
        # WIP metrics
        wip_summary = wip_tracker.get_wip_summary()
        print("\nWORK IN PROCESS (WIP) METRICS:")
        print(f"  Average WIP: {wip_summary['average_wip']:.2f} entities")
        print(f"  Maximum WIP: {wip_summary['max_wip']} entities")
        print(f"  Current WIP: {wip_summary['final_wip']} entities")
        
        # System time metrics
        system_time_summary = wip_tracker.get_system_time_summary()
        print("\nTOTAL TIME IN SYSTEM:")
        print(f"  Average: {system_time_summary['average_system_time']:.2f} time units")
        print(f"  Std Dev: {system_time_summary['std_system_time']:.2f}")
        print(f"  Min: {system_time_summary['min_system_time']:.2f}")
        print(f"  Max: {system_time_summary['max_system_time']:.2f}")
        print(f"  Median: {system_time_summary['median_system_time']:.2f}")
        print(f"  Based on: {system_time_summary['num_entities']} entities")
        
        # Little's Law verification
        self._verify_littles_law(wip_summary, system_time_summary)
    
    def _verify_littles_law(self, wip_summary: Dict, system_time_summary: Dict):
        """
        Verify Little's Law: L = λ × W
        Where:
        - L = Average number in system (WIP)
        - λ = Arrival rate (throughput)
        - W = Average time in system
        """
        avg_wip = wip_summary['average_wip']
        avg_system_time = system_time_summary['average_system_time']
        throughput = self.model.overall_throughput
        
        if throughput > 0 and avg_system_time > 0:
            print("\nLITTLE'S LAW VERIFICATION:")
            print(f"  L (Avg WIP): {avg_wip:.2f}")
            print(f"  lambda (Throughput): {throughput:.4f} entities/time unit")
            print(f"  W (Avg Time): {avg_system_time:.2f} time units")
            
            # Calculate expected WIP using Little's Law
            expected_wip = throughput * avg_system_time
            print(f"  Expected WIP (lambda * W): {expected_wip:.2f}")
            
            # Calculate percentage difference
            if avg_wip > 0:
                diff_percent = abs(avg_wip - expected_wip) / avg_wip * 100
                print(f"  Difference: {diff_percent:.1f}%")
                
                if diff_percent < 5:
                    print("  Status: Excellent match (Little's Law verified)")
                elif diff_percent < 10:
                    print("  Status: Good match")
                else:
                    print("  Status: Significant difference (check warm-up period)")


    def print_results(self):
        """Print comprehensive simulation results INCLUDING WIP."""
        print("=" * 60)
        duration_hours = self.model.env.now / self.HOURS
        print(f"📊 RESULTADOS DA SIMULACAO (⏳ Duracao: {duration_hours:.0f} horas)")
        
        if self.model.warm_up_period > 0:
            effective_time = self.model.env.now - self.model.warm_up_period
            print(f"WARM-UP: {self.model.warm_up_period/self.HOURS:.0f} horas | "
                  f"PERIODO DE ESTATISTICAS: {effective_time/self.HOURS:.0f} horas")
        print("=" * 60)
        
        self._print_stability_results()
        self._print_system_metrics()
        self._print_wip_metrics()  # NEW: Add WIP metrics here
        # self._print_activity_metrics()
        # self._print_resource_metrics()
        # self._print_entity_counts()
        # self._print_block_statistics()        
        # self.print_financial_summary() # Print financial balance sheet
        
    
    def _print_stability_results(self):
        """Print stability analysis if available."""
        if self.model.stability_result is not None:
            print(f"\nINDICE DE ESTABILIDADE: {self.model.stability_result:.2f}")
            if self.model.stability_result > 1.2:
                print("STATUS: Sistema SUPER dimensionado")
            elif self.model.stability_result > 1.05:
                print("STATUS: Sistema estavel")
            elif self.model.stability_result > 0.95:
                print("STATUS: Sistema NO LIMITE")
            elif self.model.stability_result > 0.8:
                print("STATUS: Sistema INSTAVEL")
            else:
                print("STATUS: COLAPSO IMINENTE")
    
    def _print_system_metrics(self):
        """Print overall system metrics."""
        entity_summary = self.metrics.get_entity_metrics_summary()
        system_time = entity_summary.get('tempo_medio_sistema', 0)
        
        print(f"\n⏰ Tempo medio no sistema: {system_time/self.HOURS:.2f} horas")
        print(f"👥 Total de entidades processadas: {self.model.entity_count}")
        print(f"⚙️  Throughput: {self.model.overall_throughput*self.HOURS:.2f} "
              f"entidades/hora")
        print(f"📋 Recursos ativos: {list(self.model.resources.keys())}")
        
        if self.model.warm_up_period > 0:
            print(f"\nNOTA: Estatisticas baseadas apenas no periodo pos warm-up")
            print(f"   (t > {self.model.warm_up_period/self.HOURS:.1f} horas)")
    
    def _print_activity_metrics(self):
        """Print per-activity metrics."""
        entity_summary = self.metrics.get_entity_metrics_summary()
        activities = entity_summary.get('atividades', {})
        
        if activities:
            print("\n📈 METRICAS DAS ENTIDADES POR ATIVIDADE:")
            for activity_name, metrics in activities.items():
                print(f"  {activity_name}:")
                print(f"    Tempo medio em fila: "
                      f"{metrics['tempo_medio_fila']:.2f}")
                print(f"    Tempo medio de atendimento: "
                      f"{metrics['tempo_medio_atendimento']:.2f}")
                print(f"    Tempo medio no sistema: "
                      f"{metrics['tempo_medio_sistema']:.2f}")
    
    
    def _print_resource_metrics(self):
        """Print per-resource metrics with analysis."""
        
        validator = ResourceValidator(self.model)
        validator.print_resource_summary()


        resource_summary = self.metrics.get_resource_metrics_summary()
        
        if resource_summary:
            print("\n📈 METRICAS POR RECURSO:")
            for resource_name, metrics in resource_summary.items():
                capacity = self.model.resources[resource_name].capacity
                util = metrics['taxa_utilizacao']
                
                print(f"  {resource_name} (capacidade: {capacity}):")
                print(f"    Taxa de utilizacao: {util:.2f}")
                print(f"    Tempo ocupado: {metrics['tempo_ocupado']:.2f} "
                      f"({metrics['percentual_ocupacao']:.1f}%)")
                print(f"    Tempo ocioso: {metrics['tempo_ocioso']:.2f} "
                      f"({metrics['percentual_ociosidade']:.1f}%)")
                print(f"    Maximo em fila: {metrics['maximo_fila']}")
                print(f"    Maximo em atendimento: {metrics['maximo_atendimento']}")
                print(f"    Numero medio em fila: "
                      f"{metrics['numero_medio_fila']:.2f}")
                print(f"    Numero medio em atendimento: "
                      f"{metrics['numero_medio_atendimento']:.2f}")
                
                # Analysis
                print(f"    Analise (💡): ", end="")
                if util > 0.85:
                    print(f"Sistema sobrecarregado ({util:.1%})! "
                          f"Considere aumentar capacidade.")
                elif util < 0.25:
                    print(f"Sistema ocioso ({util:.1%})! "
                          f"Considere ajustar capacidade.")
                else:
                    print("Sistema operando dentro dos parametros esperados.")
                print()
    
    def _print_entity_counts(self):
        """Print entity creation and disposal counts."""
        total_created = sum(block.entities_created 
                          for block in self.model.create_blocks)
        total_disposed = sum(
            len([e for e in block.disposed_entities 
                 if e.get_attribute('disposal_time', 0) >= 
                 self.model.warm_up_period])
            for block in self.model.dispose_blocks
        )
        
        print(f"\nEntidades criadas: {total_created}")
        print(f"Entidades que sairam: {total_disposed}")
        print(f"Entidades no sistema: {total_created - total_disposed}")
    
    def _print_block_statistics(self):
        """Print statistics for individual blocks."""
        print("\nESTATISTICAS DOS BLOCOS:")
        for block_name, block in self.model.blocks.items():
            print(f"\n{block_name} ({type(block).__name__}):")
            
            if hasattr(block, 'entities_processed'):
                print(f"  Entidades processadas: {block.entities_processed}")
                if block.entities_processed > 0:
                    avg_delay = block.total_delay_time / block.entities_processed
                    avg_queue = block.total_queue_time / block.entities_processed
                    print(f"  Tempo medio em atendimento: {avg_delay:.2f}")
                    print(f"  Tempo medio em fila: {avg_queue:.2f}")
            
            if hasattr(block, 'decision_counts'):
                print(f"  Numero de decisoes: {block.decision_counts}")


# =====================================================================
# FILE: analytics/plotting.py
# =====================================================================
class SimulationPlotter:
    """Creates visualizations from simulation results."""
    
    def __init__(self, model):
        self.model = model
        self.metrics = None  # Lazy loaded
        self.wip_tracker = None  # NEW

    def _get_wip_tracker(self):
        """Lazy load WIP tracker."""
        if self.wip_tracker is None:
            # from analytics.wip_metrics import WIPTracker
            self.wip_tracker = WIPTracker(self.model)
        return self.wip_tracker
    
    def plot_wip_over_time(self):
        """Plot WIP evolution over time."""
        wip_tracker = self._get_wip_tracker()
        wip_tracker.plot_wip_over_time()
    
    def plot_system_time_distribution(self):
        """Plot distribution of total time in system."""
        wip_tracker = self._get_wip_tracker()
        wip_tracker.plot_system_time_distribution()
    
    def _get_metrics(self):
        """Lazy load metrics collector."""
        if self.metrics is None:
            # from analytics.metrics import MetricsCollector
            self.metrics = MetricsCollector(self.model)
        return self.metrics
    
    def plot_resource_use_over_time(self, show_warm_up: bool = True, 
                                    resource: Optional[str] = None,
                                    moving_average_window: int = 50):
        """
        Plot resource utilization over time for warm-up analysis.
        
        Args:
            show_warm_up: Mark warm-up period visually
            resource: Specific resource to plot (None = all)
            moving_average_window: Window size for smoothing
        """
        # from blocks.process_block import ProcessBlock, MultiProcessBlock
        
        # Group ProcessBlocks by resource
        resource_blocks = self._group_blocks_by_resource()
        
        if not resource_blocks:
            print("Nenhum ProcessBlock encontrado para plotar")
            return
        
        # Filter for specific resource if requested
        if resource:
            if resource in resource_blocks:
                resource_blocks = {resource: resource_blocks[resource]}
            else:
                print(f"Recurso '{resource}' nao encontrado")
                return
        
        # Create subplots
        num_resources = len(resource_blocks)
        fig, axes = plt.subplots(num_resources, 1, 
                                figsize=(12, 4 * num_resources))
        if num_resources == 1:
            axes = [axes]
        
        fig.suptitle('Uso de Recursos (determine o tempo ideal de Warm-up)', 
                     fontsize=14, fontweight='bold')
        
        for idx, (resource_name, blocks) in enumerate(resource_blocks.items()):
            ax = axes[idx] if num_resources > 1 else axes[0]            
            self._plot_single_resource(ax, resource_name, blocks, 
                                      show_warm_up, moving_average_window)
        
        axes[-1].set_xlabel('Tempo de Simulacao')
        plt.tight_layout()
        plt.show()
    
    def _plot_single_resource(self, ax, resource_name: str, blocks: List,
                             show_warm_up: bool, moving_avg_window: int):
        """Plot utilization for a single resource."""
        # from blocks.process_block import ProcessBlock, MultiProcessBlock
        
        # Combine and deduplicate data
        all_data = []
        seen_timestamps = set()
        
        for block in blocks:
            if isinstance(block, ProcessBlock):
                for data_point in block.resource_data:
                    timestamp = data_point[0]
                    if timestamp not in seen_timestamps:
                        all_data.append(data_point)
                        seen_timestamps.add(timestamp)
            elif isinstance(block, MultiProcessBlock):
                resource_obj = self.model.resources[resource_name]
                if resource_obj in block.resource_data:
                    for data_point in block.resource_data[resource_obj]:
                        timestamp = data_point[0]
                        if timestamp not in seen_timestamps:
                            all_data.append(data_point)
                            seen_timestamps.add(timestamp)
        
        if not all_data:
            ax.text(0.5, 0.5, 'Sem dados disponiveis', 
                   ha='center', va='center', transform=ax.transAxes)
            ax.set_title(f'{resource_name} (capacidade: '
                        f'{self.model.resources[resource_name].capacity})')
            return
        
        # Sort and filter data
        all_data.sort(key=lambda x: x[0])

        max_time = (self.model.env.now if self.model.env.now > 0 
                   else max(point[0] for point in all_data))


        all_data = [point for point in all_data if point[0] <= max_time]
        
        if not all_data:
            ax.text(0.5, 0.5, 'Dados filtrados estao vazios', 
                   ha='center', va='center', transform=ax.transAxes)
            return
        
        # Extract time and utilization with step function
        times, utilizations = self._create_step_function(
            all_data, resource_name, max_time)

        # print(f"Times: {times}")
        # print(f"Utilizations: {utilizations}")
        
        # Plot utilization
        ax.plot(times, utilizations, drawstyle='steps-post', 
               alpha=0.7, color='lightblue', linewidth=1.5, 
               label='Utilizacao')
        
        # Plot moving average
        if len(utilizations) >= moving_avg_window:
            times_array = np.array(times)
            utils_array = np.array(utilizations)
            moving_avg = np.convolve(utils_array, 
                                    np.ones(moving_avg_window)/moving_avg_window,
                                    mode='valid')
            moving_avg_times = times_array[moving_avg_window-1:]
            ax.plot(moving_avg_times, moving_avg, color='darkblue', 
                   linewidth=2, label=f'Media movel ({moving_avg_window} pontos)',
                   alpha=0.8)
        
        # Mark warm-up period
        if show_warm_up and self.model.warm_up_period > 0:
            ax.axvline(x=self.model.warm_up_period, color='red', 
                      linestyle='--', linewidth=2, 
                      label=f'Fim do Warm-up (t={self.model.warm_up_period})')
            ax.axvspan(0, self.model.warm_up_period, alpha=0.2, 
                      color='red', label='Periodo de Warm-up')
        
        # Formatting
        capacity = self.model.resources[resource_name].capacity
        ax.set_title(f'{resource_name} (capacidade: {capacity})')
        ax.set_ylabel('Utilizacao (%)')
        ax.set_ylim(0, 105)
        ax.set_xlim(0, max_time)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper right')
        
        # Add utilization bands
        ax.axhline(y=85, color='orange', linestyle=':', alpha=0.7, 
                  label='85% (Limite recomendado)')
        ax.axhline(y=100, color='red', linestyle=':', alpha=0.7)
    
    def _create_step_function(self, data: List, resource_name: str, 
                             max_time: float) -> tuple:
        """Create step function for resource utilization."""
        times = []
        utilizations = []
        capacity = self.model.resources[resource_name].capacity
        
        for i, point in enumerate(data):
            current_time = point[0]
            current_util = point[1] / capacity * 100
            
            times.append(current_time)
            utilizations.append(current_util)
            
            # Add point before next state change
            if i < len(data) - 1:
                next_time = data[i + 1][0]
                if next_time > current_time:
                    times.append(next_time - 0.0001)
                    utilizations.append(current_util)
        
        # Extend to end of simulation
        if times and times[-1] < max_time:
            times.append(max_time)
            utilizations.append(utilizations[-1])
        
        return times, utilizations
    
    def _group_blocks_by_resource(self) -> dict:
        """Group process blocks by resource."""
        # from blocks.process_block import ProcessBlock, MultiProcessBlock
        
        resource_blocks = {}
        
        for block in self.model.blocks.values():
            if isinstance(block, ProcessBlock):
                resource_name = self._find_resource_name(block.resource)
                if resource_name:
                    if resource_name not in resource_blocks:
                        resource_blocks[resource_name] = []
                    resource_blocks[resource_name].append(block)
                    
            elif isinstance(block, MultiProcessBlock):
                for res in block.resource_requirements.keys():
                    resource_name = self._find_resource_name(res)
                    if resource_name:
                        if resource_name not in resource_blocks:
                            resource_blocks[resource_name] = []
                        resource_blocks[resource_name].append(block)
        
        return resource_blocks
    
    def _find_resource_name(self, resource_obj) -> str:
        """Find resource name from object."""
        for name, res in self.model.resources.items():
            if res == resource_obj:
                return name
        return None
    
    def plot_activity_metrics(self):
        """Create stacked bar chart for queue + service time by activity."""
        metrics = self._get_metrics()
        entity_summary = metrics.get_entity_metrics_summary()
        activities_data = entity_summary.get('atividades', {})
        
        if not activities_data:
            print("No activity data available to plot.")
            return
        
        # Extract data
        activity_names = list(activities_data.keys())
        queue_times = [activities_data[name]['tempo_medio_fila'] 
                      for name in activity_names]
        service_times = [activities_data[name]['tempo_medio_atendimento'] 
                        for name in activity_names]
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 8))
        
        bar_width = 0.6
        x_pos = np.arange(len(activity_names))
        
        # Stacked bars
        bars1 = ax.bar(x_pos, queue_times, bar_width, 
                      label='Tempo medio em fila', color='lightcoral', alpha=0.8)
        bars2 = ax.bar(x_pos, service_times, bar_width, 
                      bottom=queue_times, label='Tempo medio de atendimento', 
                      color='lightblue', alpha=0.8)
        
        # Add labels
        for i, (qt, st) in enumerate(zip(queue_times, service_times)):
            total = qt + st
            
            if qt > 0.5:
                ax.text(i, qt/2, f'{qt:.1f}', ha='center', va='center', 
                       fontweight='bold', color='darkred')
            if st > 0.5:
                ax.text(i, qt + st/2, f'{st:.1f}', ha='center', va='center',
                       fontweight='bold', color='darkblue')
            
            max_total = max(queue_times[j] + service_times[j] 
                          for j in range(len(activity_names)))
            ax.text(i, total + max_total * 0.02, f'{total:.1f}', 
                   ha='center', va='bottom', fontweight='bold', fontsize=11)
        
        # Formatting
        ax.set_xlabel('Atividades', fontsize=12, fontweight='bold')
        ax.set_ylabel('Tempo (minutos)', fontsize=12, fontweight='bold')
        ax.set_title('Metricas das Entidades por Atividade\n'
                    '(Tempo medio em fila + Tempo medio de atendimento)', 
                    fontsize=14, fontweight='bold', pad=20)
        ax.set_xticks(x_pos)
        ax.set_xticklabels(activity_names, rotation=45, ha='right')
        ax.legend(loc='upper right', framealpha=0.9)
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        ax.set_axisbelow(True)
        
        plt.tight_layout()

        self._print_activity_efficiency_analysis(activities_data)

        plt.show()
        
        
    
    def _print_activity_efficiency_analysis(self, activities_data: dict):
        """Print efficiency analysis for activities."""
        print("\nANALISE DE EFICIENCIA POR ATIVIDADE:")
        print("=" * 45)
        
        for name, data in activities_data.items():
            qt = data['tempo_medio_fila']
            st = data['tempo_medio_atendimento']
            total = qt + st
            
            if total > 0:
                queue_pct = (qt / total) * 100
                service_pct = (st / total) * 100
                
                print(f"{name}:")
                print(f"  Tempo total: {total:.1f} min")
                print(f"  Fila: {qt:.1f} min ({queue_pct:.1f}%)")
                print(f"  Atendimento: {st:.1f} min ({service_pct:.1f}%)")
                
                if queue_pct > 60:
                    print(f"  🚨 ALERTA: {queue_pct:.1f}% do tempo e gasto em fila!")
                elif queue_pct > 30:
                    print(f"  ⚠️  ATENCAO: {queue_pct:.1f}% do tempo e gasto em fila")
                else:
                    print(f"  ✅ Eficiente: apenas {queue_pct:.1f}% do tempo em fila")
                print()
    
    def plot_resources_utilization(self):
        """Create bar chart showing utilization rate per resource."""
        metrics = self._get_metrics()
        resource_summary = metrics.get_resource_metrics_summary()
        
        if not resource_summary:
            print("No resource data available to plot.")
            return
        
        # Extract data
        resource_names = list(resource_summary.keys())
        utilization_rates = [resource_summary[name]['taxa_utilizacao'] * 100 
                           for name in resource_names]
        capacities = [self.model.resources[name].capacity 
                     for name in resource_names]
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 8))
        
        bar_width = 0.6
        x_pos = np.arange(len(resource_names))
        
        # Color by utilization level
        colors = []
        for util in utilization_rates:
            if util >= 85:
                colors.append('darkred')
            elif util >= 70:
                colors.append('orange')
            elif util >= 50:
                colors.append('gold')
            elif util >= 25:
                colors.append('lightgreen')
            else:
                colors.append('lightblue')
        
        # Create bars
        bars = ax.bar(x_pos, utilization_rates, bar_width, 
                     color=colors, alpha=0.8, edgecolor='black', linewidth=1)
        
        # Add labels
        for i, (util, cap) in enumerate(zip(utilization_rates, capacities)):
            ax.text(i, util + max(utilization_rates) * 0.02, f'{util:.1f}%', 
                   ha='center', va='bottom', fontweight='bold', fontsize=11)
            if util > 15:
                ax.text(i, util/2, f'Cap: {cap}', ha='center', va='center',
                       fontweight='bold', 
                       color='white' if util > 50 else 'black')
        
        # Formatting
        ax.set_xlabel('Recursos', fontsize=12, fontweight='bold')
        ax.set_ylabel('Taxa de Utilizacao (%)', fontsize=12, fontweight='bold')
        ax.set_title('Taxa de Utilizacao por Recurso', 
                    fontsize=14, fontweight='bold', pad=20)
        ax.set_xticks(x_pos)
        ax.set_xticklabels(resource_names, rotation=45, ha='right')
        ax.set_ylim(0, max(105, max(utilization_rates) * 1.1))
        
        # Reference lines
        ax.axhline(y=85, color='red', linestyle='--', alpha=0.7, 
                  label='85% (Limite critico)')
        ax.axhline(y=70, color='orange', linestyle='--', alpha=0.5, 
                  label='70% (Utilizacao alta)')
        ax.axhline(y=25, color='blue', linestyle='--', alpha=0.3, 
                  label='25% (Subutilizacao)')
        
        ax.legend(loc='upper right', framealpha=0.9)
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        ax.set_axisbelow(True)
        
        plt.tight_layout()

        self._print_resource_utilization_analysis(resource_summary)

        plt.show()
        
    def _print_resource_utilization_analysis(self, resource_summary: dict):
        """Print detailed resource utilization analysis."""
        print("\nANALISE DE UTILIZACAO DE RECURSOS:")
        print("=" * 42)
        
        for name, metrics in resource_summary.items():
            util = metrics['taxa_utilizacao'] * 100
            cap = self.model.resources[name].capacity
            
            print(f"{name} (Capacidade: {cap}):")
            print(f"  Taxa de utilizacao: {util:.1f}%")
            
            if util >= 90:
                print(f"  🚨 CRITICO: Recurso extremamente sobrecarregado!")
                print(f"  💡 Recomendacao: Aumentar capacidade urgentemente")
            elif util >= 85:
                print(f"  🔥 ALERTA: Recurso sobrecarregado")
                print(f"  💡 Recomendacao: Considerar aumentar capacidade")
            elif util >= 70:
                print(f"  ⚠️  ATENCAO: Utilizacao alta, monitorar")
            elif util >= 50:
                print(f"  ✅ BOM: Utilizacao moderada e eficiente")
            elif util >= 25:
                print(f"  ℹ️ BAIXA: Utilizacao abaixo do ideal")
            else:
                print(f"  ⚪ MUITO BAIXA: Recurso subutilizado")
            print()



# =====================================================================
# FILE: analytics/financial.py
# =====================================================================
class FinancialAnalyzer:
    """Analyzes financial metrics from simulation results."""
    
    def __init__(self, model):
        """
        Initialize financial analyzer.
        
        Args:
            model: SimulationModel instance with completed simulation
        """
        self.model = model
    
    def get_financial_summary(self) -> Dict[str, Any]:
        """
        Calculate financial summary from disposed entities.
        
        Returns:
            Dictionary with total revenue, costs by activity, and net profit
        """
        if not self.model.dispose_blocks:
            return self._empty_summary()
        
        post_warmup_entities = self._get_post_warmup_entities()
        
        if not post_warmup_entities:
            return self._empty_summary()
        
        total_revenue = 0
        costs_by_activity = {}
        
        for entity in post_warmup_entities:
            for key, value in entity.data.items():
                if 'revenue' in key.lower() and isinstance(value, (int, float)):
                    total_revenue += value
                
                if 'cost' in key.lower() and isinstance(value, (int, float)):
                    activity_name = key.replace('_cost', '')
                    if activity_name not in costs_by_activity:
                        costs_by_activity[activity_name] = 0
                    costs_by_activity[activity_name] += value
        
        total_costs = sum(costs_by_activity.values())
        net_profit = total_revenue - total_costs
        n_entities = len(post_warmup_entities)
        
        return {
            'total_revenue': total_revenue,
            'total_costs': total_costs,
            'net_profit': net_profit,
            'costs_by_activity': costs_by_activity,
            'num_entities': n_entities,
            'avg_revenue_per_entity': total_revenue / n_entities if n_entities else 0,
            'avg_cost_per_entity': total_costs / n_entities if n_entities else 0,
            'avg_profit_per_entity': net_profit / n_entities if n_entities else 0
        }
    
    def _empty_summary(self) -> Dict[str, Any]:
        """Return empty financial summary."""
        return {
            'total_revenue': 0,
            'total_costs': 0,
            'net_profit': 0,
            'costs_by_activity': {},
            'num_entities': 0,
            'avg_revenue_per_entity': 0,
            'avg_cost_per_entity': 0,
            'avg_profit_per_entity': 0
        }
    
    def _get_post_warmup_entities(self):
        """Get entities disposed after warm-up period."""
        return [
            e for dispose_block in self.model.dispose_blocks
            for e in dispose_block.disposed_entities
            if e.get_attribute('disposal_time', 0) >= self.model.warm_up_period
        ]
    
    def print_financial_summary(self):
        """Print formatted financial balance sheet."""
        financial_data = self.get_financial_summary()
        
        print("\n" + "=" * 60)
        print("FINANCIAL BALANCE SHEET")
        print("=" * 60)
        
        print(f"\nBased on {financial_data['num_entities']} entities (post warm-up)")
        
        self._print_revenue_section(financial_data)
        self._print_costs_section(financial_data)
        self._print_profit_section(financial_data)
        
        print("=" * 60)
    
    def _print_revenue_section(self, data: Dict):
        """Print revenue section."""
        print("\nREVENUE:")
        print(f"  Total Revenue: ${data['total_revenue']:,.2f}")
        print(f"  Average per Entity: ${data['avg_revenue_per_entity']:,.2f}")
    
    def _print_costs_section(self, data: Dict):
        """Print costs section."""
        print("\nCOSTS BY ACTIVITY:")
        if data['costs_by_activity']:
            for activity, cost in sorted(data['costs_by_activity'].items(),
                                        key=lambda x: x[1], reverse=True):
                percentage = (cost / data['total_costs'] * 100) if data['total_costs'] > 0 else 0
                print(f"  {activity}: ${cost:,.2f} ({percentage:.1f}%)")
        else:
            print("  No cost data available")
        
        print(f"\n  Total Costs: ${data['total_costs']:,.2f}")
        print(f"  Average per Entity: ${data['avg_cost_per_entity']:,.2f}")
    
    def _print_profit_section(self, data: Dict):
        """Print profit section with analysis."""
        print("\n" + "-" * 60)
        print(f"NET PROFIT: ${data['net_profit']:,.2f}")
        print(f"   Average per Entity: ${data['avg_profit_per_entity']:,.2f}")
        
        if data['total_revenue'] > 0:
            profit_margin = (data['net_profit'] / data['total_revenue']) * 100
            print(f"   Profit Margin: {profit_margin:.1f}%")
            
            if profit_margin > 20:
                print("   Excellent profit margin")
            elif profit_margin > 10:
                print("   Good profit margin")
            elif profit_margin > 0:
                print("   Low profit margin")
            else:
                print("   Operating at a loss!")
    
    def plot_financial_breakdown(self):
        """Create visualizations for financial data."""
        financial_data = self.get_financial_summary()
        
        if not financial_data['costs_by_activity']:
            print("No financial data available to plot.")
            return
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Pie chart: Cost distribution
        activities = list(financial_data['costs_by_activity'].keys())
        costs = list(financial_data['costs_by_activity'].values())
        
        ax1.pie(costs, labels=activities, autopct='%1.1f%%', startangle=90)
        ax1.set_title('Cost Distribution by Activity', fontsize=14, fontweight='bold')
        
        # Bar chart: Revenue vs Costs vs Profit
        categories = ['Revenue', 'Costs', 'Net Profit']
        values = [
            financial_data['total_revenue'],
            financial_data['total_costs'],
            financial_data['net_profit']
        ]
        colors = ['green', 'red', 'blue' if financial_data['net_profit'] >= 0 else 'darkred']
        
        bars = ax2.bar(categories, values, color=colors, alpha=0.7, edgecolor='black')
        ax2.set_ylabel('Amount ($)', fontsize=12, fontweight='bold')
        ax2.set_title('Financial Overview', fontsize=14, fontweight='bold')
        ax2.grid(axis='y', alpha=0.3)
        
        # Add value labels on bars
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'${value:,.0f}',
                    ha='center', va='bottom' if value >= 0 else 'top',
                    fontweight='bold', fontsize=10)
        
        plt.tight_layout()
        plt.show()



# =====================================================================
# FILE: statistics/replication.py
# =====================================================================
class ReplicationFramework:
    """
    Framework for running multiple simulation replications with statistical analysis.
    
    The framework follows the method of independent replications for steady-state
    simulation analysis, computing confidence intervals using the t-distribution.
    """
    
    def __init__(self, simulation_function: Callable, n_replications: int = 30):
        """
        Initialize replication framework.
        
        Args:
            simulation_function: Function that creates, runs, and returns a simulation model.
                                Should accept seed parameter and return a model instance.
            n_replications: Number of replications to run (default 30 for CLT applicability)
        """
        self.simulation_function = simulation_function
        self.n_replications = n_replications
        self.replication_results: List[Dict[str, Any]] = []
        self.summary_statistics: Dict[str, Dict[str, float]] = {}
    
    def run_replications(self, base_seed: int = 12345, **simulation_kwargs):
        """
        Run multiple simulation replications with different random seeds.
        
        Args:
            base_seed: Base seed for reproducibility
            **simulation_kwargs: Additional arguments to pass to simulation function
        """
        print(f"EXECUTANDO {self.n_replications} REPLICACOES...")
        print("=" * 50)
        
        start_time = time.time()
        
        for replication in range(self.n_replications):
            # Set unique seed for each replication
            replication_seed = base_seed + replication * 1000
            
            print(f"Replicacao {replication + 1}/{self.n_replications} (seed: {replication_seed})")
            
            # Run simulation
            model = self.simulation_function(seed=replication_seed, **simulation_kwargs)
            
            # Extract KPIs from this replication
            kpis = self._extract_kpis(model, replication)
            self.replication_results.append(kpis)
            
            # Progress indicator
            if (replication + 1) % 5 == 0 or replication + 1 == self.n_replications:
                elapsed = time.time() - start_time
                avg_time = elapsed / (replication + 1)
                remaining = (self.n_replications - replication - 1) * avg_time
                print(f"  Progresso: {replication + 1}/{self.n_replications} | "
                      f"Tempo restante estimado: {remaining/60:.1f} min")
        
        total_time = time.time() - start_time
        print(f"\nREPLICACOES CONCLUIDAS em {total_time/60:.1f} minutos")
        print(f"Tempo medio por replicacao: {total_time/self.n_replications:.1f} segundos")
        
        # Calculate summary statistics
        self._calculate_summary_statistics()
        
        # Print results
        self.print_statistical_summary()
        
        # Plot confidence intervals
        self.plot_confidence_intervals()
        
        # Export results
        self.export_results()
    
    def _extract_kpis(self, model, replication_id: int) -> Dict[str, Any]:
        """
        Extract key performance indicators from a simulation model.
        
        Args:
            model: Completed simulation model instance
            replication_id: Replication number (for tracking)
            
        Returns:
            Dictionary of KPIs for this replication
        """
        # # Import here to avoid circular dependencies
        # from analytics.metrics import MetricsCollector
        # from analytics.financial import FinancialAnalyzer  # NEW
        # from analytics.wip_metrics import WIPTracker  # NEW
        
        metrics_collector = MetricsCollector(model)
        financial_analyzer = FinancialAnalyzer(model)  # NEW
        wip_tracker = WIPTracker(model)  # NEW
        
        kpis = {
            'replication_id': replication_id,
            'simulation_time': model.env.now,
            'warm_up_period': model.warm_up_period,
            'entities_processed': model.entity_count,
            'overall_throughput': model.overall_throughput
        }
        
        # Entity metrics
        entity_summary = metrics_collector.get_entity_metrics_summary()
        system_time = entity_summary.get('tempo_medio_sistema', 0)
        kpis['system_time_avg'] = 0 if (system_time is None or math.isnan(system_time)) else system_time
        
        
        # NEW: WIP metrics
        wip_summary = wip_tracker.get_wip_summary()
        kpis['average_wip'] = wip_summary['average_wip']
        kpis['max_wip'] = wip_summary['max_wip']
        kpis['final_wip'] = wip_summary['final_wip']
        
        # NEW: System time metrics
        system_time_summary = wip_tracker.get_system_time_summary()
        kpis['system_time_avg_detailed'] = system_time_summary['average_system_time']
        kpis['system_time_std'] = system_time_summary['std_system_time']
        kpis['system_time_min'] = system_time_summary['min_system_time']
        kpis['system_time_max'] = system_time_summary['max_system_time']

        
        # Activity metrics - Handle None and nan values
        activities = entity_summary.get('atividades', {})
        for activity_name, activity_metrics in activities.items():
            queue_time = activity_metrics.get('tempo_medio_fila', 0) or 0
            service_time = activity_metrics.get('tempo_medio_atendimento', 0) or 0
            activity_system_time = activity_metrics.get('tempo_medio_sistema', 0) or 0
            
            # Replace nan with 0
            kpis[f'{activity_name}_queue_time'] = 0 if math.isnan(queue_time) else queue_time
            kpis[f'{activity_name}_service_time'] = 0 if math.isnan(service_time) else service_time
            kpis[f'{activity_name}_system_time'] = 0 if math.isnan(activity_system_time) else activity_system_time
        
        # Resource metrics
        resource_summary = metrics_collector.get_resource_metrics_summary()
        for resource_name, resource_metrics in resource_summary.items():
            kpis[f'{resource_name}_utilization'] = resource_metrics['taxa_utilizacao']
            kpis[f'{resource_name}_avg_queue'] = resource_metrics['numero_medio_fila']
            kpis[f'{resource_name}_avg_in_service'] = resource_metrics['numero_medio_atendimento']
            kpis[f'{resource_name}_max_queue'] = resource_metrics['maximo_fila']
        
        # Decision routing metrics (if applicable)
        for block_name, block in model.blocks.items():
            if hasattr(block, 'decision_counts'):
                total_decisions = sum(block.decision_counts.values())
                for route_name, count in block.decision_counts.items():
                    percentage = (count / total_decisions * 100) if total_decisions > 0 else 0
                    kpis[f'{block_name}_{route_name}_percentage'] = percentage
        

        # NEW: Add financial metrics
        financial_summary = financial_analyzer.get_financial_summary()
        kpis['total_revenue'] = financial_summary['total_revenue']
        kpis['total_costs'] = financial_summary['total_costs']
        kpis['net_profit'] = financial_summary['net_profit']
        kpis['avg_revenue_per_entity'] = financial_summary['avg_revenue_per_entity']
        kpis['avg_cost_per_entity'] = financial_summary['avg_cost_per_entity']
        kpis['avg_profit_per_entity'] = financial_summary['avg_profit_per_entity']
        
        # Add costs by activity
        for activity, cost in financial_summary['costs_by_activity'].items():
            kpis[f'{activity}_total_cost'] = cost
        
        return kpis
    
    def _calculate_summary_statistics(self):
        """
        Calculate summary statistics with 95% confidence intervals.
        
        Uses t-distribution for confidence intervals to account for
        finite sample size and unknown population variance.
        """
        if not self.replication_results:
            print("Nenhum resultado de replicacao disponivel!")
            return
        
        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame(self.replication_results)
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        
        self.summary_statistics = {}
        
        for column in numeric_columns:
            if column in ['replication_id', 'simulation_time', 'warm_up_period']:
                continue
            
            values = df[column].values
            valid_values = values[~np.isnan(values)]
            n = len(valid_values)
            
            if n == 0:
                self.summary_statistics[column] = {
                    'mean': np.nan,
                    'std': np.nan,
                    'sem': np.nan,
                    'ci_lower': np.nan,
                    'ci_upper': np.nan,
                    'half_width': np.nan,
                    'relative_precision': np.nan,
                    'n_replications': 0,
                    'min': np.nan,
                    'max': np.nan
                }
                continue
            
            mean = np.mean(valid_values)
            min_val = np.min(valid_values)
            max_val = np.max(valid_values)
            
            if n > 1:
                std = np.std(valid_values, ddof=1)  # Sample standard deviation
                sem = std / np.sqrt(n)  # Standard error of the mean
                
                # 95% Confidence Interval using t-distribution
                confidence_level = 0.95
                alpha = 1 - confidence_level
                t_critical = stats.t.ppf(1 - alpha/2, df=n-1)
                
                half_width = t_critical * sem
                ci_lower = mean - half_width
                ci_upper = mean + half_width
                
                # Relative precision (half-width of CI as percentage of mean)
                relative_precision = (half_width / abs(mean) * 100) if mean != 0 else 0
            else:
                std = np.nan
                sem = np.nan
                ci_lower = np.nan
                ci_upper = np.nan
                half_width = np.nan
                relative_precision = np.nan
            
            self.summary_statistics[column] = {
                'mean': mean,
                'std': std,
                'sem': sem,
                'ci_lower': ci_lower,
                'ci_upper': ci_upper,
                'half_width': half_width,
                'relative_precision': relative_precision,
                'n_replications': n,
                'min': min_val,
                'max': max_val
            }
    
    def print_statistical_summary(self):
        """Print comprehensive statistical summary with confidence intervals."""
        if not self.summary_statistics:
            print("Estatisticas nao calculadas. Execute run_replications() primeiro.")
            return
        
        print("=" * 80)
        print(f"RESULTADOS ESTATISTICOS ({self.n_replications} REPLICACOES)")
        print("=" * 80)
        
        # System-level metrics
        self._print_section_metrics(
            title="METRICAS DO SISTEMA",
            metrics=[
                ('system_time_avg', 'Tempo medio no sistema'),
                ('entities_processed', 'Entidades processadas'),
                ('overall_throughput', 'Throughput (entidades/min)')
            ]
        )
        
        # Activity metrics
        activity_metrics = [k for k in self.summary_statistics.keys()
                          if any(suffix in k for suffix in ['_queue_time', '_service_time', '_system_time'])]
        
        if activity_metrics:
            print("\nMETRICAS DAS ATIVIDADES:")
            print("-" * 40)
            for metric_key in sorted(activity_metrics):
                stats_data = self.summary_statistics[metric_key]
                metric_name = metric_key.replace('_', ' ').title()
                self._print_metric_statistics(metric_name, stats_data)
        
        # Resource utilization metrics
        utilization_metrics = [k for k in self.summary_statistics.keys()
                             if '_utilization' in k]
        
        if utilization_metrics:
            print("\nUTILIZACAO DE RECURSOS:")
            print("-" * 40)
            for metric_key in sorted(utilization_metrics):
                stats_data = self.summary_statistics[metric_key]
                resource_name = metric_key.replace('_utilization', '')
                metric_name = f"Taxa de utilizacao - {resource_name}"
                # Convert to percentage for display
                stats_pct = self._convert_to_percentage(stats_data)
                self._print_metric_statistics(metric_name, stats_pct, unit='%')
        
        # Precision analysis
        self._print_precision_analysis()
        
        print(f"\nNumero de replicacoes: {self.n_replications}")
        print(f"Nivel de confianca: 95%")
        print(f"Recomendacao: {self._get_replication_recommendation()}")
    
    def _print_section_metrics(self, title: str, metrics: List[tuple]):
        """Print a section of metrics."""
        print(f"\n{title}:")
        print("-" * 40)
        for metric_key, metric_name in metrics:
            if metric_key in self.summary_statistics:
                stats_data = self.summary_statistics[metric_key]
                self._print_metric_statistics(metric_name, stats_data)
    
    def _convert_to_percentage(self, stats_data: Dict) -> Dict:
        """Convert statistics to percentage scale."""
        stats_pct = stats_data.copy()
        for key in ['mean', 'ci_lower', 'ci_upper', 'std', 'min', 'max', 'half_width']:
            if key in stats_pct and not np.isnan(stats_pct[key]):
                stats_pct[key] = stats_pct[key] * 100
        return stats_pct
    
    def _print_metric_statistics(self, metric_name: str, stats_data: Dict, unit: str = ""):
        """Print statistics for a single metric, handling NaN."""
        def format_val(val):
            return f"{val:.2f}" if not np.isnan(val) else "N/A"
        
        mean = stats_data['mean']
        half_width = stats_data['half_width']
        ci_lower = stats_data['ci_lower']
        ci_upper = stats_data['ci_upper']
        precision = stats_data['relative_precision']
        std = stats_data['std']
        min_val = stats_data['min']
        max_val = stats_data['max']
        
        print(f"{metric_name}:")
        print(f"  Media: {format_val(mean)}{unit} +/- {format_val(half_width)}")
        print(f"  IC 95%: [{format_val(ci_lower)}, {format_val(ci_upper)}]{unit}")
        print(f"  Precisao: +/-{format_val(precision)}%")
        print(f"  Desvio padrao: {format_val(std)}")
        print(f"  Min-Max: [{format_val(min_val)}, {format_val(max_val)}]{unit}")
        print()
    
    def _print_precision_analysis(self):
        """Print precision analysis summary."""
        print("\nANALISE DE PRECISAO:")
        print("-" * 40)
        
        high_precision = []
        medium_precision = []
        low_precision = []
        
        for metric_key, stats_data in self.summary_statistics.items():
            if metric_key in ['replication_id']:
                continue
            precision = stats_data['relative_precision']
            if np.isnan(precision):
                continue
            
            if precision <= 5:
                high_precision.append((metric_key, precision))
            elif precision <= 10:
                medium_precision.append((metric_key, precision))
            else:
                low_precision.append((metric_key, precision))
        
        print(f"Alta precisao (<=5%): {len(high_precision)} metricas")
        print(f"Media precisao (5-10%): {len(medium_precision)} metricas")
        print(f"Baixa precisao (>10%): {len(low_precision)} metricas")
        
        if low_precision:
            print("\nMetricas com baixa precisao (considere mais replicacoes):")
            for metric, precision in sorted(low_precision, key=lambda x: x[1], reverse=True):
                print(f"  {metric}: {precision:.1f}%")
    
    def _get_replication_recommendation(self) -> str:
        """Provide recommendation for number of replications."""
        if not self.summary_statistics:
            return "Execute analise estatistica primeiro"
        
        valid_precisions = [stats_data['relative_precision']
                           for stats_data in self.summary_statistics.values()
                           if not np.isnan(stats_data['relative_precision'])]
        
        if not valid_precisions:
            return "Dados insuficientes para recomendacao"
        
        avg_precision = np.mean(valid_precisions)
        
        if avg_precision <= 5:
            return "Precisao excelente - numero adequado de replicacoes"
        elif avg_precision <= 10:
            return "Precisao boa - considere mais replicacoes para metricas criticas"
        elif avg_precision <= 20:
            return "Precisao moderada - recomenda-se dobrar o numero de replicacoes"
        else:
            return "Precisao baixa - aumente significativamente o numero de replicacoes"
    
    def plot_confidence_intervals(self, metrics_to_plot: Optional[List[str]] = None):
        """
        Plot confidence intervals for resource utilization metrics.
        
        Args:
            metrics_to_plot: List of specific metrics to plot (None = all utilization metrics)
        """
        if not self.summary_statistics:
            print("Estatisticas nao calculadas.")
            return
        
        # Get only resource utilization metrics
        utilization_metrics = [k for k in self.summary_statistics.keys()
                            if '_utilization' in k]
        
        if not utilization_metrics:
            print("Nenhuma metrica de utilizacao de recursos encontrada.")
            return
        
        # Filter available metrics
        available_metrics = [m for m in utilization_metrics if m in self.summary_statistics]
        
        if not available_metrics:
            print("Nenhuma metrica de utilizacao disponivel para plotar.")
            return
        
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 6))
        
        y_pos = np.arange(len(available_metrics))
        means = []
        half_widths = []
        labels = []
        
        # Define color palette
        colors = plt.cm.Set3(np.linspace(0, 1, len(available_metrics)))
        
        for metric in available_metrics:
            stats_data = self.summary_statistics[metric]
            
            # Convert to percentages
            mean_pct = stats_data['mean'] * 100
            half_width_pct = stats_data['half_width'] * 100
            
            means.append(mean_pct)
            half_widths.append(half_width_pct)
            
            # Clean up label - extract resource name
            resource_name = metric.replace('_utilization', '').replace('_', ' ').title()
            labels.append(resource_name)
        
        # Create horizontal bar plot
        ax.barh(y_pos, means, xerr=half_widths, capsize=8,
               color=colors, edgecolor='black', linewidth=1, alpha=0.8)
        
        # Add value labels on bars
        for i, (mean, half_width) in enumerate(zip(means, half_widths)):
            label_text = f'{mean:.1f}% +/- {half_width:.1f}%'
            
            # Position label inside or outside bar based on bar width
            if mean > 15:
                ax.text(mean/2, i, label_text,
                       ha='center', va='center', fontweight='bold',
                       fontsize=9, color='black')
            else:
                ax.text(mean + half_width + 2, i, label_text,
                       ha='left', va='center', fontweight='bold',
                       fontsize=9, color='black')
        
        # Customize the plot
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=11)
        ax.set_xlabel('Taxa de Utilizacao (%)', fontsize=12, fontweight='bold')
        ax.set_title(f'Utilizacao de Recursos - Intervalos de Confianca 95%\n'
                    f'({self.n_replications} replicacoes)',
                    fontsize=14, fontweight='bold', pad=20)
        
        # Set x-axis from 0% to 100%
        ax.set_xlim(0, 100)
        
        # Add reference lines
        ax.axvline(x=85, color='red', linestyle='--', alpha=0.7, linewidth=1,
                  label='85% (Limite Critico)')
        ax.axvline(x=70, color='orange', linestyle='--', alpha=0.5, linewidth=1,
                  label='70% (Alta Utilizacao)')
        ax.axvline(x=50, color='green', linestyle='--', alpha=0.5, linewidth=1,
                  label='50% (Utilizacao Moderada)')
        ax.axvline(x=25, color='blue', linestyle='--', alpha=0.3, linewidth=1,
                  label='25% (Baixa Utilizacao)')
        
        # Add grid
        ax.grid(axis='x', alpha=0.3, linestyle='-')
        ax.set_axisbelow(True)
        
        # Add legend
        ax.legend(loc='lower right', framealpha=0.9, fontsize=9)
        
        plt.tight_layout()
        plt.show()
        
        # Print detailed resource analysis
        self._print_resource_analysis(available_metrics)
    
    def _print_resource_analysis(self, metrics: List[str]):
        """Print detailed resource utilization analysis."""
        print("\nANALISE DETALHADA DA UTILIZACAO DE RECURSOS:")
        print("=" * 55)
        
        for metric in metrics:
            stats_data = self.summary_statistics[metric]
            mean_util = stats_data['mean'] * 100
            half_width = stats_data['half_width'] * 100
            ci_lower = stats_data['ci_lower'] * 100
            ci_upper = stats_data['ci_upper'] * 100
            precision = stats_data['relative_precision']
            
            resource_name = metric.replace('_utilization', '').replace('_', ' ').title()
            
            print(f"\n{resource_name}:")
            print(f"  Utilizacao media: {mean_util:.1f}% +/- {half_width:.1f}%")
            print(f"  IC 95%: [{ci_lower:.1f}%, {ci_upper:.1f}%]")
            print(f"  Precisao relativa: +/-{precision:.1f}%")
            
            # Recommendations based on utilization level
            if mean_util >= 90:
                print("  RECOMENDACAO: Recurso extremamente sobrecarregado!")
                print("     Aumentar capacidade urgentemente")
            elif mean_util >= 85:
                print("  RECOMENDACAO: Recurso sobrecarregado")
                print("     Considerar aumentar capacidade")
            elif mean_util >= 70:
                print("  RECOMENDACAO: Utilizacao alta")
                print("     Monitorar e avaliar necessidade de recursos adicionais")
            elif mean_util >= 50:
                print("  RECOMENDACAO: Utilizacao moderada e eficiente")
                print("     Nivel ideal para maioria dos sistemas")
            elif mean_util >= 25:
                print("  RECOMENDACAO: Utilizacao abaixo do ideal")
                print("     Avaliar redimensionamento ou redistribuicao")
            else:
                print("  RECOMENDACAO: Recurso subutilizado")
                print("     Considerar reducao de capacidade")
    
    def get_results_dataframe(self) -> pd.DataFrame:
        """
        Return results as a pandas DataFrame for further analysis.
        
        Returns:
            DataFrame with one row per replication
        """
        df = pd.DataFrame(self.replication_results)
        # print(df.columns)
        df.drop(['replication_id', 'simulation_time',
        'warm_up_period', 'overall_throughput'], axis=1, inplace=True)
        # return pd.DataFrame(self.replication_results)
        return df
    
    def export_results(self, filename: str = "framework_results.csv"):
        """
        Export results to CSV file.
        
        Args:
            filename: Output CSV filename
        """
        df = self.get_results_dataframe()
        df.to_csv(filename, index=False)
        print(f"Resultados exportados para {filename}")



# =====================================================================
# FILE: statistics/factorial.py
# =====================================================================
@dataclass
class FactorLevel:
    """
    Represents a factor and its levels for factorial analysis.
    
    Attributes:
        factor_name: Short name for the factor (e.g., 'arrival_rate')
        parameter_path: Path to parameter in model (for documentation)
        levels: List of values to test for this factor
        description: Human-readable description of the factor
    """
    factor_name: str
    parameter_path: str
    levels: List[Any]
    description: str = ""


class FactorialExperiment:
    """
    Framework for conducting factorial experiments on simulation models.
    
    This class implements a full factorial design where all combinations
    of factor levels are tested with multiple replications.
    """
    
    def __init__(self, simulation_function: Callable, base_seed: int = 12345):
        """
        Initialize factorial experiment framework.
        
        Args:
            simulation_function: Function that creates and runs simulation model.
                                Must accept factor parameters as kwargs and return model.
            base_seed: Base random seed for reproducibility
        """
        self.simulation_function = simulation_function
        self.base_seed = base_seed
        self.factors: List[FactorLevel] = []
        self.results: List[Dict[str, Any]] = []
        self.results_df: Optional[pd.DataFrame] = None
    
    def add_factor(self, factor_name: str, parameter_path: str,
                   levels: List[Any], description: str = ""):
        """
        Add a factor to the experimental design.
        
        Args:
            factor_name: Name of the factor (e.g., "arrival_rate")
            parameter_path: Path to parameter in model (for documentation)
            levels: List of values to test
            description: Human-readable description
        """
        factor = FactorLevel(
            factor_name=factor_name,
            parameter_path=parameter_path,
            levels=levels,
            description=description
        )
        self.factors.append(factor)
        print(f"Fator adicionado: {factor_name} ({len(levels)} niveis)")
    
    def run_factorial_experiment(self, n_replications: int = 1,
                                 simulation_time: Optional[float] = None,
                                 warm_up_period: float = 0.0,
                                 verbose: bool = True):
        """
        Run full factorial experiment with all combinations of factor levels.
        
        Args:
            n_replications: Number of replications per combination
            simulation_time: Duration of each simulation run
            warm_up_period: Warm-up period for statistics collection
            verbose: Print progress messages
        """
        if not self.factors:
            print("Nenhum fator definido! Use add_factor() primeiro.")
            return
        
        # Generate all combinations
        factor_levels = [factor.levels for factor in self.factors]
        combinations = list(itertools.product(*factor_levels))
        total_runs = len(combinations) * n_replications
        
        self._print_experiment_header(combinations, n_replications, total_runs)
        
        self.results = []
        start_time = time.time()
        run_count = 0
        
        # Run all combinations
        for combo_idx, combination in enumerate(combinations):
            # Create factor configuration
            config = {
                self.factors[i].factor_name: combination[i]
                for i in range(len(self.factors))
            }
            
            if verbose:
                print(f"\nConfiguracao {combo_idx + 1}/{len(combinations)}: {config}")
            
            # Run replications for this combination
            for rep in range(n_replications):
                run_count += 1
                seed = self.base_seed + combo_idx * 1000 + rep
                
                if verbose and n_replications > 1:
                    print(f"  Replicacao {rep + 1}/{n_replications} (seed: {seed})")
                
                try:
                    # Run simulation with current configuration
                    model = self._run_simulation_with_config(
                        config, seed, simulation_time, warm_up_period
                    )
                    
                    # Extract results
                    result = self._extract_results(model, config, combo_idx, rep)
                    self.results.append(result)
                    
                    if verbose and run_count % 10 == 0:
                        self._print_progress(start_time, run_count, total_runs)
                
                except Exception as e:
                    print(f"  Erro na execucao: {e}")
                    continue
        
        self._print_completion_summary(start_time, total_runs)
        
        # Convert to DataFrame
        self.results_df = pd.DataFrame(self.results)
        print(f"{len(self.results)} resultados coletados")
    
    def _print_experiment_header(self, combinations: List, n_replications: int,
                                 total_runs: int):
        """Print experiment setup information."""
        print("\nEXPERIMENTO FATORIAL")
        print("=" * 60)
        print(f"Fatores: {len(self.factors)}")
        for factor in self.factors:
            print(f"  - {factor.factor_name}: {len(factor.levels)} niveis")
        print(f"Combinacoes: {len(combinations)}")
        print(f"Replicacoes por combinacao: {n_replications}")
        print(f"Total de execucoes: {total_runs}")
        print("=" * 60)
    
    def _print_progress(self, start_time: float, run_count: int, total_runs: int):
        """Print progress update."""
        elapsed = time.time() - start_time
        avg_time = elapsed / run_count
        remaining = (total_runs - run_count) * avg_time
        print(f"  Progresso: {run_count}/{total_runs} | "
              f"Tempo restante: {remaining/60:.1f} min")
    
    def _print_completion_summary(self, start_time: float, total_runs: int):
        """Print experiment completion summary."""
        total_time = time.time() - start_time
        print(f"\nEXPERIMENTO CONCLUIDO em {total_time/60:.1f} minutos")
        print(f"Tempo medio por execucao: {total_time/total_runs:.1f} segundos")
    
    def _run_simulation_with_config(self, config: Dict, seed: int,
                                     simulation_time: Optional[float],
                                     warm_up_period: float):
        """Run simulation with specific factor configuration."""
        # Build kwargs from configuration
        kwargs = {
            'seed': seed,
            'return_model': True
        }
        
        if simulation_time is not None:
            kwargs['until'] = simulation_time
        if warm_up_period > 0:
            kwargs['warm_up_period'] = warm_up_period
        
        # Add factor values to kwargs
        kwargs.update(config)
        
        # Run simulation
        model = self.simulation_function(**kwargs)
        return model
    
    def _extract_results(self, model, config: Dict, combo_idx: int,
                         rep: int) -> Dict[str, Any]:
        """
        Extract KPIs from simulation model.
        
        Args:
            model: Completed simulation model
            config: Factor configuration for this run
            combo_idx: Combination index
            rep: Replication number
            
        Returns:
            Dictionary of results including factors and KPIs
        """
        # Import here to avoid circular dependencies
        # from analytics.metrics import MetricsCollector
        
        metrics_collector = MetricsCollector(model)
        
        result = {
            'combination_id': combo_idx,
            'replication': rep,
            **config  # Include factor values
        }
        
        # System-level metrics
        result['simulation_time'] = model.env.now
        result['warm_up_period'] = model.warm_up_period
        result['entities_processed'] = model.entity_count
        result['throughput'] = model.overall_throughput
        
        # Entity metrics
        entity_summary = metrics_collector.get_entity_metrics_summary()
        result['system_time_avg'] = entity_summary.get('tempo_medio_sistema', 0)
        
        # Activity metrics
        for activity_name, metrics in entity_summary.get('atividades', {}).items():
            result[f'{activity_name}_queue_time'] = metrics.get('tempo_medio_fila', 0)
            result[f'{activity_name}_service_time'] = metrics.get('tempo_medio_atendimento', 0)
        
        # Resource metrics
        resource_summary = metrics_collector.get_resource_metrics_summary()
        for resource_name, metrics in resource_summary.items():
            result[f'{resource_name}_utilization'] = metrics['taxa_utilizacao']
            result[f'{resource_name}_avg_queue'] = metrics['numero_medio_fila']
            result[f'{resource_name}_max_queue'] = metrics['maximo_fila']
        
        return result
    
    def get_aggregated_results(self) -> Optional[pd.DataFrame]:
        """
        Aggregate results by factor combination (average over replications).
        
        Returns:
            DataFrame with mean and std for each metric by factor combination
        """
        if self.results_df is None:
            print("Execute o experimento primeiro!")
            return None
        
        # Group by factor values
        factor_names = [f.factor_name for f in self.factors]
        
        # Aggregate numeric columns
        numeric_cols = self.results_df.select_dtypes(include=[np.number]).columns
        exclude_cols = ['combination_id', 'replication', 'simulation_time', 'warm_up_period']
        agg_cols = [col for col in numeric_cols if col not in exclude_cols]
        
        aggregated = self.results_df.groupby(factor_names)[agg_cols].agg(
            ['mean', 'std']
        ).reset_index()
        
        return aggregated
    
    def plot_correlation_matrix(self):
        """Plot correlation matrix of key metrics with compact legend."""
        if self.results_df is None:
            print("Execute o experimento primeiro!")
            return
        
        # Filter columns and create labels
        selected_cols, col_labels = self._prepare_correlation_data()
        
        if not selected_cols:
            print("Nenhuma coluna relevante encontrada!")
            return
        
        # Calculate correlation
        filtered_df = self.results_df[selected_cols]
        corr_matrix = filtered_df.corr()
        
        # Create short labels
        short_labels = [col_labels[col] for col in filtered_df.columns]
        
        # Plot
        fig, ax = plt.subplots(figsize=(16, 10))
        
        sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='coolwarm',
                   center=0, square=True, linewidths=0.5,
                   xticklabels=short_labels, yticklabels=short_labels,
                   ax=ax, cbar_kws={'label': 'Correlacao'})
        
        ax.set_title('Matriz de Correlacao (Metricas Principais)',
                    fontsize=14, fontweight='bold', pad=15)
        
        # Create and position legend
        legend_text = self._create_correlation_legend(filtered_df, col_labels)
        fig.text(0.75, 0.5, legend_text,
                fontsize=9,
                verticalalignment='center',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.9, pad=0.8),
                family='monospace')
        
        plt.subplots_adjust(left=0.1, right=0.75)
        plt.show()
        
        print(f"\nMatriz de correlacao gerada com {len(selected_cols)} variaveis")
        
        return corr_matrix
    
    def _prepare_correlation_data(self) -> Tuple[List[str], Dict[str, str]]:
        """Prepare data for correlation matrix."""
        selected_cols = []
        col_labels = {}
        label_counter = 1
        
        factor_names = [f.factor_name for f in self.factors]
        
        # Add factor columns
        for col in self.results_df.columns:
            if any(col.startswith(fname) for fname in factor_names):
                selected_cols.append(col)
                col_labels[col] = f"F{label_counter}"
                label_counter += 1
        
        # Add activity metrics
        metric_counter = 1
        for col in self.results_df.columns:
            if 'queue_time' in col or 'service_time' in col:
                selected_cols.append(col)
                label = f"Q{metric_counter}" if 'queue_time' in col else f"S{metric_counter}"
                col_labels[col] = label
                metric_counter += 1
        
        # Add resource utilization
        util_counter = 1
        for col in self.results_df.columns:
            if '_utilization' in col:
                selected_cols.append(col)
                col_labels[col] = f"U{util_counter}"
                util_counter += 1
        
        return selected_cols, col_labels
    
    def _create_correlation_legend(self, filtered_df: pd.DataFrame,
                                   col_labels: Dict[str, str]) -> str:
        """Create legend text for correlation plot."""
        factor_names = [f.factor_name for f in self.factors]
        legend_lines = ["LEGENDA:", "", "Fatores:"]
        
        for col in filtered_df.columns:
            if any(col.startswith(fname) for fname in factor_names):
                legend_lines.append(f"  {col_labels[col]}: {col}")
        
        legend_lines.append("")
        legend_lines.append("Atividades:")
        for col in filtered_df.columns:
            if 'queue_time' in col or 'service_time' in col:
                short_name = col.replace('_queue_time', '').replace('_service_time', '')
                metric_type = 'Fila' if 'queue' in col else 'Atend'
                legend_lines.append(f"  {col_labels[col]}: {short_name} ({metric_type})")
        
        legend_lines.append("")
        legend_lines.append("Recursos:")
        for col in filtered_df.columns:
            if '_utilization' in col:
                resource_name = col.replace('_utilization', '')
                legend_lines.append(f"  {col_labels[col]}: {resource_name} (Util)")
        
        return "\n".join(legend_lines)
    
    def plot_main_effects(self, response_variable: str):
        """
        Plot main effects for each factor on a response variable.
        
        Args:
            response_variable: Name of the response variable to plot
        """
        if self.results_df is None:
            print("Execute o experimento primeiro!")
            return
        
        if response_variable not in self.results_df.columns:
            print(f"Variavel '{response_variable}' nao encontrada!")
            return
        
        n_factors = len(self.factors)
        fig, axes = plt.subplots(1, n_factors, figsize=(5*n_factors, 4))
        if n_factors == 1:
            axes = [axes]
        
        for idx, factor in enumerate(self.factors):
            ax = axes[idx]
            
            # Group by factor level and calculate mean response
            grouped = self.results_df.groupby(factor.factor_name)[response_variable].agg(
                ['mean', 'std']
            )
            
            # Plot
            x_pos = range(len(grouped))
            ax.errorbar(x_pos, grouped['mean'], yerr=grouped['std'],
                       marker='o', markersize=8, capsize=5, linewidth=2)
            
            ax.set_xlabel(factor.factor_name, fontsize=11, fontweight='bold')
            ax.set_ylabel(response_variable, fontsize=11, fontweight='bold')
            ax.set_title(f'Efeito de {factor.factor_name}', fontsize=12)
            ax.set_xticks(x_pos)
            ax.set_xticklabels(grouped.index, rotation=45)
            ax.grid(True, alpha=0.3)
        
        plt.suptitle(f'Efeitos Principais em {response_variable}',
                    fontsize=14, fontweight='bold')
        plt.tight_layout()
        plt.show()
    
    def plot_interaction_effects(self, response_variable: str,
                                 factor1_name: str, factor2_name: str):
        """
        Plot interaction effects between two factors.
        
        Args:
            response_variable: Response variable to analyze
            factor1_name: First factor name
            factor2_name: Second factor name
        """
        if self.results_df is None:
            print("Execute o experimento primeiro!")
            return
        
        if response_variable not in self.results_df.columns:
            print(f"Variavel '{response_variable}' nao encontrada!")
            return
        
        # Group by both factors
        grouped = self.results_df.groupby(
            [factor1_name, factor2_name]
        )[response_variable].mean().reset_index()
        
        # Pivot for plotting
        pivot = grouped.pivot(index=factor1_name, columns=factor2_name,
                            values=response_variable)
        
        # Plot
        fig, ax = plt.subplots(figsize=(10, 6))
        
        for col in pivot.columns:
            ax.plot(pivot.index, pivot[col], marker='o', markersize=8,
                   linewidth=2, label=f'{factor2_name}={col}')
        
        ax.set_xlabel(factor1_name, fontsize=12, fontweight='bold')
        ax.set_ylabel(response_variable, fontsize=12, fontweight='bold')
        ax.set_title(f'Interacao entre {factor1_name} e {factor2_name}',
                    fontsize=14, fontweight='bold')
        ax.legend(title=factor2_name, framealpha=0.9)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
    
    def print_summary(self):
        """Print comprehensive summary of factorial analysis."""
        if self.results_df is None:
            print("Execute o experimento primeiro!")
            return
        
        print("\n" + "=" * 70)
        print("RESUMO DA ANALISE FATORIAL")
        print("=" * 70)
        
        self._print_factor_summary()
        self._print_best_worst_configurations()
        self._print_descriptive_statistics()
        self._print_general_analysis()
    
    def _print_factor_summary(self):
        """Print summary of factors tested."""
        print("\nFATORES TESTADOS:")
        for factor in self.factors:
            print(f"  - {factor.factor_name}: {factor.levels}")
            if factor.description:
                print(f"    {factor.description}")
    
    def _print_best_worst_configurations(self):
        """Print best and worst configurations for key metrics."""
        factor_names = [f.factor_name for f in self.factors]
        
        # Find key metrics
        activity_metrics = [col for col in self.results_df.columns
                          if 'queue_time' in col or 'service_time' in col]
        utilization_metrics = [col for col in self.results_df.columns
                             if '_utilization' in col]
        
        sample_metrics = []
        if activity_metrics:
            sample_metrics.append(activity_metrics[0])
        if utilization_metrics:
            sample_metrics.append(utilization_metrics[0])
        
        for metric in sample_metrics[:3]:
            print(f"\n  {metric}:")
            
            # Find best and worst
            if 'time' in metric.lower():
                best_idx = self.results_df[metric].idxmin()
                worst_idx = self.results_df[metric].idxmax()
            elif 'utilization' in metric.lower():
                best_idx = (self.results_df[metric] - 0.75).abs().idxmin()
                worst_idx = self.results_df[metric].idxmax()
            else:
                best_idx = self.results_df[metric].idxmax()
                worst_idx = self.results_df[metric].idxmin()
            
            best_row = self.results_df.loc[best_idx]
            worst_row = self.results_df.loc[worst_idx]
            
            best_config = {fname: best_row[fname] for fname in factor_names}
            worst_config = {fname: worst_row[fname] for fname in factor_names}
            
            best_val = best_row[metric]
            worst_val = worst_row[metric]
            
            if 'utilization' in metric:
                print(f"    Melhor: {best_config} -> {best_val*100:.1f}%")
                print(f"    Pior: {worst_config} -> {worst_val*100:.1f}%")
            else:
                print(f"    Melhor: {best_config} -> {best_val:.2f}")
                print(f"    Pior: {worst_config} -> {worst_val:.2f}")
    
    def _print_descriptive_statistics(self):
        """Print descriptive statistics for key metrics."""
        print("\nESTATISTICAS DESCRITIVAS (Metricas Principais):")
        print("-" * 70)
        
        # Activity times
        print("\nTEMPOS DE ATIVIDADES:")
        activity_cols = [col for col in self.results_df.columns
                        if 'queue_time' in col or 'service_time' in col]
        if activity_cols:
            activity_df = self.results_df[activity_cols]
            print(activity_df.describe().T[['mean', 'std', 'min', 'max']].to_string())
        
        # Resource utilization
        print("\nUTILIZACAO DE RECURSOS:")
        util_cols = [col for col in self.results_df.columns if '_utilization' in col]
        if util_cols:
            util_df = self.results_df[util_cols]
            util_display = util_df.describe().T[['mean', 'std', 'min', 'max']] * 100
            print(util_display.to_string())
            print("(valores em %)")
    
    def _print_general_analysis(self):
        """Print general analysis summary."""
        print("\nANALISE GERAL:")
        n_combinations = len(self.results_df['combination_id'].unique())
        n_reps = len(self.results_df[self.results_df['combination_id']==0])
        print(f"   Total de configuracoes testadas: {n_combinations}")
        print(f"   Replicacoes por configuracao: {n_reps}")
        print(f"   Total de execucoes: {len(self.results_df)}")
    
    def export_results(self, filename: str = "factorial_results.csv",
                      export_filtered: bool = False):
        """
        Export results to CSV.
        
        Args:
            filename: Output filename
            export_filtered: If True, export only key metrics; if False, export all
        """
        if self.results_df is None:
            print("Execute o experimento primeiro!")
            return
        
        if export_filtered:
            export_df = self._get_filtered_results()
            print(f"Resultados FILTRADOS exportados para {filename}")
            print(f"   Colunas exportadas: {len(export_df.columns)}")
        else:
            export_df = self.results_df
            print(f"Resultados COMPLETOS exportados para {filename}")
            print(f"   Colunas exportadas: {len(export_df.columns)}")
        
        export_df.to_csv(filename, index=False)
        print(f"   Total de linhas: {len(export_df)}")
    
    def _get_filtered_results(self) -> pd.DataFrame:
        """Get filtered DataFrame with only key metrics."""
        factor_names = [f.factor_name for f in self.factors]
        key_cols = ['combination_id', 'replication']
        
        # Add factors
        for col in self.results_df.columns:
            if any(col.startswith(fname) for fname in factor_names):
                key_cols.append(col)
        
        # Add activity metrics
        for col in self.results_df.columns:
            if 'queue_time' in col or 'service_time' in col:
                key_cols.append(col)
        
        # Add resource utilization
        for col in self.results_df.columns:
            if '_utilization' in col:
                key_cols.append(col)
        
        return self.results_df[key_cols]


# =====================================================================
# FILE: hospital.py
# =====================================================================
import random
# from stats.replication import ReplicationFramework    
# from analytics.financial import FinancialAnalyzer
# from core.simulation_model import SimulationModel
# from validation.resource_validator import ResourceValidator
# from core.entity import EventLogger
# from blocks.create_block import CreateBlock
# from blocks.process_block import ProcessBlock, MultiProcessBlock
# from blocks.decide_block import DecideBlock
# from blocks.dispose_block import DisposeBlock
# from analytics.metrics import MetricsCollector
# from analytics.reporting import SimulationReporter
# from analytics.plotting import SimulationPlotter
# from validation.stability import StabilityAnalyzer
# from validation.warmup import WarmUpAnalyzer
# from config.simulation_config import SimulationConfig


# ================================================================
# Each ACD model is implemented here
# ================================================================
def build_hospital_model(event_logger=None):
    """Build a hospital simulation model with refactored structure."""
    
    HOURS = 60  # Time conversion factor (base time: minutes)
    DAYS = 1440
    YEARS = 525600
    
    model = SimulationModel()

    # Unidade básica para todos os tempos: minutos
    def distribution(tipo):
        taxa_chegadas=4         # por minuto        
        return {
            'arrival': random.expovariate(1/taxa_chegadas),
            'triage': random.uniform(2, 3),
            'consultation': random.uniform(5, 15),
            'pharmacy': random.expovariate(1/5)
        }.get(tipo,0.0)

    
    # Resources - all priority-based
    nursesT = model.add_resource("nursesT", 2, "priority")
    nurses = model.add_resource("nurses", 3, "priority")
    doctors = model.add_resource("doctors", 4, "priority")
    # pharmacy = model.add_resource("pharmacy", 4, "preemptive")
    pharmacy = model.add_resource("pharmacy", 4, "priority")
    
    # Patient severity generator
    def patient_severity():
        severity_dist = [0.1, 0.2, 0.3, 0.3, 0.1]
        return random.choices([0, 1, 2, 3, 4], weights=severity_dist)[0]
    
    # Create blocks
    arrivals = CreateBlock(
        "Arrivals", model.env,
        # inter_arrival_time=lambda: random.expovariate(1/4),
        inter_arrival_time=lambda: distribution('arrival'),
        entity_prefix="Patient",
        priority_generator=patient_severity,
        event_logger=event_logger
    )
    
    triage = ProcessBlock(
        "Triage", model.env,
        resource=nursesT,
        # delay_time=lambda: random.uniform(2, 5),
        delay_time=lambda: distribution('triage'),
        resource_units=2,         # 1 nurse of triage per service
        event_logger=event_logger
    )
    triage.set_resource_name('nursesT')
    
    consultation = MultiProcessBlock(
        "Consultation", model.env,
        resource_requirements={
            doctors: 1,
            nurses: 1
            # pharmacy: 1
        },
        # delay_time=lambda: random.uniform(5, 15),
        delay_time=lambda: distribution('consultation'),
        event_logger=event_logger
    )
    consultation.set_resource_names({
        doctors: 'doctors',
        nurses: 'nurses'
        # pharmacy: 'pharmacy'
    })
    
    treatment_decision = DecideBlock(
        "Treatment_Decision", model.env,
        decision_type="condition",
        event_logger=event_logger
    )

    moderate_treatment = DecideBlock(
        "Moderate_Treatment", model.env,
        decision_type="probability",
        event_logger=event_logger
    )

    minor_treatment = DecideBlock(
        "Minor_Treatment", model.env,
        decision_type="probability",
        event_logger=event_logger
    )
    
    pharmacy_block = ProcessBlock(
        "Pharmacy", model.env,
        resource=pharmacy,
        # delay_time=lambda: random.expovariate(1/5),
        delay_time=lambda: distribution('pharmacy'),
        resource_units=2,                 # 2 pharmacists per service
        event_logger=event_logger
    )
    pharmacy_block.set_resource_name('pharmacy')
    
    need_medication = DecideBlock(
        "Need_medication", model.env,
        decision_type="probability",
        event_logger=event_logger
    )
    
    discharge = DisposeBlock("Discharge", model.env, event_logger=event_logger)
    
    # Add blocks to model
    for block in [arrivals, triage, consultation, treatment_decision,
                  pharmacy_block, moderate_treatment, minor_treatment, 
                  need_medication, discharge]:
        model.add_block(block)
    
    
    # Connect flow
    arrivals.connect_to(triage)
    triage.connect_to(treatment_decision)

    # Decision routing functions
    def needs_intensive_treatment(entity):
        return entity.priority <= 1
    
    def needs_moderate_treatment(entity):
        return entity.priority == 2 # and random.random() < 0.80
    
    def needs_minor_treatment(entity):
        return entity.priority == 3 # and random.random() < 0.90
    
    def needs_only_medication(entity):
        return not (needs_intensive_treatment(entity) or
                   needs_moderate_treatment(entity) or
                   needs_minor_treatment(entity))
    
    # Add decision routes
    treatment_decision.add_route("Critical_Emergency", consultation,
                                condition=needs_intensive_treatment)
    treatment_decision.add_route("Urgent", moderate_treatment,
                                condition=needs_moderate_treatment)
    treatment_decision.add_route("Semi_Urgent", minor_treatment,
                                condition=needs_minor_treatment)
    treatment_decision.add_route("Non_Urgent", pharmacy_block,
                                condition=needs_only_medication)
    
    moderate_treatment.add_route("Urgent", consultation, probability=0.8)
    # Importante! Para contabilizar as saídas e o WIP
    moderate_treatment.add_route("No_Consult", discharge, probability=0.2)

    minor_treatment.add_route("Semi_Urgent", consultation, probability=0.9)
    # Importante! Para contabilizar as saídas e o WIP
    minor_treatment.add_route("No_Consult", discharge, probability=0.1)

    consultation.connect_to(need_medication)

    need_medication.add_route("Needs_Medication", pharmacy_block, probability=0.9)
    need_medication.add_route("Direct_Discharge", discharge, probability=0.1)
    
    pharmacy_block.connect_to(discharge)

    # ================================================================
    # CONFIGURE FINANCIAL ATTRIBUTES
    # ================================================================    
    # Assign costs to each activity
    triage.assign_attributes(
        cost=lambda: random.uniform(20, 30)  # Triage costs $20-30
    )
    
    consultation.assign_attributes(
        cost=lambda: random.uniform(100, 200)  # Consultation costs $100-200
    )
    
    pharmacy_block.assign_attributes(
        cost=lambda: random.uniform(15, 50)  # Medication costs $15-50
    )
    
    # Assign revenue at discharge (based on patient complexity)
    def calculate_revenue():
        """Revenue varies by patient complexity"""
        return random.uniform(200, 300)
    
    discharge.assign_attributes(revenue=calculate_revenue)    
    # ================================================================
    
    return model



# ================================================================
# For full simulation
# ================================================================
def simulation_wrapper(seed=None, until=None, warm_up_period=None):
    """Wrapper function for replication framework."""
    
    # from core.entity import EventLogger
    
    event_logger = EventLogger()
    model = build_hospital_model(event_logger)

    # Validate once on first run
    if seed == 12345:
        model.validate_resources()
    
    # model.run_simulation(
    #     until=until or 24*60,
    #     seed=seed,
    #     warm_up_period=warm_up_period or 2*60
    # )
    model.run_simulation(
        validate_resources=False,
        until=until,
        seed=seed,
        warm_up_period=warm_up_period
    )
    
    return model

# Run replications
def run_replications():
    replication_framework = ReplicationFramework(
        simulation_function=simulation_wrapper,
        n_replications=30
    )
    
    replication_framework.run_replications(
        base_seed=12345,
        until=24*60,
        warm_up_period=2*60
    )

    # Access results
    df = replication_framework.get_results_dataframe()
    print(df.describe())
# ================================================================
    

# ================================================================
# Factorial Analysis
# ================================================================
def hospital_factorial_analysis():
    """Example of factorial analysis with hospital simulation."""
    
    # Define simulation function wrapper
    def hospital_simulation_wrapper(arrival_rate=4, num_doctors=4, num_nurses=3,
                                    seed=None, until=None, warm_up_period=0, **kwargs):
        """Wrapper that adapts parameters for factorial analysis."""

        # ############################################################
        # # O modelo de simulação é importado aqui
        # ############################################################
        # from hospital import build_hospital_model()
        
        # This would need to be modified in your actual model to accept these parameters
        # For now, this is a template showing how to structure it
        model = build_hospital_model()
        model.run_simulation(until=until, seed=seed, warm_up_period=warm_up_period)
        return model
    
    # Create factorial analysis
    factorial = FactorialExperiment(
        simulation_function=hospital_simulation_wrapper,
        base_seed=12345
    )
    
    # Add factors
    factorial.add_factor(
        factor_name='arrival_rate',
        parameter_path='CreateBlock.inter_arrival_time',
        levels=[3, 4, 5],  # Minutes between arrivals
        description='Taxa de chegada de pacientes (min)'
    )
    
    factorial.add_factor(
        factor_name='num_doctors',
        parameter_path='Resource.doctors.capacity',
        levels=[3, 4, 5],
        description='Número de médicos'
    )
    
    factorial.add_factor(
        factor_name='num_nurses',
        parameter_path='Resource.nurses.capacity',
        levels=[2, 3, 4],
        description='Número de enfermeiros'
    )
    
    # Run experiment
    factorial.run_factorial_experiment(
        n_replications=5,
        simulation_time=40*60,  # 40 hours
        warm_up_period=7*60,    # 7 hours
        verbose=True
    )
    
    # Analyze results
    factorial.print_summary()
    factorial.plot_correlation_matrix()
    factorial.plot_main_effects('system_time_avg')
    factorial.plot_interaction_effects('system_time_avg', 'arrival_rate', 'num_doctors')
    
    # Export
    factorial.export_results()

    print("\n\nFactorial analysis examples completed!")
    print("Check the generated CSV files and plots for detailed results.")
    
    return factorial
# ================================================================



def main():
    """Main example demonstrating refactored usage."""
    
    HOURS = 60  # Time conversion factor (base time: Minutos)
    DAYS = 1440
    YEARS = 525600
    
    # Create event logger
    event_logger = EventLogger()
    
    # Build model
    print("Building hospital model...")
    model = build_hospital_model(event_logger)
    
    # Create configuration
    config = SimulationConfig(
        # warm_up_period=0
        # until=20
        duration=24*HOURS,
        warm_up_period=2*HOURS,
        # duration=21*DAYS,
        # warm_up_period=5*DAYS,        
        # duration=364*DAYS,
        # warm_up_period=35*DAYS,        
        seed=123,
        check_stability=True
    )
    config.validate()
    
    # Check stability BEFORE running (optional)
    print("\nChecking system stability...")
    stability_analyzer = StabilityAnalyzer(model)
    stability = stability_analyzer.check_system_stability()
    model.stability_result = stability
    
    # Run simulation
    print("\nRunning simulation (replication)...")
    model.run_simulation(
        validate_resources=True,  # Default True
        until=config.duration,
        seed=config.seed,
        warm_up_period=config.warm_up_period
    )
        
    # === ANALYSIS PHASE (using separate modules) ===
    
    # 1. Basic results
    print("\n" + "="*60)
    print("SIMULATION COMPLETE - ANALYZING RESULTS")
    print("="*60)
    
    # 2. Detailed reporting
    reporter = SimulationReporter(model)
    reporter.print_results()
    
    # 3. Warm-up analysis
    print("\nAnalyzing warm-up period...")
    warmup_analyzer = WarmUpAnalyzer(model)
    warmup_analyzer.analyze_warm_up_period()
    
    # 4. Plotting
    print("\nPlotting resourse use over time...")
    plotter = SimulationPlotter(model)
    
    # Plot resource utilization over time
    plotter.plot_resource_use_over_time(show_warm_up=True, resource='nursesT', moving_average_window=50)
    plotter.plot_resource_use_over_time(show_warm_up=True, resource='nurses', moving_average_window=50)
    plotter.plot_resource_use_over_time(show_warm_up=True, resource='doctors', moving_average_window=50)
    plotter.plot_resource_use_over_time(show_warm_up=True, resource='pharmacy', moving_average_window=50)
    plotter.plot_wip_over_time()
    plotter.plot_system_time_distribution()

    # Plot activity metrics
    print("\nPlotting activity metrics...")
    reporter._print_activity_metrics()
    plotter.plot_activity_metrics()

        
    # Plot resource utilization summary
    print("\nPlotting resourse summary...")
    plotter.plot_resources_utilization()
    reporter._print_resource_metrics()
    reporter._print_entity_counts()
    reporter._print_block_statistics()

    
    # Financial analysis
    print("\nPlotting financial analysys...")
    financial_analyzer = FinancialAnalyzer(model)
    financial_analyzer.print_financial_summary()
    financial_analyzer.plot_financial_breakdown()

    # 5. Export event log
    print("\nExporting event log...")
    df = event_logger.export_to_csv("hospital_event_log.csv")
    print(f"\nFirst 10 events:")
    print(df.head(10))
    
    # 6. Direct metrics access (if needed)
    metrics = MetricsCollector(model)
    entity_metrics = metrics.get_entity_metrics_summary()
    resource_metrics = metrics.get_resource_metrics_summary()
    
    print(f"\nAverage system time: {entity_metrics['tempo_medio_sistema']:.2f} min")
    # print(f"Nurses utilization: "
    #       f"{resource_metrics['nurses']['taxa_utilizacao']:.1%}")
    print(f"Random seed for this run: {config.seed}")
    
    return model, event_logger


if __name__ == "__main__":
    model, logger = main()
    # run_replications()
    # factorial = hospital_factorial_analysis()
    
    