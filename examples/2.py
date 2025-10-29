# =====================================================================
# FILE: 2.py
# =====================================================================
import random
from stats.factorial import FactorialExperiment
from stats.replication import ReplicationFramework    
from analytics.financial import FinancialAnalyzer
from validation.resource_validator import ResourceValidator
from core.simulation_model import SimulationModel
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

# ####################################################################################
# TODO: Checklist de ajustes em cada modelo:
# FILE: hospital.py
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

# ================================================================
# Each ACD model is implemented here
# ================================================================
def build_ex2_model(final_simulation_time=None, event_logger=None):
    """Build a hospital simulation model with refactored structure."""
    
    HOURS = 60  # Time conversion factor (base time: minutes)
    DAYS = 1440
    YEARS = 525600

    if final_simulation_time is None:
        final_simulation_time = 365 * DAYS  # Set default to match the intended simulation time
    
    model = SimulationModel()

    # Unidade básica para todos os tempos: minutos
    def distribution(tipo):
        taxa_chegadas = 0.1         # por minuto        
        return {
            'chegada': random.expovariate(taxa_chegadas),
            'servir': random.gauss(6, 1),
            'lavar': 0.5,
            'beber': random.uniform(5, 8)
        }.get(tipo,0.0)

    
    # Resources - all priority-based
    garcons = model.add_resource("Garcons", 2, "regular") 
    copos = model.add_resource("Copos", 70, "regular")  
    
    
    # Create blocks
    chegadas_clientes = CreateBlock(
        "ChegadasClientes", model.env,
        inter_arrival_time=lambda: distribution('chegada'),
        entity_prefix="Cliente",
        max_arrivals=None, # Infinito
        first_creation=0.0,
        # priority_generator=prio("Cliente"),
        event_logger=event_logger
    )    
    # CONFIGURE ENTITY ATTRIBUTES # Assign "sede" to each patient
    chegadas_clientes.assign_attributes(
        sede=lambda: random.randint(1, 4)  # Sede entre 1 e 4        
        # sedeOriginal=0
    )

    chegadas_garcons = CreateBlock(
        "ChegadasGarcons", model.env,
        inter_arrival_time=lambda: distribution('chegada'),
        entity_prefix="Garcom",
        max_arrivals=1, 
        first_creation=0.0,
        # priority_generator=prio("Cliente"),
        event_logger=event_logger
    ) 

    decide_ent_origem = DecideBlock(
        "Decide1", model.env,
        decision_type="condition",
        event_logger=event_logger
    )   

    # Define activity priorities
    PRIO_ATIVIDADE = {
        "servir": 0,  # Highest priority
        "lavar": 1    # Lower priority
    }    
    
    servir = MultiProcessBlock(
        "Servir", model.env,
        resource_requirements={
            garcons: 1,
            copos: 1
        },
        delay_time=lambda: distribution('servir'),
        event_logger=event_logger
    )
    servir.set_resource_names({
        garcons: 'Garcons',
        copos: 'Copos'
    })
    servir.set_activity_priority(PRIO_ATIVIDADE["servir"])  # Set activity priority
    
    beber = ProcessBlock(
        "Beber", model.env,
        # resource=None,    # None, se apenas Delay (sem recursos)
        resource=copos,
        delay_time=lambda: distribution('beber'),
        resource_units=1,         # 1 CHECK! 
        event_logger=event_logger
    )
    beber.set_resource_name('Copos')
    # NEW: Configure dynamic attribute modification
    beber.modify_attributes(
        # sedeOriginal=lambda sede: sede,        
        # sede=lambda current: current - 1  # Decrement sede by 1
        sede=lambda current: max(0, current - 1)
    )


    # Lavar activity with lower priority
    lavar = MultiProcessBlock(
        "Lavar", model.env,
        resource_requirements={
            garcons: 1,
            copos: 1
        },
        delay_time=lambda: distribution('lavar'),
        event_logger=event_logger
    )
    lavar.set_resource_names({
        garcons: 'Garcons',
        copos: 'Copos'
    })
    lavar.set_activity_priority(PRIO_ATIVIDADE["lavar"])  # Set activity priority

    decide_satisfeito = DecideBlock(
        "Decide2", model.env,
        decision_type="condition",
        event_logger=event_logger
    )    
    
    dispose = DisposeBlock(
        "Dispose", 
        model.env, 
        event_logger=event_logger)

    decision_time = DecideBlock(
        "DisposeDecision", model.env,
        decision_type="time_condition",
        event_logger=event_logger
    )

    # Add blocks to model
    for block in [chegadas_clientes, chegadas_garcons, servir, 
                beber, decide_satisfeito, decide_ent_origem, 
                decision_time, lavar, dispose]:
        model.add_block(block)
    
    # Connect flow
    chegadas_clientes.connect_to(servir)    
    servir.connect_to(decide_ent_origem)    
    beber.connect_to(decide_satisfeito)

    # chegadas_garcons.connect_to(servir)
    # lavar.connect_to(decision_time)
    chegadas_garcons.connect_to(lavar)
    lavar.connect_to(decision_time)
    # chegadas_clientes.connect_to(servir)    
    # servir.connect_to(beber)    
    # beber.connect_to(decide_satisfeito)
    # chegadas_garcons.connect_to(lavar)
    # lavar.connect_to(lavar)

    # Decision routing functions
    def ori_cliente(entity):
        return "cliente" in entity.id.lower()

    def ori_garcom(entity):
        return "garcom" in entity.id.lower()

    def satisfeito(entity):
        return entity.get_attribute("sede", 0) < 1
        # sede_value = entity.get_attribute("sede", 0)
        # print(f"[DEBUG SATISFEITO] {entity.id}: sede={sede_value}, satisfeito={sede_value < 1}")
        # return sede_value < 1
    
    def nao_satisfeito(entity):
        return entity.get_attribute("sede", 0) >= 1
        # sede_value = entity.get_attribute("sede", 0)
        # print(f"[DEBUG NAO_SATISFEITO] {entity.id}: sede={sede_value}, nao_satisfeito={sede_value >= 1}")
        # return sede_value >= 1
    
    # Add decision routes
    decide_ent_origem.add_route("Cliente", beber, condition=ori_cliente)
    decide_ent_origem.add_route("Garcom", lavar, condition=ori_garcom)

    decide_satisfeito.add_route("Satisfeito", dispose, condition=satisfeito)    
    decide_satisfeito.add_route("Beber_mais", servir, condition=nao_satisfeito)

    decision_time.add_route("Dispose_Yes", dispose,
        time_condition=lambda t: t >= (final_simulation_time - 10))
    decision_time.add_route("Dispose_No", lavar,
        time_condition=lambda t: t < (final_simulation_time - 10))
    
   

    # ================================================================
    # CONFIGURE FINANCIAL ATTRIBUTES
    # ================================================================    
    # Assign costs to each activity
    servir.assign_attributes(cost=lambda: random.uniform(20, 30))    
    lavar.assign_attributes(cost=lambda: random.uniform(10, 20))
    dispose.assign_attributes(revenue=lambda: random.uniform(50, 100))    
    # dispose.assign_attributes(revenue=lambda sedeOriginal: sedeOriginal * 20)    
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

    model = build_ex2_model(config.duration, event_logger)
    # model = build_ex2_model(event_logger)

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
def ex2_factorial_analysis():
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
    def ex2_simulation_wrapper(arrival_rate=10, num_garcons=1, num_copos=70,
                                    seed=None, until=None, warm_up_period=0, **kwargs):
        """Wrapper that adapts parameters for factorial analysis."""

        # ############################################################
        # # O modelo de simulação é importado aqui
        # ############################################################
        # from hospital import build_ex2_model()
        
        # This would need to be modified in your actual model to accept these parameters
        # For now, this is a template showing how to structure it
        model = build_ex2_model(config.duration)
        model.run_simulation(validate_resources=False, until=until, seed=seed, warm_up_period=warm_up_period)
        return model
    
    # Create factorial analysis
    factorial = FactorialExperiment(
        simulation_function=ex2_simulation_wrapper,
        base_seed=12345
    )
    
    # Add factors
    factorial.add_factor(
        factor_name='arrival_rate',
        parameter_path='CreateBlock.inter_arrival_time',
        levels=[10, 15, 20],  # Minutes between arrivals
        description='Taxa de chegada de clientes (min)'
    )
    
    factorial.add_factor(
        factor_name='num_garcons',
        parameter_path='Resource.garcons.capacity',
        levels=[1, 2, 3],
        description='Número de garçons'
    )
    
    factorial.add_factor(
        factor_name='num_copos',
        parameter_path='Resource.copos.capacity',
        levels=[70, 80, 90],
        description='Número de copos'
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
    factorial.plot_interaction_effects('system_time_avg', 'arrival_rate', 'num_garcons')
    
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
    print("Building ex2 model...")    
    
    # Create configuration
    config = SimulationConfig(
        # warm_up_period=0
        # until=20
        duration=8*HOURS,
        warm_up_period=0.5*HOURS,
        # duration=21*DAYS,
        # warm_up_period=5*DAYS,        
        seed=123,
        check_stability=True
    )
    config.validate()

    model = build_ex2_model(config.duration, event_logger)
    
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
    plotter.plot_resource_use_over_time(show_warm_up=True, resource='Garcons', moving_average_window=50)
    plotter.plot_resource_use_over_time(show_warm_up=True, resource='Copos', moving_average_window=50)    
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
    df = event_logger.export_to_csv("ex2_event_log.csv")
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
    # model, logger = main()
    # run_replications()
    # factorial = ex2_factorial_analysis()
    run_visualization(build_ex2_model, simulation_time=8*60)