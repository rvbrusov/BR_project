"""Optional installed-binary acceptance run on an explicitly isolated data root."""
import json,math,re,hashlib,sys,time
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from PIL import ImageGrab
import aviatest_v4 as v
from accounts import account_profile
from storage import participant_directory
from surface_view import surface_data
from demo_accounts import DEMO_INDICES,DEMO_VALUES,USER7_VALUES

LETTER=re.compile(r'\b(?:тест(?:а|у|ом|е|ы|ов|ам|ами|ах)?|методик(?:а|и|е|у|ой|ами|ах)?)\s+[ABCDEFАСДЕФВБ]\b|\bтесты\s*[=:]\s*[A-F]',re.I)

def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)

def audit_text(widget):
    texts=[]
    if isinstance(widget,(tk.Tk,tk.Toplevel)):texts.append(widget.title())
    for child in [widget,*descendants(widget)]:
        try:texts.append(str(child.cget('text')))
        except tk.TclError:pass
        if isinstance(child,tk.Canvas):
            texts.extend(child.itemcget(i,'text') for i in child.find_all() if child.type(i)=='text')
        if isinstance(child,tk.Text):texts.append(child.get('1.0','end'))
        if isinstance(child,ttk.Notebook):texts.extend(child.tab(tab,'text') for tab in child.tabs())
        if isinstance(child,ttk.Treeview):
            for item in child.get_children():texts.extend(map(str,child.item(item,'values')))
        if isinstance(child,(tk.Label,ttk.Label)):
            try:
                variable=child.cget('textvariable')
                if variable:texts.append(str(child.getvar(variable)))
            except tk.TclError:pass
    errors=[text for text in texts if LETTER.search(text)]
    assert not errors,errors
    return texts

def screenshot(window,path):
    window.lift();window.update();time.sleep(.25);window.update()
    x,y=window.winfo_rootx(),window.winfo_rooty()
    ImageGrab.grab(bbox=(x,y,x+window.winfo_width(),y+window.winfo_height())).save(path)

def audit_installed(root,app,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    errors=[];root.report_callback_exception=lambda *args:errors.append(str(args))
    root.attributes('-fullscreen',False);root.geometry('1366x900+0+0');root.update()
    initial_profiles={}
    for index in DEMO_INDICES:
        profile=account_profile(v.base,*app.accounts.authenticate(f'user{index}',f'password{index}'))
        path=v.base.UserProgressStore(participant_directory(app.data_root,profile.participant_id)).progress_file
        initial_profiles[index]=hashlib.sha256(path.read_bytes()).hexdigest()
    def login(name,password):
        app.show_mode_selection();app.fields['login'].set(name);app.fields['password'].set(password)
        app._new_submit();root.update()
        if app.view_mode not in ('menu','researcher') and not app.admin_authenticated:
            app.handle_enter();root.update()
    def new_top(before,attribute):
        tops=[w for w in root.winfo_children() if w not in before and isinstance(w,tk.Toplevel) and hasattr(w,attribute)]
        assert len(tops)==1,(attribute,[w.title() for w in root.winfo_children() if isinstance(w,tk.Toplevel)])
        return tops[0]
    authenticated=[];distinct=[]
    for index in DEMO_INDICES:
        login(f'user{index}',f'password{index}')
        assert app.view_mode=='menu'
        assert app.allowed_codes==v.ORDER
        audit_text(root)
        expected={code:list(row) for code,row in zip(v.ORDER,USER7_VALUES if index==7 else DEMO_VALUES[index-1])}
        expected['B']=[round(value*100)/80 for value in expected['B']]
        before=set(root.winfo_children());app.integral_results_btn.invoke();root.update()
        top=new_top(before,'_surface');chart=top._surface
        assert len(chart.find_withtag('sample'))==18
        for code in v.ORDER:
            assert all(math.isclose(a,b,abs_tol=1e-10) for a,b in zip(chart.values[code],expected[code])),(index,code,chart.values[code],expected[code])
        assert all(value>0 for row in chart.values.values() for value in row)
        distinct.append(tuple(tuple(chart.values[c]) for c in v.ORDER))
        audit_text(top)
        if index==7:
            top.attributes('-fullscreen',False);top.geometry('1366x900+0+0');root.update()
            screenshot(top,output/'installed-surface-user7.png')
            chart.event_generate('<ButtonPress-1>',x=650,y=220)
            chart.event_generate('<B1-Motion>',x=730,y=250)
            chart.event_generate('<ButtonRelease-1>',x=730,y=250);root.update()
            assert chart.yaw!=chart.INITIAL_YAW
            chart.reset_view();root.update();assert chart.yaw==chart.INITIAL_YAW
        top.destroy();root.update()
        for code in v.ORDER:
            before=set(root.winfo_children());app.menu_result_buttons[code].invoke();root.update()
            top=new_top(before,'_demo_result_table')
            assert top._demo_participant_id==app.current_profile.participant_id
            assert all(math.isclose(a,b,abs_tol=1e-10) for a,b in zip(top._demo_values,expected[code]))
            assert top.title().startswith(f'Тест {v.ORDER.index(code)+1} ·')
            rows=[top._demo_result_table.item(item,'values') for item in top._demo_result_table.get_children()]
            assert len(rows)==3
            assert all(float(row[1].replace(',','.'))>0 and float(row[3].replace(',','.'))>0 for row in rows)
            audit_text(top)
            if index==7 and code=='C':screenshot(top,output/'installed-individual-result.png')
            top.destroy();root.update()
            authenticated.append([index,v.ORDER.index(code)+1])
    assert len(set(distinct))==6
    login('admin','nowayin!');assert app.admin_authenticated
    tabs=[app.research_tabs.tab(tab,'text') for tab in app.research_tabs.tabs() if app.research_tabs.tab(tab,'state')!='hidden']
    assert tabs==[f'Тест {i}' for i in range(1,7)],tabs
    visible_items=app._fixed416_research_tab_items
    assert [item['label'].cget('text') for item in visible_items]==tabs
    assert all(item['label'].winfo_ismapped() for item in visible_items)
    for item in visible_items:
        item['label'].event_generate('<Button-1>');root.update();audit_text(root)
        assert app.research_tabs.tab(app.research_tabs.select(),'text')==item['label'].cget('text')
        assert item['label'].winfo_rootx()+item['label'].winfo_width()<=root.winfo_rootx()+root.winfo_width()
    app.research_tabs.select(app.research_tabs.tabs()[0]);root.update()
    screenshot(root,output/'installed-numbered-tabs.png')
    before=set(root.winfo_children());app.open_groups();root.update()
    manager=next(w for w in root.winfo_children() if w not in before and isinstance(w,tk.Toplevel))
    audit_text(manager);manager.destroy();root.update()
    before=set(root.winfo_children());app.show_all_results_browser();root.update()
    browser=next(w for w in root.winfo_children() if w not in before and isinstance(w,tk.Toplevel))
    audit_text(browser)
    check=next(w for w in descendants(browser) if isinstance(w,tk.Checkbutton) and w.cget('text')=='Тест 2')
    check.invoke()
    apply=next(w for w in descendants(browser) if isinstance(w,tk.Button) and w.cget('text')=='ПРИМЕНИТЬ ФИЛЬТРЫ')
    apply.invoke();root.update();audit_text(browser)
    buttons=[w for w in descendants(browser) if isinstance(w,tk.Button) and (re.match(r'^Тест [1-6]\n',str(w.cget('text'))) or w.cget('text')=='ОБЩИЙ\nПРОФИЛЬ СПР')]
    assert len(buttons)==42,len(buttons)
    researcher=[]
    for button in buttons:
        before=set(root.winfo_children());button.invoke();root.update()
        integral=button.cget('text')=='ОБЩИЙ\nПРОФИЛЬ СПР'
        top=new_top(before,'_surface' if integral else '_demo_result_table')
        if integral:
            assert all(z>0 for row in top._surface.values.values() for z in row)
            researcher.append([top._surface_participant_id,'surface'])
        else:
            assert all(z>0 for z in top._demo_values)
            assert top._demo_participant_id
            researcher.append([top._demo_participant_id,v.ORDER.index(top._demo_code)+1])
        audit_text(top);top.destroy();root.update()
    browser.destroy();root.update()
    for index in DEMO_INDICES:
        profile=account_profile(v.base,*app.accounts.authenticate(f'user{index}',f'password{index}'))
        path=v.base.UserProgressStore(participant_directory(app.data_root,profile.participant_id)).progress_file
        assert hashlib.sha256(path.read_bytes()).hexdigest()==initial_profiles[index]
    headers=v.v2._excel_headers()
    assert not any(LETTER.search(str(text)) for row in headers.values() for text in row)
    assert not errors,errors
    # Exercise the actual non-demo instruction windows too: their legacy B/C/D
    # identifiers must become 2/3/4, rather than modern storage-key numbers.
    login('user7','password7')
    for number,cls,loader in ((2,v.base.MethodBWindow,v.base.load_method_b_config),
                              (3,v.base.MethodCWindow,v.base.load_method_c_config),
                              (4,v.base.MethodDWindow,v.base.load_method_d_config)):
        window=cls(root,app.current_session,app.logger,app.base_dir,loader(app.base_dir))
        def close_modal(window=window,number=number):
            try:
                root.update_idletasks()
                assert f'Тест {number}' in window.win.title(),window.win.title()
                audit_text(window.win)
                screenshot(window.win,output/f'installed-test-{number}-instruction.png')
            except Exception as exc:errors.append(repr(exc))
            finally:
                if hasattr(window,'_cancel_afters'):window._cancel_afters()
                window.win.destroy()
        root.after(600,close_modal)
        result=window.run();assert not result.get('completed')
        root.update()
    engine=v.base.MethodAApp(v.base.load_config(app.base_dir/'method_a_config.json',root.winfo_screenwidth(),root.winfo_screenheight()),app.current_session,app.logger,app.base_dir)
    try:
        assert 'Тест 1' in v.base.pygame.display.get_caption()[0]
        engine.draw_background();engine.draw_zones();engine.draw_object(engine.init_stage_state());v.base.pygame.display.flip()
    finally:v.base.pygame.quit()
    orientation_top=tk.Toplevel(root)
    v.v2.IntegratedOrientationApp(orientation_top,v.v2.load_orientation_config(app.base_dir))
    root.update();audit_text(orientation_top);orientation_top.destroy();root.update()
    assert not errors,errors
    report={'installed_binary':bool(getattr(sys,'frozen',False)),'version':'4.21','six_demo_passwords_verified':True,
      'authenticated_individual_views':authenticated,'researcher_views':researcher,
      'six_distinct_nonzero_surfaces':True,'numbered_tabs':tabs,'visible_custom_tab_bar_and_clicks_verified':True,
      'no_letter_method_labels':True,'excel_headers_numbered':True,
      'mouse_rotation_and_reset_verified':True,'progress_unchanged_by_views':True,
      'real_instruction_windows_2_3_4_and_pygame_caption_1_verified':True,'callback_errors':errors}
    (output/'acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'passed':True,'individual_views':len(authenticated),'researcher_views':len(researcher)}))
