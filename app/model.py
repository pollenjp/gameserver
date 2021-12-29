# Standard Library
import uuid
from logging import getLogger
from typing import Optional

# Third Party Library
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.engine import CursorResult  # type: ignore
from sqlalchemy.exc import NoResultFound  # type: ignore

# Local Library
from .db import engine

logger = getLogger(__name__)


class InvalidToken(Exception):
    """指定されたtokenが不正だったときに投げる"""


class SafeUser(BaseModel):
    """token を含まないUser"""

    id: int
    name: str
    leader_card_id: int

    class Config:
        orm_mode = True


def create_user(name: str, leader_card_id: int) -> str:
    """Create new user and returns their token"""
    token = str(uuid.uuid4())
    # NOTE: tokenが衝突したらリトライする必要がある.
    with engine.begin() as conn:
        query: str = r" ".join(
            [
                r"INSERT INTO `user`",
                r"(`name`, `token`, `leader_card_id`)",
                r"VALUES (:name, :token, :leader_card_id)",
            ]
        )
        result: CursorResult = conn.execute(
            text(query),
            {"name": name, "token": token, "leader_card_id": leader_card_id},
        )
        logger.info(f"{result}")
    return token


def _get_user_by_token(conn, token: str) -> Optional[SafeUser]:
    query: str = r"SELECT `id`, `name`, `leader_card_id` FROM `user` WHERE `token`=:token"
    result = conn.execute(text(query), dict(token=token))
    try:
        row = result.one()
    except NoResultFound:
        logger.warning(f"No Result Found: ({query=})")
        return None
    return SafeUser.from_orm(row)


def get_user_by_token(token: str) -> Optional[SafeUser]:
    with engine.begin() as conn:
        return _get_user_by_token(conn, token)


def update_user(token: str, name: str, leader_card_id: int) -> None:
    with engine.begin() as conn:
        user: Optional[SafeUser] = get_user_by_token(token)
        if user is None:
            logger.warning(f"user not found. {name=}, {leader_card_id=}")
            raise InvalidToken
        query: str = r"UPDATE `user` SET `name`=:name, `leader_card_id`=:leader_card_id WHERE `token`=:token"
        result: CursorResult = conn.execute(text(query), dict(name=name, leader_card_id=leader_card_id, token=token))
        logger.info(f"{result=}")
        logger.info(f"{dir(result)=}")
