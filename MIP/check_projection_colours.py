from pathlib import Path
import tkinter as tk
from PIL import ImageGrab
from surface_view import SurfaceCanvas
from demo_accounts import USER7_VALUES
import aviatest_v4 as v
v.base._enable_windows_dpi_awareness()
values={code:list(row) for code,row in zip(v.ORDER,USER7_VALUES)};values['B']=[n/.8 for n in values['B']]
root=tk.Tk();root.overrideredirect(True);root.geometry('1536x864+0+0')
report=[]
for order in (v.ORDER,('A','C','D','B')):
 chart=SurfaceCanvas(root,values,order=order);chart.pack(fill='both',expand=True);root.update();chart.draw();root.update()
 for yaw in (chart.INITIAL_YAW,1.6,2.6):
  chart.yaw=yaw;chart.draw();root.update()
  for ix in range(chart.NX):
   for iy in range(chart.NY):
    surface=chart.find_withtag(f'surface_cell_{ix}_{iy}')[0];floor=chart.find_withtag(f'floor_cell_{ix}_{iy}')[0]
    q=[chart.mesh[ix][iy],chart.mesh[ix+1][iy],chart.mesh[ix+1][iy+1],chart.mesh[ix][iy+1]]
    expected=chart.colour(sum(p[2] for p in q)/4)
    assert chart.itemcget(surface,'fill')==chart.itemcget(floor,'fill')==expected
  report.append({'methods':len(order),'yaw':yaw,'matching_cell_pairs':600})
 chart.yaw=chart.INITIAL_YAW;chart.draw();root.update()
 bitmap=ImageGrab.grab(window=root.winfo_id()).convert('RGB');pairs=0;colours=set()
 assert bitmap.size==(1536,864)
 for ix in range(chart.NX):
  for iy in range(chart.NY):
   q=[chart.mesh[ix][iy],chart.mesh[ix+1][iy],chart.mesh[ix+1][iy+1],chart.mesh[ix][iy+1]]
   x,y,z=(sum(p[n] for p in q)/4 for n in range(3));fill=chart.colour(z)
   expected=tuple(int(fill[k:k+2],16) for k in (1,3,5))
   a=chart.project(x,y,z);b=chart.project(x,y,0)
   if all(0<=p[0]<1536 and 0<=p[1]<864 for p in (a,b)):
    if bitmap.getpixel((round(a[0]),round(a[1])))==bitmap.getpixel((round(b[0]),round(b[1])))==expected:pairs+=1;colours.add(expected)
 assert pairs>25 and len(colours)>5,(pairs,len(colours))
 report.append({'methods':len(order),'yaw':chart.INITIAL_YAW,'visible_rgb_pairs':pairs,'distinct_visible_rgb_colours':len(colours)})
 chart.destroy()
for job in root.tk.call('after','info'):root.after_cancel(job)
root.destroy()
import json
Path('qa/projection-colours.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
