"""One-off helper: look up a Confluence Cloud accountId by display name.

Usage: python -m common.lookup_account_id "서지권"
"""
import os
import sys

import requests
from dotenv import load_dotenv

from common.confluence_client import confluence_auth

load_dotenv()


def main():
    name = sys.argv[1]
    base_url = os.environ["CONFLUENCE_BASE_URL"]
    resp = requests.get(
        f"{base_url}/wiki/rest/api/search",
        auth=confluence_auth(),
        params={"cql": f'type=user and user.fullname~"{name}"'},
    )
    resp.raise_for_status()
    results = resp.json()["results"]
    if not results:
        print(f"No match for {name!r}")
        return
    for result in results:
        user = result["user"]
        print(f"{user['displayName']}: {user['accountId']}")


if __name__ == "__main__":
    main()
