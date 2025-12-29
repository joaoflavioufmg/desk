```markdown
# Factorial and Scenario Experiments


```python
from stats.factorial import FactorialExperiment


factorial = FactorialExperiment(
simulation_function=hospital_simulation_wrapper,
base_seed=12345
)