import unicodedata

import serial
from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget,
    QTabWidget,
    QVBoxLayout,
    QTextEdit,
    QLineEdit,
    QHBoxLayout,
    QPushButton,
)

from kevinbotlib.simulator.windowview import (
    register_window_view,
    WindowView,
    WindowViewOutputPayload,
)


class SerialConsolePage(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(QFont("monospace"))
        self.layout.addWidget(self.console)

        self.input_layout = QHBoxLayout()
        self.layout.addLayout(self.input_layout)

        self.input_line = QLineEdit()
        self.input_layout.addWidget(self.input_line)

        self.send_button = QPushButton("Send")
        self.input_layout.addWidget(self.send_button)

class SerialTxPayload(WindowViewOutputPayload):
    def __init__(self, payload: bytes):
        self._payload = payload

    def payload(self) -> bytes:
        return self._payload

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
        return "Mock Serial Devices"

    @staticmethod
    def _decode(data: bytes) -> str:
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

    def create_tab(self, devname: str):
        if devname not in self.pages:
            page = SerialConsolePage()
            page.send_button.clicked.connect(lambda: self.send(devname))
            page.input_line.returnPressed.connect(lambda: self.send(devname))
            self.tabs.addTab(page, devname)
            self.pages[devname] = page
        self.tabs.setCurrentWidget(self.pages[devname])

    def add_data(self, devname: str, data: bytes):
        page = self.pages.get(devname)
        if page:
            page.console.append("<b>Received &lt;&lt;&lt; </b>" + self._decode(data))

    def send(self, devname: str):
        page = self.pages.get(devname)
        self.send_payload(SerialTxPayload(page.input_line.text().encode("utf-8")))
        page.console.append("<b>Sent     &gt;&gt;&gt; </b>" + self._decode(page.input_line.text().encode("utf-8")))
        page.input_line.clear()

    def update(self, payload):
        if isinstance(payload, dict):
            match payload["type"]:
                case "new":
                    self.new_tab.emit(payload["name"])
                case "write":
                    self.new_data.emit(payload["name"], payload["data"])

class SimSerial:
    def __init__(self,
                 port=None,
                 baudrate=9600,
                 bytesize=serial.EIGHTBITS,
                 parity=serial.PARITY_NONE,
                 stopbits=serial.STOPBITS_ONE,
                 timeout=None,
                 xonxoff=False,
                 rtscts=False,
                 write_timeout=None,
                 dsrdtr=False,
                 inter_byte_timeout=None,
                 exclusive=None,
                 **kwargs):
        self.is_open = False
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
        newline_index = self.mock_buffer.find(b'\n')
        if newline_index == -1:
            # No newline found, return entire buffer
            data = self.mock_buffer
            self.mock_buffer = b""
        else:
            data = self.mock_buffer[:newline_index + 1]
            self.mock_buffer = self.mock_buffer[newline_index + 1:]
        return data

    def readlines(self, hint=-1):
        """Simulate reading all lines (or up to hint bytes)."""
        lines = []
        total = 0
        while b'\n' in self.mock_buffer:
            line = self.readline()
            lines.append(line)
            total += len(line)
            if 0 < hint <= total:
                break
        return lines

    @property
    def in_waiting(self):
        """Number of bytes in the mock buffer waiting to be read."""
        return len(self.mock_buffer)