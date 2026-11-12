"""Number public method labels without changing saved legacy identifiers."""
import re
import tkinter as tk
from tkinter import ttk
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps

NUMBER={'A':1,'C':2,'D':3,'E':4,'F':5,'B':6,
        'А':1,'С':2,'Д':3,'Е':4,'Ф':5,'В':6,'Б':6}
LEGACY_NUMBER={**NUMBER,'B':2,'В':2,'Б':2,'C':3,'С':3,'D':4,'Д':4}
ACTIVE_NUMBER=ContextVar('aviatest_display_number',default=None)
PATTERN=re.compile(r'\b(тест(?:а|у|ом|е|ы|ов|ам|ами|ах)?|методик(?:а|и|е|у|ой|ами|ах)?)\s+([ABCDEFАСДЕФВБ])\b',re.IGNORECASE)
RANGE=re.compile(r'\b(тест(?:а|у|ом|е|ы|ов|ам|ами|ах)?|методик(?:а|и|е|у|ой|ами|ах)?)\s+\(?([A-F])\s*[–—-]\s*([A-F])\b\)?',re.IGNORECASE)
LIST=re.compile(r'(\b(?:тесты|тестов|методики)\s*[=:]\s*)([A-F](?:\s*[,;/]\s*[A-F])*)\b',re.I)

@contextmanager
def legacy_labels():
    token=ACTIVE_NUMBER.set(LEGACY_NUMBER)
    try:yield
    finally:ACTIVE_NUMBER.reset(token)

def display_text(value):
    if not isinstance(value,str):return value
    numbers=ACTIVE_NUMBER.get() or NUMBER
    def expand(m):
        start,end=ord(m[2].upper()),ord(m[3].upper())
        values=sorted({numbers[chr(n)] for n in range(start,end+1)})
        return m[1]+' '+', '.join(map(str,values))
    value=RANGE.sub(expand,value)
    value=LIST.sub(lambda m:m[1]+', '.join(map(str,sorted({numbers[c.upper()] for c in re.findall('[A-F]',m[2],re.I)}))),value)
    value=PATTERN.sub(lambda m:f'{m[1]} {numbers[m[2].upper()]}',value)
    return re.sub('простая логическая деятельность','Счётно-логическая деятельность',value,flags=re.IGNORECASE)

def install_display_names():
    if getattr(tk.Misc,'_aviatest_numbered_labels',False):return
    original=tk.Misc._options
    def options(self,cnf,kw=None):
        config=tk._cnfmerge((cnf,kw)) if kw else tk._cnfmerge(cnf)
        if isinstance(config,dict):
            config=dict(config)
            for key in ('text','title','message','detail'):
                if key in config:config[key]=display_text(config[key])
        return original(self,config)
    tk.Misc._options=options
    title=tk.Wm.wm_title
    def numbered_title(self,string=None):
        return title(self,display_text(string))
    tk.Wm.wm_title=tk.Wm.title=numbered_title
    insert=tk.Text.insert
    def numbered_insert(self,index,chars,*args):
        return insert(self,index,display_text(chars),*args)
    tk.Text.insert=numbered_insert
    # Labels may be driven by StringVar.set(), which bypasses widget options.
    # Mirror their text for display; never modify a variable shared with input.
    def mirror(label):
        source=str(label.cget('textvariable'))
        if not source:return
        mapping=ACTIVE_NUMBER.get()
        shown=tk.StringVar(master=label.master)
        def sync(*_):
            token=ACTIVE_NUMBER.set(mapping)
            try:shown.set(display_text(str(label.getvar(source))))
            except tk.TclError:pass
            finally:ACTIVE_NUMBER.reset(token)
        sync();command=label.register(sync)
        label.tk.call('trace','add','variable',source,'write',command)
        label.configure(textvariable=shown)
        label._numbered_display_variable=shown
        def cleanup(event):
            if event.widget is label:
                try:label.tk.call('trace','remove','variable',source,'write',command)
                except tk.TclError:pass
        label.bind('<Destroy>',cleanup,add='+')
    def wrap_init(original):
        @wraps(original)
        def init(self,*args,**kwargs):
            original(self,*args,**kwargs);mirror(self)
        return init
    for cls in (tk.Label,tk.Message,ttk.Label):cls.__init__=wrap_init(cls.__init__)
    tk.Misc._aviatest_numbered_labels=True


def install_runtime_names(v):
    """Legacy memory/count/logic windows still use their original B/C/D keys."""
    install_display_names()
    if getattr(v.base,'_numbered_runtime_installed',False):return
    v.base._numbered_runtime_installed=True
    def translate_tree(value):
        if isinstance(value,dict):return {key:translate_tree(item) for key,item in value.items()}
        if isinstance(value,list):return [translate_tree(item) for item in value]
        if isinstance(value,tuple):return tuple(translate_tree(item) for item in value)
        return display_text(value)
    for code in ('C','D','E'):
        with legacy_labels():
            v.base.RESEARCH_FIELD_META[code]=translate_tree(v.base.RESEARCH_FIELD_META[code])
            v.base.RESEARCH_SECTION_META[code]=translate_tree(v.base.RESEARCH_SECTION_META[code])
    v.base.RESEARCH_CONFIG_SPECS=[(code,v.base.TEST_FULL_TITLES[code],cls,filename)
        for code,_title,cls,filename in v.base.RESEARCH_CONFIG_SPECS]
    def wrap_legacy(function):
        @wraps(function)
        def wrapped(*args,**kwargs):
            with legacy_labels():return function(*args,**kwargs)
        return wrapped
    for cls_name in ('MethodBWindow','MethodCWindow','MethodDWindow'):
        cls=getattr(v.base,cls_name)
        for method in ('__init__','_build_ui','run'):
            if hasattr(cls,method):setattr(cls,method,wrap_legacy(getattr(cls,method)))
    for name in ('show_method_b_results','show_method_c_results','show_method_d_results'):
        setattr(v.base.StartPageApp,name,wrap_legacy(getattr(v.base.StartPageApp,name)))
    # New and existing exports use the same current six-method mapping.
    headers=v.v2._excel_headers
    def numbered_headers():
        token=ACTIVE_NUMBER.set(NUMBER)
        try:return {column:tuple(display_text(value) for value in values) for column,values in headers().items()}
        finally:ACTIVE_NUMBER.reset(token)
    v.v2._excel_headers=numbered_headers
    v.base._fixed423_excel_headers=numbered_headers
    # Pygame is a separate UI path and bypasses Tk widget options entirely.
    import pygame as pg
    if v.base.pygame is None:v.base.pygame=pg
    caption=pg.display.set_caption
    pg.display.set_caption=lambda title,icontitle=None:caption(display_text(title),display_text(icontitle) if icontitle is not None else display_text(title))
    original_font=pg.font.Font
    class NumberedFont(original_font):
        def render(self,text,*args,**kwargs):return super().render(display_text(text),*args,**kwargs)
        def size(self,text):return super().size(display_text(text))
    pg.font.Font=NumberedFont
    sysfont=pg.font.SysFont
    def constructor(path,size,bold,italic):
        font=NumberedFont(path,size);font.set_bold(bold);font.set_italic(italic);return font
    def numbered_sysfont(name,size,bold=False,italic=False,constructor_override=None,**kwargs):
        custom=kwargs.pop('constructor',constructor_override)
        return sysfont(name,size,bold,italic,constructor=custom or constructor,**kwargs)
    pg.font.SysFont=numbered_sysfont


def bind_status_variable(variable):
    if getattr(variable,'_numbered_status_bound',False):return
    variable._numbered_status_bound=True
    def changed(*_):
        original=variable.get();converted=display_text(original)
        if converted!=original:variable.set(converted)
    variable.trace_add('write',changed);changed()
