"""Player Valuation page presentation."""
import streamlit as st
import pandas as pd
from typing import Dict, Any, List

from ..domain.services import PlayerService, ValuationService


def render_player_valuation(
    player_service: PlayerService,
    valuation_service: ValuationService,
):
    """Render the player valuation page."""
    st.title("💰 Player Valuation")
    
    # Player selection
    all_players = player_service.get_all_players()
    player_options = {
        f"{p.web_name} ({p.club_name})": p.player_id 
        for p in all_players
    }
    
    selected_player_name = st.selectbox(
        "Select a Player",
        options=list(player_options.keys()),
    )
    
    if selected_player_name:
        player_id = player_options[selected_player_name]
        player = player_service.get_player_by_id(player_id)
        
        if player:
            # Individual analysis
            st.markdown("### Individual Analysis")
            
            valuation = valuation_service.predict_market_value(player_id)
            
            if valuation:
                col1, col2, col3 = st.columns(3)
                
                col1.metric(
                    "Actual Market Value",
                    f"€{valuation['actual_value'] / 1_000_000:.1f}M"
                )
                col2.metric(
                    "Predicted Value",
                    f"€{valuation['predicted_value'] / 1_000_000:.1f}M"
                )
                col3.metric(
                    "Difference",
                    f"{valuation['diff_percent']:+.1f}%"
                )
                
                if valuation['is_overperform']:
                    st.success("📈 **Overperform**: Player's actual value is lower than predicted!")
                else:
                    st.warning("📉 **Underperform**: Player's actual value is higher than predicted.")
                
                # Potential stars
                stars = "⭐" * valuation['potential_stars']
                st.write(f"**Potential Rating:** {stars}")
                
                # Comparison table
                st.markdown("### Stats vs Positional Average")
                
                stats = player_service.player_stats_repo.get_aggregated_stats(player_id)
                positional_avg = player_service.get_positional_averages(player.position)
                
                comparison_data = []
                metrics = [
                    ("Goals", stats.get('total_goals', 0), positional_avg.get('goals', 0)),
                    ("Assists", stats.get('total_assists', 0), positional_avg.get('assists', 0)),
                    ("xG", f"{stats.get('avg_expected_goals', 0):.2f}", f"{positional_avg.get('xG', 0):.2f}"),
                    ("xA", f"{stats.get('avg_expected_assists', 0):.2f}", f"{positional_avg.get('xA', 0):.2f}"),
                    ("Tackles", stats.get('total_tackles', 0), positional_avg.get('tackles', 0)),
                    ("Interceptions", stats.get('total_clearances_blocks_interceptions', 0), 
                     positional_avg.get('interceptions', 0)),
                ]
                
                for name, player_val, avg_val in metrics:
                    comparison_data.append({
                        "Metric": name,
                        "Player": player_val,
                        f"{player.position} Avg": avg_val,
                    })
                
                comp_df = pd.DataFrame(comparison_data)
                st.dataframe(comp_df, use_container_width=True)
    
    # Cheap Beasts section
    st.markdown("---")
    st.subheader("🦁 Cheap Beasts")
    
    cb_col1, cb_col2 = st.columns(2)
    
    with cb_col1:
        cb_position = st.selectbox(
            "Position",
            options=["All"] + player_service.player_info_repo.get_unique_positions(),
            key="cb_position"
        )
    
    with cb_col2:
        cb_max_value = st.slider(
            "Max Market Value (€M)",
            min_value=10,
            max_value=100,
            value=50,
            step=5,
            key="cb_max_value"
        )
    
    # Mode tabs
    mode = st.tabs(["Value Picks", "Cheaper Similar", "Better at Same Price"])
    
    with mode[0]:
        if st.button("Find Cheap Beasts"):
            cheap_beasts = valuation_service.find_cheap_beasts(
                position=None if cb_position == "All" else cb_position,
                max_value=cb_max_value * 1_000_000,
                limit=20,
            )
            st.session_state.cheap_beasts = cheap_beasts
        
        if st.session_state.get("cheap_beasts"):
            beasts = st.session_state.cheap_beasts
            
            beast_data = []
            for b in beasts:
                player = b['player']
                stats = b['stats']
                
                beast_data.append({
                    "Player": player.web_name,
                    "Club": player.club_name,
                    "Position": player.position,
                    "Market Value": f"€{player.info.market_value_in_eur / 1_000_000:.1f}M",
                    "Value Rating": b['value_ratio'],
                    "G+A": stats.get('total_goals', 0) + stats.get('total_assists', 0),
                    "Rating": b['rating'],
                    "player_id": player.player_id,
                })
            
            beast_df = pd.DataFrame(beast_data)
            st.dataframe(beast_df, use_container_width=True)
    
    with mode[1]:
        # Cheaper Similar Players
        ref_player_name = st.selectbox(
            "Reference Player",
            options=list(player_options.keys()),
            key="ref_cheaper"
        )
        
        if st.button("Find Cheaper Similar"):
            ref_id = player_options[ref_player_name]
            cheaper = valuation_service.find_cheaper_similar(ref_id, limit=10)
            st.session_state.cheaper_similar = cheaper
        
        if st.session_state.get("cheaper_similar"):
            cheaper = st.session_state.cheaper_similar
            
            cheaper_data = []
            for c in cheaper:
                player = c['player']
                stats = c['stats']
                
                cheaper_data.append({
                    "Player": player.web_name,
                    "Club": player.club_name,
                    "Market Value": f"€{player.info.market_value_in_eur / 1_000_000:.1f}M",
                    "Savings": f"€{c['savings'] / 1_000_000:.1f}M",
                    "G+A": stats.get('total_goals', 0) + stats.get('total_assists', 0),
                    "player_id": player.player_id,
                })
            
            cheaper_df = pd.DataFrame(cheaper_data)
            st.dataframe(cheaper_df, use_container_width=True)
    
    with mode[2]:
        # Better Players at Same Price
        ref_player_name2 = st.selectbox(
            "Reference Player",
            options=list(player_options.keys()),
            key="ref_better"
        )
        
        if st.button("Find Better at Same Price"):
            ref_id = player_options[ref_player_name2]
            better = valuation_service.find_better_at_same_price(ref_id, limit=10)
            st.session_state.better_same_price = better
        
        if st.session_state.get("better_same_price"):
            better = st.session_state.better_same_price
            
            better_data = []
            for b in better:
                player = b['player']
                
                better_data.append({
                    "Player": player.web_name,
                    "Club": player.club_name,
                    "Market Value": f"€{player.info.market_value_in_eur / 1_000_000:.1f}M",
                    "Rating": b['rating'],
                    "Improvement": f"+{b['improvement']:.1f}",
                    "player_id": player.player_id,
                })
            
            better_df = pd.DataFrame(better_data)
            st.dataframe(better_df, use_container_width=True)
