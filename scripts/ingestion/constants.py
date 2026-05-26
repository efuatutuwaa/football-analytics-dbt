"""Shared constants for ingestion scripts.

Centralising LEAGUE_IDS and SEASONS here means a scope change (adding
a new competition, extending the seasons range) only requires editing
one file instead of every fetch_*.py script.
"""
from datetime import datetime


LEAGUE_IDS = [
    1,    # FIFA World Cup
    2,    # UEFA Champions League
    4,    # UEFA European Championship
    15,   # FIFA Club World Cup
    39,   # Premier League
    45,   # FA Cup
    48,   # Carabao Cup (EFL Cup)
    61,   # Ligue 1
    66,   # Coupe de France
    78,   # Bundesliga
    81,   # DFB-Pokal
    135,  # Serie A
    137,  # Coppa Italia
    140,  # La Liga
    143,  # Copa del Rey
]

SEASONS = list(range(2020, datetime.now().year + 1))
