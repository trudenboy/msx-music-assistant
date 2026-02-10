"""Mappers for converting Music Assistant objects to MSX models."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from .models import MsxItem

if TYPE_CHECKING:
    from .provider import MSXBridgeProvider


def append_device_param(url: str, device_param: str) -> str:
    """Append device_id to URL if present."""
    if not device_param:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}{device_param}"


def get_image_url(item: Any, provider: MSXBridgeProvider) -> str | None:
    """Get an image URL for a media item."""
    if hasattr(item, "image") and item.image:
        return provider.mass.metadata.get_image_url(item.image)
    return None


async def get_album_image_fallback(album: Any, provider: MSXBridgeProvider) -> str | None:
    """Get album image from its first track (albums often lack metadata images)."""
    try:
        tracks = await provider.mass.music.albums.tracks(album.item_id, album.provider)
        for track in tracks:
            if hasattr(track, "image") and track.image:
                return provider.mass.metadata.get_image_url(track.image)
    except Exception:
        pass
    return None


async def map_album_to_msx(
    album: Any,
    prefix: str,
    provider: MSXBridgeProvider,
    device_param: str = ""
) -> MsxItem:
    """Map a MA Album to an MSX Item."""
    image = get_image_url(album, provider)
    if not image:
        image = await get_album_image_fallback(album, provider)

    url = f"{prefix}/msx/albums/{album.item_id}/tracks.json?provider={album.provider}"
    return MsxItem(
        title=album.name,
        label=getattr(album, "artist_str", ""),
        image=image,
        action=f"content:{append_device_param(url, device_param)}"
    )


def map_artist_to_msx(
    artist: Any,
    prefix: str,
    provider: MSXBridgeProvider,
    device_param: str = ""
) -> MsxItem:
    """Map a MA Artist to an MSX Item."""
    url = f"{prefix}/msx/artists/{artist.item_id}/albums.json"
    return MsxItem(
        title=artist.name,
        image=get_image_url(artist, provider),
        action=f"content:{append_device_param(url, device_param)}"
    )


def map_playlist_to_msx(
    playlist: Any,
    prefix: str,
    provider: MSXBridgeProvider,
    device_param: str = ""
) -> MsxItem:
    """Map a MA Playlist to an MSX Item."""
    url = f"{prefix}/msx/playlists/{playlist.item_id}/tracks.json"
    return MsxItem(
        title=playlist.name,
        image=get_image_url(playlist, provider),
        action=f"content:{append_device_param(url, device_param)}"
    )


def map_track_to_msx(
    track: Any,
    prefix: str,
    player_id: str,
    provider: MSXBridgeProvider,
    device_param: str = ""
) -> MsxItem:
    """Map a MA Track to an MSX Item."""
    duration = getattr(track, "duration", 0) or 0
    duration_str = f"{duration // 60}:{duration % 60:02d}" if duration else ""
    label = getattr(track, "artist_str", "")
    if duration_str:
        label = f"{label} · {duration_str}" if label else duration_str
    image_url = get_image_url(track, provider)
    audio_url = f"{prefix}/msx/audio/{player_id}?uri={quote(track.uri, safe='')}"
    return MsxItem(
        title=track.name,
        label=label,
        player_label=track.name,
        image=image_url,
        background=image_url,
        action=f"audio:{append_device_param(audio_url, device_param)}"
    )
