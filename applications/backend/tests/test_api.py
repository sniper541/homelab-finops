import pytest

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize("path", ["/", "/version", "/health/live"])
async def test_public_health(client, path):
    assert (await client.get(path)).status_code == 200


@pytest.mark.parametrize("method,path,body", [
    ("GET","/categories",None), ("POST","/categories",{"type":"expense","name":"test"}),
    ("PATCH","/categories/1",{"name":"test"}), ("DELETE","/categories/1",None),
    ("GET","/transactions",None), ("POST","/transactions",{"category_id":1,"amount":1}),
    ("DELETE","/transactions/1",None), ("GET","/reports/summary",None),
    ("GET","/auth/me",None), ("POST","/bot/users/register",{}), ("GET","/bot/categories",None),
])
async def test_personal_endpoints_require_bearer(client,method,path,body):
    response = await client.request(method,path,json=body)
    assert response.status_code == 401
    assert response.headers['www-authenticate'] == 'Bearer'


async def test_old_public_registration_removed(client):
    assert (await client.post('/users/register',json={'telegram_id':1})).status_code == 404
