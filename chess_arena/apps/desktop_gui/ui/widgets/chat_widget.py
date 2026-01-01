# chat_widget.py - Enhanced Chat Widget

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, 
    QPushButton, QLabel, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, Signal
from datetime import datetime


class ChatWidget(QWidget):
    """Chat widget for in-game or lobby chat."""
    
    sendChat = Signal(str)
    
    def __init__(self, title: str = "Chat", parent=None):
        super().__init__(parent)
        self.setObjectName("ChatPanel")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Header
        header = QLabel(title)
        header.setObjectName("SectionHeader")
        layout.addWidget(header)
        
        # Messages area
        self.messages = QTextEdit()
        self.messages.setReadOnly(True)
        self.messages.setStyleSheet("""
            QTextEdit {
                background: #0a0e14;
                border: 1px solid #1f2a3a;
                border-radius: 8px;
                padding: 8px;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.messages, stretch=1)
        
        # Input area
        input_row = QHBoxLayout()
        input_row.setSpacing(8)
        
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type a message...")
        self.input.returnPressed.connect(self._send)
        input_row.addWidget(self.input)
        
        self.send_btn = QPushButton("Send")
        self.send_btn.setFixedWidth(70)
        self.send_btn.clicked.connect(self._send)
        input_row.addWidget(self.send_btn)
        
        layout.addLayout(input_row)
    
    def _send(self):
        text = self.input.text().strip()
        if text:
            self.sendChat.emit(text)
            self.input.clear()
    
    def append(self, message: str):
        """Add a message to the chat."""
        timestamp = datetime.now().strftime("%H:%M")
        self.messages.append(f'<span style="color: #6b7d99;">[{timestamp}]</span> {message}')
        
        # Scroll to bottom
        scrollbar = self.messages.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def append_system(self, message: str):
        """Add a system message."""
        self.messages.append(f'<span style="color: #8fa4bf; font-style: italic;">{message}</span>')
        scrollbar = self.messages.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def append_player(self, player_name: str, message: str, is_opponent: bool = False):
        """Add a player message with formatting."""
        timestamp = datetime.now().strftime("%H:%M")
        color = "#c53030" if is_opponent else "#40916c"
        self.messages.append(
            f'<span style="color: #6b7d99;">[{timestamp}]</span> '
            f'<span style="color: {color}; font-weight: 600;">{player_name}:</span> {message}'
        )
        scrollbar = self.messages.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear_messages(self):
        """Clear all messages."""
        self.messages.clear()
