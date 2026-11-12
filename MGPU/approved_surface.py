"""Native, offline renderer of the approved November 11 interactive surface.

Only the opaque result surface occludes lines. The normative plane is a
translucent reference, and the lower plane has neither colours nor values.
"""
import math
from collections import Counter
import numpy as np
from PIL import Image, ImageDraw, ImageTk
from tkinter import font as tkfont
import aviatest_v4 as v
from surface_geometry import surface_mesh
from surface_labels import box, intersects

STOPS=np.array([[.4,150,96,44],[.5583333333,201,154,76],
 [.7166666667,246,228,154],[.875,237,245,179],
 [1.0333333333,178,216,121],[1.1916666667,101,183,65],[1.35,35,134,46]])
LUT=np.stack([np.interp(np.linspace(.4,1.35,4096),STOPS[:,0],STOPS[:,k])
              for k in (1,2,3)],axis=1).round().astype(np.uint8)


class SurfaceCanvas(v.IntegralSurface3D):
    INITIAL_YAW=math.pi/4
    INITIAL_PITCH=math.asin(.26)
    NAVY='#101820'
    GRID='#19536b'
    COLOUR_MIN=0.
    COLOUR_MAX=1.6
    LEGEND_TICKS=tuple(n/5 for n in range(9))

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.yaw,self.pitch,self.zoom=self.INITIAL_YAW,self.INITIAL_PITCH,1.
        self.plane=True
        self.step=.2
        maximum=max((n for row in self.values.values() for n in row if n is not None),default=0.)
        self.zmax=max(1.8,math.ceil((maximum-1e-10)/.2)*.2)
        # Include every measured x coordinate exactly in four- and six-test modes.
        self.NX=(len(self.order)-1)*6
        self.NY=20
        self.mesh=surface_mesh(self.values,self.order,self.NX,self.NY)
        self._photo=None
        self._fit=None
        self.stats={}
        self.axis_poses={}
        self._text_metrics={}

    @staticmethod
    def colour(value):
        rgb=LUT[max(0,min(4095,round((value-.4)/.95*4095)))]
        return '#%02x%02x%02x'%tuple(rgb)

    def reset_view(self):
        self.yaw,self.pitch,self.zoom=self.INITIAL_YAW,self.INITIAL_PITCH,1.
        self.redraw()

    def drag(self,event):
        if self._drag is not None:
            x,y=self._drag
            self.yaw=(self.yaw+(event.x-x)*.009+math.pi)%(2*math.pi)-math.pi
            self.pitch=max(.105,min(1.134,self.pitch+(event.y-y)*.007))
            self._drag=(event.x,event.y)
            self.redraw()

    def raw_project(self,x,y,z):
        u=(2-y)/2-.5
        vv=.5-x/max(1,len(self.order)-1)
        zz=(z/self.zmax-.5)*.72
        c,s,cp,sp=math.cos(self.yaw),math.sin(self.yaw),math.cos(self.pitch),math.sin(self.pitch)
        horizontal=u*c-vv*s
        depth=-u*s-vv*c
        return horizontal,zz*cp-depth*sp,depth*cp+zz*sp

    def project(self,x,y,z):
        p=self.raw_project(x,y,z)
        factor,cx,cy,px,py=self._fit
        return px+(p[0]-cx)*factor*self.zoom,py-(p[1]-cy)*factor*self.zoom,p[2]

    def display_scale(self):
        return min(self.winfo_width()/1536,self.winfo_height()/864)

    def number_pixels(self):
        return max(11,round(26*self.display_scale()))

    def legend_layout(self):
        w,h=self.winfo_width(),self.winfo_height()
        return (40 if w<650 else w*.07,h*.16,max(14,w*.026),h*.45)

    def text_box(self,x,y,text,size,angle=0,anchor='center'):
        key=(text,size)
        if key not in self._text_metrics:
            f=tkfont.Font(root=self,font=('Arial',-size));lines=text.split('\n')
            self._text_metrics[key]=(max(f.measure(t) for t in lines),size*1.2*len(lines))
        width,height=self._text_metrics[key]
        return box(x,y,width,height,angle,anchor)

    def pose(self,axis,anchor,offset,text):
        a,b=[self.project(*p) for p in axis]
        p=self.project(*anchor)
        dx,dy=b[0]-a[0],b[1]-a[1]
        length=max(1e-9,math.hypot(dx,dy))
        angle=math.atan2(dy,dx)
        if angle>math.pi/2:angle-=math.pi
        elif angle< -math.pi/2:angle+=math.pi
        nx,ny=-dy/length,dx/length
        centre=self.project((len(self.order)-1)/2,1,anchor[2])
        if nx*(p[0]-centre[0])+ny*(p[1]-centre[1])<0:nx,ny=-nx,-ny
        return dict(axis=axis,world_anchor=anchor,screen=(p[0]+nx*offset,p[1]+ny*offset),
                    normal=(nx,ny),angle=-math.degrees(angle),text=text,anchor_screen=p[:2],offset=offset)

    def place_captions(self):
        last=len(self.order)-1
        s=self.display_scale()
        poses={
          'tempo':self.pose(((0,2,0),(0,2,self.zmax)),(0,2,self.zmax/2),112*s,'ПРИВЕДЕННЫЙ ТЕМП\nДЕЯТЕЛЬНОСТИ'),
          'elements':self.pose(((last,2,0),(last,0,0)),(last,.76,0),85*s,'ЧИСЛО ЭЛЕМЕНТОВ ЗАДАНИЯ')}
        points=[self.project(x,y,z)[:2] for x in (0,last) for y in (0,2) for z in (0,self.zmax)]
        def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
        lower=[];upper=[]
        for seq,out in ((sorted(points),lower),(sorted(points,reverse=True),upper)):
            for p in seq:
                while len(out)>1 and cross(out[-2],out[-1],p)<=0:out.pop()
                out.append(p)
        hull=lower[:-1]+upper[:-1]
        x,y,w,h=self.legend_layout()
        legend=[(x-48,y-45),(x+w+32,y-45),(x+w+32,y+h+15),(x-48,y+h+15)]
        n=self.number_pixels()
        obstacles=[self.text_box(px,py,text,n,angle,anchor) for px,py,text,angle,anchor in self.method_placements()]
        for i in range(round(self.zmax/.2)+1):
            px,py,_=self.project(0,2,i*.2)
            obstacles.append(self.text_box(px-9,py-(9*s if i==0 else 0),f'{i*.2:.1f}',n,anchor='e'))
        for stage,word in enumerate(('min','med','max')):
            px,py,_=self.project(last,stage,0)
            obstacles.append(self.text_box(px+12*s,py+20*s,word,n,anchor='w'))
        success=True
        for pose in poses.values():
            placed=False
            distances=list(np.arange(pose['offset'],max(self.winfo_width(),self.winfo_height()),6*max(.5,s)))
            for distance in distances+[-d for d in distances]:
                nx,ny=pose['normal'];px,py=pose['anchor_screen']
                location=(px+nx*distance,py+ny*distance)
                bounds=self.text_box(*location,pose['text'],max(11,round(26*s)),pose['angle'])
                inside=all(5<=a<=self.winfo_width()-5 and 5<=b<=self.winfo_height()-5 for a,b in bounds)
                if inside and not intersects(bounds,hull) and not intersects(bounds,legend) and not any(intersects(bounds,q) for q in obstacles):
                    pose['screen']=location;pose['offset']=float(distance);placed=True;break
            if placed:obstacles.append(bounds)
            success=success and placed
        self.axis_poses=poses
        return success

    def fit_viewport(self):
        last=len(self.order)-1
        points=[self.raw_project(x,y,z) for x in (0,last) for y in (0,2) for z in (0,self.zmax)]
        left,right=min(p[0] for p in points),max(p[0] for p in points)
        low,high=min(p[1] for p in points),max(p[1] for p in points)
        w,h=self.winfo_width(),self.winfo_height()
        a,b=self.raw_project(0,2,0),self.raw_project(0,1,0)
        angle=abs(math.atan2(a[1]-b[1],a[0]-b[0]))
        scene_h=h*.73 if .65<angle<math.pi-.65 else h
        x0,x1=w*.36,w*.88;y0,y1=scene_h*.08,scene_h*.73
        factor=min((x1-x0)/(right-left),(y1-y0)/(high-low))
        for _ in range(12):
            self._fit=(factor,(left+right)/2,(low+high)/2,(x0+x1)/2,(y0+y1)/2)
            if self.place_captions():break
            factor*=.93

    def raster_surface(self):
        """Interpolate scalar height per pixel, with the same colour LUT as HTML."""
        w,h=self.winfo_width(),self.winfo_height()
        self.depth=np.full((h,w),-1e20,dtype=np.float32)
        pixels=np.zeros((h,w,4),dtype=np.uint8)
        projected=[[self.project(x,y,z) if z is not None else None for x,y,z in row] for row in self.mesh]
        def triangle(a,b,c,zz):
            if a is None or b is None or c is None:return
            det=(b[0]-a[0])*(c[1]-a[1])-(c[0]-a[0])*(b[1]-a[1])
            if abs(det)<1e-9:return
            x0=max(0,math.floor(min(a[0],b[0],c[0])))
            x1=min(w-1,math.ceil(max(a[0],b[0],c[0])))
            y0=max(0,math.floor(min(a[1],b[1],c[1])))
            y1=min(h-1,math.ceil(max(a[1],b[1],c[1])))
            if x1<x0 or y1<y0:return
            yy,xx=np.mgrid[y0:y1+1,x0:x1+1];xx=xx+.5;yy=yy+.5
            beta=((xx-a[0])*(c[1]-a[1])-(yy-a[1])*(c[0]-a[0]))/det
            gamma=((b[0]-a[0])*(yy-a[1])-(b[1]-a[1])*(xx-a[0]))/det
            dep=a[2]+beta*(b[2]-a[2])+gamma*(c[2]-a[2])
            target=self.depth[y0:y1+1,x0:x1+1]
            mask=(beta>=-1e-8)&(gamma>=-1e-8)&(beta+gamma<=1+1e-8)&(dep>=target)
            height=zz[0]+beta*(zz[1]-zz[0])+gamma*(zz[2]-zz[0])
            indexes=np.clip(np.rint((height-.4)/.95*4095),0,4095).astype(np.int32)
            target[mask]=dep[mask]
            patch=pixels[y0:y1+1,x0:x1+1]
            patch[mask,:3]=LUT[indexes[mask]];patch[mask,3]=255
        for x in range(self.NX):
            for y in range(self.NY):
                a,b,c,d=projected[x][y],projected[x+1][y],projected[x+1][y+1],projected[x][y+1]
                z=[self.mesh[i][j][2] for i,j in ((x,y),(x+1,y),(x+1,y+1),(x,y+1))]
                if any(vv is None for vv in z):continue
                triangle(a,b,c,z[:3]);triangle(a,c,d,[z[0],z[2],z[3]])
        return Image.fromarray(pixels)

    def hidden(self,p):
        x,y=round(p[0]),round(p[1])
        return 0<=x<self.depth.shape[1] and 0<=y<self.depth.shape[0] and self.depth[y,x]>p[2]+.006

    def depth_line(self,points,kind,tag):
        surface=kind=='surface';red=kind=='stem'
        colour='#df1218' if red else '#101820' if surface else self.GRID
        faint=colour if red else '#8c9195' if surface else '#94aeba'
        s=self.display_scale()
        visible=(2.7 if surface else 1.6 if red else 1.3)*max(.65,s)
        thin=(1.1 if surface else .8 if red else .65)*max(.75,s)
        run=[];previous=None
        def flush():
            if len(run)>1:self.create_line(*[c for p in run for c in p],fill=faint if previous else colour,
                width=thin if previous else visible,tags=(tag,'hidden_line' if previous else 'visible_line',kind+'_line'))
        for a,b in zip(points,points[1:]):
            if a[2] is None or b[2] is None:
                flush();run=[];previous=None;continue
            pa,pb=self.project(*a),self.project(*b)
            steps=max(1,math.ceil(math.hypot(pb[0]-pa[0],pb[1]-pa[1])/2))
            for j in range(steps):
                p0=self.project(*(a[k]+(b[k]-a[k])*j/steps for k in range(3)))
                p1=self.project(*(a[k]+(b[k]-a[k])*(j+1)/steps for k in range(3)))
                hidden=self.hidden(tuple((p0[k]+p1[k])/2 for k in range(3)))
                self.stats[kind+('Hidden' if hidden else 'Visible')]+=1
                if previous is None:previous=hidden;run=[p0[:2],p1[:2]]
                elif hidden==previous:run.append(p1[:2])
                else:flush();previous=hidden;run=[p0[:2],p1[:2]]
        flush()

    def draw_scene(self):
        w,h=self.winfo_width(),self.winfo_height();last=len(self.order)-1
        image=Image.new('RGBA',(w,h),'white');d=ImageDraw.Draw(image)
        def poly(points,fill,outline):
            p=[self.project(*q)[:2] for q in points];d.polygon(p,fill=fill);d.line(p+[p[0]],fill=outline,width=1)
        poly([(0,0,0),(last,0,0),(last,2,0),(0,2,0)],'#f9faf7','#a0a5a7')
        fx=0 if math.cos(self.yaw)>=0 else last;fy=0 if math.sin(self.yaw)>=0 else 2
        for side in ('x','y'):
            def p(t,z):return (fx,2*t,z) if side=='x' else (last*t,fy,z)
            poly([p(0,0),p(1,0),p(1,self.zmax),p(0,self.zmax)],'#f5f6f5','#a0a5a7')
            for i in range(1,round(self.zmax/.2)):
                d.line([self.project(*p(t,i*.2))[:2] for t in (0,1)],fill='#b6bdc0',width=1)
        if self.plane:
            overlay=Image.new('RGBA',(w,h));od=ImageDraw.Draw(overlay)
            od.polygon([self.project(*q)[:2] for q in ((0,0,1),(last,0,1),(last,2,1),(0,2,1))],fill=(35,143,181,28))
            image=Image.alpha_composite(image,overlay)
        image=Image.alpha_composite(image,self.raster_surface())
        self._photo=ImageTk.PhotoImage(image.convert('RGB'),master=self)
        self.create_image(0,0,anchor='nw',image=self._photo,tags='surface_raster')
        for x in range(len(self.order)):self.depth_line([(x,0,0),(x,2,0)],'floor','floor_curve_within')
        for y in range(3):self.depth_line([(0,y,0),(last,y,0)],'floor','floor_curve_across')
        for x in range(len(self.order)):self.depth_line(self.mesh[x*6],'surface','curve_within')
        for y in range(3):self.depth_line([row[y*10] for row in self.mesh],'surface','curve_across')
        for x,code in enumerate(self.order):
            for y,z in enumerate(self.values[code]):
                if z is not None:self.depth_line([(x,y,0),(x,y,z)],'stem','stem')
        if self.plane:self.depth_line([(0,0,1),(last,0,1),(last,2,1),(0,2,1),(0,0,1)],'norm','norm_plane')

    def text(self,x,y,value,size,tag,angle=0,anchor='center',**kwargs):
        item=self.create_text(x,y,text=value,font=('Arial',-size),fill=self.NAVY,
            angle=angle,anchor=anchor,justify='center',tags=tag,**kwargs)
        self.occupied.append(self.bbox(item))
        if tag in ('z_title','stage_title','method_label','z_tick','stage'):
            self._axis_boxes.append((item,self.text_box(x,y,value,size,angle,anchor),tag))
        return item

    def method_placements(self):
        result=[]
        for x,(code,title) in enumerate(zip(self.order,self.titles)):
            a,b=self.project(x,2,0),self.project(x,1,0)
            angle=math.degrees(math.atan2(-(a[1]-b[1]),a[0]-b[0]));anchor='w'
            if angle>90:angle-=180;anchor='e'
            elif angle< -90:angle+=180;anchor='e'
            p=self.project(x,2.14,0)
            result.append((p[0],p[1],f'{v.ORDER.index(code)+1} · {title}',angle,anchor))
        return result

    def draw_axes(self):
        n=self.number_pixels();s=self.display_scale();last=len(self.order)-1
        self.line3([(0,2,0),(0,2,self.zmax)],fill='#727a7b',width=1,tags='z_axis')
        for i in range(round(self.zmax/.2)+1):
            x,y,_=self.project(0,2,i*.2)
            text=f'{i*.2:.1f}'.replace('.',',')
            item=self.text(x-9,y-(9*s if i==0 else 0),text,n,'z_tick',anchor='e')
            if i==5:
                x0,y0,x1,y1=self.bbox(item)
                bg=self.create_rectangle(x0-4,y0,x1+4,y1,fill='#d9efbf',outline='',tags='norm_tick_highlight')
                self.tag_lower(bg,item)
        for key,pose in self.axis_poses.items():
            self.text(*pose['screen'],pose['text'],max(11,round(26*s)),'z_title' if key=='tempo' else 'stage_title',angle=pose['angle'])
        for px,py,text,angle,anchor in self.method_placements():
            self.text(px,py,text,n,'method_label',angle=angle,anchor=anchor)
        for y,word in enumerate(('min','med','max')):
            x,py,_=self.project(last,y,0)
            self.text(x+12*s,py+20*s,word,n,'stage',anchor='w')

    def draw_legend(self):
        x,y,w,h=self.legend_layout()
        self.text(x+w/2,y-29,'Результат / норматив',max(11,round(15*self.display_scale())),'legend_title')
        for row in range(round(h)):
            value=1.6*(1-row/max(1,h-1))
            self.create_rectangle(x,y+row,x+w,y+row+1,fill=self.colour(value),outline='',tags='legend')
        for value in self.LEGEND_TICKS:
            py=y+(1.6-value)/1.6*h
            self.create_line(x,py,x+w,py,fill='#a7afaa',width=.7,tags='legend_tick_line')
            self.text(x-8,py,'0' if value==0 else f'{value:.1f}'.replace('.',','),self.number_pixels(),'legend_tick',anchor='e')

    def samples(self):
        n=self.number_pixels();s=self.display_scale()
        def overlap(a,b):return a[0]<b[2]+3 and a[2]+3>b[0] and a[1]<b[3]+3 and a[3]+3>b[1]
        for x,code in enumerate(self.order):
            for y,z in enumerate(self.values[code]):
                if z is None:continue
                px,py,_=self.project(x,y,0);r=max(1.6,2.3*s)
                self.create_oval(px-r,py-r,px+r,py+r,fill=self.NAVY,outline='',tags='floor_sample')
                px,py,_=self.project(x,y,z);r=max(3,5.5*s)
                self.create_oval(px-r,py-r,px+r,py+r,fill='#ed171c',outline=self.NAVY,width=1,tags='sample')
                if not self.labels:continue
                value=f'{z:.2f}'.replace('.',',')
                f=tkfont.Font(root=self,font=('Arial',-n));tw=f.measure(value)
                chosen=None
                for dx,dy in ((5,-13),(8,-30),(8,20),(-45,-15),(-45,18),(16,-45)):
                    xx,yy=px+dx*s,py+dy*s;b=(xx,yy-n*.6,xx+tw,yy+n*.6)
                    if b[0]>=4 and b[2]<self.winfo_width()-4 and b[1]>4 and b[3]<self.winfo_height()-4 and not any(overlap(b,q) for q in self.occupied):
                        chosen=(xx,yy);break
                if chosen is None:chosen=(px+5,py-13*s)
                self.text(*chosen,value,n,'value',anchor='w')

    def draw(self):
        self._pending=None;self.delete('all')
        if self.winfo_width()<80 or self.winfo_height()<80:return
        self.occupied=[];self._axis_boxes=[];self.stats=Counter()
        self.fit_viewport();self.draw_scene();self.draw_legend();self.draw_axes();self.samples()
