<!-- AUTO-GENERATED FROM README.md — DO NOT EDIT -->

# DESK — Discrete Event Simulation Kit


DESK is an open-source, academic framework for **Discrete-Event Simulation (DES)** built on top of **SimPy**, designed for:


- Scientific reproducibility
- Experimental design (replication & factorial analysis)
- Input modeling and validation
- Teaching simulation and logistics systems


It is used in graduate-level courses at **PPGEP/UFMG** and supports complex systems such as healthcare, call centers, and service operations.


## Key Features


- Modular block-based modeling
- Priority and capacity-constrained resources
- Integrated replication framework
- Factorial and scenario experiments
- Input distribution fitting (DistFit)
- Validation and warm-up detection


---


## Quick Start


```python
from core.simulation_model import SimulationModel
from blocks.create_block import CreateBlock
from blocks.process_block import ProcessBlock
from blocks.dispose_block import DisposeBlock
```