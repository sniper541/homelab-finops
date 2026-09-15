import uuid

import pytest

from app.database import get_connection
from app.main import app

pytestmark = pytest.mark.anyio


def bearer(issue, user):
    return {'Authorization':'Bearer '+issue(user['sub'])}


async def category(client, headers, kind='expense'):
    r=await client.post('/categories',headers=headers,json={'type':kind,'name':'test-'+uuid.uuid4().hex,'icon':'x'})
    assert r.status_code == 200, r.text
    return r.json()


async def test_two_tenants(client,users,issue_token):
    a,b=[bearer(issue_token,u) for u in users]
    ca,cb=await category(client,a),await category(client,b,'income')
    assert ca['user_id']==users[0]['id'] and cb['user_id']==users[1]['id']
    for headers,own in [(a,ca),(b,cb)]:
        assert [x['id'] for x in (await client.get('/categories',headers=headers)).json()]==[own['id']]
    for method in ['PATCH','DELETE']:
        args={'json':{'name':'attempt'}} if method=='PATCH' else {}
        assert (await client.request(method,f"/categories/{ca['id']}",headers=b,**args)).status_code==404
    assert (await client.post('/transactions',headers=a,json={'category_id':cb['id'],'amount':10})).status_code==400
    ta=(await client.post('/transactions',headers=a,json={'category_id':ca['id'],'amount':12.25})).json()
    tb=(await client.post('/transactions',headers=b,json={'category_id':cb['id'],'amount':99})).json()
    for headers,own in [(a,ta),(b,tb)]:
        assert [x['id'] for x in (await client.get('/transactions',headers=headers)).json()]==[own['id']]
    assert (await client.delete(f"/transactions/{ta['id']}",headers=b)).status_code==404
    assert (await client.get('/reports/summary',headers=a)).json()=={'income':0,'expense':12.25,'balance':-12.25}
    assert (await client.get('/reports/summary',headers=b)).json()=={'income':99,'expense':0,'balance':99}
    assert (await client.patch(f"/categories/{ca['id']}",headers=a,json={'name':'renamed'})).status_code==200
    assert (await client.delete(f"/transactions/{ta['id']}",headers=a)).status_code==200
    assert (await client.delete(f"/categories/{ca['id']}",headers=a)).status_code==200
    assert (await client.get('/categories',headers=a)).json()==[]
    assert len((await client.get('/categories',headers=b)).json())==1


async def test_identity_override_rejected(client,users,issue_token):
    a=bearer(issue_token,users[0])
    for path in ['/categories','/transactions','/reports/summary']:
        assert (await client.get(path,params={'user_id':users[1]['id']},headers=a)).status_code==422
    assert (await client.post('/categories',headers=a,json={'type':'expense','name':'injection','user_id':users[1]['id']})).status_code==422
    ca=await category(client,a)
    assert (await client.patch(f"/categories/{ca['id']}",headers=a,json={'user_id':users[1]['id'],'name':'injection'})).status_code==422
    assert (await client.post('/transactions',headers=a,json={'category_id':ca['id'],'amount':10,'user_id':users[1]['id']})).status_code==422
    schema=app.openapi()
    for name in ['CategoryCreateRequest','CategoryUpdateRequest','TransactionCreateRequest']:
        assert 'user_id' not in schema['components']['schemas'][name]['properties']


async def test_inactive_category_cannot_receive_transaction(client,users,issue_token):
    headers=bearer(issue_token,users[0])
    ca=await category(client,headers)
    await client.delete(f"/categories/{ca['id']}",headers=headers)
    assert (await client.post('/transactions',headers=headers,json={'category_id':ca['id'],'amount':1})).status_code==400


async def test_bot_boundary_and_identity(client,users,issue_token):
    service=issue_token(azp='finops-bot',resource_access={'finops-api':{'roles':['telegram-bot']}})
    headers={'Authorization':'Bearer '+service,'X-Telegram-User-ID':str(users[0]['telegram_id'])}
    ca=await category(client,bearer(issue_token,users[0]))
    assert (await client.get('/bot/categories',headers=headers)).json()[0]['id']==ca['id']
    assert (await client.get('/categories',headers=headers)).status_code==403
    browser={**bearer(issue_token,users[1]),'X-Telegram-User-ID':str(users[0]['telegram_id'])}
    assert (await client.get('/bot/categories',headers=browser)).status_code==403
    wrong={'Authorization':'Bearer '+issue_token(azp='another-service',resource_access={'finops-api':{'roles':['telegram-bot']}}),'X-Telegram-User-ID':'10101'}
    assert (await client.get('/bot/categories',headers=wrong)).status_code==403
    missing_role={**headers,'Authorization':'Bearer '+issue_token(azp='finops-bot')}
    assert (await client.get('/bot/categories',headers=missing_role)).status_code==403
    assert (await client.post('/bot/transactions',headers=headers,json={'category_id':ca['id'],'amount':3})).status_code==200
    assert (await client.get('/bot/reports/summary',headers=headers)).json()['expense']==3
    headers['X-Telegram-User-ID']='30303'
    registration=await client.post('/bot/users/register',headers=headers,json={'first_name':'Test only'})
    assert registration.status_code==200
    assert (await client.post('/bot/users/register',headers=headers,json={})).json()['id']==registration.json()['id']
    with get_connection() as conn:
        conn.execute('UPDATE users SET is_active=false WHERE telegram_id=30303')
    assert (await client.post('/bot/users/register',headers=headers,json={})).status_code==403
    assert (await client.get('/bot/categories',headers=headers)).status_code==403
