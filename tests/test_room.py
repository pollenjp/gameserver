# Standard Library
from logging import getLogger
from typing import Any
from typing import Dict
from typing import List

# Third Party Library
import pytest
from fastapi.testclient import TestClient

# First Party Library
from app import room_model
from app.api import app

logger = getLogger(__name__)

client = TestClient(app)


def _create_users(num: int = 10) -> List[str]:
    user_tokens = []
    for i in range(10):
        response = client.post(
            "/user/create",
            json={"user_name": f"room_user_{i}", "leader_card_id": 1000},
        )
        user_tokens.append(response.json()["user_token"])
    return user_tokens


def _get_auth_header(token: str) -> Dict[str, str]:
    return {"Authorization": f"bearer {token}"}


class TestRoom:
    def setup_class(self):
        self.user_tokens: List[str] = _create_users()
        self.auth_header = _get_auth_header(self.user_tokens[0])

    def teardown_class(self):
        pass

    def setup_method(self, method):
        pass

    def teardown_method(self, method):
        pass

    @pytest.mark.parametrize(
        "room_arg",
        [
            pytest.param(
                dict(
                    live_id=1,
                    select_difficulty=int(room_model.LiveDifficulty.normal),
                ),
            ),
            pytest.param(
                dict(
                    live_id=2,
                    select_difficulty=int(room_model.LiveDifficulty.hard),
                ),
            ),
            pytest.param(
                dict(
                    live_id=2,
                    select_difficulty=3,  # 3 does not exists
                ),
                marks=pytest.mark.xfail(strict=True),
            ),
        ],
    )
    def test_create_room(self, room_arg: Dict[str, Any]):
        response = client.post(
            "/room/create",
            headers=self.auth_header,
            json=dict(
                live_id=room_arg["live_id"],
                select_difficulty=int(room_arg["select_difficulty"]),
            ),
        )
        assert response.status_code == 200

    def test_start_to_end(self):
        response = client.post(
            "/room/create",
            headers=self.auth_header,
            json=dict(
                live_id=1001,
                select_difficulty=int(room_model.LiveDifficulty.normal),
            ),
        )
        assert response.status_code == 200
        room_id = response.json()["room_id"]
        logger.info(f"room/create {room_id=}")

        response = client.post("/room/list", json=dict(live_id=1001))
        assert response.status_code == 200
        logger.info("room/list response:", response.json())

        response = client.post(
            "/room/join",
            headers=self.auth_header,
            json={
                "room_id": room_id,
                "select_difficulty": room_model.LiveDifficulty.hard,
            },
        )
        assert response.status_code == 200
        logger.info("room/join response:", response.json())
        assert response.json()["join_room_result"] in [result for result in room_model.JoinRoomResult]

        response = client.post("/room/wait", headers=self.auth_header, json={"room_id": room_id})
        assert response.status_code == 200
        logger.info("room/wait response:", response.json())

        response = client.post("/room/start", headers=self.auth_header, json={"room_id": room_id})
        assert response.status_code == 200
        logger.info("room/wait response:", response.json())

        response = client.post(
            "/room/end",
            headers=self.auth_header,
            json={"room_id": room_id, "score": 1234, "judge_count_list": [5, 4, 3, 2, 1]},
        )
        assert response.status_code == 200
        logger.info("room/end response:", response.json())

        response = client.post(
            "/room/result",
            json={"room_id": room_id},
        )
        assert response.status_code == 200
        logger.info("room/end response:", response.json())

    def test_create_and_leave(self):
        """create room and leave it"""

        # create a host user
        user_tokens: List[str] = _create_users(num=1)
        auth_header: Dict[str, Any] = _get_auth_header(user_tokens[0])

        # host a room
        response = client.post(
            "/room/create",
            headers=auth_header,
            json=dict(
                live_id=1001,
                select_difficulty=int(room_model.LiveDifficulty.normal),
            ),
        )
        assert response.status_code == 200
        room_id = response.json()["room_id"]
        logger.info(f"room/create {room_id=}")

        # leave the room
        response = client.post(
            "/room/leave",
            headers=auth_header,
            json=dict(room_id=room_id),
        )
