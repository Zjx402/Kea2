import yaml
import subprocess
from pathlib import Path

CONFIG_PATH = Path(".github/translation-list.yml")


with open(CONFIG_PATH, "r") as f:
    file_mapping = dict(yaml.safe_load(f)["monitored_files"])
    monitored = file_mapping.keys()

# get changed file list in this commit
changed_files = subprocess.check_output(
    ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
    encoding="utf-8"
).splitlines()

# get intersection
to_translate = [f for f in changed_files if f in monitored]

if to_translate:
    print("\n".join(to_translate))
else:
    pass # empty output
