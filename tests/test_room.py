# Standard Library
from logging import getLogger

# Third Party Library
from fastapi.testclient import TestClient

# First Party Library
from app import room_model
from app.api import app

logger = getLogger(__name__)

client = TestClient(app)
user_tokens = []


def _create_users():
    for i in range(10):
        response = client.post(
            "/user/create",
            json={"user_name": f"room_user_{i}", "leader_card_id": 1000},
        )
        user_tokens.append(response.json()["user_token"])


_create_users()


def _auth_header(i=0):
    token = user_tokens[i]
    return {"Authorization": f"bearer {token}"}


def test_room_1():
    response = client.post(
        "/room/create",
        headers=_auth_header(),
        json={
            "live_id": 1001,
            "select_difficulty": room_model.LiveDifficulty.normal,
        },
    )
    assert response.status_code == 200

    room_id = response.json()["room_id"]
    logger.info(f"room/create {room_id=}")

    response = client.post("/room/list", json={"live_id": 1001})
    assert response.status_code == 200
    logger.info("room/list response:", response.json())

    response = client.post(
        "/room/join",
        headers=_auth_header(),
        json={
            "room_id": room_id,
            "select_difficulty": room_model.LiveDifficulty.hard,
        },
    )
    assert response.status_code == 200
    logger.info("room/join response:", response.json())
    assert response.json()["join_room_result"] in [result for result in room_model.JoinRoomResult]

    response = client.post("/room/wait", headers=_auth_header(), json={"room_id": room_id})
    assert response.status_code == 200
    logger.info("room/wait response:", response.json())

    response = client.post("/room/start", headers=_auth_header(), json={"room_id": room_id})
    assert response.status_code == 200
    logger.info("room/wait response:", response.json())

    response = client.post(
        "/room/end",
        headers=_auth_header(),
        json={"room_id": room_id, "score": 1234, "judge_count_list": [4, 3, 2]},
    )
    assert response.status_code == 200
    logger.info("room/end response:", response.json())

    response = client.post(
        "/room/result",
        json={"room_id": room_id},
    )
    assert response.status_code == 200
    logger.info("room/end response:", response.json())


# class TestRoom:
#     def setup_class(self):
#         response = client.post(
#             "/room/create", headers=_auth_header(), json={"live_id": 1001, "select_difficulty": 1, }
#         )
#         assert response.status_code == 200

#     def teardown_class(self):
#         pass

#     def setup_method(self, method):
#         pass

#     def teardown_method(self, method):
#         pass

#     @pytest.mark.parametrize(
#         "info_dict",
#         [
#             get_correct_info_dict(),
#             pytest.param(
#                 get_incorrect_info_dict_datetime(
#                     info_dict=get_correct_info_dict()),
#                 marks=pytest.mark.xfail(strict=True),
#             ),
#         ],
#     )
#     def test_hogehoge():
#         hogehoge()
