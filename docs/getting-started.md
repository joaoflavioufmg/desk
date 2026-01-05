# DESK — Discrete Event Simulation Kit

## 🚀 Getting Started

### Installation

```bash
# Clone the repository
git clone https://github.com/joaoflavioufmg/desk.git
cd desk

# Install dependencies
pip install -r requirements.txt



# DESK — Discrete Event Simulation Kit

## 🚀 Basic Example

```python
from core.simulation_model import SimulationModel
from core.entity import EventLogger
from blocks.create_block import CreateBlock
from blocks.process_block import ProcessBlock
from blocks.dispose_block import DisposeBlock
import random

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

# Run simulation
model.run_simulation(
    until=480,          # 8 hours
    warm_up_period=60,  # 1 hour
    seed=123
)

# Report results
from analytics.reporting import SimulationReporter
reporter = SimulationReporter(model)
reporter.print_results()
```

---

## 📊 Input Analysis with DistFit

Fit probability distributions to empirical data:

```bash
# Basic usage
python input.py -d data.txt

# Custom significance level
python input.py -d data.txt -a 0.01

# Test specific distributions
python input.py -d data.txt --distributions norm expon gamma

# Save results
python input.py -d data.txt -o results.txt --format json

# Skip plotting
python input.py -d data.txt --no-plot
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
from stats.replication import ReplicationFramework

replication_framework = ReplicationFramework(
    simulation_function=simulation_wrapper,
    n_replications=30
)

replication_framework.run_replications(
    base_seed=12345,
    until=24*60,
    warm_up_period=2*60
)

df = replication_framework.get_results_dataframe()
print(df.describe())
```

### Factorial Experiments

```python
from stats.factorial import FactorialExperiment

factorial = FactorialExperiment(
    simulation_function=hospital_simulation_wrapper,
    base_seed=12345
)

factorial.add_factor(
    factor_name='arrival_rate',
    parameter_path='CreateBlock.inter_arrival_time',
    levels=[3, 4, 5],
    description='Patient arrival rate (minutes)'
)

factorial.add_factor(
    factor_name='num_doctors',
    parameter_path='Resource.doctors.capacity',
    levels=[3, 4, 5],
    description='Number of doctors'
)

factorial.run_factorial_experiment(
    n_replications=5,
    simulation_time=40*60,
    warm_up_period=7*60
)

factorial.plot_main_effects('system_time_avg')
factorial.plot_interaction_effects(
    'system_time_avg', 'arrival_rate', 'num_doctors'
)
```

---

## 📂 Project Structure

```text
DESK/
├── core/                      # Core simulation engine
├── blocks/                    # Simulation building blocks
├── analytics/                 # Metrics, plots, reports
├── stats/                     # Replication & factorial design
├── validation/                # Stability and warm-up analysis
├── visualization/             # Real-time visualization
├── input.py                   # DistFit CLI tool
├── hospital.py                # Hospital example
├── 3.py                       # Call center example
└── README.md
```

---

## 🎓 Example Models

* **Hospital Emergency Department**
  Triage, multiple resources, priority routing, financial tracking

* **Call Center with Lost Calls**
  Trunk capacity, blocking, retrials, custom KPIs

* **Restaurant Service**
  Multi-resource activities, dynamic attributes, satisfaction metrics

---

## 🔬 Validation & Verification

DESK includes:

* Stability checker (ρ < 1)
* Resource consistency validation
* Little’s Law verification
* Automated warm-up detection

---

## 🛠️ Requirements

* Python >= 3.8
* simpy >= 4.0.1
* numpy
* pandas
* scipy
* matplotlib

**Optional (for process mining):**

* R >= 4.0
* bupaR
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

- The DESK book and documentation are licensed under Creative Commons

Attribution 4.0 (CC BY 4.0).

---

## 👨‍🏫 Acknowledgements

**Author:** Prof. João Flávio de Freitas Almeida
**Program:** PPGEP — UFMG
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
