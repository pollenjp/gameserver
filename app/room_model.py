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
from sqlalchemy.exc import NoResultFound  # type: ignore

# Local Library
from .db import engine

logger = getLogger(__name__)

# max_user_count: int = 4
max_user_count: int = 2


class RoomDBTableName:
    """table column names"""

    table_name: str = "room"
    room_id: str = "room_id"  # bigint NOT NULL AUTO_INCREMENT
    live_id: str = "live_id"  # bigint NOT NULL
    joined_user_count: str = "joined_user_count"  # bigint NOT NULL
    status: str = "status"  # NOT NULL DEFAULT 1


class RoomUserDBTableName:
    """table column names"""

    table_name: str = "room_user"

    room_id: str = "room_id"  # primary key
    user_id: str = "user_id"  # primary key
    user_name: str = "user_name"
    leader_card_id: str = "leader_card_id"
    select_difficulty: str = "select_difficulty"
    is_host: str = "is_host"
    judge_count_perfect: str = "judge_count_perfect"
    judge_count_great: str = "judge_count_great"
    judge_count_good: str = "judge_count_good"
    judge_count_bad: str = "judge_count_bad"
    judge_count_miss: str = "judge_count_miss"
    score: str = "score"
    end_playing: str = "end_playing"  # bool


const_judge_count_order: List[str] = [
    RoomUserDBTableName.judge_count_perfect,
    RoomUserDBTableName.judge_count_great,
    RoomUserDBTableName.judge_count_good,
    RoomUserDBTableName.judge_count_bad,
    RoomUserDBTableName.judge_count_miss,
]


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
    user_name: str
    leader_card_id: int
    select_difficulty: int
    is_me: bool = False
    is_host: bool

    class Config:
        orm_mode = True


def create_room(live_id: int) -> int:
    with engine.begin() as conn:
        query: str = " ".join(
            [
                f"INSERT INTO `{ RoomDBTableName.table_name }`",
                f"SET `{ RoomDBTableName.live_id }`=:live_id,"
                f"`{ RoomDBTableName.joined_user_count }`=:joined_user_count",
            ]
        )
        result: CursorResult = conn.execute(text(query), dict(live_id=live_id, joined_user_count=0))
        logger.info(f"{result=}")
        logger.info(f"{result.lastrowid=}")
        room_id: int = result.lastrowid
        return room_id


def _update_room_user_count(conn, room_id: int, offset: int) -> None:
    query: str = " ".join(
        [
            f"UPDATE `{ RoomDBTableName.table_name }`",
            f"SET `{ RoomDBTableName.joined_user_count }`={ RoomDBTableName.joined_user_count } + :offset",
            f"WHERE `{ RoomDBTableName.room_id }`=:room_id",
        ]
    )
    result: CursorResult = conn.execute(
        text(query),
        dict(
            offset=offset,
            room_id=room_id,
        ),
    )
    logger.info(f"{result=}")
    return


def _create_room_user(
    conn,
    room_id: int,
    user_id: int,
    user_name: str,
    leader_card_id: int,
    live_difficulty: LiveDifficulty,
    is_host: bool,
):
    query: str = " ".join(
        (
            f"INSERT INTO `{ RoomUserDBTableName.table_name }`",
            "SET",
            ", ".join(
                (
                    f"`{ RoomUserDBTableName.room_id }`=:room_id",
                    f"`{ RoomUserDBTableName.user_id }`=:user_id",
                    f"`{ RoomUserDBTableName.user_name }`=:user_name",
                    f"`{ RoomUserDBTableName.leader_card_id }`=:leader_card_id",
                    f"`{ RoomUserDBTableName.select_difficulty }`=:live_difficulty",
                    f"`{ RoomUserDBTableName.is_host }`=:is_host",
                )
            ),
        )
    )
    result: CursorResult = conn.execute(
        text(query),
        dict(
            room_id=room_id,
            user_id=user_id,
            user_name=user_name,
            leader_card_id=leader_card_id,
            live_difficulty=int(live_difficulty),
            is_host=is_host,
        ),
    )
    logger.info(f"{result=}")


def _get_room_info_by_id(conn, room_id: int) -> Optional[RoomInfo]:
    query: str = " ".join(
        (
            f"SELECT `{ RoomDBTableName.room_id }`, `{ RoomDBTableName.live_id }`, `{ RoomDBTableName.joined_user_count }`",
            f"FROM `{ RoomDBTableName.table_name }`",
            f"WHERE `{ RoomDBTableName.room_id }`=:room_id",
        )
    )
    result = conn.execute(text(query), dict(room_id=room_id))
    row = result.one()
    if row is None:
        return row
    return RoomInfo.from_orm(row)


def _get_room_status(conn, room_id: int) -> RoomStatus:
    query: str = " ".join(
        [
            f"SELECT `{ RoomDBTableName.room_id }`, `{ RoomDBTableName.status }`",
            f"FROM `{ RoomDBTableName.table_name }`",
            f"WHERE `{ RoomDBTableName.room_id }`=:room_id",
        ]
    )
    result = conn.execute(text(query), dict(room_id=room_id))
    try:
        row = result.one()
    except NoResultFound as e:
        logger.error(f"{e=}", exc_info=True)
        raise e
    return RoomStatus.from_orm(row)


def join_room(
    user_id: int,
    room_id: int,
    user_name: str,
    leader_card_id: int,
    live_difficulty: LiveDifficulty,
    is_host: bool = False,
) -> JoinRoomResult:
    with engine.begin() as conn:
        try:
            # lock
            conn.execute(
                text(
                    f"SELECT * FROM `{ RoomDBTableName.table_name }` WHERE `{ RoomDBTableName.room_id }`=:room_id FOR UPDATE"
                ),
                dict(room_id=room_id),
            )

            room_info: Optional[RoomInfo] = _get_room_info_by_id(conn, room_id=room_id)
            if room_info is None:
                return JoinRoomResult.Disbanded
            if room_info.joined_user_count >= room_info.max_user_count:
                return JoinRoomResult.RoomFull

            room_status: RoomStatus = _get_room_status(conn=conn, room_id=room_id)
            if room_status.status != WaitRoomStatus.Waiting:
                return JoinRoomResult.OhterError

            _create_room_user(
                conn=conn,
                room_id=room_id,
                user_id=user_id,
                user_name=user_name,
                leader_card_id=leader_card_id,
                live_difficulty=live_difficulty,
                is_host=is_host,
            )
            _update_room_user_count(conn=conn, room_id=room_id, offset=1)

            _ = conn.execute(text("COMMIT"), {})
            return JoinRoomResult.Ok
        except Exception as e:
            logger.info(f"{e=}", exc_info=True)
            return JoinRoomResult.OhterError


def _get_rooms_by_live_id(conn, live_id: int, room_status:WaitRoomStatus = WaitRoomStatus.Waiting) -> Iterator[RoomInfo]:
    """list rooms

    Args:
        conn ([type]): sql connection
        live_id (int):
            If 0, get all rooms.
            Others, get rooms by live_id.


    Yields:
        [type]: [description]
    """
    query: str = " ".join(
        [
            "SELECT",
            ", ".join(
                (
                    f"`{ RoomDBTableName.room_id }`",
                    f"`{ RoomDBTableName.live_id }`",
                    f"`{ RoomDBTableName.joined_user_count }`",
                )
            ),
            f"FROM `{ RoomDBTableName.table_name }`",
            f"WHERE `{ RoomDBTableName.status }`=:room_status",
        ]
        + ([] if live_id == 0 else [f"AND `{ RoomDBTableName.live_id }`=:live_id"])
    )
    result = conn.execute(text(query), dict(room_status=int(room_status), live_id=live_id))
    for row in result.all():
        yield RoomInfo.from_orm(row)


def get_rooms_by_live_id(live_id: int) -> List[RoomInfo]:
    with engine.begin() as conn:
        return list(_get_rooms_by_live_id(conn, live_id))


def get_room_status(room_id: int) -> RoomStatus:
    with engine.begin() as conn:
        return _get_room_status(conn, room_id)


def _get_room_users(conn, room_id: int, user_id_req: int = None) -> Iterator[RoomUser]:
    query: str = " ".join(
        [
            "SELECT",
            f"`{ RoomUserDBTableName.room_id }`,",
            f"`{ RoomUserDBTableName.user_id }`,",
            f"`{ RoomUserDBTableName.user_name }`,",
            f"`{ RoomUserDBTableName.leader_card_id }`,",
            f"`{ RoomUserDBTableName.select_difficulty }`,",
            f"`{ RoomUserDBTableName.is_host }`",
            f"FROM `{ RoomUserDBTableName.table_name }`",
            f"WHERE `{ RoomUserDBTableName.room_id }`=:room_id",
        ]
    )
    result = conn.execute(text(query), dict(room_id=room_id))
    for row in result.all():
        room_user: RoomUser = RoomUser.from_orm(row)
        logger.info(f"{room_user}")
        if user_id_req is not None and room_user.user_id == user_id_req:
            room_user.is_me = True
        yield room_user


def get_room_users(room_id: int, user_id_req: int) -> List[RoomUser]:
    with engine.begin() as conn:
        users: List[RoomUser] = list(_get_room_users(conn, room_id, user_id_req=user_id_req))
    return users


def start_room(room_id: int) -> None:
    """update room's status to LiveStart

    Args:
        room_id (int): [description]

    Returns:
        [type]: [description]
    """
    with engine.begin() as conn:
        query: str = " ".join(
            [
                f"UPDATE `{ RoomDBTableName.table_name }`",
                f"SET `{ RoomDBTableName.status }`=:status",
                f"WHERE `{ RoomDBTableName.room_id }`=:room_id",
            ]
        )
        result = conn.execute(
            text(query),
            dict(
                status=int(WaitRoomStatus.LiveStart),
                room_id=room_id,
            ),
        )
        logger.info(f"{result=}")
        return


class RoomUserResult(BaseModel):
    room_id: int
    user_id: int
    judge_count_perfect: int
    judge_count_great: int
    judge_count_good: int
    judge_count_bad: int
    judge_count_miss: int
    score: int
    end_playing: bool

    class Config:
        orm_mode = True


def _store_room_user_result(conn, room_user_result: RoomUserResult) -> None:
    query: str = " ".join(
        [
            f"UPDATE `{ RoomUserDBTableName.table_name }`",
            "SET",
            ", ".join(
                (
                    f"`{ RoomUserDBTableName.judge_count_perfect }`=:judge_count_perfect",
                    f"`{ RoomUserDBTableName.judge_count_great    }`=:judge_count_great",
                    f"`{ RoomUserDBTableName.judge_count_good   }`=:judge_count_good",
                    f"`{ RoomUserDBTableName.judge_count_bad     }`=:judge_count_bad",
                    f"`{ RoomUserDBTableName.judge_count_miss    }`=:judge_count_miss",
                    f"`{ RoomUserDBTableName.score }`=:score",
                    f"`{ RoomUserDBTableName.end_playing }`=:end_playing",
                )
            ),
            f"WHERE `{ RoomUserDBTableName.room_id }`=:room_id",
            f"AND `{ RoomUserDBTableName.user_id }`=:user_id",
        ]
    )
    result = conn.execute(
        text(query),
        dict(
            judge_count_perfect=room_user_result.judge_count_perfect,
            judge_count_great=room_user_result.judge_count_great,
            judge_count_good=room_user_result.judge_count_good,
            judge_count_bad=room_user_result.judge_count_bad,
            judge_count_miss=room_user_result.judge_count_miss,
            score=room_user_result.score,
            end_playing=room_user_result.end_playing,
            room_id=room_user_result.room_id,
            user_id=room_user_result.user_id,
        ),
    )
    logger.info(f"{result=}")
    return


def _get_room_user_result(conn, room_id: int, user_id: int) -> Optional[RoomUserResult]:
    query: str = " ".join(
        [
            "SELECT",
            ", ".join(
                (
                    f"`{ RoomUserDBTableName.room_id }`",
                    f"`{ RoomUserDBTableName.user_id }`",
                    f"`{ RoomUserDBTableName.judge_count_perfect }`",
                    f"`{ RoomUserDBTableName.judge_count_great }`",
                    f"`{ RoomUserDBTableName.judge_count_good }`",
                    f"`{ RoomUserDBTableName.judge_count_bad }`",
                    f"`{ RoomUserDBTableName.judge_count_miss }`",
                    f"`{ RoomUserDBTableName.score }`",
                    f"`{ RoomUserDBTableName.end_playing }`",
                )
            ),
            f"FROM `{ RoomUserDBTableName.table_name }`",
            f"WHERE `{ RoomUserDBTableName.room_id }`=:room_id",
            f"AND `{ RoomUserDBTableName.user_id }`=:user_id",
        ]
    )
    result = conn.execute(
        text(query),
        dict(room_id=room_id, user_id=user_id),
    )
    try:
        row = result.one()
    except NoResultFound as e:
        logger.warning(f"{e=}", exc_info=True)
        return None
    return RoomUserResult.from_orm(row)


class ResultUser(BaseModel):
    user_id: int
    judge_count_list: List[int]
    score: int


def get_result_user_list(room_id: int) -> List[ResultUser]:
    with engine.begin() as conn:
        result_user_list: List[ResultUser] = []

        room_user: RoomUser
        for room_user in _get_room_users(conn, room_id=room_id):
            room_user_result: Optional[RoomUserResult] = _get_room_user_result(
                conn,
                room_id=room_id,
                user_id=room_user.user_id,
            )
            if room_user_result is None:
                logger.warning(f"{room_user.user_id=} is empty")
                continue
            if room_user_result.end_playing is False:
                # 他のプレイヤーが結果を返すまでポーリングし続ける
                return []
            result_user_list.append(
                ResultUser(
                    user_id=room_user.user_id,
                    judge_count_list=[getattr(room_user_result, judge_name) for judge_name in const_judge_count_order],
                    score=room_user_result.score,
                )
            )
        return result_user_list


def _drop_room(conn, room_id: int):
    query: str = " ".join(
        [
            f"DELETE FROM `{ RoomDBTableName.table_name }`",
            f"WHERE `{ RoomDBTableName.room_id }`=:room_id",
        ]
    )
    result = conn.execute(
        text(query),
        dict(
            room_id=room_id,
        ),
    )
    if result.rowcount > 0:
        logger.info(f"successfully drop {room_id=}")
    else:
        logger.error(f"failed to drop {room_id=}")


def _get_room_joined_user_count(conn, room_id: int) -> int:
    query: str = " ".join(
        [
            f"SELECT `{ RoomDBTableName.joined_user_count }`",
            f"FROM `{ RoomDBTableName.table_name }`",
            f"WHERE `{ RoomDBTableName.room_id }`=:room_id",
        ]
    )
    result = conn.execute(text(query), dict(room_id=room_id))
    row = result.one()
    return int(row["joined_user_count"])


def _decrement_room_user_and_try_to_drop_room(conn, room_id: int) -> None:
    # lock
    conn.execute(
        text(f"SELECT * FROM `{ RoomDBTableName.table_name }` WHERE `{ RoomDBTableName.room_id }`=:room_id FOR UPDATE"),
        dict(room_id=room_id),
    )
    joined_user_count: int = _get_room_joined_user_count(conn, room_id=room_id)
    # decrement joined_user_count
    _update_room_user_count(conn=conn, room_id=room_id, offset=-1)
    conn.execute(text("COMMIT"), {})
    logger.info(f"{room_id}")
    if joined_user_count == 0:
        # drop the room
        _drop_room(conn=conn, room_id=room_id)
    elif joined_user_count < 0:
        logger.error(f"Something wrong... {joined_user_count=}")
        raise Exception(f"Something wrong... {joined_user_count=}")
    return


def finish_playing(room_user_result: RoomUserResult) -> None:
    with engine.begin() as conn:
        _store_room_user_result(conn=conn, room_user_result=room_user_result)
        _decrement_room_user_and_try_to_drop_room(conn, room_id=room_user_result.room_id)


def _drop_room_user(conn, room_id: int, user_id: int) -> None:
    query: str = " ".join(
        [
            f"DELETE FROM `{ RoomUserDBTableName.table_name }`",
            f"WHERE `{ RoomUserDBTableName.room_id }`=:room_id",
            f"AND `{ RoomUserDBTableName.user_id }`=:user_id",
        ]
    )
    result = conn.execute(
        text(query),
        dict(
            room_id=room_id,
            user_id=user_id,
        ),
    )
    if result.rowcount > 0:
        logger.info(f"{user_id=} is left {room_id=}")
    else:
        logger.warning(f"{user_id=} is not in {room_id=}")
        raise Exception(f"{user_id=} is not in {room_id=}")


def leave_room(room_id: int, user_id: int) -> None:
    with engine.begin() as conn:
        _drop_room_user(conn, room_id=room_id, user_id=user_id)
        _decrement_room_user_and_try_to_drop_room(conn, room_id=room_id)
        return
