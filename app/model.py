# Standard Library
import uuid
from logging import getLogger
from typing import Optional

# Third Party Library
from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.engine import CursorResult  # type: ignore
from sqlalchemy.exc import NoResultFound  # type: ignore

# Local Library
from .db import engine

logger = getLogger(__name__)


class UserDBTableName:
    """table column names"""

    table_name: str = "user"

    id: str = "id"  # primary key, bigint NOT NULL AUTO_INCREMENT,
    name: str = "name"  # varchar(255) DEFAULT NULL,
    token: str = "token"  # UNIQUE varchar(255) DEFAULT NULL,
    leader_card_id: str = "leader_card_id"  # int DEFAULT NULL,


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
        query: str = " ".join(
            [
                f"INSERT INTO `{ UserDBTableName.table_name }`",
                "SET",
                ", ".join(
                    (
                        f"`{ UserDBTableName.name }`=:name",
                        f"`{ UserDBTableName.token }`=:token",
                        f"`{ UserDBTableName.leader_card_id }`=:leader_card_id",
                    )
                ),
            ]
        )
        result: CursorResult = conn.execute(
            text(query),
            {
                "name": name,
                "token": token,
                "leader_card_id": leader_card_id,
            },
        )
        logger.info(f"{result}")
    return token


def _get_user_by_token(conn, token: str) -> Optional[SafeUser]:
    query: str = " ".join(
        (
            "SELECT",
            ", ".join(
                (
                    f"`{ UserDBTableName.id }`",
                    f"`{ UserDBTableName.name }`",
                    f"`{ UserDBTableName.leader_card_id }`",
                )
            ),
            f"FROM `{ UserDBTableName.table_name }`",
            f"WHERE `{ UserDBTableName.token }`=:token",
        )
    )
    result = conn.execute(text(query), dict(token=token))
    try:
        row = result.one()
    except NoResultFound:
        logger.warning(f"No Result Found: ({query=})")
        return None
    return SafeUser.from_orm(row)


def get_user_by_token(token: str) -> SafeUser:
    with engine.begin() as conn:
        user: Optional[SafeUser] = _get_user_by_token(conn, token)
        if user is None:
            raise HTTPException(status_code=400, detail="Unknown user token")
        return user


def update_user(token: str, name: str, leader_card_id: int) -> None:
    with engine.begin() as conn:
        user: Optional[SafeUser] = _get_user_by_token(conn, token)
        if user is None:
            logger.warning(f"user not found. {name=}, {leader_card_id=}")
            raise InvalidToken
        query: str = " ".join(
            (
                f"UPDATE `{ UserDBTableName.table_name }`",
                "SET",
                ", ".join(
                    (
                        f"`{ UserDBTableName.name }`=:name",
                        f"`{ UserDBTableName.leader_card_id }`=:leader_card_id",
                    )
                ),
                f"WHERE `{ UserDBTableName.token }`=:token",
            )
        )
        result: CursorResult = conn.execute(text(query), dict(name=name, leader_card_id=leader_card_id, token=token))
        logger.info(f"{result=}")
        logger.info(f"{dir(result)=}")
