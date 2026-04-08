from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel, QSlider, QFileDialog
)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from pathlib import Path


class AudioPlayer(QWidget):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.player = QMediaPlayer()
        self.current_file = None
        self.init_ui()
        self.setup_connections()
    
    def init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.play_btn = QPushButton()
        self.play_btn.setEnabled(False)
        self.play_btn.setFixedSize(30, 30)
        self.update_play_button(False)
        layout.addWidget(self.play_btn)
        
        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setEnabled(False)
        self.position_slider.setRange(0, 100)
        layout.addWidget(self.position_slider)
        
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setFixedWidth(100)
        layout.addWidget(self.time_label)
        
        self.volume_btn = QPushButton("🔊")
        self.volume_btn.setFixedWidth(30)
        self.volume_btn.clicked.connect(self.toggle_mute)
        layout.addWidget(self.volume_btn)
        
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setFixedWidth(80)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.valueChanged.connect(self.set_volume)
        layout.addWidget(self.volume_slider)
        
        self.open_btn = QPushButton("📁 Открыть")
        self.open_btn.setFixedWidth(80)
        layout.addWidget(self.open_btn)
        
        self.setLayout(layout)
        
        # Устанавливаем начальную громкость
        self.player.setVolume(70)
    
    def setup_connections(self):
        self.play_btn.clicked.connect(self.toggle_play)
        self.position_slider.sliderMoved.connect(self.set_position)
        self.open_btn.clicked.connect(self.open_file)
        
        self.player.positionChanged.connect(self.update_position)
        self.player.durationChanged.connect(self.update_duration)
        self.player.stateChanged.connect(self.on_state_changed)
    
    def update_play_button(self, is_playing: bool):
        if is_playing:
            self.play_btn.setText("⏸")
            self.play_btn.setToolTip("Пауза")
        else:
            self.play_btn.setText("▶")
            self.play_btn.setToolTip("Воспроизвести")
    
    def on_state_changed(self, state):
        self.update_play_button(state == QMediaPlayer.PlayingState)
    
    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите аудиофайл", str(Path.home()),
            "Аудио файлы (*.mp3 *.wav *.ogg);;Все файлы (*.*)"
        )
        if file_path:
            self.load_file(file_path)
    
    def load_file(self, file_path: str):
        self.current_file = file_path
        url = QUrl.fromLocalFile(file_path)
        content = QMediaContent(url)
        self.player.setMedia(content)
        self.play_btn.setEnabled(True)
        self.position_slider.setEnabled(True)
        self.setToolTip(Path(file_path).name)
    
    def toggle_play(self):
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()
    
    def set_position(self, position: int):
        duration = self.player.duration()
        if duration > 0:
            self.player.setPosition(int(position * duration / 100))
    
    def update_position(self, position: int):
        duration = self.player.duration()
        if duration > 0:
            self.position_slider.setValue(int(position * 100 / duration))
        self.time_label.setText(f"{self.format_time(position)} / {self.format_time(duration)}")
    
    def update_duration(self, duration: int):
        self.time_label.setText(f"00:00 / {self.format_time(duration)}")
    
    def format_time(self, ms: int) -> str:
        if ms <= 0:
            return "00:00"
        seconds = ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    def set_volume(self, value: int):
        self.player.setVolume(value)
        self.update_volume_icon(value)
    
    def toggle_mute(self):
        if self.player.volume() > 0:
            self._last_volume = self.player.volume()
            self.player.setVolume(0)
            self.volume_slider.setValue(0)
        else:
            self.player.setVolume(self._last_volume if hasattr(self, '_last_volume') else 70)
            self.volume_slider.setValue(self._last_volume if hasattr(self, '_last_volume') else 70)
    
    def update_volume_icon(self, volume: int):
        if volume == 0:
            self.volume_btn.setText("🔇")
        elif volume < 30:
            self.volume_btn.setText("🔈")
        elif volume < 70:
            self.volume_btn.setText("🔉")
        else:
            self.volume_btn.setText("🔊")
    
    def stop(self):
        self.player.stop()
    
    def unload(self):
        self.player.stop()
        self.player.setMedia(QMediaContent())
        self.play_btn.setEnabled(False)
        self.position_slider.setEnabled(False)
        self.current_file = None
        self.time_label.setText("00:00 / 00:00")