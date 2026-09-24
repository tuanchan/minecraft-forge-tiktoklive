import io
import json
import unittest
import urllib.error
from unittest.mock import patch
import test_settings as settings_tests

web = settings_tests.web


def response(value):
    return io.BytesIO(json.dumps(value).encode())


class VoiceCatalogTests(unittest.TestCase):
    def test_missing_permissions_load_public_voices_and_builtin_models(self):
        requests = []
        def fetch(request, **kwargs):
            requests.append(request)
            if request.full_url.endswith('/v1/voices'):
                self.assertNotIn('Xi-api-key', request.headers)
                return response({'voices': [{'voice_id': 'public-a', 'name': 'Public A'},
                                             {'voice_id': 'public-b', 'name': 'Public B'}]})
            raise urllib.error.HTTPError(request.full_url, 401, 'permission', {},
                response({'detail': {'message': 'missing permission'}}))
        with patch.object(web.urllib.request, 'urlopen', side_effect=fetch), \
             patch.object(web, 'load_json', return_value={'tts_voice_id': 'current', 'tts_voice_name': 'Saved'}):
            catalog = web.Controller().elevenlabs_catalog('test-key')
        self.assertEqual(len(catalog['voices']), 3)
        self.assertEqual(len(catalog['models']), 4)
        self.assertTrue(catalog['warnings'])
        self.assertEqual(len(requests), 3)

    def test_account_voices_load_all_pages_and_deduplicate(self):
        urls = []
        def fetch(request, **kwargs):
            urls.append(request.full_url)
            if '/v1/models' in request.full_url:
                return response([{'model_id': 'tts-new', 'can_do_text_to_speech': True},
                                 {'model_id': 'voice-conversion', 'can_do_text_to_speech': False}])
            if 'next_page_token=' in request.full_url:
                return response({'voices': [{'voice_id': 'a', 'name': 'A'}, {'voice_id': 'b', 'name': 'B'}], 'has_more': False})
            return response({'voices': [{'voice_id': 'a', 'name': 'A'}], 'has_more': True, 'next_page_token': 'next+/='})
        with patch.object(web.urllib.request, 'urlopen', side_effect=fetch), \
             patch.object(web, 'load_json', return_value={'tts_voice_id': 'a'}):
            catalog = web.Controller().elevenlabs_catalog('test-key')
        self.assertEqual(len(catalog['voices']), 2)
        self.assertEqual([m['model_id'] for m in catalog['models']], ['tts-new'])
        self.assertIn('next_page_token=next%2B%2F%3D', urls[1])
        self.assertEqual(catalog['warnings'], [])

    def test_no_key_can_browse_public_voices_without_synthesis(self):
        with patch.object(web, 'load_api_key', return_value=''), \
             patch.object(web.urllib.request, 'urlopen', return_value=response({'voices': [{'voice_id': 'public', 'name': 'Public'}]})) as fetch, \
             patch.object(web, 'load_json', return_value={}):
            catalog = web.Controller().elevenlabs_catalog('')
        self.assertEqual(len(catalog['voices']), 1)
        self.assertEqual(len(catalog['models']), 4)
        fetch.assert_called_once()


if __name__ == '__main__':
    unittest.main()
