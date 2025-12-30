from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QPushButton, QLabel, QMessageBox, QHBoxLayout

class LoginDialog(QDialog):
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self.setWindowTitle("Login")
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Email"))
        self.email = QLineEdit()
        self.email.setPlaceholderText("you@example.com")
        layout.addWidget(self.email)

        layout.addWidget(QLabel("Password"))
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password)

        row = QHBoxLayout()
        row.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_login = QPushButton("Login")
        self.btn_login.setDefault(True)
        self.btn_login.clicked.connect(self.do_login)

        row.addWidget(self.btn_cancel)
        row.addWidget(self.btn_login)
        layout.addLayout(row)

    def do_login(self):
        try:
            self.api.login(self.email.text().strip(), self.password.text())
            QMessageBox.information(self, "OK", f"Logged in as {self.api.name}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
