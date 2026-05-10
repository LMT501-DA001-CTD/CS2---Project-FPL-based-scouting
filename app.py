import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, date
import json
import os

# Page configuration
st.set_page_config(
    page_title="Football Scout Pro",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
DATA_DIR = "data"
PLAYERSTATS_FILE = os.path.join(DATA_DIR, "playerstats.csv")
PLAYERS_INFO_FILE = os.path.join(DATA_DIR, "players_info.csv")
WATCHLIST_FILE = "watchlist.json"

# Initialize session state
if 'page' not in st.session_state:
    st.session_state.page = 'Home'
if 'selected_player_id' not in st.session_state:
    st.session_state.selected_player_id = None
if 'previous_page' not in st.session_state:
    st.session_state.previous_page = 'Home'

# Load data
@st.cache_data
def load_data():
    player_stats = pd.read_csv(PLAYERSTATS_FILE)
    player_stats = player_stats.rename(columns={'id': 'player_id'})
    player_info = pd.read_csv(PLAYERS_INFO_FILE)
    return player_stats, player_info

def save_watchlist(watchlist):
    with open(WATCHLIST_FILE, 'w') as f:
        json.dump(watchlist, f, indent=2, default=str)

def load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, 'r') as f:
            return json.load(f)
    return {}

def format_market_value(value):
    """Format market value as €X.XM or €X.XB"""
    if value >= 1_000_000_000:
        return f"€{value/1_000_000_000:.1f}B"
    elif value >= 1_000_000:
        return f"€{value/1_000_000:.1f}M"
    elif value >= 1_000:
        return f"€{value/1_000:.0f}K"
    else:
        return f"€{value:.0f}"

def calculate_age(dob_str):
    """Calculate age from date of birth string"""
    try:
        dob = datetime.strptime(dob_str, '%Y-%m-%d')
        today = datetime.now()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return age
    except:
        return None

def calculate_composite_rating(row):
    """Calculate composite rating (0-100) based on performance metrics"""
    # Normalize and combine key metrics
    score = 0
    
    # Goals and assists contribution
    score += min(row.get('goals_scored', 0) * 10, 30)
    score += min(row.get('assists', 0) * 8, 24)
    
    # Expected goals and assists
    score += min(row.get('expected_goals', 0) * 15, 20)
    score += min(row.get('expected_assists', 0) * 12, 16)
    
    # Defensive contribution
    score += min(row.get('tackles', 0) * 2, 10)
    score += min(row.get('clearances_blocks_interceptions', 0) * 1, 8)
    
    # ICT Index contribution
    score += min(row.get('ict_index', 0) * 0.5, 10)
    
    # Discipline penalty
    score -= row.get('yellow_cards', 0) * 2
    score -= row.get('red_cards', 0) * 5
    
    # Clean sheet bonus for defenders and goalkeepers
    score += row.get('clean_sheets', 0) * 3
    
    return min(max(score, 0), 100)

def get_position_category(position):
    """Map sub-position to main position category"""
    position = str(position).lower()
    if 'goalkeeper' in position or 'keeper' in position:
        return 'Goalkeeper'
    elif 'defender' in position or 'centre-back' in position or 'full-back' in position or 'wing-back' in position:
        return 'Defender'
    elif 'midfielder' in position or 'winger' in position:
        return 'Midfielder'
    elif 'forward' in position or 'striker' in position:
        return 'Forward'
    return 'Midfielder'  # Default

# Sidebar navigation
with st.sidebar:
    st.title("⚽ Football Scout Pro")
    st.markdown("---")
    
    menu_options = ['Home', 'Player Explorer', 'My Watchlist', 'Advanced Scouting', 'Player Valuation']
    
    for option in menu_options:
        if st.button(option, key=f"sidebar_{option}", use_container_width=True):
            st.session_state.previous_page = st.session_state.page
            st.session_state.page = option
            st.rerun()
    
    st.markdown("---")
    st.markdown("### About")
    st.markdown("Professional football analytics and scouting tool")

# Home Page
def render_home():
    st.title("⚽ Football Scout Pro")
    st.subheader("Professional Player Analytics & Scouting Platform")
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔍 Player Explorer", use_container_width=True, height=150):
            st.session_state.previous_page = st.session_state.page
            st.session_state.page = 'Player Explorer'
            st.rerun()
        st.markdown("Browse and filter players by club, position, age, and market value")
    
    with col2:
        if st.button("🎯 Advanced Scouting", use_container_width=True, height=150):
            st.session_state.previous_page = st.session_state.page
            st.session_state.page = 'Advanced Scouting'
            st.rerun()
        st.markdown("Find players matching specific skill profiles and tactical requirements")
    
    with col3:
        if st.button("💰 Player Valuation", use_container_width=True, height=150):
            st.session_state.previous_page = st.session_state.page
            st.session_state.page = 'Player Valuation'
            st.rerun()
        st.markdown("Analyze player market values and find undervalued talents")

# Player Dashboard
def render_player_dashboard(player_id):
    player_stats, player_info = load_data()
    
    # Get player info
    player = player_info[player_info['player_id'] == player_id]
    if player.empty:
        st.error("Player not found")
        return
    
    player = player.iloc[0]
    
    # Get player stats
    stats = player_stats[player_stats['player_id'] == player_id].copy()
    
    # Calculate aggregated stats
    total_minutes = stats['minutes'].sum()
    total_goals = stats['goals_scored'].sum()
    total_assists = stats['assists'].sum()
    total_xg = stats['expected_goals'].sum()
    total_xa = stats['expected_assists'].sum()
    total_tackles = stats['tackles'].sum()
    total_interceptions = stats['clearances_blocks_interceptions'].sum()
    
    # Calculate per 90 metrics
    minutes_per_90 = total_minutes / 90 if total_minutes > 0 else 1
    goals_per_90 = total_goals / minutes_per_90
    assists_per_90 = total_assists / minutes_per_90
    tackles_per_90 = total_tackles / minutes_per_90
    interceptions_per_90 = total_interceptions / minutes_per_90
    
    # Calculate average composite rating
    stats['composite_rating'] = stats.apply(calculate_composite_rating, axis=1)
    avg_composite = stats['composite_rating'].mean()
    
    # Left panel - Basic Info
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.markdown("### Player Info")
        # Placeholder image
        st.image("https://via.placeholder.com/200x200?text=Player+Photo", 
                 caption=player['name'], use_container_width=True)
        
        st.markdown(f"**Name:** {player['name']}")
        st.markdown(f"**Age:** {calculate_age(player['date_of_birth'])}")
        st.markdown(f"**Height:** {player['height_in_cm']} cm")
        st.markdown(f"**Club:** {player['club_name']}")
        st.markdown(f"**Position:** {player['sub_position']} ({player['position']})")
        st.markdown(f"**Nationality:** {player['country_of_citizenship']}")
        st.markdown(f"**Preferred Foot:** {player['foot']}")
        st.markdown(f"**Market Value:** {format_market_value(player['market_value_in_eur'])}")
        st.markdown(f"**Contract Expires:** {player['contract_expiration_date']}")
        
        # Watchlist management
        watchlist = load_watchlist()
        player_id_str = str(player_id)
        
        if player_id_str in watchlist:
            if st.button("Remove from Watchlist", use_container_width=True):
                del watchlist[player_id_str]
                save_watchlist(watchlist)
                st.success("Removed from watchlist!")
                st.rerun()
        else:
            if st.button("Add to Watchlist", use_container_width=True):
                with st.form("add_to_watchlist"):
                    notes = st.text_area("Notes")
                    tags = st.text_input("Tags (comma-separated)")
                    if st.form_submit_button("Save"):
                        watchlist[player_id_str] = {
                            'player_id': player_id,
                            'notes': notes,
                            'tags': [t.strip() for t in tags.split(',') if t.strip()],
                            'date_added': datetime.now().strftime('%Y-%m-%d')
                        }
                        save_watchlist(watchlist)
                        st.success("Added to watchlist!")
                        st.rerun()
    
    with col2:
        # Tabs
        tab1, tab2, tab3 = st.tabs(["Overview", "Performance", "Records"])
        
        with tab1:
            st.markdown(f"#### Overview - Based on {len(stats)} matches")
            
            # Metric cards
            cols = st.columns(4)
            cols[0].metric("Goals", total_goals)
            cols[1].metric("Assists", total_assists)
            cols[2].metric("Expected Goals", f"{total_xg:.2f}")
            cols[3].metric("Expected Assists", f"{total_xa:.2f}")
            
            cols2 = st.columns(4)
            cols2[0].metric("Goals/90", f"{goals_per_90:.2f}")
            cols2[1].metric("Assists/90", f"{assists_per_90:.2f}")
            cols2[2].metric("Tackles/90", f"{tackles_per_90:.2f}")
            cols2[3].metric("Composite Rating", f"{avg_composite:.1f}")
            
            # Radar chart
            st.markdown("#### Player Comparison vs Position Average")
            
            # Calculate position averages
            position_category = get_position_category(player['sub_position'])
            position_players = player_info[player_info['position'] == position_category]['player_id'].tolist()
            position_stats = player_stats[player_stats['player_id'].isin(position_players)]
            
            # Calculate averages
            avg_goals = position_stats['goals_scored'].mean()
            avg_assists = position_stats['assists'].mean()
            avg_xg = position_stats['expected_goals'].mean()
            avg_xa = position_stats['expected_assists'].mean()
            avg_tackles = position_stats['tackles'].mean()
            avg_interceptions = position_stats['clearances_blocks_interceptions'].mean()
            avg_threat = position_stats['threat'].mean()
            avg_creativity = position_stats['creativity'].mean()
            
            # Player averages
            p_avg_goals = stats['goals_scored'].mean()
            p_avg_assists = stats['assists'].mean()
            p_avg_xg = stats['expected_goals'].mean()
            p_avg_xa = stats['expected_assists'].mean()
            p_avg_tackles = stats['tackles'].mean()
            p_avg_interceptions = stats['clearances_blocks_interceptions'].mean()
            p_avg_threat = stats['threat'].mean()
            p_avg_creativity = stats['creativity'].mean()
            
            # Create radar chart
            categories = ['Scoring', 'Assisting', 'xG', 'xA', 'Tackles', 'Interceptions', 'Threat', 'Creativity']
            
            fig = go.Figure()
            
            # Player data
            fig.add_trace(go.Scatterpolar(
                r=[p_avg_goals, p_avg_assists, p_avg_xg, p_avg_xa, 
                   p_avg_tackles, p_avg_interceptions, p_avg_threat, p_avg_creativity],
                theta=categories,
                fill='toself',
                name=player['web_name'] or player['name']
            ))
            
            # Position average
            fig.add_trace(go.Scatterpolar(
                r=[avg_goals, avg_assists, avg_xg, avg_xa,
                   avg_tackles, avg_interceptions, avg_threat, avg_creativity],
                theta=categories,
                fill='toself',
                name=f'{position_category} Avg'
            ))
            
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True)),
                showlegend=True,
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            st.markdown("#### Performance Across Gameweeks")
            
            metric_choice = st.selectbox(
                "Select Metric",
                ['Composite Rating', 'Goals', 'Assists', 'Expected Goals', 'Expected Assists', 
                 'Tackles', 'Interceptions', 'ICT Index']
            )
            
            metric_mapping = {
                'Composite Rating': 'composite_rating',
                'Goals': 'goals_scored',
                'Assists': 'assists',
                'Expected Goals': 'expected_goals',
                'Expected Assists': 'expected_assists',
                'Tackles': 'tackles',
                'Interceptions': 'clearances_blocks_interceptions',
                'ICT Index': 'ict_index'
            }
            
            selected_col = metric_mapping[metric_choice]
            
            fig = px.line(stats.sort_values('gw'), x='gw', y=selected_col, 
                         title=f"{metric_choice} by Gameweek", markers=True)
            st.plotly_chart(fig, use_container_width=True)
        
        with tab3:
            st.markdown("#### Match Records")
            
            display_cols = ['gw', 'minutes', 'goals_scored', 'assists', 'expected_goals', 
                           'expected_assists', 'tackles', 'clearances_blocks_interceptions']
            
            stats_display = stats[['gw', 'minutes', 'goals_scored', 'assists', 'expected_goals', 
                                   'expected_assists', 'tackles', 'clearances_blocks_interceptions']].copy()
            stats_display['composite_rating'] = stats.apply(calculate_composite_rating, axis=1)
            
            stats_display = stats_display.rename(columns={
                'gw': 'Gameweek',
                'minutes': 'Minutes',
                'goals_scored': 'Goals',
                'assists': 'Assists',
                'expected_goals': 'xG',
                'expected_assists': 'xA',
                'tackles': 'Tackles',
                'clearances_blocks_interceptions': 'Interceptions'
            })
            
            st.dataframe(stats_display, use_container_width=True)
    
    # Back button
    if st.button("← Back"):
        st.session_state.page = st.session_state.previous_page
        st.rerun()

# Player Explorer
def render_player_explorer():
    player_stats, player_info = load_data()
    
    st.title("🔍 Player Explorer")
    
    # Filter bar
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        clubs = sorted(player_info['club_name'].unique())
        selected_clubs = st.multiselect("Club", clubs, key="explorer_club")
    
    with col2:
        positions = ['Forward', 'Midfielder', 'Defender', 'Goalkeeper']
        selected_positions = st.multiselect("Position", positions, key="explorer_position")
    
    with col3:
        ages = player_info['date_of_birth'].apply(calculate_age).dropna()
        min_age, max_age = int(ages.min()), int(ages.max())
        age_range = st.slider("Age Range", min_age, max_age, (min_age, max_age), key="explorer_age")
    
    with col4:
        values = player_info['market_value_in_eur']
        min_val, max_val = int(values.min()), int(values.max())
        value_range = st.slider("Market Value (€)", min_val, max_val, (min_val, max_val), key="explorer_value")
    
    # Apply filters
    filtered_info = player_info.copy()
    
    if selected_clubs:
        filtered_info = filtered_info[filtered_info['club_name'].isin(selected_clubs)]
    
    if selected_positions:
        filtered_info = filtered_info[filtered_info['position'].isin(selected_positions)]
    
    # Age filter
    filtered_info['age'] = filtered_info['date_of_birth'].apply(calculate_age)
    filtered_info = filtered_info[
        (filtered_info['age'] >= age_range[0]) & 
        (filtered_info['age'] <= age_range[1])
    ]
    
    # Market value filter
    filtered_info = filtered_info[
        (filtered_info['market_value_in_eur'] >= value_range[0]) & 
        (filtered_info['market_value_in_eur'] <= value_range[1])
    ]
    
    # Merge with stats and calculate overall rating
    player_ids = filtered_info['player_id'].tolist()
    player_season_stats = player_stats[player_stats['player_id'].isin(player_ids)].groupby('player_id').agg({
        'goals_scored': 'sum',
        'assists': 'sum',
        'expected_goals': 'sum',
        'expected_assists': 'sum',
        'tackles': 'sum',
        'clearances_blocks_interceptions': 'sum',
        'ict_index': 'mean',
        'minutes': 'sum',
        'yellow_cards': 'sum',
        'red_cards': 'sum',
        'clean_sheets': 'sum'
    }).reset_index()
    
    player_season_stats['composite_rating'] = player_season_stats.apply(calculate_composite_rating, axis=1)
    
    # Merge
    merged = filtered_info.merge(player_season_stats, on='player_id', how='left')
    merged['composite_rating'] = merged['composite_rating'].fillna(0)
    
    # Display table
    display_df = merged[['player_id', 'web_name', 'name', 'club_name', 'age', 
                         'market_value_in_eur', 'composite_rating', 'position']].copy()
    display_df['Player'] = display_df.apply(
        lambda x: x['web_name'] if pd.notna(x['web_name']) else x['name'], axis=1
    )
    display_df['Market Value'] = display_df['market_value_in_eur'].apply(format_market_value)
    display_df['Overall Rating'] = display_df['composite_rating'].round(1)
    
    display_df = display_df[['Player', 'club_name', 'age', 'Market Value', 'Overall Rating']]
    display_df = display_df.rename(columns={'club_name': 'Club', 'age': 'Age'})
    
    st.markdown("### Players")
    
    # Make player names clickable
    for idx, row in display_df.iterrows():
        player_id = merged[merged['web_name'].fillna(merged['name']) == row['Player']]['player_id'].values[0]
        cols = st.columns(5)
        cols[0].markdown(f"[**{row['Player']}**](#)", key=f"player_{player_id}")
        if cols[0].button("View", key=f"btn_{player_id}"):
            st.session_state.selected_player_id = player_id
            st.session_state.previous_page = 'Player Explorer'
            st.session_state.page = 'Player Dashboard'
            st.rerun()
        cols[1].write(row['Club'])
        cols[2].write(row['Age'])
        cols[3].write(row['Market Value'])
        cols[4].write(row['Overall Rating'])
        st.divider()
    
    # Quick Analysis section
    st.markdown("---")
    st.markdown("### Quick Analysis")
    
    analysis_option = st.segmented_control(
        "Analysis Type",
        ["Attacking Output", "Defensive Contribution", "Form & Consistency"]
    )
    
    if analysis_option:
        position_filter = st.radio(
            "Position",
            ["Goalkeepers", "Defenders", "Midfielders", "Forwards"],
            horizontal=True
        )
        
        analysis_types = {
            "Attacking Output": ["Top Scorers", "Top Assisters", "Top G/A", "Best xG Performance", "Top Young Attackers (U23)"],
            "Defensive Contribution": ["Top Tacklers per 90", "Top Interceptors per 90", "Most Recoveries per 90", "Best Defensive Duo", "Top Young Defenders (U23)"],
            "Form & Consistency": ["Highest Composite Rating", "Most In-form Players", "Most Minutes Played", "Best Discipline", "Top Young Consistent Performers (U23)"]
        }
        
        selected_analysis = st.selectbox("Analysis", analysis_types.get(analysis_option, []))
        
        # Generate results based on selection
        st.markdown(f"#### {selected_analysis}")
        
        # Example: Top Scorers
        if selected_analysis == "Top Scorers":
            top_scorers = merged.nlargest(10, 'goals_scored')[['name', 'age', 'position', 'club_name', 'goals_scored', 'minutes']]
            st.dataframe(top_scorers, use_container_width=True)
            
            fig = px.bar(top_scorers, x='name', y='goals_scored', title="Top 10 Scorers")
            st.plotly_chart(fig, use_container_width=True)

# My Watchlist
def render_watchlist():
    st.title("⭐ My Watchlist")
    
    watchlist = load_watchlist()
    player_stats, player_info = load_data()
    
    # Add new player section
    st.markdown("### Add Player to Watchlist")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        player_options = player_info.apply(lambda x: f"{x['web_name'] if pd.notna(x['web_name']) else x['name']} ({x['club_name']})", axis=1)
        selected_player = st.selectbox("Select Player", player_options.tolist(), key="add_watchlist_player")
    
    with col2:
        notes = st.text_input("Notes", key="add_watchlist_notes")
    
    with col3:
        tags = st.text_input("Tags (comma-separated)", key="add_watchlist_tags")
    
    with col4:
        if st.button("Add", key="add_watchlist_btn"):
            player_row = player_info[player_info.apply(lambda x: f"{x['web_name'] if pd.notna(x['web_name']) else x['name']} ({x['club_name']})", axis=1) == selected_player]
            if not player_row.empty:
                player_id = str(player_row.iloc[0]['player_id'])
                if player_id not in watchlist:
                    watchlist[player_id] = {
                        'player_id': int(player_id),
                        'notes': notes,
                        'tags': [t.strip() for t in tags.split(',') if t.strip()],
                        'date_added': datetime.now().strftime('%Y-%m-%d')
                    }
                    save_watchlist(watchlist)
                    st.success("Player added to watchlist!")
                    st.rerun()
                else:
                    st.warning("Player already in watchlist")
    
    st.markdown("---")
    
    # Filter bar
    col1, col2, col3 = st.columns(3)
    
    all_tags = set()
    for entry in watchlist.values():
        all_tags.update(entry.get('tags', []))
    
    with col1:
        selected_tags = st.multiselect("Filter by Tags", list(all_tags), key="filter_tags")
    
    with col2:
        positions = ['Forward', 'Midfielder', 'Defender', 'Goalkeeper']
        selected_pos = st.multiselect("Position", positions, key="filter_position")
    
    with col3:
        clubs = sorted(player_info['club_name'].unique())
        selected_clubs = st.multiselect("Club", clubs, key="filter_club")
    
    # Display watchlist
    if watchlist:
        st.markdown("### Saved Players")
        
        for player_id_str, entry in watchlist.items():
            player = player_info[player_info['player_id'] == int(player_id_str)]
            if player.empty:
                continue
            
            player = player.iloc[0]
            
            # Apply filters
            if selected_tags and not any(tag in entry.get('tags', []) for tag in selected_tags):
                continue
            if selected_pos and player['position'] not in selected_pos:
                continue
            if selected_clubs and player['club_name'] not in selected_clubs:
                continue
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"#### {player['web_name'] if pd.notna(player['web_name']) else player['name']}")
                st.write(f"**Club:** {player['club_name']} | **Position:** {player['position']}")
                
                # Display tags
                if entry.get('tags'):
                    tags_html = " ".join([f"`{tag}`" for tag in entry['tags']])
                    st.markdown(f"Tags: {tags_html}")
                
                # Display notes
                if entry.get('notes'):
                    st.write(f"**Notes:** {entry['notes'][:100]}{'...' if len(entry['notes']) > 100 else ''}")
                
                st.write(f"Added: {entry.get('date_added', 'Unknown')}")
            
            with col2:
                # Edit button
                if st.button("Edit", key=f"edit_{player_id_str}"):
                    with st.expander("Edit Entry", expanded=True):
                        with st.form(f"edit_form_{player_id_str}"):
                            new_notes = st.text_area("Notes", value=entry.get('notes', ''), key=f"edit_notes_{player_id_str}")
                            new_tags = st.text_input("Tags", value=",".join(entry.get('tags', [])), key=f"edit_tags_{player_id_str}")
                            if st.form_submit_button("Update"):
                                watchlist[player_id_str]['notes'] = new_notes
                                watchlist[player_id_str]['tags'] = [t.strip() for t in new_tags.split(',') if t.strip()]
                                save_watchlist(watchlist)
                                st.success("Updated!")
                                st.rerun()
                
                # Delete button
                if st.button("Delete", key=f"delete_{player_id_str}"):
                    del watchlist[player_id_str]
                    save_watchlist(watchlist)
                    st.success("Deleted!")
                    st.rerun()
                
                # View player button
                if st.button("View Profile", key=f"view_{player_id_str}"):
                    st.session_state.selected_player_id = int(player_id_str)
                    st.session_state.previous_page = 'My Watchlist'
                    st.session_state.page = 'Player Dashboard'
                    st.rerun()
            
            st.divider()
        
        # Clear all button
        if st.button("🗑️ Clear All Watchlist", type="primary"):
            if st.confirm("Are you sure you want to clear your entire watchlist?"):
                watchlist = {}
                save_watchlist(watchlist)
                st.success("Watchlist cleared!")
                st.rerun()
    else:
        st.info("Your watchlist is empty. Add players using the form above.")

# Advanced Scouting
def render_advanced_scouting():
    st.title("🎯 Advanced Scouting")
    
    player_stats, player_info = load_data()
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### Search Criteria")
        
        # League (placeholder - only one league in our data)
        leagues = player_info['club_name'].unique()
        if len(leagues) == 1:
            st.text(f"League: {leagues[0]}")
        else:
            selected_league = st.selectbox("League", leagues)
        
        # Position
        position = st.selectbox("Position", ['All', 'Forward', 'Midfielder', 'Defender', 'Goalkeeper'])
        
        # Max market value
        max_value = st.slider("Max Market Value (€)", 0, int(player_info['market_value_in_eur'].max()), 
                             int(player_info['market_value_in_eur'].max()))
        
        # Max results
        max_results = st.number_input("Max Results", min_value=1, max_value=50, value=10)
        
        # Skills
        st.markdown("### Skills (Select up to 5)")
        
        skills = [
            "Goal Scoring", "Goal Efficiency", "Shooting", "Passing Influence",
            "Goal Creation", "Possession Influence", "Progression", "Dribbling",
            "Aerial Influence", "Defensive Influence", "Discipline & Consistency"
        ]
        
        selected_skills = st.multiselect("Select Skills", skills, max_selections=5)
        
        skill_weights = {}
        for skill in selected_skills:
            skill_weights[skill] = st.slider(skill, 0, 100, 50)
        
        search_btn = st.button("Search", type="primary", use_container_width=True)
    
    with col2:
        if search_btn or 'scout_results' in st.session_state:
            # Filter players
            filtered = player_info.copy()
            
            if position != 'All':
                filtered = filtered[filtered['position'] == position]
            
            filtered = filtered[filtered['market_value_in_eur'] <= max_value]
            
            # Calculate compatibility scores (simplified)
            filtered = filtered.merge(
                player_stats.groupby('player_id').agg({
                    'goals_scored': 'sum',
                    'assists': 'sum',
                    'expected_goals': 'sum',
                    'tackles': 'sum',
                    'clearances_blocks_interceptions': 'sum',
                    'ict_index': 'mean'
                }).reset_index(),
                on='player_id'
            )
            
            # Simple scoring based on stats
            filtered['compatibility_score'] = (
                filtered['goals_scored'] * 10 +
                filtered['assists'] * 8 +
                filtered['expected_goals'] * 5 +
                filtered['tackles'] * 3 +
                filtered['ict_index'] * 2
            )
            
            filtered = filtered.nlargest(min(max_results, len(filtered)), 'compatibility_score')
            
            st.markdown("### Results")
            
            if not filtered.empty:
                # Show top player radar chart
                top_player = filtered.iloc[0]
                st.markdown(f"#### Top Match: {top_player['web_name'] or top_player['name']}")
                
                # Get player stats for radar
                p_stats = player_stats[player_stats['player_id'] == top_player['player_id']]
                
                if not p_stats.empty:
                    categories = ['Goals', 'Assists', 'xG', 'xA', 'Tackles', 'Interceptions', 'ICT', 'Threat']
                    
                    fig = go.Figure()
                    fig.add_trace(go.Scatterpolar(
                        r=[
                            p_stats['goals_scored'].mean(),
                            p_stats['assists'].mean(),
                            p_stats['expected_goals'].mean(),
                            p_stats['expected_assists'].mean(),
                            p_stats['tackles'].mean(),
                            p_stats['clearances_blocks_interceptions'].mean(),
                            p_stats['ict_index'].mean(),
                            p_stats['threat'].mean()
                        ],
                        theta=categories,
                        fill='toself',
                        name=top_player['web_name'] or top_player['name']
                    ))
                    fig.update_layout(polar=dict(radialaxis=dict(visible=True)), height=400)
                    st.plotly_chart(fig, use_container_width=True)
                
                # Results table
                for idx, row in filtered.iterrows():
                    cols = st.columns(6)
                    cols[0].write(f"#{idx + 1}")
                    
                    player_name = row['web_name'] if pd.notna(row['web_name']) else row['name']
                    cols[1].markdown(f"[**{player_name}**](#)")
                    
                    if cols[1].button("View", key=f"scout_view_{row['player_id']}"):
                        st.session_state.selected_player_id = row['player_id']
                        st.session_state.previous_page = 'Advanced Scouting'
                        st.session_state.page = 'Player Dashboard'
                        st.rerun()
                    
                    cols[2].write(row['club_name'])
                    cols[3].write(row['position'])
                    cols[4].write(calculate_age(row['date_of_birth']))
                    cols[5].write(f"{format_market_value(row['market_value_in_eur'])}")
                    
                    if st.button("Find Similar", key=f"similar_{row['player_id']}"):
                        st.info(f"Finding similar players to {player_name}...")
                    
                    st.divider()

# Player Valuation
def render_player_valuation():
    st.title("💰 Player Valuation")
    
    player_stats, player_info = load_data()
    
    # Player selection
    player_options = player_info.apply(lambda x: f"{x['web_name'] if pd.notna(x['web_name']) else x['name']} ({x['club_name']})", axis=1)
    selected_player_name = st.selectbox("Select Player", player_options.tolist())
    
    if selected_player_name:
        player_row = player_info[player_info.apply(lambda x: f"{x['web_name'] if pd.notna(x['web_name']) else x['name']} ({x['club_name']})", axis=1) == selected_player_name]
        
        if not player_row.empty:
            player = player_row.iloc[0]
            player_id = player['player_id']
            
            # Get player stats
            p_stats = player_stats[player_stats['player_id'] == player_id]
            
            if not p_stats.empty:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### Player Stats vs Position Average")
                    
                    # Calculate position average
                    position = player['position']
                    pos_players = player_info[player_info['position'] == position]['player_id']
                    pos_stats = player_stats[player_stats['player_id'].isin(pos_players)]
                    
                    comparison_data = {
                        'Metric': ['Goals', 'Assists', 'xG', 'xA', 'Tackles', 'Interceptions'],
                        'Player': [
                            p_stats['goals_scored'].sum(),
                            p_stats['assists'].sum(),
                            p_stats['expected_goals'].sum(),
                            p_stats['expected_assists'].sum(),
                            p_stats['tackles'].sum(),
                            p_stats['clearances_blocks_interceptions'].sum()
                        ],
                        'Position Avg': [
                            pos_stats['goals_scored'].mean() * len(p_stats),
                            pos_stats['assists'].mean() * len(p_stats),
                            pos_stats['expected_goals'].mean() * len(p_stats),
                            pos_stats['expected_assists'].mean() * len(p_stats),
                            pos_stats['tackles'].mean() * len(p_stats),
                            pos_stats['clearances_blocks_interceptions'].mean() * len(p_stats)
                        ]
                    }
                    
                    comp_df = pd.DataFrame(comparison_data)
                    st.dataframe(comp_df, use_container_width=True)
                
                with col2:
                    st.markdown("### Valuation Analysis")
                    
                    actual_value = player['market_value_in_eur']
                    
                    # Simple valuation model
                    predicted_value = (
                        p_stats['goals_scored'].sum() * 5_000_000 +
                        p_stats['assists'].sum() * 3_000_000 +
                        p_stats['expected_goals'].sum() * 2_000_000 +
                        p_stats['ict_index'].mean() * 500_000
                    )
                    predicted_value = max(predicted_value, 1_000_000)  # Minimum 1M
                    
                    diff_percent = ((actual_value - predicted_value) / predicted_value) * 100
                    
                    st.metric("Actual Market Value", format_market_value(actual_value))
                    st.metric("Predicted Value", format_market_value(predicted_value))
                    st.metric("Difference", f"{diff_percent:+.1f}%")
                    
                    if actual_value > predicted_value:
                        st.error("⚠️ Overperform (Actual higher than predicted)")
                    else:
                        st.success("✅ Underperform (Potential bargain!)")
                    
                    # Potential rating
                    age = calculate_age(player['date_of_birth'])
                    potential = 5
                    if age and age > 28:
                        potential = 3
                    elif age and age > 25:
                        potential = 4
                    
                    st.markdown(f"**Potential Rating:** {'⭐' * potential}")
    
    # Cheap Beasts section
    st.markdown("---")
    st.markdown("### Cheap Beasts")
    
    cb_col1, cb_col2 = st.columns(2)
    
    with cb_col1:
        cb_position = st.selectbox("Position", ['All', 'Forward', 'Midfielder', 'Defender', 'Goalkeeper'], key="cb_pos")
        cb_max_value = st.number_input("Max Market Value (€)", value=50_000_000, key="cb_max_val")
    
    with cb_col2:
        mode = st.radio("Mode", ["Value Rating", "Cheaper Similar", "Better at Same Price"], horizontal=True)
    
    # Calculate value-for-money
    player_stats_agg = player_stats.groupby('player_id').agg({
        'goals_scored': 'sum',
        'assists': 'sum',
        'ict_index': 'mean'
    }).reset_index()
    
    merged = player_info.merge(player_stats_agg, on='player_id')
    merged['composite_rating'] = merged.apply(
        lambda x: x['goals_scored'] * 10 + x['assists'] * 8 + x['ict_index'] * 2, axis=1
    )
    merged['value_rating'] = merged['composite_rating'] / merged['market_value_in_eur'] * 1_000_000
    
    if cb_position != 'All':
        merged = merged[merged['position'] == cb_position]
    
    merged = merged[merged['market_value_in_eur'] <= cb_max_value]
    merged = merged.nlargest(20, 'value_rating')
    
    st.markdown("#### Top 20 Value Picks")
    
    for idx, row in merged.iterrows():
        cols = st.columns(6)
        player_name = row['web_name'] if pd.notna(row['web_name']) else row['name']
        cols[0].markdown(f"**{player_name}**")
        cols[1].write(row['club_name'])
        cols[2].write(row['position'])
        cols[3].write(format_market_value(row['market_value_in_eur']))
        cols[4].write(f"{row['value_rating']:.2f}")
        cols[5].write(f"G+A: {row['goals_scored'] + row['assists']}")
        st.divider()

# Main app logic
def main():
    page = st.session_state.page
    
    if page == 'Home':
        render_home()
    elif page == 'Player Explorer':
        render_player_explorer()
    elif page == 'Player Dashboard':
        if st.session_state.selected_player_id:
            render_player_dashboard(st.session_state.selected_player_id)
        else:
            st.warning("No player selected")
            render_home()
    elif page == 'My Watchlist':
        render_watchlist()
    elif page == 'Advanced Scouting':
        render_advanced_scouting()
    elif page == 'Player Valuation':
        render_player_valuation()

if __name__ == "__main__":
    main()
