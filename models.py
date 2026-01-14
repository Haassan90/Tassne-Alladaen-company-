from sqlalchemy import Column, Integer, String, DateTime
from database import Base
from datetime import datetime, timezone


class Machine(Base):
    __tablename__ = "machines"

    # =====================================================
    # BASIC INFO
    # =====================================================
    id = Column(Integer, primary_key=True, index=True)
    location = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)

    # =====================================================
    # MACHINE STATUS
    # free | running | paused | stopped | completed
    # =====================================================
    status = Column(String, default="free", index=True)

    # =====================================================
    # PRODUCTION DATA
    # =====================================================
    target_qty = Column(Integer, default=0)
    produced_qty = Column(Integer, default=0)

    # =====================================================
    # STEP-12 : AUTOMATIC METER COUNTING
    # seconds_per_meter = kitne seconds me 1 meter banta
    # last_tick_time = last time meter add hua (UTC safe)
    # =====================================================
    seconds_per_meter = Column(Integer, nullable=True)
    last_tick_time = Column(
        DateTime(timezone=True),
        nullable=True,
        default=lambda: datetime.now(timezone.utc)
    )

    # =====================================================
    # ERP READY (FUTURE)
    # =====================================================
    work_order = Column(String, nullable=True)
    pipe_size = Column(String, nullable=True)

    # =====================================================
    # HELPERS (NON-BREAKING)
    # =====================================================
    def is_running(self) -> bool:
        return self.status == "running"

    def is_completed(self) -> bool:
        return self.produced_qty >= self.target_qty > 0
