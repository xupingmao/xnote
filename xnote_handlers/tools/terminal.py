# -*- coding:utf-8 -*-
"""Web 终端后端（配合 xterm.js 使用）

页面: /tools/terminal (由 LoadInnerToolHandler 渲染 tools/terminal.html)
接口: /api/v1/tools/terminal/{action}  (仅管理员可用)
    - start  创建终端会话
    - write  写入输入（input 为标准 base64 编码的 UTF-8 文本）
    - poll   读取输出（支持服务端等待，避免频繁轮询）
    - resize 调整终端尺寸
    - kill   终止会话

底层实现按优先级自动选择:
    1. conpty: Windows 10 1809+ 的伪终端（ConPTY），完整交互能力（回显/颜色/Ctrl+C/交互式程序）
    2. pty:    Unix 的伪终端，完整交互能力
    3. pipe:   管道模式（Windows 旧版本兜底，功能受限：无回显编辑、无交互式程序）

注意:
    1. ConPTY 输出固定为 UTF-8；管道模式的输出编码为控制台 OEM 代码页（如 GBK）
    2. 会话保存在内存中，服务重启后会话失效，由前端重新创建
"""

import base64
import os
import subprocess
import threading
import time
import logging

from typing import Dict, List, Optional, Tuple

import xutils
from xutils import Storage
from xnote.core import xauth
from xutils import webutil

MAX_SESSIONS = 20
SESSION_TTL = 600.0        # 会话空闲10分钟后回收
DEAD_SESSION_TTL = 60.0    # 子进程退出后再保留60秒供前端读取尾部输出
CLEANUP_INTERVAL = 30.0
MAX_POLL_WAIT_MS = 2000

class TerminalSessionException(Exception):
    """终端会话相关异常"""
    pass

def clamp_int(value: int, min_value: int, max_value: int) -> int:
    if value < min_value:
        return min_value
    if value > max_value:
        return max_value
    return value

class TerminalSession:
    """终端会话基类，子类负责实现具体的进程 I/O"""

    def __init__(self, session_id: str, shell_name: str, cwd: str,
                 cols: int, rows: int, owner: str = ""):
        self.id = session_id
        self.shell_name = shell_name
        self.cwd = cwd
        self.cols = cols
        self.rows = rows
        self.owner = owner
        self.mode = ""           # conpty / pty / pipe
        self.encoding = "utf-8"  # 输出解码使用的编码
        self.created_time = time.time()
        self.last_active_time = time.time()
        self.running = True
        self.output_buffer: List[str] = []
        self.lock = threading.Lock()

    # ---------- 对外接口 ----------

    def write(self, text: str):
        """写入终端输入，子类实现"""
        raise NotImplementedError

    def resize(self, cols: int, rows: int):
        """调整终端尺寸，子类按需实现"""
        self.cols = clamp_int(cols, 20, 500)
        self.rows = clamp_int(rows, 5, 200)

    def close(self):
        """关闭会话并终止子进程"""
        self.running = False

    def is_running(self) -> bool:
        """子进程是否仍在运行"""
        return self.running

    # ---------- 供 reader 线程和会话管理器使用 ----------

    def touch(self):
        self.last_active_time = time.time()

    def append_output(self, text: str):
        with self.lock:
            self.output_buffer.append(text)

    def drain_output(self) -> str:
        """取出并清空累计的输出"""
        with self.lock:
            output = "".join(self.output_buffer)
            self.output_buffer = []
            return output

    def idle_time(self) -> float:
        return time.time() - self.last_active_time

    def to_dict(self) -> Storage:
        return Storage(session_id=self.id, mode=self.mode, shell=self.shell_name,
                       cwd=self.cwd, running=self.is_running())

# ---------------------------------------------------------------------------
# Windows ConPTY 实现
# ---------------------------------------------------------------------------

if xutils.is_windows():
    import ctypes
    from ctypes import wintypes

    class WinCOORD(ctypes.Structure):
        _fields_ = [("X", wintypes.SHORT), ("Y", wintypes.SHORT)]

    class WinSTARTUPINFOW(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("lpReserved", wintypes.LPWSTR),
            ("lpDesktop", wintypes.LPWSTR),
            ("lpTitle", wintypes.LPWSTR),
            ("dwX", wintypes.DWORD),
            ("dwY", wintypes.DWORD),
            ("dwXSize", wintypes.DWORD),
            ("dwYSize", wintypes.DWORD),
            ("dwXCountChars", wintypes.DWORD),
            ("dwYCountChars", wintypes.DWORD),
            ("dwFillAttribute", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD),
            ("wShowWindow", wintypes.WORD),
            ("cbReserved2", wintypes.WORD),
            ("lpReserved2", ctypes.c_void_p),
            ("hStdInput", wintypes.HANDLE),
            ("hStdOutput", wintypes.HANDLE),
            ("hStdError", wintypes.HANDLE),
        ]

    class WinSTARTUPINFOEXW(ctypes.Structure):
        _fields_ = [
            ("StartupInfo", WinSTARTUPINFOW),
            ("lpAttributeList", ctypes.c_void_p),
        ]

    class WinPROCESS_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("hProcess", wintypes.HANDLE),
            ("hThread", wintypes.HANDLE),
            ("dwProcessId", wintypes.DWORD),
            ("dwThreadId", wintypes.DWORD),
        ]

    # 参考: https://learn.microsoft.com/windows/console/creating-a-pseudoconsole-session
    WIN_PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE = 0x00020016
    WIN_EXTENDED_STARTUPINFO_PRESENT = 0x00080000
    WIN_STARTF_USESTDHANDLES = 0x00000100

    def _load_winapi() -> Optional[ctypes.WinDLL]:  # type: ignore
        try:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            if not hasattr(kernel32, "CreatePseudoConsole"):
                return None
            kernel32.CreatePipe.argtypes = [
                ctypes.POINTER(wintypes.HANDLE), ctypes.POINTER(wintypes.HANDLE),
                ctypes.c_void_p, wintypes.DWORD]
            kernel32.CreatePseudoConsole.argtypes = [
                WinCOORD, wintypes.HANDLE, wintypes.HANDLE, wintypes.DWORD,
                ctypes.POINTER(ctypes.c_void_p)]
            kernel32.ClosePseudoConsole.argtypes = [ctypes.c_void_p]
            kernel32.ResizePseudoConsole.argtypes = [ctypes.c_void_p, WinCOORD]
            kernel32.InitializeProcThreadAttributeList.argtypes = [
                ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
                ctypes.POINTER(wintypes.DWORD)]
            kernel32.UpdateProcThreadAttribute.argtypes = [
                ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p, ctypes.c_void_p,
                ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p]
            kernel32.CreateProcessW.argtypes = [
                wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.c_void_p, ctypes.c_void_p,
                wintypes.BOOL, wintypes.DWORD, ctypes.c_void_p, wintypes.LPCWSTR,
                ctypes.POINTER(WinSTARTUPINFOW), ctypes.POINTER(WinPROCESS_INFORMATION)]
            kernel32.ReadFile.argtypes = [
                wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
                ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
            kernel32.WriteFile.argtypes = [
                wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
                ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
            kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            kernel32.WaitForSingleObject.restype = wintypes.DWORD
            kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
            return kernel32
        except Exception:
            logging.exception("加载ConPTY相关的WinAPI失败")
            return None

    _kernel32 = _load_winapi()

    class ConPtySession(TerminalSession):
        """基于 ConPTY 的终端会话（Windows 10 1809+）"""

        def __init__(self, session_id: str, cmdline: str, shell_name: str, cwd: str,
                     cols: int, rows: int, owner: str = ""):
            if _kernel32 is None:
                raise TerminalSessionException("当前系统不支持ConPTY")
            self.kernel32 = _kernel32
            self.h_pcon = ctypes.c_void_p()
            self.h_input = wintypes.HANDLE()   # 写入端: 键盘输入
            self.h_output = wintypes.HANDLE()  # 读取端: 屏幕输出
            self.h_process = wintypes.HANDLE()
            self.pid = 0
            super(ConPtySession, self).__init__(session_id, shell_name, cwd, cols, rows, owner)
            self.mode = "conpty"
            self._create_pcon(cmdline, cwd)
            self.reader_thread = threading.Thread(target=self._read_loop, daemon=True,
                                                  name="term-conpty-" + session_id[:8])
            self.reader_thread.start()

        def _create_pcon(self, cmdline: str, cwd: str):
            kernel32 = self.kernel32
            h_in_read = wintypes.HANDLE()
            h_in_write = wintypes.HANDLE()
            h_out_read = wintypes.HANDLE()
            h_out_write = wintypes.HANDLE()
            if not kernel32.CreatePipe(ctypes.byref(h_in_read), ctypes.byref(h_in_write), None, 0):
                raise TerminalSessionException("创建输入管道失败")
            if not kernel32.CreatePipe(ctypes.byref(h_out_read), ctypes.byref(h_out_write), None, 0):
                raise TerminalSessionException("创建输出管道失败")
            size = WinCOORD(self.cols, self.rows)
            result = kernel32.CreatePseudoConsole(size, h_in_read, h_out_write, 0,
                                                  ctypes.byref(self.h_pcon))
            if result != 0:
                kernel32.CloseHandle(h_in_read)
                kernel32.CloseHandle(h_in_write)
                kernel32.CloseHandle(h_out_read)
                kernel32.CloseHandle(h_out_write)
                raise TerminalSessionException("CreatePseudoConsole失败: %s" % result)
            # 伪终端接管了这两个句柄
            kernel32.CloseHandle(h_in_read)
            kernel32.CloseHandle(h_out_write)
            self.h_input = h_in_write
            self.h_output = h_out_read

            attr_size = wintypes.DWORD(0)
            kernel32.InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(attr_size))
            attr_buf = ctypes.create_string_buffer(attr_size.value)
            if not kernel32.InitializeProcThreadAttributeList(attr_buf, 1, 0,
                                                              ctypes.byref(attr_size)):
                raise TerminalSessionException("InitializeProcThreadAttributeList失败")
            if not kernel32.UpdateProcThreadAttribute(
                    attr_buf, 0, ctypes.c_void_p(WIN_PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE),
                    self.h_pcon, ctypes.sizeof(ctypes.c_void_p), None, None):
                raise TerminalSessionException("UpdateProcThreadAttribute失败")

            startup_info = WinSTARTUPINFOEXW()
            startup_info.StartupInfo.cb = ctypes.sizeof(startup_info)
            # 关键: 父进程的stdout被重定向时，内核会把父进程的标准句柄复制给子进程
            # 必须显式设置 STARTF_USESTDHANDLES 且三个句柄为空，子进程才会使用伪终端
            startup_info.StartupInfo.dwFlags = WIN_STARTF_USESTDHANDLES
            startup_info.lpAttributeList = ctypes.cast(attr_buf, ctypes.c_void_p)

            proc_info = WinPROCESS_INFORMATION()
            cmdline_buf = ctypes.create_unicode_buffer(cmdline)
            if not kernel32.CreateProcessW(
                    None, cmdline_buf, None, None, False,
                    WIN_EXTENDED_STARTUPINFO_PRESENT, None,
                    cwd or None, ctypes.byref(startup_info.StartupInfo),
                    ctypes.byref(proc_info)):
                err = ctypes.get_last_error()
                self._close_handles()
                raise TerminalSessionException("CreateProcess失败: %s" % err)
            kernel32.CloseHandle(proc_info.hThread)
            self.h_process = proc_info.hProcess
            self.pid = proc_info.dwProcessId

        def _close_handles(self):
            kernel32 = self.kernel32
            if self.h_pcon:
                kernel32.ClosePseudoConsole(self.h_pcon)
                self.h_pcon = ctypes.c_void_p()
            if self.h_input:
                kernel32.CloseHandle(self.h_input)
                self.h_input = wintypes.HANDLE()
            if self.h_output:
                kernel32.CloseHandle(self.h_output)
                self.h_output = wintypes.HANDLE()
            if self.h_process:
                kernel32.CloseHandle(self.h_process)
                self.h_process = wintypes.HANDLE()

        def _read_loop(self):
            kernel32 = self.kernel32
            data = ctypes.create_string_buffer(65536)
            nread = wintypes.DWORD()
            while True:
                ok = kernel32.ReadFile(self.h_output, data, 65536, ctypes.byref(nread), None)
                if not ok or nread.value == 0:
                    break
                self.append_output(data.raw[:nread.value].decode("utf-8", errors="replace"))
            self.running = False

        def write(self, text: str):
            if not self.running or not self.h_input:
                raise TerminalSessionException("会话已关闭")
            data = text.encode("utf-8")
            written = wintypes.DWORD()
            ok = self.kernel32.WriteFile(self.h_input, data, len(data),
                                          ctypes.byref(written), None)
            if not ok:
                raise TerminalSessionException("写入输入失败")

        def resize(self, cols: int, rows: int):
            super(ConPtySession, self).resize(cols, rows)
            if self.h_pcon:
                self.kernel32.ResizePseudoConsole(self.h_pcon, WinCOORD(self.cols, self.rows))

        def is_running(self) -> bool:
            if not self.h_process:
                return False
            # WAIT_TIMEOUT 表示子进程仍在运行
            return self.kernel32.WaitForSingleObject(self.h_process, 0) == 0x102

        def close(self):
            try:
                if self.h_process:
                    self.kernel32.TerminateProcess(self.h_process, 0)
                    self.kernel32.WaitForSingleObject(self.h_process, 2000)
            finally:
                self._close_handles()
            self.running = False

def get_windows_oem_encoding() -> str:
    """Windows 管道模式下控制台的输出编码（OEM代码页，中文系统为GBK）"""
    if xutils.is_windows():
        import ctypes
        try:
            return "cp%d" % ctypes.windll.kernel32.GetOEMCP()
        except Exception:
            pass
    return "utf-8"

# ---------------------------------------------------------------------------
# Unix PTY 实现
# ---------------------------------------------------------------------------

class PtySession(TerminalSession):
    """基于 Unix pty 的终端会话"""

    def __init__(self, session_id: str, cmdline: str, shell_name: str, cwd: str,
                 cols: int, rows: int, owner: str = ""):
        import pty  # type: ignore
        import fcntl  # type: ignore
        import termios  # type: ignore
        self.pty_mod = pty  # type: ignore
        self.fcntl_mod = fcntl  # type: ignore
        self.termios_mod = termios  # type: ignore
        self.master_fd = -1
        self.process: Optional[subprocess.Popen[bytes]] = None
        super(PtySession, self).__init__(session_id, shell_name, cwd, cols, rows, owner)
        self.mode = "pty"
        self._create_pty(cmdline, cwd)
        self.reader_thread = threading.Thread(target=self._read_loop, daemon=True,
                                              name="term-pty-" + session_id[:8])
        self.reader_thread.start()

    def _set_winsize(self, fd: int, cols: int, rows: int):
        import struct
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        self.fcntl_mod.ioctl(fd, self.termios_mod.TIOCSWINSZ, winsize)  # type: ignore

    def _create_pty(self, cmdline: str, cwd: str):
        import select
        self.select_mod = select
        master_fd, slave_fd = self.pty_mod.openpty()  # type: ignore
        self.master_fd = master_fd
        self._set_winsize(slave_fd, self.cols, self.rows)
        env = dict(os.environ)
        env["TERM"] = "xterm-256color"
        self.process = subprocess.Popen(
            [cmdline], stdin=slave_fd, stdout=slave_fd, stderr=slave_fd,
            cwd=cwd or None, env=env, start_new_session=True, close_fds=True)
        os.close(slave_fd)

    def _read_loop(self):
        if self.process is None:
            return
        process = self.process
        while True:
            try:
                result = self.select_mod.select([self.master_fd], [], [], 0.2)
                if not result[0]:
                    if process.poll() is not None and not self._has_pending_output():
                        break
                    continue
                data = os.read(self.master_fd, 65536)
                if not data:
                    break
                self.append_output(data.decode("utf-8", errors="replace"))
            except OSError:
                break
        self.running = False

    def _has_pending_output(self) -> bool:
        with self.lock:
            return len(self.output_buffer) > 0

    def write(self, text: str):
        if not self.running or self.master_fd < 0:
            raise TerminalSessionException("会话已关闭")
        data = text.encode("utf-8")
        while data:
            n = os.write(self.master_fd, data)
            data = data[n:]

    def resize(self, cols: int, rows: int):
        super(PtySession, self).resize(cols, rows)
        if self.master_fd >= 0:
            self._set_winsize(self.master_fd, self.cols, self.rows)

    def is_running(self) -> bool:
        if self.process is None:
            return False
        if self.process.poll() is not None:
            return False
        return True

    def close(self):
        import signal
        self.running = False
        try:
            if self.process is not None and self.process.poll() is None:
                # 新会话组长，可以kill整个进程组
                try:
                    os.killpg(self.process.pid, signal.SIGTERM)
                except OSError:
                    self.process.terminate()
                try:
                    self.process.wait(2)
                except Exception:
                    try:
                        os.killpg(self.process.pid, signal.SIGKILL)
                    except OSError:
                        self.process.kill()
        finally:
            if self.master_fd >= 0:
                try:
                    os.close(self.master_fd)
                except OSError:
                    pass
                self.master_fd = -1

# ---------------------------------------------------------------------------
# 管道模式（兜底实现，功能受限）
# ---------------------------------------------------------------------------

class PipeSession(TerminalSession):
    """基于管道的终端会话（兜底方案，无伪终端，交互能力受限）"""

    def __init__(self, session_id: str, cmdline: str, shell_name: str, cwd: str,
                 cols: int, rows: int, owner: str = ""):
        self.process: Optional[subprocess.Popen[bytes]] = None
        super(PipeSession, self).__init__(session_id, shell_name, cwd, cols, rows, owner)
        self.mode = "pipe"
        self.encoding = get_windows_oem_encoding()
        self.process = subprocess.Popen(
            [cmdline], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, cwd=cwd or None)
        self.reader_thread = threading.Thread(target=self._read_loop, daemon=True,
                                              name="term-pipe-" + session_id[:8])
        self.reader_thread.start()

    def _read_loop(self):
        if self.process is None or self.process.stdout is None:
            return
        stdout = self.process.stdout
        while True:
            try:
                data = stdout.read1(65536)
            except (ValueError, OSError):
                break
            if not data:
                break
            self.append_output(data.decode(self.encoding, errors="replace"))
        self.running = False

    def write(self, text: str):
        if not self.running or self.process is None or self.process.stdin is None:
            raise TerminalSessionException("会话已关闭")
        # 管道模式下行结束符必须是 \r\n
        text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")
        data = text.encode(self.encoding, errors="replace")
        stdin = self.process.stdin
        try:
            stdin.write(data)
            stdin.flush()
        except (OSError, ValueError):
            raise TerminalSessionException("写入输入失败")

    def is_running(self) -> bool:
        if self.process is None:
            return False
        return self.process.poll() is None

    def close(self):
        self.running = False
        if self.process is None:
            return
        try:
            self.process.kill()
            self.process.wait(2)
        except Exception:
            pass

# ---------------------------------------------------------------------------
# 会话工厂与管理器
# ---------------------------------------------------------------------------

def resolve_shell(shell: str) -> Tuple[str, str]:
    """返回 (可读名称, 命令行)"""
    shell = shell.lower().strip()
    if xutils.is_windows():
        if shell in ("", "cmd"):
            return "cmd", "cmd.exe"
        if shell == "powershell":
            return "powershell", "powershell.exe"
        # 其他命令原样执行
        return shell, shell
    else:
        if shell in ("", "bash"):
            return "bash", "/bin/bash"
        if shell == "zsh":
            return "zsh", "/bin/zsh"
        if shell == "sh":
            return "sh", "/bin/sh"
        return shell, shell

def create_terminal_session(session_id: str, shell: str, cwd: str,
                            cols: int, rows: int, owner: str) -> TerminalSession:
    """创建终端会话，按平台选择最优实现，失败时降级到管道模式"""
    shell_name, cmdline = resolve_shell(shell)
    if xutils.is_windows() and _kernel32 is not None:
        try:
            return ConPtySession(session_id, cmdline, shell_name, cwd, cols, rows, owner)
        except TerminalSessionException:
            logging.exception("创建ConPTY会话失败，降级到管道模式")
    if not xutils.is_windows():
        try:
            return PtySession(session_id, cmdline, shell_name, cwd, cols, rows, owner)
        except (OSError, ImportError) as e:
            logging.exception("创建PTY会话失败，降级到管道模式: %s", e)
    return PipeSession(session_id, cmdline, shell_name, cwd, cols, rows, owner)

class TerminalSessionManager:
    """终端会话管理器"""

    def __init__(self):
        self.sessions: Dict[str, TerminalSession] = {}
        self.lock = threading.Lock()
        self.cleanup_started = False

    def _ensure_cleanup_thread(self):
        if self.cleanup_started:
            return
        self.cleanup_started = True
        thread = threading.Thread(target=self._cleanup_loop, daemon=True,
                                  name="term-session-cleaner")
        thread.start()

    def _cleanup_loop(self):
        while True:
            time.sleep(CLEANUP_INTERVAL)
            try:
                self.sweep()
            except Exception:
                logging.exception("清理终端会话失败")

    def sweep(self):
        """回收空闲/退出的会话"""
        with self.lock:
            session_ids = list(self.sessions.keys())
        for session_id in session_ids:
            session = self.sessions.get(session_id)
            if session is None:
                continue
            running = False
            try:
                running = session.is_running()
            except Exception:
                pass
            if session.idle_time() > SESSION_TTL:
                logging.info("终端会话(%s)空闲超时，自动关闭", session_id)
                self.remove(session_id)
            elif not running and session.idle_time() > DEAD_SESSION_TTL:
                logging.info("终端会话(%s)已退出，自动回收", session_id)
                self.remove(session_id)

    def create_session(self, shell: str, cwd: str, cols: int, rows: int,
                       owner: str) -> TerminalSession:
        session_id = xutils.create_uuid()
        session = create_terminal_session(session_id, shell, cwd, cols, rows, owner)
        with self.lock:
            # 超过最大会话数时关闭最早创建的会话
            if len(self.sessions) >= MAX_SESSIONS:
                oldest_id = None
                oldest_time = None
                for key, item in self.sessions.items():
                    if oldest_time is None or item.created_time < oldest_time:
                        oldest_time = item.created_time
                        oldest_id = key
                if oldest_id is not None:
                    self.remove(oldest_id)
            self.sessions[session_id] = session
        self._ensure_cleanup_thread()
        return session

    def get_session(self, session_id: str, owner: str = "") -> Optional[TerminalSession]:
        with self.lock:
            session = self.sessions.get(session_id)
            if session is None:
                return None
            if owner and session.owner and session.owner != owner:
                return None
            session.touch()
            return session

    def remove(self, session_id: str):
        """删除并关闭会话"""
        with self.lock:
            session = self.sessions.pop(session_id, None)
        if session is None:
            return
        try:
            session.close()
        except Exception:
            logging.exception("关闭终端会话(%s)失败", session_id)

    def close_all(self):
        """关闭并清空全部会话"""
        with self.lock:
            sessions = list(self.sessions.values())
            self.sessions = {}
        _close_session_list(sessions)

    def get_count(self) -> int:
        with self.lock:
            return len(self.sessions)

_SESSION_MANAGER = TerminalSessionManager()

def get_session_manager() -> TerminalSessionManager:
    return _SESSION_MANAGER

def _close_session_list(sessions: List[TerminalSession]):
    for session in sessions:
        try:
            session.close()
        except Exception:
            logging.exception("关闭终端会话失败")

def unload():
    """handlers重载时清理所有终端会话"""
    _SESSION_MANAGER.close_all()

# ---------------------------------------------------------------------------
# HTTP 接口
# ---------------------------------------------------------------------------

class TerminalApiHandler:
    """Web终端会话接口，仅管理员可用"""

    @xauth.login_required("admin")
    def GET(self, action: str = ""):
        return self.dispatch(action)

    @xauth.login_required("admin")
    def POST(self, action: str = ""):
        return self.dispatch(action)

    def dispatch(self, action: str):
        manager = get_session_manager()
        if action == "start":
            return self.handle_start(manager)
        if action == "write":
            return self.handle_write(manager)
        if action == "poll":
            return self.handle_poll(manager)
        if action == "resize":
            return self.handle_resize(manager)
        if action == "kill":
            return self.handle_kill(manager)
        return webutil.FailedResult(code="404", message="未知的操作: %s" % action)

    def handle_start(self, manager: TerminalSessionManager):
        shell = xutils.get_argument_str("shell", "")
        cwd = xutils.get_argument_str("cwd", "")
        cols = clamp_int(xutils.get_argument_int("cols", 80), 20, 500)
        rows = clamp_int(xutils.get_argument_int("rows", 24), 5, 200)
        if cwd != "" and not os.path.isdir(cwd):
            return webutil.FailedResult(code="400", message="目录不存在: %s" % cwd)
        owner = xauth.current_name_str()
        try:
            session = manager.create_session(shell, cwd, cols, rows, owner)
        except TerminalSessionException as e:
            return webutil.FailedResult(code="500", message=str(e))
        except Exception as e:
            xutils.print_exc()
            return webutil.FailedResult(code="500", message="创建终端会话失败: %s" % e)
        return webutil.SuccessResult(data=session.to_dict())

    def get_session(self, manager: TerminalSessionManager) -> Optional[TerminalSession]:
        session_id = xutils.get_argument_str("session_id")
        if session_id == "":
            return None
        return manager.get_session(session_id, xauth.current_name_str())

    def handle_write(self, manager: TerminalSessionManager):
        session = self.get_session(manager)
        if session is None:
            return webutil.FailedResult(code="404", message="会话不存在")
        input_b64 = xutils.get_argument_str("input")
        try:
            text = base64.b64decode(input_b64).decode("utf-8")
        except Exception:
            return webutil.FailedResult(code="400", message="base64解码失败")
        if text == "":
            return webutil.SuccessResult()
        try:
            session.write(text)
        except TerminalSessionException as e:
            return webutil.FailedResult(code="410", message=str(e))
        return webutil.SuccessResult()

    def handle_poll(self, manager: TerminalSessionManager):
        session = self.get_session(manager)
        if session is None:
            return webutil.FailedResult(code="404", message="会话不存在")
        wait_ms = clamp_int(xutils.get_argument_int("wait_ms", 200), 0, MAX_POLL_WAIT_MS)
        deadline = time.time() + wait_ms / 1000.0
        output = ""
        running = True
        while True:
            output = session.drain_output()
            running = session.is_running()
            if output != "" or not running or time.time() >= deadline:
                break
            time.sleep(0.05)
        return webutil.SuccessResult(data=Storage(output=output, running=running))

    def handle_resize(self, manager: TerminalSessionManager):
        session = self.get_session(manager)
        if session is None:
            return webutil.FailedResult(code="404", message="会话不存在")
        cols = clamp_int(xutils.get_argument_int("cols", 80), 20, 500)
        rows = clamp_int(xutils.get_argument_int("rows", 24), 5, 200)
        try:
            session.resize(cols, rows)
        except Exception:
            xutils.print_exc()
            return webutil.FailedResult(code="500", message="调整尺寸失败")
        return webutil.SuccessResult()

    def handle_kill(self, manager: TerminalSessionManager):
        session_id = xutils.get_argument_str("session_id")
        if session_id == "":
            return webutil.FailedResult(code="400", message="session_id不能为空")
        session = manager.get_session(session_id, xauth.current_name_str())
        if session is None:
            # 会话不存在视为成功，保证幂等
            return webutil.SuccessResult()
        manager.remove(session_id)
        return webutil.SuccessResult()

xurls = (
    r"/api/v1/tools/terminal/(\w+)", TerminalApiHandler,
)
