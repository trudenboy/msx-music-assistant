"""Tests for MSX mappers."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from provider.msx_bridge.mappers import map_track_to_msx, map_album_to_msx
from music_assistant_models.media_items import Track, Album


@pytest.fixture
def mock_provider():
    """Create a mock provider."""
    provider = MagicMock()
    provider.mass.metadata.get_image_url.return_value = "http://image.url"
    return provider


def test_map_track_to_msx(mock_provider) -> None:
    """Test mapping a track to MSX item."""
    track = MagicMock(spec=Track)
    track.name = "Test Track"
    track.uri = "library://track/1"
    track.duration = 125
    track.artist_str = "Test Artist"
    track.image = "some_image"

    item = map_track_to_msx(
        track=track,
        prefix="http://localhost",
        player_id="msx_123",
        provider=mock_provider,
        device_param="device_id=abc"
    )

    assert item.title == "Test Track"
    assert item.label == "Test Artist · 2:05"
    assert item.image == "http://image.url"
    assert "audio:http://localhost/msx/audio/msx_123?uri=library%3A%2F%2Ftrack%2F1&device_id=abc" == item.action


@pytest.mark.asyncio
async def test_map_album_to_msx(mock_provider) -> None:
    """Test mapping an album to MSX item."""
    album = MagicMock(spec=Album)
    album.name = "Test Album"
    album.item_id = "1"
    album.provider = "library"
    album.artist_str = "Test Artist"
    album.image = "album_image"

    item = await map_album_to_msx(
        album=album,
        prefix="http://localhost",
        provider=mock_provider,
        device_param="device_id=abc"
    )

    assert item.title == "Test Album"
    assert item.label == "Test Artist"
    assert item.image == "http://image.url"
    assert "content:http://localhost/msx/albums/1/tracks.json?provider=library&device_id=abc" == item.action
