"""Fixtures for integration tests — real MA server, real provider."""

from __future__ import annotations

import asyncio
import itertools
import logging
import pathlib
from collections.abc import AsyncGenerator

import aiohttp
import pytest
from music_assistant_models.config_entries import ProviderConfig
from music_assistant_models.enums import EventType

from music_assistant.mass import MusicAssistant

_port_counter = itertools.count(18100)


async def _wait_for_player(
    mass: MusicAssistant, player_id: str, timeout: float = 10.0
) -> None:
    """Wait until a player with the given ID is registered in MA."""
    if mass.players.get(player_id) is not None:
        return

    flag = asyncio.Event()

    def _on_player_added(event):  # noqa: ANN001
        if event.object_id == player_id:
            flag.set()

    release_cb = mass.subscribe(_on_player_added, EventType.PLAYER_ADDED)
    try:
        await asyncio.wait_for(flag.wait(), timeout=timeout)
    finally:
        release_cb()


@pytest.fixture
async def mass(tmp_path: pathlib.Path) -> AsyncGenerator[MusicAssistant, None]:
    """Start a real MusicAssistant instance with temporary storage."""
    storage_path = tmp_path / "data"
    cache_path = tmp_path / "cache"
    storage_path.mkdir(parents=True)
    cache_path.mkdir(parents=True)

    logging.getLogger("aiosqlite").level = logging.INFO

    mass_instance = MusicAssistant(str(storage_path), str(cache_path))
    await mass_instance.start()

    try:
        yield mass_instance
    finally:
        await mass_instance.stop()


@pytest.fixture
def msx_port() -> int:
    """Return a unique port for the MSX HTTP server."""
    return next(_port_counter)


@pytest.fixture
async def msx_provider(
    mass: MusicAssistant, msx_port: int
) -> AsyncGenerator[ProviderConfig, None]:
    """Load the MSX Bridge provider into the running MA instance."""
    config = await mass.config.save_provider_config(
        "msx_bridge",
        {"http_port": msx_port, "output_format": "mp3"},
    )
    await _wait_for_player(mass, "msx_default")
    yield config
    await mass.config.remove_provider_config(config.instance_id)


@pytest.fixture
async def msx_http_client(
    msx_port: int, msx_provider: ProviderConfig
) -> AsyncGenerator[aiohttp.ClientSession, None]:
    """Return an aiohttp session pointing at the MSX HTTP server."""
    async with aiohttp.ClientSession(
        base_url=f"http://127.0.0.1:{msx_port}"
    ) as session:
        yield session
