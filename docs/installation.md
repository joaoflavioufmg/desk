# DESK — Discrete Event Simulation Kit

## 🚀 Getting Started

### Installation

## 🛠️ Requirements

* Python >= 3.11
* simpy == 4.1.1
* numpy == 2.2.6
* pandas == 2.3.1
* scipy == 1.15.3
* matplotlib == 3.10.5

**Optional (for process mining):**

* R >= 4.0
* BupaR
* processanimateR

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