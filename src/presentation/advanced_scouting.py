"""Advanced Scouting page presentation."""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Dict, Any, List

from ..domain.services import PlayerService, ScoutingService


def render_advanced_scouting(
    player_service: PlayerService,
    scouting_service: ScoutingService,
):
    """Render the advanced scouting page."""
    st.title("🎯 Advanced Scouting")
    
    # Left column - Search criteria
    left_col, right_col = st.columns([1, 2])
    
    with left_col:
        st.markdown("### Search Criteria")
        
        # League dropdown (only one league in our data)
        all_clubs = player_service.player_info_repo.get_unique_clubs()
        st.selectbox("League", options=["Premier League"], disabled=True)
        
        # Position dropdown
        all_positions = player_service.player_info_repo.get_unique_positions()
        position = st.selectbox(
            "Position",
            options=["All"] + all_positions,
        )
        
        # Max market value slider
        max_value = st.slider(
            "Max Market Value (€)",
            min_value=0,
            max_value=200_000_000,
            value=200_000_000,
            step=5_000_000,
        )
        
        # Max results
        max_results = st.number_input(
            "Max Results",
            min_value=1,
            max_value=50,
            value=10,
        )
        
        # Skill selection
        st.markdown("### Skills (max 5)")
        
        skill_options = {
            "goal_scoring": "Goal Scoring",
            "goal_efficiency": "Goal Efficiency",
            "shooting": "Shooting",
            "passing_influence": "Passing Influence",
            "goal_creation": "Goal Creation",
            "possession_influence": "Possession Influence",
            "progression": "Progression",
            "dribbling": "Dribbling",
            "aerial_influence": "Aerial Influence",
            "defensive_influence": "Defensive Influence",
            "discipline_consistency": "Discipline & Consistency",
        }
        
        selected_skills = {}
        
        for skill_key, skill_name in skill_options.items():
            if st.checkbox(skill_name, key=skill_key):
                weight = st.slider(
                    f"{skill_name} Weight",
                    min_value=0,
                    max_value=100,
                    value=50,
                    key=f"weight_{skill_key}",
                )
                selected_skills[skill_key] = weight
        
        # Limit to 5 skills
        if len(selected_skills) > 5:
            st.warning("Maximum 5 skills can be selected.")
            selected_skills = dict(list(selected_skills.items())[:5])
        
        # Search button
        if st.button("🔍 Search", use_container_width=True):
            if not selected_skills:
                st.warning("Please select at least one skill.")
            else:
                st.session_state.scouting_results = scouting_service.search_players(
                    skills=selected_skills,
                    max_results=max_results,
                    position=None if position == "All" else position,
                    max_value=max_value if max_value < 200_000_000 else None,
                )
                st.session_state.show_scouting_results = True
    
    # Right column - Results
    with right_col:
        if st.session_state.get("show_scouting_results"):
            results = st.session_state.get("scouting_results", [])
            
            if results:
                st.markdown("### Results")
                
                # Build table
                table_data = []
                for item in results:
                    player = item['player']
                    table_data.append({
                        "Player": player.web_name,
                        "Club": player.club_name,
                        "Position": player.position,
                        "Age": player.age,
                        "Market Value": f"€{player.info.market_value_in_eur / 1_000_000:.1f}M",
                        "Compatibility": item['compatibility'],
                        "player_id": player.player_id,
                    })
                
                df = pd.DataFrame(table_data)
                st.dataframe(df, use_container_width=True)
                
                # Show radar chart for top player
                if results:
                    top_player = results[0]['player']
                    st.markdown(f"### Top Player: {top_player.web_name}")
                    
                    stats = player_service.player_stats_repo.get_aggregated_stats(top_player.player_id)
                    positional_avg = player_service.get_positional_averages(top_player.position)
                    
                    categories = ['Goals', 'Assists', 'xG', 'xA', 'Tackles', 'Interceptions', 'Threat', 'Creativity']
                    
                    player_vals = [
                        stats.get('total_goals', 0),
                        stats.get('total_assists', 0),
                        stats.get('avg_expected_goals', 0) * stats.get('total_matches', 1),
                        stats.get('avg_expected_assists', 0) * stats.get('total_matches', 1),
                        stats.get('total_tackles', 0),
                        stats.get('total_clearances_blocks_interceptions', 0),
                        stats.get('avg_threat', 0),
                        stats.get('avg_creativity', 0),
                    ]
                    
                    avg_vals = [
                        positional_avg.get('goals', 0),
                        positional_avg.get('assists', 0),
                        positional_avg.get('xG', 0),
                        positional_avg.get('xA', 0),
                        positional_avg.get('tackles', 0),
                        positional_avg.get('interceptions', 0),
                        positional_avg.get('threat', 0),
                        positional_avg.get('creativity', 0),
                    ]
                    
                    # Normalize
                    max_vals = [max(p, a, 1) for p, a in zip(player_vals, avg_vals)]
                    player_norm = [p / m for p, m in zip(player_vals, max_vals)]
                    avg_norm = [a / m for a, m in zip(avg_vals, max_vals)]
                    
                    fig = go.Figure()
                    
                    fig.add_trace(go.Scatterpolar(
                        r=player_norm,
                        theta=categories,
                        fill='toself',
                        name=top_player.web_name
                    ))
                    
                    fig.add_trace(go.Scatterpolar(
                        r=avg_norm,
                        theta=categories,
                        fill='toself',
                        name=f'{top_player.position} Avg'
                    ))
                    
                    fig.update_layout(
                        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
                        showlegend=True,
                        height=400,
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                
                # Find Similar buttons
                st.markdown("### Find Similar Players")
                
                for item in results:
                    player = item['player']
                    
                    col1, col2 = st.columns([3, 1])
                    col1.write(f"**{player.web_name}** ({player.club_name})")
                    
                    if col2.button("Find Similar", key=f"similar_{player.player_id}"):
                        similar_players = player_service.find_similar_players(player.player_id, limit=10)
                        st.session_state[f"similar_{player.player_id}"] = similar_players
                
                # Show similar players sub-tables
                for item in results:
                    player = item['player']
                    similar_key = f"similar_{player.player_id}"
                    
                    if st.session_state.get(similar_key):
                        similar = st.session_state[similar_key]
                        
                        with st.expander(f"Similar to {player.web_name}", expanded=False):
                            sim_data = []
                            for s in similar:
                                sim_player = s['player']
                                sim_data.append({
                                    "Player": sim_player.web_name,
                                    "Club": sim_player.club_name,
                                    "Similarity": s['similarity'],
                                    "player_id": sim_player.player_id,
                                })
                            
                            sim_df = pd.DataFrame(sim_data)
                            st.dataframe(sim_df, use_container_width=True)
            else:
                st.info("No results found. Try adjusting your criteria.")
        else:
            st.info("Configure search criteria and click Search to see results.")
