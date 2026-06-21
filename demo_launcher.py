"""
Demo launcher — bypasses T&C and vault unlock so we can screenshot the app.
Sets a fake private key in env and jumps straight to MainApp.
"""
import os
import sys

sys.path.insert(0, "/home/user/bbc")
os.environ["WALLET_PRIVATE_KEY"] = "0x" + "a" * 64
os.environ["WALLET_ADDRESS"]     = "0x35FC6d6d715Fe6B699783030BF3AdF2d75c6645a"
os.environ["TELEGRAM_BOT_TOKEN"] = "demo"

import customtkinter as ctk
from ui.app import MainApp

app = MainApp()
app.mainloop()
