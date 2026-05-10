"""Repository interfaces for data access."""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from ..domain.models import PlayerInfo, PlayerStats, WatchlistEntry


class IPlayerInfoRepository(ABC):
    """Interface for player information data access."""
    
    @abstractmethod
    def get_all_players(self) -> List[PlayerInfo]:
        """Get all players."""
        pass
    
    @abstractmethod
    def get_player_by_id(self, player_id: int) -> Optional[PlayerInfo]:
        """Get a player by ID."""
        pass
    
    @abstractmethod
    def get_players_by_club(self, club_name: str) -> List[PlayerInfo]:
        """Get players by club name."""
        pass
    
    @abstractmethod
    def get_players_by_position(self, position: str) -> List[PlayerInfo]:
        """Get players by position."""
        pass
    
    @abstractmethod
    def get_unique_clubs(self) -> List[str]:
        """Get list of unique clubs."""
        pass
    
    @abstractmethod
    def get_unique_positions(self) -> List[str]:
        """Get list of unique positions."""
        pass


class IPlayerStatsRepository(ABC):
    """Interface for player statistics data access."""
    
    @abstractmethod
    def get_all_stats(self) -> List[PlayerStats]:
        """Get all player statistics."""
        pass
    
    @abstractmethod
    def get_stats_by_player_id(self, player_id: int) -> List[PlayerStats]:
        """Get statistics for a specific player."""
        pass
    
    @abstractmethod
    def get_stats_by_gameweek(self, gw: int) -> List[PlayerStats]:
        """Get statistics for a specific gameweek."""
        pass
    
    @abstractmethod
    def get_aggregated_stats(self, player_id: int) -> Dict[str, Any]:
        """Get aggregated statistics for a player."""
        pass


class IWatchlistRepository(ABC):
    """Interface for watchlist data access."""
    
    @abstractmethod
    def get_all_entries(self) -> List[WatchlistEntry]:
        """Get all watchlist entries."""
        pass
    
    @abstractmethod
    def add_entry(self, entry: WatchlistEntry) -> bool:
        """Add a new watchlist entry."""
        pass
    
    @abstractmethod
    def update_entry(self, player_id: int, notes: str, tags: List[str]) -> bool:
        """Update an existing watchlist entry."""
        pass
    
    @abstractmethod
    def remove_entry(self, player_id: int) -> bool:
        """Remove a watchlist entry."""
        pass
    
    @abstractmethod
    def get_entry_by_player_id(self, player_id: int) -> Optional[WatchlistEntry]:
        """Get a watchlist entry by player ID."""
        pass
    
    @abstractmethod
    def clear_all(self) -> bool:
        """Clear all watchlist entries."""
        pass
