from pathlib import Path
from typing import Any, Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase, QKeySequence
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QInputDialog,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QKeySequenceEdit,
)

from streamer_sidekick.modules.counter.service import default_counter_config


class CounterPresetDialog(QDialog):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        preset_name: str = "",
        counters: Optional[list[dict[str, Any]]] = None,
        reserved_hotkeys: Optional[dict[str, str]] = None,
        marker_files: Optional[list[str]] = None,
        create_marker_file: Optional[Callable[[str], str]] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Preset do contador")
        self.resize(860, 680)
        self.forms: list[CounterForm] = []
        self.marker_files = marker_files or []
        self.create_marker_file = create_marker_file
        self.reserved_hotkeys = {
            _normalize_hotkey(sequence): label
            for sequence, label in (reserved_hotkeys or {}).items()
            if _normalize_hotkey(sequence)
        }

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        title = QLabel("Preset do contador")
        title.setObjectName("PageTitle")
        root.addWidget(title)

        name_row = QFormLayout()
        self.name_input = QLineEdit(preset_name)
        self.name_input.setPlaceholderText("Nome do preset")
        name_row.addRow("Nome", self.name_input)
        root.addLayout(name_row)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        actions = QHBoxLayout()
        add_counter = QPushButton("Adicionar contador")
        add_counter.clicked.connect(self._add_counter)
        duplicate_counter = QPushButton("Duplicar contador")
        duplicate_counter.clicked.connect(self._duplicate_current_counter)
        remove_counter = QPushButton("Remover contador")
        remove_counter.clicked.connect(self._remove_current_counter)
        actions.addWidget(add_counter)
        actions.addWidget(duplicate_counter)
        actions.addWidget(remove_counter)
        actions.addStretch(1)
        root.addLayout(actions)

        footer = QHBoxLayout()
        footer.addStretch(1)
        cancel = QPushButton("Cancelar")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Salvar")
        save.setObjectName("PrimaryButton")
        save.clicked.connect(self._accept_if_valid)
        footer.addWidget(cancel)
        footer.addWidget(save)
        root.addLayout(footer)

        initial = counters or [default_counter_config(0)]
        for index, config in enumerate(initial):
            self._add_counter(config)

    def preset_name(self) -> str:
        return self.name_input.text().strip()

    def counter_configs(self) -> list[dict[str, Any]]:
        return [form.to_dict() for form in self.forms]

    def _add_counter(self, config: Optional[dict[str, Any]] = None) -> None:
        if len(self.forms) >= 4:
            QMessageBox.information(self, "Limite", "Por enquanto, use no maximo 4 contadores por preset.")
            return

        index = len(self.forms)
        form = CounterForm(
            index,
            config or default_counter_config(index),
            marker_files=self.marker_files,
            create_marker_file=self._create_marker_file_from_form,
        )
        self.forms.append(form)
        self.tabs.addTab(form, f"Contador {index + 1}")
        self.tabs.setCurrentWidget(form)
        form.title_input.textChanged.connect(self._rename_tabs)
        self._rename_tabs()

    def _remove_current_counter(self) -> None:
        if len(self.forms) <= 1:
            QMessageBox.information(self, "Preset", "Um preset precisa ter pelo menos 1 contador.")
            return

        index = self.tabs.currentIndex()
        widget = self.tabs.widget(index)
        self.tabs.removeTab(index)
        self.forms = [form for form in self.forms if form is not widget]
        self._rename_tabs()

    def _duplicate_current_counter(self) -> None:
        if len(self.forms) >= 4:
            QMessageBox.information(self, "Limite", "Por enquanto, use no maximo 4 contadores por preset.")
            return

        current = self.tabs.currentWidget()
        if not isinstance(current, CounterForm):
            return

        config = current.to_dict()
        config["titulo"] = self._copy_title(config.get("titulo", "Contador"))
        config["hotkey"] = ""
        self._add_counter(config)

    def _copy_title(self, title: object) -> str:
        base = str(title or "Contador").strip()
        names = {form.title_input.text().strip().casefold() for form in self.forms}
        candidate = f"{base} copia"
        number = 2
        while candidate.casefold() in names:
            candidate = f"{base} copia {number}"
            number += 1
        return candidate

    def _create_marker_file_from_form(self, name: str) -> str:
        if self.create_marker_file is None:
            return ""

        file_name = self.create_marker_file(name)
        if file_name and file_name not in self.marker_files:
            self.marker_files.append(file_name)
            for form in self.forms:
                form.add_marker_file_option(file_name)
        return file_name

    def _rename_tabs(self) -> None:
        for index, form in enumerate(self.forms):
            form.index = index
            title = form.title_input.text().strip() or f"Contador {index + 1}"
            if len(title) > 24:
                title = f"{title[:21]}..."
            self.tabs.setTabText(index, title)

    def _accept_if_valid(self) -> None:
        if not self.preset_name():
            QMessageBox.warning(self, "Nome do preset", "Digite um nome para o preset.")
            self.name_input.setFocus()
            return
        if not self._validate_counter_titles():
            return
        if not self._validate_counter_hotkeys():
            return
        if not self._validate_counter_marker_messages():
            return
        self.accept()

    def _validate_counter_titles(self) -> bool:
        seen: dict[str, CounterForm] = {}
        for index, form in enumerate(self.forms):
            title = form.title_input.text().strip()
            if not title:
                QMessageBox.warning(
                    self,
                    "Titulo do contador",
                    f"Digite um titulo para o contador {index + 1}.",
                )
                self.tabs.setCurrentWidget(form)
                form.title_input.setFocus()
                return False

            normalized = title.casefold()
            if normalized in seen:
                QMessageBox.warning(
                    self,
                    "Titulo repetido",
                    "Cada contador do preset precisa ter um titulo unico. "
                    f"O titulo repetido e: {title}",
                )
                self.tabs.setCurrentWidget(form)
                form.title_input.setFocus()
                return False
            seen[normalized] = form
        return True

    def _validate_counter_hotkeys(self) -> bool:
        seen: dict[str, tuple[str, CounterForm]] = {}
        for form in self.forms:
            title = form.title_input.text().strip()
            sequence = form.hotkey_text()
            normalized = _normalize_hotkey(sequence)
            if not normalized:
                continue

            if normalized in self.reserved_hotkeys:
                QMessageBox.warning(
                    self,
                    "Atalho em uso",
                    f"O atalho {sequence} ja esta em uso por: {self.reserved_hotkeys[normalized]}. "
                    "Escolha outro para evitar acionar duas acoes ao mesmo tempo.",
                )
                self.tabs.setCurrentWidget(form)
                form.hotkey_input.setFocus()
                return False

            if normalized in seen:
                previous_title, _ = seen[normalized]
                QMessageBox.warning(
                    self,
                    "Atalho repetido",
                    f"O atalho {sequence} esta repetido em {previous_title} e {title}.",
                )
                self.tabs.setCurrentWidget(form)
                form.hotkey_input.setFocus()
                return False

            seen[normalized] = (title, form)
        return True

    def _validate_counter_marker_messages(self) -> bool:
        for form in self.forms:
            marker_text = form.marker_text()
            if marker_text and not form.hotkey_text():
                QMessageBox.warning(
                    self,
                    "Marcacao automatica",
                    "Para salvar uma marcacao automatica, esse contador tambem precisa de uma hotkey.",
                )
                self.tabs.setCurrentWidget(form)
                form.hotkey_input.setFocus()
                return False
        return True


class CounterForm(QWidget):
    def __init__(
        self,
        index: int,
        config: dict[str, Any],
        marker_files: Optional[list[str]] = None,
        create_marker_file: Optional[Callable[[str], str]] = None,
    ) -> None:
        super().__init__()
        self.index = index
        self.icon_path: Optional[str] = None
        self.marker_files = marker_files or []
        self.create_marker_file = create_marker_file

        scroll_layout = QVBoxLayout(self)
        scroll_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_layout.addWidget(scroll)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(4, 4, 12, 4)
        layout.setSpacing(14)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)

        self.title_input = QLineEdit()
        self.prefix_input = QLineEdit()
        self.prefix_input.setPlaceholderText("Ex: Mortes: ")
        self.infinite_input = QCheckBox("Contador infinito")
        self.limit_input = QSpinBox()
        self.limit_input.setRange(1, 99999)
        self.hotkey_input = QKeySequenceEdit()
        self.marker_text_input = QLineEdit()
        self.marker_text_input.setPlaceholderText("Opcional: texto salvo no Marcador ao apertar a hotkey")
        self.marker_file_input = QComboBox()
        self.marker_file_input.addItem("Sem vinculo", "")
        for file_name in self.marker_files:
            self.add_marker_file_option(file_name)
        self.marker_file_button = QPushButton("Criar txt")
        self.marker_file_button.clicked.connect(self._create_marker_file)

        self.font_input = QComboBox()
        self.font_input.addItems(QFontDatabase().families())
        self.font_size_input = QSpinBox()
        self.font_size_input.setRange(8, 240)

        self.width_input = QSpinBox()
        self.width_input.setRange(160, 3840)
        self.height_input = QSpinBox()
        self.height_input.setRange(80, 2160)

        icon_row = QHBoxLayout()
        self.icon_label = QLabel("Nenhum icone")
        self.icon_button = QPushButton("Escolher imagem")
        self.icon_button.clicked.connect(self._choose_icon)
        self.icon_clear_button = QPushButton("Remover")
        self.icon_clear_button.clicked.connect(self._clear_icon)
        icon_row.addWidget(self.icon_label, 1)
        icon_row.addWidget(self.icon_button)
        icon_row.addWidget(self.icon_clear_button)

        self.icon_size_input = QSpinBox()
        self.icon_size_input.setRange(16, 256)

        form.addRow("Titulo", self.title_input)
        form.addRow("Prefixo", self.prefix_input)
        form.addRow("", self.infinite_input)
        form.addRow("Limite", self.limit_input)
        form.addRow("Hotkey", self.hotkey_input)
        form.addRow("Marcar no txt", self.marker_text_input)
        marker_file_row = QHBoxLayout()
        marker_file_row.addWidget(self.marker_file_input, 1)
        marker_file_row.addWidget(self.marker_file_button)
        form.addRow("Txt vinculado", marker_file_row)
        form.addRow("Fonte", self.font_input)
        form.addRow("Tamanho da fonte", self.font_size_input)
        form.addRow("Largura", self.width_input)
        form.addRow("Altura", self.height_input)
        form.addRow("Icone", icon_row)
        form.addRow("Tamanho do icone", self.icon_size_input)

        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumHeight(140)
        self.preview.setStyleSheet("background: #11161c; border: 1px solid #303946; border-radius: 8px;")

        layout.addLayout(form)
        layout.addWidget(QLabel("Preview"))
        layout.addWidget(self.preview)
        layout.addStretch(1)
        scroll.setWidget(content)

        self._load(config)
        self._wire_preview()
        self._update_limit_state()
        self._update_preview()

    def to_dict(self) -> dict[str, Any]:
        return {
            "titulo": self.title_input.text().strip(),
            "prefixo": self.prefix_input.text(),
            "infinito": self.infinite_input.isChecked(),
            "limite": None if self.infinite_input.isChecked() else self.limit_input.value(),
            "hotkey": self.hotkey_text(),
            "marcacao": self.marker_text(),
            "marker_file": self.marker_file(),
            "fonte": self.font_input.currentText(),
            "font_size": self.font_size_input.value(),
            "icone": self.icon_path,
            "icon_size": self.icon_size_input.value(),
            "largura": self.width_input.value(),
            "altura": self.height_input.value(),
        }

    def _load(self, config: dict[str, Any]) -> None:
        self.title_input.setText(str(config.get("titulo") or f"Contador {self.index + 1}"))
        self.prefix_input.setText(str(config.get("prefixo") or ""))
        self.infinite_input.setChecked(bool(config.get("infinito", True)))
        self.limit_input.setValue(int(config.get("limite") or 1))
        self.hotkey_input.setKeySequence(QKeySequence(str(config.get("hotkey") or "")))
        self.marker_text_input.setText(str(config.get("marcacao") or config.get("marker_text") or ""))
        marker_file = str(config.get("marker_file") or "")
        if marker_file:
            self.add_marker_file_option(marker_file)
            index = self.marker_file_input.findData(marker_file)
            if index >= 0:
                self.marker_file_input.setCurrentIndex(index)

        font = str(config.get("fonte") or "Arial")
        font_index = self.font_input.findText(font, Qt.MatchFlag.MatchExactly)
        if font_index >= 0:
            self.font_input.setCurrentIndex(font_index)

        self.font_size_input.setValue(int(config.get("font_size") or 48))
        self.width_input.setValue(int(config.get("largura") or 400))
        self.height_input.setValue(int(config.get("altura") or 160))
        self.icon_path = str(config.get("icone")) if config.get("icone") else None
        self.icon_label.setText(Path(self.icon_path).name if self.icon_path else "Nenhum icone")
        self.icon_size_input.setValue(int(config.get("icon_size") or 48))

    def _wire_preview(self) -> None:
        self.title_input.textChanged.connect(self._update_preview)
        self.prefix_input.textChanged.connect(self._update_preview)
        self.infinite_input.stateChanged.connect(self._update_limit_state)
        self.infinite_input.stateChanged.connect(self._update_preview)
        self.limit_input.valueChanged.connect(self._update_preview)
        self.font_input.currentTextChanged.connect(self._update_preview)
        self.font_size_input.valueChanged.connect(self._update_preview)
        self.icon_size_input.valueChanged.connect(self._update_preview)

    def _choose_icon(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Escolher imagem", "", "Imagens (*.png *.jpg *.jpeg *.webp)")
        if not path:
            return
        self.icon_path = path
        self.icon_label.setText(Path(path).name)
        self._update_preview()

    def _clear_icon(self) -> None:
        self.icon_path = None
        self.icon_label.setText("Nenhum icone")
        self._update_preview()

    def _update_limit_state(self) -> None:
        self.limit_input.setEnabled(not self.infinite_input.isChecked())

    def _update_preview(self) -> None:
        if self.infinite_input.isChecked():
            text = f"{self.prefix_input.text()}0"
        else:
            text = f"{self.prefix_input.text()}0/{self.limit_input.value()}"

        font = self.font_input.currentText()
        font_size = self.font_size_input.value()

        if self.icon_path:
            icon_size = self.icon_size_input.value()
            self.preview.setText(
                f'<img src="{self.icon_path}" height="{icon_size}"> '
                f'<span style="font-family:{font}; font-size:{font_size}pt; color:white;">{text}</span>'
            )
        else:
            self.preview.setText(
                f'<span style="font-family:{font}; font-size:{font_size}pt; color:white;">{text}</span>'
            )

    def hotkey_text(self) -> str:
        return self.hotkey_input.keySequence().toString(QKeySequence.SequenceFormat.NativeText).strip()

    def marker_text(self) -> str:
        return self.marker_text_input.text().strip()

    def marker_file(self) -> str:
        return str(self.marker_file_input.currentData() or "").strip()

    def add_marker_file_option(self, file_name: str) -> None:
        clean = str(file_name).strip()
        if not clean or self.marker_file_input.findData(clean) >= 0:
            return
        self.marker_file_input.addItem(clean, clean)

    def _create_marker_file(self) -> None:
        if self.create_marker_file is None:
            return

        name, accepted = QInputDialog.getText(self, "Criar txt do Marcador", "Nome do arquivo:")
        if not accepted or not name.strip():
            return

        file_name = self.create_marker_file(name.strip())
        if not file_name:
            return
        self.add_marker_file_option(file_name)
        index = self.marker_file_input.findData(file_name)
        if index >= 0:
            self.marker_file_input.setCurrentIndex(index)


def _normalize_hotkey(sequence: str) -> str:
    return str(sequence).strip().casefold().replace(" ", "")
