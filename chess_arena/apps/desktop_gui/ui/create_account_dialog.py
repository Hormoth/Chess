from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QLabel,
    QMessageBox,
    QCheckBox,
)


class CreateAccountDialog(QDialog):
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self.setWindowTitle("Create Account")
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.email = QLineEdit()
        form.addRow("Email:", self.email)

        self.name = QLineEdit()
        form.addRow("Name:", self.name)

        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        form.addRow("Password:", self.password)

        layout.addLayout(form)

        self.is_bot = QCheckBox("Create as Bot account (gives API key)")
        layout.addWidget(self.is_bot)

        self.btn = QPushButton("Create Account")
        self.btn.clicked.connect(self.do_create)
        layout.addWidget(self.btn)

    def do_create(self):
        try:
            data = self.api.register(
                email=self.email.text().strip(),
                name=self.name.text().strip(),
                password=self.password.text(),
                is_bot=self.is_bot.isChecked(),
            )

            msg = f"Created account: {data['name']}"
            if data.get("api_key"):
                msg += f"\n\nBot API Key:\n{data['api_key']}"

            QMessageBox.information(self, "Account Created", msg)
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
