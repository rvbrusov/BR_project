import tempfile
from pathlib import Path
import tkinter as tk
import aviatest_v4 as v
v.base._enable_windows_dpi_awareness()
with tempfile.TemporaryDirectory() as folder:
 v.base._runtime_app_dir=lambda:Path(folder)
 root=tk.Tk(); app=v.base.StartPageApp(root); app.build_researcher_ui(); root.update()
 root.attributes('-fullscreen', False); root.state('normal'); root.minsize(640,480)
 for w,h in [(1600,900),(1366,768),(1024,600)]:
  root.geometry(f'{w}x{h}');root.update();app.apply_researcher_layout();root.update()
  tabs=app.research_tabs;bar=app._fixed416_research_tab_bar
  print(root.winfo_width(),root.winfo_height(),'bar',bar.winfo_height(),'req',bar.winfo_reqheight(),'tabs',tabs.winfo_height())
  for item,tab in zip(app._fixed416_research_tab_items,tabs.tabs()):
   label=item['label']; print(label.cget('text'),label.winfo_height(),label.winfo_reqheight())
   assert label.winfo_rooty()>=bar.winfo_rooty()
   assert label.winfo_rooty()+label.winfo_height()<=bar.winfo_rooty()+bar.winfo_height()
   label.event_generate('<Button-1>');root.update();assert tabs.select()==tab
 root.destroy()
print('PASS settings tabs fit and select all pages')

