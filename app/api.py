# Standard Library
from logging import getLogger
from logging.config import dictConfig
from pathlib import Path
from typing import List
from typing import Optional

# Third Party Library
import yaml
from fastapi import Depends
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.security.http import HTTPAuthorizationCredentials
from fastapi.security.http import HTTPBearer
from pydantic import BaseModel

if __name__ == "__main__":
    filepath = Path(__file__).parents[1] / "conf" / "logging.yml"
    with open(file=str(filepath), mode="rt") as f:
        config_dict = yaml.safe_load(f)
    dictConfig(config=config_dict)
    del filepath, config_dict


# Local Library
from . import model
from . import room_model
from .model import SafeUser

logger = getLogger(__name__)

app = FastAPI()

# Sample APIs


@app.get("/")
async def root():
    return {"message": "Hello World"}


# User APIs


class UserCreateRequest(BaseModel):
    user_name: str
    leader_card_id: int


class UserCreateResponse(BaseModel):
    user_token: str


@app.post("/user/create", response_model=UserCreateResponse)
def user_create(req: UserCreateRequest):
    """新規ユーザー作成"""
    token = model.create_user(req.user_name, req.leader_card_id)
    return UserCreateResponse(user_token=token)


bearer = HTTPBearer()


def get_auth_token(cred: HTTPAuthorizationCredentials = Depends(bearer)) -> str:
    assert cred is not None
    if not cred.credentials:
        raise HTTPException(status_code=401, detail="invalid credential")
    return cred.credentials


@app.get("/user/me", response_model=SafeUser)
def user_me(token: str = Depends(get_auth_token)):
    user = model.get_user_by_token(token)
    if user is None:
        raise HTTPException(status_code=404)
    # logger.info(f"user_me({token=}, {user=})")
    return user


class Empty(BaseModel):
    pass


@app.post("/user/update", response_model=Empty)
def update(req: UserCreateRequest, token: str = Depends(get_auth_token)):
    """Update user attributes"""
    # logger.info(req)
    model.update_user(token, req.user_name, req.leader_card_id)
    return {}


class RoomCreateRequest(BaseModel):
    live_id: int
    select_difficulty: room_model.LiveDifficulty


class RoomCreateResponse(BaseModel):
    room_id: int


@app.post("/room/create", response_model=RoomCreateResponse)
def room_create(req: RoomCreateRequest, token: str = Depends(get_auth_token)):
    room_id: int = room_model.create_room(req.live_id)
    user: Optional[SafeUser] = model.get_user_by_token(token)
    if user is None:
        return HTTPException(status_code=400, detail="Unknown user token")
    room_model.join_room(room_id=room_id, user_id=user.id, live_difficulty=req.select_difficulty, is_host=True)
    logger.info(f"create room: {room_id=}")
    return RoomCreateResponse(room_id=room_id)


class RoomListRequest(BaseModel):
    live_id: int


class RoomListResponse(BaseModel):
    room_info_list: List[room_model.RoomInfo]


@app.post("/room/list", response_model=RoomListResponse)
def room_list(req: RoomListRequest):
    rooms: List[room_model.RoomInfo] = room_model.get_rooms_by_live_id(req.live_id)
    logger.info(f"{rooms=}")
    logger.info(f"{type(rooms)=}")
    return RoomListResponse(room_info_list=rooms)


class RoomWaitRequest(BaseModel):
    room_id: int


class RoomWaitResponse(BaseModel):
    status: room_model.WaitRoomStatus
    room_user_list: List[room_model.RoomUser]


@app.post("/room/wait", response_model=RoomWaitResponse)
def room_wait(req: RoomWaitRequest, token: str = Depends(get_auth_token)):
    room_status: room_model.RoomStatus = room_model.get_room_status(room_id=req.room_id)
    logger.info(f"{room_status=}")
    user: Optional[SafeUser] = model.get_user_by_token(token)
    if user is None:
        return HTTPException(status_code=400, detail="Unknown user token")
    room_user_list: List[room_model.RoomUser] = room_model.get_room_users(room_id=req.room_id, user_id_req=user.id)
    logger.info(f"{room_user_list=}")
    return RoomWaitResponse(status=room_status.status, room_user_list=room_user_list)


class RoomJoinRequest(BaseModel):
    room_id: int
    select_difficulty: room_model.LiveDifficulty


class RoomJoinResponse(BaseModel):
    join_room_result: room_model.JoinRoomResult  # ルーム入場結果


@app.post("/room/join", response_model=RoomJoinResponse)
def room_join(req: RoomJoinRequest, token: str = Depends(get_auth_token)):
    user: Optional[SafeUser] = model.get_user_by_token(token)
    if user is None:
        return HTTPException(status_code=400, detail="Unknown user token")
    join_room_result: room_model.JoinRoomResult = room_model.join_room(
        room_id=req.room_id,
        user_id=user.id,
        live_difficulty=req.select_difficulty,
    )
    return RoomJoinResponse(join_room_result=join_room_result)
