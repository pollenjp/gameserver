from enum import Enum
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security.http import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from . import model
from .model import SafeUser
from . import room_model

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
    # print(f"user_me({token=}, {user=})")
    return user


class Empty(BaseModel):
    pass


@app.post("/user/update", response_model=Empty)
def update(req: UserCreateRequest, token: str = Depends(get_auth_token)):
    """Update user attributes"""
    # print(req)
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
    user: SafeUser = model.get_user_by_token(token)
    room_model.join_room(room_id=room_id, user_id=user.id,
                         live_difficulty=req.select_difficulty, is_host=True)
    print(f"create room: {room_id=}")
    return RoomCreateResponse(room_id=room_id)


class RoomListRequest(BaseModel):
    live_id: int


class RoomListResponse(BaseModel):
    room_info_list: List[room_model.RoomInfo]


@app.post("/room/list", response_model=RoomListResponse)
def room_list(req: RoomListRequest):
    rooms: List[room_model.RoomInfo] = room_model.get_rooms_by_live_id(
        req.live_id)
    print(f"{rooms=}")
    print(f"{type(rooms)=}")
    return RoomListResponse(room_info_list=rooms)


class RoomWaitRequest(BaseModel):
    room_id: int


class RoomWaitResponse(BaseModel):
    status: room_model.WaitRoomStatus
    room_user_list: List[room_model.RoomUser]


@app.post("/room/wait", response_model=RoomWaitResponse)
def room_list(req: RoomWaitRequest, token: str = Depends(get_auth_token)):
    room_status: room_model.WaitRoomStatus = room_model.get_room_status(
        room_id=req.room_id)
    print(f"{room_status=}")
    user_id: SafeUser = model.get_user_by_token(token)
    room_user_list: List[room_model.RoomUser] = room_model.get_room_users(
        room_id=req.room_id, user_id_req=user_id.id)
    print(f"{room_user_list=}")
    return RoomWaitResponse(status=room_status.status, room_user_list=room_user_list)
