"""Participant introduction using the type and shape geometry of Boris's DOCX."""
import tkinter as tk
from tkinter import font as tkfont
from PIL import Image,ImageTk

BACKGROUND='#ffffdb'  # FFFFCC at 69.804% opacity on white, as in the DOCX.


def show(app):
    if not app.active_account:return app.show_mode_selection()
    app.page('')
    for child in app.main.winfo_children():child.destroy()
    app.main.configure(bg=BACKGROUND)
    app.main.unbind('<MouseWheel>')
    canvas=tk.Canvas(app.main,bg=BACKGROUND,bd=0,highlightthickness=0)
    canvas.pack(fill='both',expand=True)
    app.intro_canvas=canvas
    codes=app.allowed_codes
    if len(codes)==6:
        paragraphs=PARAGRAPHS
    else:
        from welcome_ui import METHODS
        paragraphs=[('Тест предназначен для определения психической работоспособности человека. Для вашей группы доступны четыре методики, которые предъявляются друг за другом:','body')]
        paragraphs += [(METHODS[c]+(';' if i<3 else '.'),str(i+1)) for i,c in enumerate(codes)]
        paragraphs += [PARAGRAPHS[-1]]
    app.intro_text='\n'.join(t for t,_ in paragraphs)
    import aviatest_v4 as v
    resources=v.base._runtime_resource_dir()/'assets'
    app._intro_label_sources=[Image.open(resources/name).convert('RGBA') for name in ('intro_exit_label.png','intro_next_label.png')]
    app._intro_label_images=[]
    app.intro_buttons=[]
    for title,command,color,points in [('ВЫХОД',app.exit_app,'#ee0000',20),('ДАЛЕЕ',app.build_menu_ui,'#47d459',22)]:
        border=tk.Frame(canvas,bg='#030e13',bd=0)
        button=tk.Button(border,text=title,command=command,bg=color,fg='black',activebackground=color,
            activeforeground='black',bd=0,relief='flat',highlightthickness=0,padx=0,pady=0,cursor='hand2')
        button.place(x=1,y=1,relwidth=1,relheight=1,width=-2,height=-2)
        app.intro_buttons.append((border,button,points))
    app.actions=tk.Frame(canvas)  # Native buttons are placed by document coordinates below.
    app._new_submit=app.build_menu_ui
    def layout(event=None):
        w,h=canvas.winfo_width(),canvas.winfo_height()
        if min(w,h)<20:return
        scale=min((w-24)/722.2,(h-24)/437.1)
        ox=(w-722.2*scale)/2;oy=(h-437.1*scale)/2
        canvas.delete('text')
        normal=tkfont.Font(root=app.root,family='Times New Roman',size=-max(10,round(18*scale)),weight='normal')
        bold=tkfont.Font(root=app.root,family='Times New Roman',size=-max(10,round(18*scale)),weight='bold')
        italic=tkfont.Font(root=app.root,family='Times New Roman',size=-max(10,round(18*scale)),weight='bold',slant='italic')
        app._intro_fonts=(normal,bold,italic)
        y=oy+3.6*scale
        line_height=20.7*scale
        for text,kind in paragraphs:
            font=italic if kind=='heading' else bold
            numbered=kind.isdigit()
            left=ox+(43.2 if numbered else 7.2)*scale
            right=ox+(722.2-7.2)*scale
            first_left=left if numbered else left+18*scale
            if numbered:
                canvas.create_text(ox+25.2*scale,y,text=kind+'.',font=normal,fill='black',anchor='nw',tags='text')
            words=text.split();first=True
            while words:
                x=first_left if first else left
                row=[]
                while words and (not row or font.measure(' '.join(row+[words[0]]))<=right-x):row.append(words.pop(0))
                if words and kind!='heading' and len(row)>1:
                    gap=(right-x-sum(font.measure(v) for v in row))/(len(row)-1)
                    for word in row:
                        canvas.create_text(x,y,text=word,font=font,fill='black',anchor='nw',tags='text')
                        x+=font.measure(word)+gap
                else:canvas.create_text(x,y,text=' '.join(row),font=font,fill='black',anchor='nw',tags='text')
                y+=line_height;first=False
        app._intro_text_bottom=y
        app._intro_label_images=[]
        for index,((frame,button,points),(x,y,bw,bh)) in enumerate(zip(app.intro_buttons,[(23.54,376.93,94.05,36),(326.2,376.88,130.05,36)])):
            source=app._intro_label_sources[index]
            ratio=points*scale/240
            label_image=ImageTk.PhotoImage(source.resize((max(1,round(source.width*ratio)),max(1,round(source.height*ratio))),Image.Resampling.LANCZOS))
            app._intro_label_images.append(label_image)
            button.configure(image=label_image,compound='none')
            inset=max(1,round(scale))
            button.place_configure(x=inset,y=inset,width=-2*inset,height=-2*inset)
            frame.place(x=round(ox+x*scale),y=round(oy+y*scale),width=round(bw*scale),height=round(bh*scale))
            frame.lift()
        app._intro_scale=scale
    canvas.bind('<Configure>',layout)
    app._intro_layout=layout
    layout()


PARAGRAPHS=[('Тест предназначен для определения психической работоспособности человека. Он состоит из четырех основных и двух дополнительных методик, которые предъявляются друг за другом:', 'body'), ('Основные методики:', 'heading'), ('компенсаторное слежение за двигающимся объектом;', '1'), ('запоминание фигур в матрице;', '2'), ('счет в автотемпе;', '3'), ('установление закономерностей цветового заполнения полей щита.', '4'), ('Дополнительные методики:', 'heading'), ('отыскание чисел в матрице (черно-красно-белые таблицы);', '5'), ('определение положения объекта в пространстве при смещенной системе координат (авиагоризонт).', '6'), ('Все методики состоят из ряда заданий, которые усложняются в ходе выполнения работы. Перед выполнением каждой методики внимательно прочтите инструкцию. Для начала тестирования с помощью клавиши «далее» перейдите на следующую страницу и выберите из открывшегося списка методику 1.', 'body')]
