```markdown
# Basic Simulation Example


This example illustrates a simple hospital triage system using DESK blocks.
```

```python
from core.simulation_model import SimulationModel
from core.entity import EventLogger
from blocks.create_block import CreateBlock
from blocks.process_block import ProcessBlock
from blocks.dispose_block import DisposeBlock
import random


model = SimulationModel()
event_logger = EventLogger()


nurses = model.add_resource("Nurses", capacity=3, resource_type="priority")


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


model.add_block(arrivals)
model.add_block(triage)
model.add_block(discharge)


arrivals.connect_to(triage)
triage.connect_to(discharge)


model.run_simulation(until=480, warm_up_period=60, seed=123)
```