import uuid

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app import auth
from app.database import get_connection


def verify(value):
    return auth.verify_access_token(HTTPAuthorizationCredentials(scheme="Bearer",credentials=value))


def test_correct_signed_token(issue_token):
    sub=str(uuid.uuid4())
    assert verify(issue_token(sub))["sub"] == sub


@pytest.mark.parametrize("claims", [{"iss":"https://wrong.invalid"},{"exp":1},{"aud":"another-api"},
    {"sub":"not-a-uuid"},{"sub":""},{"aud":None},{"iss":None},{"exp":None}])
def test_invalid_claims(issue_token,claims):
    with pytest.raises(HTTPException) as error:
        verify(issue_token(**claims))
    assert error.value.status_code == 401


@pytest.mark.parametrize("value", ["malformed", "a.b.c", ""])
def test_malformed_token(issue_token,value):
    with pytest.raises(HTTPException) as error:
        verify(value)
    assert error.value.status_code == 401


def test_signature_and_algorithm(issue_token):
    value=issue_token()
    head,payload,signature=value.split('.')
    altered=('a' if signature[0]!='a' else 'b')+signature[1:]
    for token in [f'{head}.{payload}.{altered}',jwt.encode({'sub':str(uuid.uuid4())},None,algorithm='none',headers={'kid':'test-only'})]:
        with pytest.raises(HTTPException) as error:
            verify(token)
        assert error.value.status_code == 401


def test_audience_list(issue_token):
    assert verify(issue_token(aud=['account','finops-api']))


@pytest.mark.anyio
async def test_linked_unknown_inactive(client,users,issue_token):
    headers={'Authorization':'Bearer '+issue_token(users[0]['sub'])}
    response=await client.get('/auth/me',headers=headers)
    assert response.status_code == 200 and response.json()['id'] == users[0]['id']
    assert (await client.get('/auth/me',headers={'Authorization':'Bearer '+issue_token()})).status_code == 403
    with get_connection() as conn:
        conn.execute('UPDATE users SET is_active=false WHERE id=%s',(users[0]['id'],))
    assert (await client.get('/auth/me',headers=headers)).status_code == 403


def test_realm_role_authorization():
    payload={'realm_access':{'roles':['user','admin']}}
    user={'id':123}
    assert auth.require_roles('admin')(payload,user) is user
    with pytest.raises(HTTPException): auth.require_roles('admin')({'realm_access':{'roles':['user']}})
    assert auth.realm_roles({'realm_access':{'roles':'admin'}}) == frozenset()
