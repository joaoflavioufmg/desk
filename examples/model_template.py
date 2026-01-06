# ####################################################################################
# TODO: Checklist de ajustes em cada modelo:
# FILE: model_template.py
# Função: build_ex1_model;
# Atividades e termos em def distribution(tipo):
# Resources: model.add_resource("Equipes", 1);
# simulation_wrapper: model = build_ex1_model(event_logger);
# def ex1_factorial_analysis(): def ex1_simulation_wrapper(arrival_rate=1, num_equipes=1,
# def ex1_factorial_analysis(): ex1_simulation_wrapper: model = build_ex1_model()
# factorial.add_factor(factor_name='arrival_rate',
# factorial.add_factor(factor_name='num_equipes',
# factorial.plot_interaction_effects('system_time_avg', 'arrival_rate', 'num_equipes')
# def main(): print("Building ex1 model...");     model = build_ex1_model(event_logger)
# plotter.plot_resource_use_over_time(show_warm_up=True, resource='equipes', moving_average_window=50)    
# print("\nExporting event log...")    df = event_logger.export_to_csv("ex1_event_log.csv");
# ####################################################################################

# =====================================================================
# FILE: model_template.py
# =====================================================================
import random
import sys
from stats.factorial import FactorialExperiment
from stats.replication import ReplicationFramework    
from analytics.financial import FinancialAnalyzer
from validation.resource_validator import ResourceValidator
from core.simulation_model import SimulationModel
from core.simulation_observer import SimulationObserver
from core.entity import EventLogger
from blocks.create_block import CreateBlock
from blocks.process_block import ProcessBlock, MultiProcessBlock
from blocks.decide_block import DecideBlock
from blocks.dispose_block import DisposeBlock
from analytics.metrics import MetricsCollector
from analytics.reporting import SimulationReporter
from analytics.plotting import SimulationPlotter
from validation.stability import StabilityAnalyzer
from validation.warmup import WarmUpAnalyzer
from config.simulation_config import SimulationConfig
from visualization.interface import run_visualization


# ================================================================
# Each ACD model is implemented here
# ================================================================
def build_ex_model(final_simulation_time=None, event_logger=None, verbose=True,
                        entity_filter=None, resource_filter=None,
                        event_type_filter=None, time_range=None): 
    """Build the simulation model with refactored structure.
    Args:
        event_logger: Optional event logger
        verbose: Enable event tracing
        entity_filter: Optional entity filter for tracing
        resource_filter: Optional resource filter for tracing
        event_type_filter: Optional event type filter for tracing
        time_range: Optional time range for tracing
    """
    
    HOURS = 60  # Time conversion factor (base time: minutes)
    DAYS = 1440
    YEARS = 525600

    if final_simulation_time is None:
        final_simulation_time = 365 * DAYS  # Set default to match the intended simulation time
    
    model = SimulationModel(verbose=verbose,
        entity_filter=entity_filter,
        resource_filter=resource_filter,
        event_type_filter=event_type_filter,
        time_range=time_range)  # NEW: Pass verbose flag

    # Unidade básica para todos os tempos: minutos
    def distribution(tipo):
        # taxa_chegadas = 6         # 6 por minuto        
        return {
            # 'chegada': random.expovariate(taxa_chegadas), # or ...
            # 'chegada': random.expovariate(1/6), # Intervalo entre chegadas 1 a cada 0,16 min.
            'chegada': random.expovariate(1/10), # Intervalo entre chegadas 1 a cada 10 min.
            'ativ1': random.gauss(6, 1),
            'ativ2': 0.5,
            'ativ3': random.uniform(5, 8)
        }.get(tipo,0.0)

    
    # Resources - regular, priority, preempt
    rec1 = model.add_resource("Rec1", 2, "regular")     
    rec2 = model.add_resource("Rec2", 4, "priority")
    # rec3 = model.add_resource("Rec3", 4, "preemptive") 
    rec3 = model.add_resource("Rec3", 6, "regular") 

    # Entity severity generator
    def entity_priority():
        severity_dist = [0.1, 0.2, 0.3, 0.3, 0.1]
        return random.choices([0, 1, 2, 3, 4], weights=severity_dist)[0]

    # Add model variables
    model.add_model_variable('var1_num_eventos', 0, 
                            'Descrição da variável 01', 'unidades')

    model.add_model_variable('var_02_percentual_eventos', 0,
                            'Descrição da variável 02', '%',
                            calculate_fn=lambda m: (
                                m.variable_tracker.get_current('var1_num_eventos') /
                                max(1, m.entity_count) * 100))
    
    
    # Create blocks
    chegadas_ent_A = CreateBlock(
        "ChegadasEnt_A", model.env,
        inter_arrival_time=lambda: distribution('chegada'),
        entity_prefix="Ent_A",
        max_arrivals=None, # Infinito
        first_creation=0.0,
        priority_generator=entity_priority,
        event_logger=event_logger
    )    
    # CONFIGURE ENTITY ATTRIBUTES # Assign "atrib1" to each entity
    chegadas_ent_A.assign_attributes(
        atrib1=lambda: random.randint(1, 4)  # Entidade recebe um atributo: Num entre 1 e 4 
    )

    # Chegada de 2 entidades em paralelo?
    chegadas_ent_B = CreateBlock(
        "ChegadasEnt_B", model.env,
        inter_arrival_time=lambda: distribution('chegada'),
        entity_prefix="Ent_B",
        max_arrivals=1, # Limite do num max de chegadas
        first_creation=0.0, # A chegada do entidade_B pode ser a posteriori
        # priority_generator=entity_priority,
        event_logger=event_logger
    ) 

    decide_condition = DecideBlock(
        "Decide1", model.env,
        decision_type="condition", # Condition tradicional (entity based)
        event_logger=event_logger
    )   

    decide_generic_condition = DecideBlock(
        "Decide2", model.env,
        decision_type="condition_generic", # Condition generic (formula based)
        event_logger=event_logger
    )    

    decide_probalility = DecideBlock(
        "Decide3", model.env,
        decision_type="probability", # Probability (hostorical based)
        event_logger=event_logger
    )

    # Define activity priorities
    PRIO_ATIVIDADE = {
        "ativ2": 0,  # Highest priority
        "ativ3": 1    # Lower priority
    }    

    # Activity with attibute modification
    atividade_1 = ProcessBlock(
        "Ativ_1", model.env,
        # resource=None,    # None, se apenas Delay (sem recursos)
        resource=rec1,
        delay_time=lambda: distribution('ativ1'),
        resource_units=1,         # 1 CHECK! 
        event_logger=event_logger
    )
    atividade_1.set_resource_name('Rec1')    
    atividade_1.modify_attributes(        
        atrib1=lambda current: max(0, current - 1) # Dynamic attribute modification
    )
    
    # Higher priority Activity
    atividade_2 = MultiProcessBlock(
        "Ativ_2", model.env,
        resource_requirements={
            rec2: 1,
            rec3: 1 
        },
        delay_time=lambda: distribution('ativ2'),
        event_logger=event_logger
    )
    atividade_2.set_resource_names({
        rec2: 'Rec2',
        rec3: 'Rec3'
    })
    atividade_2.set_activity_priority(PRIO_ATIVIDADE["ativ2"])  # Set activity priority
    
    
    # lower priority Activity
    atividade_3 = MultiProcessBlock(
        "Ativ3", model.env,
        resource_requirements={
            rec2: 1, # Need 2 resources for that activity (check: Is there (capacity) 3 resouces?)
            rec3: 1  # Both rec2 and rec3 must evaluate priority (preempt evaluate priority too)
        },
        delay_time=lambda: distribution('ativ3'),
        event_logger=event_logger
    )
    atividade_3.set_resource_names({
        rec2: 'Rec2',
        rec3: 'Rec3'
    })
    atividade_3.set_activity_priority(PRIO_ATIVIDADE["ativ3"])  # Set activity priority

    decide_time_condition = DecideBlock(
        "DisposeDecision", model.env,
        decision_type="time_condition", # Decide (time condition based)
        event_logger=event_logger
    )   
    
    dispose1 = DisposeBlock(
        "Dispose1", 
        model.env, 
        event_logger=event_logger)

    dispose2 = DisposeBlock(
        "Dispose2", 
        model.env, 
        event_logger=event_logger)


    # Add blocks to model
    for block in [chegadas_ent_A, chegadas_ent_B, 
        atividade_1, atividade_2, atividade_3, 
        decide_condition, decide_generic_condition, decide_probalility, decide_time_condition, 
        dispose1, dispose2]:
        model.add_block(block)
    
    # Connect flow
    chegadas_ent_A.connect_to(atividade_1)    
    atividade_1.connect_to(decide_condition)    
    decide_condition.connect_to(decide_generic_condition)
    decide_generic_condition.connect_to(decide_time_condition)
    decide_time_condition.connect_to(dispose1)
    
    chegadas_ent_B.connect_to(atividade_2)
    atividade_2.connect_to(decide_generic_condition)
    atividade_3.connect_to(dispose1)
    

    # Decision routing functions
    def entity_type_A(entity):
        return "Ent_A" in entity.id.lower()

    def entity_type_B(entity):
        return "Ent_B" in entity.id.lower()

    def evaluate_attribute_1(entity):
        return entity.get_attribute("atrib1", 0) < 1        
    
    def evaluate_attribute_2(entity):
        return entity.get_attribute("atrib1", 0) >= 1
    
    # Decision routing functions
    def entity_urgent(entity):
        return entity.priority <= 1
    
    def entity_not_very_urgent(entity):
        return entity.priority == 2 
    
    def entity_not_urgent(entity):
        return entity.priority >= 3 
        
    
    # Add decision routes (Attention: MUST consider 100% of flows!)
    decide_condition.add_route("It_is_Ent_A_Attrib_01", dispose1, 
        condition=entity_type_A and evaluate_attribute_1)
    decide_condition.add_route("It_is_Ent_A_Attrib_02", atividade_2, 
        condition=entity_type_A and evaluate_attribute_2)

    # Add decision routes (Attention: MUST consider 100% of flows!)
    decide_condition.add_route("It_is_Ent_B_Urgent", atividade_3, 
        condition=entity_type_B and entity_urgent)
    decide_condition.add_route("It_is_Ent_B_Not_Very_Urgent", atividade_2, 
        condition=entity_type_B and entity_not_very_urgent)
    decide_condition.add_route("It_is_Ent_B_Not_Urgent", dispose2, 
        condition=entity_type_B and entity_not_urgent)

    # Add decision routes (Attention: MUST consider 100% of flows!)
    decide_generic_condition.add_route(
        "Route1", decide_time_condition, 
        condition_generic=lambda e, ctx: (
            ctx['resources']['Rec1'].count >= ctx['resources']['Rec1'].capacity
            )
        )
    decide_generic_condition.add_route(
        "Route2", decide_probalility, 
        condition_generic=lambda e, ctx: (
            ctx['resources']['Rec1'].count < ctx['resources']['Rec1'].capacity
            )
        ) 

    # Add decision routes (Attention: MUST consider 100% of flows!)
    decide_time_condition.add_route("Dispose_Yes", dispose2,
        time_condition=lambda t: t >= (final_simulation_time - 0.1*final_simulation_time))

    decide_time_condition.add_route("Dispose_No", atividade_3,
        time_condition=lambda t: t < (final_simulation_time - 0.1*final_simulation_time))

    # Add decision routes (Attention: MUST consider 100% of flows!)
    decide_probalility.add_route("Return_Ativ_1", atividade_1, probability=0.3)
    decide_probalility.add_route("Go_on", atividade_2, probability=0.7)


    # ================================================================
    # ✅ Systen variable: CREATE OBSERVER 
    # ================================================================    
    observer = SimulationObserver(model)
    
    # ✅ DEFINE CALLBACK: What to do when call is lost
    # def count_lost_call(entity, block_name, time, verbose=True):        
    def var_compute_variable_value(entity, block_name, time, verbose=verbose):        
        """Called when entity disposed to Dispose2."""
        tracker = model.variable_tracker
        current = tracker.get_current('var1_num_eventos')
        tracker.update('var1_num_eventos', time, current + 1)
        tracker.update('var_02_percentual_eventos')  # Auto-calculate (lambda)
        if verbose:
            print(f"[{time:.2f}] VAR: Entidade {entity.id} COMPUTADA - Total: {current + 1}")
    
    # ✅ ATTACH OBSERVER: Monitor specific dispose block
    observer.on_entity_disposed(
        block_name='Dispose2',
        callback=var_compute_variable_value
    )

    # ================================================================
    # CONFIGURE FINANCIAL ATTRIBUTES
    # ================================================================    
    # Assign costs to each activity
    atividade_1.assign_attributes(cost=lambda: round(random.uniform(20, 30), 2))    
    atividade_2.assign_attributes(cost=lambda: round(random.uniform(10, 20)))
    atividade_3.assign_attributes(cost=lambda: round(random.uniform(5, 15)))
    dispose1.assign_attributes(revenue=lambda: round(random.uniform(50, 100)))    
    # ================================================================
    
    return model


def simulation_wrapper(seed=None, until=None, warm_up_period=None):
    """Wrapper function for replication framework."""
    
    from core.entity import EventLogger    
    event_logger = EventLogger()

    HOURS = 60  # Time conversion factor (base time: minutes)
    DAYS = 1440
    YEARS = 525600

    # Create configuration
    config = SimulationConfig(
        duration=24*HOURS,
        warm_up_period=2*HOURS,        
        seed=123,
        check_stability=True
    )

    model = build_ex_model(config.duration, event_logger, verbose=False)

    # Validate once on first run
    # if seed == 12345:
    #     model.validate_resources()
    
    
    model.run_simulation(
        validate_resources=False,
        until=until,
        seed=seed,
        warm_up_period=warm_up_period
    )
    
    return model

# ================================================================
# For full simulation
# ================================================================
# Run replications
def run_replications():
    replication_framework = ReplicationFramework(
        simulation_function=simulation_wrapper,
        n_replications=30
    )

    HOURS = 60  # Time conversion factor (base time: minutes)
    DAYS = 1440
    YEARS = 525600
    
    replication_framework.run_replications(
        base_seed=12345,
        until=24*HOURS,
        warm_up_period=2*HOURS
    )

    # Access results
    df = replication_framework.get_results_dataframe()
    print(df.describe())
# ================================================================
    

# ================================================================
# Factorial Analysis
# ================================================================
def ex_factorial_analysis():
    """Example of factorial analysis with hospital simulation."""

    HOURS = 60  # Time conversion factor (base time: minutes)
    DAYS = 1440
    YEARS = 525600

    # Create configuration
    config = SimulationConfig(
        duration=24*HOURS,
        warm_up_period=2*HOURS,        
        seed=123,
        check_stability=True        
    )
    
    # Define simulation function wrapper
    def ex_simulation_wrapper(arrival_rate=10, num_Rec1=5, num_Rec2=10, 
                                    seed=None, until=None, warm_up_period=0, **kwargs):
        """Wrapper that adapts parameters for factorial analysis."""

        # ############################################################
        # # O modelo de simulação é importado aqui
        # ############################################################
        
        # This would need to be modified in your actual model to accept these parameters
        # For now, this is a template showing how to structure it
        model = build_ex_model(config.duration, verbose=False)
        model.run_simulation(validate_resources=False, until=until, seed=seed, warm_up_period=warm_up_period)
        return model
    
    # Create factorial analysis
    factorial = FactorialExperiment(
        simulation_function=ex_simulation_wrapper,
        base_seed=12345
    )
    
    # Add factors
    factorial.add_factor(
        factor_name='arrival_rate',
        parameter_path='CreateBlock.inter_arrival_time',
        levels=[10, 15, 20],  # Minutes between arrivals
        description='Taxa de chegada de entidades (min)'
    )
    
    factorial.add_factor(
        factor_name='num_Rec1',
        parameter_path='Resource.rec1.capacity',
        levels=[5, 10, 15],
        description='Número de Rec #1'
    )
    
    factorial.add_factor(
        factor_name='num_Rec2',
        parameter_path='Resource.rec2.capacity',
        levels=[10, 20, 30],
        description='Número de Rec #2'
    )
    
    # Run experiment
    factorial.run_factorial_experiment(
        n_replications=5,
        simulation_time=40*60,  # 40 hours
        warm_up_period=7*60,    # 7 hours
        verbose=True
        # verbose=False
    )
    
    # Analyze results
    factorial.print_summary()
    factorial.plot_correlation_matrix()
    factorial.plot_main_effects('system_time_avg')
    factorial.plot_interaction_effects('system_time_avg', 'arrival_rate', 'num_Rec1')
    
    # Export
    factorial.export_results()

    print("\n\nFactorial analysis examples completed!")
    print("Check the generated CSV files and plots for detailed results.")
    
    return factorial
# ================================================================

def pause_simulation(message="Continue? (Enter=yes / n=no): "):
    answer = input(message)
    if answer.lower().startswith('n'):
        print(f"Simulation stopped!")
        sys.exit()  # stops the simulation


def main():
    """Main example demonstrating refactored usage."""
    
    HOURS = 60  # Time conversion factor (base time: Minutos)
    DAYS = 1440
    YEARS = 525600
    
    # Create configuration
    config = SimulationConfig(
        warm_up_period=1,
        duration=60,
        # warm_up_period=0.5*HOURS,
        # duration=8*HOURS,        
        # warm_up_period=5*DAYS,        
        # duration=21*DAYS,        
        seed=123,
        check_stability=True
    )
    config.validate()

    # Create event logger
    event_logger = EventLogger()
    
    # Build model
    print("Building ex model...")
    verbose = config.duration <= 10*HOURS    
    model = build_ex_model(config.duration, event_logger, verbose=verbose)
    
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
    # ========================================
    # Trace specific chamada
    # ========================================    
    print("\n" + "="*80)
    print("FILTER: Journey of Ent_A_1")
    print("="*80)    
    pause_simulation()
    model.trace_entity('Ent_A_1')    
    
    
    # ========================================
    # Replay with filters
    # ========================================
    print("\n" + "="*80)
    print("FILTER: Replay - First 3 Ent_A only")
    print("="*80)    
    pause_simulation()
    model.replay_trace(entity_pattern = r'^Ent_A_[1-3]$')
    

    # ========================================
    # Trace specific resource
    # ========================================
    print("\n" + "="*80)
    print("FILTER: Replay - Rec1 interactions only")
    print("="*80)    
    pause_simulation()
    model.replay_trace(resource_filter={'Rec1'})
    

    # ========================================
    # Trace specific event types
    # ========================================
    print("\n" + "="*80)
    print("FILTER: Replay - Queue and service events only")
    print("="*80)    
    pause_simulation()
    model.replay_trace(event_type_filter={'queue', 'service_start', 'service_end'})
    

    # ========================================
    # Trace time window
    # ========================================
    print("\n" + "="*80)
    print("FILTER: Replay - Events between t=20 and t=30")
    print("="*80)    
    pause_simulation()
    model.replay_trace(time_range=(20, 30))
    

    # ========================================
    # Combined filters
    # ========================================
    print("\n" + "="*80)
    print("FILTER: Replay - Ent_A_1 at Rec1 (queue + service)")
    print("="*80)    
    pause_simulation()
    model.replay_trace(
        entity_filter={'Ent_A_1'},
        resource_filter={'Rec1'},
        event_type_filter={'queue', 'service_start', 'service_end'}
    )
    

    # ========================================
    # Multiple chamadas journeys
    # ========================================
    print("\n" + "="*80)
    print("FILTER: Detailed journeys of first 3 Ent_A")
    print("="*80)    
    pause_simulation()
    model.trace_entities(['Ent_A_1', 'Ent_A_2', 'Ent_A_3'])
    

    # ========================================
    # Trace statistics
    # ========================================
    model.print_trace_statistics()
    pause_simulation()


    # ========================================
    # 2. Detailed reporting
    # ========================================
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
    plotter.plot_resource_use_over_time(show_warm_up=True, resource='Rec1', moving_average_window=50)
    plotter.plot_resource_use_over_time(show_warm_up=True, resource='Rec2', moving_average_window=50)    
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

    
    # Print variable results
    # ================================================================
    tracker = model.variable_tracker
    print(f"\n{'='*60}")
    print(f"RESULTS (Variables):")
    print(f"Total entities: {model.entity_count}")
    print(f"Entities tracked: {tracker.get_final('var1_num_eventos')}")
    print(f"Percentage tracked: {tracker.get_final('var_02_percentual_eventos'):.2f}%")
    print(f"{'='*60}")
    # ================================================================
    

    # Financial analysis
    print("\nPlotting financial analysys...")
    financial_analyzer = FinancialAnalyzer(model)
    financial_analyzer.print_financial_summary()
    financial_analyzer.plot_financial_breakdown()

    # 5. Export event log
    print("\nExporting event log...")
    df = event_logger.export_to_csv("results/ex_event_log.csv")
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
    # factorial = ex_factorial_analysis()
    # run_visualization(build_ex_model, simulation_time=8*60)