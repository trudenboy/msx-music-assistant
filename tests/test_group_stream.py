"""Tests for group streaming modes (SharedGroupStream and MA Redirect)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from unittest.mock import Mock


from music_assistant.providers.msx_bridge.constants import (
    GROUP_STREAM_MODE_INDEPENDENT,
    GROUP_STREAM_MODE_REDIRECT,
    GROUP_STREAM_MODE_SHARED,
)
from music_assistant.providers.msx_bridge.provider import (
    MSXBridgeProvider,
    SharedGroupStream,
)


# --- SharedGroupStream Tests ---


async def test_shared_stream_basic_flow() -> None:
    """SharedGroupStream should produce chunks and deliver to subscriber."""
    stream = SharedGroupStream("group_1", "http://example.com/track.mp3")

    # Create async chunk generator
    async def chunk_gen() -> AsyncIterator[bytes]:
        yield b"chunk1"
        yield b"chunk2"
        yield b"chunk3"

    await stream.start(chunk_gen())

    # Subscribe and collect chunks
    chunks = []
    async for chunk in stream.subscribe("player_1"):
        chunks.append(chunk)

    # Chunks may include catch-up buffer duplicates, so check contents
    assert b"chunk1" in chunks
    assert b"chunk2" in chunks
    assert b"chunk3" in chunks
    assert stream.finished


async def test_shared_stream_multiple_subscribers() -> None:
    """SharedGroupStream should deliver same chunks to multiple subscribers."""
    stream = SharedGroupStream("group_1", "http://example.com/track.mp3")

    produced_chunks = [b"a", b"b", b"c", b"d", b"e"]
    chunk_idx = 0

    async def chunk_gen() -> AsyncIterator[bytes]:
        nonlocal chunk_idx
        for chunk in produced_chunks:
            chunk_idx += 1
            yield chunk
            await asyncio.sleep(0.01)  # Small delay to allow subscribers to catch up

    await stream.start(chunk_gen())

    # Subscribe two players
    async def collect(player_id: str) -> list[bytes]:
        result = []
        async for chunk in stream.subscribe(player_id):
            result.append(chunk)
        return result

    player1_task = asyncio.create_task(collect("player_1"))
    player2_task = asyncio.create_task(collect("player_2"))

    chunks1, chunks2 = await asyncio.gather(player1_task, player2_task)

    # Both should get all chunks (including catch-up buffer)
    assert b"a" in chunks1
    assert b"e" in chunks1
    assert b"a" in chunks2
    assert b"e" in chunks2


async def test_shared_stream_late_joiner() -> None:
    """Late subscriber should receive buffered chunks first."""
    stream = SharedGroupStream("group_1", "http://example.com/track.mp3")

    chunk_event = asyncio.Event()
    all_produced = asyncio.Event()

    async def chunk_gen() -> AsyncIterator[bytes]:
        yield b"early1"
        yield b"early2"
        chunk_event.set()  # Signal that early chunks are produced
        await asyncio.sleep(0.05)  # Wait for late joiner
        yield b"late1"
        all_produced.set()

    await stream.start(chunk_gen())

    # Wait for early chunks to be buffered
    await chunk_event.wait()
    await asyncio.sleep(0.02)  # Ensure chunks are in buffer

    # Late joiner subscribes
    chunks = []
    async for chunk in stream.subscribe("late_player"):
        chunks.append(chunk)
        if all_produced.is_set() and len(chunks) >= 3:
            break

    # Should have early chunks from buffer + late chunk
    assert b"early1" in chunks
    assert b"early2" in chunks


async def test_shared_stream_stop() -> None:
    """stop() should cancel producer and set finished flag."""
    stream = SharedGroupStream("group_1", "http://example.com/track.mp3")

    async def infinite_gen() -> AsyncIterator[bytes]:
        while True:
            yield b"chunk"
            await asyncio.sleep(0.1)

    await stream.start(infinite_gen())
    await asyncio.sleep(0.05)

    await stream.stop()

    assert stream.finished
    assert stream.producer_task is not None
    assert stream.producer_task.cancelled() or stream.producer_task.done()


async def test_shared_stream_subscriber_count() -> None:
    """subscriber_count should track active subscribers."""
    stream = SharedGroupStream("group_1", "http://example.com/track.mp3")

    produced = asyncio.Event()

    async def chunk_gen() -> AsyncIterator[bytes]:
        yield b"chunk"
        produced.set()
        await asyncio.sleep(1)  # Keep stream alive

    await stream.start(chunk_gen())
    await produced.wait()

    assert stream.subscriber_count == 0

    # Start subscriber
    sub_task = asyncio.create_task(anext(aiter(stream.subscribe("player_1"))))
    await asyncio.sleep(0.05)
    assert stream.subscriber_count == 1

    sub_task.cancel()
    await asyncio.sleep(0.05)


# --- Provider Group Stream Methods Tests ---


async def test_provider_is_shared_stream_mode(
    mass_mock: Mock, manifest_mock: Mock
) -> None:
    """is_shared_stream_mode should return True when configured."""
    config = Mock()
    config.name = "MSX Bridge"
    config.instance_id = "test"
    config.enabled = True
    config.get_value = Mock(
        side_effect=lambda key, default=None: {
            "http_port": 0,  # Use port 0 for auto-select
            "group_stream_mode": GROUP_STREAM_MODE_SHARED,
            "log_level": "GLOBAL",
        }.get(key, default)
    )

    prov = MSXBridgeProvider(mass_mock, manifest_mock, config, set())
    await prov.handle_async_init()

    assert prov.is_shared_stream_mode()
    assert not prov.is_redirect_stream_mode()

    if prov.http_server:
        await prov.http_server.stop()


async def test_provider_is_redirect_stream_mode(
    mass_mock: Mock, manifest_mock: Mock
) -> None:
    """is_redirect_stream_mode should return True when configured."""
    config = Mock()
    config.name = "MSX Bridge"
    config.instance_id = "test"
    config.enabled = True
    config.get_value = Mock(
        side_effect=lambda key, default=None: {
            "http_port": 0,  # Use port 0 for auto-select
            "group_stream_mode": GROUP_STREAM_MODE_REDIRECT,
            "log_level": "GLOBAL",
        }.get(key, default)
    )

    prov = MSXBridgeProvider(mass_mock, manifest_mock, config, set())
    await prov.handle_async_init()

    assert prov.is_redirect_stream_mode()
    assert not prov.is_shared_stream_mode()

    if prov.http_server:
        await prov.http_server.stop()


async def test_provider_default_independent_mode(
    mass_mock: Mock, manifest_mock: Mock
) -> None:
    """Default mode should be independent (neither shared nor redirect)."""
    config = Mock()
    config.name = "MSX Bridge"
    config.instance_id = "test"
    config.enabled = True
    config.get_value = Mock(
        side_effect=lambda key, default=None: {
            "http_port": 0,  # Use port 0 for auto-select
            "log_level": "GLOBAL",
        }.get(key, default)
    )

    prov = MSXBridgeProvider(mass_mock, manifest_mock, config, set())
    await prov.handle_async_init()

    assert not prov.is_shared_stream_mode()
    assert not prov.is_redirect_stream_mode()
    assert prov.group_stream_mode == GROUP_STREAM_MODE_INDEPENDENT

    if prov.http_server:
        await prov.http_server.stop()


async def test_provider_get_group_id_for_leader(provider: MSXBridgeProvider) -> None:
    """get_group_id_for_player should return player_id for leader."""
    player = Mock()
    player.player_id = "msx_leader"
    player.synced_to = None
    player.group_members = ["msx_leader", "msx_member1", "msx_member2"]

    group_id = provider.get_group_id_for_player(player)
    assert group_id == "msx_leader"


async def test_provider_get_group_id_for_member(provider: MSXBridgeProvider) -> None:
    """get_group_id_for_player should return leader's ID for member."""
    player = Mock()
    player.player_id = "msx_member1"
    player.synced_to = "msx_leader"
    player.group_members = []

    group_id = provider.get_group_id_for_player(player)
    assert group_id == "msx_leader"


async def test_provider_get_group_id_for_solo(provider: MSXBridgeProvider) -> None:
    """get_group_id_for_player should return None for solo player."""
    player = Mock()
    player.player_id = "msx_solo"
    player.synced_to = None
    player.group_members = ["msx_solo"]  # Only itself

    group_id = provider.get_group_id_for_player(player)
    assert group_id is None


async def test_provider_get_or_create_shared_stream(
    provider: MSXBridgeProvider,
) -> None:
    """get_or_create_shared_stream should create new stream."""

    async def chunk_gen() -> AsyncIterator[bytes]:
        yield b"test"

    stream = await provider.get_or_create_shared_stream(
        "group_1", "http://example.com/track.mp3", chunk_gen()
    )

    assert stream is not None
    assert stream.group_id == "group_1"
    assert "group_1" in provider._shared_streams

    await stream.stop()


async def test_provider_reuse_existing_shared_stream(
    provider: MSXBridgeProvider,
) -> None:
    """get_or_create_shared_stream should reuse existing stream for same media."""

    async def chunk_gen() -> AsyncIterator[bytes]:
        yield b"test"
        await asyncio.sleep(1)

    stream1 = await provider.get_or_create_shared_stream(
        "group_1", "http://example.com/track.mp3", chunk_gen()
    )

    # Request same stream again
    stream2 = await provider.get_or_create_shared_stream(
        "group_1", "http://example.com/track.mp3", chunk_gen()
    )

    assert stream1 is stream2

    await stream1.stop()


async def test_provider_replace_stream_on_new_media(
    provider: MSXBridgeProvider,
) -> None:
    """get_or_create_shared_stream should replace stream for different media."""

    async def chunk_gen() -> AsyncIterator[bytes]:
        yield b"test"
        await asyncio.sleep(0.5)

    stream1 = await provider.get_or_create_shared_stream(
        "group_1", "http://example.com/track1.mp3", chunk_gen()
    )
    stream1_id = id(stream1)

    await asyncio.sleep(0.05)

    # Request stream for different media
    stream2 = await provider.get_or_create_shared_stream(
        "group_1", "http://example.com/track2.mp3", chunk_gen()
    )

    assert id(stream2) != stream1_id
    assert stream1.finished  # Old stream should be stopped

    await stream2.stop()


async def test_provider_remove_shared_stream(provider: MSXBridgeProvider) -> None:
    """remove_shared_stream should cleanup stream."""

    async def chunk_gen() -> AsyncIterator[bytes]:
        yield b"test"
        await asyncio.sleep(1)

    await provider.get_or_create_shared_stream(
        "group_1", "http://example.com/track.mp3", chunk_gen()
    )
    assert "group_1" in provider._shared_streams

    provider.remove_shared_stream("group_1")

    assert "group_1" not in provider._shared_streams


async def test_provider_cleanup_shared_streams(provider: MSXBridgeProvider) -> None:
    """cleanup_shared_streams should stop all streams."""

    async def chunk_gen() -> AsyncIterator[bytes]:
        yield b"test"
        await asyncio.sleep(1)

    await provider.get_or_create_shared_stream(
        "group_1", "http://example.com/track1.mp3", chunk_gen()
    )
    await provider.get_or_create_shared_stream(
        "group_2", "http://example.com/track2.mp3", chunk_gen()
    )

    assert len(provider._shared_streams) == 2

    await provider.cleanup_shared_streams()

    assert len(provider._shared_streams) == 0


# --- MA Redirect Tests ---


async def test_provider_get_ma_stream_url_success(
    provider: MSXBridgeProvider,
) -> None:
    """get_ma_stream_url should return URL when all data available."""
    media = Mock()
    media.queue_item_id = "queue_item_123"
    media.source_id = "queue_456"

    queue = Mock()
    queue.session_id = "session_789"
    provider.mass.player_queues.get = Mock(return_value=queue)
    provider.mass.webserver.host = "192.168.1.10"
    provider.mass.webserver.port = 8097

    url = await provider.get_ma_stream_url(media, "mp3")

    assert url is not None
    assert "queue_item_123" in url
    assert "queue_456" in url
    assert ".mp3" in url


async def test_provider_get_ma_stream_url_no_queue_item(
    provider: MSXBridgeProvider,
) -> None:
    """get_ma_stream_url should return None when queue_item_id missing."""
    media = Mock()
    media.queue_item_id = None
    media.source_id = "queue_456"

    url = await provider.get_ma_stream_url(media, "mp3")
    assert url is None


async def test_provider_get_ma_stream_url_no_source(
    provider: MSXBridgeProvider,
) -> None:
    """get_ma_stream_url should return None when source_id missing."""
    media = Mock()
    media.queue_item_id = "queue_item_123"
    media.source_id = None

    url = await provider.get_ma_stream_url(media, "mp3")
    assert url is None


async def test_provider_get_ma_stream_url_no_queue(
    provider: MSXBridgeProvider,
) -> None:
    """get_ma_stream_url should return None when queue not found."""
    media = Mock()
    media.queue_item_id = "queue_item_123"
    media.source_id = "queue_456"

    provider.mass.player_queues.get = Mock(return_value=None)

    url = await provider.get_ma_stream_url(media, "mp3")
    assert url is None
