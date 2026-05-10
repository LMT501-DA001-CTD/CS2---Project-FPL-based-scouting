# Football Scout Pro

A professional football player analytics and scouting tool built with Streamlit.

## Features

- **Player Explorer**: Browse and filter players by club, position, age, and market value
- **Player Dashboard**: Detailed player statistics, performance charts, and match records
- **My Watchlist**: Save and track players with personal notes and tags
- **Advanced Scouting**: Find players matching specific skill profiles
- **Player Valuation**: Analyze market values and find undervalued talents

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
streamlit run app.py
```

3. Open your browser to `http://localhost:8501`

## Data Files

The application uses two CSV datasets:

- `data/playerstats.csv`: Per-match performance statistics for each player
- `data/players_info.csv`: Biographical and market value information for each player

## Usage

### Navigation
- Use the sidebar menu to navigate between pages
- Click on player names to view detailed dashboards
- Filters are applied instantly as you adjust them

### Watchlist
- Add players to your personal watchlist with notes and tags
- Watchlist data persists across sessions in `watchlist.json`
- Filter watchlist by tags, position, or club

### Quick Analysis
In Player Explorer, use the Quick Analysis section to discover:
- Top scorers, assisters, and G/A leaders
- Best defensive performers
- Most consistent players by composite rating

## Session Behavior

- Filter selections and active tabs reset when the application is closed
- Watchlist data persists across sessions

## License

MIT License
