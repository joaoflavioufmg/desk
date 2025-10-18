# =====================================================================
# FILE: ex1.py
# =====================================================================
import random
from stats.factorial import FactorialExperiment
from stats.replication import ReplicationFramework    
from analytics.financial import FinancialAnalyzer
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
# Projeto: Maquinas operando ininterruptamente 
# Autor: João Flávio F. ALmeida <joao.flavio@dep.ufmg.br>
# Descrição: Uma empresa opera três máquinas, em um determinado setor de sua 
# planta industrial. As máquinas trabalham em operação contínua, 
# interrompendo seu funcionamento apenas para manutenção corretiva. 
# O tempo entre falhas é descrito por uma distribuição exponencial 
# com média de 3 dias. A manutenção é feita por uma única equipe e 
# sua duração segue uma distribuição exponencial com média de 1 dia. 
# Deseja-se simular este problema para avaliar o tempo que as 
# máquinas ficam paradas aguardando por manutenção e para estimar 
# a ocupação média da equipe de manutenção. 
# Para tanto, construir o modelo conceitual do sistema usando 
# diagramas de ciclo de atividades.
# ####################################################################################

# ####################################################################################
# TODO: Checklist de ajustes em cada modelo:
# FILE: ex1.py
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

def build_ex1_model(final_simulation_time, event_logger=None):
    """Build a ex1 simulation model with refactored structure."""
    
    HOURS = 60  # Time conversion factor (base time: minutes)
    DAYS = 1440
    YEARS = 525600
    
    model = SimulationModel()

    def distribution(tipo):
        taxa_chegadas=1         # por minuto        
        return {
            'arrival': random.expovariate(1/taxa_chegadas),
            'operacao': random.expovariate(1/(3*DAYS)),
            'manutencao': random.expovariate(1/(1*DAYS))
        }.get(tipo,0.0)  


    # Resources
    equipes = model.add_resource("Equipes", 1, "regular")
    
    
     # Create blocks
    arrivals = CreateBlock(
        "Arrivals", model.env,        
        inter_arrival_time=lambda: distribution('arrival'),
        entity_prefix="Maquina",  
        max_arrivals=3,
        first_creation=0.0,
        event_logger=event_logger
    )
    
    operacao = ProcessBlock(
        "Operacao", model.env,
        resource=None, # Apenas DELAY (sem recurso)
        delay_time=lambda: distribution('operacao'),
        event_logger=event_logger
    ) 
    
    manutencao = ProcessBlock(
        "Manutencao", model.env,
        resource=equipes,
        delay_time=lambda: distribution('manutencao'),
        resource_units=1,                 
        event_logger=event_logger
    )
    manutencao.set_resource_name('Equipes')
   
    
    decision_time = DecideBlock(
        "DisposeDecision", model.env,
        decision_type="time_condition",
        event_logger=event_logger
    )

    def should_dispose(env):
        """Return True if current time >= final_simulation_time - 30 days."""
        time_threshold = final_simulation_time - 30 * DAYS
        return env.now >= time_threshold

    def should_not_dispose(env):
        """Return True if current time < final_simulation_time - 30 days."""
        time_threshold = final_simulation_time - 30 * DAYS
        return env.now < time_threshold

    decision_time.add_route(
        "Dispose_Yes", 
        next_block=None,  # Will be connected later
        # time_condition=should_dispose)
        time_condition=lambda t: t >= (final_simulation_time - 3*DAYS))

    decision_time.add_route(
        "Dispose_No", 
        next_block=None,  # Will be connected later
        # time_condition=should_not_dispose)
        time_condition=lambda t: t < (final_simulation_time - 3*DAYS))

    dispose = DisposeBlock(
        "Dispose", 
        model.env, 
        event_logger=event_logger)
    
    # Add blocks to model
    for block in [arrivals, operacao, manutencao, dispose]:
        model.add_block(block)

    # Connect flow
    arrivals.connect_to(operacao)
    operacao.connect_to(manutencao)    
    manutencao.connect_to(decision_time)
    decision_time.routes["Dispose_No"]["block"] = operacao
    decision_time.routes["Dispose_Yes"]["block"] = dispose
    
    # ================================================================
    # CONFIGURE FINANCIAL ATTRIBUTES
    # ================================================================    
    # Assign costs to each activity
    operacao.assign_attributes(
        cost=lambda: random.uniform(20, 30)  # Operacao costs $20-30
    )
    
    manutencao.assign_attributes(
        cost=lambda: random.uniform(100, 200)  # Manutencao costs $100-200
    )    
    
    # Assign revenue at discharge (based on patient complexity)
    def calculate_revenue():
        """Revenue varies"""
        return random.uniform(200, 300)
    
    operacao.assign_attributes(revenue=calculate_revenue)    
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
        duration=365*DAYS,
        warm_up_period=30*DAYS,        
        seed=123,
        check_stability=True
    )

    model = build_ex1_model(config.duration, event_logger)

    # Validate once on first run
    if seed == 12345:
        model.validate_resources()

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
        until=365*DAYS,
        warm_up_period=30*DAYS
    )

    # Access results
    df = replication_framework.get_results_dataframe()
    print(df.describe())
# ================================================================


# ================================================================
# Factorial Analysis
# ================================================================
def ex1_factorial_analysis():
    """Example of factorial analysis with simulation."""

    HOURS = 60  # Time conversion factor (base time: minutes)
    DAYS = 1440
    YEARS = 525600

    # Create configuration
    config = SimulationConfig(
        duration=365*DAYS,
        warm_up_period=30*DAYS,        
        seed=123,
        check_stability=True
    )
    
    # Define simulation function wrapper
    def ex1_simulation_wrapper(arrival_rate=1, num_equipes=1,
                                seed=None, until=None, warm_up_period=0, **kwargs):
        """Wrapper that adapts parameters for factorial analysis."""

        # ############################################################
        # # O modelo de simulação é importado aqui
        # ############################################################
        model = build_ex1_model(config.duration)
        model.run_simulation(until=until, seed=seed, warm_up_period=warm_up_period)
        return model
    
    # Create factorial analysis
    factorial = FactorialExperiment(
        simulation_function=ex1_simulation_wrapper,
        base_seed=12345
    )
    
    # Add factors
    factorial.add_factor(
        factor_name='arrival_rate',
        parameter_path='CreateBlock.inter_arrival_time',
        levels=[1, 2, 3],  # Minutes between arrivals
        description='Taxa de chegada de maquinas (min)'
    )
    
    factorial.add_factor(
        factor_name='num_equipes',
        parameter_path='Resource.equipes.capacity',
        levels=[1, 2, 3],
        description='Número de equipes de manutenção'
    )
    
    
    # Run experiment
    factorial.run_factorial_experiment(
        n_replications=5,
        simulation_time=30*DAYS,  # 40 hours
        warm_up_period=3*DAYS,    # 7 hours
        verbose=True
    )
    
    # Analyze results
    factorial.print_summary()
    factorial.plot_correlation_matrix()
    factorial.plot_main_effects('system_time_avg')
    factorial.plot_interaction_effects('system_time_avg', 'arrival_rate', 'num_equipes')
    
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
    print("Building ex1 model...")    
    
    # Create configuration
    config = SimulationConfig(
        # warm_up_period=0
        # until=20
        # duration=24*HOURS,
        # warm_up_period=2*HOURS,
        duration=365*DAYS,
        warm_up_period=30*DAYS,        
        seed=123,
        check_stability=True
    )
    config.validate()

    model = build_ex1_model(config.duration, event_logger)
    
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
    plotter.plot_resource_use_over_time(show_warm_up=True, resource='Equipes', moving_average_window=50)    
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
    df = event_logger.export_to_csv("ex1_event_log.csv")
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
    # factorial = ex1_factorial_analysis()
