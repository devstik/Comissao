# models.py
from __future__ import annotations
from typing import List, Any, Set
from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex, QEvent, QItemSelection, QItemSelectionModel
from PySide6.QtWidgets import QStyledItemDelegate, QLineEdit, QTableView
from PySide6.QtGui import QFont, QColor, QKeyEvent
from decimal import Decimal, InvalidOperation

_NUMERIC_HINTS = {
    "Recebido","ICMSST","Frete","Rec Liquido",
    "Prazo Médio","Preço Médio","Preço Venda",
    "% Comissão","Valor Comissão"
}
def _is_num(header: str) -> bool:
    h = (header or "").strip()
    return h in _NUMERIC_HINTS or any(x in h.lower() for x in ["preço","receb","prazo","valor","%"])
def _s(v: Any) -> str:
    return "" if v is None else str(v)

class EditableTableModel(QAbstractTableModel):
    def __init__(self, headers: List[str], rows: List[List[Any]]):
        super().__init__()
        self.headers = list(headers)
        self.rows = [list(r) for r in rows]
        self._all_readonly = False
        self._editable_cols: Set[int] = set()
        
        # Estado de ordenação
        self._sort_column = -1
        self._sort_order = Qt.SortOrder.AscendingOrder

    # ---- API usada no main.py ----
    def set_all_readonly(self, value: bool):
        self._all_readonly = bool(value)
        tl = self.index(0,0)
        br = self.index(max(0,self.rowCount()-1), max(0,self.columnCount()-1))
        self.dataChanged.emit(tl, br, [Qt.ItemDataRole.EditRole])

    def set_columns_readonly(self, editable_headers: List[str]):
        self._editable_cols.clear()
        allow = set(editable_headers or [])
        for i,h in enumerate(self.headers):
            if h in allow:
                self._editable_cols.add(i)
        tl = self.index(0,0)
        br = self.index(max(0,self.rowCount()-1), max(0,self.columnCount()-1))
        self.dataChanged.emit(tl, br, [Qt.ItemDataRole.EditRole])

    def remove_rows(self, indices: List[int]):
        for r in sorted(indices, reverse=True):
            if 0 <= r < len(self.rows):
                self.beginRemoveRows(QModelIndex(), r, r)
                del self.rows[r]
                self.endRemoveRows()

    # ---- QAbstractTableModel ----
    def rowCount(self, parent=QModelIndex()): return 0 if parent.isValid() else len(self.rows)
    def columnCount(self, parent=QModelIndex()): return 0 if parent.isValid() else len(self.headers)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid(): return None
        r,c = index.row(), index.column()
        if r<0 or r>=len(self.rows) or c<0 or c>=len(self.headers): return None
        val = self.rows[r][c]; head = self.headers[c]
        
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return _s(val)
        
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if _is_num(head):
                return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        # Destaca a coluna ordenada
        if role == Qt.ItemDataRole.BackgroundRole:
            if c == self._sort_column:
                return QColor(30, 35, 50)
        
        # Coluna ordenada em negrito
        if role == Qt.ItemDataRole.FontRole:
            if c == self._sort_column:
                font = QFont()
                font.setBold(True)
                return font
        
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal:
            if role == Qt.ItemDataRole.DisplayRole:
                header = self.headers[section] if 0 <= section < len(self.headers) else ""
                # Adiciona seta indicadora de ordenação
                if section == self._sort_column:
                    arrow = " ▲" if self._sort_order == Qt.SortOrder.AscendingOrder else " ▼"
                    return header + arrow
                return header
            
            if role == Qt.ItemDataRole.FontRole:
                font = QFont()
                font.setBold(True)
                if section == self._sort_column:
                    font.setPointSize(font.pointSize() + 1)
                return font
        
        if orientation == Qt.Orientation.Vertical and role == Qt.ItemDataRole.DisplayRole:
            return section + 1
        
        return None

    def flags(self, index: QModelIndex):
        if not index.isValid(): return Qt.ItemFlag.NoItemFlags
        f = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        if not self._all_readonly:
            if (not self._editable_cols) or (index.column() in self._editable_cols):
                f |= Qt.ItemFlag.ItemIsEditable
        return f

    def setData(self, index: QModelIndex, value, role=Qt.ItemDataRole.EditRole):
        if role != Qt.ItemDataRole.EditRole or not index.isValid(): return False
        r,c = index.row(), index.column()
        if r<0 or r>=len(self.rows) or c<0 or c>=len(self.headers): return False
        if self._all_readonly: return False
        if self._editable_cols and c not in self._editable_cols: return False
        self.rows[r][c] = (value)
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole])
        return True

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder):
        """Implementa ordenação inteligente da tabela"""
        if column < 0 or column >= len(self.headers):
            return

        self.layoutAboutToBeChanged.emit()

        self._sort_column = column
        self._sort_order = order

        def convert_value(val):
            """Retorna uma chave ordenável com prioridade explícita:
            0 -> número (Decimal)
            1 -> data (yyyyMMdd string)
            2 -> competência (yyyymm)
            3 -> string (lowercase)
            4 -> empty
            """
            if val is None or val == "":
                return (4, "")

            val_str = str(val).strip()

            # Tenta número (normaliza BR -> US)
            try:
                num_str = val_str.replace(".", "").replace(",", ".")
                num_str = num_str.replace("%", "").strip()
                num_dec = Decimal(num_str)
                return (0, num_dec)
            except (InvalidOperation, ValueError):
                pass

            # Data no formato dd/mm/yyyy
            if "/" in val_str and len(val_str) == 10:
                try:
                    d, m, y = val_str.split("/")
                    return (1, f"{y}{m}{d}")
                except Exception:
                    pass

            # Competência tipo 'Jan-2024' ou similar
            if "-" in val_str and len(val_str) <= 12:
                month_map = {
                    "jan": "01", "fev": "02", "mar": "03", "abr": "04",
                    "mai": "05", "jun": "06", "jul": "07", "ago": "08",
                    "set": "09", "out": "10", "nov": "11", "dez": "12"
                }
                parts = val_str.lower().split("-")
                if len(parts) == 2 and parts[0] in month_map:
                    return (2, f"{parts[1]}{month_map[parts[0]]}")

            # Fallback: string
            return (3, val_str.lower())

        reverse = (order == Qt.SortOrder.DescendingOrder)
        self.rows.sort(key=lambda row: convert_value(row[column]), reverse=reverse)

        self.layoutChanged.emit()
        self.headerDataChanged.emit(Qt.Orientation.Horizontal, 0, len(self.headers) - 1)


class ExcelLikeTableView(QTableView):
    """
    Adiciona um atalho estilo planilha para expandir a seleção
    da célula atual até a última linha visível do model.
    """

    def _select_from_current_cell(self, target_row: int, target_column: int) -> bool:
        index = self.currentIndex()
        model = self.model()

        if not index.isValid() or model is None or model.rowCount() == 0:
            return False

        selection_model = self.selectionModel()

        if selection_model is None:
            return False

        target_row = max(0, min(target_row, model.rowCount() - 1))
        target_column = max(0, min(target_column, model.columnCount() - 1))

        top_left = model.index(index.row(), index.column())
        bottom_right = model.index(target_row, target_column)
        selection = QItemSelection(top_left, bottom_right)

        selection_model.select(
            selection,
            QItemSelectionModel.SelectionFlag.ClearAndSelect
            | QItemSelectionModel.SelectionFlag.Current
        )
        self.setCurrentIndex(top_left)
        self.scrollTo(bottom_right)
        return True

    def select_from_current_cell_to_bottom(self) -> bool:
        index = self.currentIndex()
        model = self.model()
        if not index.isValid() or model is None:
            return False
        return self._select_from_current_cell(model.rowCount() - 1, index.column())

    def select_from_current_cell_to_top(self) -> bool:
        index = self.currentIndex()
        if not index.isValid():
            return False
        return self._select_from_current_cell(0, index.column())

    def select_from_current_cell_to_right(self) -> bool:
        index = self.currentIndex()
        model = self.model()
        if not index.isValid() or model is None:
            return False
        return self._select_from_current_cell(index.row(), model.columnCount() - 1)

    def select_from_current_cell_to_left(self) -> bool:
        index = self.currentIndex()
        if not index.isValid():
            return False
        return self._select_from_current_cell(index.row(), 0)

    def keyPressEvent(self, event: QKeyEvent):
        if _handle_excel_selection_shortcut(self, event):
            event.accept()
            return

        super().keyPressEvent(event)


class ShortcutSelectAllLineEdit(QLineEdit):
    """
    Encaminha Ctrl+Shift+Seta para baixo para a tabela,
    expandindo a seleção a partir da célula atual.
    """

    def __init__(self, table_view: QTableView | None = None, parent=None):
        super().__init__(parent)
        self.table_view = table_view

    def _handle_select_all_shortcut(self, event) -> bool:
        if self.table_view is None:
            return False
        return _handle_excel_selection_shortcut(self.table_view, event)

    def event(self, event):
        if event.type() == QEvent.Type.ShortcutOverride and self._handle_select_all_shortcut(event):
            return True
        return super().event(event)

    def keyPressEvent(self, event: QKeyEvent):
        if self._handle_select_all_shortcut(event):
            return

        super().keyPressEvent(event)

class DecimalDelegate(QStyledItemDelegate):
    """
    Delegate para formatação automática de decimais
    Usuario digita: 3 → Formata para: 3,0000
    """
    
    def __init__(self, decimal_places=2, parent=None):
        super().__init__(parent)
        self.decimal_places = decimal_places
    
    def createEditor(self, parent, option, index):
        editor = ShortcutSelectAllLineEdit(table_view=self.parent(), parent=parent)
        editor.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        return editor
    
    def setEditorData(self, editor, index):
        value = index.data(Qt.EditRole)
        if value:
            value_str = str(value).replace(".", "").replace(",", ".")
            try:
                value_float = float(value_str)
                editor.setText(str(value_float))
            except:
                editor.setText(str(value))
        else:
            editor.setText("")
    
    def setModelData(self, editor, model, index):
        from utils.formatters import fmt_num
        
        text = editor.text().strip()
        
        if not text:
            formatted = fmt_num(0, self.decimal_places)
            model.setData(index, formatted, Qt.EditRole)
            return
        
        try:
            value_str = text.replace(",", ".")
            value_float = float(value_str)
            formatted = fmt_num(value_float, self.decimal_places)
            model.setData(index, formatted, Qt.EditRole)
        except ValueError:
            model.setData(index, text, Qt.EditRole)


def _handle_excel_selection_shortcut(table_view: QTableView, event) -> bool:
    modifiers = event.modifiers()
    ctrl_shift = (
        modifiers & Qt.KeyboardModifier.ControlModifier
        and modifiers & Qt.KeyboardModifier.ShiftModifier
    )

    if not ctrl_shift:
        return False

    handlers = {
        Qt.Key.Key_Down: "select_from_current_cell_to_bottom",
        Qt.Key.Key_Up: "select_from_current_cell_to_top",
        Qt.Key.Key_Right: "select_from_current_cell_to_right",
        Qt.Key.Key_Left: "select_from_current_cell_to_left",
    }

    method_name = handlers.get(event.key())
    if not method_name or not hasattr(table_view, method_name):
        return False

    handled = getattr(table_view, method_name)()
    if handled:
        event.accept()
    return handled
