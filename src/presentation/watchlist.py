"""Watchlist page presentation."""
import streamlit as st
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any

from ..domain.services import PlayerService, WatchlistService


def render_watchlist(
    player_service: PlayerService,
    watchlist_service: WatchlistService,
):
    """Render the watchlist page."""
    st.title("📋 My Watchlist")
    
    # Add new player section
    with st.expander("➕ Add Player to Watchlist", expanded=False):
        all_players = player_service.get_all_players()
        player_options = {
            f"{p.web_name} ({p.club_name})": p.player_id 
            for p in all_players
        }
        
        selected_player = st.selectbox(
            "Select Player",
            options=list(player_options.keys()),
        )
        
        notes = st.text_area("Notes")
        tags = st.text_input("Tags (comma-separated)")
        
        if st.button("Add to Watchlist"):
            player_id = player_options[selected_player]
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]
            
            try:
                watchlist_service.add_to_watchlist(player_id, notes, tag_list)
                st.success(f"Added {selected_player} to watchlist!")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to add: {e}")
    
    # Filter bar
    with st.expander("🔍 Filters", expanded=True):
        all_entries = watchlist_service.get_all_entries()
        
        # Get unique tags, positions, clubs from watchlist
        all_tags = set()
        all_positions = set()
        all_clubs = set()
        
        for item in all_entries:
            all_tags.update(item['entry'].tags)
            all_positions.add(item['player'].position)
            all_clubs.add(item['player'].club_name)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            filter_tags = st.multiselect("Filter by Tags", options=list(all_tags))
        
        with col2:
            filter_position = st.selectbox("Position", options=["All"] + list(all_positions))
        
        with col3:
            filter_club = st.selectbox("Club", options=["All"] + list(all_clubs))
    
    # Apply filters
    filtered_entries = all_entries
    
    if filter_tags:
        filtered_entries = watchlist_service.filter_by_tags(filter_tags)
    
    if filter_position != "All":
        filtered_entries = [
            e for e in filtered_entries 
            if e['player'].position == filter_position
        ]
    
    if filter_club != "All":
        filtered_entries = [
            e for e in filtered_entries 
            if e['player'].club_name == filter_club
        ]
    
    # Display table
    if filtered_entries:
        table_data = []
        for item in filtered_entries:
            entry = item['entry']
            player = item['player']
            
            table_data.append({
                "Player": player.web_name,
                "Club": player.club_name,
                "Position": player.position,
                "Tags": ", ".join(entry.tags),
                "Notes": entry.notes[:50] + "..." if len(entry.notes) > 50 else entry.notes,
                "Date Added": entry.date_added.strftime("%Y-%m-%d"),
                "player_id": player.player_id,
            })
        
        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True)
        
        # Edit/Delete actions
        st.markdown("### Actions")
        
        for item in filtered_entries:
            player = item['player']
            entry = item['entry']
            
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                
                col1.write(f"**{player.web_name}** - {player.club_name}")
                col2.write(f"Tags: {', '.join(entry.tags)}")
                
                if col3.button("✏️ Edit", key=f"edit_{player.player_id}"):
                    st.session_state.edit_player_id = player.player_id
                    st.session_state.show_edit_form = True
                
                if col4.button("🗑️ Delete", key=f"delete_{player.player_id}"):
                    if st.confirmation(f"Delete {player.web_name} from watchlist?"):
                        watchlist_service.remove_from_watchlist(player.player_id)
                        st.success("Removed!")
                        st.rerun()
        
        # Show edit form if requested
        if st.session_state.get("show_edit_form"):
            edit_player_id = st.session_state.get("edit_player_id")
            if edit_player_id:
                entry = watchlist_service.watchlist_repo.get_entry_by_player_id(edit_player_id)
                if entry:
                    with st.form("edit_watchlist_form"):
                        new_notes = st.text_area("Notes", value=entry.notes)
                        new_tags = st.text_input("Tags", value=", ".join(entry.tags))
                        
                        if st.form_submit_button("Update"):
                            tag_list = [t.strip() for t in new_tags.split(",") if t.strip()]
                            watchlist_service.update_watchlist_entry(edit_player_id, new_notes, tag_list)
                            st.session_state.show_edit_form = False
                            st.success("Updated!")
                            st.rerun()
                        
                        if st.form_submit_button("Cancel"):
                            st.session_state.show_edit_form = False
                            st.rerun()
        
        # Clear all button
        st.markdown("---")
        if st.button("🗑️ Clear All Watchlist", type="secondary"):
            if st.confirmation("Are you sure you want to clear all watchlist entries?"):
                watchlist_service.clear_watchlist()
                st.success("Watchlist cleared!")
                st.rerun()
    else:
        st.info("No players in watchlist matching the filters.")
