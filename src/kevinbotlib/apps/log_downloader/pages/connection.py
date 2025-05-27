import paramiko
from PySide6.QtCore import Signal
from PySide6.QtGui import QFont, QPixmap, Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from kevinbotlib.apps.common.dnd import DragDropLabel


class ConnectionForm(QWidget):
    auth_pwd = Signal(str, int, str, str)
    auth_key = Signal(str, int, str, paramiko.RSAKey)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.private_key_file = ""

        self.root_layout = QVBoxLayout(self)
        self.root_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.root_layout.addStretch()

        self.icon = QLabel()
        self.icon.setPixmap(QPixmap(":/app_icons/log-downloader-128.svg"))
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.root_layout.addWidget(self.icon)

        self.title = QLabel("Connect to Host")
        self.title.setFont(QFont(self.font().family(), 20, QFont.Weight.Light))
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.root_layout.addWidget(self.title)

        self.root_layout.addSpacing(16)

        self.tabs = QTabWidget()
        self.root_layout.addWidget(self.tabs)

        self.password_widget = QWidget()
        self.tabs.addTab(self.password_widget, "Password Authentication")

        self.password_form = QFormLayout()
        self.password_widget.setLayout(self.password_form)

        self.password_host = QLineEdit(placeholderText="Robot Address e.g. 10.0.0.2")
        self.password_host.textChanged.connect(self.check_button_enabled)
        self.password_form.addRow("Host", self.password_host)

        self.password_port = QSpinBox(minimum=1, maximum=65535, value=22)
        self.password_form.addRow("Port", self.password_port)

        self.password_user = QLineEdit(placeholderText="Username")
        self.password_user.textChanged.connect(self.check_button_enabled)
        self.password_form.addRow("Username", self.password_user)

        self.password_password = QLineEdit(placeholderText="Password", echoMode=QLineEdit.EchoMode.Password)
        self.password_password.textChanged.connect(self.check_button_enabled)
        self.password_form.addRow("Password", self.password_password)

        self.key_widget = QWidget()
        self.tabs.addTab(self.key_widget, "Key Authentication")

        self.key_form = QFormLayout()
        self.key_widget.setLayout(self.key_form)

        self.key_host = QLineEdit(placeholderText="Robot Address e.g. 10.0.0.2")
        self.key_host.textChanged.connect(self.check_button_enabled)
        self.key_form.addRow("Host", self.key_host)

        self.key_port = QSpinBox(minimum=1, maximum=65535, value=22)
        self.key_port.textChanged.connect(self.check_button_enabled)
        self.key_form.addRow("Port", self.key_port)

        self.key_user = QLineEdit(placeholderText="Username")
        self.key_user.textChanged.connect(self.check_button_enabled)
        self.key_form.addRow("Username", self.key_user)

        self.key_dnd = DragDropLabel("Drop Private Key\n(or click to pick)")
        self.key_dnd.mouseReleaseEvent = self.load_pkey_file
        self.key_dnd.path_changed.connect(self.set_key_path)

        self.key_form.addRow("Private Key", self.key_dnd)

        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.attempt_connection)
        self.connect_button.setDisabled(True)
        self.root_layout.addWidget(self.connect_button)

        self.root_layout.addStretch()

        self.tabs.currentChanged.connect(self.check_button_enabled)

    def load_pkey_file(self, _event):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Private Key File", "", "Private Key Files (*.pem *.ppk *.pvk *.rsa *.key)"
        )
        if path:
            self.set_key_path(path)

    def set_key_path(self, path):
        self.private_key_file = path
        self.key_dnd.setText(path)
        self.check_button_enabled()

    def attempt_connection(self):
        if self.tabs.currentIndex() == 0:
            self.auth_pwd.emit(
                self.password_host.text(),
                self.password_port.value(),
                self.password_user.text(),
                self.password_password.text(),
            )
        else:
            pkey = paramiko.RSAKey.from_private_key_file(self.private_key_file)
            self.auth_key.emit(
                self.key_host.text(),
                self.key_port.value(),
                self.key_user.text(),
                pkey,
            )

    def check_button_enabled(self):
        match self.tabs.currentIndex():
            case 0:
                self.connect_button.setDisabled(
                    not self.password_host.text() or not self.password_user.text() or not self.password_password.text()
                )
            case 1:
                self.connect_button.setDisabled(
                    not self.key_host.text() or not self.key_user.text() or not self.private_key_file
                )
