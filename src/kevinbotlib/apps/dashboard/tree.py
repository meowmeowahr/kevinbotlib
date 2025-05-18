from typing import Any

from PySide6.QtCore import QAbstractItemModel, QModelIndex, QPersistentModelIndex, Qt


class TreeItem:
    __slots__ = ("data", "key", "parent_item", "child_items", "userdata", "_row")

    def __init__(self, data: Any, key: str = "", parent: "TreeItem | None" = None, row: int = 0):
        self.data = data
        self.key = key
        self.parent_item = parent
        self._row = row  # precomputed row index

        self.child_items: list[TreeItem] = []
        self.userdata = None

        if isinstance(data, dict):
            # First check for "key" and skip children if present
            if "key" in data:
                self.userdata = data["key"]
                # Don't populate child_items, as it's sendable
            else:
                # Precompute children with their row index
                self.child_items = [TreeItem(v, k, self, i) for i, (k, v) in enumerate(data.items())]

    def child(self, row: int) -> "TreeItem | None":
        if 0 <= row < len(self.child_items):
            return self.child_items[row]
        return None

    def child_count(self) -> int:
        return len(self.child_items)

    def row(self) -> int:
        return self._row

    def parent(self) -> "TreeItem | None":
        return self.parent_item


class DictTreeModel(QAbstractItemModel):
    def __init__(self, data: dict):
        super().__init__()
        self.root_item = TreeItem(data)

    def index(self, row: int, column: int, parent: QModelIndex = QModelIndex()) -> QModelIndex:  # noqa: B008
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        parent_item = self.root_item if not parent.isValid() else parent.internalPointer()
        child_item = parent_item.child(row)
        if child_item:
            return self.createIndex(row, column, child_item)
        return QModelIndex()

    def parent(self, index: QModelIndex) -> QModelIndex:
        if not index.isValid():
            return QModelIndex()

        child_item = index.internalPointer()
        parent_item = child_item.parent()

        if parent_item is None or parent_item == self.root_item:
            return QModelIndex()

        return self.createIndex(parent_item.row(), 0, parent_item)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802, B008
        if parent.column() > 0:
            return 0

        parent_item = self.root_item if not parent.isValid() else parent.internalPointer()
        return parent_item.child_count()

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:  # noqa: N802, B008, ARG002
        return 1

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None

        item = index.internalPointer()

        if role == Qt.ItemDataRole.DisplayRole:
            if isinstance(item.data, dict):
                if item.userdata is not None:
                    return f"{item.key} [{item.userdata}]"
                return f"{item.key}"
        elif role == Qt.ItemDataRole.UserRole:
            return item.userdata

        return None

    def update_data(self, new_data: dict):
        self.beginResetModel()
        self.root_item = TreeItem(new_data)
        self.endResetModel()
