# DESK — Discrete Event Simulation Kit

## 🚀 Getting Started

### Installation

## Requirements

- Python >= 3.10
- simpy >= 4.0.1
- numpy
- pandas
- scipy
- matplotlib

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
desk-sim -h
desk-sim -m examples/hospital.py --mode visualization

desk-distfit -h
desk-distfit -d input_data/data10.txt
```