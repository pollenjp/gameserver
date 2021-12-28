import pytest
from fastapi.testclient import TestClient

import app.api
import app.model
from app.model import InvalidToken

client = TestClient(app.api.app)


def test_create_user():
    response = client.post(
        "/user/create", json={"user_name": "test1", "leader_card_id": 1000}
    )
    assert response.status_code == 200

    response_data = response.json()
    assert response_data.keys() == {"user_token"}

    token = response.json()["user_token"]

    response = client.get("/user/me", headers={"Authorization": f"bearer {token}"})
    assert response.status_code == 200

    response_data = response.json()
    assert response_data.keys() == {"id", "name", "leader_card_id"}
    assert response_data["name"] == "test1"
    assert response_data["leader_card_id"] == 1000


def test_update_not_existing_user():
    with pytest.raises(InvalidToken):
        app.model.update_user(token="nothing", name="Hello", leader_card_id=0)
