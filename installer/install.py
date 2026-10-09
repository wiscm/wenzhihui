# -*- coding: utf-8 -*-
"""文智汇 v1.0 安装向导（PyInstaller 单 exe 入口）。"""
import os
import sys
import io
import zipfile
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


APP_NAME = '文智汇'
APP_VERSION = '1.0'
APP_DESCRIPTION = 'AI 文献智能数据获取系统'
DEFAULT_INSTALL_DIR = os.path.join(
    os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), APP_NAME
)


def resource_path(rel):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, rel)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), rel)


def get_embedded_zip_bytes():
    with open(resource_path('release.zip'), 'rb') as f:
        return f.read()


def create_shortcut(target, lnk_path, description=''):
    ps = (
        "$ws = New-Object -ComObject WScript.Shell\n"
        f"$sc = $ws.CreateShortcut('{lnk_path}')\n"
        f"$sc.TargetPath = '{target}'\n"
        f"$sc.WorkingDirectory = '{os.path.dirname(target)}'\n"
        f"$sc.Description = '{description}'\n"
        f"$sc.IconLocation = '{target},0'\n"
        "$sc.Save()\n"
    )
    subprocess.run(
        ['powershell', '-NoProfile', '-NonInteractive', '-Command', ps],
        capture_output=True, text=True
    )


class Installer:
    def __init__(self, root):
        self.root = root
        self.root.title(f'{APP_NAME} v{APP_VERSION} - 安装向导')
        self.root.geometry('620x440')
        self.root.resizable(False, False)

        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 620) // 2
        y = (self.root.winfo_screenheight() - 440) // 2
        self.root.geometry(f'+{x}+{y}')

        self.create_desktop = tk.BooleanVar(value=True)
        self.create_startmenu = tk.BooleanVar(value=True)
        self.launch_after = tk.BooleanVar(value=True)
        self.path_var = tk.StringVar(value=DEFAULT_INSTALL_DIR)

        self._build_ui()

    def _build_ui(self):
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill='both', expand=True, padx=10, pady=10)

        # Page 1: Welcome
        p1 = ttk.Frame(self.nb)
        ttk.Label(p1, text=f'欢迎安装 {APP_NAME}', font=('Microsoft YaHei', 16, 'bold')).pack(pady=(30, 8))
        ttk.Label(p1, text=f'版本 v{APP_VERSION}', font=('Microsoft YaHei', 10)).pack()
        ttk.Label(p1, text=APP_DESCRIPTION, foreground='gray').pack(pady=4)
        ttk.Label(
            p1,
            text='本程序将把文智汇安装到您的电脑。\n安装完成后，您可以从桌面快捷方式启动它。',
            justify='center',
        ).pack(pady=24)
        self.nb.add(p1, text='  欢迎  ')

        # Page 2: Path
        p2 = ttk.Frame(self.nb)
        ttk.Label(p2, text='安装路径：').pack(anchor='w', padx=20, pady=(20, 4))
        path_frame = ttk.Frame(p2)
        path_frame.pack(fill='x', padx=20)
        ttk.Entry(path_frame, textvariable=self.path_var).pack(side='left', fill='x', expand=True)
        ttk.Button(path_frame, text='浏览...', command=self._browse).pack(side='left', padx=(4, 0))

        opts = ttk.LabelFrame(p2, text='选项')
        opts.pack(fill='x', padx=20, pady=20)
        ttk.Checkbutton(opts, text='创建桌面快捷方式', variable=self.create_desktop).pack(anchor='w', padx=10, pady=2)
        ttk.Checkbutton(opts, text='创建开始菜单快捷方式', variable=self.create_startmenu).pack(anchor='w', padx=10, pady=2)
        self.nb.add(p2, text='  安装路径  ')

        # Page 3: Installing
        p3 = ttk.Frame(self.nb)
        ttk.Label(p3, text='正在安装...', font=('Microsoft YaHei', 12)).pack(pady=(40, 12))
        self.progress = ttk.Progressbar(p3, mode='determinate', length=520)
        self.progress.pack(pady=8, padx=20)
        self.progress_label = ttk.Label(p3, text='准备中...')
        self.progress_label.pack(pady=4)
        self.nb.add(p3, text='  正在安装  ')

        # Page 4: Done
        p4 = ttk.Frame(self.nb)
        ttk.Label(p4, text='安装完成！', font=('Microsoft YaHei', 16, 'bold'), foreground='green').pack(pady=(40, 10))
        ttk.Label(p4, text=f'{APP_NAME} 已成功安装到您的电脑。').pack(pady=4)
        ttk.Checkbutton(p4, text='安装完成后启动文智汇', variable=self.launch_after).pack(pady=24)
        self.nb.add(p4, text='  完成  ')

        # 底部按钮
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill='x', padx=10, pady=(0, 10))
        self.btn_cancel = ttk.Button(btn_frame, text='取消', command=self.root.destroy)
        self.btn_cancel.pack(side='right', padx=4)
        self.btn_next = ttk.Button(btn_frame, text='下一步 >', command=self._on_next)
        self.btn_next.pack(side='right')

        self.nb.bind('<<NotebookTabChanged>>', lambda e: self._refresh_buttons())
        self._refresh_buttons()

    def _refresh_buttons(self):
        idx = self.nb.index('current')
        if idx == 0:
            self.btn_next.config(text='下一步 >', state='normal')
            self.btn_cancel.config(text='取消', state='normal')
        elif idx == 1:
            self.btn_next.config(text='安装', state='normal')
            self.btn_cancel.config(text='取消', state='normal')
        elif idx == 2:
            self.btn_next.config(text='安装中...', state='disabled')
            self.btn_cancel.config(state='disabled')
        elif idx == 3:
            self.btn_next.config(text='完成', state='normal')
            self.btn_cancel.config(text='关闭', state='normal')

    def _on_next(self):
        idx = self.nb.index('current')
        if idx == 0:
            self.nb.select(1)
        elif idx == 1:
            self._start_install()
        elif idx == 3:
            self._finish()

    def _browse(self):
        d = filedialog.askdirectory(initialdir=self.path_var.get())
        if d:
            self.path_var.set(d)

    def _start_install(self):
        path = self.path_var.get().strip()
        if not path:
            messagebox.showerror('错误', '请选择安装路径')
            return
        self.nb.select(2)
        threading.Thread(target=self._do_install, args=(path,), daemon=True).start()

    def _do_install(self, target_dir):
        try:
            os.makedirs(target_dir, exist_ok=True)
            self._set_progress(5, '解压文件...')

            zip_bytes = get_embedded_zip_bytes()
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
                names = z.namelist()
                total = max(len(names), 1)
                for i, name in enumerate(names):
                    z.extract(name, target_dir)
                    pct = 5 + int(85 * (i + 1) / total)
                    if i % 3 == 0:
                        self._set_progress(pct, f'解压 {i+1}/{total} ...')

            self._set_progress(92, '创建快捷方式...')
            bat_path = os.path.join(target_dir, '启动.bat')
            if self.create_desktop.get():
                desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
                create_shortcut(
                    bat_path,
                    os.path.join(desktop, f'{APP_NAME}.lnk'),
                    f'{APP_NAME} - 文献智能数据获取系统',
                )
            if self.create_startmenu.get():
                start_menu = os.path.join(
                    os.environ['APPDATA'], 'Microsoft', 'Windows', 'Start Menu', 'Programs'
                )
                create_shortcut(
                    bat_path,
                    os.path.join(start_menu, f'{APP_NAME}.lnk'),
                    f'{APP_NAME} - 文献智能数据获取系统',
                )

            self._set_progress(100, '安装完成')
            self.root.after(0, lambda: self.nb.select(3))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror('安装失败', str(e)))
            self.root.after(0, lambda: self.nb.select(1))

    def _set_progress(self, value, text):
        def _u():
            self.progress['value'] = value
            self.progress_label.config(text=text)
            self._refresh_buttons()
        self.root.after(0, _u)

    def _finish(self):
        if self.launch_after.get():
            bat_path = os.path.join(self.path_var.get().strip(), '启动.bat')
            if os.path.exists(bat_path):
                subprocess.Popen(
                    ['cmd', '/c', 'start', '""', bat_path],
                    shell=True,
                    cwd=os.path.dirname(bat_path),
                )
        self.root.destroy()


if __name__ == '__main__':
    # 烟雾测试：双击安装包后内核能跑起来
    if '--selftest' in sys.argv:
        try:
            data = get_embedded_zip_bytes()
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                names = z.namelist()
            print(f'SELFTEST_OK zip_bytes={len(data)} files={len(names)} first={names[0] if names else ""}')
            sys.exit(0)
        except Exception as e:
            print(f'SELFTEST_FAIL {e}')
            sys.exit(2)

    root = tk.Tk()
    Installer(root)
    root.mainloop()