# Distribution Fitting Tool

Course: EPD899: Simulacao de Sistemas Logísticos 
Prof: João Flávio de Freitas Almeida (PPGEP-UFMG)

A Python tool for fitting probability distributions to empirical data using statistical tests. This tool helps identify the best-fitting probability distribution from a set of common distributions and provides Python code for generating random numbers from the fitted distribution.

## Features

- **Multiple Distribution Support**: Tests 9 common probability distributions (uniform, triangular, exponential, normal, lognormal, beta, gamma, Weibull)
- **Statistical Testing**: Uses Kolmogorov-Smirnov test for goodness-of-fit assessment
- **Command-Line Interface**: Easy-to-use CLI with comprehensive options
- **Multiple Output Formats**: Results can be saved as table, CSV, or JSON
- **Visualization**: Generates comparative plots of fitted distributions
- **Python Code Generation**: Automatically generates Python `random` module code for the best-fitting distribution
- **Robust Error Handling**: Comprehensive error handling and logging

## Installation

### Prerequisites

- Python 3.7 or higher
- Required packages:

```bash
pip install numpy pandas scipy matplotlib
```

### Quick Install

1. Clone this repository:
```bash
git clone https://github.com/yourusername/distribution-fitting-tool.git
cd distribution-fitting-tool
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the tool:
```bash
python input.py -h
```

## Usage

### Basic Usage

```bash
python input.py -d your_data_file.txt
```

### Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `-d, --data` | Path to data file (required) | - |
| `-a, --alpha` | Significance level for statistical tests | 0.05 |
| `-b, --bins` | Number of histogram bins | 50 |
| `--distributions` | Specific distributions to test | All |
| `--no-plot` | Skip generating plots | False |
| `--show-all` | Show all distributions in plot | False |
| `-o, --output` | Output file path | None |
| `--format` | Output format (table/csv/json) | table |
| `-v, --verbose` | Enable verbose logging | False |
| `-h, --help` | Show help message | - |

### Examples

```bash
# Basic analysis
python input.py -d entrada1.txt

# Custom significance level
python input.py -d data.txt -a 0.01

# Test specific distributions only
python input.py -d data.txt --distributions norm expon gamma

# Save results to file
python input.py -d data.txt -o results.txt

# Generate CSV output
python input.py -d data.txt -o results.csv --format csv

# Skip plotting (useful for batch processing)
python input.py -d data.txt --no-plot

# Show all fitted distributions in plot
python input.py -d data.txt --show-all

# Verbose output for debugging
python input.py -d data.txt -v

# Complete example with multiple options
python input.py -d data.txt -a 0.01 -b 100 --show-all -o results.json --format json -v
```

## Input Data Format

The input file should contain one numeric value per line:

```
1.234
2.567
0.891
3.456
...
```

**Supported formats:**
- Plain text files (.txt)
- One number per line
- UTF-8 encoding
- Blank lines are ignored

## Supported Distributions

| Distribution | Python Random Function | Parameters |
|-------------|------------------------|------------|
| Uniform | `random.uniform(a, b)` | a, b |
| Triangular | `random.triangular(low, high, mode)` | low, high, mode |
| Exponential | `random.expovariate(lambd)` | lambda |
| Normal | `random.gauss(mu, sigma)` | mu, sigma |
| Log-Normal | `random.lognormvariate(mu, sigma)` | mu, sigma |
| Beta | `random.betavariate(alpha, beta)` | alpha, beta |
| Gamma | `random.gammavariate(alpha, beta)` | alpha, beta |
| Weibull (Min) | `random.weibullvariate(alpha, beta)` | alpha, beta |
| Weibull (Max) | `random.weibullvariate(alpha, beta)` | alpha, beta |

## Output

### Console Output

The tool provides:
1. **Data statistics** (sample size, mean, std dev, min, max)
2. **Distribution fitting results** with p-values and significance indicators
3. **Parameter details** for all fitted distributions
4. **Summary report** with best-fitting distribution
5. **Python code** for generating random numbers

### Example Output

```
Data Statistics:
Sample size: 200
Mean: 2.0156
Std Dev: 2.0298
Min: 0.0089
Max: 11.2445

Item Distribution   Statistic   P-value     Significant
------------------------------------------------------------
1    expon          0.0456      0.8234      (*)
2    gamma          0.0523      0.7891      (*)
3    norm           0.0789      0.4567      
...

Distribution Fitting Summary Report
==================================================

Best Fitting Distribution: expon
- Parameters: loc=0.000, scale=2.016
- P-value: 0.8234
- Significant at α=0.05: Yes

Python Random Code:
random.expovariate(0.496)
```

### File Output Formats

#### Table Format (default)
Human-readable text format with detailed results and parameters.

#### CSV Format
```csv
Distribution,P_value,Statistic,Significant,Python_Code
expon,0.823400,0.045600,Yes,random.expovariate(0.496)
gamma,0.789100,0.052300,Yes,random.gammavariate(1.024,0.496)
...
```

#### JSON Format
```json
{
  "summary": {
    "sample_size": 200,
    "best_distribution": "expon",
    "alpha": 0.05
  },
  "results": [
    {
      "distribution": "expon",
      "p_value": 0.8234,
      "statistic": 0.0456,
      "parameters": {"loc": 0.0, "scale": 2.016},
      "significant": true,
      "python_code": "random.expovariate(0.496)"
    }
  ]
}
```

## Interpretation

### P-Values
- **p ≥ α**: Distribution is a good fit (significant)
- **p < α**: Distribution is not a good fit (reject)
- Higher p-values indicate better fits

### Significance Indicators
- **(*) asterisk**: Indicates significant fit at the chosen α level
- Results are sorted by p-value (best fit first)

## Programmatic Usage

You can also use the tool as a Python module:

```python
from input import DistributionFitter

# Create fitter instance
fitter = DistributionFitter(alpha=0.05, bins=50)

# Load data
fitter.load_data("your_data.txt")

# Or set data directly
import numpy as np
data = np.random.exponential(2.0, 1000)
fitter.set_data(data)

# Fit distributions
results = fitter.fit_distributions()

# Get best fit
best_fit = fitter.get_best_fit()
print(f"Best distribution: {best_fit.name}")
print(f"P-value: {best_fit.p_value:.4f}")

# Generate Python code
code = fitter.get_python_random_code(best_fit)
print(f"Python code: {code}")

# Create plots
fitter.plot_results(show_all=True)

# Generate report
report = fitter.generate_summary_report()
print(report)
```

## Statistical Method

The tool uses the **Kolmogorov-Smirnov test** to assess goodness-of-fit:

1. **Null Hypothesis (H₀)**: The data follows the tested distribution
2. **Alternative Hypothesis (H₁)**: The data does not follow the tested distribution
3. **Test Statistic**: Maximum difference between empirical and theoretical CDFs
4. **Decision Rule**: Reject H₀ if p-value < α

## Limitations

- **Sample Size**: Requires sufficient data points (recommended: n ≥ 30)
- **Distribution Assumptions**: Only tests common continuous distributions
- **Parameter Estimation**: Uses Maximum Likelihood Estimation (MLE)
- **Independence**: Assumes data points are independent
- **Stationarity**: Assumes data comes from a stationary process

## Troubleshooting

### Common Issues

1. **"File not found" error**
   ```bash
   # Check file path and existence
   ls -la your_data.txt
   ```

2. **"No module named" errors**
   ```bash
   # Install missing packages
   pip install numpy pandas scipy matplotlib
   ```

3. **Empty or invalid data**
   - Ensure file contains numeric values
   - Check for proper encoding (UTF-8)
   - Remove headers or non-numeric content

4. **Plotting errors**
   ```bash
   # Use --no-plot flag to skip visualization
   python input.py -d data.txt --no-plot
   ```

### Getting Help

```bash
# Show detailed help
python input.py -h

# Enable verbose output for debugging
python input.py -d data.txt -v
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-distribution`)
3. Make your changes
4. Add tests if applicable
5. Commit your changes (`git commit -am 'Add new distribution support'`)
6. Push to the branch (`git push origin feature/new-distribution`)
7. Create a Pull Request

### Development Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/distribution-fitting-tool.git
cd distribution-fitting-tool

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Based on work from EPD899: Simulacao de Sistemas Logísticos course
- Prof. João Flávio de Freitas Almeida (PPGEP-UFMG)
- Uses SciPy for statistical distributions and tests
- Matplotlib for visualization
- Pandas for data handling

## References

1. Massey Jr, F. J. (1951). The Kolmogorov-Smirnov test for goodness of fit. Journal of the American statistical Association, 46(253), 68-78.
2. Scipy.stats documentation: https://docs.scipy.org/doc/scipy/reference/stats.html
3. Distribution fitting with Python: https://medium.com/@amirarsalan.rajabi/distribution-fitting-with-python-scipy-bb70a42c0aed

## Changelog

### Version 2.0.0
- Complete rewrite with object-oriented design
- Added command-line interface
- Multiple output formats support
- Enhanced error handling and logging
- Improved visualization

### Version 1.0.0
- Initial release
- Basic distribution fitting functionality
- Simple plotting capabilities