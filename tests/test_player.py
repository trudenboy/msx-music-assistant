"""Tests for MSXPlayer."""

from __future__ import annotations

from unittest.mock import Mock, patch

from music_assistant_models.enums import PlaybackState, PlayerFeature, PlayerType
from music_assistant_models.player import PlayerMedia

from music_assistant.providers.msx_bridge.player import MSXPlayer


# --- Initialization and properties ---


def test_init_defaults(player: MSXPlayer) -> None:
    """MSXPlayer should have correct default attributes."""
    assert player._attr_name == "Test TV"
    assert player._attr_type == PlayerType.PLAYER
    assert PlayerFeature.PAUSE in player._attr_supported_features
    assert PlayerFeature.VOLUME_SET in player._attr_supported_features
    assert player._attr_available is True
    assert player._attr_powered is True
    assert player._attr_volume_level == 100
    assert player.output_format == "mp3"


def test_init_custom_params(provider: object) -> None:
    """MSXPlayer should accept custom name and output_format."""
    p = MSXPlayer(provider, "msx_custom", name="Living Room TV", output_format="flac")
    p.update_state = Mock()
    assert p._attr_name == "Living Room TV"
    assert p.output_format == "flac"


def test_needs_poll_always_true(player: MSXPlayer) -> None:
    """needs_poll should always return True."""
    assert player.needs_poll is True


def test_poll_interval_playing(player: MSXPlayer) -> None:
    """poll_interval should return 5 when playing."""
    player._attr_playback_state = PlaybackState.PLAYING
    assert player.poll_interval == 5


def test_poll_interval_not_playing(player: MSXPlayer) -> None:
    """poll_interval should return 30 when idle or paused."""
    player._attr_playback_state = PlaybackState.IDLE
    assert player.poll_interval == 30
    player._attr_playback_state = PlaybackState.PAUSED
    assert player.poll_interval == 30


# --- Playback ---


async def test_play_media(player: MSXPlayer) -> None:
    """play_media should store stream URL, set state to PLAYING, and reset elapsed."""
    media = Mock(spec=PlayerMedia)
    media.uri = "http://ma-server/stream/12345"

    await player.play_media(media)

    assert player.current_stream_url == "http://ma-server/stream/12345"
    assert player._attr_playback_state == PlaybackState.PLAYING
    assert player._attr_elapsed_time == 0
    assert player._attr_elapsed_time_last_updated is not None
    assert player._attr_current_media is media
    player.update_state.assert_called()


async def test_play_resume(player: MSXPlayer) -> None:
    """play() should set state to PLAYING and update timestamp without touching elapsed."""
    player._attr_playback_state = PlaybackState.PAUSED
    player._attr_elapsed_time = 42.0

    await player.play()

    assert player._attr_playback_state == PlaybackState.PLAYING
    assert player._attr_elapsed_time == 42.0  # untouched
    assert player._attr_elapsed_time_last_updated is not None
    player.update_state.assert_called()


async def test_pause_accumulates_time(player: MSXPlayer) -> None:
    """pause() should accumulate elapsed time from last update."""
    player._attr_playback_state = PlaybackState.PLAYING
    player._attr_elapsed_time = 10.0
    player._attr_elapsed_time_last_updated = 100.0

    with patch("music_assistant.providers.msx_bridge.player.time") as mock_time:
        mock_time.time.return_value = 115.0
        await player.pause()

    assert player._attr_playback_state == PlaybackState.PAUSED
    assert player._attr_elapsed_time == 25.0  # 10 + (115 - 100)
    player.update_state.assert_called()


async def test_pause_none_elapsed(player: MSXPlayer) -> None:
    """pause() should not crash when elapsed_time is None."""
    player._attr_playback_state = PlaybackState.PLAYING
    player._attr_elapsed_time = None
    player._attr_elapsed_time_last_updated = None

    await player.pause()

    assert player._attr_playback_state == PlaybackState.PAUSED
    # elapsed stays None since there was nothing to accumulate
    assert player._attr_elapsed_time is None


async def test_stop_clears_all(player: MSXPlayer) -> None:
    """stop() should reset state, media, elapsed, and stream URL."""
    player._attr_playback_state = PlaybackState.PLAYING
    player._attr_current_media = Mock()
    player._attr_elapsed_time = 42.0
    player.current_stream_url = "http://something"

    await player.stop()

    assert player._attr_playback_state == PlaybackState.IDLE
    assert player._attr_current_media is None
    assert player._attr_elapsed_time is None
    assert player._attr_elapsed_time_last_updated is None
    assert player.current_stream_url is None
    player.update_state.assert_called()


async def test_stop_idempotent(player: MSXPlayer) -> None:
    """Calling stop() on an idle player should not raise."""
    player._attr_playback_state = PlaybackState.IDLE
    await player.stop()
    assert player._attr_playback_state == PlaybackState.IDLE


# --- Volume and polling ---


async def test_volume_set(player: MSXPlayer) -> None:
    """volume_set should update volume level and call update_state."""
    await player.volume_set(75)
    assert player._attr_volume_level == 75
    player.update_state.assert_called()


async def test_poll_updates_elapsed(player: MSXPlayer) -> None:
    """poll() should accumulate elapsed time during PLAYING."""
    player._attr_playback_state = PlaybackState.PLAYING
    player._attr_elapsed_time = 10.0
    player._attr_elapsed_time_last_updated = 200.0

    with patch("music_assistant.providers.msx_bridge.player.time") as mock_time:
        mock_time.time.return_value = 205.0
        await player.poll()

    assert player._attr_elapsed_time == 15.0  # 10 + (205 - 200)
    assert player._attr_elapsed_time_last_updated == 205.0
    player.update_state.assert_called()


async def test_poll_noop_when_paused(player: MSXPlayer) -> None:
    """poll() should not update anything when paused."""
    player._attr_playback_state = PlaybackState.PAUSED
    player._attr_elapsed_time = 42.0
    player.update_state.reset_mock()

    await player.poll()

    assert player._attr_elapsed_time == 42.0
    player.update_state.assert_not_called()


async def test_poll_noop_when_idle(player: MSXPlayer) -> None:
    """poll() should not update anything when idle."""
    player._attr_playback_state = PlaybackState.IDLE
    player.update_state.reset_mock()

    await player.poll()

    player.update_state.assert_not_called()
