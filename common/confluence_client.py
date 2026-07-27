"""Shared Confluence REST API v1 helpers, used by every *_weekly_report.py script."""
import os

import requests


def confluence_auth():
    return (os.environ["CONFLUENCE_EMAIL"], os.environ["CONFLUENCE_API_TOKEN"])


def find_existing_page(base_url, space_key, title):
    """Search by exact title across all content types (page and folder) — the plain
    /content?title= endpoint defaults to type=page and silently misses folders."""
    resp = requests.get(
        f"{base_url}/wiki/rest/api/content/search",
        auth=confluence_auth(),
        params={"cql": f'space="{space_key}" and title="{title}"', "expand": "version"},
    )
    resp.raise_for_status()
    results = resp.json()["results"]
    return results[0] if results else None


def get_page_body(base_url, space_key, title):
    """Return the storage-format HTML body of the page titled `title`, or None if missing."""
    existing = find_existing_page(base_url, space_key, title)
    if not existing:
        return None
    resp = requests.get(
        f"{base_url}/wiki/rest/api/content/{existing['id']}",
        auth=confluence_auth(),
        params={"expand": "body.storage"},
    )
    resp.raise_for_status()
    return resp.json()["body"]["storage"]["value"]


def get_or_create_folder(base_url, space_key, parent_id, title):
    """Return the id of the page titled `title` under `parent_id`, creating an empty one if missing."""
    existing = find_existing_page(base_url, space_key, title)
    if existing:
        return existing["id"]
    payload = {
        "type": "page",
        "title": title,
        "space": {"key": space_key},
        "ancestors": [{"id": parent_id}],
        "body": {"storage": {"value": "", "representation": "storage"}},
    }
    resp = requests.post(f"{base_url}/wiki/rest/api/content", auth=confluence_auth(), json=payload)
    resp.raise_for_status()
    return resp.json()["id"]


def upsert_page(base_url, space_key, parent_id, title, body_html):
    existing = find_existing_page(base_url, space_key, title)
    payload = {
        "type": "page",
        "title": title,
        "space": {"key": space_key},
        "body": {"storage": {"value": body_html, "representation": "storage"}},
    }
    if existing:
        payload["version"] = {"number": existing["version"]["number"] + 1}
        resp = requests.put(
            f"{base_url}/wiki/rest/api/content/{existing['id']}",
            auth=confluence_auth(),
            json=payload,
        )
    else:
        payload["ancestors"] = [{"id": parent_id}]
        resp = requests.post(
            f"{base_url}/wiki/rest/api/content",
            auth=confluence_auth(),
            json=payload,
        )
    resp.raise_for_status()
    return resp.json()
