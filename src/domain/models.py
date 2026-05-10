"""Domain models for the Football Scout Pro application."""
from pydantic import BaseModel, Field, model_validator
from typing import Optional, List, Dict, Any
from datetime import date, datetime
import math


class PlayerInfo(BaseModel):
    """Player biographical and market value information."""
    player_id: int
    name: str
    position: str
    sub_position: str
    foot: str
    height_in_cm: int
    date_of_birth: date
    club_name: str = Field(alias="current_club_name")
    market_value_in_eur: int
    highest_market_value_in_eur: int
    contract_expiration_date: date
    international_caps: int
    international_goals: int
    country_of_citizenship: str
    
    class Config:
        populate_by_name = True
    
    @property
    def age(self) -> int:
        """Calculate player age from date of birth."""
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
    
    @property
    def web_name(self) -> str:
        """Return web_name (same as name for this dataset)."""
        return self.name.split()[-1] if self.name else self.name


class PlayerStats(BaseModel):
    """Player match-by-match performance statistics."""
    player_id: int = Field(alias="id")
    gw: int
    minutes: int
    goals_scored: int
    assists: int
    clean_sheets: int
    goals_conceded: int
    own_goals: int
    penalties_saved: int
    penalties_missed: int
    yellow_cards: int
    red_cards: int
    saves: int
    starts: int
    expected_goals: float
    expected_assists: float
    expected_goal_involvements: float
    expected_goals_conceded: float
    influence: float
    creativity: float
    threat: float
    ict_index: float
    corners_and_indirect_freekicks_order: Optional[str] = None
    direct_freekicks_order: Optional[str] = None
    penalties_order: Optional[int] = None
    tackles: int
    clearances_blocks_interceptions: int
    recoveries: int
    defensive_contribution: int
    first_name: str
    second_name: str
    web_name: str
    
    class Config:
        populate_by_name = True
        
    @model_validator(mode='before')
    @classmethod
    def handle_nan_values(cls, values):
        """Handle NaN values and convert numeric values to string for optional fields."""
        for field in ['corners_and_indirect_freekicks_order', 'direct_freekicks_order']:
            if field in values:
                val = values[field]
                if val is None or (isinstance(val, float) and math.isnan(val)):
                    values[field] = None
                elif isinstance(val, (int, float)):
                    # Convert numeric values to string
                    values[field] = str(int(val))
        if 'penalties_order' in values:
            val = values['penalties_order']
            if val is None or (isinstance(val, float) and math.isnan(val)):
                values['penalties_order'] = None
        return values


class WatchlistEntry(BaseModel):
    """Watchlist entry model."""
    player_id: int
    notes: str = ""
    tags: List[str] = []
    date_added: datetime
    
    class Config:
        arbitrary_types_allowed = True


class PlayerComposite(BaseModel):
    """Combined player info and stats."""
    info: PlayerInfo
    stats: Optional[List[PlayerStats]] = []
    
    @property
    def player_id(self) -> int:
        return self.info.player_id
    
    @property
    def name(self) -> str:
        return self.info.name
    
    @property
    def web_name(self) -> str:
        return self.info.web_name
    
    @property
    def club_name(self) -> str:
        return self.info.club_name
    
    @property
    def position(self) -> str:
        return self.info.position
    
    @property
    def age(self) -> int:
        return self.info.age
    
    @property
    def market_value_in_eur(self) -> int:
        return self.info.market_value_in_eur
