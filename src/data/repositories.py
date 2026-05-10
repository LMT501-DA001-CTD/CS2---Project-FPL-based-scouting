"""Data access layer implementations."""
import pandas as pd
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..domain.models import PlayerInfo, PlayerStats, WatchlistEntry
from ..domain.repositories import (
    IPlayerInfoRepository,
    IPlayerStatsRepository,
    IWatchlistRepository,
)
from ..core.exceptions import DataAccessException, PlayerNotFoundException
from ..core.logging_config import get_logger


logger = get_logger(__name__)


class CSVPlayerInfoRepository(IPlayerInfoRepository):
    """CSV implementation of player info repository."""
    
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self._df: Optional[pd.DataFrame] = None
    
    @property
    def df(self) -> pd.DataFrame:
        """Lazy load the DataFrame."""
        if self._df is None:
            try:
                self._df = pd.read_csv(self.file_path)
                # Rename current_club_name to club_name for consistency
                if 'current_club_name' in self._df.columns:
                    self._df = self._df.rename(columns={'current_club_name': 'club_name'})
            except Exception as e:
                logger.error(f"Error loading player info: {e}")
                raise DataAccessException(f"Failed to load player info from {self.file_path}", e)
        return self._df
    
    def get_all_players(self) -> List[PlayerInfo]:
        """Get all players."""
        try:
            records = self.df.to_dict(orient='records')
            return [PlayerInfo(**r) for r in records]
        except Exception as e:
            logger.error(f"Error getting all players: {e}")
            raise DataAccessException("Failed to get all players", e)
    
    def get_player_by_id(self, player_id: int) -> Optional[PlayerInfo]:
        """Get a player by ID."""
        try:
            row = self.df[self.df['player_id'] == player_id]
            if row.empty:
                return None
            return PlayerInfo(**row.iloc[0].to_dict())
        except Exception as e:
            logger.error(f"Error getting player by ID {player_id}: {e}")
            raise DataAccessException(f"Failed to get player {player_id}", e)
    
    def get_players_by_club(self, club_name: str) -> List[PlayerInfo]:
        """Get players by club name."""
        try:
            filtered = self.df[self.df['club_name'] == club_name]
            return [PlayerInfo(**r) for r in filtered.to_dict(orient='records')]
        except Exception as e:
            logger.error(f"Error getting players by club {club_name}: {e}")
            raise DataAccessException(f"Failed to get players for club {club_name}", e)
    
    def get_players_by_position(self, position: str) -> List[PlayerInfo]:
        """Get players by position."""
        try:
            filtered = self.df[self.df['position'] == position]
            return [PlayerInfo(**r) for r in filtered.to_dict(orient='records')]
        except Exception as e:
            logger.error(f"Error getting players by position {position}: {e}")
            raise DataAccessException(f"Failed to get players for position {position}", e)
    
    def get_unique_clubs(self) -> List[str]:
        """Get list of unique clubs."""
        try:
            return sorted(self.df['club_name'].dropna().unique().tolist())
        except Exception as e:
            logger.error(f"Error getting unique clubs: {e}")
            raise DataAccessException("Failed to get unique clubs", e)
    
    def get_unique_positions(self) -> List[str]:
        """Get list of unique positions."""
        try:
            return sorted(self.df['position'].dropna().unique().tolist())
        except Exception as e:
            logger.error(f"Error getting unique positions: {e}")
            raise DataAccessException("Failed to get unique positions", e)


class CSVPlayerStatsRepository(IPlayerStatsRepository):
    """CSV implementation of player stats repository."""
    
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self._df: Optional[pd.DataFrame] = None
    
    @property
    def df(self) -> pd.DataFrame:
        """Lazy load the DataFrame."""
        if self._df is None:
            try:
                self._df = pd.read_csv(self.file_path)
                # Rename id to player_id for consistency
                if 'id' in self._df.columns:
                    self._df = self._df.rename(columns={'id': 'player_id'})
            except Exception as e:
                logger.error(f"Error loading player stats: {e}")
                raise DataAccessException(f"Failed to load player stats from {self.file_path}", e)
        return self._df
    
    def get_all_stats(self) -> List[PlayerStats]:
        """Get all player statistics."""
        try:
            records = self.df.to_dict(orient='records')
            return [PlayerStats(**r) for r in records]
        except Exception as e:
            logger.error(f"Error getting all stats: {e}")
            raise DataAccessException("Failed to get all stats", e)
    
    def get_stats_by_player_id(self, player_id: int) -> List[PlayerStats]:
        """Get statistics for a specific player."""
        try:
            filtered = self.df[self.df['player_id'] == player_id]
            return [PlayerStats(**r) for r in filtered.to_dict(orient='records')]
        except Exception as e:
            logger.error(f"Error getting stats for player {player_id}: {e}")
            raise DataAccessException(f"Failed to get stats for player {player_id}", e)
    
    def get_stats_by_gameweek(self, gw: int) -> List[PlayerStats]:
        """Get statistics for a specific gameweek."""
        try:
            filtered = self.df[self.df['gw'] == gw]
            return [PlayerStats(**r) for r in filtered.to_dict(orient='records')]
        except Exception as e:
            logger.error(f"Error getting stats for gameweek {gw}: {e}")
            raise DataAccessException(f"Failed to get stats for gameweek {gw}", e)
    
    def get_aggregated_stats(self, player_id: int) -> Dict[str, Any]:
        """Get aggregated statistics for a player."""
        try:
            player_stats = self.df[self.df['player_id'] == player_id]
            if player_stats.empty:
                return {}
            
            agg = {
                'total_matches': len(player_stats),
                'total_minutes': int(player_stats['minutes'].sum()),
                'total_goals': int(player_stats['goals_scored'].sum()),
                'total_assists': int(player_stats['assists'].sum()),
                'total_clean_sheets': int(player_stats['clean_sheets'].sum()),
                'total_yellow_cards': int(player_stats['yellow_cards'].sum()),
                'total_red_cards': int(player_stats['red_cards'].sum()),
                'avg_expected_goals': float(player_stats['expected_goals'].mean()),
                'avg_expected_assists': float(player_stats['expected_assists'].mean()),
                'avg_influence': float(player_stats['influence'].mean()),
                'avg_creativity': float(player_stats['creativity'].mean()),
                'avg_threat': float(player_stats['threat'].mean()),
                'avg_ict_index': float(player_stats['ict_index'].mean()),
                'total_tackles': int(player_stats['tackles'].sum()),
                'total_clearances_blocks_interceptions': int(player_stats['clearances_blocks_interceptions'].sum()),
                'total_recoveries': int(player_stats['recoveries'].sum()),
            }
            
            # Calculate per 90 metrics
            total_mins = agg['total_minutes']
            if total_mins > 0:
                factor = 90 / total_mins
                agg['goals_per_90'] = round(agg['total_goals'] * factor, 2)
                agg['assists_per_90'] = round(agg['total_assists'] * factor, 2)
                agg['tackles_per_90'] = round(agg['total_tackles'] * factor, 2)
                agg['interceptions_per_90'] = round(agg['total_clearances_blocks_interceptions'] * factor, 2)
            
            return agg
        except Exception as e:
            logger.error(f"Error getting aggregated stats for player {player_id}: {e}")
            raise DataAccessException(f"Failed to get aggregated stats for player {player_id}", e)
    
    def get_stats_dataframe(self) -> pd.DataFrame:
        """Get raw stats DataFrame for advanced queries."""
        return self.df


class JSONWatchlistRepository(IWatchlistRepository):
    """JSON file implementation of watchlist repository."""
    
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Ensure the watchlist file exists."""
        if not self.file_path.exists():
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, 'w') as f:
                json.dump([], f)
    
    def _load_data(self) -> List[Dict]:
        """Load data from JSON file."""
        try:
            with open(self.file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading watchlist: {e}")
            raise DataAccessException("Failed to load watchlist", e)
    
    def _save_data(self, data: List[Dict]):
        """Save data to JSON file."""
        try:
            with open(self.file_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving watchlist: {e}")
            raise DataAccessException("Failed to save watchlist", e)
    
    def get_all_entries(self) -> List[WatchlistEntry]:
        """Get all watchlist entries."""
        data = self._load_data()
        return [WatchlistEntry(**entry) for entry in data]
    
    def add_entry(self, entry: WatchlistEntry) -> bool:
        """Add a new watchlist entry."""
        data = self._load_data()
        
        # Check if already exists
        if any(e['player_id'] == entry.player_id for e in data):
            return False
        
        data.append(entry.model_dump())
        self._save_data(data)
        return True
    
    def update_entry(self, player_id: int, notes: str, tags: List[str]) -> bool:
        """Update an existing watchlist entry."""
        data = self._load_data()
        
        for entry in data:
            if entry['player_id'] == player_id:
                entry['notes'] = notes
                entry['tags'] = tags
                self._save_data(data)
                return True
        
        return False
    
    def remove_entry(self, player_id: int) -> bool:
        """Remove a watchlist entry."""
        data = self._load_data()
        
        original_len = len(data)
        data = [e for e in data if e['player_id'] != player_id]
        
        if len(data) < original_len:
            self._save_data(data)
            return True
        return False
    
    def get_entry_by_player_id(self, player_id: int) -> Optional[WatchlistEntry]:
        """Get a watchlist entry by player ID."""
        data = self._load_data()
        
        for entry in data:
            if entry['player_id'] == player_id:
                return WatchlistEntry(**entry)
        
        return None
    
    def clear_all(self) -> bool:
        """Clear all watchlist entries."""
        self._save_data([])
        return True
