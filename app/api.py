# Standard Library
from logging import getLogger
from logging.config import dictConfig
from pathlib import Path
from typing import List

# Third Party Library
import yaml
from fastapi import Depends
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.security.http import HTTPAuthorizationCredentials
from fastapi.security.http import HTTPBearer
from pydantic import BaseModel

# if __name__ == "__main__":
if True:
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
    try:
        user: SafeUser = model.get_user_by_token(token)
    except HTTPException as e:
        logger.warning(f"{e=}", exc_info=True)
        raise HTTPException(status_code=404)
    logger.info(f"user_me ({token=}, {user=})")
    return user


class EmptyResponse(BaseModel):
    pass


@app.post("/user/update", response_model=EmptyResponse)
def user_update(req: UserCreateRequest, token: str = Depends(get_auth_token)):
    """Update user attributes"""
    logger.warning(f"/usr/update : {req=}")
    model.update_user(token, req.user_name, req.leader_card_id)
    return EmptyResponse()


class RoomCreateRequest(BaseModel):
    live_id: int
    select_difficulty: room_model.LiveDifficulty


class RoomCreateResponse(BaseModel):
    room_id: int


@app.post("/room/create", response_model=RoomCreateResponse)
def room_create(req: RoomCreateRequest, token: str = Depends(get_auth_token)):
    room_id: int = room_model.create_room(req.live_id)
    user: SafeUser = model.get_user_by_token(token)
    room_model.join_room(
        room_id=room_id,
        user_id=user.id,
        leader_card_id=user.leader_card_id,
        live_difficulty=req.select_difficulty,
        is_host=True,
    )
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


class WaitResponseRoomUser(BaseModel):
    user_id: int
    leader_card_id: int
    select_difficulty: int
    is_me: bool = False
    is_host: bool


class RoomWaitResponse(BaseModel):
    status: room_model.WaitRoomStatus
    room_user_list: List[WaitResponseRoomUser]


@app.post("/room/wait", response_model=RoomWaitResponse)
def room_wait(req: RoomWaitRequest, token: str = Depends(get_auth_token)):
    room_status: room_model.RoomStatus = room_model.get_room_status(room_id=req.room_id)
    logger.info(f"{room_status=}")
    user: SafeUser = model.get_user_by_token(token)
    room_user_list: List[room_model.RoomUser] = room_model.get_room_users(room_id=req.room_id, user_id_req=user.id)
    logger.info(f"{room_user_list=}")
    wait_response_room_user_list: List[WaitResponseRoomUser] = [
        WaitResponseRoomUser(
            user_id=room_user.user_id,
            leader_card_id=room_user.leader_card_id,
            select_difficulty=room_user.select_difficulty,
            is_me=room_user.user_id,
            is_host=room_user.is_host,
        )
        for room_user in room_user_list
    ]
    logger.info(f"{wait_response_room_user_list=}")
    return RoomWaitResponse(status=room_status.status, room_user_list=wait_response_room_user_list)


class RoomJoinRequest(BaseModel):
    room_id: int
    select_difficulty: room_model.LiveDifficulty


class RoomJoinResponse(BaseModel):
    join_room_result: room_model.JoinRoomResult  # ルーム入場結果


@app.post("/room/join", response_model=RoomJoinResponse)
def room_join(req: RoomJoinRequest, token: str = Depends(get_auth_token)):
    user: SafeUser = model.get_user_by_token(token)
    join_room_result: room_model.JoinRoomResult = room_model.join_room(
        room_id=req.room_id,
        user_id=user.id,
        leader_card_id=user.leader_card_id,
        live_difficulty=req.select_difficulty,
    )
    return RoomJoinResponse(join_room_result=join_room_result)


class RoomStartRequest(BaseModel):
    room_id: int


@app.post("/room/start", response_model=EmptyResponse)
def room_start(req: RoomStartRequest, token: str = Depends(get_auth_token)):
    room_model.start_room(req.room_id)
    return EmptyResponse()


class RoomEndRequest(BaseModel):
    room_id: int
    judge_count_list: List[int]
    score: int


@app.post("/room/end", response_model=EmptyResponse)
def room_end(req: RoomEndRequest, token: str = Depends(get_auth_token)):
    if len(req.judge_count_list) != 5:
        raise HTTPException(status_code=400, detail="judge_count_list must be 5")
    user: SafeUser = model.get_user_by_token(token)
    room_user_result: room_model.RoomUserResult = room_model.RoomUserResult(
        room_id=req.room_id,
        user_id=user.id,
        judge_count_perfect=req.judge_count_list[0],
        judge_count_great=req.judge_count_list[1],
        judge_count_good=req.judge_count_list[2],
        judge_count_bad=req.judge_count_list[3],
        judge_count_miss=req.judge_count_list[4],
        score=req.score,
    )
    room_model.store_room_user_result(room_user_result=room_user_result)
    return EmptyResponse()


class RoomResultRequest(BaseModel):
    room_id: int


class RoomResultResponse(BaseModel):
    result_user_list: List[room_model.ResultUser]


@app.post("/room/result", response_model=RoomResultResponse)
def room_result(req: RoomResultRequest):
    return RoomResultResponse(result_user_list=room_model.get_result_user_list(req.room_id))


class RoomLeaveRequest(BaseModel):
    room_id: int


@app.post("/room/leave", response_model=EmptyResponse)
def room_leave(req: RoomLeaveRequest, token: str = Depends(get_auth_token)):
    user: SafeUser = model.get_user_by_token(token)
    room_model.leave_room(room_id=req.room_id, user_id=user.id)
    return EmptyResponse()
