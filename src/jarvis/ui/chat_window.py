"""Standalone chat window for RAG knowledge base queries."""

import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import scrolledtext

RAG_DIR = Path(__file__).resolve().parents[3] / "RAG"
if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

# Try to import RAG module
try:
    from retriever import answer_query
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    answer_query = None


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
            cls._instance.window.lift()
            cls._instance.window.focus()
            return cls._instance
        return super().__new__(cls)

    def __init__(self):
        if ChatWindow._instance is not None:
            return
        
        ChatWindow._instance = self
        
        self.query_thread = None
        self.rag_available = RAG_AVAILABLE

        # Create standalone window
        self.window = tk.Toplevel()
        self.window.title("FRIDAY - RAG Chat")
        self.window.geometry("600x500")
        self.window.configure(bg="#1a1a1a")
        
        # Icon/styling
        self.window.resizable(True, True)
        self.window.attributes("-topmost", False)

        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self.close_window)

        # Header
        header = tk.Frame(self.window, bg="#0d0d0d")
        header.pack(side="top", fill="x", padx=5, pady=5)

        title = tk.Label(
            header,
            text="💬 FRIDAY - RAG Knowledge Chat",
            fg="#00ff00",
            bg="#0d0d0d",
            font=("Mono", 11, "bold"),
        )
        title.pack(side="left", padx=5)

        # Message history (read-only text widget)
        self.message_display = scrolledtext.ScrolledText(
            self.window,
            bg="#0a0a0a",
            fg="#00ff00",
            font=("Mono", 9),
            wrap="word",
            state="disabled",
            relief="flat",
            bd=1,
        )
        self.message_display.pack(side="top", fill="both", expand=True, padx=5, pady=5)

        # Configure text tags for styling
        self.message_display.tag_config("user", foreground="#00ffff")
        self.message_display.tag_config("rag", foreground="#00ff00")
        self.message_display.tag_config("error", foreground="#ff6b6b")
        self.message_display.tag_config("thinking", foreground="#ffff00")

        # Input frame
        input_frame = tk.Frame(self.window, bg="#1a1a1a")
        input_frame.pack(side="bottom", fill="x", padx=5, pady=5)

        self.input_field = tk.Entry(
            input_frame,
            bg="#0d0d0d",
            fg="#00ff00",
            font=("Mono", 9),
            relief="flat",
            bd=1,
        )
        self.input_field.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.input_field.bind("<Return>", lambda e: self.send_query())

        self.send_btn = tk.Button(
            input_frame,
            text="Send",
            command=self.send_query,
            bg="#0d0d0d",
            fg="#00ff00",
            font=("Mono", 8, "bold"),
            relief="flat",
            bd=1,
            padx=15,
        )
        self.send_btn.pack(side="right")

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
            self.input_field.config(state="disabled")
            self.send_btn.config(state="disabled")
        else:
            self._add_message(
                "FRIDAY",
                "👋 Hello! Ask me about anything in the knowledge base.",
                "rag",
            )

        self.input_field.focus()

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
        if not self.rag_available:
            self._add_message("System", "RAG not available. Cannot process query.", "error")
            return

        query = self.input_field.get().strip()
        if not query:
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
            result = answer_query(query, k=5, threshold=0.7)

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
