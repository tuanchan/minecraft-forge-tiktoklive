"""Read-only LIVE handshake check: no gameplay, TTS, or credential logging."""
import asyncio
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit, quote

from TikTokLive import TikTokLiveClient
from TikTokLive.client.web.routes.fetch_signed_websocket import WebcastPlatform
from TikTokLive.client.web.web_settings import WebDefaults
from TikTokLive.client.ws.ws_utils import build_webcast_uri
from websockets.legacy.client import connect
from websockets.legacy.exceptions import InvalidStatusCode

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bridge"))
from live_connection import install_websocket_url_fix


async def compare_handshakes():
    config = json.loads((Path(__file__).resolve().parents[1] / "bridge/config.json").read_text(encoding="utf-8"))
    client = TikTokLiveClient(unique_id=config["tiktok_username"])
    try:
        room = int(await client.web.fetch_room_id_from_api(client.unique_id))
        print("ROOM", room, "LIVE", await client.web.fetch_is_live(room_id=room), flush=True)
        client.web.params["room_id"] = str(room)
        response = await client.web.fetch_signed_websocket(WebcastPlatform.WEB)
        params = {**WebDefaults.ws_client_params, "room_id": room, "compress": "gzip"}
        uri = build_webcast_uri(response, params, WebDefaults.ws_client_params_append_str)
        print("HOST", urlsplit(uri).hostname, "WHITESPACE", any(c.isspace() for c in uri), "ROUTE_KEYS", sorted(response.route_params), flush=True)
        headers = {"Cookie": client._ws.get_ws_cookie_string(client.web.cookies), "User-Agent": client.web.headers["User-Agent"]}
        for mode in ("default", "no_deflate", "origin", "escaped", "single_version"):
            candidate = uri
            kwargs = {}
            if mode == "no_deflate":
                kwargs["compression"] = None
            elif mode == "origin":
                kwargs["origin"] = "https://www.tiktok.com"
            elif mode == "escaped":
                candidate = quote(uri, safe=":/?&=%+;,@!$'()*[]")
            elif mode == "single_version":
                candidate = build_webcast_uri(response, {**params, "version_code": "270000"}, "")
            try:
                async with connect(candidate, extra_headers=headers, subprotocols=["echo-protocol"], open_timeout=5, close_timeout=1, **kwargs) as ws:
                    print(mode, "CONNECTED", flush=True)
                    return
            except InvalidStatusCode as error:
                print(mode, "HTTP", error.status_code, {k: error.headers.get(k) for k in ("Server", "Handshake-Msg", "Handshake-Status", "X-Tt-Logid")}, flush=True)
            except Exception as error:
                print(mode, type(error).__name__, flush=True)
    finally:
        await client.web.close()


async def verify_fixed_client():
    from TikTokLive.events import ConnectEvent, WebsocketResponseEvent

    install_websocket_url_fix()
    config = json.loads((Path(__file__).resolve().parents[1] / "bridge/config.json").read_text(encoding="utf-8"))
    client = TikTokLiveClient(unique_id=config["tiktok_username"])
    connected = asyncio.Event()
    responses = 0

    @client.on(ConnectEvent)
    async def on_connect(event):
        print("FIXED_CLIENT_CONNECTED", flush=True)
        connected.set()

    @client.on(WebsocketResponseEvent)
    async def on_response(event):
        nonlocal responses
        responses += 1

    try:
        task = await asyncio.wait_for(client.start(), timeout=20)
        ready = asyncio.create_task(connected.wait())
        try:
            done, _ = await asyncio.wait((task, ready), timeout=15, return_when=asyncio.FIRST_COMPLETED)
            if task in done:
                await task
            if not connected.is_set():
                generator = client._ws._connection_generator
                print("DIAGNOSTIC", "socket_open", client._ws.connected,
                      "initial_is_first", getattr(getattr(generator, "_initial_response", None), "is_first", None),
                      "responses", responses, flush=True)
                raise RuntimeError("LIVE handshake did not complete")
            await asyncio.sleep(2)
            print("WEBSOCKET_RESPONSES", responses, flush=True)
        finally:
            ready.cancel()
            await asyncio.gather(ready, return_exceptions=True)
    finally:
        await client.disconnect()
        await client.web.close()


if __name__ == "__main__":
    asyncio.run(compare_handshakes() if "--compare" in sys.argv else verify_fixed_client())
