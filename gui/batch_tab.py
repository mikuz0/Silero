from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFileDialog, QProgressBar, QTableWidget,
    QTableWidgetItem, QHeaderView, QCheckBox, QGroupBox,
    QMessageBox, QAbstractItemView
)
from PyQt5.QtCore import Qt
from pathlib import Path
from typing import List

from config.settings import TTSSettings, AppSettings
from utils.file_utils import FileUtils
from workers.batch_worker import BatchWorker


class BatchTab(QWidget):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.settings = TTSSettings()
        self.app_settings = AppSettings()
        self.worker = None
        self.files: List[Path] = []
        self.working_dir: Path = None
        
        self.init_ui()
        self.restore_last_working_dir()
    
    def init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout(self)
        
        # Выбор рабочей папки
        dir_group = QGroupBox("Рабочая папка")
        dir_layout = QHBoxLayout()
        
        self.dir_label = QLabel("Папка не выбрана")
        self.dir_label.setStyleSheet("color: gray;")
        
        self.select_dir_btn = QPushButton("📁 Выбрать папку")
        self.select_dir_btn.clicked.connect(self.select_working_dir)
        
        self.refresh_btn = QPushButton("🔄 Обновить")
        self.refresh_btn.clicked.connect(self.scan_files)
        self.refresh_btn.setEnabled(False)
        
        dir_layout.addWidget(self.dir_label)
        dir_layout.addStretch()
        dir_layout.addWidget(self.select_dir_btn)
        dir_layout.addWidget(self.refresh_btn)
        
        dir_group.setLayout(dir_layout)
        layout.addWidget(dir_group)
        
        # Таблица файлов
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["", "Файл", "Статус", "Аудио"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.table)
        
        # Кнопки управления (первая строка)
        btn_layout1 = QHBoxLayout()
        
        self.select_all_btn = QPushButton("✅ Выбрать все")
        self.select_all_btn.clicked.connect(self.select_all)
        self.select_all_btn.setEnabled(False)
        
        self.clear_selected_btn = QPushButton("❌ Снять выделение")
        self.clear_selected_btn.clicked.connect(self.clear_selected)
        self.clear_selected_btn.setEnabled(False)
        
        self.select_unprocessed_btn = QPushButton("⏳ Отметить не обработанные")
        self.select_unprocessed_btn.clicked.connect(self.select_unprocessed)
        self.select_unprocessed_btn.setEnabled(False)
        
        btn_layout1.addWidget(self.select_all_btn)
        btn_layout1.addWidget(self.clear_selected_btn)
        btn_layout1.addWidget(self.select_unprocessed_btn)
        btn_layout1.addStretch()
        
        layout.addLayout(btn_layout1)
        
        # Кнопки управления (вторая строка)
        btn_layout2 = QHBoxLayout()
        
        self.start_btn = QPushButton("▶️ Обработать выбранные")
        self.start_btn.clicked.connect(self.start_processing)
        self.start_btn.setEnabled(False)
        
        self.stop_btn = QPushButton("⏸️ Остановить")
        self.stop_btn.clicked.connect(self.stop_processing)
        self.stop_btn.setEnabled(False)
        
        self.clear_audio_btn = QPushButton("🗑️ Очистить аудио")
        self.clear_audio_btn.clicked.connect(self.clear_audio)
        self.clear_audio_btn.setEnabled(False)
        
        btn_layout2.addWidget(self.start_btn)
        btn_layout2.addWidget(self.stop_btn)
        btn_layout2.addWidget(self.clear_audio_btn)
        btn_layout2.addStretch()
        
        layout.addLayout(btn_layout2)
        
        # Прогресс
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Готов")
        layout.addWidget(self.status_label)
    
    def restore_last_working_dir(self):
        """Восстановление последней рабочей папки"""
        last_dir = self.app_settings.get_working_dir()
        if last_dir and Path(last_dir).exists():
            self.working_dir = Path(last_dir)
            self.dir_label.setText(str(self.working_dir))
            self.dir_label.setStyleSheet("color: green;")
            self.refresh_btn.setEnabled(True)
            self.clear_audio_btn.setEnabled(True)
            self.select_unprocessed_btn.setEnabled(True)
            self.scan_files()
    
    def select_working_dir(self):
        """Выбор рабочей папки"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Выберите рабочую папку",
            str(self.working_dir) if self.working_dir else str(Path.home())
        )
        
        if dir_path:
            self.working_dir = Path(dir_path)
            self.dir_label.setText(str(self.working_dir))
            self.dir_label.setStyleSheet("color: green;")
            
            # Сохраняем путь
            self.app_settings.set_working_dir(str(self.working_dir))
            
            # Обновляем интерфейс
            self.refresh_btn.setEnabled(True)
            self.clear_audio_btn.setEnabled(True)
            self.select_unprocessed_btn.setEnabled(True)
            self.scan_files()
    
    def scan_files(self):
        """Сканирование файлов в рабочей папке"""
        if not self.working_dir:
            return
        
        source_dir = FileUtils.get_source_dir(self.working_dir)
        self.files = FileUtils.scan_text_files(source_dir, recursive=True)
        
        if not self.files:
            self.table.setRowCount(0)
            self.status_label.setText("Текстовые файлы не найдены")
            self.start_btn.setEnabled(False)
            self.select_all_btn.setEnabled(False)
            self.clear_selected_btn.setEnabled(False)
            self.select_unprocessed_btn.setEnabled(False)
            return
        
        self.table.setRowCount(len(self.files))
        
        for i, file_path in enumerate(self.files):
            # Чекбокс
            checkbox = QCheckBox()
            checkbox.setChecked(True)
            self.table.setCellWidget(i, 0, checkbox)
            
            # Имя файла (относительный путь)
            try:
                rel_path = file_path.relative_to(self.working_dir)
            except:
                rel_path = file_path.name
            self.table.setItem(i, 1, QTableWidgetItem(str(rel_path)))
            
            # Статус
            status = FileUtils.get_file_status(
                file_path, self.working_dir, self.settings.output_format
            )
            if status == 'completed':
                status_text = "✅ Обработан"
            else:
                status_text = "⏳ Ожидает"
            self.table.setItem(i, 2, QTableWidgetItem(status_text))
            
            # Путь к аудио
            audio_path = FileUtils.get_audio_path_for_batch(
                file_path, self.working_dir, self.settings.output_format
            )
            if audio_path.exists():
                self.table.setItem(i, 3, QTableWidgetItem(audio_path.name))
            else:
                self.table.setItem(i, 3, QTableWidgetItem("-"))
        
        self.table.resizeColumnsToContents()
        self.status_label.setText(f"Найдено файлов: {len(self.files)}")
        self.start_btn.setEnabled(True)
        self.select_all_btn.setEnabled(True)
        self.clear_selected_btn.setEnabled(True)
        self.select_unprocessed_btn.setEnabled(True)
    
    def select_all(self):
        """Выбрать все файлы"""
        for i in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(i, 0)
            if checkbox:
                checkbox.setChecked(True)
    
    def clear_selected(self):
        """Снять выделение со всех"""
        for i in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(i, 0)
            if checkbox:
                checkbox.setChecked(False)
    
    def select_unprocessed(self):
        """Отметить только необработанные файлы (ожидает или ошибка)"""
        for i in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(i, 0)
            if checkbox:
                # Получаем статус из колонки 2
                status_item = self.table.item(i, 2)
                if status_item:
                    status_text = status_item.text()
                    # Если статус не "✅ Обработан" — отмечаем
                    if status_text != "✅ Обработан":
                        checkbox.setChecked(True)
                    else:
                        checkbox.setChecked(False)
    
    def get_selected_files(self) -> List[Path]:
        """Получить список выбранных файлов"""
        selected = []
        for i in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(i, 0)
            if checkbox and checkbox.isChecked():
                selected.append(self.files[i])
        return selected
    
    def start_processing(self):
        """Запуск обработки"""
        selected_files = self.get_selected_files()
        
        if not selected_files:
            self.status_label.setText("Нет выбранных файлов")
            return
        
        # Подтверждение для длинной обработки
        if len(selected_files) > 10 and self.settings.accent_model == 'accurate':
            reply = QMessageBox.question(
                self,
                "Подтверждение",
                f"Будет обработано {len(selected_files)} файлов.\n"
                "Это может занять много времени.\n\n"
                "Продолжить?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        # Блокируем UI
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.select_dir_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.select_all_btn.setEnabled(False)
        self.clear_selected_btn.setEnabled(False)
        self.select_unprocessed_btn.setEnabled(False)
        self.clear_audio_btn.setEnabled(False)
        
        # Показываем прогресс
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(selected_files))
        self.progress_bar.setValue(0)
        
        # Запускаем worker
        self.worker = BatchWorker(selected_files, self.working_dir, self.settings)
        self.worker.progress.connect(self.update_progress)
        self.worker.file_completed.connect(self.file_completed)
        self.worker.finished.connect(self.processing_finished)
        self.worker.error.connect(self.processing_error)
        self.worker.start()
    
    def update_progress(self, current: int, total: int, file_name: str, message: str):
        """Обновление прогресса"""
        self.progress_bar.setValue(current)
        self.status_label.setText(f"[{current}/{total}] {file_name}: {message}")
    
    def file_completed(self, input_path: str, output_path: str, status: str):
        """Обработка одного файла завершена"""
        # Обновляем статус в таблице
        for i, file_path in enumerate(self.files):
            if str(file_path) == input_path:
                if status == 'success':
                    self.table.setItem(i, 2, QTableWidgetItem("✅ Обработан"))
                    audio_path = Path(output_path)
                    self.table.setItem(i, 3, QTableWidgetItem(audio_path.name))
                else:
                    self.table.setItem(i, 2, QTableWidgetItem("❌ Ошибка"))
                    self.table.setItem(i, 3, QTableWidgetItem("-"))
                break
    
    def processing_finished(self):
        """Обработка завершена"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.select_dir_btn.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        self.select_all_btn.setEnabled(True)
        self.clear_selected_btn.setEnabled(True)
        self.select_unprocessed_btn.setEnabled(True)
        self.clear_audio_btn.setEnabled(True)
        
        self.progress_bar.setVisible(False)
        self.status_label.setText("✅ Обработка завершена!")
        
        self.worker = None
    
    def processing_error(self, error_msg: str):
        """Ошибка обработки"""
        self.processing_finished()
        QMessageBox.critical(self, "Ошибка", error_msg)
    
    def stop_processing(self):
        """Остановка обработки"""
        if self.worker:
            self.worker.stop()
            self.status_label.setText("Остановка...")
    
    def clear_audio(self):
        """Очистка всех аудиофайлов"""
        if not self.working_dir:
            return
        
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Все сгенерированные аудиофайлы будут удалены.\n"
            "Это действие нельзя отменить.\n\n"
            "Продолжить?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            FileUtils.clear_audio_files(self.working_dir)
            self.scan_files()
            self.status_label.setText("Аудиофайлы очищены")
    
    def update_settings(self, settings: TTSSettings):
        """Обновление настроек из главного окна"""
        self.settings = settings
        self.scan_files()