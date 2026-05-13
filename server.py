import sys
import tkinter as tk
from tkinter import scrolledtext, messagebox, simpledialog, filedialog
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import threading
import json
import os
import requests
from datetime import datetime

BACKEND_URL = "https://deepseek-server-bcrf.onrender.com"

CONFIG_FILE = "config.json"
TOKEN_FILE = "token.json"

PLANS = {
    "30天": 30,
    "90天": 90,
    "365天": 365
}

class LoginWindow(tb.Toplevel):
    def __init__(self, app):
        super().__init__(app.root)
        self.title("欢迎回来")
        self.geometry("360x340")
        self.resizable(False, False)
        self.app = app
        self.token = None
        self.username = None

        self.configure(bg="#343541")
        frame = tb.Frame(self, padding=30)
        frame.pack(expand=True)

        tb.Label(frame, text="👤 用户名", font=("微软雅黑", 10, "bold"),
                 foreground="#fff", background="#343541").pack(anchor=W, pady=(10, 2))
        self.username_entry = tb.Entry(frame, font=("微软雅黑", 11), width=25)
        self.username_entry.pack(ipady=3)

        tb.Label(frame, text="🔒 密码", font=("微软雅黑", 10, "bold"),
                 foreground="#fff", background="#343541").pack(anchor=W, pady=(10, 2))
        self.password_entry = tb.Entry(frame, show="•", font=("微软雅黑", 11), width=25)
        self.password_entry.pack(ipady=3)

        btn_frame = tb.Frame(frame)
        btn_frame.pack(fill=X, pady=20)
        self.login_btn = tb.Button(btn_frame, text="登录", bootstyle=(SUCCESS, OUTLINE), command=self.do_login, width=12)
        self.login_btn.pack(side=LEFT, padx=5)
        self.reg_btn = tb.Button(btn_frame, text="注册", bootstyle=(PRIMARY, OUTLINE), command=self.do_register, width=12)
        self.reg_btn.pack(side=RIGHT, padx=5)

        self.status_label = tb.Label(frame, text="", foreground="#aaa", background="#343541", font=("微软雅黑", 9))
        self.status_label.pack(pady=5)

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
                self.app.on_login_success(username, self.token, data.get("member_expire"))
                self.destroy()
            else:
                self.status_label.config(text=data.get("msg", "登录失败"))
        except Exception as e:
            self.status_label.config(text=f"网络错误：{e}")

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
            self.status_label.config(text=f"网络错误：{e}")

    def on_close(self):
        self.app.on_login_close()


class DeepSeekChatPro:
    def __init__(self, root):
        self.root = root
        self.root.withdraw()

        self.token = None
        self.username = None
        self.member_expire = None
        self.messages = []

        self.load_token()
        if self.token and self.check_token():
            self.init_ui()
            self.root.deiconify()
            return

        self.root.after(100, self.show_login)

    def show_login(self):
        LoginWindow(self)

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

    def init_ui(self):
        self.style = tb.Style(theme="darkly")
        self.style.configure("TButton", borderwidth=0, focusthickness=0, relief="flat")
        self.style.map("TButton",
                       background=[("active", "#50535c"), ("pressed", "#30323a")])
        self.style.configure("primary.TButton", font=("微软雅黑", 9, "bold"), borderradius=8)
        self.style.configure("success.TButton", font=("微软雅黑", 9, "bold"), borderradius=8)
        self.style.configure("warning.TButton", font=("微软雅黑", 9, "bold"), borderradius=8)
        self.style.configure("danger.TButton", font=("微软雅黑", 9, "bold"), borderradius=8)

        self.root.title(f"DeepSeek Chat - {self.username}")
        self.root.geometry("860x680")
        self.root.minsize(600, 500)

        toolbar = tb.Frame(self.root, padding=(10, 8), bootstyle="dark")
        toolbar.pack(fill=X)

        tb.Button(toolbar, text="🗑 清空对话", bootstyle=(OUTLINE, DANGER), command=self.clear_chat).pack(side=LEFT, padx=3)
        tb.Button(toolbar, text="💾 保存记录", bootstyle=(OUTLINE, INFO), command=self.save_chat).pack(side=LEFT, padx=3)
        tb.Button(toolbar, text="🌟 会员激活", bootstyle=(OUTLINE, WARNING), command=self.activate_member).pack(side=LEFT, padx=3)
        tb.Button(toolbar, text="👤 个人中心", bootstyle=(OUTLINE, SECONDARY), command=self.show_profile).pack(side=LEFT, padx=3)

        self.member_label_var = tk.StringVar()
        self.update_member_label()
        tb.Label(toolbar, textvariable=self.member_label_var, font=("微软雅黑", 9),
                 foreground="#10a37f", background="#212529").pack(side=RIGHT, padx=10)

        chat_frame = tb.Frame(self.root, padding=(10, 5))
        chat_frame.pack(fill=BOTH, expand=True)

        self.chat_display = scrolledtext.ScrolledText(
            chat_frame, state='disabled', wrap=tk.WORD,
            font=("微软雅黑", 10), bg="#2b2d31", fg="#e0e0e0",
            insertbackground="white", relief=FLAT, borderwidth=0, highlightthickness=0)
        self.chat_display.pack(fill=BOTH, expand=True)

        self.chat_display.tag_config("user", foreground="#fff", background="#0d7377",
                                     font=("微软雅黑", 10, "bold"), lmargin1=20, lmargin2=20,
                                     spacing1=5, spacing3=5)
        self.chat_display.tag_config("ai", foreground="#e0e0e0", background="#3a3d42",
                                     font=("微软雅黑", 10), lmargin1=20, lmargin2=20,
                                     spacing1=5, spacing3=5)
        self.chat_display.tag_config("system", foreground="#888", font=("微软雅黑", 9, "italic"))

        input_frame = tb.Frame(self.root, padding=(10, 10), bootstyle="dark")
        input_frame.pack(fill=X, side=BOTTOM)

        self.input_field = tk.Text(input_frame, height=3, font=("微软雅黑", 11),
                                   wrap=tk.WORD, relief=FLAT, bg="#40414f", fg="#fff",
                                   insertbackground="white", padx=10, pady=8,
                                   borderwidth=0, highlightthickness=0)
        self.input_field.pack(side=LEFT, fill=BOTH, expand=True)
        self.input_field.bind("<Return>", self.send_message_event)
        self.input_field.bind("<Shift-Return>", lambda e: None)

        send_btn = tb.Button(input_frame, text="发送", bootstyle=SUCCESS, command=self.send_message, width=8)
        send_btn.pack(side=RIGHT, padx=(10, 0))

        self.status_var = tk.StringVar(value="就绪")
        status_bar = tb.Label(self.root, textvariable=self.status_var, anchor=W,
                              font=("微软雅黑", 8), padding=(10, 3),
                              background="#212529", foreground="#aaa")
        status_bar.pack(fill=X, side=BOTTOM)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def update_member_label(self):
        if self.member_expire:
            try:
                expire_date = datetime.strptime(self.member_expire, '%Y-%m-%d')
                days_left = (expire_date - datetime.now()).days
                if days_left > 0:
                    self.member_label_var.set(f"✨ 会员剩余 {days_left} 天")
                else:
                    self.member_label_var.set("⚠️ 会员已过期")
            except:
                self.member_label_var.set("状态异常")
        else:
            self.member_label_var.set("未开通会员")

    def show_profile(self):
        win = tb.Toplevel(self.root)
        win.title("个人中心")
        win.geometry("320x300")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        win.configure(bg="#2b2d31")
        frame = tb.Frame(win, padding=20, bootstyle="dark")
        frame.pack(fill=BOTH, expand=True)

        tb.Label(frame, text=f"👤 用户名：{self.username}", font=("微软雅黑", 11),
                 foreground="#fff", background="#2b2d31").pack(anchor=W, pady=5)

        if self.member_expire:
            try:
                expire_date = datetime.strptime(self.member_expire, '%Y-%m-%d')
                days_left = (expire_date - datetime.now()).days
                if days_left > 0:
                    status = f"✨ 有效期至：{self.member_expire}（剩余 {days_left} 天）"
                    color = "#10a37f"
                else:
                    status = "⚠️ 已过期"
                    color = "#ff6b6b"
            except:
                status = "状态异常"
                color = "#ff6b6b"
        else:
            status = "未开通会员"
            color = "#ff6b6b"
        tb.Label(frame, text=status, font=("微软雅黑", 10), foreground=color,
                 background="#2b2d31").pack(anchor=W, pady=10)

        btn_frame = tb.Frame(frame, bootstyle="dark")
        btn_frame.pack(fill=X, pady=20)

        purchase_btn = tb.Button(btn_frame, text="购买套餐", bootstyle=(SUCCESS, OUTLINE),
                                 command=self.buy_plan_from_profile)
        purchase_btn.pack(fill=X, pady=5)

        if self.member_expire:
            try:
                expire_date = datetime.strptime(self.member_expire, '%Y-%m-%d')
                if expire_date > datetime.now():
                    renew_btn = tb.Button(btn_frame, text="续费会员", bootstyle=(WARNING, OUTLINE),
                                          command=self.buy_plan_from_profile)
                else:
                    renew_btn = tb.Button(btn_frame, text="立即续费", bootstyle=(DANGER, OUTLINE),
                                          command=self.buy_plan_from_profile)
            except:
                renew_btn = tb.Button(btn_frame, text="续费会员", bootstyle=(WARNING, OUTLINE),
                                      command=self.buy_plan_from_profile)
        else:
            renew_btn = tb.Button(btn_frame, text="开通会员", bootstyle=(PRIMARY, OUTLINE),
                                  command=self.buy_plan_from_profile)
        renew_btn.pack(fill=X, pady=5)

        tb.Label(frame, text="API 由系统提供，无需设置", font=("微软雅黑", 8),
                 foreground="#888", background="#2b2d31").pack(anchor=W, pady=(10, 0))

    def buy_plan_from_profile(self):
        self._show_plans()

    def activate_member(self):
        top = tb.Toplevel(self.root)
        top.title("会员操作")
        top.geometry("280x200")
        top.resizable(False, False)
        top.transient(self.root)
        top.grab_set()
        top.configure(bg="#2b2d31")

        frame = tb.Frame(top, padding=20, bootstyle="dark")
        frame.pack(expand=True, fill=BOTH)

        tb.Label(frame, text="请选择激活方式", font=("微软雅黑", 11),
                 foreground="#fff", background="#2b2d31").pack(pady=10)

        def use_code():
            top.destroy()
            self._input_code()

        def buy_plan():
            top.destroy()
            self._show_plans()

        tb.Button(frame, text="使用激活码", bootstyle=(INFO, OUTLINE), command=use_code).pack(pady=5, fill=X)
        tb.Button(frame, text="扫码购买套餐", bootstyle=(SUCCESS, OUTLINE), command=buy_plan).pack(pady=5, fill=X)

    def _input_code(self):
        code = simpledialog.askstring("输入激活码", "请输入管理员提供的激活码：")
        if code:
            self._activate(code)

    def _activate(self, code):
        try:
            resp = requests.post(f"{BACKEND_URL}/api/member/activate",
                                 headers={"Authorization": f"Bearer {self.token}"},
                                 json={"code": code})
            data = resp.json()
            if resp.status_code == 200:
                self.member_expire = data.get("member_expire")
                self.update_member_label()
                messagebox.showinfo("成功", "激活成功！")
            else:
                messagebox.showerror("失败", data.get("msg", "激活失败"))
        except Exception as e:
            messagebox.showerror("错误", f"请求失败：{e}")

    def _show_plans(self):
        win = tb.Toplevel(self.root)
        win.title("选择套餐")
        win.geometry("280x300")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()
        win.configure(bg="#2b2d31")

        frame = tb.Frame(win, padding=20, bootstyle="dark")
        frame.pack(expand=True, fill=BOTH)

        tb.Label(frame, text="请选择会员时长", font=("微软雅黑", 11, "bold"),
                 foreground="#fff", background="#2b2d31").pack(pady=5)

        for text, days in PLANS.items():
            btn = tb.Button(frame, text=f"{text} ({days}天)", bootstyle=(PRIMARY, OUTLINE),
                           command=lambda d=days: self._purchase_plan(d, win))
            btn.pack(fill=X, pady=3)

        tb.Label(frame, text="\n💰 选择后显示付款二维码", font=("微软雅黑", 8),
                 foreground="#888", background="#2b2d31").pack()

    def _purchase_plan(self, days, win):
        win.destroy()
        qr_win = tb.Toplevel(self.root)
        qr_win.title("付款二维码")
        qr_win.geometry("320x380")
        qr_win.resizable(False, False)
        qr_win.transient(self.root)
        qr_win.grab_set()
        qr_win.configure(bg="#2b2d31")

        frame = tb.Frame(qr_win, padding=20, bootstyle="dark")
        frame.pack(fill=BOTH, expand=True)

        try:
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.abspath(".")
            img_path = os.path.join(base_path, "qrcode.png")
            img = tk.PhotoImage(file=img_path)
            lbl = tb.Label(frame, image=img, background="#2b2d31")
            lbl.image = img
            lbl.pack(pady=10)
        except Exception:
            tb.Label(frame, text="⚠️ 二维码图片未找到\n请联系管理员", font=("微软雅黑", 10),
                     foreground="red", background="#2b2d31").pack(pady=20)

        tb.Label(frame, text=f"您选择了 {days} 天套餐", font=("微软雅黑", 10, "bold"),
                 foreground="#fff", background="#2b2d31").pack(pady=5)
        tb.Label(frame, text="请扫描上方二维码付款\n付款后联系管理员获取激活码", font=("微软雅黑", 9),
                 foreground="#aaa", background="#2b2d31").pack(pady=10)

    # ========== 非流式聊天核心 ==========
    def send_message_event(self, event=None):
        self.send_message()
        return "break"

    def send_message(self):
        try:
            resp = requests.get(f"{BACKEND_URL}/api/member/check",
                                headers={"Authorization": f"Bearer {self.token}"})
            if resp.status_code == 200 and not resp.json().get("is_member"):
                messagebox.showwarning("提示", "会员已过期，请续费。")
                return
        except:
            messagebox.showwarning("错误", "无法连接服务器")
            return

        user_text = self.input_field.get("1.0", tk.END).strip()
        if not user_text:
            return

        self.input_field.delete("1.0", tk.END)
        self.display_message("你", user_text, "user")
        self.messages.append({"role": "user", "content": user_text})
        self.input_field.config(state=DISABLED)
        self.status_var.set("思考中...")
        self.display_message("DeepSeek", "", "ai")

        threading.Thread(target=self.normal_chat, daemon=True).start()

    def normal_chat(self):
        """非流式请求，一次性显示回复"""
        try:
            resp = requests.post(
                f"{BACKEND_URL}/api/chat",
                headers={"Authorization": f"Bearer {self.token}"},
                json={"messages": self.messages},
                timeout=30
            )
            data = resp.json()
            if resp.status_code == 200 and 'reply' in data:
                reply = data['reply']
                self.messages.append({"role": "assistant", "content": reply})
                self.root.after(0, self.show_full_reply, reply)
            else:
                error = data.get('msg', '未知错误')
                self.root.after(0, self.replace_placeholder, error, "system")
                if self.messages and self.messages[-1]["role"] == "user":
                    self.messages.pop()
        except Exception as e:
            self.root.after(0, self.replace_placeholder, f"网络错误：{e}", "system")
            if self.messages and self.messages[-1]["role"] == "user":
                self.messages.pop()
        finally:
            self.root.after(0, self.finalize_input)

    def show_full_reply(self, text):
        """一次性插入完整回复"""
        self.chat_display.config(state=NORMAL)
        self.chat_display.insert(tk.END, text, "ai")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=DISABLED)

    def replace_placeholder(self, text, tag):
        self.chat_display.config(state=NORMAL)
        self.chat_display.delete("end-2l", tk.END)
        self.display_message("系统", text, tag)
        self.chat_display.config(state=DISABLED)

    def display_message(self, sender, content, tag):
        self.chat_display.config(state=NORMAL)
        self.chat_display.insert(tk.END, f"{sender}：\n", f"{tag}_header")
        self.chat_display.insert(tk.END, f"{content}\n\n", tag)
        self.chat_display.see(tk.END)
        self.chat_display.config(state=DISABLED)

    def finalize_input(self):
        self.input_field.config(state=NORMAL)
        self.input_field.focus_set()
        self.status_var.set("就绪")

    def clear_chat(self):
        if messagebox.askyesno("清空对话", "确定清空所有对话记录吗？"):
            self.messages.clear()
            self.chat_display.config(state=NORMAL)
            self.chat_display.delete("1.0", tk.END)
            self.chat_display.config(state=DISABLED)

    def save_chat(self):
        content = self.chat_display.get("1.0", tk.END).strip()
        if not content:
            messagebox.showinfo("提示", "没有对话内容")
            return
        filename = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = filedialog.asksaveasfilename(defaultextension=".txt", initialfile=filename)
        if filepath:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("成功", f"已保存至：{filepath}")

    def on_close(self):
        self.root.destroy()


if __name__ == "__main__":
    root = tb.Window(themename="darkly")
    app = DeepSeekChatPro(root)
    root.mainloop()
