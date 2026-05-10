"""Domain services for business logic."""
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

from ..domain.models import PlayerInfo, PlayerStats, PlayerComposite, WatchlistEntry
from ..domain.repositories import (
    IPlayerInfoRepository,
    IPlayerStatsRepository,
    IWatchlistRepository,
)
from ..core.exceptions import PlayerNotFoundException, InvalidFilterException
from ..core.logging_config import get_logger


logger = get_logger(__name__)


class PlayerService:
    """Service for player-related business logic."""
    
    def __init__(
        self,
        player_info_repo: IPlayerInfoRepository,
        player_stats_repo: IPlayerStatsRepository,
    ):
        self.player_info_repo = player_info_repo
        self.player_stats_repo = player_stats_repo
    
    def get_all_players(self) -> List[PlayerComposite]:
        """Get all players with their stats."""
        players = self.player_info_repo.get_all_players()
        return [
            PlayerComposite(info=p, stats=self.player_stats_repo.get_stats_by_player_id(p.player_id))
            for p in players
        ]
    
    def get_player_by_id(self, player_id: int) -> Optional[PlayerComposite]:
        """Get a player by ID with stats."""
        player_info = self.player_info_repo.get_player_by_id(player_id)
        if not player_info:
            return None
        
        stats = self.player_stats_repo.get_stats_by_player_id(player_id)
        return PlayerComposite(info=player_info, stats=stats)
    
    def filter_players(
        self,
        clubs: Optional[List[str]] = None,
        positions: Optional[List[str]] = None,
        min_age: Optional[int] = None,
        max_age: Optional[int] = None,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
    ) -> List[PlayerComposite]:
        """Filter players based on criteria."""
        players = self.player_info_repo.get_all_players()
        
        filtered = []
        for player in players:
            # Club filter
            if clubs and player.club_name not in clubs:
                continue
            
            # Position filter
            if positions and player.position not in positions:
                continue
            
            # Age filter
            if min_age is not None and player.age < min_age:
                continue
            if max_age is not None and player.age > max_age:
                continue
            
            # Market value filter
            if min_value is not None and player.market_value_in_eur < min_value:
                continue
            if max_value is not None and player.market_value_in_eur > max_value:
                continue
            
            stats = self.player_stats_repo.get_stats_by_player_id(player.player_id)
            filtered.append(PlayerComposite(info=player, stats=stats))
        
        return filtered
    
    def calculate_composite_rating(self, player_id: int) -> float:
        """Calculate composite rating for a player (0-100)."""
        stats = self.player_stats_repo.get_aggregated_stats(player_id)
        if not stats:
            return 0.0
        
        # Weighted scoring based on various metrics
        score = 0.0
        
        # Attacking metrics (40%)
        score += min(stats.get('total_goals', 0) * 5, 20)
        score += min(stats.get('total_assists', 0) * 4, 12)
        score += min(stats.get('avg_expected_goals', 0) * 20, 8)
        
        # Creative metrics (20%)
        score += min(stats.get('avg_creativity', 0) / 5, 10)
        score += min(stats.get('avg_expected_assists', 0) * 15, 10)
        
        # Defensive metrics (20%)
        score += min(stats.get('total_tackles', 0) * 2, 10)
        score += min(stats.get('total_recoveries', 0) * 0.5, 10)
        
        # Consistency metrics (20%)
        score += min(stats.get('avg_influence', 0) / 3, 10)
        score += min(stats.get('avg_ict_index', 0), 10)
        
        return min(round(score, 1), 100.0)
    
    def get_top_scorers(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top scorers."""
        players = self.get_all_players()
        results = []
        
        for p in players:
            stats = self.player_stats_repo.get_aggregated_stats(p.player_id)
            results.append({
                'player': p,
                'goals': stats.get('total_goals', 0),
                'minutes': stats.get('total_minutes', 0),
            })
        
        results.sort(key=lambda x: x['goals'], reverse=True)
        return results[:limit]
    
    def get_top_assisters(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top assist providers."""
        players = self.get_all_players()
        results = []
        
        for p in players:
            stats = self.player_stats_repo.get_aggregated_stats(p.player_id)
            results.append({
                'player': p,
                'assists': stats.get('total_assists', 0),
                'minutes': stats.get('total_minutes', 0),
            })
        
        results.sort(key=lambda x: x['assists'], reverse=True)
        return results[:limit]
    
    def get_positional_averages(self, position: str) -> Dict[str, float]:
        """Get average stats for a specific position."""
        players = self.player_info_repo.get_players_by_position(position)
        
        if not players:
            return {}
        
        total_stats = {
            'goals': 0, 'assists': 0, 'xG': 0, 'xA': 0,
            'tackles': 0, 'interceptions': 0, 'threat': 0, 'creativity': 0
        }
        count = 0
        
        for player in players:
            stats = self.player_stats_repo.get_aggregated_stats(player.player_id)
            if stats:
                total_stats['goals'] += stats.get('total_goals', 0)
                total_stats['assists'] += stats.get('total_assists', 0)
                total_stats['xG'] += stats.get('avg_expected_goals', 0) * stats.get('total_matches', 1)
                total_stats['xA'] += stats.get('avg_expected_assists', 0) * stats.get('total_matches', 1)
                total_stats['tackles'] += stats.get('total_tackles', 0)
                total_stats['interceptions'] += stats.get('total_clearances_blocks_interceptions', 0)
                total_stats['threat'] += stats.get('avg_threat', 0)
                total_stats['creativity'] += stats.get('avg_creativity', 0)
                count += 1
        
        if count == 0:
            return {}
        
        return {k: v / count for k, v in total_stats.items()}
    
    def find_similar_players(self, player_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Find players with similar statistical profiles."""
        target_stats = self.player_stats_repo.get_aggregated_stats(player_id)
        if not target_stats:
            return []
        
        target_player = self.player_info_repo.get_player_by_id(player_id)
        if not target_player:
            return []
        
        all_players = self.player_info_repo.get_all_players()
        similarities = []
        
        for player in all_players:
            if player.player_id == player_id:
                continue
            
            # Skip different positions for better similarity
            if player.position != target_player.position:
                continue
            
            other_stats = self.player_stats_repo.get_aggregated_stats(player.player_id)
            if not other_stats:
                continue
            
            # Calculate Euclidean distance in normalized stat space
            keys = ['total_goals', 'total_assists', 'avg_expected_goals', 
                    'avg_expected_assists', 'total_tackles', 'total_recoveries']
            
            diff_sum = 0
            for key in keys:
                t_val = target_stats.get(key, 0)
                o_val = other_stats.get(key, 0)
                max_val = max(t_val, o_val, 1)
                diff_sum += ((t_val - o_val) / max_val) ** 2
            
            similarity = 1 / (1 + np.sqrt(diff_sum))
            similarities.append((player, other_stats, similarity))
        
        similarities.sort(key=lambda x: x[2], reverse=True)
        return [
            {'player': p, 'stats': s, 'similarity': round(sim, 3)}
            for p, s, sim in similarities[:limit]
        ]


class WatchlistService:
    """Service for watchlist business logic."""
    
    def __init__(
        self,
        watchlist_repo: IWatchlistRepository,
        player_service: PlayerService,
    ):
        self.watchlist_repo = watchlist_repo
        self.player_service = player_service
    
    def get_all_entries(self) -> List[Dict[str, Any]]:
        """Get all watchlist entries with player info."""
        entries = self.watchlist_repo.get_all_entries()
        results = []
        
        for entry in entries:
            player = self.player_service.get_player_by_id(entry.player_id)
            if player:
                results.append({
                    'entry': entry,
                    'player': player,
                })
        
        return results
    
    def add_to_watchlist(
        self,
        player_id: int,
        notes: str = "",
        tags: Optional[List[str]] = None,
    ) -> bool:
        """Add a player to the watchlist."""
        from datetime import datetime
        
        # Check if player exists
        player = self.player_service.get_player_by_id(player_id)
        if not player:
            raise PlayerNotFoundException(player_id)
        
        entry = WatchlistEntry(
            player_id=player_id,
            notes=notes,
            tags=tags or [],
            date_added=datetime.now(),
        )
        
        return self.watchlist_repo.add_entry(entry)
    
    def update_watchlist_entry(
        self,
        player_id: int,
        notes: str,
        tags: List[str],
    ) -> bool:
        """Update a watchlist entry."""
        return self.watchlist_repo.update_entry(player_id, notes, tags)
    
    def remove_from_watchlist(self, player_id: int) -> bool:
        """Remove a player from the watchlist."""
        return self.watchlist_repo.remove_entry(player_id)
    
    def is_in_watchlist(self, player_id: int) -> bool:
        """Check if a player is in the watchlist."""
        entry = self.watchlist_repo.get_entry_by_player_id(player_id)
        return entry is not None
    
    def clear_watchlist(self) -> bool:
        """Clear all watchlist entries."""
        return self.watchlist_repo.clear_all()
    
    def filter_by_tags(self, tags: List[str]) -> List[Dict[str, Any]]:
        """Filter watchlist entries by tags."""
        all_entries = self.get_all_entries()
        
        if not tags:
            return all_entries
        
        filtered = []
        for item in all_entries:
            entry_tags = item['entry'].tags
            if any(tag in entry_tags for tag in tags):
                filtered.append(item)
        
        return filtered


class ScoutingService:
    """Service for advanced scouting business logic."""
    
    def __init__(self, player_service: PlayerService):
        self.player_service = player_service
    
    SKILL_WEIGHTS = {
        'goal_scoring': ['total_goals', 'avg_expected_goals'],
        'goal_efficiency': ['goals_per_90'],
        'shooting': ['avg_threat'],
        'passing_influence': ['avg_creativity', 'avg_expected_assists'],
        'goal_creation': ['total_assists', 'avg_expected_assists'],
        'possession_influence': ['avg_influence'],
        'progression': ['avg_ict_index'],
        'dribbling': ['avg_creativity', 'avg_threat'],
        'aerial_influence': ['avg_influence'],
        'defensive_influence': ['total_tackles', 'total_recoveries'],
        'discipline_consistency': ['total_yellow_cards', 'total_red_cards'],
    }
    
    def search_players(
        self,
        skills: Dict[str, int],
        max_results: int = 10,
        position: Optional[str] = None,
        max_value: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Search players based on skill weights."""
        players = self.player_service.get_all_players()
        
        # Filter by position and value
        filtered = []
        for p in players:
            if position and p.position != position:
                continue
            if max_value and p.info.market_value_in_eur > max_value:
                continue
            filtered.append(p)
        
        # Calculate compatibility scores
        scored = []
        for player in filtered:
            stats = self.player_service.player_stats_repo.get_aggregated_stats(player.player_id)
            if not stats:
                continue
            
            score = 0
            total_weight = sum(skills.values())
            
            if total_weight == 0:
                continue
            
            for skill_name, weight in skills.items():
                if skill_name not in self.SKILL_WEIGHTS:
                    continue
                
                stat_keys = self.SKILL_WEIGHTS[skill_name]
                skill_score = 0
                
                for key in stat_keys:
                    val = stats.get(key, 0)
                    # Normalize score (simple normalization)
                    if key.startswith('total_'):
                        skill_score += min(val / 5, 100)
                    elif key.endswith('_per_90'):
                        skill_score += min(val * 10, 100)
                    else:
                        skill_score += min(val, 100)
                
                skill_score /= len(stat_keys)
                score += skill_score * (weight / 100)
            
            compatibility = min(round(score / len(skills) if skills else 0, 1), 100)
            scored.append((player, compatibility))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return [
            {'player': p, 'compatibility': c}
            for p, c in scored[:max_results]
        ]


class ValuationService:
    """Service for player valuation business logic."""
    
    def __init__(self, player_service: PlayerService):
        self.player_service = player_service
    
    def predict_market_value(self, player_id: int) -> Optional[Dict[str, Any]]:
        """Predict theoretical market value for a player."""
        player = self.player_service.get_player_by_id(player_id)
        if not player:
            return None
        
        stats = self.player_service.player_stats_repo.get_aggregated_stats(player_id)
        if not stats:
            return None
        
        # Simple valuation model based on performance and age
        base_value = player.info.market_value_in_eur
        
        # Performance adjustment
        performance_factor = 1.0
        performance_factor += (stats.get('total_goals', 0) * 0.02)
        performance_factor += (stats.get('total_assists', 0) * 0.015)
        performance_factor += (player.info.age < 25) * 0.1  # Young player bonus
        
        # Contract length adjustment
        from datetime import date
        contract_years = (player.info.contract_expiration_date - date.today()).days / 365
        contract_factor = min(max(contract_years / 3, 0.8), 1.2)
        
        predicted_value = int(base_value * performance_factor * contract_factor)
        
        actual_value = player.info.market_value_in_eur
        diff_percent = ((predicted_value - actual_value) / actual_value) * 100 if actual_value > 0 else 0
        
        return {
            'actual_value': actual_value,
            'predicted_value': predicted_value,
            'diff_percent': round(diff_percent, 1),
            'is_overperform': predicted_value > actual_value,
            'potential_stars': self._calculate_potential_stars(player, stats),
        }
    
    def _calculate_potential_stars(self, player: PlayerComposite, stats: Dict[str, Any]) -> int:
        """Calculate potential rating (1-5 stars)."""
        stars = 3  # Base stars
        
        # Age factor
        if player.info.age < 23:
            stars += 1
        elif player.info.age < 26:
            stars += 0.5
        
        # Performance trend
        if stats.get('total_goals', 0) > 10 or stats.get('total_assists', 0) > 8:
            stars += 0.5
        
        # Contract length
        from datetime import date
        contract_years = (player.info.contract_expiration_date - date.today()).days / 365
        if contract_years > 3:
            stars += 0.5
        
        return min(int(stars), 5)
    
    def find_cheap_beasts(
        self,
        position: Optional[str] = None,
        max_value: int = 50000000,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Find players with high value-for-money ratio."""
        players = self.player_service.get_all_players()
        
        filtered = []
        for p in players:
            if position and p.position != position:
                continue
            if p.info.market_value_in_eur > max_value:
                continue
            
            stats = self.player_service.player_stats_repo.get_aggregated_stats(p.player_id)
            if not stats:
                continue
            
            rating = self.player_service.calculate_composite_rating(p.player_id)
            value_ratio = rating / (p.info.market_value_in_eur / 1000000) if p.info.market_value_in_eur > 0 else 0
            
            filtered.append({
                'player': p,
                'rating': rating,
                'value_ratio': round(value_ratio, 2),
                'stats': stats,
            })
        
        filtered.sort(key=lambda x: x['value_ratio'], reverse=True)
        return filtered[:limit]
    
    def find_cheaper_similar(
        self,
        reference_player_id: int,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Find players with similar stats but lower market value."""
        reference = self.player_service.get_player_by_id(reference_player_id)
        if not reference:
            return []
        
        ref_stats = self.player_service.player_stats_repo.get_aggregated_stats(reference_player_id)
        ref_value = reference.info.market_value_in_eur
        
        similar = self.player_service.find_similar_players(reference_player_id, limit=20)
        
        cheaper = []
        for item in similar:
            player = item['player']
            if player.info.market_value_in_eur >= ref_value:
                continue
            
            # Check if stats are within ±10%
            player_stats = self.player_service.player_stats_repo.get_aggregated_stats(player.player_id)
            is_similar = True
            
            for key in ['total_goals', 'total_assists', 'avg_expected_goals']:
                ref_val = ref_stats.get(key, 0)
                p_val = player_stats.get(key, 0)
                if ref_val > 0 and abs(ref_val - p_val) / ref_val > 0.15:
                    is_similar = False
                    break
            
            if is_similar:
                cheaper.append({
                    'player': player,
                    'stats': player_stats,
                    'savings': ref_value - player.info.market_value_in_eur,
                })
        
        return cheaper[:limit]
    
    def find_better_at_same_price(
        self,
        reference_player_id: int,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Find players with similar price but better performance."""
        reference = self.player_service.get_player_by_id(reference_player_id)
        if not reference:
            return []
        
        ref_value = reference.info.market_value_in_eur
        ref_rating = self.player_service.calculate_composite_rating(reference_player_id)
        
        all_players = self.player_service.get_all_players()
        better = []
        
        for p in all_players:
            if p.player_id == reference_player_id:
                continue
            
            # Similar price (±10%)
            if abs(p.info.market_value_in_eur - ref_value) / ref_value > 0.1:
                continue
            
            p_rating = self.player_service.calculate_composite_rating(p.player_id)
            if p_rating <= ref_rating:
                continue
            
            better.append({
                'player': p,
                'rating': p_rating,
                'improvement': p_rating - ref_rating,
            })
        
        better.sort(key=lambda x: x['improvement'], reverse=True)
        return better[:limit]
