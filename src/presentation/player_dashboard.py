"""Player Dashboard page presentation."""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Dict, Any, Optional

from ..domain.models import PlayerComposite
from ..domain.services import PlayerService, WatchlistService


def render_player_dashboard(
    player_service: PlayerService,
    watchlist_service: WatchlistService,
):
    """Render the player dashboard page."""
    player_id = st.session_state.get("selected_player_id")
    
    if not player_id:
        st.warning("No player selected. Please select a player from another page.")
        if st.button("← Back to Explorer"):
            st.session_state.current_page = "player_explorer"
            st.rerun()
        return
    
    player = player_service.get_player_by_id(player_id)
    
    if not player:
        st.error(f"Player with ID {player_id} not found.")
        if st.button("← Back to Explorer"):
            st.session_state.current_page = "player_explorer"
            st.rerun()
        return
    
    # Back button
    if st.button("← Back"):
        st.session_state.current_page = "player_explorer"
        st.rerun()
    
    # Layout: Left panel and central area
    left_col, center_col = st.columns([1, 3])
    
    # Left panel - Basic info
    with left_col:
        st.image("https://via.placeholder.com/200x200?text=Player", use_container_width=True)
        
        st.markdown(f"### {player.web_name}")
        st.write(f"**Age:** {player.info.age}")
        st.write(f"**Height:** {player.info.height_in_cm} cm")
        st.write(f"**Club:** {player.club_name}")
        st.write(f"**Position:** {player.position} ({player.info.sub_position})")
        st.write(f"**Nationality:** {player.info.country_of_citizenship}")
        st.write(f"**Preferred Foot:** {player.info.foot}")
        st.write(f"**Market Value:** €{player.info.market_value_in_eur / 1_000_000:.1f}M")
        st.write(f"**Contract Expires:** {player.info.contract_expiration_date}")
        
        # Watchlist button
        in_watchlist = watchlist_service.is_in_watchlist(player_id)
        
        if in_watchlist:
            if st.button("🗑️ Remove from Watchlist", use_container_width=True):
                watchlist_service.remove_from_watchlist(player_id)
                st.success("Removed from watchlist!")
                st.rerun()
        else:
            if st.button("➕ Add to Watchlist", use_container_width=True):
                st.session_state.show_add_watchlist_form = True
                st.session_state.temp_player_id = player_id
                st.rerun()
        
        # Show add form if requested
        if st.session_state.get("show_add_watchlist_form") and st.session_state.get("temp_player_id") == player_id:
            with st.form("add_watchlist_form"):
                notes = st.text_area("Notes")
                tags = st.text_input("Tags (comma-separated)")
                
                if st.form_submit_button("Save"):
                    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
                    watchlist_service.add_to_watchlist(player_id, notes, tag_list)
                    st.session_state.show_add_watchlist_form = False
                    st.success("Added to watchlist!")
                    st.rerun()
                
                if st.form_submit_button("Cancel"):
                    st.session_state.show_add_watchlist_form = False
                    st.rerun()
    
    # Central area - Tabs
    with center_col:
        tab1, tab2, tab3 = st.tabs(["📊 Overview", "📈 Performance", "📋 Records"])
        
        # Tab 1: Overview
        with tab1:
            render_overview_tab(player, player_service)
        
        # Tab 2: Performance
        with tab2:
            render_performance_tab(player, player_service)
        
        # Tab 3: Records
        with tab3:
            render_records_tab(player, player_service)


def render_overview_tab(player: PlayerComposite, player_service: PlayerService):
    """Render the overview tab."""
    stats = player_service.player_stats_repo.get_aggregated_stats(player.player_id)
    total_matches = stats.get("total_matches", 0)
    
    st.write(f"**Based on {total_matches} matches**")
    
    # Metric cards
    cols = st.columns(4)
    
    cols[0].metric("Goals", stats.get("total_goals", 0))
    cols[1].metric("Assists", stats.get("total_assists", 0))
    cols[2].metric("Expected Goals", f"{stats.get('avg_expected_goals', 0):.2f}")
    cols[3].metric("Expected Assists", f"{stats.get('avg_expected_assists', 0):.2f}")
    
    cols2 = st.columns(4)
    cols2[0].metric("Tackles/90", f"{stats.get('tackles_per_90', 0):.2f}")
    cols2[1].metric("Interceptions/90", f"{stats.get('interceptions_per_90', 0):.2f}")
    cols2[2].metric("Composite Rating", player_service.calculate_composite_rating(player.player_id))
    
    # Radar chart
    st.markdown("### Player Comparison vs Position Average")
    
    positional_avg = player_service.get_positional_averages(player.position)
    
    # Prepare radar chart data
    categories = ['Scoring', 'Assisting', 'xG', 'xA', 'Tackles', 'Interceptions', 'Threat', 'Creativity']
    
    player_values = [
        stats.get('total_goals', 0),
        stats.get('total_assists', 0),
        stats.get('avg_expected_goals', 0) * total_matches,
        stats.get('avg_expected_assists', 0) * total_matches,
        stats.get('total_tackles', 0),
        stats.get('total_clearances_blocks_interceptions', 0),
        stats.get('avg_threat', 0),
        stats.get('avg_creativity', 0),
    ]
    
    avg_values = [
        positional_avg.get('goals', 0),
        positional_avg.get('assists', 0),
        positional_avg.get('xG', 0),
        positional_avg.get('xA', 0),
        positional_avg.get('tackles', 0),
        positional_avg.get('interceptions', 0),
        positional_avg.get('threat', 0),
        positional_avg.get('creativity', 0),
    ]
    
    # Normalize for visualization
    max_vals = [max(p, a, 1) for p, a in zip(player_values, avg_values)]
    player_norm = [p / m for p, m in zip(player_values, max_vals)]
    avg_norm = [a / m for a, m in zip(avg_values, max_vals)]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=player_norm,
        theta=categories,
        fill='toself',
        name=player.web_name
    ))
    
    fig.add_trace(go.Scatterpolar(
        r=avg_norm,
        theta=categories,
        fill='toself',
        name=f'{player.position} Avg'
    ))
    
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        showlegend=True,
        height=500,
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_performance_tab(player: PlayerComposite, player_service: PlayerService):
    """Render the performance tab."""
    stats_list = player.stats or []
    
    if not stats_list:
        st.info("No performance data available.")
        return
    
    # Create DataFrame for gameweek data
    df_data = []
    for s in stats_list:
        df_data.append({
            "GW": s.gw,
            "Minutes": s.minutes,
            "Goals": s.goals_scored,
            "Assists": s.assists,
            "xG": s.expected_goals,
            "xA": s.expected_assists,
            "Tackles": s.tackles,
            "Interceptions": s.clearances_blocks_interceptions,
            "ICT Index": s.ict_index,
        })
    
    df = pd.DataFrame(df_data).sort_values("GW")
    
    # Metric selector
    metric = st.selectbox(
        "Select Metric",
        ["Composite Rating", "Goals", "Assists", "Expected Goals", "Expected Assists", 
         "Tackles", "Interceptions", "ICT Index"],
    )
    
    # Map metric to column
    metric_map = {
        "Goals": "Goals",
        "Assists": "Assists",
        "Expected Goals": "xG",
        "Expected Assists": "xA",
        "Tackles": "Tackles",
        "Interceptions": "Interceptions",
        "ICT Index": "ICT Index",
    }
    
    if metric == "Composite Rating":
        # Calculate composite rating per gameweek (simplified)
        df["Rating"] = df["Goals"] * 5 + df["Assists"] * 4 + df["xG"] * 3 + df["xA"] * 2
        y_col = "Rating"
    else:
        y_col = metric_map.get(metric, "Goals")
    
    # Create line chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["GW"],
        y=df[y_col],
        mode='lines+markers',
        name=metric,
    ))
    
    fig.update_layout(
        title=f"{metric} by Gameweek",
        xaxis_title="Gameweek",
        yaxis_title=metric,
        height=400,
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_records_tab(player: PlayerComposite, player_service: PlayerService):
    """Render the records tab."""
    stats_list = player.stats or []
    
    if not stats_list:
        st.info("No match records available.")
        return
    
    # Build table data
    table_data = []
    for s in stats_list:
        rating = s.goals_scored * 5 + s.assists * 4 + s.expected_goals * 3 + s.expected_assists * 2
        table_data.append({
            "Gameweek": s.gw,
            "Minutes": s.minutes,
            "Goals": s.goals_scored,
            "Assists": s.assists,
            "xG": round(s.expected_goals, 2),
            "xA": round(s.expected_assists, 2),
            "Tackles": s.tackles,
            "Interceptions": s.clearances_blocks_interceptions,
            "Rating": round(rating, 1),
        })
    
    df = pd.DataFrame(table_data)
    
    # Pagination
    page_size = 10
    total_pages = (len(df) - 1) // page_size + 1
    
    page = st.slider("Page", 1, total_pages, 1)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    
    st.dataframe(df.iloc[start_idx:end_idx], use_container_width=True)
