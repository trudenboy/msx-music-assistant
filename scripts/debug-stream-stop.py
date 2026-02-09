#!/usr/bin/env python3
"""
Debug script: simulate MSX stream + stop flow and capture MSX_DEBUG logs.

Usage:
  ./scripts/debug-stream-stop.py

Requires MA server with linked MSX provider. Run ./scripts/link-to-ma.sh first.
"""
from __future__ import annotations

import asyncio
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote, unquote

try:
    import aiohttp
except ImportError:
    print("Install aiohttp: pip install aiohttp")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MA_SERVER = Path(os.environ.get("MA_SERVER", PROJECT_ROOT / ".." / "ma-server"))
LOG_FILE = PROJECT_ROOT / ".test-server.log"
BASE_URL = "http://127.0.0.1:8099"
# MA_DATA_DIR for test - use project dir to avoid sandbox permission issues
DATA_DIR = PROJECT_ROOT / ".ma-test-data"


async def main() -> None:
    print("=== MSX Stream Stop Debug ===\n")

    # 1. Ensure server is running
    if not (MA_SERVER / ".venv").exists():
        print("Error: MA venv not found. Run ./scripts/link-to-ma.sh first.")
        sys.exit(1)

    test_server = PROJECT_ROOT / "scripts" / "test-server.sh"
    result = subprocess.run(
        [str(test_server), "status"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    if "Not running" in result.stdout:
        print("Starting MA server...")
        env = os.environ.copy()
        env["MA_DATA_DIR"] = str(DATA_DIR)
        subprocess.run(
            [str(test_server), "start"],
            check=True,
            cwd=str(PROJECT_ROOT),
            env=env,
        )
        await asyncio.sleep(8)  # MA + MSX provider need time to init
    else:
        print("MA server already running")

    # 2. Register player (device_id=debug_test -> msx_debug_test) and get a track
    device_param = "device_id=debug_test"
    player_id = "msx_debug_test"
    track_uri: str | None = None

    async with aiohttp.ClientSession() as session:
        # Health check
        try:
            async with session.get(f"{BASE_URL}/health", timeout=5) as resp:
                if resp.status != 200:
                    print(f"Health check failed: {resp.status}")
                    sys.exit(1)
        except aiohttp.ClientError as e:
            print(f"Server not reachable: {e}")
            sys.exit(1)
        print("Server OK")

        # Register player and get tracks (hitting MSX endpoint registers the player)
        async with session.get(
            f"{BASE_URL}/msx/tracks.json?{device_param}", timeout=10
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                items = data.get("items", [])
                if items:
                    item = items[0]
                    track_uri = item.get("uri")
                    if not track_uri and (action := item.get("action", "")):
                        m = re.search(r"uri=([^&]+)", action)
                        if m:
                            track_uri = unquote(m.group(1))
                    if track_uri:
                        print(f"Got track: {track_uri}")
        if not track_uri:
            async with session.get(f"{BASE_URL}/api/tracks?limit=1", timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    items = data.get("items", [])
                    if items:
                        track_uri = items[0].get("uri")
        if not track_uri:
            track_uri = "library://track/test"
            print(f"No library tracks, using fallback: {track_uri}")

        # 3. Start playback: POST /api/play then GET /stream (same flow as MSX)
        print("\nTest A: POST /api/play + GET /stream (MSX flow)...")
        play_ok = False
        async with session.post(
            f"{BASE_URL}/api/play",
            json={"track_uri": track_uri, "player_id": player_id},
            timeout=10,
        ) as resp:
            play_ok = resp.status == 200
            if not play_ok:
                print(f"  Play failed ({resp.status}), trying /msx/audio fallback...")

        stream_done = asyncio.Event()
        stream_error: str | None = None

        async def fetch_stream() -> None:
            nonlocal stream_error
            url = f"{BASE_URL}/stream/{player_id}" if play_ok else f"{BASE_URL}/msx/audio/{player_id}?uri={quote(track_uri, safe='')}&{device_param}"
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=35)) as resp:
                    if resp.status != 200:
                        stream_error = f"status={resp.status}"
                    else:
                        await resp.read()
            except asyncio.CancelledError:
                stream_error = "cancelled"
            except Exception as e:
                stream_error = str(e)
            finally:
                stream_done.set()

        stream_task = asyncio.create_task(fetch_stream())
        await asyncio.sleep(3)

        # 5. Call stop while stream is active
        print("Calling stop...")
        async with session.post(
            f"{BASE_URL}/api/stop/{player_id}",
            timeout=5,
        ) as resp:
            stop_ok = resp.status == 200
            print(f"Stop response: {resp.status}")

        # 6. Wait for stream to finish
        try:
            await asyncio.wait_for(stream_done.wait(), timeout=35)
        except asyncio.TimeoutError:
            stream_task.cancel()
            print("Stream timed out after 35s (expected if stop doesn't work)")
        print(f"Stream ended: {stream_error or 'ok'}")

    # 7. Show MSX_DEBUG logs
    print("\n=== MSX_DEBUG logs ===")
    if not LOG_FILE.exists():
        print("No log file found. Server may log elsewhere.")
        return

    with open(LOG_FILE) as f:
        lines = f.readlines()

    debug_lines = [l.rstrip() for l in lines if "[MSX_DEBUG]" in l]
    if not debug_lines:
        print("No [MSX_DEBUG] lines found in log.")
        print("Check if log level is INFO+ and server is writing to", LOG_FILE)
    else:
        for line in debug_lines[-20:]:
            print(line)

    # Analysis
    print("\n=== Analysis ===")
    registered = [l for l in debug_lines if "_register_stream" in l]
    cancelled = [l for l in debug_lines if "cancel_streams_for_player" in l]
    notify = [l for l in debug_lines if "notify_play_stopped" in l]

    print(f"notify_play_stopped calls: {len(notify)}")
    print(f"cancel_streams_for_player calls: {len(cancelled)}")
    print(f"_register_stream calls: {len(registered)}")

    if notify and cancelled:
        for n in notify:
            print(f"  notify: {n}")
        for c in cancelled:
            print(f"  cancel: {c}")
        if registered:
            for r in registered:
                print(f"  register: {r}")

        if cancelled and "found tasks=0 transports=0" in " ".join(cancelled):
            print("\n*** ISSUE: cancel_streams_for_player found 0 tasks/transports!")
            print("   Possible cause: player_id mismatch between register and cancel.")
            if registered:
                print("   Registered under:", registered[-1].split("all_registered=")[-1][:80])
        elif not registered:
            print("\n*** ISSUE: _register_stream never called - stream didn't start?")


if __name__ == "__main__":
    asyncio.run(main())
