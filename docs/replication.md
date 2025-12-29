# Replication Analysis


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
```