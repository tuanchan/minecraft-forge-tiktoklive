"""Compatibility fix for TikTokLive 7.0.0 signed WebSocket URLs."""
from functools import wraps
from urllib.parse import quote, urlsplit


def install_websocket_url_fix() -> None:
    # EulerStream's fallback includes a raw user_agent in route_params.
    # TikTokLive joins those values without escaping, and websockets sends
    # literal spaces in the HTTP request target, which is rejected with 400.
    from TikTokLive.client.ws import ws_connect

    original = ws_connect.build_webcast_uri
    if getattr(original, "_tiktokmob_url_fix", False):
        return

    @wraps(original)
    def build_safe_uri(initial_webcast_response, base_uri_params, base_uri_append_str):
        uri = original(initial_webcast_response, base_uri_params, base_uri_append_str)
        if urlsplit(uri).hostname == "ws-fallback.eulerstream.com":
            # The fallback's bootstrap omits is_first. TikTokLive needs this
            # flag to send room entry, start heartbeat and emit ConnectEvent.
            # This response is yielded only AFTER the socket opens successfully.
            initial_webcast_response.is_first = True
        # Preserve the signed query, duplicate keys and existing % escapes.
        # Re-encoding the whole query with urlencode would double-encode it.
        return quote(uri, safe=":/?&=%+;,@!$'()*[]")

    build_safe_uri._tiktokmob_url_fix = True
    ws_connect.build_webcast_uri = build_safe_uri
def run_client_with_cleanup(client):
    """Release each discarded client's sessions before closing its owned loop."""
    import asyncio

    loop = client._asyncio_loop
    try:
        return client.run()
    finally:
        async def cleanup():
            # client.close() in TikTokLive 7 calls run_until_complete inside an
            # async function. Close its public HTTP transport directly instead.
            for close in (client.disconnect, client.web.close):
                try:
                    await asyncio.wait_for(close(), timeout=5)
                except Exception as error:
                    print(f"[LIVE cleanup] {type(error).__name__}: {error}")
            pending = [task for task in asyncio.all_tasks(loop)
                       if task is not asyncio.current_task() and not task.done()]
            for task in pending:
                task.cancel()
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)
            await loop.shutdown_asyncgens()
            await loop.shutdown_default_executor(timeout=5)
            # Allow Proactor pipe/socket close callbacks to release their handles.
            await asyncio.sleep(0.1)

        try:
            if not loop.is_closed():
                loop.run_until_complete(cleanup())
        except Exception as error:
            print(f"[LIVE cleanup] {type(error).__name__}: {error}")
        finally:
            if not loop.is_closed():
                loop.close()
