"""
Football Scout Pro - Modular Architecture
Separation of Concerns: Presentation | Business Logic | Data Access
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
import json
import logging
from dataclasses import dataclass, field, asdict
import numpy as np

# ============================================================================
# CONFIGURATION & LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
WATCHLIST_FILE = Path(__file__).parent / "watchlist.json"

# ============================================================================
# DATA ACCESS LAYER (Repository Pattern without ABC)
# ============================================================================

class DataLoader:
    """Handles all data loading and persistence operations."""
    
    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = data_dir
        self._player_stats_cache: Optional[pd.DataFrame] = None
        self._player_info_cache: Optional[pd.DataFrame] = None
    
    def load_player_stats(self) -> pd.DataFrame:
        """Load player statistics from CSV."""
        if self._player_stats_cache is not None:
            return self._player_stats_cache.copy()
        
        file_path = self.data_dir / "playerstats.csv"
        if not file_path.exists():
            raise FileNotFoundError(f"Player stats file not found: {file_path}")
        
        df = pd.read_csv(file_path)
        
        # Normalize column names
        df.columns = df.columns.str.strip().str.lower()
        
        # Ensure player_id exists
        if 'id' in df.columns and 'player_id' not in df.columns:
            df['player_id'] = df['id']
        
        self._player_stats_cache = df
        return df.copy()
    
    def load_player_info(self) -> pd.DataFrame:
        """Load player information from CSV."""
        if self._player_info_cache is not None:
            return self._player_info_cache.copy()
        
        file_path = self.data_dir / "players_info.csv"
        if not file_path.exists():
            raise FileNotFoundError(f"Player info file not found: {file_path}")
        
        df = pd.read_csv(file_path)
        
        # Normalize column names
        df.columns = df.columns.str.strip().str.lower()
        
        # Rename current_club_name to club_name for consistency
        if 'current_club_name' in df.columns:
            df = df.rename(columns={'current_club_name': 'club_name'})
        
        # Create web_name from name if not present
        if 'web_name' not in df.columns:
            df['web_name'] = df['name']
        
        self._player_info_cache = df
        return df.copy()
    
    def get_merged_data(self) -> pd.DataFrame:
        """Merge player stats with player info."""
        stats = self.load_player_stats()
        info = self.load_player_info()
        
        # Ensure both have player_id
        if 'player_id' not in stats.columns:
            stats['player_id'] = stats['id']
        
        # Remove web_name from stats before merge to avoid duplication
        stats_to_merge = stats.copy()
        if 'web_name' in stats_to_merge.columns:
            stats_to_merge = stats_to_merge.drop(columns=['web_name'])
        
        merged = stats_to_merge.merge(info, on='player_id', how='left')
        
        # Fill missing web_name with name
        if 'web_name' not in merged.columns and 'name' in merged.columns:
            merged['web_name'] = merged['name']
        elif 'web_name' in merged.columns and 'name' in merged.columns:
            merged['web_name'] = merged['web_name'].fillna(merged['name'])
        
        return merged
    
    def save_watchlist(self, watchlist: List[Dict]) -> bool:
        """Save watchlist to JSON file."""
        try:
            with open(WATCHLIST_FILE, 'w') as f:
                json.dump(watchlist, f, indent=2, default=str)
            return True
        except Exception as e:
            logger.error(f"Failed to save watchlist: {e}")
            return False
    
    def load_watchlist(self) -> List[Dict]:
        """Load watchlist from JSON file."""
        if not WATCHLIST_FILE.exists():
            return []
        
        try:
            with open(WATCHLIST_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load watchlist: {e}")
            return []


# ============================================================================
# BUSINESS LOGIC LAYER (Domain Services)
# ============================================================================

@dataclass
class PlayerProfile:
    """Represents a complete player profile."""
    player_id: int
    name: str
    web_name: str
    club_name: str
    position: str
    sub_position: Optional[str]
    age: int
    height_cm: Optional[int]
    nationality: str
    foot: str
    market_value: float
    contract_expiry: Optional[str]
    
    # Stats
    total_matches: int = 0
    total_minutes: int = 0
    goals: int = 0
    assists: int = 0
    xg: float = 0.0
    xa: float = 0.0
    tackles: int = 0
    interceptions: int = 0
    composite_rating: float = 0.0
    
    @classmethod
    def from_dataframe(cls, df: pd.DataFrame, player_id: int) -> Optional['PlayerProfile']:
        """Create PlayerProfile from dataframe."""
        player_info = df[df['player_id'] == player_id].iloc[0] if len(df[df['player_id'] == player_id]) > 0 else None
        
        if player_info is None or pd.isna(player_info.get('name')):
            return None
        
        # Calculate age
        dob = player_info.get('date_of_birth')
        age = cls._calculate_age(dob) if pd.notna(dob) else 0
        
        return cls(
            player_id=int(player_id),
            name=str(player_info.get('name', '')),
            web_name=str(player_info.get('web_name', player_info.get('name', ''))),
            club_name=str(player_info.get('club_name', 'Unknown')),
            position=str(player_info.get('position', 'Unknown')),
            sub_position=player_info.get('sub_position'),
            age=age,
            height_cm=int(player_info['height_in_cm']) if pd.notna(player_info.get('height_in_cm')) else None,
            nationality=str(player_info.get('country_of_citizenship', 'Unknown')),
            foot=str(player_info.get('foot', 'Unknown')),
            market_value=float(player_info.get('market_value_in_eur', 0)),
            contract_expiry=str(player_info.get('contract_expiration_date')) if pd.notna(player_info.get('contract_expiration_date')) else None,
        )
    
    @staticmethod
    def _calculate_age(dob) -> int:
        """Calculate age from date of birth."""
        try:
            if isinstance(dob, (datetime, date)):
                birth_date = dob
            elif isinstance(dob, str):
                birth_date = datetime.strptime(dob, '%Y-%m-%d')
            else:
                return 0
            
            today = date.today()
            return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        except:
            return 0


class PlayerStatsService:
    """Business logic for player statistics."""
    
    def __init__(self, data_loader: DataLoader):
        self.data_loader = data_loader
    
    def get_all_players_summary(self) -> pd.DataFrame:
        """Get summary statistics for all players."""
        df = self.data_loader.get_merged_data()
        
        # Aggregate stats per player
        agg_cols = {
            'minutes': 'sum',
            'goals_scored': 'sum',
            'assists': 'sum',
            'expected_goals': 'sum',
            'expected_assists': 'sum',
            'tackles': 'sum',
            'clearances_blocks_interceptions': 'sum',
            'ict_index': 'mean',
            'gw': 'count'
        }
        
        available_cols = {k: v for k, v in agg_cols.items() if k in df.columns}
        
        summary = df.groupby(['player_id', 'web_name', 'name', 'club_name', 'position']).agg(available_cols).reset_index()
        
        # Rename columns
        summary = summary.rename(columns={
            'minutes': 'total_minutes',
            'goals_scored': 'total_goals',
            'assists': 'total_assists',
            'expected_goals': 'total_xg',
            'expected_assists': 'total_xa',
            'tackles': 'total_tackles',
            'clearances_blocks_interceptions': 'total_interceptions',
            'gw': 'total_matches'
        })
        
        # Calculate composite rating
        summary['composite_rating'] = self._calculate_composite_rating(summary)
        
        # Calculate age
        info_df = self.data_loader.load_player_info()
        summary = summary.merge(info_df[['player_id', 'date_of_birth']], on='player_id', how='left')
        summary['age'] = summary['date_of_birth'].apply(PlayerProfile._calculate_age)
        summary = summary.drop(columns=['date_of_birth'], errors='ignore')
        
        return summary
    
    def _calculate_composite_rating(self, df: pd.DataFrame) -> pd.Series:
        """Calculate composite rating based on multiple metrics."""
        rating = pd.Series(index=df.index, data=0.0)
        
        if 'total_goals' in df.columns:
            rating += df['total_goals'] * 5
        if 'total_assists' in df.columns:
            rating += df['total_assists'] * 4
        if 'total_xg' in df.columns:
            rating += df['total_xg'] * 3
        if 'total_xa' in df.columns:
            rating += df['total_xa'] * 3
        if 'total_tackles' in df.columns:
            rating += df['total_tackles'] * 2
        if 'total_interceptions' in df.columns:
            rating += df['total_interceptions'] * 2
        if 'ict_index' in df.columns:
            rating += df['ict_index'] * 0.5
        
        # Normalize to 0-100
        if rating.max() > 0:
            rating = (rating / rating.max()) * 100
        
        return rating.round(1)
    
    def get_player_detailed_stats(self, player_id: int) -> Tuple[Optional[PlayerProfile], Optional[pd.DataFrame]]:
        """Get detailed stats for a specific player."""
        try:
            df = self.data_loader.get_merged_data()
            player_stats = df[df['player_id'] == player_id].copy()
            
            if player_stats.empty:
                logger.warning(f"No stats found for player {player_id}")
                return None, None
            
            profile = PlayerProfile.from_dataframe(df, player_id)
            if profile:
                profile.total_matches = len(player_stats)
                profile.total_minutes = int(player_stats['minutes'].sum()) if 'minutes' in player_stats.columns else 0
                profile.goals = int(player_stats['goals_scored'].sum()) if 'goals_scored' in player_stats.columns else 0
                profile.assists = int(player_stats['assists'].sum()) if 'assists' in player_stats.columns else 0
                profile.xg = float(player_stats['expected_goals'].sum()) if 'expected_goals' in player_stats.columns else 0.0
                profile.xa = float(player_stats['expected_assists'].sum()) if 'expected_assists' in player_stats.columns else 0.0
                profile.tackles = int(player_stats['tackles'].sum()) if 'tackles' in player_stats.columns else 0
                profile.interceptions = int(player_stats['clearances_blocks_interceptions'].sum()) if 'clearances_blocks_interceptions' in player_stats.columns else 0
                profile.composite_rating = float(self._calculate_composite_rating(
                    pd.DataFrame([{
                        'total_goals': profile.goals,
                        'total_assists': profile.assists,
                        'total_xg': profile.xg,
                        'total_xa': profile.xa,
                        'total_tackles': profile.tackles,
                        'total_interceptions': profile.interceptions,
                        'ict_index': player_stats['ict_index'].mean() if 'ict_index' in player_stats.columns else 0
                    }])
                ).iloc[0])
            
            return profile, player_stats
            
        except Exception as e:
            logger.error(f"Failed to get stats for player {player_id}: {e}")
            return None, None
    
    def get_positional_averages(self, position: str) -> Dict[str, float]:
        """Get average stats for a specific position."""
        df = self.data_loader.get_merged_data()
        position_df = df[df['position'] == position]
        
        if position_df.empty:
            return {}
        
        averages = {}
        stat_cols = ['goals_scored', 'assists', 'expected_goals', 'expected_assists', 
                     'tackles', 'clearances_blocks_interceptions', 'ict_index', 'influence', 'creativity', 'threat']
        
        for col in stat_cols:
            if col in position_df.columns:
                averages[col] = float(position_df[col].mean())
        
        return averages
    
    def find_similar_players(self, player_id: int, limit: int = 10) -> List[Dict]:
        """Find players with similar statistical profiles."""
        summary = self.get_all_players_summary()
        
        if player_id not in summary['player_id'].values:
            return []
        
        target = summary[summary['player_id'] == player_id].iloc[0]
        
        # Calculate similarity score
        summary['similarity'] = 0.0
        
        stat_cols = ['total_goals', 'total_assists', 'total_xg', 'total_xa', 'total_tackles', 'total_interceptions']
        available_cols = [c for c in stat_cols if c in summary.columns]
        
        for col in available_cols:
            if col in summary.columns and col in target:
                max_val = summary[col].max()
                if max_val > 0:
                    diff = abs(summary[col] - target[col]) / max_val
                    summary['similarity'] += (1 - diff)
        
        similar = summary[summary['player_id'] != player_id].nlargest(limit, 'similarity')
        
        return similar.to_dict('records')


class WatchlistService:
    """Business logic for watchlist management."""
    
    def __init__(self, data_loader: DataLoader):
        self.data_loader = data_loader
    
    def get_watchlist(self) -> List[Dict]:
        """Get current watchlist with player details."""
        watchlist = self.data_loader.load_watchlist()
        
        # Enrich with player info
        info_df = self.data_loader.load_player_info()
        
        for item in watchlist:
            player_id = item.get('player_id')
            if player_id:
                player_info = info_df[info_df['player_id'] == player_id]
                if not player_info.empty:
                    p = player_info.iloc[0]
                    item['player_name'] = str(p.get('web_name', p.get('name', 'Unknown')))
                    item['club_name'] = str(p.get('club_name', 'Unknown'))
                    item['position'] = str(p.get('position', 'Unknown'))
        
        return watchlist
    
    def add_to_watchlist(self, player_id: int, notes: str = "", tags: List[str] = None) -> bool:
        """Add player to watchlist."""
        watchlist = self.data_loader.load_watchlist()
        
        # Check if already exists
        if any(item.get('player_id') == player_id for item in watchlist):
            return False
        
        entry = {
            'player_id': player_id,
            'notes': notes,
            'tags': tags or [],
            'date_added': datetime.now().isoformat()
        }
        
        watchlist.append(entry)
        return self.data_loader.save_watchlist(watchlist)
    
    def update_watchlist_entry(self, player_id: int, notes: str, tags: List[str]) -> bool:
        """Update watchlist entry."""
        watchlist = self.data_loader.load_watchlist()
        
        for item in watchlist:
            if item.get('player_id') == player_id:
                item['notes'] = notes
                item['tags'] = tags
                return self.data_loader.save_watchlist(watchlist)
        
        return False
    
    def remove_from_watchlist(self, player_id: int) -> bool:
        """Remove player from watchlist."""
        watchlist = self.data_loader.load_watchlist()
        watchlist = [item for item in watchlist if item.get('player_id') != player_id]
        return self.data_loader.save_watchlist(watchlist)
    
    def clear_watchlist(self) -> bool:
        """Clear entire watchlist."""
        return self.data_loader.save_watchlist([])


# ============================================================================
# PRESENTATION LAYER (Streamlit UI Components)
# ============================================================================

def init_session_state():
    """Initialize session state variables."""
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'Home'
    if 'selected_player_id' not in st.session_state:
        st.session_state.selected_player_id = None
    if 'filters' not in st.session_state:
        st.session_state.filters = {}


def navigate_to(page: str, player_id: Optional[int] = None):
    """Navigate to a specific page."""
    st.session_state.current_page = page
    if player_id is not None:
        st.session_state.selected_player_id = player_id
    st.rerun()


def render_sidebar():
    """Render sidebar navigation."""
    with st.sidebar:
        st.title("⚽ Football Scout Pro")
        st.markdown("---")
        
        pages = [
            ("🏠 Home", "Home"),
            ("🔍 Player Explorer", "Player Explorer"),
            ("⭐ My Watchlist", "My Watchlist"),
            ("🎯 Advanced Scouting", "Advanced Scouting"),
            ("💰 Player Valuation", "Player Valuation")
        ]
        
        for label, page in pages:
            if st.button(label, use_container_width=True, key=f"nav_{page}"):
                navigate_to(page)
        
        st.markdown("---")
        st.info("Professional football analytics tool")


def create_player_card(name: str, club: str, value: str, rating: float, player_id: int):
    """Create a clickable player card."""
    col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1])
    
    with col1:
        st.markdown(f"**{name}**")
    with col2:
        st.markdown(club)
    with col3:
        st.markdown(value)
    with col4:
        st.markdown(f"**{rating}**")
    with col5:
        if st.button("📊", key=f"view_{player_id}", help="View Dashboard"):
            navigate_to("Player Dashboard", player_id)
    
    st.divider()


def render_home():
    """Render home page."""
    st.title("⚽ Football Scout Pro")
    st.subheader("Professional Player Analytics & Scouting Platform")
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔍 Player Explorer\nExplore and filter players", use_container_width=True):
            navigate_to("Player Explorer")
    
    with col2:
        if st.button("🎯 Advanced Scouting\nFind players by skills", use_container_width=True):
            navigate_to("Advanced Scouting")
    
    with col3:
        if st.button("💰 Player Valuation\nAnalyze market values", use_container_width=True):
            navigate_to("Player Valuation")


def render_player_explorer():
    """Render player explorer page."""
    st.title("🔍 Player Explorer")
    
    data_loader = DataLoader()
    stats_service = PlayerStatsService(data_loader)
    
    # Get data
    try:
        summary = stats_service.get_all_players_summary()
        info_df = data_loader.load_player_info()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        clubs = sorted(summary['club_name'].dropna().unique())
        selected_clubs = st.multiselect("Club", clubs, key="filter_clubs")
    
    with col2:
        positions = sorted(summary['position'].dropna().unique())
        selected_positions = st.multiselect("Position", positions, key="filter_positions")
    
    with col3:
        min_age, max_age = int(summary['age'].min()), int(summary['age'].max())
        age_range = st.slider("Age Range", min_age, max_age, (min_age, max_age), key="filter_age")
    
    with col4:
        min_val, max_val = summary['market_value_in_eur'].min() if 'market_value_in_eur' in summary.columns else 0, \
                          summary['market_value_in_eur'].max() if 'market_value_in_eur' in summary.columns else 100000000
        value_range = st.slider("Market Value (€)", int(min_val), int(max_val), (int(min_val), int(max_val)), key="filter_value")
    
    # Apply filters
    filtered = summary.copy()
    
    if selected_clubs:
        filtered = filtered[filtered['club_name'].isin(selected_clubs)]
    if selected_positions:
        filtered = filtered[filtered['position'].isin(selected_positions)]
    if age_range:
        filtered = filtered[(filtered['age'] >= age_range[0]) & (filtered['age'] <= age_range[1])]
    if 'market_value_in_eur' in filtered.columns:
        filtered = filtered[(filtered['market_value_in_eur'] >= value_range[0]) & (filtered['market_value_in_eur'] <= value_range[1])]
    
    # Display table with sticky header using container
    st.markdown("### Players")
    
    # Create display dataframe
    display_df = filtered[['player_id', 'web_name', 'club_name', 'age', 'market_value_in_eur', 'composite_rating', 'position']].copy()
    display_df = display_df.rename(columns={
        'web_name': 'Player',
        'club_name': 'Club',
        'age': 'Age',
        'market_value_in_eur': 'Market Value (€)',
        'composite_rating': 'Rating',
        'position': 'Position'
    })
    
    # Format market value
    display_df['Market Value (€)'] = display_df['Market Value (€)'].apply(
        lambda x: f"€{x/1e6:.1f}M" if x >= 1e6 else f"€{x/1e3:.0f}K" if x >= 1e3 else f"€{x:.0f}"
    )
    
    # Use a scrollable container with fixed height to keep headers visible
    with st.container():
        # Custom CSS for sticky header
        st.markdown("""
        <style>
        .dataframe-container {
            max-height: 400px;
            overflow-y: auto;
        }
        .dataframe thead th {
            position: sticky;
            top: 0;
            background-color: #0e1117;
            z-index: 10;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Display as table with selection
        for idx, row in display_df.iterrows():
            cols = st.columns([3, 2, 1, 2, 2, 1])
            with cols[0]:
                st.markdown(f"**{row['Player']}**")
            with cols[1]:
                st.markdown(row['Club'])
            with cols[2]:
                st.markdown(str(row['Age']))
            with cols[3]:
                st.markdown(row['Market Value (€)'])
            with cols[4]:
                st.markdown(f"**{row['Rating']}**")
            with cols[5]:
                if st.button("📊", key=f"explore_{int(row['player_id'])}"):
                    navigate_to("Player Dashboard", int(row['player_id']))
            st.divider()
    
    # Quick Analysis Section
    st.markdown("---")
    st.markdown("### Quick Analysis")
    
    analysis_type = st.selectbox("Analysis Type", 
                                  ["Attacking Output", "Defensive Contribution", "Form & Consistency"],
                                  key="quick_analysis_type")
    
    position_filter = st.selectbox("Position Filter", 
                                    ["All", "Goalkeepers", "Defenders", "Midfielders", "Forwards"],
                                    key="quick_analysis_position")
    
    # Perform analysis
    if analysis_type == "Attacking Output":
        st.markdown("#### Top Scorers")
        top_scorers = filtered.nlargest(10, 'total_goals')[['web_name', 'position', 'club_name', 'total_minutes', 'total_goals', 'total_xg']]
        st.dataframe(top_scorers, hide_index=True)
    elif analysis_type == "Defensive Contribution":
        st.markdown("#### Top Tacklers")
        top_tacklers = filtered.nlargest(10, 'total_tackles')[['web_name', 'position', 'club_name', 'total_minutes', 'total_tackles', 'total_interceptions']]
        st.dataframe(top_tacklers, hide_index=True)
    else:
        st.markdown("#### Highest Composite Rating")
        top_rated = filtered.nlargest(10, 'composite_rating')[['web_name', 'position', 'club_name', 'composite_rating', 'total_matches']]
        st.dataframe(top_rated, hide_index=True)


def render_player_dashboard():
    """Render player dashboard page."""
    player_id = st.session_state.get('selected_player_id')
    
    if player_id is None:
        st.warning("No player selected. Please select a player from the Explorer.")
        if st.button("← Back to Explorer"):
            navigate_to("Player Explorer")
        return
    
    data_loader = DataLoader()
    stats_service = PlayerStatsService(data_loader)
    watchlist_service = WatchlistService(data_loader)
    
    # Get player data
    profile, player_stats = stats_service.get_player_detailed_stats(player_id)
    
    if profile is None:
        st.error(f"Failed to get stats for player {player_id}")
        if st.button("← Back"):
            navigate_to("Player Explorer")
        return
    
    st.title(f"{profile.web_name}")
    
    # Layout: Left panel + Tabs
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.markdown("### Profile")
        st.image("https://via.placeholder.com/200x200?text=Player", use_container_width=True)
        st.markdown(f"**Name:** {profile.name}")
        st.markdown(f"**Age:** {profile.age}")
        if profile.height_cm:
            st.markdown(f"**Height:** {profile.height_cm} cm")
        st.markdown(f"**Club:** {profile.club_name}")
        st.markdown(f"**Position:** {profile.position}" + (f" ({profile.sub_position})" if profile.sub_position else ""))
        st.markdown(f"**Nationality:** {profile.nationality}")
        st.markdown(f"**Foot:** {profile.foot}")
        st.markdown(f"**Market Value:** €{profile.market_value/1e6:.1f}M" if profile.market_value >= 1e6 else f"€{profile.market_value/1e3:.0f}K")
        st.markdown(f"**Contract:** {profile.contract_expiry if profile.contract_expiry else 'N/A'}")
        
        # Watchlist button
        watchlist = watchlist_service.get_watchlist()
        in_watchlist = any(item.get('player_id') == player_id for item in watchlist)
        
        if in_watchlist:
            if st.button("Remove from Watchlist", use_container_width=True, key="remove_wl"):
                watchlist_service.remove_from_watchlist(player_id)
                st.success("Removed from watchlist!")
                st.rerun()
        else:
            if st.button("Add to Watchlist", use_container_width=True, key="add_wl"):
                with st.form("add_to_wl_form"):
                    notes = st.text_area("Notes")
                    tags = st.text_input("Tags (comma-separated)")
                    if st.form_submit_button("Save"):
                        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
                        if watchlist_service.add_to_watchlist(player_id, notes, tag_list):
                            st.success("Added to watchlist!")
                            st.rerun()
                        else:
                            st.error("Failed to add to watchlist")
    
    with col2:
        tab1, tab2, tab3 = st.tabs(["Overview", "Performance", "Records"])
        
        with tab1:
            st.markdown(f"Based on {profile.total_matches} matches")
            
            # Metric cards
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Goals", profile.goals)
            m2.metric("Assists", profile.assists)
            m3.metric("xG", f"{profile.xg:.2f}")
            m4.metric("xA", f"{profile.xa:.2f}")
            m5.metric("Rating", profile.composite_rating)
            
            # Radar chart
            avg_stats = stats_service.get_positional_averages(profile.position)
            
            categories = ['Goals', 'Assists', 'xG', 'xA', 'Tackles', 'Interceptions', 'Threat', 'Creativity']
            
            player_values = [
                profile.goals / max(profile.total_matches, 1),
                profile.assists / max(profile.total_matches, 1),
                profile.xg / max(profile.total_matches, 1),
                profile.xa / max(profile.total_matches, 1),
                profile.tackles / max(profile.total_matches, 1),
                profile.interceptions / max(profile.total_matches, 1),
                player_stats['threat'].mean() if 'threat' in player_stats.columns else 0,
                player_stats['creativity'].mean() if 'creativity' in player_stats.columns else 0
            ]
            
            avg_values = [
                avg_stats.get('goals_scored', 0),
                avg_stats.get('assists', 0),
                avg_stats.get('expected_goals', 0),
                avg_stats.get('expected_assists', 0),
                avg_stats.get('tackles', 0),
                avg_stats.get('clearances_blocks_interceptions', 0),
                avg_stats.get('threat', 0),
                avg_stats.get('creativity', 0)
            ]
            
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(r=player_values, theta=categories, fill='toself', name=profile.web_name))
            fig.add_trace(go.Scatterpolar(r=avg_values, theta=categories, fill='toself', name='Position Avg'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True)), showlegend=True)
            st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            metric = st.selectbox("Select Metric", 
                                   ["composite_rating", "goals_scored", "assists", "expected_goals", "expected_assists", "tackles"],
                                   key="perf_metric")
            
            if 'gw' in player_stats.columns and metric in player_stats.columns:
                fig = px.line(player_stats, x='gw', y=metric, title=f"{metric} by Gameweek", markers=True)
                st.plotly_chart(fig, use_container_width=True)
        
        with tab3:
            st.markdown("### Match Records")
            display_cols = ['gw', 'minutes', 'goals_scored', 'assists', 'expected_goals', 'expected_assists', 'tackles', 'clearances_blocks_interceptions']
            available_cols = [c for c in display_cols if c in player_stats.columns]
            st.dataframe(player_stats[available_cols], hide_index=True)
    
    if st.button("← Back"):
        navigate_to("Player Explorer")


def render_watchlist():
    """Render watchlist page."""
    st.title("⭐ My Watchlist")
    
    data_loader = DataLoader()
    watchlist_service = WatchlistService(data_loader)
    
    watchlist = watchlist_service.get_watchlist()
    
    # Add player section
    with st.expander("Add Player to Watchlist"):
        info_df = data_loader.load_player_info()
        player_options = info_df.apply(
            lambda x: f"{x.get('web_name', x.get('name', 'Unknown'))} ({x.get('club_name', 'Unknown')})", 
            axis=1
        )
        
        selected = st.selectbox("Select Player", player_options.tolist(), key="wl_add_player")
        notes = st.text_area("Notes", key="wl_notes")
        tags = st.text_input("Tags (comma-separated)", key="wl_tags")
        
        if st.button("Add to Watchlist"):
            player_id = info_df[player_options == selected]['player_id'].iloc[0]
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]
            if watchlist_service.add_to_watchlist(player_id, notes, tag_list):
                st.success("Added!")
                st.rerun()
            else:
                st.error("Already in watchlist or failed")
    
    if not watchlist:
        st.info("Your watchlist is empty.")
        return
    
    # Filters
    all_tags = set()
    for item in watchlist:
        all_tags.update(item.get('tags', []))
    
    col1, col2 = st.columns(2)
    with col1:
        filter_tags = st.multiselect("Filter by Tags", list(all_tags), key="wl_filter_tags")
    with col2:
        filter_pos = st.selectbox("Filter by Position", ["All"] + list(info_df['position'].unique()), key="wl_filter_pos")
    
    # Display watchlist
    for item in watchlist:
        if filter_tags and not set(item.get('tags', [])).intersection(filter_tags):
            continue
        
        col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 2, 3, 1, 1])
        
        with col1:
            st.markdown(f"**{item.get('player_name', 'Unknown')}**")
        with col2:
            st.markdown(item.get('club_name', ''))
        with col3:
            st.markdown(item.get('position', ''))
        with col4:
            tags_display = ", ".join(item.get('tags', []))
            st.markdown(f"🏷️ {tags_display}")
        with col5:
            if st.button("✏️", key=f"edit_wl_{item['player_id']}"):
                with st.form(f"edit_form_{item['player_id']}"):
                    new_notes = st.text_area("Notes", value=item.get('notes', ''), key=f"edit_notes_{item['player_id']}")
                    new_tags = st.text_input("Tags", value=", ".join(item.get('tags', [])), key=f"edit_tags_{item['player_id']}")
                    if st.form_submit_button("Update"):
                        tag_list = [t.strip() for t in new_tags.split(",") if t.strip()]
                        watchlist_service.update_watchlist_entry(item['player_id'], new_notes, tag_list)
                        st.rerun()
        with col6:
            if st.button("🗑️", key=f"del_wl_{item['player_id']}"):
                watchlist_service.remove_from_watchlist(item['player_id'])
                st.rerun()
        
        st.divider()
    
    if st.button("🗑️ Clear All Watchlist", type="primary"):
        if st.confirm("Are you sure?"):
            watchlist_service.clear_watchlist()
            st.rerun()


def render_advanced_scouting():
    """Render advanced scouting page."""
    st.title("🎯 Advanced Scouting")
    
    data_loader = DataLoader()
    stats_service = PlayerStatsService(data_loader)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### Search Criteria")
        
        info_df = data_loader.load_player_info()
        
        position = st.selectbox("Position", ["All"] + list(info_df['position'].unique()), key="scout_pos")
        max_value = st.number_input("Max Market Value (€)", min_value=0, value=100000000, key="scout_max_val")
        max_results = st.number_input("Max Results", min_value=1, max_value=50, value=10, key="scout_limit")
        
        skills = st.multiselect("Skills", 
                                 ["Goal Scoring", "Passing", "Defending", "Pace", "Physical", "Technical"],
                                 key="scout_skills")
        
        skill_weights = {}
        for skill in skills[:5]:
            skill_weights[skill] = st.slider(f"{skill} Weight", 0, 100, 50, key=f"weight_{skill}")
        
        if st.button("Search", use_container_width=True, key="scout_search"):
            summary = stats_service.get_all_players_summary()
            
            # Filter
            filtered = summary.copy()
            if position != "All":
                filtered = filtered[filtered['position'] == position]
            if 'market_value_in_eur' in filtered.columns:
                filtered = filtered[filtered['market_value_in_eur'] <= max_value]
            
            # Sort by composite rating
            results = filtered.nlargest(max_results, 'composite_rating')
            
            st.session_state.scout_results = results.to_dict('records')
    
    with col2:
        if 'scout_results' in st.session_state and st.session_state.scout_results:
            results = st.session_state.scout_results
            
            st.markdown("### Results")
            
            for i, player in enumerate(results):
                cols = st.columns([1, 3, 2, 2, 2, 2])
                with cols[0]:
                    st.markdown(f"#{i+1}")
                with cols[1]:
                    st.markdown(f"**{player.get('web_name', 'Unknown')}**")
                with cols[2]:
                    st.markdown(player.get('club_name', ''))
                with cols[3]:
                    st.markdown(player.get('position', ''))
                with cols[4]:
                    st.markdown(f"Rating: {player.get('composite_rating', 0)}")
                with cols[5]:
                    if st.button("📊", key=f"scout_view_{player['player_id']}"):
                        navigate_to("Player Dashboard", player['player_id'])
                
                st.divider()
            
            # Radar chart for top player
            if results:
                top_player = results[0]
                profile, _ = stats_service.get_player_detailed_stats(top_player['player_id'])
                if profile:
                    avg_stats = stats_service.get_positional_averages(profile.position)
                    
                    categories = ['Goals', 'Assists', 'xG', 'xA', 'Tackles', 'Interceptions']
                    player_vals = [profile.goals, profile.assists, profile.xg, profile.xa, profile.tackles, profile.interceptions]
                    avg_vals = [avg_stats.get('goals_scored', 0), avg_stats.get('assists', 0), 
                               avg_stats.get('expected_goals', 0), avg_stats.get('expected_assists', 0),
                               avg_stats.get('tackles', 0), avg_stats.get('clearances_blocks_interceptions', 0)]
                    
                    fig = go.Figure()
                    fig.add_trace(go.Scatterpolar(r=player_vals, theta=categories, fill='toself', name=profile.web_name))
                    fig.add_trace(go.Scatterpolar(r=avg_vals, theta=categories, fill='toself', name='Avg'))
                    fig.update_layout(polar=dict(radialaxis=dict(visible=True)), showlegend=True)
                    st.plotly_chart(fig, use_container_width=True)


def render_player_valuation():
    """Render player valuation page."""
    st.title("💰 Player Valuation")
    
    data_loader = DataLoader()
    stats_service = PlayerStatsService(data_loader)
    
    info_df = data_loader.load_player_info()
    
    # Player selection
    player_options = info_df.apply(
        lambda x: f"{x.get('web_name', x.get('name', 'Unknown'))} ({x.get('club_name', 'Unknown')})", 
        axis=1
    )
    
    selected = st.selectbox("Select Player for Valuation", player_options.tolist(), key="val_player")
    
    if selected:
        player_id = info_df[player_options == selected]['player_id'].iloc[0]
        profile, _ = stats_service.get_player_detailed_stats(player_id)
        
        if profile:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### Player Stats vs Position Average")
                avg_stats = stats_service.get_positional_averages(profile.position)
                
                stats_df = pd.DataFrame({
                    'Stat': ['Goals', 'Assists', 'xG', 'xA'],
                    'Player': [profile.goals, profile.assists, profile.xg, profile.xa],
                    'Position Avg': [avg_stats.get('goals_scored', 0), avg_stats.get('assists', 0),
                                    avg_stats.get('expected_goals', 0), avg_stats.get('expected_assists', 0)]
                })
                st.dataframe(stats_df, hide_index=True)
            
            with col2:
                st.markdown("### Valuation")
                actual_value = profile.market_value
                predicted_value = actual_value * (1 + (profile.composite_rating - 50) / 100)  # Simple model
                
                st.metric("Actual Market Value", f"€{actual_value/1e6:.2f}M")
                st.metric("Predicted Value", f"€{predicted_value/1e6:.2f}M")
                
                diff_pct = ((predicted_value - actual_value) / actual_value) * 100 if actual_value > 0 else 0
                st.metric("Difference", f"{diff_pct:.1f}%")
                
                if predicted_value > actual_value:
                    st.success("Underperform (Good Value!)")
                else:
                    st.warning("Overperform (Expensive)")
            
            # Cheap Beasts section
            st.markdown("---")
            st.markdown("### Cheap Beasts")
            
            summary = stats_service.get_all_players_summary()
            
            # Value for money
            if 'market_value_in_eur' in summary.columns and summary['market_value_in_eur'].max() > 0:
                summary['value_rating'] = summary['composite_rating'] / (summary['market_value_in_eur'] / 1e6 + 1)
                
                cheap_beasts = summary[summary['market_value_in_eur'] < 10e6].nlargest(20, 'value_rating')
                
                st.dataframe(cheap_beasts[['web_name', 'club_name', 'position', 'market_value_in_eur', 'composite_rating', 'value_rating']].head(10), hide_index=True)


def main():
    """Main application entry point."""
    st.set_page_config(page_title="Football Scout Pro", layout="wide", page_icon="⚽")
    
    init_session_state()
    render_sidebar()
    
    page = st.session_state.current_page
    
    try:
        if page == "Home":
            render_home()
        elif page == "Player Explorer":
            render_player_explorer()
        elif page == "Player Dashboard":
            render_player_dashboard()
        elif page == "My Watchlist":
            render_watchlist()
        elif page == "Advanced Scouting":
            render_advanced_scouting()
        elif page == "Player Valuation":
            render_player_valuation()
        else:
            render_home()
    except Exception as e:
        logger.error(f"Application error: {e}")
        st.error(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
