"""Football Scout Pro - Main Application Entry Point.

This application demonstrates a modular architecture with:
- Separation of Concerns (Presentation, Domain, Data layers)
- SOLID Principles (Single Responsibility, Dependency Injection)
- Type Hinting and Pydantic for data validation
- Global Exception Handling and Logging
"""
import streamlit as st
from pathlib import Path

from src.config import get_config
from src.data import (
    CSVPlayerInfoRepository,
    CSVPlayerStatsRepository,
    JSONWatchlistRepository,
)
from src.domain.services import (
    PlayerService,
    WatchlistService,
    ScoutingService,
    ValuationService,
)
from src.presentation import (
    render_home,
    render_player_explorer,
    render_player_dashboard,
    render_watchlist,
    render_advanced_scouting,
    render_player_valuation,
)
from src.core.logging_config import get_logger


logger = get_logger(__name__)


@st.cache_resource
def initialize_services():
    """Initialize all services with dependency injection."""
    config = get_config()
    
    # Initialize repositories (Data Access Layer)
    player_info_repo = CSVPlayerInfoRepository(config.database.players_info_path)
    player_stats_repo = CSVPlayerStatsRepository(config.database.player_stats_path)
    watchlist_repo = JSONWatchlistRepository(config.database.watchlist_path)
    
    # Initialize services (Business Logic Layer)
    player_service = PlayerService(player_info_repo, player_stats_repo)
    watchlist_service = WatchlistService(watchlist_repo, player_service)
    scouting_service = ScoutingService(player_service)
    valuation_service = ValuationService(player_service)
    
    return {
        "player_service": player_service,
        "watchlist_service": watchlist_service,
        "scouting_service": scouting_service,
        "valuation_service": valuation_service,
    }


def setup_sidebar():
    """Setup the sidebar navigation."""
    st.sidebar.title("🏈 Football Scout Pro")
    
    pages = {
        "Home": "home",
        "Player Explorer": "player_explorer",
        "My Watchlist": "watchlist",
        "Advanced Scouting": "advanced_scouting",
        "Player Valuation": "player_valuation",
    }
    
    for page_name, page_key in pages.items():
        if st.sidebar.button(page_name, use_container_width=True):
            st.session_state.current_page = page_key
    
    st.sidebar.markdown("---")
    st.sidebar.info("Select a page to navigate.")


def main():
    """Main application entry point."""
    st.set_page_config(
        page_title="Football Scout Pro",
        page_icon="⚽",
        layout="wide",
    )
    
    # Initialize services
    services = initialize_services()
    
    # Setup sidebar
    setup_sidebar()
    
    # Initialize current page if not set
    if "current_page" not in st.session_state:
        st.session_state.current_page = "home"
    
    # Route to appropriate page
    current_page = st.session_state.current_page
    
    try:
        if current_page == "home":
            render_home()
        elif current_page == "player_explorer":
            render_player_explorer(services["player_service"])
        elif current_page == "player_dashboard":
            render_player_dashboard(
                services["player_service"],
                services["watchlist_service"],
            )
        elif current_page == "watchlist":
            render_watchlist(
                services["player_service"],
                services["watchlist_service"],
            )
        elif current_page == "advanced_scouting":
            render_advanced_scouting(
                services["player_service"],
                services["scouting_service"],
            )
        elif current_page == "player_valuation":
            render_player_valuation(
                services["player_service"],
                services["valuation_service"],
            )
        else:
            render_home()
    
    except Exception as e:
        logger.error(f"Application error: {e}")
        st.error(f"An error occurred: {str(e)}")
        st.info("Please try refreshing the page or contact support.")


if __name__ == "__main__":
    main()
