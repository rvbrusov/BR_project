"""A local show/hide control. Password values are never copied or logged."""
import tkinter as tk
from PIL import Image,ImageDraw,ImageTk


def add_toggle(entry):
    icons=[]
    for slash in (False,True):
        image=Image.new('RGBA',(96,96))
        draw=ImageDraw.Draw(image)
        color='#245da8'
        draw.line([(12,48),(22,35),(35,26),(48,23),(61,26),(74,35),(84,48),(74,61),(61,70),(48,73),(35,70),(22,61),(12,48)],fill=color,width=6,joint='curve')
        draw.ellipse((36,36,60,60),fill=color)
        if slash:
            draw.line((15,15,81,81),fill='#eef3f8',width=13)
            draw.line((15,15,81,81),fill=color,width=6)
        icons.append(ImageTk.PhotoImage(image.resize((22,22),Image.Resampling.LANCZOS)))
    button=tk.Button(entry.master,image=icons[0],text='Показать пароль',compound='none',
        bg='#eef3f8',activebackground='#dce4ed',bd=0,highlightthickness=1,
        highlightbackground='#eef3f8',highlightcolor='#245da8',cursor='hand2',takefocus=True,padx=3,pady=2)
    button._eye_images=icons
    button._password_visible=False
    def toggle():
        visible=not button._password_visible
        entry.configure(show='' if visible else '●')
        button._password_visible=visible
        button.configure(image=icons[int(visible)],text='Скрыть пароль' if visible else 'Показать пароль')
    button.configure(command=toggle)
    def activate(event):
        toggle()
        return 'break'
    button.bind('<Return>',activate)
    return button
