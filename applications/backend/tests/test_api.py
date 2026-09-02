from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "service": "finops-api",
        "status": "running",
    }


def test_version():
    response = client.get("/version")

    assert response.status_code == 200
    assert response.json() == {
        "version": "auto-cd-test",
    }

def test_liveness():
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {
        "status": "alive",
    }
def test_register_user():
    mock_cursor = MagicMock()

    mock_cursor.fetchone.return_value = (
        1,
        123456789,
        "sniper541",
        "Михаил",
        True,
        "2026-09-02T12:00:00+00:00",
        "2026-09-02T12:00:00+00:00",
    )

    mock_connection = MagicMock()
    mock_connection.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor

    with patch("app.main.get_connection", return_value=mock_connection):
        response = client.post(
            "/users/register",
            json={
                "telegram_id": 123456789,
                "telegram_username": "sniper541",
                "first_name": "Михаил",
            },
        )

    assert response.status_code == 200

    assert response.json()["telegram_id"] == 123456789
    assert response.json()["telegram_username"] == "sniper541"
    assert response.json()["first_name"] == "Михаил"

    assert mock_cursor.execute.call_count == 2

    first_call = mock_cursor.execute.call_args_list[0]

    sql_query = first_call.args[0]
    sql_params = first_call.args[1]

    assert "INSERT INTO users" in sql_query
    assert sql_params == (
        123456789,
        "sniper541",
        "Михаил",
    )
    second_call = mock_cursor.execute.call_args_list[1]
    
    settings_query = second_call.args[0]
    settings_params = second_call.args[1]
    
    assert "INSERT INTO user_settings" in settings_query
    assert settings_params == (1,)

def test_create_category():
    mock_cursor = MagicMock()

    mock_cursor.fetchone.return_value = (
        10,
        1,
        "expense",
        "Продукты",
        "🛒",
        True,
        "2026-09-02T12:00:00+00:00",
        "2026-09-02T12:00:00+00:00",
    )

    mock_connection = MagicMock()
    mock_connection.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor

    with patch("app.main.get_connection", return_value=mock_connection):
        response = client.post(
            "/categories",
            json={
                "user_id": 1,
                "type": "expense",
                "name": "Продукты",
                "icon": "🛒",
            },
        )

    assert response.status_code == 200
    assert response.json()["user_id"] == 1
    assert response.json()["type"] == "expense"
    assert response.json()["name"] == "Продукты"
    assert response.json()["icon"] == "🛒"