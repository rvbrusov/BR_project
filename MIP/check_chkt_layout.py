"""Real Tk layout regression: all numeric targets must stay visible after resizing."""
import ast
import pathlib
import tempfile
import tkinter as tk
import red_black_numbers as rb

root = tk.Tk()
app = rb.RedBlackApp(root)
errors = []
root.report_callback_exception = lambda *args: errors.append(args)
# Simulate client areas at different Windows scaling factors without changing the display.
original_attributes = root.attributes
root.attributes = lambda *args: None if args and args[0] == '-fullscreen' else original_attributes(*args)
root.minsize(1, 1)

def inside(widget, ancestor):
    x = widget.winfo_rootx() - ancestor.winfo_rootx()
    y = widget.winfo_rooty() - ancestor.winfo_rooty()
    assert widget.winfo_ismapped(), str(widget)
    assert x >= 0 and y >= 0, (str(widget), x, y)
    assert x + widget.winfo_width() <= ancestor.winfo_width(), (str(widget), 'right')
    assert y + widget.winfo_height() <= ancestor.winfo_height(), (str(widget), 'bottom')

def settle(width, height):
    root.geometry(f'{width}x{height}+0+0')
    for _ in range(4):
        root.update()

def descendants(parent):
    for child in parent.winfo_children():
        yield child
        yield from descendants(child)

for width, height in [(640,420), (800,480), (910,512), (1093,614), (1366,768), (1536,864), (1920,1080)]:
    for stage in (1,2,3):
        app.start_stage(stage)
        settle(width, height)
        inside(app.grid_frame, root)
        assert abs(app.grid_frame.winfo_width()-app.grid_frame.winfo_height()) <= 1
        for widget in app.grid_frame.winfo_children():
            inside(widget, app.grid_frame)
        inside(app.cancel_stage_button, root)
        inside(app.next_stage_button, root)
        inside(app.progress_label, root)
        inside(app.time_canvas, root)
        # Error feedback and undo keep the layout; exercise the actual buttons.
        wrong = next(c for c in app.sequence if c != app.sequence[0])
        app.click_cell(wrong)
        app.click_cell(app.sequence[0])
        app.undo_last_click()
        assert app.position == 0
        for cell in app.sequence:
            app.cell_widgets[cell].invoke()
        assert app.pending_stage_result['stage'] == stage
        root.update()
        inside(app.error_label, root)
        assert str(app.next_stage_button['state']) == 'normal'
        # Test result screens without persisting synthetic results.
        app.training = True
        app.open_pending_result()
        settle(width, height)
        for w in descendants(root):
            if isinstance(w, tk.Button): inside(w, root)
    app.show_home()
    settle(width, height)
    for w in descendants(root):
        if isinstance(w, tk.Button): inside(w, root)
    app.show_instruction()
    settle(width, height)
    for w in descendants(root):
        if isinstance(w, (tk.Button, tk.Text)): inside(w, root)
    app.show_settings()
    settle(width, height)
    for w in descendants(root):
        if isinstance(w, (tk.Button, rb.ttk.Entry)): inside(w, root)
    print(f'PASS {width}x{height}: three stages, all cells, feedback, controls, results, home, settings', flush=True)

root.destroy()
assert not errors, errors
# Calculation, order, norms and persistence must retain their original ASTs.
old = ast.parse(pathlib.Path('../aviatest_v4_1/red_black_numbers.py').read_text(encoding='utf-8'))
new = ast.parse(pathlib.Path('red_black_numbers.py').read_text(encoding='utf-8'))
changed = []
def definitions(tree):
    result = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef): result[node.name] = ast.dump(node)
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef): result[node.name+'.'+item.name] = ast.dump(item)
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ('DEFAULT_SETTINGS','STAGES'):
                    result[target.id] = ast.dump(node)
    return result
before, after = definitions(old), definitions(new)
allowed = {'RedBlackApp.'+name for name in ('__init__','header','show_home','show_instruction','show_settings','start_stage','tick','show_stage_result')}
for name, value in before.items():
    if value != after[name]:
        changed.append(name)
        assert name in allowed, name
print('PASS: only UI methods changed:', ', '.join(changed))
