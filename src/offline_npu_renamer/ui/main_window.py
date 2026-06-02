from __future__ import annotations

from datetime import date
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from offline_npu_renamer.core.analyzer import analyze_file
from offline_npu_renamer.core.article_analysis import analyze_article_text
from offline_npu_renamer.core.extractors import extract_document_content
from offline_npu_renamer.core.model_assets import validate_model_sessions
from offline_npu_renamer.core.models import RenameSuggestion, SuggestionStatus
from offline_npu_renamer.core.npu import detect_npu_status
from offline_npu_renamer.core.renamer import apply_renames, undo_latest
from offline_npu_renamer.core.scanner import scan_folder


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Offline NPU Renamer")
        self.selected_folder: Path | None = None
        self.suggestions: list[RenameSuggestion] = []
        self.npu_status = detect_npu_status()
        self.model_status = validate_model_sessions(self.npu_status)

        self.status_label = QLabel(self._startup_message())
        self.status_label.setWordWrap(True)

        tabs = QTabWidget()
        tabs.addTab(self._build_rename_tab(), "Rename")
        tabs.addTab(self._build_article_tab(), "Article Analysis")

        layout = QVBoxLayout()
        layout.addWidget(self.status_label)
        layout.addWidget(tabs)

        root = QWidget()
        root.setLayout(layout)
        self.setCentralWidget(root)

    def _build_rename_tab(self) -> QWidget:
        self.folder_label = QLabel("No folder selected")
        self.choose_button = QPushButton("Choose Folder")
        self.scan_button = QPushButton("Scan")
        self.apply_button = QPushButton("Apply Renames")
        self.undo_button = QPushButton("Undo Latest")
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Include", "Original", "Suggested", "Type", "Date Source", "Confidence", "Reason"]
        )

        self.choose_button.clicked.connect(self.choose_folder)
        self.scan_button.clicked.connect(self.scan)
        self.apply_button.clicked.connect(self.apply)
        self.undo_button.clicked.connect(self.undo)

        top = QHBoxLayout()
        top.addWidget(self.choose_button)
        top.addWidget(self.scan_button)
        top.addWidget(self.apply_button)
        top.addWidget(self.undo_button)

        layout = QVBoxLayout()
        layout.addWidget(self.status_label)
        layout.addWidget(self.folder_label)
        layout.addLayout(top)
        layout.addWidget(self.table)

        tab = QWidget()
        tab.setLayout(layout)
        return tab

    def _build_article_tab(self) -> QWidget:
        self.article_path: Path | None = None
        self.article_label = QLabel("No article selected")
        self.choose_article_button = QPushButton("Choose Article")
        self.analyze_article_button = QPushButton("Analyze Article")
        self.article_output = QPlainTextEdit()
        self.article_output.setReadOnly(True)

        self.choose_article_button.clicked.connect(self.choose_article)
        self.analyze_article_button.clicked.connect(self.analyze_article)

        top = QHBoxLayout()
        top.addWidget(self.choose_article_button)
        top.addWidget(self.analyze_article_button)

        layout = QVBoxLayout()
        layout.addWidget(self.article_label)
        layout.addLayout(top)
        layout.addWidget(self.article_output)

        tab = QWidget()
        tab.setLayout(layout)
        return tab

    def choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose folder")
        if folder:
            self.selected_folder = Path(folder)
            self.folder_label.setText(str(self.selected_folder))

    def scan(self) -> None:
        if self.selected_folder is None:
            QMessageBox.warning(self, "No folder", "Choose a folder first.")
            return
        if not self.model_status.available:
            QMessageBox.warning(self, "Models unavailable", self.model_status.message)
            return
        if not self.npu_status.available:
            QMessageBox.warning(self, "NPU unavailable", self.npu_status.message)
            return
        scanned = scan_folder(self.selected_folder)
        self.suggestions = [
            analyze_file(item.path, item.kind, self.npu_status, self.model_status, today=date.today())
            for item in scanned
        ]
        self.populate_table()

    def populate_table(self) -> None:
        self.table.setRowCount(len(self.suggestions))
        for row, suggestion in enumerate(self.suggestions):
            include = QTableWidgetItem("yes" if suggestion.status is SuggestionStatus.READY else "no")
            include.setFlags(include.flags() | Qt.ItemFlag.ItemIsEditable)
            values = [
                include,
                QTableWidgetItem(suggestion.source_path.name),
                QTableWidgetItem(suggestion.target_path.name),
                QTableWidgetItem(suggestion.file_kind.value),
                QTableWidgetItem(suggestion.date_source.value),
                QTableWidgetItem(f"{suggestion.confidence:.2f}"),
                QTableWidgetItem(suggestion.reason),
            ]
            for column, item in enumerate(values):
                self.table.setItem(row, column, item)
        self.table.resizeColumnsToContents()

    def apply(self) -> None:
        if self.selected_folder is None:
            QMessageBox.warning(self, "No folder", "Choose a folder first.")
            return
        selected = [
            suggestion
            for row, suggestion in enumerate(self.suggestions)
            if self.table.item(row, 0) and self.table.item(row, 0).text().lower() == "yes"
        ]
        results = apply_renames(selected, self.selected_folder / "rename-log.jsonl")
        renamed = sum(1 for _, _, status in results if status == "renamed")
        QMessageBox.information(self, "Rename complete", f"Renamed {renamed} of {len(results)} file(s).")

    def undo(self) -> None:
        if self.selected_folder is None:
            QMessageBox.warning(self, "No folder", "Choose a folder first.")
            return
        results = undo_latest(self.selected_folder / "rename-log.jsonl")
        undone = sum(1 for _, _, status in results if status == "undone")
        QMessageBox.information(self, "Undo complete", f"Undone {undone} file(s).")

    def choose_article(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose article",
            "",
            "Documents (*.txt *.md *.pdf *.docx)",
        )
        if file_path:
            self.article_path = Path(file_path)
            self.article_label.setText(str(self.article_path))

    def analyze_article(self) -> None:
        if self.article_path is None:
            QMessageBox.warning(self, "No article", "Choose an article first.")
            return
        try:
            content = extract_document_content(self.article_path)
        except Exception as error:
            QMessageBox.warning(self, "Article read failed", str(error))
            return
        result = analyze_article_text(content.text)
        if result.status is SuggestionStatus.ERROR:
            QMessageBox.warning(self, "Analysis failed", result.reason)
            return
        self.article_output.setPlainText(
            "Suggested title:\n"
            f"{result.suggested_title}\n\n"
            "Summary:\n"
            f"{result.summary}\n\n"
            "Key sentences:\n"
            + "\n".join(f"- {sentence}" for sentence in result.key_sentences)
            + "\n\nReason:\n"
            + result.reason
        )

    def _startup_message(self) -> str:
        if not self.model_status.available:
            return self.model_status.message
        if not self.npu_status.available:
            return self.npu_status.message
        return f"{self.model_status.message} {self.npu_status.message}"
