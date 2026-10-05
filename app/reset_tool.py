import os,sys,tkinter as tk
from tkinter import messagebox
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from wpos_app import ResetTool,db_path
root=tk.Tk();root.withdraw()
if not os.path.exists(db_path()):
 messagebox.showerror('Database tidak ditemukan','Letakkan wpos.db di folder EXE.');root.destroy();raise SystemExit(1)
tool=ResetTool(root);tool.protocol('WM_DELETE_WINDOW',root.destroy);root.mainloop()
