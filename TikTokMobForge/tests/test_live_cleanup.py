import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bridge"))
from TikTokLive import TikTokLiveClient
from live_connection import run_client_with_cleanup


class LiveCleanupTests(unittest.TestCase):
    def test_offline_and_normal_exit_close_real_client(self):
        for failure in (None, RuntimeError("offline simulation")):
            with self.subTest(failure=failure):
                client = TikTokLiveClient(unique_id="@cleanup_test")
                loop = client._asyncio_loop
                errors = []
                loop.set_exception_handler(lambda _, context: errors.append(context))
                stopped = []

                async def background():
                    try:
                        await asyncio.sleep(3600)
                    finally:
                        stopped.append(True)

                async def connect(**kwargs):
                    asyncio.create_task(background())
                    await asyncio.sleep(0)
                    if failure:
                        raise failure

                with patch.object(client, "connect", side_effect=connect), \
                     patch.object(client.web, "close", wraps=client.web.close) as close:
                    if failure:
                        with self.assertRaisesRegex(RuntimeError, "offline simulation"):
                            run_client_with_cleanup(client)
                    else:
                        run_client_with_cleanup(client)
                    close.assert_awaited_once()
                self.assertTrue(loop.is_closed())
                self.assertEqual(stopped, [True])
                self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
