"""Point the ChatGPT plugin at this folder. Run after cloning, or after moving the folder."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
config = {"mcpServers": {"low-vision-mac": {
    "command": str(ROOT / ".venv/bin/python"),
    "args": [str(ROOT / "scripts/server.py")],
}}}
target = ROOT / "plugins/low-vision-mac/.mcp.json"
target.write_text(json.dumps(config, indent=2) + "\n")
print(f"Plugin now runs {ROOT / 'scripts/server.py'}")
