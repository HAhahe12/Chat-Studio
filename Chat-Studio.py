import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox, filedialog
import requests, json, threading, uuid, time, re, os
from datetime import datetime

# ═══════════════════════════════════════════════════════════════
#  Constants
# ═══════════════════════════════════════════════════════════════
# Change to your own API
OLLAMA_API = "http://***.**.***.**:******/api/chat"
OLLAMA_TAGS = "http://***.**.***.**:******/api/tags"
HISTORY_FILE = "chat_conversations.json"
SETTINGS_FILE = "chat_settings.json"
DEFAULT_SYSTEM = "You are a professional AI assistant. Provide clear, accurate, and well-structured answers."
MODELS = [
    "qwen3:30b-a3b-thinking-2507-q8_0",
    "qwen3:30b-a3b-thinking-2507-q4_K_M",
    "qwen3:32b",
]


class ChatStudio:
    def __init__(self, root):
        self.root = root
        self.root.title("ChatStudio")
        self.root.geometry("1260x880")
        self.root.minsize(900, 600)

        # ── Fonts ──
        code_font = "Cascadia Code"
        try:
            tk.Label(root, font=(code_font, 12), text="test").winfo_reqwidth()
        except Exception:
            code_font = "Consolas"

        self.F = {
            "body":   ("Segoe UI", 13),
            "bold":   ("Segoe UI", 13, "bold"),
            "code":   (code_font, 12),
            "small":  ("Segoe UI", 11),
            "tiny":   ("Segoe UI", 10),
            "hdr":    ("Segoe UI", 16, "bold"),
            "think":  ("Segoe UI", 12, "italic"),
            "title":  ("Segoe UI", 22, "bold"),
            "brand":  ("Segoe UI", 36, "bold"),
        }

        # ── Themes ──
        self.themes = {
            "dark": {
                "bg": "#0d1117", "sidebar": "#161b22", "surface": "#21262d",
                "surface2": "#30363d", "border": "#30363d", "txt": "#e6edf3",
                "txt2": "#8b949e", "txt3": "#6e7681", "accent": "#238636",
                "accent_h": "#2ea043", "user_bg": "#1f6feb", "user_txt": "#ffffff",
                "code_bg": "#161b22", "think_bg": "#0d1d30", "think_brd": "#1f6feb",
                "think_txt": "#58a6ff", "ok": "#3fb950", "err": "#f85149",
                "warn": "#d29922", "scrollbar": "#484f58", "input_bg": "#0d1117",
            },
            "light": {
                "bg": "#ffffff", "sidebar": "#f6f8fa", "surface": "#f0f2f5",
                "surface2": "#e1e4e8", "border": "#d0d7de", "txt": "#1f2328",
                "txt2": "#656d76", "txt3": "#8c959f", "accent": "#238636",
                "accent_h": "#2ea043", "user_bg": "#0969da", "user_txt": "#ffffff",
                "code_bg": "#f6f8fa", "think_bg": "#ddf4ff", "think_brd": "#0969da",
                "think_txt": "#0550ae", "ok": "#1a7f37", "err": "#cf222e",
                "warn": "#9a6700", "scrollbar": "#afb8c1", "input_bg": "#ffffff",
            },
        }

        # ── State ──
        self.dark = True
        self.c = self.themes["dark"]
        self.model_var = tk.StringVar(value=MODELS[0])
        self.sys_prompt = DEFAULT_SYSTEM
        self.temp = 0.3
        self.convos = []
        self.cur_id = None
        self.msgs = []
        self.gen = False
        self.stop_flag = False
        self.online = False

        # Streaming component references
        self._s_think_frm = None
        self._s_think_txt = None
        self._s_ans_frm = None
        self._s_ans_txt = None
        self._think_lbl = None
        self._welcome_frm = None

        self.search_var = tk.StringVar()

        self._load_settings()
        self._load_convos()
        self.c = self.themes["dark" if self.dark else "light"]
        self.root.configure(bg=self.c["bg"])

        # ── Outer container ──
        self.outer = tk.Frame(self.root, bg=self.c["bg"])
        self.outer.pack(fill=tk.BOTH, expand=True)

        self._build_sidebar()
        self._build_chat()

        # ── Initialize conversation ──
        if self.convos:
            self.convos.sort(key=lambda c: c.get("updated", 0))
            self._switch(self.convos[-1]["id"])
        else:
            self._new_conv()

        # ── Shortcuts & close ──
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind("<Control-n>", lambda e: self._new_conv())
        self.root.bind("<Control-t>", lambda e: self._toggle_theme())

        # ── Connection check ──
        threading.Thread(target=self._check_conn, daemon=True).start()

    # ═══════════════════════════════════════════════════════════
    #  Helpers
    # ═══════════════════════════════════════════════════════════

    def _btn(self, parent, text, cmd, bg, fg, font, hov=None, **kw):
        b = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg, font=font,
                      relief=tk.FLAT, cursor="hand2", activebackground=hov or bg,
                      activeforeground=fg, **kw)
        if hov:
            b.bind("<Enter>", lambda e: b.config(bg=hov))
            b.bind("<Leave>", lambda e: b.config(bg=bg))
        return b

    def _clear_stream_refs(self):
        self._s_think_frm = None
        self._s_think_txt = None
        self._s_ans_frm = None
        self._s_ans_txt = None
        self._think_lbl = None

    def _safe_winfo(self, widget):
        """Safely check if widget exists and is valid"""
        if widget is None:
            return False
        try:
            return widget.winfo_exists()
        except Exception:
            return False

    # ═══════════════════════════════════════════════════════════
    #  Sidebar
    # ═══════════════════════════════════════════════════════════

    def _build_sidebar(self):
        c = self.c
        self.sb = tk.Frame(self.outer, bg=c["sidebar"], width=280)
        self.sb.pack(side=tk.LEFT, fill=tk.Y)
        self.sb.pack_propagate(False)

        # Header
        hdr = tk.Frame(self.sb, bg=c["sidebar"])
        hdr.pack(fill=tk.X, padx=16, pady=(16, 8))
        tk.Label(hdr, text="✦ ChatStudio", bg=c["sidebar"], fg=c["txt"],
                 font=self.F["hdr"]).pack(side=tk.LEFT)

        # New conversation button
        self._btn(self.sb, "  ＋  New Chat", self._new_conv,
                  c["accent"], c["user_txt"], self.F["bold"], c["accent_h"]
                  ).pack(fill=tk.X, padx=16, pady=(8, 4))

        # Search
        sf = tk.Frame(self.sb, bg=c["surface"], padx=8, pady=6)
        sf.pack(fill=tk.X, padx=16, pady=(8, 4))

        self.search_var.set("")
        self.search_var.trace_add("write", lambda *_: self._render_list())

        se = tk.Entry(sf, textvariable=self.search_var, font=self.F["small"],
                      bg=c["surface"], fg=c["txt"], relief=tk.FLAT,
                      insertbackground=c["txt"])
        se.pack(fill=tk.X)
        se.insert(0, "")
        se.bind("<FocusIn>", lambda e: sf.config(bg=c["surface2"]))
        se.bind("<FocusOut>", lambda e: sf.config(bg=c["surface"]))

        # History label
        tk.Label(self.sb, text="Chat History", bg=c["sidebar"], fg=c["txt3"],
                 font=self.F["tiny"]).pack(fill=tk.X, padx=20, pady=(12, 4), anchor=tk.W)

        hc = tk.Frame(self.sb, bg=c["sidebar"])
        hc.pack(fill=tk.BOTH, expand=True, padx=8)

        self.his_canvas = tk.Canvas(hc, bg=c["sidebar"], highlightthickness=0)
        sb_scroll = tk.Scrollbar(hc, orient=tk.VERTICAL, command=self.his_canvas.yview)
        self.his_canvas.configure(yscrollcommand=sb_scroll.set)
        sb_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.his_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.his_inner = tk.Frame(self.his_canvas, bg=c["sidebar"])
        self.his_win = self.his_canvas.create_window((0, 0), window=self.his_inner, anchor=tk.NW)
        self.his_inner.bind("<Configure>", lambda e: self.his_canvas.configure(
            scrollregion=self.his_canvas.bbox("all")))
        self.his_canvas.bind("<Configure>",
                             lambda e: self.his_canvas.itemconfig(self.his_win, width=e.width))

        # Bottom
        bf = tk.Frame(self.sb, bg=c["sidebar"])
        bf.pack(fill=tk.X, padx=16, pady=16, side=tk.BOTTOM)

        self.conn_lbl = tk.Label(bf, text="● Connecting...", bg=c["sidebar"],
                                 fg=c["warn"], font=self.F["tiny"], anchor=tk.W)
        self.conn_lbl.pack(fill=tk.X, pady=(0, 8))

        self._btn(bf, "  ⚙  Settings", self._open_settings,
                  c["sidebar"], c["txt2"], self.F["small"], c["surface"]).pack(fill=tk.X, pady=2)
        self._btn(bf, "  🌙 Dark Mode" if self.dark else "  ☀ Light Mode",
                  self._toggle_theme, c["sidebar"], c["txt2"], self.F["small"],
                  c["surface"]).pack(fill=tk.X, pady=2)

    # ═══════════════════════════════════════════════════════════
    #  Chat Area
    # ═══════════════════════════════════════════════════════════

    def _build_chat(self):
        c = self.c
        self.chat = tk.Frame(self.outer, bg=c["bg"])
        self.chat.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Header
        hf = tk.Frame(self.chat, bg=c["bg"], height=56)
        hf.pack(fill=tk.X, padx=24, pady=(12, 0))
        hf.pack_propagate(False)

        self.hdr_title = tk.Label(hf, text="", bg=c["bg"], fg=c["txt"],
                                  font=self.F["hdr"])
        self.hdr_title.pack(side=tk.LEFT)

        self._btn(hf, "  ↻  Regenerate", self._regen, c["surface"], c["txt2"],
                  self.F["tiny"], c["surface2"]).pack(side=tk.RIGHT, padx=(4, 0))
        self._btn(hf, "  🗑  Clear", self._clear_cur, c["surface"], c["txt2"],
                  self.F["tiny"], c["surface2"]).pack(side=tk.RIGHT, padx=(4, 0))
        self._btn(hf, "  📤  Export", self._export, c["surface"], c["txt2"],
                  self.F["tiny"], c["surface2"]).pack(side=tk.RIGHT, padx=(4, 0))

        ttk.Combobox(hf, textvariable=self.model_var, values=MODELS,
                     width=30, font=self.F["tiny"], state="readonly").pack(side=tk.RIGHT, padx=8)

        # Messages area
        mc = tk.Frame(self.chat, bg=c["bg"])
        mc.pack(fill=tk.BOTH, expand=True, padx=0, pady=8)

        self.msg_canvas = tk.Canvas(mc, bg=c["bg"], highlightthickness=0)
        msb = tk.Scrollbar(mc, orient=tk.VERTICAL, command=self.msg_canvas.yview)
        self.msg_canvas.configure(yscrollcommand=msb.set)
        msb.pack(side=tk.RIGHT, fill=tk.Y)
        self.msg_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.msg_inner = tk.Frame(self.msg_canvas, bg=c["bg"])
        self.msg_win = self.msg_canvas.create_window((0, 0), window=self.msg_inner, anchor=tk.NW)
        self.msg_inner.bind("<Configure>", lambda e: self.msg_canvas.configure(
            scrollregion=self.msg_canvas.bbox("all")))
        self.msg_canvas.bind("<Configure>",
                             lambda e: self.msg_canvas.itemconfig(self.msg_win, width=e.width))
        self.msg_canvas.bind("<Enter>", lambda e: self.msg_canvas.bind_all("<MouseWheel>", self._mw))
        self.msg_canvas.bind("<Leave>", lambda e: self.msg_canvas.unbind_all("<MouseWheel>"))

        # Input area
        self._build_input()

    def _build_input(self):
        c = self.c
        self.input_frame = tk.Frame(self.chat, bg=c["bg"])
        self.input_frame.pack(fill=tk.X, padx=24, pady=(0, 20))

        ic = tk.Frame(self.input_frame, bg=c["input_bg"],
                      highlightbackground=c["border"], highlightthickness=1)
        ic.pack(fill=tk.X)

        self.input_box = tk.Text(ic, font=self.F["body"], bg=c["input_bg"], fg=c["txt"],
                                 insertbackground=c["txt"], relief=tk.FLAT, height=3,
                                 wrap=tk.WORD, padx=16, pady=14, spacing1=2, spacing3=2)
        self.input_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.input_box.bind("<Return>", self._on_enter)
        self.input_box.bind("<Shift-Return>", lambda e: None)
        self.input_box.bind("<FocusIn>", lambda e: ic.config(highlightbackground=c["accent"]))
        self.input_box.bind("<FocusOut>", lambda e: ic.config(highlightbackground=c["border"]))

        self.send_btn = self._btn(ic, "  ➤  ", self._send, c["accent"], c["user_txt"],
                                  ("Segoe UI", 18, "bold"), c["accent_h"])
        self.send_btn.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 4), pady=4)

        self.stop_btn = self._btn(ic, "  ■  ", self._stop, c["err"], "#ffffff",
                                  ("Segoe UI", 18, "bold"), "#da3633")

        # Character count & hint
        bf = tk.Frame(self.input_frame, bg=c["bg"])
        bf.pack(fill=tk.X, pady=(6, 0))
        tk.Label(bf, text="Enter to send · Shift+Enter for new line", bg=c["bg"],
                 fg=c["txt3"], font=self.F["tiny"]).pack(side=tk.LEFT)
        self.char_lbl = tk.Label(bf, text="0", bg=c["bg"], fg=c["txt3"],
                                 font=self.F["tiny"])
        self.char_lbl.pack(side=tk.RIGHT)
        self.input_box.bind("<KeyRelease>", self._count_chars)

    def _count_chars(self, e=None):
        n = len(self.input_box.get("1.0", "end-1c"))
        self.char_lbl.config(text=str(n))

    def _on_enter(self, e):
        if not (e.state & 0x1):
            self._send()
            return "break"

    def _mw(self, e):
        self.msg_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

    def _scroll_bottom(self):
        self.root.after(30, lambda: self.msg_canvas.yview_moveto(1.0))

    # ═══════════════════════════════════════════════════════════
    #  Welcome Screen
    # ═══════════════════════════════════════════════════════════

    def _build_welcome(self):
        c = self.c
        # Destroy old welcome frame
        if self._safe_winfo(self._welcome_frm):
            self._welcome_frm.destroy()
            self._welcome_frm = None

        self._welcome_frm = tk.Frame(self.msg_inner, bg=c["bg"])
        self._welcome_frm.pack(fill=tk.BOTH, expand=True, pady=80)

        tk.Label(self._welcome_frm, text="✦ ChatStudio", bg=c["bg"], fg=c["txt"],
                 font=self.F["brand"]).pack(pady=(0, 12))
        tk.Label(self._welcome_frm, text="How can I help you?", bg=c["bg"], fg=c["txt2"],
                 font=self.F["body"]).pack(pady=(0, 40))

        examples = ["Explain the basics of quantum computing", "Write a quicksort in Python",
                    "Analyze current trends in AI", "Help me draft a cover letter"]
        gf = tk.Frame(self._welcome_frm, bg=c["bg"])
        gf.pack()
        for i, ex in enumerate(examples):
            row, col = divmod(i, 2)
            b = self._btn(gf, f"  {ex}  →", lambda t=ex: self._quick_send(t),
                          c["surface"], c["txt"], self.F["small"], c["surface2"])
            b.grid(row=row, column=col, padx=8, pady=6, sticky="ew")
        gf.columnconfigure(0, weight=1)
        gf.columnconfigure(1, weight=1)

    def _quick_send(self, text):
        if self._safe_winfo(self._welcome_frm):
            self._welcome_frm.destroy()
            self._welcome_frm = None
        self.input_box.delete("1.0", tk.END)
        self.input_box.insert("1.0", text)
        self._send()

    # ═══════════════════════════════════════════════════════════
    #  Message Rendering
    # ═══════════════════════════════════════════════════════════

    def _render_msgs(self):
        for w in self.msg_inner.winfo_children():
            w.destroy()
        self._welcome_frm = None
        self._clear_stream_refs()

        for msg in self.msgs:
            if msg["role"] == "user":
                self._add_user_bubble(msg["content"])
            elif msg["role"] == "assistant":
                self._add_asst_bubble(msg["content"])
        self._scroll_bottom()

    def _add_user_bubble(self, content):
        c = self.c
        f = tk.Frame(self.msg_inner, bg=c["bg"])
        f.pack(fill=tk.X, pady=4)
        inner = tk.Frame(f, bg=c["bg"])
        inner.pack(anchor=tk.E, padx=80)

        tk.Label(inner, text="👤", bg=c["bg"], font=("Segoe UI", 20)).pack(side=tk.RIGHT, padx=(8, 0))
        bubble = tk.Frame(inner, bg=c["user_bg"], padx=18, pady=12)
        bubble.pack(side=tk.RIGHT)

        t = tk.Text(bubble, font=self.F["body"], bg=c["user_bg"], fg=c["user_txt"],
                    wrap=tk.WORD, relief=tk.FLAT, padx=0, pady=0, spacing1=2, spacing3=2,
                    selectbackground=c["accent"])
        t.pack(fill=tk.X)
        t.insert("1.0", content)
        t.config(state=tk.DISABLED, height=max(1, content.count("\n") + 1))

        cp = self._btn(inner, "📋", lambda: self._copy(content), c["surface"], c["txt3"],
                       self.F["tiny"], c["surface2"])
        cp.pack(side=tk.RIGHT, padx=(0, 8))
        cp.pack_forget()
        inner.bind("<Enter>", lambda e: cp.pack(side=tk.RIGHT, padx=(0, 8)))
        inner.bind("<Leave>", lambda e: cp.pack_forget())

    def _add_asst_bubble(self, content):
        c = self.c
        f = tk.Frame(self.msg_inner, bg=c["bg"])
        f.pack(fill=tk.X, pady=4)
        inner = tk.Frame(f, bg=c["bg"])
        inner.pack(anchor=tk.W, padx=80)

        tk.Label(inner, text="🤖", bg=c["bg"], font=("Segoe UI", 20)).pack(side=tk.LEFT, padx=(0, 8))
        cf = tk.Frame(inner, bg=c["bg"])
        cf.pack(side=tk.LEFT, fill=tk.X, expand=True)

        think, answer = self._parse_think(content)
        if think:
            self._add_think_static(cf, think)
        if answer:
            self._add_answer_static(cf, answer)

        cp = self._btn(inner, "📋", lambda: self._copy(content), c["surface"], c["txt3"],
                       self.F["tiny"], c["surface2"])
        cp.pack(side=tk.LEFT, padx=(8, 0))
        cp.pack_forget()
        inner.bind("<Enter>", lambda e: cp.pack(side=tk.LEFT, padx=(8, 0)))
        inner.bind("<Leave>", lambda e: cp.pack_forget())

    def _add_think_static(self, parent, text):
        c = self.c
        tf = tk.Frame(parent, bg=c["think_bg"], highlightbackground=c["think_brd"],
                      highlightthickness=1, padx=14, pady=10)
        tf.pack(fill=tk.X, pady=(0, 6))

        hdr = tk.Frame(tf, bg=c["think_bg"])
        hdr.pack(fill=tk.X, pady=(0, 6))
        tk.Label(hdr, text="💭", bg=c["think_bg"], font=("Segoe UI", 14)).pack(side=tk.LEFT)
        tk.Label(hdr, text="Thinking Process", bg=c["think_bg"], fg=c["think_txt"],
                 font=self.F["bold"]).pack(side=tk.LEFT, padx=(4, 0))

        tw = tk.Text(tf, font=self.F["think"], bg=c["think_bg"], fg=c["think_txt"],
                     wrap=tk.WORD, relief=tk.FLAT, padx=0, pady=0, spacing1=2, spacing3=2,
                     selectbackground=c["think_brd"])
        tw.pack(fill=tk.X)
        tw.insert("1.0", text)
        tw.config(state=tk.DISABLED, height=max(2, text.count("\n") + 1 + len(text) // 80))

    def _add_answer_static(self, parent, content):
        c = self.c
        bf = tk.Frame(parent, bg=c["surface"], padx=18, pady=12)
        bf.pack(fill=tk.X)
        self._render_rich(bf, content)

    def _render_rich(self, parent, content):
        c = self.c
        lines = content.split("\n")
        buf = []
        in_code = False
        lang = ""
        code_buf = []

        for line in lines:
            if line.startswith("```"):
                if in_code:
                    if buf:
                        self._add_text(parent, "\n".join(buf))
                        buf = []
                    self._add_code(parent, "\n".join(code_buf), lang)
                    code_buf = []
                    in_code = False
                else:
                    if buf:
                        self._add_text(parent, "\n".join(buf))
                        buf = []
                    in_code = True
                    lang = line[3:].strip()
                continue
            (code_buf if in_code else buf).append(line)

        if buf:
            self._add_text(parent, "\n".join(buf))
        if code_buf:
            self._add_code(parent, "\n".join(code_buf), lang)

    def _add_text(self, parent, text):
        if not text.strip():
            return
        c = self.c
        t = tk.Text(parent, font=self.F["body"], bg=c["surface"], fg=c["txt"],
                    wrap=tk.WORD, relief=tk.FLAT, padx=0, pady=2, spacing1=2, spacing3=2,
                    selectbackground=c["accent"])
        t.pack(fill=tk.X)
        self._insert_fmt(t, text)
        t.config(state=tk.DISABLED, height=max(1, text.count("\n") + 1 + len(text) // 80))

    def _insert_fmt(self, w, text):
        w.tag_config("bold", font=self.F["bold"])
        w.tag_config("italic", font=(self.F["body"][0], self.F["body"][1], "italic"))
        w.tag_config("code", font=self.F["code"],
                     background=self.c["code_bg"],
                     foreground="#f97583" if self.dark else "#cf222e")
        parts = re.split(r"(\*\*.*?\*\*|\*[^*]+\*|`[^`]+`)", text)
        for p in parts:
            if p.startswith("**") and p.endswith("**"):
                w.insert(tk.END, p[2:-2], "bold")
            elif p.startswith("*") and p.endswith("*") and len(p) > 2:
                w.insert(tk.END, p[1:-1], "italic")
            elif p.startswith("`") and p.endswith("`"):
                w.insert(tk.END, p[1:-1], "code")
            else:
                w.insert(tk.END, p)

    def _add_code(self, parent, code, lang=""):
        if not code.strip():
            return
        c = self.c
        cf = tk.Frame(parent, bg=c["code_bg"], padx=10, pady=10)
        cf.pack(fill=tk.X, pady=6)

        top = tk.Frame(cf, bg=c["code_bg"])
        top.pack(fill=tk.X, pady=(0, 4))
        tk.Label(top, text=lang or "code", bg=c["code_bg"], fg=c["txt3"],
                 font=self.F["tiny"]).pack(side=tk.LEFT)
        self._btn(top, "Copy", lambda: self._copy(code), c["surface2"], c["txt2"],
                  self.F["tiny"], c["border"]).pack(side=tk.RIGHT)

        t = tk.Text(cf, font=self.F["code"], bg=c["code_bg"],
                    fg="#e6edf3" if self.dark else "#24292f", wrap=tk.NONE,
                    relief=tk.FLAT, padx=6, pady=6, spacing1=2, spacing3=2,
                    selectbackground=c["accent"],
                    height=min(25, code.count("\n") + 2))
        t.pack(fill=tk.X)
        t.insert("1.0", code)
        t.config(state=tk.DISABLED)

    # ═══════════════════════════════════════════════════════════
    #  Streaming Bubble
    # ═══════════════════════════════════════════════════════════

    def _create_stream_bubble(self):
        c = self.c
        self._clear_stream_refs()

        f = tk.Frame(self.msg_inner, bg=c["bg"])
        f.pack(fill=tk.X, pady=4)
        inner = tk.Frame(f, bg=c["bg"])
        inner.pack(anchor=tk.W, padx=80)

        tk.Label(inner, text="🤖", bg=c["bg"], font=("Segoe UI", 20)).pack(side=tk.LEFT, padx=(0, 8))
        cf = tk.Frame(inner, bg=c["bg"])
        cf.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Thinking area (hidden by default)
        self._s_think_frm = tk.Frame(cf, bg=c["think_bg"],
                                     highlightbackground=c["think_brd"],
                                     highlightthickness=1, padx=14, pady=10)

        hdr = tk.Frame(self._s_think_frm, bg=c["think_bg"])
        hdr.pack(fill=tk.X, pady=(0, 6))
        tk.Label(hdr, text="💭", bg=c["think_bg"], font=("Segoe UI", 14)).pack(side=tk.LEFT)
        self._think_lbl = tk.Label(hdr, text=" Thinking...", bg=c["think_bg"],
                                   fg=c["think_txt"], font=self.F["bold"])
        self._think_lbl.pack(side=tk.LEFT, padx=(4, 0))

        self._s_think_txt = tk.Text(self._s_think_frm, font=self.F["think"],
                                    bg=c["think_bg"], fg=c["think_txt"],
                                    wrap=tk.WORD, relief=tk.FLAT, height=1,
                                    padx=0, pady=0, spacing1=2, spacing3=2,
                                    selectbackground=c["think_brd"])
        self._s_think_txt.pack(fill=tk.X)
        self._s_think_txt.config(state=tk.DISABLED)

        # Answer area
        self._s_ans_frm = tk.Frame(cf, bg=c["surface"], padx=18, pady=12)
        self._s_ans_frm.pack(fill=tk.X)

        self._s_ans_txt = tk.Text(self._s_ans_frm, font=self.F["body"],
                                  bg=c["surface"], fg=c["txt"],
                                  wrap=tk.WORD, relief=tk.FLAT, height=1,
                                  padx=0, pady=0, spacing1=2, spacing3=2,
                                  selectbackground=c["accent"])
        self._s_ans_txt.pack(fill=tk.X)
        self._s_ans_txt.config(state=tk.DISABLED)

        self._scroll_bottom()

    def _append_think(self, chunk):
        def _do():
            if not self._safe_winfo(self._s_think_txt):
                return
            if not self._s_think_frm.winfo_ismapped():
                self._s_think_frm.pack(before=self._s_ans_frm, fill=tk.X, pady=(0, 6))
            self._s_think_txt.config(state=tk.NORMAL)
            self._s_think_txt.insert(tk.END, chunk)
            self._s_think_txt.config(state=tk.DISABLED)
            content = self._s_think_txt.get("1.0", "end-1c")
            self._s_think_txt.config(height=max(2, content.count("\n") + 1 + len(content) // 80))
            self._scroll_bottom()
        self.root.after(0, _do)

    def _append_answer(self, chunk):
        def _do():
            if not self._safe_winfo(self._s_ans_txt):
                return
            self._s_ans_txt.config(state=tk.NORMAL)
            self._s_ans_txt.insert(tk.END, chunk)
            self._s_ans_txt.config(state=tk.DISABLED)
            content = self._s_ans_txt.get("1.0", "end-1c")
            self._s_ans_txt.config(height=max(1, content.count("\n") + 1 + len(content) // 80))
            self._scroll_bottom()
        self.root.after(0, _do)

    # ═══════════════════════════════════════════════════════════
    #  Conversation Management
    # ═══════════════════════════════════════════════════════════

    def _find(self, cid):
        for i, c in enumerate(self.convos):
            if c["id"] == cid:
                return c
        return None

    def _new_conv(self):
        if self.gen:
            messagebox.showinfo("Info", "Generation in progress, please wait.")
            return
        if self.cur_id:
            self._save_cur()
        cid = str(uuid.uuid4())
        conv = {"id": cid, "title": "New Conversation",
                "messages": [{"role": "system", "content": self.sys_prompt}],
                "created": time.time(), "updated": time.time()}
        self.convos.append(conv)
        self._save_convos()
        self._switch(cid)

    def _switch(self, cid):
        if self.gen:
            messagebox.showinfo("Info", "Generation in progress, please wait.")
            return
        if self.cur_id and self.cur_id != cid:
            self._save_cur()

        conv = self._find(cid)
        if not conv:
            return

        self.cur_id = cid
        self.msgs = conv["messages"]
        self._clear_stream_refs()

        # Clear message area
        for w in self.msg_inner.winfo_children():
            w.destroy()
        self._welcome_frm = None

        if len(self.msgs) <= 1:
            self._build_welcome()
        else:
            self._render_msgs()

        self.hdr_title.config(text=conv.get("title", ""))
        self._render_list()

    def _save_cur(self):
        if not self.cur_id:
            return
        conv = self._find(self.cur_id)
        if not conv:
            return
        title = "New Conversation"
        for m in self.msgs:
            if m["role"] == "user":
                title = m["content"][:30] + ("..." if len(m["content"]) > 30 else "")
                break
        conv["title"] = title
        conv["messages"] = self.msgs
        conv["updated"] = time.time()
        self._save_convos()

    def _del_conv(self, cid):
        if self.gen:
            return
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this conversation?"):
            self.convos = [c for c in self.convos if c["id"] != cid]
            self._save_convos()
            if self.cur_id == cid:
                self.cur_id = None
                if self.convos:
                    self._switch(self.convos[-1]["id"])
                else:
                    self._new_conv()
            self._render_list()

    def _clear_cur(self):
        if self.gen:
            return
        if not self.cur_id:
            return
        self.msgs = [{"role": "system", "content": self.sys_prompt}]
        conv = self._find(self.cur_id)
        if conv:
            conv["messages"] = self.msgs
            conv["updated"] = time.time()
        for w in self.msg_inner.winfo_children():
            w.destroy()
        self._welcome_frm = None
        self._clear_stream_refs()
        self._build_welcome()
        self._save_convos()

    def _regen(self):
        if self.gen:
            return
        if len(self.msgs) < 2:
            return
        if self.msgs[-1]["role"] == "assistant":
            self.msgs.pop()
        for w in self.msg_inner.winfo_children():
            w.destroy()
        self._welcome_frm = None
        self._clear_stream_refs()
        self._render_msgs()
        self._create_stream_bubble()
        threading.Thread(target=self._stream, daemon=True).start()

    def _render_list(self):
        if not self._safe_winfo(self.his_inner):
            return
        for w in self.his_inner.winfo_children():
            w.destroy()

        q = self.search_var.get().strip().lower()
        sorted_c = sorted(self.convos, key=lambda c: c.get("updated", 0), reverse=True)
        filtered = [c for c in sorted_c if not q or q in c.get("title", "").lower()]

        if not filtered:
            tk.Label(self.his_inner, text="No conversations" if not q else "No matches",
                     bg=self.c["sidebar"], fg=self.c["txt3"],
                     font=self.F["small"]).pack(pady=20)
            return

        for conv in filtered:
            is_active = conv["id"] == self.cur_id
            bg = self.c["surface"] if is_active else self.c["sidebar"]
            fg = self.c["txt"] if is_active else self.c["txt2"]
            bdr = self.c["accent"] if is_active else self.c["sidebar"]

            row = tk.Frame(self.his_inner, bg=bg, highlightbackground=bdr,
                           highlightthickness=1 if is_active else 0)
            row.pack(fill=tk.X, pady=1, padx=4)

            lbl = tk.Label(row, text=conv["title"][:28], bg=bg, fg=fg,
                           font=self.F["small"], anchor=tk.W, padx=10, pady=8, cursor="hand2")
            lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

            del_btn = self._btn(row, "✕", lambda cid=conv["id"]: self._del_conv(cid),
                                bg, self.c["err"], self.F["tiny"], self.c["surface2"])
            del_btn.pack(side=tk.RIGHT, padx=6)
            del_btn.pack_forget()

            def enter(e, r=row, d=del_btn, b=bg, a=is_active):
                if not a:
                    r.config(bg=self.c["surface"])
                d.pack(side=tk.RIGHT, padx=6)

            def leave(e, r=row, d=del_btn, a=is_active, b=bg):
                d.pack_forget()
                r.config(bg=self.c["surface"] if a else self.c["sidebar"])

            for widget in (row, lbl):
                widget.bind("<Enter>", enter)
                widget.bind("<Leave>", leave)
                widget.bind("<Button-1>", lambda e, cid=conv["id"]: self._switch(cid))

    # ═══════════════════════════════════════════════════════════
    #  Send & Streaming
    # ═══════════════════════════════════════════════════════════

    def _send(self):
        if self.gen:
            return
        if not self.cur_id:
            self._new_conv()
        text = self.input_box.get("1.0", "end-1c").strip()
        if not text:
            return

        # Hide welcome screen
        if self._safe_winfo(self._welcome_frm):
            self._welcome_frm.destroy()
            self._welcome_frm = None

        self._add_user_bubble(text)
        self.input_box.delete("1.0", tk.END)
        self._count_chars()
        self.msgs.append({"role": "user", "content": text})

        self._create_stream_bubble()

        # Switch to stop button
        self.send_btn.pack_forget()
        self.stop_btn.pack(fill=tk.BOTH, expand=True, padx=(0, 4), pady=4)

        threading.Thread(target=self._stream, daemon=True).start()

    def _stop(self):
        self.stop_flag = True

    def _stream(self):
        self.gen = True
        self.stop_flag = False
        full_think = ""
        full_content = ""

        data = {
            "model": self.model_var.get(),
            "messages": self.msgs,
            "stream": True,
            "options": {"temperature": self.temp},
        }

        try:
            with requests.post(OLLAMA_API, json=data, stream=True, timeout=120) as resp:
                buf = b""
                for chunk in resp.iter_content(512):
                    if self.stop_flag:
                        break
                    if not chunk:
                        continue
                    buf += chunk
                    try:
                        text = buf.decode("utf-8")
                        buf = b""
                    except UnicodeDecodeError:
                        continue
                    for line in text.splitlines():
                        if not line.strip():
                            continue
                        try:
                            obj = json.loads(line)
                            msg = obj.get("message", {})
                            th = msg.get("thinking", "")
                            if th:
                                full_think += th
                                self._append_think(th)
                            ct = msg.get("content", "")
                            if ct:
                                full_content += ct
                                self._append_answer(ct)
                        except Exception:
                            pass

            final = ""
            if full_think:
                final += f"&lt;think&gt;{full_think}&lt;/think&gt;\n"
            final += full_content
            self.msgs.append({"role": "assistant", "content": final})
            self._save_cur()
            self._render_list()

        except requests.exceptions.ConnectionError:
            self._append_answer("\n\n❌ Cannot connect to Ollama service")
        except requests.exceptions.Timeout:
            self._append_answer("\n\n❌ Request timeout")
        except Exception as e:
            self._append_answer(f"\n\n❌ Error: {str(e)}")

        def _restore():
            if self._safe_winfo(self.stop_btn):
                self.stop_btn.pack_forget()
            if self._safe_winfo(self.send_btn):
                self.send_btn.pack(fill=tk.BOTH, expand=True, padx=(0, 4), pady=4)
        self.root.after(0, _restore)
        self.gen = False

    # ═══════════════════════════════════════════════════════════
    #  Utilities
    # ═══════════════════════════════════════════════════════════

    def _copy(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)

    def _export(self):
        if not self.msgs or len(self.msgs) <= 1:
            messagebox.showinfo("Info", "Conversation is empty.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("Text", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        try:
            conv = self._find(self.cur_id)
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"# {conv.get('title', 'Conversation')}\n\n")
                f.write(f"> Model: `{self.model_var.get()}` | "
                        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n---\n\n")
                for m in self.msgs:
                    if m["role"] == "user":
                        f.write(f"### 👤 User\n\n{m['content']}\n\n")
                    elif m["role"] == "assistant":
                        th, ans = self._parse_think(m["content"])
                        if th:
                            f.write(f"<details><summary>💭 Thinking Process</summary>\n\n{th}\n\n</details>\n\n")
                        f.write(f"### 🤖 Assistant\n\n{ans}\n\n---\n\n")
            messagebox.showinfo("Success", f"Exported to:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _parse_think(self, content):
        m = re.search(r"&lt;think&gt;(.*?)&lt;/think&gt;", content, re.DOTALL)
        if m:
            return m.group(1).strip(), re.sub(r"&lt;think&gt;.*?&lt;/think&gt;", "", content, flags=re.DOTALL).strip()
        return "", content

    def _check_conn(self):
        try:
            r = requests.get(OLLAMA_TAGS, timeout=8)
            if r.status_code == 200:
                self.online = True
                self.root.after(0, lambda: self.conn_lbl.config(text="● Connected", fg=self.c["ok"]))
            else:
                raise Exception()
        except Exception:
            self.online = False
            self.root.after(0, lambda: self.conn_lbl.config(text="● Disconnected", fg=self.c["err"]))

    # ═══════════════════════════════════════════════════════════
    #  Settings
    # ═══════════════════════════════════════════════════════════

    def _open_settings(self):
        c = self.c
        dlg = tk.Toplevel(self.root)
        dlg.title("Settings")
        dlg.geometry("560x480")
        dlg.configure(bg=c["bg"])
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 560) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 480) // 2
        dlg.geometry(f"+{x}+{y}")

        tk.Label(dlg, text="  ⚙  Settings", bg=c["bg"], fg=c["txt"],
                 font=self.F["hdr"]).pack(padx=28, pady=(24, 20), anchor=tk.W)

        tk.Label(dlg, text="System Prompt", bg=c["bg"], fg=c["txt2"],
                 font=self.F["small"]).pack(padx=28, anchor=tk.W)
        sp = tk.Text(dlg, font=self.F["small"], bg=c["surface"], fg=c["txt"],
                     relief=tk.FLAT, height=6, wrap=tk.WORD, padx=12, pady=10,
                     insertbackground=c["txt"], highlightbackground=c["border"],
                     highlightthickness=1, spacing1=2, spacing3=2)
        sp.pack(fill=tk.X, padx=28, pady=(4, 16))
        sp.insert("1.0", self.sys_prompt)

        tk.Label(dlg, text="Temperature (creativity 0~2)", bg=c["bg"], fg=c["txt2"],
                 font=self.F["small"]).pack(padx=28, anchor=tk.W)
        tv = tk.DoubleVar(value=self.temp)
        tk.Scale(dlg, variable=tv, from_=0.0, to=2.0, orient=tk.HORIZONTAL,
                 resolution=0.1, bg=c["bg"], fg=c["txt"], troughcolor=c["surface"],
                 highlightthickness=0, font=self.F["tiny"], activebackground=c["accent"],
                 sliderrelief=tk.FLAT, length=500).pack(padx=28, pady=(4, 16))

        tk.Label(dlg, text="Model Selection", bg=c["bg"], fg=c["txt2"],
                 font=self.F["small"]).pack(padx=28, anchor=tk.W)
        mv = tk.StringVar(value=self.model_var.get())
        ttk.Combobox(dlg, textvariable=mv, values=MODELS, width=40,
                     font=self.F["small"], state="readonly").pack(padx=28, pady=(4, 16), anchor=tk.W)

        bf = tk.Frame(dlg, bg=c["bg"])
        bf.pack(fill=tk.X, padx=28, pady=(8, 24))

        def save():
            self.sys_prompt = sp.get("1.0", tk.END).strip() or DEFAULT_SYSTEM
            self.temp = tv.get()
            self.model_var.set(mv.get())
            self._save_settings()
            dlg.destroy()

        self._btn(bf, "  Save  ", save, c["accent"], c["user_txt"],
                  self.F["bold"], hov=c["accent_h"]).pack(side=tk.RIGHT, padx=(8, 0))
        self._btn(bf, "  Cancel  ", dlg.destroy, c["surface"], c["txt2"],
                  self.F["small"], hov=c["surface2"]).pack(side=tk.RIGHT)

    # ═══════════════════════════════════════════════════════════
    #  Theme Toggle
    # ═══════════════════════════════════════════════════════════

    def _toggle_theme(self):
        self.dark = not self.dark
        self.c = self.themes["dark" if self.dark else "light"]
        self._save_settings()

        # Clear all streaming references
        self._clear_stream_refs()
        self._welcome_frm = None

        # Rebuild UI
        for w in self.outer.winfo_children():
            w.destroy()

        self.outer.configure(bg=self.c["bg"])
        self.root.configure(bg=self.c["bg"])

        self._build_sidebar()
        self._build_chat()

        if self.cur_id:
            conv = self._find(self.cur_id)
            if conv:
                self.msgs = conv["messages"]
                if len(self.msgs) <= 1:
                    self._build_welcome()
                else:
                    self._render_msgs()
                self._render_list()
                self.hdr_title.config(text=conv.get("title", ""))

    # ═══════════════════════════════════════════════════════════
    #  Persistence
    # ═══════════════════════════════════════════════════════════

    def _load_convos(self):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                self.convos = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.convos = []

    def _save_convos(self):
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.convos, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_settings(self):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                s = json.load(f)
            self.dark = s.get("dark", True)
            self.sys_prompt = s.get("system_prompt", DEFAULT_SYSTEM)
            self.temp = s.get("temperature", 0.3)
            self.model_var.set(s.get("model", MODELS[0]))
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def _save_settings(self):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "dark": self.dark,
                    "system_prompt": self.sys_prompt,
                    "temperature": self.temp,
                    "model": self.model_var.get()
                }, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _on_close(self):
        if self.cur_id:
            self._save_cur()
        self._save_settings()
        self.root.destroy()

    # ═══════════════════════════════════════════════════════════
    #  Launch
    # ═══════════════════════════════════════════════════════════

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    root = tk.Tk()
    app = ChatStudio(root)
    app.run()