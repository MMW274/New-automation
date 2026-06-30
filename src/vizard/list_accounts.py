from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import load_vizard_config
from src.vizard.client import VizardClient


def main() -> None:
    config = load_vizard_config()
    client = VizardClient(config)
    accounts = client.list_social_accounts()

    if not accounts:
        print("No active social accounts connected in Vizard.")
        print("Connect platforms at vizard.ai → Settings → Social accounts")
        return

    print("Active Vizard social accounts (matched by config/vizard.yaml social_accounts when publish_all_connected: false):\n")
    for account in accounts:
        print(f"  platform: {account.get('platform')}")
        print(f"  username: {account.get('username')}")
        print(f"  page:     {account.get('page')}")
        print(f"  id:       {account.get('id')}")
        print(f"  status:   {account.get('status')}\n")

    print("Connect X, Facebook, etc. in Vizard — they auto-publish on next run.")


if __name__ == "__main__":
    main()
