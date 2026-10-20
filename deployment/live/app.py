"""Streamlit Cloud entrypoint; requirements.txt alongside this file is intentional."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from assistant.live_app import render
render()
