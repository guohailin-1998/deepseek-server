import tkinter as tk
from tkinter import scrolledtext, messagebox, simpledialog, filedialog
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import threading
import json
import os
import requests
from datetime import datetime
from openai import OpenAI

# ---------- 配置 ----------
CONFIG_FILE = "config.json"          # 保存 API Key
TOKEN_FILE = "token.json"            # 保存 JWT token
BACKEND_URL = "https://你的后端地址.railway.app"   # 部署后替换成真实地址

class LoginWindow(tb.Toplevel):
    """登录/注册窗口"""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("登录 / 注册")
        self.geometry("350x300")
        self.resizable(False, False)
        self.parent = parent
        self.token = None
        self.username = None

        frame = tb.Frame(self, padding=20)
        frame.pack(fill=BOTH, expand=True)

        tb.Label(frame, text="用户名：").pack(anchor=W, pady=5)
        self.username_entry = tb.Entry(frame, font=("微软雅黑", 10))
        self.username_entry.pack(fill=X, pady=3)

        tb.Label(frame, text="密码：").pack(anchor=W, pady=5)
        self.password_entry = tb.Entry(frame, show="*", font=("微软雅黑", 10))
        self.password_entry.pack(fill=X, pady=3)

        btn_frame = tb.Frame(frame)
        btn_frame.pack(fill=X, pady=15)
        tb.Button(btn_frame, text="登录", bootstyle=SUCCESS, command=self.do_login).pack(side=LEFT, expand=True, fill=X, padx=5)
        tb.Button(btn_frame, text="注册", bootstyle=PRIMARY, command=self.do_register).pack(side=RIGHT, expand=True, fill=X, padx=5)

        self.status_label = tb.Label(frame, text="", foreground="gray")
        self.status_label.pack()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def do_login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        if not username or not password:
            self.status_label.config(text="请输入用户名和密码")
            return
        try:
            resp = requests.post(f"{BACKEND_URL}/api/login", json={"username": username, "password": password})
            data = resp.json()
            if resp.status_code == 200:
                self.token = data.get("token")
                self.username = username
                self.status_label.config(text="登录成功")
                self.parent.on_login_success(username, self.token, data.get("member_expire"))
                self.destroy()
            else:
                self.status_label.config(text=data.get("msg", "登录失败"))
        except Exception as e:
            self.status_label.config(text=f"网络错误: {e}")

    def do_register(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        if not username or not password:
            self.status_label.config(text="请输入用户名和密码")
            return
        if len(password) < 6:
            self.status_label.config(text="密码至少6位")
            return
        try:
            resp = requests.post(f"{BACKEND_URL}/api/register", json={"username": username, "password": password})
            data = resp.json()
            if resp.status_code == 201:
                self.status_label.config(text="注册成功，请登录")
            else:
                self.status_label.config(text=data.get("msg", "注册失败"))
        except Exception as e:
            self.status_label.config(text=f"网络错误: {e}")

    def on_close(self):
        self.parent.on_login_close()


class DeepSeekChatPro:
    def __init__(self, root):
        self.root = root
        self.root.withdraw()   # 先隐藏主窗口，登录后再显示

        self.token = None
        self.username = None
        self.member_expire = None
        self.messages = []
        self.api_key = ""
        self.client = None

        # 尝试从本地加载 token
        self.load_token()
        if self.token and self.check_token():
            self.init_ui()
            self.root.deiconify()
            return

        # 打开登录窗口
        self.root.after(100, self.show_login)

    def show_login(self):
        LoginWindow(self.root)

    def load_token(self):
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "r") as f:
                data = json.load(f)
                self.token = data.get("token")
                self.username = data.get("username")

    def save_token(self):
        with open(TOKEN_FILE, "w") as f:
            json.dump({"token": self.token, "username": self.username}, f)

    def check_token(self):
        try:
            resp = requests.get(f"{BACKEND_URL}/api/user/info",
                                headers={"Authorization": f"Bearer {self.token}"})
            if resp.status_code == 200:
                data = resp.json()
                self.member_expire = data.get("member_expire")
                return True
        except:
            pass
        return False

    def on_login_success(self, username, token, member_expire):
        self.username = username
        self.token = token
        self.member_expire = member_expire
        self.save_token()
        self.init_ui()
        self.root.deiconify()

    def on_login_close(self):
        if not self.token:
            self.root.destroy()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                self.api_key = data.get("api_key", "")
        else:
            self.api_key = ""

    def save_config(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump({"api_key": self.api_key}, f)

    def update_client(self):
        if self.api_key and self.api_key.strip():
            try:
                self.client = OpenAI(api_key=self.api_key.strip(), base_url="https://api.deepseek.com/v1")
                self.status_var.set("已连接 DeepSeek API")
            except Exception as e:
                self.status_var.set(f"客户端创建失败: {e}")
                self.client = None
        else:
            self.client = None
            self.status_var.set("请设置 API Key")

    def init_ui(self):
        self.style = tb.Style(theme="flatly")
        self.root.title(f"DeepSeek 聊天助手 Pro - {self.username}")
        self.root.geometry("800x650")

        toolbar = tb.Frame(self.root, padding=5)
        toolbar.pack(side=TOP, fill=X)

        tb.Button(toolbar, text="⚙ API Key", bootstyle=(OUTLINE, SECONDARY), command=self.open_settings).pack(side=LEFT, padx=5)
        tb.Button(toolbar, text="🗑 清除对话", bootstyle=(OUTLINE, DANGER), command=self.clear_chat).pack(side=LEFT, padx=5)
        tb.Button(toolbar, text="💾 保存对话", bootstyle=(OUTLINE, INFO), command=self.save_chat).pack(side=LEFT, padx=5)
        tb.Button(toolbar, text="🌟 激活会员", bootstyle=(OUTLINE, WARNING), command=self.activate_member).pack(side=LEFT, padx=5)

        self.member_label_var = tk.StringVar()
        self.update_member_label()
        tb.Label(toolbar, textvariable=self.member_label_var, font=("微软雅黑", 9), foreground="green").pack(side=RIGHT, padx=10)

        self.status_var = tk.StringVar(value="就绪")
        tb.Label(toolbar, textvariable=self.status_var, font=("微软雅黑", 9)).pack(side=RIGHT, padx=10)

        chat_frame = tb.Frame(self.root, padding=(10, 5))
        chat_frame.pack(fill=BOTH, expand=True)

        self.chat_display = scrolledtext.ScrolledText(
            chat_frame, state='disabled', wrap=tk.WORD,
            font=("微软雅黑", 10), bg=self.style.colors.get("light"))
        self.chat_display.pack(fill=BOTH, expand=True)

        self.chat_display.tag_config("user", foreground="#ffffff", background="#0d6efd", font=("微软雅黑", 10, "bold"))
        self.chat_display.tag_config("ai", foreground="#212529", background="#f8f9fa", font=("微软雅黑", 10))
        self.chat_display.tag_config("system", foreground="#6c757d", font=("微软雅黑", 9, "italic"))

        input_frame = tb.Frame(self.root, padding=(10, 5))
        input_frame.pack(fill=X, side=BOTTOM)

        self.input_field = tk.Text(input_frame, height=4, font=("微软雅黑", 10), wrap=tk.WORD)
        self.input_field.pack(side=LEFT, fill=BOTH, expand=True)
        self.input_field.bind("<Control-Return>", self.send_message_event)
        self.input_field.bind("<Return>", lambda e: None)

        tb.Button(input_frame, text="发送", bootstyle=SUCCESS, command=self.send_message).pack(side=RIGHT, padx=(10, 0))

        tb.Label(self.root, text=" Ctrl+Enter 发送 | Enter 换行 ", relief=SUNKEN, anchor=tk.W, font=("微软雅黑", 8)).pack(side=BOTTOM, fill=X)

        self.load_config()
        self.update_client()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def update_member_label(self):
        if self.member_expire:
            try:
                expire_date = datetime.strptime(self.member_expire, '%Y-%m-%d')
                if expire_date >= datetime.now():
                    self.member_label_var.set(f"会员到期：{self.member_expire}")
                else:
                    self.member_label_var.set("会员已过期")
            except:
                self.member_label_var.set("")
        else:
            self.member_label_var.set("未开通会员")

    def open_settings(self):
        win = tb.Toplevel(self.root)
        win.title("API Key 设置")
        win.geometry("450x200")
        win.transient(self.root)
        win.grab_set()
        frame = tb.Frame(win, padding=20)
        frame.pack(fill=BOTH, expand=True)

        tb.Label(frame, text="DeepSeek API Key：").pack(anchor=tk.W, pady=5)
        key_entry = tb.Entry(frame, show="*", font=("Consolas", 10))
        key_entry.pack(fill=X, pady=5)
        key_entry.insert(0, self.api_key)

        def save_key():
            new_key = key_entry.get().strip()
            if new_key:
                self.api_key = new_key
                self.save_config()
                self.update_client()
                win.destroy()
                messagebox.showinfo("提示", "API Key 已保存")
            else:
                messagebox.showwarning("提示", "Key 不能为空")

        btn_frame = tb.Frame(frame)
        btn_frame.pack(fill=X, pady=15)
        tb.Button(btn_frame, text="保存", bootstyle=SUCCESS, command=save_key).pack(side=RIGHT, padx=5)
        tb.Button(btn_frame, text="取消", bootstyle=SECONDARY, command=win.destroy).pack(side=RIGHT)

    def clear_chat(self):
        if messagebox.askyesno("确认", "确定要清除所有对话记录吗？"):
            self.messages.clear()
            self.chat_display.config(state=NORMAL)
            self.chat_display.delete("1.0", END)
            self.chat_display.config(state=DISABLED)

    def save_chat(self):
        content = self.chat_display.get("1.0", END).strip()
        if not content:
            messagebox.showinfo("提示", "没有对话内容")
            return
        filename = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = filedialog.asksaveasfilename(defaultextension=".txt", initialfile=filename)
        if filepath:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("成功", f"已保存到：{filepath}")

    def activate_member(self):
        code = simpledialog.askstring("激活会员", "请输入激活码：")
        if not code:
            return
        try:
            resp = requests.post(f"{BACKEND_URL}/api/member/activate",
                                 headers={"Authorization": f"Bearer {self.token}"},
                                 json={"code": code})
            data = resp.json()
            if resp.status_code == 200:
                self.member_expire = data.get("member_expire")
                self.update_member_label()
                messagebox.showinfo("成功", data.get("msg", "激活成功"))
            else:
                messagebox.showerror("失败", data.get("msg", "激活失败"))
        except Exception as e:
            messagebox.showerror("错误", f"请求失败: {e}")

    def send_message_event(self, event=None):
        self.send_message()
        return "break"

    def send_message(self):
        if not self.client:
            messagebox.showwarning("提示", "请先设置 API Key")
            return

        # 检查会员
        try:
            resp = requests.get(f"{BACKEND_URL}/api/member/check",
                                headers={"Authorization": f"Bearer {self.token}"})
            if resp.status_code == 200:
                data = resp.json()
                is_member = data.get("is_member", False)
                if not is_member:
                    messagebox.showwarning("提示", "您的会员已过期，请续费激活")
                    return
        except:
            messagebox.showwarning("错误", "网络问题，无法检查会员状态")
            return

        user_text = self.input_field.get("1.0", END).strip()
        if not user_text:
            return

        self.input_field.delete("1.0", END)
        self.display_message("你", user_text, "user")
        self.messages.append({"role": "user", "content": user_text})

        self.input_field.config(state=DISABLED)
        self.status_var.set("DeepSeek 思考中...")
        self.display_message("DeepSeek", "", "ai")   # 占位

        thread = threading.Thread(target=self.call_deepseek_api_stream, daemon=True)
        thread.start()

    def call_deepseek_api_stream(self):
        full_response = ""
        try:
            stream = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=self.messages,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    self.root.after(0, self.update_stream_message, content)
            self.messages.append({"role": "assistant", "content": full_response})
        except Exception as e:
            error_msg = f"请求出错: {e}"
            self.root.after(0, self.replace_last_ai_message, error_msg, "系统")
            if self.messages and self.messages[-1]["role"] == "user":
                self.messages.pop()
        finally:
            self.root.after(0, self.enable_input)

    def update_stream_message(self, text):
        self.chat_display.config(state=NORMAL)
        self.chat_display.insert(END, text, "ai")
        self.chat_display.see(END)
        self.chat_display.config(state=DISABLED)

    def replace_last_ai_message(self, text, tag):
        self.chat_display.config(state=NORMAL)
        last_line_start = self.chat_display.index("end-2l")
        self.chat_display.delete(last_line_start, END)
        self.display_message("系统", text, tag)
        self.chat_display.config(state=DISABLED)

    def display_message(self, sender, message, tag):
        self.chat_display.config(state=NORMAL)
        self.chat_display.insert(END, f"{sender}: ", (f"{tag}_bold",))
        self.chat_display.insert(END, f"{message}\n\n", tag)
        self.chat_display.see(END)
        self.chat_display.config(state=DISABLED)

    def enable_input(self):
        self.input_field.config(state=NORMAL)
        self.input_field.focus_set()
        self.status_var.set("就绪")

    def on_close(self):
        self.root.destroy()


if __name__ == "__main__":
    root = tb.Window(themename="flatly")
    app = DeepSeekChatPro(root)
    root.mainloop()