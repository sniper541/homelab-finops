import os
import pathlib
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'app'))
os.environ.setdefault('TELEGRAM_BOT_TOKEN','test-only-not-a-real-token')
import main
import service_auth


class BotIdentityTests(unittest.IsolatedAsyncioTestCase):
    async def test_identity_comes_from_telegram_update_not_cached_internal_id(self):
        update=SimpleNamespace(effective_user=SimpleNamespace(id=123456))
        context=SimpleNamespace(user_data={'user_id':999})
        self.assertEqual(await main.ensure_user(update,context),123456)

    async def test_service_headers_and_endpoint(self):
        response=MagicMock()
        response.json.return_value=[]
        client=AsyncMock()
        client.__aenter__.return_value=client
        client.request.return_value=response
        with patch.object(main,'access_token',AsyncMock(return_value='test-service-token')), patch.object(main.httpx,'AsyncClient',return_value=client):
            await main.api_request('GET','/categories',telegram_id=123456)
        call=client.request.call_args
        self.assertTrue(call.args[1].endswith('/bot/categories'))
        self.assertEqual(call.kwargs['headers'],{'Authorization':'Bearer test-service-token','X-Telegram-User-ID':'123456'})
        self.assertNotIn('params',call.kwargs)

    async def test_registration_does_not_choose_internal_identity(self):
        user=SimpleNamespace(id=123456,username='test',first_name='Example')
        with patch.object(main,'api_request',AsyncMock(return_value={'id':987})) as request:
            await main.get_or_create_user(user)
        self.assertEqual(request.call_args.kwargs['telegram_id'],123456)
        self.assertNotIn('telegram_id',request.call_args.kwargs['json'])
        self.assertNotIn('user_id',request.call_args.kwargs['json'])

    async def test_service_token_cache_and_renewal(self):
        service_auth._token=None
        response=MagicMock()
        response.json.return_value={'access_token':'test-service-token','expires_in':300}
        client=AsyncMock()
        client.__aenter__.return_value=client
        client.post.return_value=response
        with patch.dict(os.environ,{'KEYCLOAK_TOKEN_URL':'https://identity.invalid/token','KEYCLOAK_CLIENT_SECRET':'nonfunctional-test-value'}), patch.object(service_auth.httpx,'AsyncClient',return_value=client):
            self.assertEqual(await service_auth.access_token(),'test-service-token')
            await service_auth.access_token()
            self.assertEqual(client.post.await_count,1)
            service_auth._expires=0
            await service_auth.access_token()
            self.assertEqual(client.post.await_count,2)
            self.assertEqual(client.post.call_args.kwargs['data']['grant_type'],'client_credentials')
