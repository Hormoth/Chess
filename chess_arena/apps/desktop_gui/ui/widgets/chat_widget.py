from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QHBoxLayout, QLineEdit, QPushButton
from PySide6.QtCore import Signal



class ChatWidget(QWidget):
    sendChat = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)

        row = QHBoxLayout()
        self.input = QLineEdit()
        self.btn = QPushButton("Send")
        self.btn.clicked.connect(self._send)
        self.input.returnPressed.connect(self._send)
        self.setObjectName("ChessBoardWidget")

        row.addWidget(self.input)
        row.addWidget(self.btn)
        layout.addLayout(row)

    def _send(self):
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self.sendChat.emit(text)

    def append(self, line: str):
        self.log.append(line)
