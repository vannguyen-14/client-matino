from sqlalchemy import (
    Column, BigInteger, String, Enum, DateTime, ForeignKey,
    Integer, UniqueConstraint, Date, Computed, Float
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import LONGTEXT, SMALLINT
from database import Base
from datetime import datetime
import enum

# --- Enums giữ lại nếu dùng cho log hoặc API ---
class ChannelEnum(str, enum.Enum):
    SMS = "SMS"
    USSD = "USSD"
    WAP = "WAP"
    WEB = "WEB"
    APP = "APP"

class ActionEnum(str, enum.Enum):
    SUBSCRIBE = "SUBSCRIBE"
    UNSUBSCRIBE = "UNSUBSCRIBE"
    ON_DEMAND = "ON_DEMAND"
    IAP = "IAP"

class StatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

class GameModeEnum(str, enum.Enum):
    NORMAL = "normal"
    EVENT = "event"

# --- Core models ---

class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, index=True)
    msisdn = Column(String(20), unique=True, nullable=True)
    email = Column(String(191), unique=True, nullable=True)
    display_name = Column(String(100), nullable=False)
    country = Column(String(2), nullable=True)
    api_token = Column(String(64), unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    gameplays = relationship("GameplayHistory", back_populates="user", lazy="select")


class GameStatement(Base):
    __tablename__ = "game_statements"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(String(100), nullable=True)
    file_name = Column(String(255), nullable=True)
    payload_version = Column(Integer, nullable=True, default=1)
    statement_json = Column(LONGTEXT, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class GameStatementSummary(Base):
    __tablename__ = "game_statement_summary"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    statement_id = Column(Integer, ForeignKey("game_statements.id", ondelete="CASCADE"), nullable=False)
    coins = Column(Integer, default=0)
    scores = Column(Integer, default=0)
    level_played = Column(Integer, default=0)
    language_id = Column(String(10))
    last_login_time = Column(DateTime)
    daily_day = Column(Integer, default=0)
    skin_equipped = Column(String(50))
    achie_count = Column(Integer, default=0)
    server_last_login = Column(DateTime, nullable=True)
    spin_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SpinReward(Base):
    __tablename__ = "spin_rewards"
    __table_args__ = (UniqueConstraint('position', name='unique_position'),)

    id = Column(SMALLINT(unsigned=True), primary_key=True, autoincrement=True)
    codename = Column(String(50), nullable=False)
    amount = Column(Integer, nullable=False, default=1)
    weight = Column(Integer, nullable=False, default=1)
    position = Column(SMALLINT(unsigned=True), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LeaderboardHistory(Base):
    """
    Enhanced LeaderboardHistory model theo planBXH.txt
    Bổ sung 6 cột mới để hỗ trợ xếp hạng đa tiêu chí
    """
    __tablename__ = "leaderboard_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    period = Column(String(20), nullable=False)

    # Tiêu chí xếp hạng chính
    scores = Column(Integer, default=0, comment="Tổng điểm")

    # Các tiêu chí phụ (theo thứ tự ưu tiên)
    play_count = Column(Integer, default=0, comment="Số lượt chơi")
    max_level = Column(Integer, default=0, comment="Level cao nhất đạt được")
    avg_stars = Column(Float, default=0.0, comment="Trung bình số sao")
    total_duration = Column(BigInteger, default=0, comment="Tổng thời gian chơi (giây)")
    first_played_at = Column(DateTime, nullable=True, comment="Thời gian chơi đầu tiên")

    # Thứ hạng
    rank = Column(Integer, default=0, comment="Thứ hạng đã tính")

    # Legacy columns (giữ lại để tương thích)
    coins = Column(Integer, default=0)
    level_played = Column(Integer, default=0)


class GameplayHistory(Base):
    """
    Simplified GameplayHistory model theo plan mới
    Loại bỏ các trường không cần thiết, tập trung vào dữ liệu core
    """
    __tablename__ = "gameplay_history"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    msisdn = Column(String(20), nullable=False, comment="Số điện thoại")

    # Thông tin màn chơi
    level_code = Column(String(50), nullable=True, comment="Mã màn chơi (level_001...)")
    play_attempt = Column(Integer, nullable=False, default=1, comment="Số lần người chơi chơi màn này")

    # Kết quả
    score = Column(Integer, nullable=False, default=0, comment="Điểm đạt được")
    coins_earned = Column(Integer, nullable=False, default=0, comment="Coins kiếm được")
    stars = Column(SMALLINT, nullable=True, comment="Số sao đạt được (1-3)")

    # Thời gian
    started_at = Column(DateTime, nullable=False, comment="Thời gian bắt đầu chơi")
    duration_seconds = Column(Integer, nullable=True, comment="Thời gian chơi (giây)")

    # Items (JSON as TEXT for compatibility)
    items_start = Column(LONGTEXT, nullable=True, comment="JSON: Vật phẩm có lúc bắt đầu")
    items_used = Column(LONGTEXT, nullable=True, comment="JSON: Vật phẩm tiêu hao")
    items_earned = Column(LONGTEXT, nullable=True, comment="JSON: Vật phẩm nhặt được")

    # Metadata
    game_mode = Column(String(50), default='normal', comment="Chế độ chơi: normal, event")

    # Timestamp
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="Thời gian ghi log")

    # Computed column
    started_date = Column(
        Date,
        Computed("DATE(started_at)"),
        nullable=False,
        comment="Ngày chơi (tự động sinh từ started_at)"
    )

    # Relationship
    user = relationship("User", back_populates="gameplays", lazy="joined")

    def __repr__(self):
        return (
            f"<GameplayHistory(user_id={self.user_id}, level={self.level_code}, "
            f"attempt={self.play_attempt}, score={self.score})>"
        )
