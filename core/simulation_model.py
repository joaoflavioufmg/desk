# =====================================================================
# FILE: core/simulation_model.py
# =====================================================================
from typing import Dict, Any, List, Optional, Union, Callable
import simpy
import sys
from .base_block import BaseBlock
from blocks.create_block import CreateBlock
from blocks.dispose_block import DisposeBlock
from .model_variables import ModelVariableTracker


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
        # self.resources: Dict[str, Union[simpy.Resource, simpy.PriorityResource]] = {}
        self.resources: Dict[str, Union[
            simpy.Resource, 
            simpy.PriorityResource, 
            simpy.PreemptiveResource]] = {}
        self.create_blocks: List['CreateBlock'] = []
        self.dispose_blocks: List['DisposeBlock'] = []
        self.stability_result: Optional[float] = None
        self.warm_up_period: float = 0.0
        self.is_warm_up_complete: bool = False
        self.variable_tracker = ModelVariableTracker(self)


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
        from validation.resource_validator import ResourceValidator
        
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
            from validation.stability import StabilityAnalyzer
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
        from blocks.process_block import ProcessBlock, MultiProcessBlock
        
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

    def add_model_variable(self, name: str, initial_value: Any = 0,
                          description: str = "", unit: str = "",
                          calculate_fn: Optional[Callable] = None):
        """Add a custom model variable to track."""
        self.variable_tracker.add_variable(
            name, initial_value, description, unit, calculate_fn
        )

    def update_model_variable(self, name: str, value: Any = None):
        """Update a model variable."""
        self.variable_tracker.update(name, value=value)

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