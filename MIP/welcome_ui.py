"""Native login controls arranged after Boris's two 11 November references."""
import tkinter as tk
from tkinter import font as tkfont
from PIL import Image,ImageTk,ImageOps
BG='#eef3f8'
INK='#152c42'


def setup_login(app,resources):
    app.login_header.destroy()
    app.login_photo=tk.Label(app.main,bd=0,bg='#071626')
    app.login_photo.place(x=0,y=0,relwidth=1,relheight=1);app.login_photo.lower()
    app._welcome_assets={key:Image.open(resources/'assets'/name).convert('RGB') for key,name in (
        ('photo','login_background.png'),('left','login_institution.png'),('right','login_circle.png'),('shield','login_shield.png'))}
    app.login_banner=tk.Frame(app.main,bg='#fffed6');app.identity_banner=app.login_banner
    app.login_left=tk.Label(app.login_banner,bg='#fffed6',bd=0)
    app.login_right=tk.Label(app.login_banner,bg='#fffed6',bd=0)
    app.login_title=tk.Label(app.login_banner,text='СИСТЕМНЫЙ ТЕСТ\nПСИХИЧЕСКОЙ\nРАБОТОСПОСОБНОСТИ',bg='#fffed6',fg=INK,justify='center',bd=0)
    app.login_shield=tk.Label(app.main,bg='#ffffdb',bd=0)
    app.login_footer=tk.Frame(app.main,bg='#ffffdb',bd=0)
    app.login_group.configure(highlightthickness=1,highlightbackground=INK)
    app.form_body.pack_configure(padx=14,pady=8)
    app._welcome_images={}
    def changed(*_):
        if app.login_group.winfo_exists():app._login_size=None;layout_login(app)
    app.error_var.trace_add('write',changed)


def layout_login(app):
    if app.view_mode!='mode44' or not app.login_group.winfo_exists():return
    w,h=app.main.winfo_width(),app.main.winfo_height()
    if min(w,h)<20:return
    signature=(w,h,app.error_var.get(),float(app.root.tk.call('tk','scaling')))
    if signature==app._login_size:return
    app._login_size=signature
    def photo(key,widget,size,cover=False):
        image=app._welcome_assets[key];size=tuple(max(1,round(n)) for n in size)
        image=ImageOps.fit(image,size,method=Image.Resampling.LANCZOS,centering=(.5,1.)) if cover else ImageOps.contain(image,size,method=Image.Resampling.LANCZOS)
        app._welcome_images[key]=ImageTk.PhotoImage(image);widget.configure(image=app._welcome_images[key])
    photo('photo',app.login_photo,(w,h),True)
    margin=max(8,round(min(w,h)*.025));bw=w-2*margin;bh=round(min(h*.285,bw*.245))
    app.login_banner.place(x=margin,y=margin,width=bw,height=bh)
    institution_ratio=.50 if app._welcome_assets['left'].width<100 else .62
    left_size=round(bh*institution_ratio);right_size=round(bh*.70)
    photo('left',app.login_left,(left_size,left_size));photo('right',app.login_right,(right_size,right_size))
    app.login_left.place(x=round(bh*.12),rely=.5,anchor='w')
    app.login_right.place(x=bw-round(bh*.08),rely=.5,anchor='e')
    title_width=bw-2*right_size-bh*.4;size=max(13,round(bh/4.7))
    font=tkfont.Font(root=app.root,family='Segoe UI',size=-size,weight='bold')
    while font.measure('РАБОТОСПОСОБНОСТИ')>title_width and size>10:size-=1;font.configure(size=-size)
    app.login_title.configure(font=('Segoe UI',-size,'bold'));app.login_title.place(relx=.5,rely=.5,anchor='center')
    fit=min(1.5,max(.75,h/768));body=max(12,round(14*fit))
    for widget in app._login_labels+app._login_entries:widget.configure(font=('Segoe UI',-body))
    for widget in app._login_labels:widget.grid_configure(padx=(0,round(12*fit)),pady=round(2*fit))
    for widget in app._login_entries:widget.configure(width=24);widget.grid_configure(pady=round(2*fit),ipady=max(1,round(2*fit)))
    app.actions.grid_configure(pady=(round(8*fit),round(5*fit)))
    for widget in app.actions.winfo_children():widget.configure(font=('Segoe UI',-body),width=10,padx=round(5*fit),pady=max(3,round(4*fit)))
    app._login_link.configure(font=('Segoe UI',-body,'underline'));app._login_link.grid_configure(pady=0)
    app._login_error.configure(font=('Segoe UI',-max(11,round(12*fit))),wraplength=min(w-70,round(320*fit)))
    if app.error_var.get():app._login_error.grid()
    else:app._login_error.grid_remove()
    app.form_body.update_idletasks()
    pw=max(app.form_body.winfo_reqwidth()+30,round(h*.40));ph=app.form_body.winfo_reqheight()+18
    source_w,source_h=app._welcome_assets['photo'].size;photo_scale=max(w/source_w,h/source_h)
    stairs_y=round(source_h*(710/855)*photo_scale-(source_h*photo_scale-h));app._login_stairs_y=stairs_y
    top=margin+bh;footer_h=max(8,round(h*.035));shield_h=max(1,stairs_y-top-ph-footer_h+2)
    x=round((w-pw)/2)
    app.login_shield.place(x=x,y=top,width=pw,height=shield_h)
    photo('shield',app.login_shield,(pw-14,max(1,shield_h-8)))
    app.login_group.place(relx=0,rely=0,anchor='nw',x=x,y=top+shield_h-1,width=pw,height=ph)
    app.login_footer.place(x=x,y=top+shield_h+ph-2,width=pw,height=footer_h)
    app.login_footer.lift();app.login_shield.lift();app.login_group.lift();app.login_banner.lift()


METHODS={
 'A':'компенсаторное слежение за двигающимся объектом',
 'B':'определение положения объекта в пространстве при смещённой системе координат (авиагоризонт)',
 'C':'запоминание фигур в матрице',
 'D':'счёт в автотемпе',
 'E':'установление закономерностей цветового заполнения полей щита',
 'F':'отыскание чисел в матрице (чёрно-красно-белые таблицы)',
}


def show_user_intro(app):
    from intro_reference import show
    show(app)
