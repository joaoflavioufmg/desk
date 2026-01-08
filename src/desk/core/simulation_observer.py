# =============================================================================
# FILE: core/simulation_observer.py
# =============================================================================
"""
Generic Observer System for Computing Model Variables

DESIGN PRINCIPLES:
1. Keep simulation blocks generic and reusable
2. Separate concerns: blocks handle flow, observers handle metrics
3. Use event-driven architecture (observer pattern)
4. Easy to add/remove observers without touching block code

USAGE:
    observer = SimulationObserver(model)
    observer.on_entity_disposed(block_name='ChamadaBloqueada', 
                                callback=count_lost_calls)
"""

from typing import Callable, Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class ObservableEvent(Enum):
    """Types of observable simulation events."""
    ENTITY_CREATED = "entity_created"
    ENTITY_MOVED = "entity_moved"
    ENTITY_DISPOSED = "entity_disposed"
    RESOURCE_SEIZED = "resource_seized"
    RESOURCE_RELEASED = "resource_released"
    DECISION_MADE = "decision_made"
    ACTIVITY_START = "activity_start"
    ACTIVITY_COMPLETE = "activity_complete"


@dataclass
class ObservationRule:
    """Rule for observing specific events."""
    event_type: ObservableEvent
    callback: Callable
    block_filter: Optional[str] = None  # Specific block name
    route_filter: Optional[str] = None  # Specific decision route
    condition: Optional[Callable] = None  # Custom filter function


class SimulationObserver:
    """
    Observes simulation events and updates model variables.
    
    This class wraps simulation blocks to intercept events WITHOUT
    modifying the original block code.
    
    Example:
        observer = SimulationObserver(model)
        
        # Count lost calls when disposed to specific block
        def count_lost_call(entity, block_name, time):
            tracker = model.variable_tracker
            current = tracker.get_current('num_chamadas_perdidas')
            tracker.update('num_chamadas_perdidas', time, current + 1)
        
        observer.on_entity_disposed(
            block_name='ChamadaBloqueada',
            callback=count_lost_call
        )
    """
    
    def __init__(self, model):
        """
        Initialize observer.
        
        Args:
            model: SimulationModel instance
        """
        self.model = model
        self.rules: List[ObservationRule] = []
        self._wrapped_blocks = set()
        
    def on_entity_created(self, callback: Callable, block_name: Optional[str] = None):
        """
        Observe entity creation events.
        
        Args:
            callback: Function(entity, block_name, time)
            block_name: Specific CreateBlock to observe (None = all)
        """
        rule = ObservationRule(
            event_type=ObservableEvent.ENTITY_CREATED,
            callback=callback,
            block_filter=block_name
        )
        self.rules.append(rule)
        self._wrap_blocks_if_needed()
        
    def on_entity_disposed(self, callback: Callable, block_name: Optional[str] = None,
                          condition: Optional[Callable] = None):
        """
        Observe entity disposal events.
        
        Args:
            callback: Function(entity, block_name, time)
            block_name: Specific DisposeBlock to observe (None = all)
            condition: Function(entity) -> bool to filter entities
        
        Example:
            # Count only high-priority disposals
            observer.on_entity_disposed(
                callback=count_vip,
                condition=lambda e: e.priority == 0
            )
        """
        rule = ObservationRule(
            event_type=ObservableEvent.ENTITY_DISPOSED,
            callback=callback,
            block_filter=block_name,
            condition=condition
        )
        self.rules.append(rule)
        self._wrap_blocks_if_needed()
        
    def on_decision_made(self, callback: Callable, block_name: Optional[str] = None,
                        route_name: Optional[str] = None):
        """
        Observe decision routing events.
        
        Args:
            callback: Function(entity, block_name, route_taken, time)
            block_name: Specific DecideBlock to observe (None = all)
            route_name: Specific route to observe (None = all routes)
        
        Example:
            # Count emergency route usage
            observer.on_decision_made(
                block_name='TriageDecision',
                route_name='Emergency',
                callback=count_emergency
            )
        """
        rule = ObservationRule(
            event_type=ObservableEvent.DECISION_MADE,
            callback=callback,
            block_filter=block_name,
            route_filter=route_name
        )
        self.rules.append(rule)
        self._wrap_blocks_if_needed()
        
    def on_activity_complete(self, callback: Callable, block_name: Optional[str] = None):
        """
        Observe activity completion events.
        
        Args:
            callback: Function(entity, block_name, service_time, time)
            block_name: Specific ProcessBlock to observe (None = all)
        """
        rule = ObservationRule(
            event_type=ObservableEvent.ACTIVITY_COMPLETE,
            callback=callback,
            block_filter=block_name
        )
        self.rules.append(rule)
        self._wrap_blocks_if_needed()
        
    def _wrap_blocks_if_needed(self):
        """Wrap blocks to intercept events (only once per block)."""
        from desk.blocks.create_block import CreateBlock
        from desk.blocks.dispose_block import DisposeBlock
        from desk.blocks.decide_block import DecideBlock
        from desk.blocks.process_block import ProcessBlock, MultiProcessBlock
        
        for block_name, block in self.model.blocks.items():
            if block_name in self._wrapped_blocks:
                continue
                
            # Wrap CreateBlocks
            if isinstance(block, CreateBlock):
                self._wrap_create_block(block)
                
            # Wrap DisposeBlocks
            elif isinstance(block, DisposeBlock):
                self._wrap_dispose_block(block)
                
            # Wrap DecideBlocks
            elif isinstance(block, DecideBlock):
                self._wrap_decide_block(block)
                
            # Wrap ProcessBlocks
            elif isinstance(block, (ProcessBlock, MultiProcessBlock)):
                self._wrap_process_block(block)
            
            self._wrapped_blocks.add(block_name)
    
    def _wrap_create_block(self, block):
        """Wrap CreateBlock to observe entity creation."""
        original_gen = block._generation_process
        
        def wrapped_generator():
            for item in original_gen():
                # Entity was just created
                if hasattr(block, 'entities_created') and block.entities_created > 0:
                    entity_num = block.entities_created - 1
                    entity_id = f"{block.entity_prefix}_{entity_num}"
                    
                    # Reconstruct entity (we don't have direct access)
                    # This is a limitation - we trigger callbacks based on count
                    self._trigger_event(
                        ObservableEvent.ENTITY_CREATED,
                        block_name=block.name,
                        entity=None,  # We don't have entity object here
                        entity_id=entity_id,
                        time=self.model.env.now
                    )
                
                yield item
        
        block._generation_process = wrapped_generator
    
    def _wrap_dispose_block(self, block):
        """Wrap DisposeBlock to observe entity disposal."""
        original_process = block.process_entity
        
        def wrapped(entity):
            # Trigger callbacks BEFORE disposal
            self._trigger_event(
                ObservableEvent.ENTITY_DISPOSED,
                block_name=block.name,
                entity=entity,
                time=self.model.env.now
            )
            
            # Continue normal processing
            yield from original_process(entity)
        
        block.process_entity = wrapped
    
    def _wrap_decide_block(self, block):
        """Wrap DecideBlock to observe routing decisions."""
        original_process = block.process_entity
        
        def wrapped(entity):
            # Store original route history length
            original_history_len = len(entity.route_history)
            
            # Process normally
            yield from original_process(entity)
            
            # Detect which route was taken
            decision_attr = f"{block.name}_decision"
            route_taken = entity.get_attribute(decision_attr, None)
            
            if route_taken:
                self._trigger_event(
                    ObservableEvent.DECISION_MADE,
                    block_name=block.name,
                    entity=entity,
                    route_taken=route_taken,
                    time=self.model.env.now
                )
        
        block.process_entity = wrapped
    
    def _wrap_process_block(self, block):
        """Wrap ProcessBlock to observe activity completion."""
        original_log_complete = block.log_complete
        
        def wrapped_log_complete(entity, resource_name=None):
            # Get service time
            service_time = entity.get_attribute(f"{block.name}_service_time", 0)
            
            # Trigger callbacks
            self._trigger_event(
                ObservableEvent.ACTIVITY_COMPLETE,
                block_name=block.name,
                entity=entity,
                service_time=service_time,
                time=self.model.env.now
            )
            
            # Continue normal logging
            original_log_complete(entity, resource_name)
        
        block.log_complete = wrapped_log_complete
    
    def _trigger_event(self, event_type: ObservableEvent, **kwargs):
        """Trigger all callbacks matching the event."""
        block_name = kwargs.get('block_name')
        entity = kwargs.get('entity')
        time = kwargs.get('time')
        
        for rule in self.rules:
            # Check event type
            if rule.event_type != event_type:
                continue
            
            # Check block filter
            if rule.block_filter and rule.block_filter != block_name:
                continue
            
            # Check route filter (for decisions)
            if event_type == ObservableEvent.DECISION_MADE:
                route_taken = kwargs.get('route_taken')
                if rule.route_filter and rule.route_filter != route_taken:
                    continue
            
            # Check custom condition
            if rule.condition and entity:
                if not rule.condition(entity):
                    continue
            
            # Execute callback
            try:
                if event_type == ObservableEvent.ENTITY_CREATED:
                    rule.callback(kwargs.get('entity_id'), block_name, time)
                elif event_type == ObservableEvent.ENTITY_DISPOSED:
                    rule.callback(entity, block_name, time)
                elif event_type == ObservableEvent.DECISION_MADE:
                    rule.callback(entity, block_name, kwargs.get('route_taken'), time)
                elif event_type == ObservableEvent.ACTIVITY_COMPLETE:
                    rule.callback(entity, block_name, kwargs.get('service_time'), time)
            except Exception as e:
                print(f"Error in observer callback: {e}")


# # =============================================================================
# # USAGE EXAMPLES
# # =============================================================================
# def example_call_center_with_observer():
#     """Example: Call center with lost call tracking using observer."""
    
#     from core.simulation_model import SimulationModel
#     from core.entity import EventLogger
#     from blocks.create_block import CreateBlock
#     from blocks.process_block import ProcessBlock
#     from blocks.dispose_block import DisposeBlock
#     from blocks.decide_block import DecideBlock
#     import random
    
#     # Build model (generic blocks - no modifications)
#     model = SimulationModel()
#     event_logger = EventLogger()
    
#     # Add model variables
#     model.add_model_variable('num_chamadas_perdidas', 0, 
#                             'Número de chamadas perdidas', 'unidades')
#     model.add_model_variable('percentual_chamadas_perdidas', 0,
#                             'Percentual de chamadas perdidas', '%',
#                             calculate_fn=lambda m: (
#                                 m.variable_tracker.get_current('num_chamadas_perdidas') /
#                                 max(1, m.entity_count) * 100
#                             ))
    
#     # Create resources and blocks (GENERIC - no special logic)
#     troncos = model.add_resource("Troncos", 30, "regular")
    
#     chegadas = CreateBlock("ChegadasChamadas", model.env,
#                           inter_arrival_time=lambda: random.expovariate(1/15),
#                           entity_prefix="Chamada",
#                           max_arrivals=1000,
#                           event_logger=event_logger)
    
#     decide = DecideBlock("DecideTronco", model.env,
#                         decision_type="condition_generic",
#                         event_logger=event_logger)
    
#     atendimento = ProcessBlock("Atendimento", model.env,
#                               resource=troncos,
#                               delay_time=lambda: random.expovariate(1/2),
#                               event_logger=event_logger)
#     atendimento.set_resource_name('Troncos')
    
#     dispose_atendida = DisposeBlock("ChamadaAtendida", model.env, event_logger)
#     dispose_bloqueada = DisposeBlock("ChamadaBloqueada", model.env, event_logger)
    
#     # Add blocks
#     for block in [chegadas, decide, atendimento, dispose_atendida, dispose_bloqueada]:
#         model.add_block(block)
    
#     # Connect flow
#     chegadas.connect_to(decide)
#     atendimento.connect_to(dispose_atendida)
    
#     # Add routes
#     decide.add_route("Atender", atendimento,
#                     condition_generic=lambda e, ctx: (
#                         ctx['resources']['Troncos'].count < ctx['resources']['Troncos'].capacity
#                     ))
#     decide.add_route("Bloquear", dispose_bloqueada,
#                     condition_generic=lambda e, ctx: (
#                         ctx['resources']['Troncos'].count >= ctx['resources']['Troncos'].capacity
#                     ))
    
#     # ✅ CREATE OBSERVER (separate from blocks)
#     observer = SimulationObserver(model)
    
#     # ✅ DEFINE CALLBACK: What to do when call is lost
#     def count_lost_call(entity, block_name, time):
#         """Called when entity disposed to ChamadaBloqueada."""
#         tracker = model.variable_tracker
#         current = tracker.get_current('num_chamadas_perdidas')
#         tracker.update('num_chamadas_perdidas', time, current + 1)
#         tracker.update('percentual_chamadas_perdidas')  # Auto-calculate
#         print(f"[{time:.2f}] Chamada {entity.id} PERDIDA - Total: {current + 1}")
    
#     # ✅ ATTACH OBSERVER: Monitor specific dispose block
#     observer.on_entity_disposed(
#         block_name='ChamadaBloqueada',
#         callback=count_lost_call
#     )
    
#     # Run simulation
#     model.run_simulation(until=480, seed=123)
    
#     # Print results
#     tracker = model.variable_tracker
#     print(f"\n{'='*60}")
#     print(f"RESULTADOS:")
#     print(f"Total de chamadas: {model.entity_count}")
#     print(f"Chamadas perdidas: {tracker.get_final('num_chamadas_perdidas')}")
#     print(f"Percentual perdido: {tracker.get_final('percentual_chamadas_perdidas'):.2f}%")
#     print(f"{'='*60}")
    
#     return model


# def example_hospital_with_multiple_observers():
#     """Example: Hospital with multiple metric tracking."""
    
#     from core.simulation_model import SimulationModel
    
#     model = SimulationModel()
    
#     # Add multiple variables
#     model.add_model_variable('num_emergency_cases', 0, 'Emergency cases', 'unidades')
#     model.add_model_variable('num_long_waits', 0, 'Long wait times (>30min)', 'unidades')
#     model.add_model_variable('avg_service_time', 0, 'Average service time', 'minutes')
    
#     # ... build model with generic blocks ...
    
#     # Create observer
#     observer = SimulationObserver(model)
    
#     # Observer 1: Count emergency routing
#     def count_emergency(entity, block_name, route_taken, time):
#         if route_taken == 'Emergency':
#             tracker = model.variable_tracker
#             current = tracker.get_current('num_emergency_cases')
#             tracker.update('num_emergency_cases', time, current + 1)
    
#     observer.on_decision_made(
#         block_name='TriageDecision',
#         callback=count_emergency
#     )
    
#     # Observer 2: Track long wait times
#     def check_long_wait(entity, block_name, service_time, time):
#         queue_time = entity.get_attribute('queue_time', 0)
#         if queue_time > 30:
#             tracker = model.variable_tracker
#             current = tracker.get_current('num_long_waits')
#             tracker.update('num_long_waits', time, current + 1)
    
#     observer.on_activity_complete(
#         block_name='Treatment',
#         callback=check_long_wait
#     )
    
#     # Observer 3: Update rolling average service time
#     def update_avg_service_time(entity, block_name, service_time, time):
#         tracker = model.variable_tracker
#         # Simple exponential moving average
#         current_avg = tracker.get_current('avg_service_time')
#         alpha = 0.1  # Smoothing factor
#         new_avg = alpha * service_time + (1 - alpha) * current_avg
#         tracker.update('avg_service_time', time, new_avg)
    
#     observer.on_activity_complete(callback=update_avg_service_time)
    
#     return model, observer


# # =============================================================================
# # INTEGRATION WITH YOUR MODEL
# # =============================================================================
# def your_model_integration_example():
#     """How to add observer to your existing model."""
    
#     code_example = '''
# # In your build_ex3_model() function:

# def build_ex3_model(final_simulation_time=None, event_logger=None):
#     # ... existing model building code (UNCHANGED) ...
    
#     model = SimulationModel()
    
#     # Add variables
#     model.add_model_variable('num_chamadas_perdidas', 0, 
#                             'Chamadas perdidas', 'unidades')
#     model.add_model_variable('percentual_chamadas_perdidas', 0,
#                             'Percentual perdidas', '%',
#                             calculate_fn=lambda m: (
#                                 m.variable_tracker.get_current('num_chamadas_perdidas') /
#                                 max(1, m.entity_count) * 100
#                             ))
    
#     # ... create all blocks (GENERIC - no changes) ...
    
#     # ✅ ADD: Create observer (AFTER all blocks are added)
#     observer = SimulationObserver(model)
    
#     # ✅ ADD: Define callback
#     def count_lost_call(entity, block_name, time):
#         tracker = model.variable_tracker
#         current = tracker.get_current('num_chamadas_perdidas')
#         tracker.update('num_chamadas_perdidas', time, current + 1)
#         tracker.update('percentual_chamadas_perdidas')
    
#     # ✅ ADD: Attach observer
#     observer.on_entity_disposed(
#         block_name='ChamadaBloqueada',
#         callback=count_lost_call
#     )
    
#     # Store observer in model for later access (optional)
#     model.observer = observer
    
#     return model
#     '''
    
#     return code_example


# if __name__ == "__main__":
#     print("="*70)
#     print("SIMULATION OBSERVER SYSTEM")
#     print("="*70)
#     print("\n✅ BENEFITS:")
#     print("  1. Keeps simulation blocks GENERIC and reusable")
#     print("  2. Separates metric computation from simulation logic")
#     print("  3. Easy to add/remove observers without touching blocks")
#     print("  4. Follows observer pattern (event-driven)")
#     print("  5. Can attach multiple observers to same event")
    
#     print("\n📋 USAGE:")
#     print("  observer = SimulationObserver(model)")
#     print("  observer.on_entity_disposed(block_name='LostSales', callback=count_loss)")
    
#     print("\n🎯 SUPPORTED EVENTS:")
#     print("  - on_entity_created()")
#     print("  - on_entity_disposed()")
#     print("  - on_decision_made()")
#     print("  - on_activity_complete()")
    
#     print("\n" + "="*70)
    
#     # Run example
#     print("\nRunning call center example...")
#     model = example_call_center_with_observer()