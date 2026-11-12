"""Real participant-card callbacks and authenticated demo views stay distinct."""
from pathlib import Path
import re,tempfile,tkinter as tk
import aviatest_v4 as v
from mode_ui import install_modes,descendants
from storage import seed_configs
from demo_accounts import DEMO_VALUES,USER7_VALUES,DEMO_INDICES
with tempfile.TemporaryDirectory(prefix='aviatest414_browser_') as folder:
    rootdir=Path(folder);seed_configs(rootdir,Path(__file__).parent)
    v.base._runtime_app_dir=lambda:rootdir;v.base._enable_windows_dpi_awareness();install_modes(v)
    root=tk.Tk();root.withdraw();errors=[];root.report_callback_exception=lambda *args:errors.append(args)
    app=v.base.StartPageApp(root);root.attributes('-fullscreen',False);root.geometry('1366x768+20000+20000');root.deiconify();root.update()
    app.admin_authenticated=True;app.build_researcher_ui();root.update()
    app.show_all_results_browser();root.update()
    browser=next(x for x in root.winfo_children() if isinstance(x,tk.Toplevel))
    buttons=[w for w in descendants(browser) if isinstance(w,tk.Button) and w.cget('text')=='ОБЩИЙ\nПРОФИЛЬ СПР']
    assert len(buttons)==6,len(buttons)
    seen={}
    for button in buttons:
        button.invoke();root.update()
        top=next(x for x in root.winfo_children() if isinstance(x,tk.Toplevel) and hasattr(x,'_surface'))
        top.attributes('-fullscreen',False);top.geometry('1366x768+20000+20000');root.update()
        index=int(re.search(r'user([1-57])',top._surface_name).group(1))
        assert top._surface_raw['A']==list((USER7_VALUES if index==7 else DEMO_VALUES[index-1])[0])
        assert len(top._surface.find_withtag('sample'))==18
        seen[index]=tuple(tuple(top._surface.values[c]) for c in v.ORDER)
        top.destroy();root.update()
    assert len(set(seen.values()))==6
    browser.destroy();root.update()
    for index in DEMO_INDICES:
        app.show_mode_selection();app.fields['login'].set(f'user{index}');app.fields['password'].set(f'password{index}')
        app._new_submit();root.update();app.handle_enter();root.update()
        assert app.view_mode=='menu'
        top=app.show_integral_results();root.update()
        assert tuple(tuple(top._surface.values[c]) for c in v.ORDER)==seen[index]
        top.destroy();root.update()
    assert not errors,errors
    root.destroy()
print('PASS: all six real researcher-card callbacks and all six authenticated logins display their own distinct 18-point surface')
