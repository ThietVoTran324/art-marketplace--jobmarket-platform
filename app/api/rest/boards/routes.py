from typing import Optional

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, insert, select, update

from app.api.rest.dependencies import db, filter, user_id
from app.api.rest.ownership import assert_board_owner
from app.api.rest.pins.schemas import PinOut
from app.celery.tasks import make_update_save_pin
from app.postgresql.models import BoardsOrm, PinsOrm, UsersOrm, board_pins

from .schemas import BoardCreate, BoardResponse

router = APIRouter(prefix="/boards", tags=["boards"])


@router.post("/", response_model=BoardResponse, status_code=status.HTTP_201_CREATED)
async def create_board(board: BoardCreate, db: db, user_id: user_id):
    new_board = BoardsOrm(user_id=user_id, title=board.title)
    db.add(new_board)
    await db.commit()
    await db.refresh(new_board)
    return new_board


@router.patch("/selected", status_code=status.HTTP_204_NO_CONTENT)
async def update_user_board_selected(db: db, user_id: user_id, board_id: int):
    await assert_board_owner(db, board_id, user_id)
    user = await db.scalar(
        update(UsersOrm)
        .where(UsersOrm.id == user_id)
        .values(selected_board=board_id)
        .returning(UsersOrm)
    )
    await db.commit()


@router.patch("/selected/disable", status_code=status.HTTP_204_NO_CONTENT)
async def update_user_board_disable(db: db, user_id: user_id):
    user = await db.scalar(
        update(UsersOrm)
        .where(UsersOrm.id == user_id)
        .values(selected_board=None)
        .returning(UsersOrm)
    )
    await db.commit()


@router.get("/selected", response_model=Optional[BoardResponse])
async def get_user_selected_board(db: db, user_id: user_id):
    stmt = (
        select(BoardsOrm)
        .join(UsersOrm, UsersOrm.selected_board == BoardsOrm.id)
        .where(UsersOrm.id == user_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


@router.get("/user/{id}", response_model=list[BoardResponse])
async def get_user_boards(id: int, db: db, user_id: user_id):
    result = await db.execute(select(BoardsOrm).where(BoardsOrm.user_id == id))
    boards = result.scalars().all()
    return boards


@router.get("/me", response_model=list[BoardResponse])
async def get_me_user_boards(db: db, user_id: user_id):
    result = await db.execute(select(BoardsOrm).where(BoardsOrm.user_id == user_id))
    boards = result.scalars().all()
    return boards


@router.post("/{board_id}/pins/{pin_id}")
async def add_pin_to_board(board_id: int, pin_id: int, db: db, user_id: user_id):
    """Add a pin to a board."""
    await assert_board_owner(db, board_id, user_id)
    pin = await db.scalar(select(PinsOrm).where(PinsOrm.id == pin_id))
    if pin is None:
        raise HTTPException(status_code=404, detail="Pin not found")

    existing_link = await db.execute(
        select(board_pins).where(
            (board_pins.c.board_id == board_id) & (board_pins.c.pin_id == pin_id)
        )
    )
    if existing_link.scalar():
        raise HTTPException(status_code=409, detail="Pin is already in the board")

    stmt = insert(board_pins).values(board_id=board_id, pin_id=pin_id)
    await db.execute(stmt)
    await db.commit()

    if pin.user_id != user_id:
        make_update_save_pin.delay(pin.user_id, user_id, pin_id, "Board")

    return {"message": "Pin added to board"}


@router.delete("/{board_id}/pins/{pin_id}")
async def remove_pin_from_board(board_id: int, pin_id: int, db: db, user_id: user_id):
    """Remove a pin from a board."""
    await assert_board_owner(db, board_id, user_id)
    stmt = delete(board_pins).where(
        (board_pins.c.board_id == board_id) & (board_pins.c.pin_id == pin_id)
    )
    result = await db.execute(stmt)
    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Pin not found in board")

    return {"message": "Pin removed from board"}


@router.get("/{board_id}", response_model=list[PinOut])
async def get_pins_by_boardg(board_id: int, user_id: user_id, db: db, filter: filter):
    # Newest saves first (board_pins.created_at).
    result = await db.execute(
        select(board_pins.c.pin_id)
        .where(board_pins.c.board_id == board_id)
        .order_by(board_pins.c.created_at.desc(), board_pins.c.pin_id.desc())
    )
    pin_ids = [row[0] for row in result.all()]
    page_ids = pin_ids[filter.offset : filter.offset + filter.limit]
    if not page_ids:
        return []
    pins_by_id = {
        p.id: p
        for p in (
            await db.scalars(select(PinsOrm).where(PinsOrm.id.in_(page_ids)))
        ).all()
    }
    return [pins_by_id[pid] for pid in page_ids if pid in pins_by_id]


@router.delete("/{board_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_board(board_id: int, db: db, user_id: user_id):
    board = await assert_board_owner(db, board_id, user_id)
    await db.delete(board)
    await db.commit()

    return {"message": "Board deleted successfully"}
