import json
import uuid
from enum import Enum, IntEnum
from typing import List, Optional

import sqlalchemy
from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import NoResultFound
from .model import SafeUser

from .db import engine

max_user_count: int = 4


class LiveDifficulty(IntEnum):
    normal: int = 1
    hard: int = 2


class JoinedRoomResult(IntEnum):
    Ok: int = 1
    RoomFull: int = 2
    Disbanded: int = 3
    OhterError: int = 4


class WaitRoomStatus(IntEnum):
    Waiting = 1  # ホストがライブ開始ボタン押すのを待っている
    LiveStart = 2  # ライブ画面遷移OK
    Dissolution = 3  # 解散された


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
    is_me: bool  # 代入時にチェック？
    is_host: bool


class RoomUserRow(BaseModel):
    room_id: int
    user_id: int
    live_difficulty: int
    is_host: bool


def create_room(live_id: int) -> int:
    with engine.begin() as conn:
        result: sqlalchemy.engine.CursorResult = conn.execute(
            # text(
            #     "INSERT INTO `room` SET `live_id`=:live_id, `joined_user_count`=:joined_user_count RETURNING *"
            # ),
            text(
                "INSERT INTO `room` (live_id, joined_user_count) VALUES (:live_id, :joined_user_count)"
            ),
            dict(
                live_id=live_id,
                joined_user_count=0,
            ),
        )
        # TODO: need exception?
        print(f"{result=}")
        print(f"{result.lastrowid=}")
        return result.lastrowid


def _update_room_user_count(conn, room_id: int, offset: int):
    result: sqlalchemy.engine.CursorResult = conn.execute(
        text("SELECT joined_user_count FROM `room` WHERE `room_id`=:room_id"),
        dict(room_id=room_id),
    )
    joined_user_count: int = result.one().joined_user_count
    joined_user_count += offset
    result: sqlalchemy.engine.CursorResult = conn.execute(
        text(
            "UPDATE `room` SET `joined_user_count`=:joined_user_count WHERE `room_id`=:room_id"
        ),
        dict(
            joined_user_count=joined_user_count,
            room_id=room_id,
        ),
    )
    return


def _create_room_user(conn, room_id: int, user_id: int, live_difficulty: LiveDifficulty, is_host: bool):
    result: sqlalchemy.engine.CursorResult = conn.execute(
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
    print(f"{result=}")


def join_room(room_id: int, user_id: int, live_difficulty: LiveDifficulty, is_host: bool) -> None:
    with engine.begin() as conn:
        _create_room_user(conn, room_id, user_id, live_difficulty, is_host)
        _update_room_user_count(conn=conn, room_id=room_id, offset=1)
    return


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


