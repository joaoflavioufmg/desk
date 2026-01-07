from pathlib import Path

folder = Path(".")  # current folder

for i in range(1, 27):
    # From current name ...
    old_name = folder / f"entrada{i}.txt"
    # ... To new name
    new_name = folder / f"data{i}.txt"

    if old_name.exists():
        old_name.rename(new_name)
        print(f"{old_name.name} → {new_name.name}")
    else:
        print(f"File not found: {old_name.name}")
