"""Disposable Windows worker for the GRD 10.0.2 profile.

Standard controls use Win32 messages. Only the windowless/legacy product browser
requires pointer input, relative to discovered control bounds. A cross-process
lock serializes all operations; foreground checks protect the input phase.
"""
from __future__ import annotations

import contextlib
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

from .core import KSelectError, PerformanceRequest, verify_report


def executable() -> Path:
    path = Path(os.environ.get("KSELECT_GRD_EXE", r"C:\Program Files (x86)\Krueger\Selection\GRD\grd.exe"))
    if path.name.lower() != "grd.exe" or not path.is_file():
        raise KSelectError("not_installed", "Install official K-Select with the GRD module, or set KSELECT_GRD_EXE to its grd.exe", path=str(path))
    return path.resolve()


def manufacturer_environment(base=None):
    """Restore public Windows COM paths omitted by restricted MCP clients.

    The MCP SDK's default inherited environment omits CommonProgramFiles. GRD's
    registered 32-bit components then fail with error 335 / 8007007E. Read only
    these standard paths from Windows, and preserve explicit client overrides.
    """
    import winreg
    env = dict(os.environ if base is None else base)
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion",
                        0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
        common = winreg.QueryValueEx(key, "CommonFilesDir")[0]
        try:
            common_x86 = winreg.QueryValueEx(key, "CommonFilesDir (x86)")[0]
        except FileNotFoundError:
            common_x86 = common
    names = {name.casefold() for name in env}
    for name, value in {"CommonProgramFiles": common, "CommonProgramFiles(x86)": common_x86,
                        "CommonProgramW6432": common}.items():
        if name.casefold() not in names:
            env[name] = value
    return env


@contextlib.contextmanager
def desktop_lock():
    import msvcrt
    directory = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "K-select-mcp"
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "desktop.lock").open("a+b") as f:
        if f.tell() == 0:
            f.write(b"0")
            f.flush()
        f.seek(0)
        try:
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            raise KSelectError("busy", "Another K-Select CLI/MCP operation owns the desktop lock") from exc
        try:
            yield
        finally:
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)


def wait_for(predicate, message: str, seconds: float = 5):
    deadline = time.monotonic() + seconds
    while True:
        value = predicate()
        if value:
            return value
        if time.monotonic() >= deadline:
            raise KSelectError("state_timeout", message)
        time.sleep(0.1)


def window_gone(handle):
    # A successful action can destroy a dialog before pywinauto revalidates its
    # wrapper. Query the OS handle directly so that success is not a stale-handle
    # exception. Never dereference the destroyed wrapper while polling.
    return not ctypes.windll.user32.IsWindow(handle) or not ctypes.windll.user32.IsWindowVisible(handle)


class GRD:
    def __init__(self):
        from pywinauto import Desktop
        self.desktop = Desktop(backend="win32")
        self.exe = executable()
        self.launch_record = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "K-select-mcp" / "launch.json"

    def process_matches(self, pid):
        import win32api
        from ctypes import wintypes
        try:
            query = ctypes.windll.kernel32.QueryFullProcessImageNameW
            query.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
            query.restype = wintypes.BOOL
            with contextlib.closing(win32api.OpenProcess(0x1000, False, pid)) as h:
                buffer = ctypes.create_unicode_buffer(32768)
                length = ctypes.c_ulong(len(buffer))
                if not query(int(h), 0, buffer, ctypes.byref(length)):
                    return False
            return Path(buffer.value).resolve() == self.exe
        except Exception:
            return False

    def path_matches(self, window):
        return self.process_matches(window.process_id())

    def starting(self):
        try:
            record = json.loads(self.launch_record.read_text(encoding="utf-8"))
            if 0 <= time.time() - record["time"] < 120 and self.process_matches(record["pid"]):
                return record
        except (OSError, ValueError, KeyError, TypeError):
            pass
        return None

    def roots(self):
        return [w for w in self.native_windows(prefix="GRD Selection Version ") if self.path_matches(w)]

    def native_windows(self, pid=None, prefix=None):
        import win32gui
        import win32process
        from pywinauto.controls.hwndwrapper import HwndWrapper, InvalidWindowHandle
        handles = []
        def collect(handle, _):
            if prefix and not win32gui.GetWindowText(handle).startswith(prefix):
                return True
            if pid is None or win32process.GetWindowThreadProcessId(handle)[1] == pid:
                handles.append(handle)
            return True
        win32gui.EnumWindows(collect, None)
        windows = []
        for handle in handles:
            try:
                if win32gui.IsWindow(handle) and win32gui.IsWindowVisible(handle):
                    windows.append(HwndWrapper(handle))
            except (InvalidWindowHandle, win32gui.error):
                # A transient dropdown/dialog can disappear between EnumWindows
                # and wrapper construction. Do not fail the whole snapshot.
                continue
        return windows

    def root(self):
        roots = self.roots()
        if len(roots) != 1:
            raise KSelectError("not_ready", "Expected exactly one GRD main window; launch or resolve multiple instances", count=len(roots))
        if "10.0.2" not in roots[0].window_text():
            raise KSelectError("unsupported_version", "This release is validated against GRD 10.0.2", title=roots[0].window_text())
        return roots[0]

    def windows(self, root):
        return [w for w in self.native_windows(root.process_id()) if w.handle != root.handle and w.class_name() not in ("ThunderRT6Main", "tooltips_class32")]

    @staticmethod
    def dialog_details(window):
        details = {"title": window.window_text(), "class": window.class_name()}
        if details["class"] == "#32770":
            details["text"] = [c.window_text()[:2000] for c in window.descendants() if c.is_visible() and c.class_name() in ("Static", "Button") and c.window_text()]
        return details

    def status(self):
        roots = self.roots()
        result = {"ok": True, "executable": str(self.exe), "windows": [{"handle": w.handle, "title": w.window_text(), "pid": w.process_id()} for w in roots]}
        if not roots:
            starting = self.starting()
            if starting:
                return {**result, "state": "starting", "pid": starting["pid"]}
            return {**result, "state": "not_running"}
        if len(roots) != 1:
            return {**result, "state": "multiple_instances"}
        w = roots[0]
        dialogs = self.windows(w)
        state = "blocked" if dialogs or not w.is_enabled() else "ready"
        if "10.0.2" not in w.window_text():
            state = "unsupported_version"
        return {**result, "state": state, "dialogs": [self.dialog_details(d) for d in dialogs], "screen": w.window_text()}

    def launch(self):
        if self.roots():
            return self.status()
        starting = self.starting()
        if starting:
            return {"ok": True, "state": "starting", "pid": starting["pid"], "executable": str(self.exe)}
        # Do not wait for input-idle or the GUI. Clients poll status afterwards.
        process = subprocess.Popen([str(self.exe)], cwd=str(self.exe.parent), env=manufacturer_environment())
        self.launch_record.parent.mkdir(parents=True, exist_ok=True)
        self.launch_record.write_text(json.dumps({"pid": process.pid, "time": time.time()}), encoding="utf-8")
        return {"ok": True, "state": "starting", "pid": process.pid, "executable": str(self.exe)}

    def require_unblocked(self, root):
        dialogs = self.windows(root)
        if dialogs or not root.is_enabled():
            raise KSelectError("blocked", "Close or resolve the existing GRD report/dialog before calculating", dialogs=[d.window_text() for d in dialogs])

    @staticmethod
    def visible(root, **criteria):
        matches = []
        for c in root.descendants():
            if not c.is_visible():
                continue
            if "control_id" in criteria and c.control_id() != criteria["control_id"]:
                continue
            if "class_name" in criteria and c.class_name() != criteria["class_name"]:
                continue
            if "title" in criteria and c.window_text() != criteria["title"]:
                continue
            matches.append(c)
        if len(matches) != 1:
            raise KSelectError("unexpected_ui", "Expected one visible control", criteria=criteria, count=len(matches))
        return matches[0]

    @staticmethod
    def foreground(root):
        for _ in range(3):
            root.set_focus()
            if ctypes.windll.user32.GetForegroundWindow() == root.handle:
                return
            time.sleep(0.15)
        raise KSelectError("desktop_interference", "Could not foreground GRD; keep the desktop unlocked and retry")

    def back(self, root):
        controls = [c for c in root.descendants(class_name="AfxOleControl42s") if c.is_visible() and not c.window_text()]
        if len(controls) != 2:
            raise KSelectError("unexpected_ui", "Product Index Back/Next controls were not found")
        self.foreground(root)
        min(controls, key=lambda c: c.rectangle().left).click_input()
        time.sleep(0.4)

    def row(self, root, index):
        grid = self.visible(root, title="Double Click an item to select it")
        rect = grid.rectangle()
        # Observed native grid: 25px heading and 24px rows at 96 DPI. Scale
        # relative to the discovered grid width, then verify native PDF identity.
        scale = rect.width() / 371
        x, y = int(rect.width() / 2), round((38 + index * 24) * scale)
        # This legacy grid updates its selected row on WM_MOUSEMOVE, not on
        # button-down. Send that event before the double-click; no pointer input
        # or foreground ownership is needed for the observed grid control.
        grid.send_message(0x0200, 0, (y << 16) | x)
        time.sleep(0.15)
        grid.double_click(coords=(x, y))
        time.sleep(0.7)

    def select_1400(self, root):
        import win32gui
        fresh_index = False
        if "[Project Screen]" in root.window_text():
            project = self.visible(root, class_name="ThunderRT6TextBox", control_id=6).window_text().strip()
            if project and project.lower() != "temp.kec":
                raise KSelectError("project_open", "Use a separate GRD quick-selection session; a named project is open", project=project)
            quick = self.visible(root, title="Quick Select", class_name="ThunderRT6CommandButton")
            win32gui.PostMessage(win32gui.GetParent(quick.handle), 0x0111, quick.control_id(), quick.handle)
            wait_for(lambda: "[Product Index]" in root.window_text(), "Quick Select did not open Product Index")
            fresh_index = not project
        elif "[GRD Performance]" in root.window_text():
            # Keep an already open performance screen. Final native PDF identity
            # verification rejects any model other than 1400; never infer identity
            # from a previously saved run or from the generic window title.
            return
        if "[Product Index]" not in root.window_text():
            raise KSelectError("unexpected_ui", "Start from Project Screen, Product Index or GRD Performance")
        current = self.visible(root, class_name="ThunderRT6TextBox", control_id=2).window_text().strip()
        root_categories = {"Accessories", "Architectural", "Clean Room", "Diffusers", "Grilles & Registers",
                           "Industrial Supply Grilles", "Linear Grilles", "Metric", "Security Grilles", "Stainless Steel GRDs", "Underfloor (UFAD)"}
        diffuser_categories = {"Drop Faced Louver Diffuser", "Flush Faced Louver Face Diffuser", "Linear Slot Diffusers",
                               "Modular Core Diffusers", "Perforated Diffuser", "Plenum Slot Diffusers", "Round Ceiling Diffusers"}
        family = "4 Cone Louvered Face Diffuser - Steel Construction"
        if fresh_index or current in root_categories:
            self.row(root, 3)  # Diffusers
            self.row(root, 0)  # Drop Faced Louver Diffuser
        elif current in diffuser_categories:
            self.row(root, 0)
        elif current != family:
            # Other families need the interactive Back controls. Keep this
            # bounded and verify the resulting family before calculating.
            for _ in range(3):
                self.back(root)
            self.row(root, 3)
            self.row(root, 0)
        description = self.visible(root, class_name="ThunderRT6TextBox", control_id=2).window_text()
        if "4 Cone Louvered Face Diffuser - Steel Construction" != description.strip():
            raise KSelectError("unexpected_ui", "Product browser did not reach the validated 1400 family", description=description)
        self.row(root, 0)  # 1400
        try:
            wait_for(lambda: "[GRD Performance]" in root.window_text(), "1400 performance screen did not open")
        except KSelectError:
            self.require_unblocked(root)
            # A missed double-click is safe to repeat once only when the same
            # verified family page remains. Never click a different screen.
            if "[Product Index]" not in root.window_text() or self.visible(root, class_name="ThunderRT6TextBox", control_id=2).window_text().strip() != description.strip():
                raise
            self.row(root, 0)
            wait_for(lambda: "[GRD Performance]" in root.window_text(), "1400 performance screen did not open")

    def dialog(self, root, title):
        def find():
            matches = [w for w in self.windows(root) if w.window_text() == title]
            return matches[0] if len(matches) == 1 else None
        return wait_for(find, f"Expected GRD dialog: {title}")

    @staticmethod
    def button(dialog, control_id=1):
        return GRD.visible(dialog, control_id=control_id, class_name="Button")

    def accept_dialog(self, dialog):
        import win32gui
        button = wait_for(lambda: self.button(dialog) if self.button(dialog).is_enabled() else None,
                          "Native dialog OK/Save button is not enabled")
        handle = dialog.handle
        # Post the standard IDOK/BN_CLICKED notification to the dialog itself.
        # Unlike synchronous BM_CLICK, this neither depends on foreground focus
        # nor waits inside a handler which may open the next modal dialog.
        win32gui.PostMessage(handle, 0x0111, 1, button.handle)  # WM_COMMAND
        wait_for(lambda: window_gone(handle), "Native dialog did not accept OK/Save")

    @staticmethod
    def replace_edit(edit, text):
        edit.set_edit_text(text, pos_start=0, pos_end=-1)
        time.sleep(0.2)
        if edit.window_text() != text:
            raise KSelectError("input_mismatch", "Native edit control did not retain exact replacement text")

    def export(self, root, path):
        from pywinauto import Desktop
        root.menu_select("Performance->Print Performance")
        report = self.dialog(root, "Performance Results Report")
        report_uia = Desktop(backend="uia").window(handle=report.handle)
        report_uia.child_window(title="Export Report", control_type="Button").wait("exists", timeout=5).invoke()
        export = self.dialog(root, "Export")
        # Old Crystal ComboBoxEx returns corrupt CB_GETLBTEXT across bitness.
        # UIA value text is readable; keyboard chooses PDF explicitly if needed.
        fmt = report_uia.child_window(auto_id="16401", control_type="ComboBox").wrapper_object()
        value = fmt.iface_value.CurrentValue
        if value != "Adobe Acrobat (PDF)":
            fmt.select("Adobe Acrobat (PDF)")
        dest = report_uia.child_window(auto_id="16934", control_type="ComboBox").wrapper_object()
        if dest.iface_value.CurrentValue != "Disk file":
            dest.select("Disk file")
        self.accept_dialog(export)
        options = self.dialog(root, "Export Options")
        self.accept_dialog(options)
        save = self.dialog(root, "Choose export file")
        time.sleep(0.8)  # The shell populates its default filename asynchronously.
        self.replace_edit(self.visible(save, control_id=1001, class_name="Edit"), str(path))
        time.sleep(0.3)  # Let the common dialog commit its filename change.
        save_handle = save.handle
        self.accept_dialog(save)
        wait_for(lambda: window_gone(save_handle), "Native Save dialog did not close", seconds=5)
        def finished():
            if not path.exists() or path.stat().st_size < 100:
                return False
            try:
                from pypdf import PdfReader
                return len(PdfReader(path).pages) == 1
            except Exception:
                return False
        wait_for(finished, "Native PDF did not finish exporting", seconds=8)
        # Close only the report created by this operation, never arbitrary dialogs.
        report.close()

    def calculate(self, request, output_directory):
        root = self.root()
        self.require_unblocked(root)
        request = PerformanceRequest(**request)
        output = Path(output_directory).resolve()
        try:
            output.mkdir(parents=True, exist_ok=False)
        except FileExistsError as exc:
            raise KSelectError("output_exists", "Choose a fresh output directory; existing evidence is never overwritten", path=str(output)) from exc
        journal = {"state": "started", "request": request.as_dict(), "output_directory": str(output), "backend": "GRD 10.0.2 native GUI", "started_at": time.time()}

        def record(state, **values):
            journal.update(state=state, **values)
            temp = output / "journal.tmp"
            temp.write_text(json.dumps(journal, indent=2), encoding="utf-8")
            temp.replace(output / "journal.json")

        try:
            record("selecting")
            self.select_1400(root)
            # Duplicate neck diameters correspond to different module sizes.
            neck = self.visible(root, class_name="ThunderRT6ComboBox", control_id=5)
            neck.select(request.neck_index)
            border = self.visible(root, class_name="ThunderRT6ComboBox", control_id=7)
            border.select(request.border)
            if neck.window_text().strip() != str(request.neck_in) or border.window_text() != request.border:
                raise KSelectError("input_mismatch", "GRD did not retain requested controls")
            record("calculating")
            root.menu_select("Performance->View Performance at Given Airflow")
            flow = self.dialog(root, "Enter Desired CFM")
            edit = self.visible(flow, control_id=4900, class_name="Edit")
            self.replace_edit(edit, str(request.effective_cfm))
            if edit.window_text() != str(request.effective_cfm):
                raise KSelectError("input_mismatch", "Airflow edit did not retain input")
            flow_handle = flow.handle
            self.accept_dialog(flow)
            wait_for(lambda: window_gone(flow_handle), "Airflow dialog did not close")
            self.require_unblocked(root)
            record("exporting")
            pdf = output / "performance.pdf"
            self.export(root, pdf)
            result = verify_report(pdf, request)
            result.update(output_directory=str(output), backend="GRD 10.0.2 native GUI", journal=str(output / "journal.json"))
            (output / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
            record("complete", completed_at=time.time(), report_sha256=result["report"]["sha256"])
            return result
        except Exception as exc:
            (output / "diagnostic.txt").write_text(traceback.format_exc(), encoding="utf-8")
            try:
                journal["failure_windows"] = [self.dialog_details(w) for w in self.windows(root)]
            except Exception:
                pass
            error = exc.as_dict()["error"] if isinstance(exc, KSelectError) else {"code": "unexpected_ui", "message": str(exc)}
            record("failed", failed_stage=journal["state"], error=error)
            details = {k: v for k, v in error.items() if k not in ("code", "message")}
            raise KSelectError(error["code"], error["message"], **details, output_directory=str(output), journal=str(output / "journal.json")) from exc


def main():
    try:
        arguments = json.load(sys.stdin)
        operation = arguments.pop("operation")
        with desktop_lock():
            grd = GRD()
            if operation == "status":
                result = grd.status()
            elif operation == "launch":
                result = grd.launch()
            elif operation == "calculate":
                result = grd.calculate(**arguments)
            else:
                raise KSelectError("invalid_operation", "Unknown worker operation")
    except KSelectError as exc:
        result = exc.as_dict()
    except Exception as exc:
        traceback.print_exc(file=sys.stderr)
        result = KSelectError("worker_failed", str(exc)).as_dict()
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()
