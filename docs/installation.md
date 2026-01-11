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

🪟 Windows (PowerShell / VS Code / Cursor )

```bash
# 1) Clone the DESK repository
git clone https://github.com/joaoflavioufmg/desk.git
```

```bash
# 2) Enter the project directory
cd desk
```

```bash
# 3) Create a virtual environment
py -m venv venv
```

```bash
# 4) Allow PowerShell to activate virtual environments (run once per machine)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

```bash
# 5) Activate the virtual environment
.\venv\Scripts\Activate.ps1
```

```bash
# 6) Upgrade pip inside the virtual environment
python -m pip install --upgrade pip
```

```bash
# 7) Install DESK and its dependencies
pip install .
```

```bash
# 8) Verify that DESK was installed correctly
desk-sim -h
desk-distfit -h
```

```bash
# 9) Run the hospital example with visualization
desk-sim -m examples/hospital.py --mode visualization
```

```bash
# 10) Run desk-distfit with some data
desk-distfit -d input_data/data10.txt
```

🐧 Linux / macOS (Terminal)

```bash
# 1) Clone the DESK repository
git clone https://github.com/joaoflavioufmg/desk.git
```

```bash
# 2) Enter the project directory
cd desk
```

```bash
# 3) Create a virtual environment
python3 -m venv venv
```

```bash
# 4) Activate the virtual environment
source venv/bin/activate
```

```bash
# 5) Upgrade pip inside the virtual environment
python -m pip install --upgrade pip
```

```bash
# 6) Install DESK and its dependencies
pip install .
```

```bash
# 7) Verify that DESK was installed correctly
desk-sim -h
desk-distfit -h
```

```bash
# 8) Run the hospital example with visualization
desk-sim -m examples/hospital.py --mode visualization
```

```bash
# 9) Run desk-distfit with some data
desk-distfit -d input_data/data10.txt
```