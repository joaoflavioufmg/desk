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
def build_ex2_model(event_logger=None):
    """Build a hospital simulation model with refactored structure."""
    
    HOURS = 60  # Time conversion factor (base time: minutes)
    DAYS = 1440
    YEARS = 525600
    
    model = SimulationModel()

    # Unidade básica para todos os tempos: minutos
    def distribution(tipo):
        taxa_chegadas=10         # por minuto        
        return {
            'chegada': random.expovariate(1/taxa_chegadas),
            'servir': random.gauss(6, 1),
            'lavar': 0.5,
            'beber': random.uniform(5, 8)
        }.get(tipo,0.0)

    
    # Resources - all priority-based
    garcons = model.add_resource("Garcons", 1, "priority") 
    copos = model.add_resource("Copos", 70, "priority")
    
    # Entity priority
    def prio(entidade):
        return {
            "Cliente": 0
        }.get(entidade,0.0)
    
    # Create blocks
    chegadas_clientes = CreateBlock(
        "Chegadas", model.env,
        inter_arrival_time=lambda: distribution('chegada'),
        entity_prefix="Cliente",
        max_arrivals=None, # Infinito
        first_creation=0.0,
        priority_generator=prio("Cliente"),
        event_logger=event_logger
    )
    # ================================================================
    # CONFIGURE ENTITY ATTRIBUTES
    # ================================================================    
    # Assign thursty to each patient
    chegadas_clientes.assign_attributes(
        sede=lambda: random.randint(1, 4)  # Sede entre 1 e 4
    )
    
    # Create blocks
    chegada_garcom = CreateBlock(
        "Chegada_Garcom", model.env,
        inter_arrival_time=lambda: distribution('chegada'),
        entity_prefix="Garcom",   
        max_arrivals=1, # Apenas 1 garcom
        first_creation=0.0,        
        event_logger=event_logger
    )
    
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
        garcons: 'garcom',
        copos: 'copo'
    })
    
    beber = ProcessBlock(
        "Beber", model.env,
        # resource=None,    # None, se apenas Delay (sem recursos)
        resource=copos,
        delay_time=lambda: distribution('beber'),
        resource_units=1,         # 1 CHECK! 
        event_logger=event_logger
    )
    beber.set_resource_name('Copo')

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
        garcons: 'garcom',
        copos: 'copo'
    })

    decide_satisfeito = DecideBlock(
        "DecideSair", model.env,
        decision_type="condition",
        event_logger=event_logger
    )    
    
    dispose = DisposeBlock(
        "Dispose", 
        model.env, 
        event_logger=event_logger)
    
    # Add blocks to model
    for block in [chegadas_clientes, chegada_garcom, 
                servir, decide_satisfeito,
                beber, lavar, dispose]:
        model.add_block(block)
    
    # Connect flow
    chegadas_clientes.connect_to(beber)
    beber.connect_to(decide_satisfeito)
    chegada_garcom.connect_to(servir)
    servir.connect_to(lavar)
    lavar.connect_to(servir)

    # Decision routing functions
    def satisfeito(entity):
        return entity.sede < 1
    
    def nao_satisfeito(entity):
        return entity.sede >= 1 
    
    # Add decision routes
    decide_satisfeito.add_route(
        "Satisfeito",
        next_block=None,  # Will be connected later,
        condition=satisfeito)
    
    decide_satisfeito.add_route(
        "NaoSatisfeito",
        next_block=None,  # Will be connected later,
        condition=nao_satisfeito)

    decide_satisfeito.routes["Satisfeito"]["block"] = dispose
    decide_satisfeito.routes["NaoSatisfeito"]["block"] = beber

    

    # ================================================================
    # CONFIGURE FINANCIAL ATTRIBUTES
    # ================================================================    
    # Assign costs to each activity
    servir.assign_attributes(
        cost=lambda: random.uniform(20, 30)  # Triage costs $20-30
    )
    
    lavar.assign_attributes(
        cost=lambda: random.uniform(1, 2)  # Consultation costs $100-200
    )
    
    
    # Assign revenue at discharge (based on patient complexity)
    def calculate_revenue():
        """Revenue varies by patient complexity"""
        return random.uniform(50, 200)
    
    dispose.assign_attributes(revenue=calculate_revenue)    
    # ================================================================
    
    return model


def simulation_wrapper(seed=None, until=None, warm_up_period=None):
    """Wrapper function for replication framework."""
    
    from core.entity import EventLogger
    
    event_logger = EventLogger()
    model = build_ex2_model(event_logger)

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
    
    # Define simulation function wrapper
    def ex2_simulation_wrapper(arrival_rate=4, num_garcons=1, num_copos=70,
                                    seed=None, until=None, warm_up_period=0, **kwargs):
        """Wrapper that adapts parameters for factorial analysis."""

        # ############################################################
        # # O modelo de simulação é importado aqui
        # ############################################################
        # from hospital import build_ex2_model()
        
        # This would need to be modified in your actual model to accept these parameters
        # For now, this is a template showing how to structure it
        model = build_ex2_model()
        model.run_simulation(until=until, seed=seed, warm_up_period=warm_up_period)
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
        levels=[3, 4, 5],  # Minutes between arrivals
        description='Taxa de chegada de clientes (min)'
    )
    
    factorial.add_factor(
        factor_name='num_garcons',
        parameter_path='Resource.garcons.capacity',
        levels=[1, 3, 5],
        description='Número de garçons'
    )
    
    factorial.add_factor(
        factor_name='num_copos',
        parameter_path='Resource.copos.capacity',
        levels=[50, 70, 90],
        description='Número de copos'
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
    model = build_ex2_model(event_logger)
    
    # Create configuration
    config = SimulationConfig(
        # warm_up_period=0
        # until=20
        duration=24*HOURS,
        warm_up_period=2*HOURS,
        # duration=21*DAYS,
        # warm_up_period=5*DAYS,        
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