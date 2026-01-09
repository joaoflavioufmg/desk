from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[1]
readme = root / "README.md"
docs = root / "docs"
index = docs / "index.md"

docs.mkdir(exist_ok=True)

shutil.copyfile(readme, index)
shutil.copytree("figs", "docs/figs", dirs_exist_ok=True)


text = Path("README.md").read_text(encoding="utf-8")

# Remove illegal MkDocs paths
text = text.replace("docs/figs/", "figs/")
text = text.replace("/docs/figs/", "figs/")

Path("docs/index.md").write_text(text, encoding="utf-8")

# Copy figures
shutil.copytree("figs", "docs/figs", dirs_exist_ok=True)

print("README.md synced to docs/index.md")
