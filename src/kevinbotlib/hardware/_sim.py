import binascii
import unicodedata

import serial
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from kevinbotlib.simulator.windowview import (
    WindowView,
    WindowViewOutputPayload,
    register_window_view,
)


class SerialConsolePage(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(QFont("monospace"))
        self.console.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.layout.addWidget(self.console)

        self.input_layout = QHBoxLayout()
        self.layout.addLayout(self.input_layout)

        self.bin_button = QPushButton("Bin")
        self.input_layout.addWidget(self.bin_button)

        self.input_line = QLineEdit()
        self.input_layout.addWidget(self.input_line)

        self.send_button = QPushButton("Send")
        self.input_layout.addWidget(self.send_button)

        self.newline_type_box = QComboBox()
        self.newline_type_box.addItems(["LF", "CRLF", "No Newline"])
        self.newline_type_box.setCurrentIndex(0)
        self.input_layout.addWidget(self.newline_type_box)

    def get_newline(self):
        match self.newline_type_box.currentText():
            case "LF":
                return b"\n"
            case "CRLF":
                return b"\r\n"
            case "No Newline":
                return b""
            case _:
                msg = f"Invalid newline type: {self.newline_type_box.currentText()}"
                raise ValueError(msg)


class SerialTxPayload(WindowViewOutputPayload):
    def __init__(self, payload: bytes):
        self._payload = payload

    def payload(self) -> bytes:
        return self._payload


def repr_byte_data(data: bytes) -> str:
    result = ""
    for char in data:
        try:
            bytes([char]).decode("utf-8", errors="strict")
            if unicodedata.category(chr(char)) in ("Cc", "Cf"):
                result += f"<span style='color: yellow'>\\{char:02x}</span>"
            else:
                result += bytes([char]).decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            result += f"<span style='color: red'>\\{char:02x}</span>"
    return result


class BinaryFrameMaker(QDialog):
    # Define signal to emit binary data
    data_submitted = Signal(bytearray)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Binary Frame Maker")
        self.data = bytearray()

        layout = QVBoxLayout()

        instructions = QLabel("Enter hex values (e.g., 'FF 0A' or 'FF0A') in the left panel. UTF-8 view on the right.")
        layout.addWidget(instructions)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.hex_edit = QTextEdit()
        self.hex_edit.setPlaceholderText("Enter hex values (e.g., FF 0A)")
        self.hex_edit.textChanged.connect(self.update_from_hex)
        splitter.addWidget(self.hex_edit)

        self.utf8_view = QTextEdit()
        self.utf8_view.setReadOnly(True)
        self.utf8_view.setPlaceholderText("UTF-8 representation")
        splitter.addWidget(self.utf8_view)

        layout.addWidget(splitter)

        button_layout = QHBoxLayout()
        layout.addLayout(button_layout)
        button_layout.addStretch()

        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.submit_data)
        button_layout.addWidget(self.submit_button)

        self.status_label = QStatusBar(self)
        self.status_label.setSizeGripEnabled(False)
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def update_from_hex(self):
        try:
            # Get hex text and clean it
            hex_text = self.hex_edit.toPlainText().replace(" ", "").replace("\n", "")
            if len(hex_text) % 2 != 0:
                self.status_label.showMessage("Invalid hex: Odd number of characters")
                return

            self.data = bytearray(binascii.unhexlify(hex_text))
            self.utf8_view.setText(repr_byte_data(self.data))

            self.status_label.showMessage(f"Valid: {len(self.data)} bytes")
        except binascii.Error:
            self.status_label.showMessage("Invalid hex characters")
            self.data = bytearray()
            self.utf8_view.setPlainText("")

    def submit_data(self):
        if self.data:
            self.data_submitted.emit(self.data)
            self.status_label.showMessage("Data submitted")
            self.accept()  # Close dialog
        else:
            self.status_label.showMessage("No valid data to submit")


@register_window_view("kevinbotlib.serial.internal.view")
class SerialWindowView(WindowView):
    new_tab = Signal(str)
    new_data = Signal(str, bytes)

    def __init__(self):
        super().__init__()
        self.widget = QWidget()
        self.layout = QVBoxLayout(self.widget)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("CompactTabs")
        self.layout.addWidget(self.tabs)

        self.pages: dict[str, SerialConsolePage] = {}
        self.new_tab.connect(self.create_tab)
        self.new_data.connect(self.add_data)

    def generate(self) -> QWidget:
        return self.widget

    @property
    def title(self):
        return "Serial Devices"

    def create_tab(self, devname: str):
        if devname not in self.pages:
            page = SerialConsolePage()
            page.send_button.clicked.connect(lambda: self.send(devname))
            page.bin_button.clicked.connect(lambda: self.make_binary(devname))
            page.input_line.returnPressed.connect(lambda: self.send(devname))
            self.tabs.addTab(page, devname)
            self.pages[devname] = page
        self.tabs.setCurrentWidget(self.pages[devname])

    def add_data(self, devname: str, data: bytes):
        page = self.pages.get(devname)
        if page:
            page.console.append("<b>Received &lt;&lt;&lt; </b>" + repr_byte_data(data))

    def send(self, devname: str):
        page = self.pages.get(devname)
        self.send_payload(SerialTxPayload(page.input_line.text().encode("utf-8") + page.get_newline()))
        page.console.append(
            "<b>Sent&nbsp;&nbsp;&nbsp;&nbsp; &gt;&gt;&gt; </b>"
            + repr_byte_data(page.input_line.text().encode("utf-8") + page.get_newline())
        )
        page.input_line.clear()

    def make_binary(self, devname: str):
        tool = BinaryFrameMaker(self.widget)
        if tool.exec() and tool.data:
            self.send_payload(SerialTxPayload(tool.data))
            page = self.pages.get(devname)
            self.send_payload(SerialTxPayload(page.input_line.text().encode("utf-8")))
            page.console.append("<b>Sent&nbsp;&nbsp;&nbsp;&nbsp; &gt;&gt;&gt; </b>" + repr_byte_data(tool.data))
            page.input_line.clear()

    def update(self, payload):
        if isinstance(payload, dict):
            match payload["type"]:
                case "new":
                    self.new_tab.emit(payload["name"])
                case "write":
                    self.new_data.emit(payload["name"], payload["data"])


class SimSerial:
    def __init__(
        self,
        port=None,
        baudrate=9600,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=None,
        xonxoff=False,  # noqa: FBT002
        rtscts=False,  # noqa: FBT002
        write_timeout=None,
        dsrdtr=False,  # noqa: FBT002
        inter_byte_timeout=None,
        exclusive=None,
    ):
        self.is_open = True
        self.portstr = None
        self.name = None

        self._port = port
        self._baudrate = baudrate
        self._bytesize = bytesize
        self._parity = parity
        self._stopbits = stopbits
        self._timeout = timeout
        self._write_timeout = write_timeout
        self._xonxoff = xonxoff
        self._rtscts = rtscts
        self._dsrdtr = dsrdtr
        self._inter_byte_timeout = inter_byte_timeout
        self._rs485_mode = None
        self._exclusive = exclusive

        self.mock_buffer = b""

    @property
    def port(self):
        return self._port

    @property
    def baudrate(self):
        return self._baudrate

    def append_mock_buffer_internal(self, data: bytes):
        self.mock_buffer += data

    def write(self, data: bytes):
        raise NotImplementedError

    def read(self, size=1):
        """Simulate reading `size` bytes from the serial buffer."""
        data = self.mock_buffer[:size]
        self.mock_buffer = self.mock_buffer[size:]
        return data

    def readline(self):
        """Simulate reading a line, ending with a newline character."""
        newline_index = self.mock_buffer.find(b"\n")
        if newline_index == -1:
            # No newline found, return entire buffer
            data = self.mock_buffer
            self.mock_buffer = b""
        else:
            data = self.mock_buffer[: newline_index + 1]
            self.mock_buffer = self.mock_buffer[newline_index + 1 :]
        return data

    def readlines(self, hint=-1):
        """Simulate reading all lines (or up to hint bytes)."""
        lines = []
        total = 0
        while b"\n" in self.mock_buffer:
            line = self.readline()
            lines.append(line)
            total += len(line)
            if 0 < hint <= total:
                break
        return lines

    def read_until(self, expected=b"\n", size: int | None = None):
        """Simulate reading a line, ending with a newline character."""
        newline_index = self.mock_buffer.find(expected)
        if newline_index == -1:
            # No newline found
            if size is not None:
                data = self.mock_buffer[:size]
                self.mock_buffer = self.mock_buffer[size:]
            else:
                data = self.mock_buffer
                self.mock_buffer = b""
        else:
            end_index = newline_index + 1
            if size is not None and end_index > size:
                data = self.mock_buffer[:size]
                self.mock_buffer = self.mock_buffer[size:]
            else:
                data = self.mock_buffer[:end_index]
                self.mock_buffer = self.mock_buffer[end_index:]
        return data

    @property
    def in_waiting(self):
        """Number of bytes in the mock buffer waiting to be read."""
        return len(self.mock_buffer)
