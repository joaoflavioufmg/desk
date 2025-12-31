from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[1]
readme = root / "README.md"
docs = root / "docs"
index = docs / "index.md"

docs.mkdir(exist_ok=True)

shutil.copyfile(readme, index)
print("README.md synced to docs/index.md")
