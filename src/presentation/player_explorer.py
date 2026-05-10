"""Player Explorer page presentation."""
import streamlit as st
import pandas as pd
import plotly.express as px
from typing import List, Dict, Any, Optional

from ..domain.models import PlayerComposite
from ..domain.services import PlayerService


def format_market_value(value: int) -> str:
    """Format market value as string."""
    if value >= 1_000_000_000:
        return f"€{value / 1_000_000_000:.1f}B"
    elif value >= 1_000_000:
        return f"€{value / 1_000_000:.1f}M"
    else:
        return f"€{value / 1_000:.0f}K"


def render_player_explorer(player_service: PlayerService):
    """Render the player explorer page."""
    st.title("🔍 Player Explorer")
    
    # Initialize session state for filters
    if "explorer_filters" not in st.session_state:
        st.session_state.explorer_filters = {
            "clubs": [],
            "positions": [],
            "min_age": 16,
            "max_age": 45,
            "min_value": 0,
            "max_value": 200_000_000,
        }
    
    # Filter bar
    with st.expander("📊 Filters", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            # Get unique clubs and positions
            all_clubs = player_service.player_info_repo.get_unique_clubs()
            all_positions = player_service.player_info_repo.get_unique_positions()
            
            selected_clubs = st.multiselect(
                "Club",
                options=all_clubs,
                default=st.session_state.explorer_filters["clubs"],
            )
            
            selected_positions = st.multiselect(
                "Position",
                options=all_positions,
                default=st.session_state.explorer_filters["positions"],
            )
        
        with col2:
            age_range = st.slider(
                "Age Range",
                min_value=16,
                max_value=45,
                value=(st.session_state.explorer_filters["min_age"], 
                       st.session_state.explorer_filters["max_age"]),
            )
            
            value_range = st.slider(
                "Market Value Range (€)",
                min_value=0,
                max_value=200_000_000,
                value=(st.session_state.explorer_filters["min_value"],
                       st.session_state.explorer_filters["max_value"]),
                step=1_000_000,
            )
            
            # Update session state
            st.session_state.explorer_filters["clubs"] = selected_clubs
            st.session_state.explorer_filters["positions"] = selected_positions
            st.session_state.explorer_filters["min_age"] = age_range[0]
            st.session_state.explorer_filters["max_age"] = age_range[1]
            st.session_state.explorer_filters["min_value"] = value_range[0]
            st.session_state.explorer_filters["max_value"] = value_range[1]
    
    # Apply filters
    filtered_players = player_service.filter_players(
        clubs=selected_clubs if selected_clubs else None,
        positions=selected_positions if selected_positions else None,
        min_age=age_range[0],
        max_age=age_range[1],
        min_value=value_range[0],
        max_value=value_range[1],
    )
    
    # Build table data
    table_data = []
    for p in filtered_players:
        rating = player_service.calculate_composite_rating(p.player_id)
        table_data.append({
            "Player": p.web_name,
            "Club": p.club_name,
            "Age": p.age,
            "Market Value": format_market_value(p.market_value_in_eur),
            "Overall Rating": rating,
            "player_id": p.player_id,
        })
    
    if table_data:
        df = pd.DataFrame(table_data)
        
        # Display table with clickable names
        def make_clickable(row):
            player_id = row["player_id"]
            name = row["Player"]
            return f'<a href="#" onclick="document.getElementById(\'player_{player_id}\').click();">{name}</a>'
        
        # Store player_ids for navigation
        for idx, row in df.iterrows():
            player_id = row["player_id"]
            col = st.columns(5)
            col[0].markdown(f"**[{row['Player']}](#)**", help=f"Click to view dashboard")
            if col[0].button("👁️", key=f"view_{player_id}", help="View Dashboard"):
                st.session_state.selected_player_id = player_id
                st.session_state.current_page = "player_dashboard"
                st.rerun()
            col[1].write(row["Club"])
            col[2].write(str(row["Age"]))
            col[3].write(row["Market Value"])
            col[4].write(str(row["Overall Rating"]))
        
        # Quick Analysis section
        st.markdown("---")
        st.subheader("📈 Quick Analysis")
        
        analysis_option = st.selectbox(
            "Select Analysis Type",
            ["Attacking Output", "Defensive Contribution", "Form & Consistency"],
        )
        
        position_filter = st.selectbox(
            "Filter by Position",
            ["All", "Goalkeepers", "Defenders", "Midfielders", "Forwards"],
        )
        
        # Perform analysis based on selection
        results = perform_analysis(player_service, analysis_option, position_filter)
        
        if results:
            display_analysis_results(results, analysis_option, player_service)
    else:
        st.warning("No players match the selected filters.")


def perform_analysis(
    player_service: PlayerService,
    analysis_type: str,
    position_filter: str,
) -> List[Dict[str, Any]]:
    """Perform quick analysis based on type."""
    # Map position filter to actual positions
    pos_map = {
        "All": None,
        "Goalkeepers": ["Goalkeeper"],
        "Defenders": ["Defender"],
        "Midfielders": ["Midfielder"],
        "Forwards": ["Forward"],
    }
    positions = pos_map.get(position_filter)
    
    if analysis_type == "Attacking Output":
        analysis_subtype = st.selectbox(
            "Select Metric",
            ["Top Scorers", "Top Assisters", "Top G/A", "Best xG Performance", "Top Young Attackers (U23)"],
        )
        
        if analysis_subtype == "Top Scorers":
            return player_service.get_top_scorers(limit=10)
        elif analysis_subtype == "Top Assisters":
            return player_service.get_top_assisters(limit=10)
        # Add more subtypes as needed
    
    elif analysis_type == "Defensive Contribution":
        analysis_subtype = st.selectbox(
            "Select Metric",
            ["Top Tacklers per 90", "Top Interceptors per 90", "Most Recoveries per 90"],
        )
        # Implementation for defensive analysis
    
    elif analysis_type == "Form & Consistency":
        analysis_subtype = st.selectbox(
            "Select Metric",
            ["Highest Composite Rating", "Most In-form Players", "Most Minutes Played"],
        )
        # Implementation for form analysis
    
    return []


def display_analysis_results(
    results: List[Dict[str, Any]],
    analysis_type: str,
    player_service: PlayerService,
):
    """Display analysis results."""
    st.markdown(f"### {analysis_type} - Top 10")
    
    if not results:
        st.info("No results available for this analysis.")
        return
    
    # Build results table
    table_data = []
    for item in results:
        player = item.get("player")
        if not player:
            continue
        
        table_data.append({
            "Player": player.web_name,
            "Age": player.age,
            "Position": player.position,
            "Club": player.club_name,
            "Minutes": item.get("minutes", 0),
            "Value": item.get("goals", item.get("assists", 0)),
            "player_id": player.player_id,
        })
    
    if table_data:
        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True)
        
        # Create chart
        fig = px.bar(
            df.head(10),
            x="Player",
            y="Value",
            title=f"Top 10 - {analysis_type}",
            labels={"Value": analysis_type.split()[1]},
        )
        st.plotly_chart(fig, use_container_width=True)
