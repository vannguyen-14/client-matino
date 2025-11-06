# schemas/gameplay_schemas.py - Updated with result field
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime

class GameplayLogRequest(BaseModel):
    """
    Request schema cho /log-gameplay
    Bổ sung field result để track win/lose
    """
    # Auth
    auth: str = Field(..., description="Authentication token (base64 or JWT)")
    
    # Core gameplay data
    level_code: str = Field(..., min_length=1, max_length=50, description="Mã màn chơi (vd: level_001)")
    score: int = Field(0, ge=0, description="Điểm đạt được")
    coins_earned: int = Field(0, ge=0, description="Coins kiếm được")
    duration_seconds: int = Field(0, ge=0, description="Thời gian chơi (giây)")
    
    # Optional fields
    stars: Optional[int] = Field(None, ge=0, le=3, description="Số sao (0-3)")
    result: int = Field(0, ge=0, le=1, description="Kết quả: 0=Win (vượt qua màn), 1=Lose (thua)")
    
    # Items tracking
    items_start: Optional[Dict[str, int]] = Field(None, description="Vật phẩm lúc bắt đầu")
    items_used: Optional[Dict[str, int]] = Field(None, description="Vật phẩm đã dùng")
    items_earned: Optional[Dict[str, int]] = Field(None, description="Vật phẩm nhặt được")
    
    # Game mode
    game_mode: str = Field("normal", pattern="^(normal|event)$", description="Chế độ chơi")

    @validator('level_code')
    def validate_level_code(cls, v):
        """Validate level_code format"""
        if not v:
            raise ValueError("level_code cannot be empty")
        
        # Accept both "level_XXX" and "event_XXX" formats
        if not (v.startswith('level_') or v.startswith('event_')):
            raise ValueError("level_code must start with 'level_' or 'event_'")
        
        return v.lower()

    @validator('stars')
    def validate_stars_with_result(cls, v, values):
        """
        Logic validation: Nếu thua (result=1) thì không nên có stars
        Nếu thắng (result=0) thì nên có stars
        """
        result = values.get('result', 0)
        
        if result == 1 and v and v > 0:
            # Thua nhưng có stars -> warning (không raise error, chỉ normalize)
            return 0
        
        if result == 0 and v is None:
            # Thắng nhưng không có stars -> mặc định 1 sao
            return 1
            
        return v

    class Config:
        schema_extra = {
            "example": {
                "auth": {
                    "msisdn": "959123456789",
                    "api_token": "abc123xyz"
                },
                "level_code": "level_038",
                "score": 9400,
                "coins_earned": 150,
                "stars": 3,
                "result": 0,
                "duration_seconds": 285,
                "items_start": {"itemAmmo": 10, "itemShield": 2},
                "items_used": {"itemAmmo": 3, "itemShield": 1},
                "items_earned": {"itemAmmo": 1, "itemClock": 2},
                "game_mode": "normal"
            }
        }


class GameplayLogSuccessResponse(BaseModel):
    status: str = "success"
    message: str
    gameplay_id: int


class GameplayHistoryItem(BaseModel):
    """Single gameplay history record"""
    id: int
    user_id: int
    msisdn: str
    level_code: str
    play_attempt: int
    score: int
    coins_earned: int
    stars: Optional[int]
    result: int = Field(0, description="0=Win, 1=Lose")
    duration_seconds: Optional[int]
    items_start: Optional[Dict[str, int]]
    items_used: Optional[Dict[str, int]]
    items_earned: Optional[Dict[str, int]]
    game_mode: str
    started_at: Optional[str]
    created_at: Optional[str]


class GameplayHistoryResponse(BaseModel):
    status: str = "success"
    total: int
    limit: int
    offset: int
    data: list[GameplayHistoryItem]


class GameplayStatsResponse(BaseModel):
    status: str = "success"
    period: str
    date: str
    stats: Dict[str, Any]


class LevelLeaderboardItem(BaseModel):
    rank: int
    user_id: int
    display_name: str
    msisdn: str
    best_score: int
    best_stars: Optional[int]
    fastest_time_seconds: Optional[int]
    win_rate: Optional[float] = Field(None, description="Tỷ lệ thắng (%)")


class LevelLeaderboardResponse(BaseModel):
    status: str = "success"
    level_code: str
    leaderboard: list[LevelLeaderboardItem]


class UserGameplayStatsDetailed(BaseModel):
    """Chi tiết stats của user"""
    total_games: int
    total_wins: int
    total_losses: int
    win_rate: float
    total_score: int
    total_coins: int
    unique_levels: int
    avg_duration_seconds: float
    best_score: int
    best_level: Optional[str]


class UserGameplayStatsResponse(BaseModel):
    status: str = "success"
    user_id: int
    period: str
    date: str
    stats: UserGameplayStatsDetailed