# Main.py
import multiprocessing
import sys
import tkinter as tk


def main():
    from ui.app import App
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    # ← ЭТА СТРОКА ДОЛЖНА БЫТЬ ПЕРВОЙ. Без неё multiprocessing в .exe
    #   будет запускать GUI вместо воркера.
    multiprocessing.freeze_support()
    main()