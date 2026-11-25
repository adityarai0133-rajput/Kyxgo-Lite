import os
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from kyxgo_core import KyxgoCore


class KyxgoLiteApp:

    def __init__(self, root):
        self.root = root
        self.root.title("Kyxgo Lite — Ultra-Fast Offline Study & Code Engine")
        self.root.geometry("920x640")
        self.root.minsize(780, 520)

        # --------------------------------------------------
        # DARK-MODE PALETTE
        # --------------------------------------------------
        self.bg_main = "#0F172A"
        self.bg_panel = "#1E293B"
        self.bg_card = "#162032"
        self.bg_input = "#0B1120"

        self.fg_text = "#F8FAFC"
        self.fg_muted = "#94A3B8"

        self.accent = "#38BDF8"
        self.accent_hover = "#0284C7"

        self.danger = "#EF4444"
        self.success = "#22C55E"
        self.border = "#334155"

        self.root.configure(bg=self.bg_main)

        # --------------------------------------------------
        # APPLICATION STATE
        # --------------------------------------------------
        self.temp_mode = False
        self.notes_folder = os.path.abspath("my_notes")
        self.core = KyxgoCore(temp_mode=self.temp_mode)

        self.executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="KyxgoWorker"
        )

        self.busy = False
        self.closing = False

        self.active_future = None
        self.active_success = None
        self.active_error = None
        self.shutdown_future = None

        self.chat_cards = []

        # --------------------------------------------------
        # BUILD UI & STARTUP
        # --------------------------------------------------
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._set_status("Starting Kyxgo Lite...", self.accent)
        self._run_task(self._startup_task, self._startup_complete)

    # ======================================================
    # USER INTERFACE
    # ======================================================

    def _build_ui(self):
        # HEADER
        header = tk.Frame(
            self.root,
            bg=self.bg_panel,
            height=58,
            padx=16,
            pady=10
        )
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        title_box = tk.Frame(header, bg=self.bg_panel)
        title_box.pack(side=tk.LEFT)

        tk.Label(
            title_box,
            text="⚡ KYXGO LITE",
            font=("Segoe UI", 14, "bold"),
            fg=self.accent,
            bg=self.bg_panel
        ).pack(side=tk.LEFT)

        self.status_lbl = tk.Label(
            title_box,
            text="  |  Ready",
            font=("Segoe UI", 9),
            fg=self.fg_muted,
            bg=self.bg_panel
        )
        self.status_lbl.pack(side=tk.LEFT, padx=(6, 0))

        # TOP CONTROLS
        controls = tk.Frame(header, bg=self.bg_panel)
        controls.pack(side=tk.RIGHT)

        self.mode_btn = tk.Button(
            controls,
            text="🔒 Saved Mode",
            font=("Segoe UI", 9, "bold"),
            bg="#064E3B",
            fg="#A7F3D0",
            activebackground="#065F46",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            padx=10,
            pady=5,
            cursor="hand2",
            command=self._toggle_mode
        )
        self.mode_btn.pack(side=tk.LEFT, padx=4)

        self.pick_btn = tk.Button(
            controls,
            text="📂 Pick Folder",
            font=("Segoe UI", 9, "bold"),
            bg=self.bg_card,
            fg=self.fg_text,
            activebackground=self.border,
            activeforeground=self.fg_text,
            relief=tk.FLAT,
            padx=10,
            pady=5,
            cursor="hand2",
            command=self._pick_folder
        )
        self.pick_btn.pack(side=tk.LEFT, padx=4)

        self.topic_btn = tk.Button(
            controls,
            text="🔄 New Topic",
            font=("Segoe UI", 9),
            bg=self.bg_card,
            fg=self.accent,
            activebackground=self.border,
            activeforeground=self.accent,
            relief=tk.FLAT,
            padx=10,
            pady=5,
            cursor="hand2",
            command=self._reset_topic
        )
        self.topic_btn.pack(side=tk.LEFT, padx=4)

        self.wipe_btn = tk.Button(
            controls,
            text="🧹 Wipe All",
            font=("Segoe UI", 9, "bold"),
            bg="#450A0A",
            fg="#FCA5A5",
            activebackground="#7F1D1D",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            padx=10,
            pady=5,
            cursor="hand2",
            command=self._wipe_all
        )
        self.wipe_btn.pack(side=tk.LEFT, padx=(4, 0))

        # CHAT STREAM
        stream_wrapper = tk.Frame(self.root, bg=self.bg_main)
        stream_wrapper.pack(fill=tk.BOTH, expand=True, padx=16, pady=(12, 8))

        self.canvas = tk.Canvas(
            stream_wrapper,
            bg=self.bg_main,
            highlightthickness=0
        )
        self.scrollbar = tk.Scrollbar(
            stream_wrapper,
            orient=tk.VERTICAL,
            command=self.canvas.yview
        )
        self.chat_container = tk.Frame(self.canvas, bg=self.bg_main)

        self.chat_container.bind("<Configure>", self._update_scroll_region)

        self.canvas_window = self.canvas.create_window(
            (0, 0),
            window=self.chat_container,
            anchor="nw"
        )
        self.canvas.bind("<Configure>", self._resize_chat_container)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Scroll events
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", self._on_linux_scroll)
        self.canvas.bind("<Button-5>", self._on_linux_scroll)

        # INPUT BAR
        input_bar = tk.Frame(self.root, bg=self.bg_panel, padx=16, pady=12)
        input_bar.pack(fill=tk.X)

        self.query_entry = tk.Entry(
            input_bar,
            font=("Segoe UI", 11),
            bg=self.bg_input,
            fg=self.fg_text,
            insertbackground=self.accent,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=self.border,
            highlightcolor=self.accent
        )
        self.query_entry.pack(
            side=tk.LEFT,
            fill=tk.X,
            expand=True,
            ipady=8,
            padx=(0, 10)
        )
        self.query_entry.bind("<Return>", self._on_enter)
        self.query_entry.focus_set()

        self.ask_btn = tk.Button(
            input_bar,
            text="Ask ⚡",
            font=("Segoe UI", 10, "bold"),
            bg=self.accent,
            fg="#0F172A",
            activebackground=self.accent_hover,
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            padx=18,
            pady=7,
            cursor="hand2",
            command=self._ask_question
        )
        self.ask_btn.pack(side=tk.RIGHT)

        self._update_mode_button()

    # ======================================================
    # SCROLLING
    # ======================================================

    def _update_scroll_region(self, event=None):
        if not self.closing:
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _resize_chat_container(self, event):
        if not self.closing:
            self.canvas.itemconfigure(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        if not self.closing and event.delta:
            self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def _on_linux_scroll(self, event):
        if self.closing:
            return
        if event.num == 4:
            self.canvas.yview_scroll(-3, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(3, "units")

    def _scroll_to_bottom(self):
        if not self.closing:
            self.root.after(50, self._perform_scroll)

    def _perform_scroll(self):
        if not self.closing:
            self.canvas.yview_moveto(1.0)

    # ======================================================
    # STATUS & CONTROL STATE
    # ======================================================

    def _set_status(self, text, color=None):
        if not self.closing:
            self.status_lbl.configure(
                text=f"  |  {text}",
                fg=color or self.fg_muted
            )

    def _set_controls(self, enabled):
        if self.closing:
            enabled = False

        state = tk.NORMAL if enabled else tk.DISABLED

        self.mode_btn.configure(state=state)
        self.pick_btn.configure(state=state)
        self.topic_btn.configure(state=state)
        self.ask_btn.configure(state=state)
        self.query_entry.configure(state=state)

        self.wipe_btn.configure(
            state=(
                tk.NORMAL
                if enabled and not self.temp_mode
                else tk.DISABLED
            )
        )

    # ======================================================
    # BACKGROUND TASK MANAGEMENT
    # ======================================================

    def _run_task(self, function, on_success, on_error=None):
        if self.closing or self.busy:
            return False

        self.busy = True
        self.active_success = on_success
        self.active_error = on_error
        self._set_controls(False)

        try:
            self.active_future = self.executor.submit(function)
        except Exception as error:
            self.busy = False
            self.active_future = None
            self._set_controls(True)
            self._show_error(error)
            return False

        self.root.after(50, self._poll_task)
        return True

    def _poll_task(self):
        if self.closing:
            return

        future = self.active_future
        if future is None:
            return

        if not future.done():
            self.root.after(50, self._poll_task)
            return

        try:
            result = future.result()
            error = None
        except Exception as exc:
            result = None
            error = exc

        success_callback = self.active_success
        error_callback = self.active_error

        self.active_future = None
        self.active_success = None
        self.active_error = None
        self.busy = False
        self._set_controls(True)

        if error is not None:
            if error_callback:
                error_callback(error)
            else:
                self._show_error(error)
        else:
            try:
                success_callback(result)
            except Exception as callback_error:
                self._show_error(callback_error)

    def _show_error(self, error):
        self._set_status("Operation failed", self.danger)
        messagebox.showerror("Kyxgo Lite Error", str(error), parent=self.root)

    # ======================================================
    # STARTUP
    # ======================================================

    def _startup_task(self):
        indexed_count = self.core.index_folder(self.notes_folder)
        saved_chats = self.core.get_all_chats()
        return indexed_count, saved_chats

    def _startup_complete(self, result):
        indexed_count, saved_chats = result
        self._render_saved_chats(saved_chats)
        self._set_status(
            f"Ready | Indexed {indexed_count} chunks",
            self.success
        )

    # ======================================================
    # CHAT CARD MANAGEMENT
    # ======================================================

    def _clear_ui_cards(self):
        for widget in self.chat_container.winfo_children():
            widget.destroy()
        self.chat_cards.clear()

    def _render_saved_chats(self, chats):
        self._clear_ui_cards()
        for chat_id, timestamp, question, answer, source in chats:
            self._render_chat_card(
                chat_id,
                question,
                answer,
                source,
                timestamp
            )
        self._scroll_to_bottom()

    def _render_chat_card(
        self,
        chat_id,
        question,
        answer,
        source,
        timestamp=None
    ):
        if self.closing:
            return

        card = tk.Frame(
            self.chat_container,
            bg=self.bg_card,
            padx=14,
            pady=10,
            highlightthickness=1,
            highlightbackground=self.border
        )
        card.pack(fill=tk.X, pady=6)
        self.chat_cards.append(card)

        # CARD HEADER
        top_row = tk.Frame(card, bg=self.bg_card)
        top_row.pack(fill=tk.X)

        time_text = timestamp or datetime.now().strftime("%d %b %Y, %I:%M %p")
        tk.Label(
            top_row,
            text=time_text,
            font=("Segoe UI", 8),
            fg=self.fg_muted,
            bg=self.bg_card
        ).pack(side=tk.LEFT)

        if chat_id is not None:
            tk.Button(
                top_row,
                text="🗑️ Delete",
                font=("Segoe UI", 8, "bold"),
                bg="#3B0D11",
                fg="#FCA5A5",
                activebackground=self.danger,
                activeforeground="#FFFFFF",
                relief=tk.FLAT,
                padx=8,
                pady=2,
                cursor="hand2",
                command=lambda c=card, cid=chat_id: self._delete_card(c, cid)
            ).pack(side=tk.RIGHT)

        # QUESTION
        tk.Label(
            card,
            text="YOU",
            font=("Segoe UI", 8, "bold"),
            fg=self.accent,
            bg=self.bg_card
        ).pack(anchor="w", pady=(10, 3))

        tk.Label(
            card,
            text=question,
            font=("Segoe UI", 10, "bold"),
            fg=self.accent,
            bg=self.bg_card,
            wraplength=820,
            justify=tk.LEFT,
            anchor="w"
        ).pack(fill=tk.X, anchor="w")

        # ANSWER
        tk.Label(
            card,
            text="KYXGO",
            font=("Segoe UI", 8, "bold"),
            fg=self.success,
            bg=self.bg_card
        ).pack(anchor="w", pady=(10, 3))

        tk.Label(
            card,
            text=answer,
            font=("Segoe UI", 10),
            fg=self.fg_text,
            bg=self.bg_card,
            wraplength=820,
            justify=tk.LEFT,
            anchor="w"
        ).pack(fill=tk.X, anchor="w")

        # SOURCE
        mode_tag = (
            "Temporary Session"
            if self.temp_mode
            else f"Saved ID #{chat_id}"
        )
        tk.Label(
            card,
            text=f"📄 Source: {source}   •   {mode_tag}",
            font=("Segoe UI", 8),
            fg=self.fg_muted,
            bg=self.bg_card
        ).pack(anchor="w", pady=(8, 0))

    # ======================================================
    # ASK QUESTION & FOLDER ACTIONS
    # ======================================================

    def _on_enter(self, event):
        self._ask_question()
        return "break"

    def _ask_question(self):
        if self.busy or self.closing:
            return

        question = self.query_entry.get().strip()
        if not question:
            return

        current_core = self.core
        save_chat = not self.temp_mode

        self.query_entry.delete(0, tk.END)
        self._set_status("Searching offline knowledge...", self.accent)

        def task():
            return current_core.ask(question, save_chat=save_chat)

        def success(result):
            answer, source, chat_id = result
            self._render_chat_card(chat_id, question, answer, source)
            self._set_status("Answer ready", self.success)
            self._scroll_to_bottom()

        self._run_task(task, success)

    def _pick_folder(self):
        if self.busy or self.closing:
            return

        selected = filedialog.askdirectory(
            title="Select Notes / PDFs / Code Folder",
            initialdir=self.notes_folder,
            parent=self.root
        )
        if not selected:
            return

        folder = os.path.abspath(selected)
        current_core = self.core
        self._set_status("Indexing selected folder...", self.accent)

        def task():
            return current_core.index_folder(folder)

        def success(count):
            self.notes_folder = folder
            self._set_status(f"Indexed {count} chunks", self.success)

        self._run_task(task, success)

    def _reset_topic(self):
        if self.busy or self.closing:
            return

        current_core = self.core

        def task():
            current_core.reset_context()
            return True

        def success(_):
            self._set_status("Follow-up context cleared", self.accent)

        self._run_task(task, success)

    # ======================================================
    # MODE SWITCHING
    # ======================================================

    def _toggle_mode(self):
        if self.busy or self.closing:
            return

        old_core = self.core
        old_mode = self.temp_mode
        target_mode = not old_mode
        folder = self.notes_folder

        self._set_status("Switching mode...", self.accent)

        def task():
            old_core.close_and_cleanup()
            new_core = None

            try:
                new_core = KyxgoCore(temp_mode=target_mode)
                indexed_count = new_core.index_folder(folder)
                saved_chats = new_core.get_all_chats()
                self.core = new_core
                return indexed_count, saved_chats, target_mode, None
            except Exception as switch_error:
                if new_core is not None:
                    new_core.close_and_cleanup()

                recovery_core = KyxgoCore(temp_mode=old_mode)
                try:
                    recovery_core.index_folder(folder)
                    saved_chats = recovery_core.get_all_chats()
                    self.core = recovery_core
                    return 0, saved_chats, old_mode, str(switch_error)
                except Exception:
                    recovery_core.close_and_cleanup()
                    raise

        def success(result):
            indexed_count, saved_chats, active_mode, switch_error = result
            self.temp_mode = active_mode
            self._update_mode_button()
            self._render_saved_chats(saved_chats)

            if switch_error:
                self._set_status("Previous mode restored", self.danger)
                messagebox.showerror(
                    "Mode Switch Error",
                    switch_error,
                    parent=self.root
                )
                return

            if self.temp_mode:
                self._set_status(
                    f"Temp Mode ON | {indexed_count} chunks",
                    "#FBBF24"
                )
            else:
                self._set_status(
                    f"Saved Mode ON | {indexed_count} chunks",
                    self.success
                )

        self._run_task(task, success, self._mode_switch_error)

    def _mode_switch_error(self, error):
        self._set_status("Mode switch failed", self.danger)
        self._show_error(error)

    def _update_mode_button(self):
        if self.temp_mode:
            self.mode_btn.configure(
                text="⚡ Temp RAM Mode",
                bg="#78350F",
                fg="#FDE68A",
                activebackground="#92400E"
            )
     
