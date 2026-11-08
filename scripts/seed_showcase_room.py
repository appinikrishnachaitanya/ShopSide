#!/usr/bin/env python3
"""Create a prepared, real ShopSide room for a judge walkthrough.

The script uses the public frontend proxy so membership cookies and room updates
follow the same API path as a browser. It creates a fresh room on each run.
"""
import json
import os
import re
import sys
from urllib.parse import quote

import requests

SPATIAL = re.compile(r"\b(?:furniture|decor|lamp|desk|chair|table|sofa|couch|loveseat|bed|shelf|cabinet|dresser|rug|nightstand)s?\b", re.I)


def request(session, method, url, *, payload=None):
    response = session.request(method, url, json=payload, timeout=20)
    if not response.ok:
        try:
            detail = response.json().get("detail", "Request failed")
        except ValueError:
            detail = "Request failed"
        raise RuntimeError(f"{method} {url} returned {response.status_code}: {detail}")
    return response.json()


def command(session, base, room_id, kind, value):
    state = request(session, "GET", f"{base}/api/rooms/{quote(room_id, safe='')}")
    request(session, "POST", f"{base}/api/rooms/{quote(room_id, safe='')}/commands", payload={
        "kind": kind,
        "value": value,
        "revision": state["revision"],
        "command_id": f"showcase-{os.urandom(12).hex()}",
    })


def main():
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    if not base.startswith("https://"):
        raise RuntimeError("Set FRONTEND_URL to the HTTPS ShopSide frontend Cloud Run URL.")

    person_a = requests.Session()
    person_b = requests.Session()
    catalog = request(person_a, "GET", f"{base}/api/catalog")
    products = [product for product in catalog if SPATIAL.search(
        f"{product.get('category') or ''} {product.get('name') or ''}")]
    if len(products) < 2:
        raise RuntimeError("The ShopSide catalog needs at least two spatially eligible products.")
    first, second = products[:2]

    created = request(person_a, "POST", f"{base}/api/rooms", payload={
        "name": "Person A",
        "title": "A shared home office",
        "initial_request": "Let's set up a shared home office together under $250.",
        "mode": "move_in",
    })
    room = created.get("room") or created
    room_id = room["id"]
    invite = created.get("invite") or room.get("invite")
    if not invite:
        raise RuntimeError("Room was created without an invite link.")

    request(person_b, "POST", f"{base}/api/join/{quote(invite, safe='')}", payload={"name": "Person B"})
    for product, x, z in ((first, -0.55, 0.1), (second, 0.55, -0.15)):
        command(person_a, base, room_id, "placement_upsert", json.dumps({
            "product_id": product["id"], "x": x, "z": z,
        }, separators=(",", ":")))

    command(person_a, base, room_id, "marker_reaction", json.dumps({
        "product_id": first["id"], "reaction": "love",
    }, separators=(",", ":")))
    command(person_b, base, room_id, "marker_reaction", json.dumps({
        "product_id": first["id"], "reaction": "price",
    }, separators=(",", ":")))
    command(person_a, base, room_id, "chat", f"I like the {first['name']} for our workspace.")
    command(person_b, base, room_id, "chat", "Same here. Let's compare it with the other option.")

    print("Prepared ShopSide room with Person A and Person B.")
    print(f"Products: {first['name']} and {second['name']}")
    print(f"Room ID: {room_id}")
    print(f"Judge invite: {base}/?invite={quote(invite, safe='')}")
    print("Open the invite in a browser and enter a new participant name to join the live room.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Could not prepare the room: {exc}", file=sys.stderr)
        sys.exit(1)
