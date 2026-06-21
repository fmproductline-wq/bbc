"""
Best Brand Corp — Trading & Prediction Bot Desktop App

Launch:
    python desktop_app.py

Requirements:
    pip install -r requirements.txt
    pip install customtkinter matplotlib Pillow
"""
import sys
import os

# Ensure project root is on path so all imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.app import run_app

if __name__ == "__main__":
    run_app()
