from collections.abc import Generator

import pytest
from sqlmodel import Session, delete

from app.core.db import engine, init_db
from app.models import User


@pytest.fixture(scope="session", autouse=True)
def db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        init_db(session)
        yield session
        statement = delete(User)
        session.execute(statement)
        session.commit()
