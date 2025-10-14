"""Utility script to pull Beget VPS pricing via public configurator endpoints.

This script mirrors the browser calls captured in the HAR files. It fetches
availability metadata for each region/configuration group combination and then
queries the configurator calculation endpoint to obtain `price_day` and
`price_month` values for a grid of CPU/RAM/Disk combinations.

Notes:
    * Endpoints do not require authentication headers, but we keep the admin
      credentials lookup to make it easy to extend the workflow if token-based
      APIs are discovered later.
    * The numeric grid can become huge. By default we cap the number of values
      we sample per dimension (`MAX_VALUES_PER_DIM`) to keep the request volume
      reasonable while still covering a meaningful spread of plans. Adjust the
      limits or provide explicit value lists if you need a denser matrix.

Usage:
    python3 scripts/beget_pricing_fetch.py

Output:
    Writes `beget_vps_prices.json` in the project root containing an array of
    pricing records. Also prints a short summary to stdout.
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import requests

from app import create_app
from app.core.models import ProviderAdminCredentials
from app.providers.beget.beget_client import BegetAPIClient


logger = logging.getLogger("beget_pricing_fetch")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


BASE_URL = "https://api.beget.com/v1"
HEADERS = {
    "Origin": "https://cp.beget.com",
    "Referer": "https://cp.beget.com/",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}


# Default configurator groups observed in HAR sessions.
# Start with the common group. Additional groups can be appended later.
CONFIG_GROUPS = ["normal_cpu"]

# HAR calls used software_id=6153 (Ubuntu base image). The API expects a value
# even when pricing appears OS-agnostic, so we reuse that constant.
DEFAULT_SOFTWARE_ID = 6153

# Cap the number of samples per dimension to avoid tens of thousands of
# requests. Adjust as needed.
MAX_VALUES_PER_DIM = 12


@dataclass
class GridSettings:
    cpu_values: List[int]
    memory_values: List[int]
    disk_values: List[int]


def load_admin_credentials() -> Optional[Dict[str, str]]:
    """Load stored Beget admin credentials (for future authenticated calls)."""

    app = create_app()
    with app.app_context():
        creds = ProviderAdminCredentials.query.filter_by(provider_type="beget").first()
        if not creds:
            logger.warning("No provider_admin_credentials found for Beget")
            return None

        data = creds.get_credentials()
        username = data.get("username")
        password = data.get("password")
        if not username or not password:
            logger.warning("Stored Beget credentials missing username/password")
            return None

        logger.info("Loaded Beget credentials for user '%s'", username)
        return {"username": username, "password": password}


def fetch_json(session: requests.Session, endpoint: str, params: Optional[Dict] = None) -> Dict:
    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    response = session.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_regions(session: requests.Session) -> List[Dict]:
    data = fetch_json(session, "vps/region")
    return data.get("regions", [])


def generate_value_range(setting: Dict, max_values: int, convert_to_gb: bool = False) -> List[int]:
    """Generate a list of values from configurator ranges with capping."""

    min_value = setting["available_range"]["min"]
    max_value = setting["available_range"]["max"]
    step = setting["step"]

    values = list(range(min_value, max_value + 1, step))
    if convert_to_gb:
        values = [math.ceil(v / 1024) for v in values]

    if len(values) > max_values:
        # Down-sample while keeping endpoints.
        sampled = [values[0], values[-1]]
        if max_values > 2:
            stride = max(1, len(values) // (max_values - 1))
            sampled.extend(values[stride:-stride:stride])
        values = sorted(set(sampled))

    return values


def build_grid(settings: Dict) -> GridSettings:
    cpu_values = generate_value_range(settings["cpu_settings"], MAX_VALUES_PER_DIM)
    memory_values = generate_value_range(settings["memory_settings"], MAX_VALUES_PER_DIM)
    disk_values = generate_value_range(settings["disk_settings"], MAX_VALUES_PER_DIM)
    return GridSettings(cpu_values=cpu_values, memory_values=memory_values, disk_values=disk_values)


def collect_vps_prices(session: requests.Session) -> List[Dict]:
    regions = fetch_regions(session)
    available_regions = [r for r in regions if r.get("available")]
    logger.info("Regions available for configurator: %s", [r["id"] for r in available_regions])

    pricing_records: List[Dict] = []

    for region in available_regions:
        region_id = region["id"]
        for group in CONFIG_GROUPS:
            try:
                info = fetch_json(
                    session,
                    "vps/configurator/info",
                    params={"region": region_id, "configuration_group": group},
                )
            except requests.HTTPError as exc:
                if exc.response.status_code == 404:
                    logger.debug("Configurator info missing for region=%s group=%s", region_id, group)
                    continue
                raise

            settings = info.get("settings")
            if not settings or not info.get("is_available", True):
                logger.debug("Configurator not available for region=%s group=%s", region_id, group)
                continue

            grid = build_grid(settings)
            logger.info(
                "Fetching prices for region=%s group=%s (cpu=%d, memory=%d, disk=%d combinations)",
                region_id,
                group,
                len(grid.cpu_values),
                len(grid.memory_values),
                len(grid.disk_values),
            )

            for cpu in grid.cpu_values:
                for memory in grid.memory_values:
                    for disk in grid.disk_values:
                        params = {
                            "params.cpu_count": cpu,
                            "params.memory": memory,
                            "params.disk_size": disk,
                            "region": region_id,
                            "configuration_group": group,
                            "software_id": DEFAULT_SOFTWARE_ID,
                        }

                        data = fetch_json(session, "vps/configurator/calculation", params=params)
                        success = data.get("success") or {}

                        pricing_records.append(
                            {
                                "provider": "beget",
                                "resource_type": "server",
                                "configuration_group": group,
                                "region": region_id,
                                "cpu_count": cpu,
                                "ram_mb": memory,
                                "disk_mb": disk,
                                "price_day": success.get("price_day"),
                                "price_month": success.get("price_month"),
                                "raw": success,
                            }
                        )

    return pricing_records


def main():
    load_admin_credentials()  # Currently unused but kept for future authenticated flows.

    session = requests.Session()
    session.headers.update(HEADERS)

    creds = load_admin_credentials()
    if creds:
        client = BegetAPIClient(creds["username"], creds["password"])
        if client.authenticate() and client.access_token:
            session.headers["Authorization"] = f"Bearer {client.access_token}"
            logger.info("Authenticated HTTP session with Bearer token")
        else:
            logger.warning("Failed to authenticate with Beget API; proceeding without token")
    else:
        logger.warning("No credentials found; attempting unauthenticated requests")

    logger.info("Collecting Beget VPS price matrix...")
    pricing = collect_vps_prices(session)
    logger.info("Collected %d pricing records", len(pricing))

    output_path = Path("beget_vps_prices.json")
    output_path.write_text(json.dumps(pricing, ensure_ascii=False, indent=2))
    logger.info("Pricing data written to %s", output_path.resolve())


if __name__ == "__main__":
    main()

