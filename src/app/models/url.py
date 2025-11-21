from datetime import datetime
from sqlalchemy import String, DateTime, Index, BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..core.db.database import Base


class URL(Base):
    """URL shortening model"""

    __tablename__ = "urls"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    original_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    short_code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationship to visits
    visits: Mapped[list["URLVisit"]] = relationship(
        "URLVisit",
        back_populates="url",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    # Add index for better query performance
    __table_args__ = (
        Index('ix_urls_short_code', 'short_code'),
    )


class URLVisit(Base):
    """URL visit tracking model"""

    __tablename__ = "url_visits"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    url_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("urls.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    visitor_ip: Mapped[str] = mapped_column(String(45), nullable=False)  # IPv6 max length
    visited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationship to URL
    url: Mapped["URL"] = relationship("URL", back_populates="visits")

    # Composite index for efficient stats queries
    __table_args__ = (
        Index('ix_url_visits_url_id_visited_at', 'url_id', 'visited_at'),
    )