# DESK — Discrete Event Simulation Kit

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18088013.svg)](https://doi.org/10.5281/zenodo.18088013)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
![CI](https://github.com/joaoflavioufmg/desk/actions/workflows/tests.yml/badge.svg)![Docs](https://github.com/joaoflavioufmg/desk/actions/workflows/deploy-docs.yml/badge.svg?branch=main)
[![Documentation Status](https://readthedocs.org/projects/desk-sim/badge/?version=latest)](https://desk-sim.readthedocs.io/en/latest/?badge=latest)


A comprehensive Python framework for **Discrete Event Simulation** with advanced analysis, visualization, and experimental design capabilities.

---

## 📋 Overview

**DESK (Discrete Event Simulation Kit)** is a professional-grade simulation framework built on top of **SimPy**, designed for modeling complex systems such as hospitals, call centers, manufacturing, and service operations.

DESK addresses the gap of structured experimental design and replication automation in discrete-event simulation workflows.

The framework emphasizes:
- modularity,
- reusability,
- transparency,
- and rigorous statistical analysis.

DESK is suitable for **teaching, research, and applied decision support**.

---

## ✨ Key Features

### Core Simulation Engine
- **Modular Block Architecture**: Reusable building blocks (`CREATE`, `PROCESS`, `DECIDE`, `DISPOSE`)
- **Advanced Resource Management**: Regular, priority-based, and preemptive resources
- **Entity Attributes & State Variables**: Dynamic assignment and modification
- **Priority Scheduling**: Activity-level and entity-level priority control
- **Event Tracing**: Comprehensive event logging with filtering and replay

---

### Input Analysis (`desk-distfit`)
- **DistFit Tool**: Automated distribution fitting with statistical tests (`desk-distfit`) 
- Supports 9+ distributions:
  - uniform, triangular, exponential, normal, lognormal, beta, gamma, Weibull
- Kolmogorov–Smirnov goodness-of-fit tests
- Automatic Python `random` code generation
- Multiple output formats: table, JSON, CSV

---

### Experimental Design & Analysis
- **Replication Framework**: Automated multi-run experiments with confidence intervals
- **Factorial Experiments**: Full factorial design with interaction analysis
- **Warm-Up Analysis**: Automated transient detection
- **Stability Analysis**: Capacity analysis on utilization (ρ < 1)

---

### Performance Metrics
- **Entity Metrics**: System time, queue time, service time
- **Resource Metrics**: Utilization, queue length, busy/idle time
- **WIP Tracking**: Time-weighted work-in-process analysis
- **Financial Analysis**: Cost and revenue per activity
- **Little’s Law Verification**: Automatic analysis on stability: The average number of items in the system (L) equals the average arrival rate (λ) multiplied by the average time an item spends in the system (W): L = λW

---

### Visualization & Reporting
- **Real-Time Visualization**: Interactive process animation during simulation
- **Statistical Plots**:
  - Resource utilization over time
  - WIP evolution
  - System time distributions
  - Activity-level metrics
- **BupaR Integration**: Process mining and animation in R ([processanimateR](https://bupaverse.github.io/processanimateR/)).

- **Automated Reports**: Results with diagnostics and recommendations

---

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/joaoflavioufmg/desk.git
cd desk

# Install dependencies
pip install .
# or
pip install -e .

# Then test:
desk-distfit -h
desk-distfit -d data.txt
```


# DESK — Discrete Event Simulation Kit

## 🚀 Basic Example

```python
def build_model(until=None, event_logger=None, verbose=True): 
    
    import random
    from core.simulation_model import SimulationModel
    from core.entity import EventLogger
    from blocks.create_block import CreateBlock
    from blocks.process_block import ProcessBlock
    from blocks.dispose_block import DisposeBlock
    
    HOURS = 60  # Time conversion factor (base time: minutes)
    DAYS = 1440
    YEARS = 525600
    
    # Create model
    model = SimulationModel()
    event_logger = EventLogger()

    # Add resources
    nurses = model.add_resource("Nurses", capacity=3, resource_type="priority")

    # Define blocks
    arrivals = CreateBlock(
        "Arrivals", model.env,
        inter_arrival_time=lambda: random.expovariate(1/10),
        entity_prefix="Patient",
        event_logger=event_logger
    )

    triage = ProcessBlock(
        "Triage", model.env,
        resource=nurses,
        delay_time=lambda: random.uniform(5, 10),
        resource_units=1,
        event_logger=event_logger
    )

    discharge = DisposeBlock("Discharge", model.env, event_logger=event_logger)

    # Register blocks
    for block in [arrivals, triage, discharge]:
        model.add_block(block)

    # Connect flow
    arrivals.connect_to(triage)
    triage.connect_to(discharge)
    
    return model
    
    
# Run a simulation replication
model = build_model()
model.run_simulation(
    until=480,          # 8 hours
    warm_up_period=60,  # 1 hour
    seed=123
)

# Report results
from analytics.reporting import SimulationReporter
reporter = SimulationReporter(model)
reporter.print_results()
reporter._print_activity_metrics()
reporter._print_resource_metrics()
reporter._print_entity_counts()
reporter._print_block_statistics()
```

---

## 📊 Input Analysis with Desk-DistFit

`desk-distfit` is the official DESK input-analysis CLI for statistically fitting probability distributions to empirical data. 

*DESK adopts a verb-oriented command-line interface, where simulation tasks are expressed as structured actions (`desk-distfit`), ensuring consistency, reproducibility, and ease of learning across the framework.*”*

Fit probability distributions to empirical data:

```bash
# Basic usage
desk-distfit -d data.txt

# Custom significance level
desk-distfit -d data.txt -a 0.01

# Test specific distributions
desk-distfit -d data.txt --distributions norm expon gamma

# Save results
desk-distfit -d data.txt -o results.txt --format json

# Skip plotting
desk-distfit -d data.txt --no-plot
```

**Output includes:**

* Goodness-of-fit statistics
* Best-fit distribution
* Parameter estimates
* Ready-to-use Python code

---

## 🧪 Experimental Design

### Replication Analysis

```python
# Define simulation function wrapper
def simulation_wrapper(seed=None, until=None, warm_up_period=None):
    """Wrapper function for replication framework."""
    
    from core.entity import EventLogger
    event_logger = EventLogger()

    # Create a fresh model
    model = build_model(until=until, event_logger=event_logger, verbose=False)
    
    model.run_simulation(
        validate_resources=False,
        until=until,
        seed=seed,
        warm_up_period=warm_up_period
    )
    
    return model

def run_replications():
    from stats.replication import ReplicationFramework
    
    replication_framework = ReplicationFramework(
        simulation_function=simulation_wrapper,
        n_replications=30
    )

    HOURS = 60  # Time conversion factor (base time: minutes)
    DAYS = 1440
    YEARS = 525600
    
    replication_framework.run_replications(
        base_seed=12345,
        until=8*HOURS,
        warm_up_period=1*HOURS
    )

    # Access results
    df = replication_framework.get_results_dataframe()
    print(df.describe())

   
# Run a full simulation    
run_replications()
```

### Factorial Experiments

```python
def factorial_analysis():
    """Factorial analysis with simulation."""
    
    from stats.factorial import FactorialExperiment

    HOURS = 60  # Time conversion factor (base time: minutes)
    DAYS = 1440
    YEARS = 525600
    

    def simulation_wrapper(arrival_rate=1, num_nurses=1,
                                seed=None, until=None, warm_up_period=0, **kwargs):
        """Wrapper that adapts parameters for factorial analysis."""

        from core.entity import EventLogger
        event_logger = EventLogger()

        # Create a fresh model
        model = build_model(until=until, event_logger=event_logger, verbose=False)
        
        model.run_simulation(
            validate_resources=False,
            until=until,
            seed=seed,
            warm_up_period=warm_up_period
        )
        
        return model
    
    # Create factorial analysis
    factorial = FactorialExperiment(
        simulation_function=simulation_wrapper,
        base_seed=12345
    )
    
    # Add factors
    factorial.add_factor(
        factor_name='arrival_rate',
        parameter_path='CreateBlock.inter_arrival_time',
        levels=[1, 2, 3],  # Minutes between arrivals
        description='Inter arrival rates (min)'
    )
    
    factorial.add_factor(
        factor_name='num_nurses',
        parameter_path='Resource.nurses.capacity',
        levels=[1, 2, 3],
        description='Number of nurses'
    )
    
    
    # Run experiment
    factorial.run_factorial_experiment(
        n_replications=5,
        simulation_time=4*HOURS,  # 4 hours
        warm_up_period=1/2*HOURS,    # 1/2 hour
        verbose=True
    )
    
    # Analyze results
    factorial.print_summary()
    factorial.plot_correlation_matrix()
    factorial.plot_main_effects('system_time_avg')
    factorial.plot_interaction_effects('system_time_avg', 'arrival_rate', 'num_nurses')
     
    return factorial

# Run factorial analysis
factorial_analysis()
```

---

## 📂 Project Structure

```text
DESK/
├── config/                    # Simulation setting
├── core/                      # Core simulation engine
├── blocks/                    # Simulation building blocks
├── analytics/                 # Metrics, plots, reports
├── stats/                     # Replication & factorial design
├── validation/                # Stability and warm-up analysis
├── visualization/             # Real-time visualization
├── distfit/distfit.py         # DistFit CLI tool
├── examples/
├── 1) hospital.py             # Hospital example
├── 2) 2.py                    # Restaurant example
├── 3) 3.py, 3a.py, 3b.py      # Call center (and variations 3a, 3b)
└── README.md
```

---

## 🎓 Example Models

1) **Hospital Emergency Department**
  Triage, multiple resources, priority routing, financial tracking

2) **Restaurant Service**
  Multi-resource activities, dynamic attributes, financials

3) **Call Center with Lost Calls**
  Trunk capacity, blocking, retrials, custom KPIs



---

## 🔬 Validation & Verification

DESK includes:

* Stability checker (utilization ρ < 1)
* Resource consistency validation
* Little’s Law analysis
* Automated warm-up suggestion

---

## 🛠️ Requirements

* Python >= 3.10
* simpy == 4.1.1
* numpy == 2.2.6
* pandas == 2.3.1
* scipy == 1.15.3
* matplotlib == 3.10.5

**Optional (for process mining):**

* R >= 4.0
* BupaR
* processanimateR

---

## 🤝 Contributing

Contributions are welcome:

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Open a Pull Request

---

## 📄 License

GPL-3.0 License — see `LICENSE` file.

- The DESK documentation are licensed under Creative Commons

Attribution 4.0 (CC BY 4.0).

---

## 👨‍🏫 Acknowledgements

**Author:** Prof. João Flávio de Freitas Almeida

**Program:** PPGEP — UFMG (Brazil)

**Course:** Simulating Logistics Systems

**Credits:**
* SimPy
* bupaR (R)

---

## 📚 Citation

If you use DESK in academic work, please cite:

```bibtex
@software{desk2025,
  author = {Almeida, João Flávio de Freitas},
  title = {DESK: Discrete Event Simulation Kit},
  year = {2025},
  institution = {PPGEP-UFMG},
  url = {https://github.com/joaoflavioufmg/desk}
}
```
