
from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import create_engine, String, Integer, Float, Boolean, DateTime, ForeignKey, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


DATABASE_URL = "sqlite:///fundfc.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


class Youth(Base):
    __tablename__ = "youth"

    id: Mapped[int] = mapped_column(primary_key=True)
    participant_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    preferred_name: Mapped[str] = mapped_column(String(100), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)

    consent_status: Mapped[str] = mapped_column(String(30), default="Pending")
    status: Mapped[str] = mapped_column(String(30), default="Active")

    education_goal: Mapped[str] = mapped_column(String(500), default="")
    employment_goal: Mapped[str] = mapped_column(String(500), default="")
    housing_goal: Mapped[str] = mapped_column(String(500), default="")

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)

    youth_id: Mapped[int] = mapped_column(
        ForeignKey("youth.id"),
        nullable=False
    )

    transaction_type: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    category: Mapped[str] = mapped_column(String(100), default="General")
    description: Mapped[str] = mapped_column(String(500), default="")
    reference: Mapped[str] = mapped_column(String(200), default="")

    transaction_date: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )


class Milestone(Base):
    __tablename__ = "milestones"

    id: Mapped[int] = mapped_column(primary_key=True)

    youth_id: Mapped[int] = mapped_column(
        ForeignKey("youth.id"),
        nullable=False
    )

    domain: Mapped[str] = mapped_column(String(100), nullable=False)
    milestone: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="Not started")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)

    due_date: Mapped[str] = mapped_column(String(20), default="")
    notes: Mapped[str] = mapped_column(String(1000), default="")

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )


def init_db():
    """Create FundFC database tables if they do not already exist."""
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_session():
    """Provide a database session and close it when finished."""
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()


def account_balance(session, youth_id):
    """Calculate the current FundFC opportunity-account ledger balance."""

    transactions = session.scalars(
        select(Transaction).where(
            Transaction.youth_id == youth_id
        )
    ).all()

    inflows = {
        "Contribution",
        "Grant",
        "Adjustment In"
    }

    outflows = {
        "Distribution",
        "Fee",
        "Adjustment Out"
    }

    balance = 0.0

    for tx in transactions:

        if tx.transaction_type in inflows:
            balance += float(tx.amount)

        elif tx.transaction_type in outflows:
            balance -= float(tx.amount)

    return balance
