"""Smoke-render six unchanged method interfaces in a real authenticated account."""
from dataclasses import asdict
from pathlib import Path
import tempfile
import tkinter as tk

import aviatest_v4 as v
from mode_ui import install_modes
from storage import seed_configs


def run():
    with tempfile.TemporaryDirectory(prefix='aviatest44_methods_') as folder:
        directory = Path(folder)
        seed_configs(directory, Path(__file__).parent)
        v.base._runtime_app_dir = lambda: directory
        install_modes(v)
        root = tk.Tk()
        errors = []
        root.report_callback_exception = lambda *args: errors.append(args)
        app = v.base.StartPageApp(root)
        profile = v.base.UserProfile(name='QA methods', age=30, gender='Мужской', education='Высшее')
        account=app.accounts.register('qa-methods', 'qa-only', 'qa-only', profile)
        app.groups.assign(account[0],1)
        app.enter_account(*account)
        root.update()
        # A: real pygame renderer and resources, no altered normative values.
        engine = v.base.MethodAApp(v.base.load_config(app.base_dir / 'method_a_config.json',
                                                      root.winfo_screenwidth(), root.winfo_screenheight()),
                                  app.current_session, app.logger, app.base_dir)
        try:
            engine.draw_background()
            engine.draw_zones()
            engine.draw_object(engine.init_stage_state())
            v.base.pygame.display.flip()
        finally:
            v.base.pygame.quit()
        # B: orientation intro, followed by C/D/E actual modal instruction windows.
        top = tk.Toplevel(root)
        orientation = v.v2.IntegratedOrientationApp(top, v.v2.load_orientation_config(app.base_dir))
        root.update()
        assert top.winfo_exists()
        top.destroy()
        root.update()
        for cls, loader in ((v.base.MethodBWindow, v.base.load_method_b_config),
                            (v.base.MethodCWindow, v.base.load_method_c_config),
                            (v.base.MethodDWindow, v.base.load_method_d_config)):
            window = cls(root, app.current_session, app.logger, app.base_dir, loader(app.base_dir))
            def close_modal(window=window):
                root.update_idletasks()
                assert window.win.winfo_exists()
                if hasattr(window, '_cancel_afters'):
                    window._cancel_afters()
                window.win.destroy()
            root.after(600, close_modal)
            result = window.run()
            assert not result.get('completed')
            root.update()
        # F: complete the real three-stage click flow through grouped persistence.
        for code in 'ABCDE':
            app.progress_store.mark_completed(app.current_profile, code)
        top = v.launch_f(app)
        root.update()
        assert top._red_black.root.winfo_exists()
        child=top._red_black
        child.session=[];child.training=False
        original_clock=v.rb.time.perf_counter
        ticks=[100.]
        def clock():
            ticks[0]+=.5
            return ticks[0]
        v.rb.time.perf_counter=clock
        try:
            for stage in range(1,4):
                child.start_stage(stage);root.update()
                assert len(child.sequence)==(34,51,68)[stage-1]
                assert len(child.cell_widgets)==len(child.sequence)
                for cell in list(child.sequence)[:-1]:child.click_cell(cell)
                assert child.pending_stage_result is None
                child.click_cell(child.sequence[-1])
                assert child.pending_stage_result['target_count']==(34,51,68)[stage-1]
                child.open_pending_result();root.update()
        finally:
            v.rb.time.perf_counter=original_clock
        stored=app.progress_store.get_test_result(app.current_profile,'F')
        assert len(stored['stages'])==3 and stored['study_group']=={'number':1,'test_count':6}
        assert (app.base_dir/'Integrated Data_methods_tracking_header_final.xlsx').exists()
        child.close()
        root.update()
        root.destroy()
        assert not errors, errors
    print('PASS: A real pygame render; B orientation intro; C/D/E modal instruction windows and cancel; F complete three-stage flow, group snapshot, JSON and Excel; authenticated private data directory; no Tk callback errors. Full timed A-E sessions not performed.')


if __name__ == '__main__':
    run()
