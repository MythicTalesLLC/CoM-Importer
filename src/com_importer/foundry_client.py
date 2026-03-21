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

from .foundry_export import FoundryJsonExporter

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
        export_fallback: bool = True,
        export_dir: str | None = None,
    ) -> None:
        """
        Initialize REST client.

        Args:
            api_url: Base URL of Foundry REST API relay (e.g., https://foundryvtt-rest-api-relay.fly.dev)
            api_key: API authentication key (x-api-key header)
            client_id: Client ID identifying the Foundry world on the relay
            world_name: Name of the Foundry world/game
            export_fallback: If True, export JSON when REST API items fail (default: True)
            export_dir: Directory for fallback exports (defaults to ~/Downloads)
        """
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.client_id = client_id
        self.world_name = world_name
        self.export_fallback = export_fallback
        self.export_dir = export_dir
        self.session = requests.Session()
        self.session.headers.update(
            {
                "x-api-key": api_key,
                "x-client-id": client_id,
                "Content-Type": "application/json",
            }
        )
        self._full_actor_data = None  # Store for export fallback

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

        Creates actor first, then adds items separately.
        If items fail to persist (known REST API limitation), exports JSON
        for manual import as a fallback.

        Args:
            actor_data: Foundry actor object

        Returns:
            Actor ID

        Raises:
            Exception: If creation fails
        """
        # Store for potential export fallback
        self._full_actor_data = actor_data.copy()

        print(f"\n[TRACE] create_actor() called for: {actor_data.get('name')}")
        print(f"[TRACE] Items in actor_data: {len(actor_data.get('items', []))}")

        logger.info(f"create_actor() called for: {actor_data.get('name')}")

        # Build actor data for creation - send ONLY minimal fields to REST API
        create_actor_data = {
            "name": actor_data.get("name", "New Actor"),
            "type": actor_data.get("type", "threat"),
            "img": actor_data.get("img", "icons/svg/mystery-man.svg"),
        }

        # Send system fields but stripped to only what REST API supports
        if actor_data.get("system"):
            system = actor_data["system"]
            # REST API might only support specific system fields
            create_actor_data["system"] = {
                "description": system.get("description", ""),
                "biography": system.get("biography", ""),
                "gmnotes": system.get("gmnotes", ""),
                "mythos": system.get("mythos", ""),
                "logos": system.get("logos", ""),
                "alias": system.get("alias", "?????"),
                "useAlias": system.get("useAlias", True),
                "locked": system.get("locked", False),
                "version": system.get("version", "3.0.0"),
            }

        endpoint = urljoin(self.api_url, f"/create?clientId={self.client_id}")
        payload = {
            "entityType": "Actor",
            "collection": "actors",
            "data": create_actor_data,
        }
        logger.debug(f"Posting to {endpoint}")
        print("[TRACE] Creating actor (embedded items NOT supported by REST API)")
        response = self.session.post(endpoint, json=payload, timeout=30)
        print(f"[TRACE] Actor creation response: {response.status_code}")
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

        # Now attempt to add items separately
        items_failed = False
        if actor_id and actor_data.get("items"):
            items = actor_data.get("items", [])
            print(f"[TRACE] Attempting to add {len(items)} items to actor {actor_id}")
            logger.info(f"Adding {len(items)} items to actor {actor_id}")
            for i, item_data in enumerate(items):
                try:
                    print(f"[TRACE] Adding item {i+1}/{len(items)}: {item_data.get('name')}")
                    self.add_item_to_actor(actor_id, item_data)
                    item_name = item_data.get("name", "Unknown")
                    print(f"[TRACE] ✓ Item {i+1} added: {item_name}")
                    logger.info(f"  Item {i+1}/{len(items)}: {item_name}")
                except Exception as e:
                    # Log but don't fail - actor was created
                    print(f"[TRACE] ✗ Item {i+1} failed: {str(e)[:200]}")
                    logger.error(f"  Failed to add item {i+1}: {str(e)[:200]}")
                    items_failed = True
        else:
            if actor_id:
                print(f"[TRACE] No items to add (actor_data.items = {actor_data.get('items')})")
            else:
                print("[TRACE] No actor_id or items")

        # If items failed and export fallback is enabled, provide export option
        if items_failed and self.export_fallback:
            print("[TRACE] Items failed to persist via REST API")
            print("[TRACE] Exporting as JSON for manual import...")
            try:
                export_path = FoundryJsonExporter.export_actor_to_file(
                    self._full_actor_data,
                    export_dir=self.export_dir,
                )
                print(f"[TRACE] ✓ JSON exported to: {export_path}")
                print("[TRACE] You can manually import this file into Foundry")
                logger.info(f"Exported JSON fallback to: {export_path}")
            except Exception as e:
                print(f"[TRACE] ✗ Export failed: {str(e)}")
                logger.error(f"Export fallback failed: {str(e)}")

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
        item_name = item_data.get("name", "Unknown")
        item_type = item_data.get("type", "unknown")
        print(f"[DEBUG] Adding {item_type} item to {actor_id}: {item_name}")
        print(f"[DEBUG] Payload keys: {list(payload.get('data', {}).keys())}")
        response = self.session.post(endpoint, json=payload, timeout=30)
        print(f"[DEBUG] Response: {response.status_code}")
        print(f"[DEBUG] Response text: {response.text[:300]}")
        if response.status_code not in (200, 201):
            logger.error(
                f"Failed to add item {item_name}: HTTP {response.status_code} - {response.text}"
            )
            print(f"[ERROR] Failed to add item: HTTP {response.status_code}")
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
        api_url: str,
        api_key: str,
        client_id: str,
        world_name: str,
        export_fallback: bool = True,
        export_dir: str | None = None,
    ) -> FoundryRestClient:
        """
        Create a REST API client.

        Args:
            api_url: Base URL of Foundry REST API relay
            api_key: API authentication key
            client_id: Client ID identifying the Foundry world
            world_name: Name of the Foundry world
            export_fallback: If True, export JSON when items fail to persist
            export_dir: Directory for fallback exports

        Returns:
            FoundryRestClient instance
        """
        return FoundryRestClient(
            api_url=api_url,
            api_key=api_key,
            client_id=client_id,
            world_name=world_name,
            export_fallback=export_fallback,
            export_dir=export_dir,
        )

    @staticmethod
    def create_local_client(foundry_data_dir: str, world_name: str) -> FoundryLocalClient:
        """Create a local filesystem client."""
        return FoundryLocalClient(
            foundry_data_dir=foundry_data_dir,
            world_name=world_name,
        )
