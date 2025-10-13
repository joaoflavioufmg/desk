# =====================================================================
# FILE: blocks/process_block.py
# =====================================================================
from core.base_block import BaseBlock
from core.entity import Entity, EventLogger
from typing import Dict, Callable, Optional
import simpy

# =====================================================================
# FILE: blocks/process_block.py
# =====================================================================
class ProcessBlock(BaseBlock):
    """
    PROCESS block - performs delay operation with optional resource seizure.
    
    Can operate in two modes:
    1. With resource: seize resource, delay, release resource (traditional queue)
    2. Without resource: pure delay operation (no queueing)
    
    Args:
        name: Block name
        env: SimPy environment
        delay_time: Function returning delay duration
        resource: Optional resource to seize (None = pure delay)
        resource_units: Number of resource units to seize (default 1)
        event_logger: Optional event logger
    """
    
    def __init__(self, name: str, env: simpy.Environment,
                 delay_time: Callable[[], float],
                 resource: Optional[simpy.Resource] = None,
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

    def process_entity(self, entity: Entity):
        """
        Process an entity through delay operation with optional resource usage.
        
        If resource is None: performs pure delay
        If resource exists: seizes resource, delays, releases resource
        """
        entity.route_history.append(self.name)
        
        if self.resource is None:
            # Pure delay mode (no resource)
            yield from self._process_without_resource(entity)
        else:
            # Resource-based mode (traditional queue)
            yield from self._process_with_resource(entity)
    
    def _process_without_resource(self, entity: Entity):
        """Process entity with pure delay (no resource seizure)."""
        # Log activity start
        self.log_start(entity, resource_name=None)
        
        # Calculate delay
        if hasattr(self.env, 'model') and hasattr(self.env.model, 'safe_delay_time'):
            delay = self.env.model.safe_delay_time(self.delay_time)
        else:
            delay = max(0.0, self.delay_time())
        
        # Perform delay
        yield self.env.timeout(delay)
        
        # Update statistics
        self.entities_processed += 1
        self.total_delay_time += delay
        entity.add_attribute(f"{self.name}_service_time", delay)
        entity.add_attribute(f"{self.name}_queue_time", 0.0)  # No queueing
        
        # Apply configured attributes
        self._apply_attributes(entity)
        
        # Log activity complete
        self.log_complete(entity, resource_name=None)
        
        # Continue to next block
        yield from self.send_to_next(entity)
    
    def _process_with_resource(self, entity: Entity):
        """Process entity with resource seizure (traditional queue behavior)."""
        self._monitor_resource()

        # 🔄 RETRY LOOP - handles preemption during acquisition OR service
        while True:
            queue_start = self.env.now

            # Create list of requests according to resource_units
            requests = []
            for _ in range(self.resource_units):
                if isinstance(self.resource, simpy.PreemptiveResource):
                    # ⚠️ Use preempt=False during request
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
        """Monitor resource state for statistics (only if resource exists)."""
        if self.resource is None:
            return  # Skip monitoring if no resource
        
        current_queue_length = len(self.resource.queue)
        current_in_service = self.resource.count
        
        self.max_queue_length = max(self.max_queue_length, current_queue_length)
        self.max_in_service = max(self.max_in_service, current_in_service)
        
        # Always collect data for warm-up analysis
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
