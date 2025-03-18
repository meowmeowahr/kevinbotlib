from qtpy.QtCore import QModelIndex, QPersistentModelIndex
from qtpy.QtGui import QPainter
from qtpy.QtWidgets import QApplication, QStyle, QStyledItemDelegate, QStyleOptionViewItem


class NoFocusDelegate(QStyledItemDelegate):
    """Qt QStyledItemDelegate that removes the focus indicator"""

    def paint(self, painter, option: QStyleOptionViewItem, index):
        option.state = QStyle.StateFlag.State_Enabled  # type: ignore
        super().paint(painter, option, index)


class ComboBoxNoTextDelegate(QStyledItemDelegate):
    """Qt QStyledItemDelegate that removes text from QComboBox"""

    def __init__(self, parent=None):
        super().__init__(parent)

    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex | QPersistentModelIndex
    ) -> None:
        # Create a copy of the style option
        opt = option

        # Initialize the style option with the index data
        self.initStyleOption(opt, index)

        # Set decoration width to match the rect width
        opt.decorationSize.setWidth(opt.rect.width())

        # Get the style from the widget or application
        style = opt.widget.style() if opt.widget else QApplication.style()

        # Draw the item using the style
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, opt.widget)
