# -*- coding: utf-8 -*-
"""后台任务管理器。

Streamlit 每次页面切换/交互都会重新运行脚本，脚本内的耗时循环会随切换被丢弃。
本模块用"模块级单例 + 独立线程"解决该问题：
- 任务在独立线程中运行，与页面脚本无关，切换页面不会中断；
- 任务对象记录进度/日志/结果，任何页面随时读取状态；
- 页面端只需短间隔轮询刷新显示即可。
"""
import threading
import time
import uuid


class TaskCancelled(Exception):
    """任务被用户取消。"""


class Task:
    """一个后台任务的运行状态。"""

    def __init__(self, name: str):
        self.id = uuid.uuid4().hex[:8]
        self.name = name
        self.status = "running"          # running / done / failed / cancelled
        self.progress = 0.0              # 0~1
        self.status_text = ""
        self.log = []                    # list[dict]，任务过程日志/结果行
        self.result = None               # 任务返回值
        self.error = None
        self.cancel_flag = False
        self.created_at = time.time()
        self.finished_at = None
        self._lock = threading.Lock()

    def set_progress(self, fraction, text: str = ""):
        with self._lock:
            try:
                self.progress = max(0.0, min(1.0, float(fraction or 0)))
            except (TypeError, ValueError):
                pass
            if text:
                self.status_text = str(text)

    def add_log(self, entry: dict):
        with self._lock:
            self.log.append(entry)

    def check_cancel(self):
        """任务函数在合适的时机调用；已取消则抛出 TaskCancelled。"""
        if self.cancel_flag:
            raise TaskCancelled("任务已被用户取消")

    def cancel(self):
        self.cancel_flag = True

    @property
    def done(self) -> bool:
        return self.status != "running"


class TaskManager:
    """任务注册表。作为模块级单例使用，跨 Streamlit rerun 存活。"""

    def __init__(self, max_keep: int = 20):
        self._tasks = {}
        self._lock = threading.Lock()
        self.max_keep = max_keep

    def submit(self, name: str, fn, *args, **kwargs) -> Task:
        """提交后台任务：fn(task, *args, **kwargs) 在新线程中运行。"""
        task = Task(name)
        with self._lock:
            self._tasks[task.id] = task
            # 只保留最近 max_keep 个（已结束的）任务，避免无限增长
            if len(self._tasks) > self.max_keep:
                for tid in list(self._tasks.keys()):
                    if len(self._tasks) <= self.max_keep:
                        break
                    if self._tasks[tid].done:
                        del self._tasks[tid]

        def _runner():
            try:
                task.result = fn(task, *args, **kwargs)
                task.status = "cancelled" if task.cancel_flag else "done"
            except TaskCancelled:
                task.status = "cancelled"
                task.status_text = "已取消"
            except Exception as ex:  # noqa: BLE001
                task.status = "failed"
                task.error = str(ex)
                task.status_text = f"失败：{ex}"
            finally:
                task.finished_at = time.time()

        threading.Thread(target=_runner, daemon=True,
                         name=f"bg-task-{task.id}").start()
        return task

    def get(self, task_id: str):
        with self._lock:
            return self._tasks.get(task_id)

    def running(self) -> list:
        with self._lock:
            return [t for t in self._tasks.values() if t.status == "running"]

    def finished_unclaimed(self, claimed: set) -> list:
        """已结束且尚未被页面领取结果的任务（claimed 为已领取任务ID集合）。"""
        with self._lock:
            return [t for t in self._tasks.values()
                    if t.status != "running" and t.id not in (claimed or set())]


# 模块级单例：Streamlit 脚本每次 rerun 都拿到同一个实例
MANAGER = TaskManager()
