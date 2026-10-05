import asyncio
from types import SimpleNamespace

import pytest
from prometheus_client import REGISTRY
from app.metrics import HTTPMetrics


def test_route_labels_and_inflight_cleanup():
    async def app(scope, receive, send):
        assert REGISTRY.get_sample_value('finops_http_requests_in_flight') == 1
        scope['route'] = SimpleNamespace(path='/transactions/{id}')
        await send({'type': 'http.response.start', 'status': 404})
        await send({'type': 'http.response.body', 'body': b''})
    messages = []
    async def send(message): messages.append(message)
    async def receive(): return {'type': 'http.request', 'body': b''}
    labels = {'method': 'GET', 'route': '/transactions/{id}', 'status': '404'}
    before = REGISTRY.get_sample_value('finops_http_requests_total', labels) or 0
    asyncio.run(HTTPMetrics(app)({'type': 'http', 'method': 'GET', 'path': '/transactions/private-value'}, receive, send))
    assert REGISTRY.get_sample_value('finops_http_requests_total', labels) == before + 1
    assert REGISTRY.get_sample_value('finops_http_requests_in_flight') == 0
    assert messages[0]['status'] == 404


def test_unhandled_error_is_counted_without_leaking_path():
    async def app(scope, receive, send): raise RuntimeError('test')
    labels = {'method': 'OTHER', 'route': 'unmatched', 'status': '500'}
    before = REGISTRY.get_sample_value('finops_http_requests_total', labels) or 0
    with pytest.raises(RuntimeError):
        asyncio.run(HTTPMetrics(app)({'type': 'http', 'method': 'CUSTOM-UNBOUNDED', 'path': '/private'}, None, None))
    assert REGISTRY.get_sample_value('finops_http_requests_total', labels) == before + 1
    assert REGISTRY.get_sample_value('finops_http_requests_in_flight') == 0
