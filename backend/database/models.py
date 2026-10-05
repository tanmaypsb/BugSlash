from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String, Text, Integer, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    scans: Mapped[list["Scan"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan"
    )


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id")
    )
    status: Mapped[str] = mapped_column(String(50))
    files_analyzed: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    project: Mapped["Project"] = relationship(
        back_populates="scans"
    )

    findings: Mapped[list["Finding"]] = relationship(
        back_populates="scan",
        cascade="all, delete-orphan"
    )


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    scan_id: Mapped[int] = mapped_column(
        ForeignKey("scans.id")
    )

    language: Mapped[str] = mapped_column(String(50))
    file: Mapped[str] = mapped_column(String(500))
    line: Mapped[int] = mapped_column(Integer)
    column: Mapped[int] = mapped_column(Integer)

    category: Mapped[str] = mapped_column(String(100))
    severity: Mapped[str] = mapped_column(String(50))
    message: Mapped[str] = mapped_column(Text)
    analyzer: Mapped[str] = mapped_column(String(100))
    confidence: Mapped[float] = mapped_column(Float)

    verification_status: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    scan: Mapped["Scan"] = relationship(
        back_populates="findings"
    )