"""
Foundry VTT integration clients for both REST API and local filesystem.

Supports remote Foundry instances via REST API and local Foundry installations.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests

logger = logging.getLogger(__name__)


class FoundryClient(ABC):
    """Abstract base for Foundry clients."""

    @abstractmethod
    def create_actor(self, actor_data: dict[str, Any]) -> str:
        """Create a new actor. Returns the actor ID."""

    @abstractmethod
    def update_actor(self, actor_id: str, actor_data: dict[str, Any]) -> None:
        """Update an existing actor."""

    @abstractmethod
    def add_item_to_actor(self, actor_id: str, item_data: dict[str, Any]) -> None:
        """Add an item (move, spectrum, tag, etc.) to an actor."""

    @abstractmethod
    def test_connection(self) -> tuple[bool, str]:
        """Test the connection. Returns (success, message)."""


class FoundryRestClient(FoundryClient):
    """Client for remote Foundry instances via REST API relay.

    Works with foundryvtt-rest-api-relay: https://github.com/ThreeHats/foundryvtt-rest-api-relay
    """

    def __init__(
        self,
        api_url: str,
        api_key: str,
        client_id: str,
        world_name: str,
    ) -> None:
        """
        Initialize REST client.

        Args:
            api_url: Base URL of Foundry REST API relay (e.g., https://foundryvtt-rest-api-relay.fly.dev)
            api_key: API authentication key (x-api-key header)
            client_id: Client ID identifying the Foundry world on the relay
            world_name: Name of the Foundry world/game
        """
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.client_id = client_id
        self.world_name = world_name
        self.session = requests.Session()
        self.session.headers.update(
            {
                "x-api-key": api_key,
                "x-client-id": client_id,
                "Content-Type": "application/json",
            }
        )

    def test_connection(self) -> tuple[bool, str]:
        """Test connection to Foundry API relay.

        Attempts to connect to /clients endpoint to verify the relay is running.
        """
        try:
            # Test connection to /clients endpoint (lists connected Foundry worlds)
            endpoint = urljoin(self.api_url, "/clients")
            response = self.session.get(endpoint, timeout=10)

            if response.status_code == 200:
                data = response.json()
                # Response is a dict with "total" and "clients" keys
                if isinstance(data, dict):
                    total = data.get("total", 0)
                    clients = data.get("clients", [])
                    if total > 0 and len(clients) > 0:
                        world = clients[0].get("worldTitle", "Unknown")
                        return True, f"Connected to '{world}' ({total} client(s))"
                    return True, "API relay responding (no clients connected yet)"
                # Fallback for alternative response formats
                if isinstance(data, list) and len(data) > 0:
                    return True, f"Connected. Found {len(data)} Foundry client(s)"

            if response.status_code == 401:
                return False, "Authentication failed: Invalid API key"

            return False, f"HTTP {response.status_code}: {response.text[:200]}"
        except requests.RequestException as e:
            return False, f"Connection failed: {str(e)}"

    def create_actor(self, actor_data: dict[str, Any]) -> str:
        """
        Create a new actor in Foundry via REST API.

        Creates actor with all fields including items in initial creation.
        This matches how the local filesystem client works.

        Args:
            actor_data: Foundry actor object (includes items array)

        Returns:
            Actor ID

        Raises:
            Exception: If creation fails
        """
        print(f"\n[TRACE] create_actor() called for: {actor_data.get('name')}")
        print(f"[TRACE] Items in actor_data: {len(actor_data.get('items', []))}")

        logger.info(f"create_actor() called for: {actor_data.get('name')}")

        # Send entire actor data including items in the initial creation
        # This matches how the local filesystem client works
        endpoint = urljoin(self.api_url, f"/create?clientId={self.client_id}")
        payload = {
            "entityType": "Actor",
            "collection": "actors",
            "data": actor_data,
        }
        logger.debug(f"Posting to {endpoint}")
        print(f"[TRACE] Payload includes {len(actor_data.get('items', []))} items")
        response = self.session.post(endpoint, json=payload, timeout=30)
        if response.status_code not in (200, 201):
            raise Exception(
                f"Failed to create actor: HTTP {response.status_code} - {response.text}"
            )
        result = response.json()
        # REST API returns entity nested within response
        entity = result.get("entity", {})
        actor_id = entity.get("_id", result.get("_id", result.get("id", "")))

        print(f"[TRACE] Actor created with ID: {actor_id}")
        logger.info(f"Actor created with ID: {actor_id}")
        print(f"[TRACE] create_actor() complete for {actor_id}\n")
        logger.info(f"create_actor() complete for {actor_id}")
        return actor_id

    def update_actor(self, actor_id: str, actor_data: dict[str, Any]) -> None:
        """
        Update an existing actor via REST API.

        Args:
            actor_id: Foundry actor ID
            actor_data: Updated actor object

        Raises:
            Exception: If update fails
        """
        endpoint = urljoin(self.api_url, f"/update?clientId={self.client_id}")
        payload = {
            "entityType": "Actor",
            "collection": "actors",
            "_id": actor_id,
            "data": actor_data,
        }
        response = self.session.patch(endpoint, json=payload, timeout=30)
        if response.status_code not in (200, 204):
            raise Exception(
                f"Failed to update actor: HTTP {response.status_code} - {response.text}"
            )

    def add_item_to_actor(self, actor_id: str, item_data: dict[str, Any]) -> None:
        """
        Add an item to an actor via REST API.

        Args:
            actor_id: Foundry actor ID
            item_data: Item object (move, spectrum, tag, status, etc.)

        Raises:
            Exception: If addition fails
        """
        endpoint = urljoin(self.api_url, f"/create?clientId={self.client_id}")

        # Remove _id - REST API will generate it
        item_for_creation = {k: v for k, v in item_data.items() if k != "_id"}

        payload = {
            "entityType": "Item",
            "collection": "items",
            "data": {**item_for_creation, "parent": actor_id},
        }
        logger.debug(f"Adding item: {item_data.get('name')} (type: {item_data.get('type')})")
        print(f"[DEBUG] Adding item to {actor_id}: {item_data.get('name')}")  # Console output
        response = self.session.post(endpoint, json=payload, timeout=30)
        print(f"[DEBUG] Response: {response.status_code}")  # Console output
        if response.status_code not in (200, 201):
            logger.error(f"Failed to add item {item_data.get('name')}: HTTP {response.status_code}")
            print(f"[ERROR] Failed to add item: HTTP {response.status_code}")  # Console output
            raise Exception(f"Failed to add item: HTTP {response.status_code} - {response.text}")


class FoundryLocalClient(FoundryClient):
    """Client for local Foundry installations via filesystem."""

    def __init__(self, foundry_data_dir: str, world_name: str) -> None:
        """
        Initialize local filesystem client.

        Args:
            foundry_data_dir: Path to Foundry data directory (typically ~/.foundry/data)
            world_name: Name of the world
        """
        self.foundry_data_dir = Path(foundry_data_dir)
        self.world_name = world_name
        self.world_path = self.foundry_data_dir / "worlds" / world_name
        self.actors_path = self.world_path / "data" / "actors"

    def test_connection(self) -> tuple[bool, str]:
        """Test connection to local Foundry installation."""
        if not self.foundry_data_dir.exists():
            return False, f"Foundry data dir not found: {self.foundry_data_dir}"
        if not self.world_path.exists():
            return False, f"World '{self.world_name}' not found in {self.foundry_data_dir}"
        if not self.actors_path.exists():
            return (
                False,
                f"Actors directory not found: {self.actors_path}",
            )
        return True, "Connection successful"

    def create_actor(self, actor_data: dict[str, Any]) -> str:
        """
        Create an actor by writing to filesystem.

        Args:
            actor_data: Foundry actor object

        Returns:
            Actor ID

        Raises:
            Exception: If creation fails
        """
        actor_id = actor_data.get("_id")
        if not actor_id:
            raise ValueError("actor_data must have _id field")

        # Check for duplicate names
        existing = self._find_actor_by_name(actor_data.get("name", ""))
        if existing:
            raise Exception(f"Actor with name '{actor_data['name']}' already exists")

        actor_file = self.actors_path / f"{actor_id}.json"
        if actor_file.exists():
            raise Exception(f"Actor file already exists: {actor_file}")

        # Ensure parent directory exists
        self.actors_path.mkdir(parents=True, exist_ok=True)

        # Write actor file
        with open(actor_file, "w", encoding="utf-8") as f:
            json.dump(actor_data, f, indent=2, ensure_ascii=False)

        return actor_id

    def update_actor(self, actor_id: str, actor_data: dict[str, Any]) -> None:
        """
        Update an existing actor.

        Args:
            actor_id: Foundry actor ID
            actor_data: Updated actor object

        Raises:
            Exception: If update fails
        """
        actor_file = self.actors_path / f"{actor_id}.json"
        if not actor_file.exists():
            raise Exception(f"Actor not found: {actor_id}")

        # Load existing data and merge
        with open(actor_file, encoding="utf-8") as f:
            existing_data = json.load(f)

        # Deep merge, preserving items if not provided
        merged_data = {**existing_data, **actor_data}
        if "items" not in actor_data and "items" in existing_data:
            merged_data["items"] = existing_data["items"]

        with open(actor_file, "w", encoding="utf-8") as f:
            json.dump(merged_data, f, indent=2, ensure_ascii=False)

    def add_item_to_actor(self, actor_id: str, item_data: dict[str, Any]) -> None:
        """
        Add an item to an actor by modifying its JSON file.

        Args:
            actor_id: Foundry actor ID
            item_data: Item object

        Raises:
            Exception: If operation fails
        """
        actor_file = self.actors_path / f"{actor_id}.json"
        if not actor_file.exists():
            raise Exception(f"Actor not found: {actor_id}")

        with open(actor_file, encoding="utf-8") as f:
            actor_data = json.load(f)

        if "items" not in actor_data:
            actor_data["items"] = []

        # Ensure item has an ID
        if "_id" not in item_data:
            import uuid

            item_data["_id"] = str(uuid.uuid4())

        actor_data["items"].append(item_data)

        with open(actor_file, "w", encoding="utf-8") as f:
            json.dump(actor_data, f, indent=2, ensure_ascii=False)

    def _find_actor_by_name(self, name: str) -> str | None:
        """Find actor ID by name. Returns actor ID or None."""
        if not self.actors_path.exists():
            return None

        for actor_file in self.actors_path.glob("*.json"):
            try:
                with open(actor_file, encoding="utf-8") as f:
                    actor_data = json.load(f)
                    if actor_data.get("name") == name:
                        return actor_data.get("_id")
            except (OSError, json.JSONDecodeError):
                continue

        return None


class FoundryClientFactory:
    """Factory for creating appropriate Foundry client."""

    @staticmethod
    def create_rest_client(
        api_url: str, api_key: str, client_id: str, world_name: str
    ) -> FoundryRestClient:
        """Create a REST API client."""
        return FoundryRestClient(
            api_url=api_url,
            api_key=api_key,
            client_id=client_id,
            world_name=world_name,
        )

    @staticmethod
    def create_local_client(foundry_data_dir: str, world_name: str) -> FoundryLocalClient:
        """Create a local filesystem client."""
        return FoundryLocalClient(
            foundry_data_dir=foundry_data_dir,
            world_name=world_name,
        )
