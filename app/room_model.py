# Standard Library
from enum import IntEnum
from logging import getLogger
from typing import Iterator
from typing import List
from typing import Optional

# Third Party Library
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.engine import CursorResult  # type: ignore

# Local Library
from .db import engine

logger = getLogger(__name__)

max_user_count: int = 4


class LiveDifficulty(IntEnum):
    normal: int = 1
    hard: int = 2


class JoinRoomResult(IntEnum):
    Ok: int = 1
    RoomFull: int = 2
    Disbanded: int = 3
    OhterError: int = 4


class WaitRoomStatus(IntEnum):
    Waiting = 1  # ホストがライブ開始ボタン押すのを待っている
    LiveStart = 2  # ライブ画面遷移OK
    Dissolution = 3  # 解散された


class RoomStatus(BaseModel):
    room_id: int
    status: WaitRoomStatus

    class Config:
        orm_mode = True


class RoomInfo(BaseModel):
    room_id: int
    live_id: int
    joined_user_count: int
    max_user_count: int = max_user_count

    class Config:
        orm_mode = True


class RoomUser(BaseModel):
    room_id: int
    user_id: int
    live_difficulty: int
    is_me: bool = False
    is_host: bool

    class Config:
        orm_mode = True


class RoomUserRow(BaseModel):
    room_id: int
    user_id: int
    live_difficulty: int
    is_host: bool


def create_room(live_id: int) -> int:
    with engine.begin() as conn:
        result: CursorResult = conn.execute(
            text("INSERT INTO `room` SET `live_id`=:live_id, `joined_user_count`=:joined_user_count"),
            # text("INSERT INTO `room` (live_id, joined_user_count) VALUES (:live_id, :joined_user_count)"),
            dict(
                live_id=live_id,
                joined_user_count=0,
            ),
        )
        # TODO: need exception?
        logger.info(f"{result=}")
        logger.info(f"{result.lastrowid=}")
        room_id: int = result.lastrowid
        return room_id


def _update_room_user_count(conn, room_id: int, offset: int):
    result_select: CursorResult = conn.execute(
        text("SELECT joined_user_count FROM `room` WHERE `room_id`=:room_id"),
        dict(room_id=room_id),
    )
    joined_user_count: int = result_select.one().joined_user_count
    joined_user_count += offset
    result_update: CursorResult = conn.execute(
        text("UPDATE `room` SET `joined_user_count`=:joined_user_count WHERE `room_id`=:room_id"),
        dict(
            joined_user_count=joined_user_count,
            room_id=room_id,
        ),
    )
    logger.info(f"{result_update=}")
    return


def _create_room_user(conn, room_id: int, user_id: int, live_difficulty: LiveDifficulty, is_host: bool):
    result: CursorResult = conn.execute(
        text(
            "INSERT INTO `room_user` "
            "SET "
            "`room_id`=:room_id, "
            "`user_id`=:user_id, "
            "`live_difficulty`=:live_difficulty, "
            "`is_host`=:is_host ",
        ),
        dict(
            room_id=room_id,
            user_id=user_id,
            live_difficulty=int(live_difficulty),
            is_host=is_host,
        ),
    )
    logger.info(f"{result=}")


def _get_room_info_by_id(conn, room_id: int) -> Optional[RoomInfo]:
    result = conn.execute(
        text("SELECT `room_id`, `live_id`, `joined_user_count` FROM `room` WHERE `room_id`=:room_id"),
        dict(room_id=room_id),
    )
    row = result.one()
    if row is None:
        return row
    return RoomInfo.from_orm(row)


def join_room(user_id: int, room_id: int, live_difficulty: LiveDifficulty, is_host: bool = False) -> JoinRoomResult:
    with engine.begin() as conn:
        try:
            room_info: Optional[RoomInfo] = _get_room_info_by_id(conn, room_id=room_id)
            if room_info is None:
                return JoinRoomResult.Disbanded
            if room_info.joined_user_count >= room_info.max_user_count:
                return JoinRoomResult.RoomFull
            _create_room_user(conn, room_id, user_id, live_difficulty, is_host)
            _update_room_user_count(conn=conn, room_id=room_id, offset=1)
            return JoinRoomResult.Ok
        except Exception as e:
            # Standard Library
            import traceback

            logger.info(f"{traceback.format_exc()}")
            logger.info(f"{e=}")
            return JoinRoomResult.OhterError


def _get_rooms_by_live_id(conn, live_id: int):
    """
    to list rooms
    """
    result = conn.execute(
        text("SELECT `room_id`, `live_id`, `joined_user_count` FROM `room` WHERE `live_id`=:live_id"),
        dict(live_id=live_id),
    )
    for row in result.all():
        yield RoomInfo.from_orm(row)


def get_rooms_by_live_id(live_id: int) -> List[RoomInfo]:
    with engine.begin() as conn:
        return list(_get_rooms_by_live_id(conn, live_id))


def _get_room_status(conn, room_id: int) -> RoomStatus:
    result = conn.execute(
        text("SELECT `room_id`, `status` FROM `room` WHERE `room_id`=:room_id"),
        dict(room_id=room_id),
    )
    return RoomStatus.from_orm(result.one())


def get_room_status(room_id: int) -> RoomStatus:
    with engine.begin() as conn:
        return _get_room_status(conn, room_id)


def _get_room_users(conn, room_id: int, user_id_req: int) -> Iterator[RoomUser]:
    result = conn.execute(
        text("SELECT `room_id`, `user_id`, `live_difficulty`, `is_host` FROM `room_user` WHERE `room_id`=:room_id"),
        dict(room_id=room_id),
    )
    for row in result.all():
        room_user: RoomUser = RoomUser.from_orm(row)
        logger.info(f"{room_user}")
        if room_user.user_id == user_id_req:
            room_user.is_me = True
        yield room_user


def get_room_users(room_id: int, user_id_req: int) -> List[RoomUser]:
    with engine.begin() as conn:
        users: List[RoomUser] = list(_get_room_users(conn, room_id, user_id_req=user_id_req))
    return users
