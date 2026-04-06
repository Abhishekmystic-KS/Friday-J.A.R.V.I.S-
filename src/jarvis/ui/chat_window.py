"""Standalone chat window for RAG knowledge base queries."""

import sys
import threading
import tkinter as tk
import importlib
from pathlib import Path
from tkinter import scrolledtext

RAG_DIR = Path(__file__).resolve().parents[3] / "RAG"
if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

def _load_answer_query():
    try:
        mod = importlib.import_module("retriever")
        return getattr(mod, "answer_query", None)
    except Exception:
        return None


answer_query = _load_answer_query()
RAG_AVAILABLE = answer_query is not None


class ChatWindow:
    """
    Standalone window for RAG knowledge base queries.
    Opens as independent window (600x500), can be moved/resized/closed separately from robo popup.
    Runs RAG queries in background thread to avoid blocking UI.
    """

    _instance = None  # Singleton to prevent multiple windows

    def __new__(cls):
        if cls._instance is not None:
            # Bring existing window to front
            cls._instance.window.deiconify()
            cls._instance.window.lift()
            cls._instance.window.focus_force()
            cls._instance.input_field.focus_force()
            return cls._instance
        return super().__new__(cls)

    def __init__(self):
        if ChatWindow._instance is not None:
            return
        
        ChatWindow._instance = self
        
        self.query_thread = None
        self.rag_available = RAG_AVAILABLE
        self.answer_query_fn = answer_query

        # Create standalone window
        self.window = tk.Toplevel()
        self.window.title("FRIDAY - RAG Chat")
        self.window.geometry("600x500")
        self.window.minsize(520, 360)
        # Modern color palette
        bg_main = "#1e1e2e"
        bg_header = "#181825"
        bg_text = "#11111b"
        bg_input = "#313244"
        text_fg = "#cdd6f4"
        accent_color = "#89b4fa"
        btn_bg = "#89b4fa"
        btn_fg = "#11111b"

        self.window.configure(bg=bg_main)
        
        # Icon/styling
        self.window.resizable(True, True)
        self.window.attributes("-topmost", False)

        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self.close_window)

        # Stable layout so input row is always visible.
        self.window.grid_columnconfigure(0, weight=1)
        self.window.grid_rowconfigure(1, weight=1)

        # Header
        header = tk.Frame(self.window, bg=bg_header)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        title = tk.Label(
            header,
            text="💬 FRIDAY - RAG Knowledge Chat",
            fg=accent_color,
            bg=bg_header,
            font=("Helvetica", 11, "bold"),
            pady=8,
        )
        title.pack(side="left", padx=10)

        # Message history (read-only text widget)
        self.message_display = scrolledtext.ScrolledText(
            self.window,
            bg=bg_text,
            fg=text_fg,
            font=("Helvetica", 10),
            wrap="word",
            state="disabled",
            relief="flat",
            padx=10,
            pady=10,
            highlightthickness=0,
            borderwidth=0,
        )
        self.message_display.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        # Configure text tags for styling
        self.message_display.tag_config("user", foreground="#89b4fa", font=("Helvetica", 10, "bold"))
        self.message_display.tag_config("rag", foreground="#a6e3a1")
        self.message_display.tag_config("error", foreground="#f38ba8")
        self.message_display.tag_config("thinking", foreground="#f9e2af", font=("Helvetica", 10, "italic"))

        # Input frame
        input_frame = tk.Frame(self.window, bg=bg_main)
        input_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        input_frame.grid_columnconfigure(0, weight=1)

        self.input_field = tk.Entry(
            input_frame,
            bg=bg_input,
            fg=text_fg,
            insertbackground=text_fg,
            font=("Helvetica", 10),
            relief="flat",
            highlightthickness=1,
            highlightbackground="#45475a",
            highlightcolor=accent_color,
            takefocus=1,
        )
        self.input_field.grid(row=0, column=0, sticky="ew", padx=(0, 8), ipady=6)
        self.input_field.bind("<Return>", lambda e: self.send_query())

        self.send_btn = tk.Button(
            input_frame,
            text="Send",
            command=self.send_query,
            bg=btn_bg,
            fg=btn_fg,
            activebackground="#b4befe",
            activeforeground="#11111b",
            font=("Helvetica", 10, "bold"),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            cursor="hand2",
            padx=15,
            pady=4,
        )
        self.send_btn.grid(row=0, column=1, sticky="e")

        # Message history storage
        self.messages = []
        self.max_messages = 30

        # Check RAG availability
        if not self.rag_available:
            self._add_message(
                "System",
                "⚠️ RAG module not available. Ensure chromadb is installed:\npip install chromadb langchain-text-splitters requests",
                "error",
            )
        else:
            self._add_message(
                "FRIDAY",
                "👋 Hello! Ask me about anything in the knowledge base.",
                "rag",
            )

        self.window.after(100, self.input_field.focus_force)

    def _add_message(self, sender, text, tag="rag"):
        """Add message to display and store in history."""
        self.messages.append({"sender": sender, "text": text})

        # Keep only last 30 messages
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)

        # Update display
        self.message_display.config(state="normal")
        self.message_display.insert("end", f"{sender}: ", f"{tag}")
        self.message_display.insert("end", f"{text}\n\n")
        self.message_display.see("end")  # Auto-scroll to bottom
        self.message_display.config(state="disabled")

    def send_query(self):
        """Send RAG query in background thread."""
        query = self.input_field.get().strip()
        if not query:
            return

        # Lazy-load RAG import so users can type even if env changed after app start.
        if self.answer_query_fn is None:
            try:
                self.answer_query_fn = _load_answer_query()
                if self.answer_query_fn is None:
                    raise RuntimeError("answer_query_not_available")
                self.rag_available = True
                self._add_message("System", "✅ RAG module loaded. You can ask now.", "rag")
            except Exception:
                self._add_message(
                    "System",
                    "RAG still unavailable. Install deps and restart app:\npip install bytez chromadb langchain-text-splitters requests",
                    "error",
                )
                return

        # Clear input field
        self.input_field.delete(0, tk.END)

        # Add user message
        self._add_message("You", query, "user")

        # Show thinking indicator
        self._add_message("FRIDAY", "Thinking...", "thinking")

        # Disable send button while processing
        self.send_btn.config(state="disabled")

        # Run RAG query in background thread
        self.query_thread = threading.Thread(target=self._query_rag, args=(query,), daemon=True)
        self.query_thread.start()

    def _query_rag(self, query):
        """Execute RAG query (runs in background thread)."""
        try:
            # Call RAG retriever
            result = self.answer_query_fn(query, k=5, threshold=0.7)

            # Remove "Thinking..." message
            if self.messages and self.messages[-1]["text"] == "Thinking...":
                self.messages.pop()

            # Update display - remove thinking indicator
            self.message_display.config(state="normal")
            self.message_display.delete("end-2c linestart", "end")
            self.message_display.config(state="disabled")

            # Add RAG response
            self._add_message("FRIDAY", result if result else "No relevant knowledge found.", "rag")

        except Exception as e:
            # Remove thinking indicator and show error
            if self.messages and self.messages[-1]["text"] == "Thinking...":
                self.messages.pop()

            self.message_display.config(state="normal")
            self.message_display.delete("end-2c linestart", "end")
            self.message_display.config(state="disabled")

            error_msg = f"Error querying knowledge base: {str(e)}"
            self._add_message("System", error_msg, "error")

        finally:
            # Re-enable send button
            self.send_btn.config(state="normal")
            self.input_field.focus()

    def close_window(self):
        """Close the chat window and reset singleton."""
        ChatWindow._instance = None
        self.window.destroy()


def launch_chat_window():
    """Launch chat window (or bring to front if already open)."""
    ChatWindow()
