from __future__ import annotations
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from ui import PhotoIngestUI

def main() -> None:
#    root = tk.Tk()
    root = ttk.Window(themename="rsimko")
    app = PhotoIngestUI(root)
    app.run()

if __name__ == "__main__":
    main()
