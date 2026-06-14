from __future__ import annotations

import random
import re
from collections.abc import Callable

from PySide6.QtCore import Qt, QTime, QTimer
from PySide6.QtGui import QCloseEvent, QColor, QPainter, QPixmap
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSpinBox,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from config import (
    APP_NAME,
    DEFAULT_CONFIG,
    MAX_INTERVAL_MINUTES,
    MIN_INTERVAL_MINUTES,
    ReminderConfig,
    format_qtime,
    resource_path,
)


MESSAGES = [
    "椅子说它想独处三分钟，你先起来走走吧。",
    "检测到久坐能量过高，请立刻释放一点活力。",
    "腿腿申请上线，站起来让它们活动一下。",
    "脖子和肩膀开了个小会，一致建议你起身伸展。",
    "恭喜触发健康彩蛋：站起来，深呼吸。",
    "办公桌不会跑，但你可以走两步。",
]


def elapsed_html(value: str) -> str:
    return re.sub(
        r"(\d+)(小时|分钟|秒)",
        r'<span style="color:#344054;">\1</span><span style="color:#7b8794;">\2</span>',
        value,
    )


class ReminderPopup(QWidget):
    def __init__(self, on_done: Callable[[], None], elapsed_provider: Callable[[], str]) -> None:
        super().__init__(
            None,
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint,
        )
        self.on_done = on_done
        self.elapsed_provider = elapsed_provider
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(1_000)
        self.refresh_timer.timeout.connect(self.refresh_elapsed)
        self.setWindowTitle(APP_NAME)
        self.setFixedSize(440, 520)
        self.setStyleSheet(
            """
            QWidget {
                background: #fffaf3;
                color: #2f3542;
                font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
            }
            QLabel#title {
                color: #283044;
                font-size: 24px;
                font-weight: 700;
            }
            QLabel#message {
                color: #4b5565;
                font-size: 18px;
                line-height: 1.35;
            }
            QLabel#elapsed {
                color: #667085;
                font-size: 13px;
            }
            QLabel#elapsedValue {
                background: #eef4fb;
                border: 1px solid #d7e2ef;
                border-radius: 5px;
                color: #344054;
                font-size: 13px;
                font-weight: 600;
                padding: 2px 7px;
            }
            QPushButton {
                background: #2eb67d;
                border: none;
                border-radius: 8px;
                color: white;
                font-size: 17px;
                font-weight: 700;
                padding: 12px 22px;
            }
            QPushButton:hover {
                background: #279e6d;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(18)

        title = QLabel("起来活动一下")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.image = MascotImage()
        self.image.setFixedSize(280, 280)

        self.message = QLabel()
        self.message.setObjectName("message")
        self.message.setWordWrap(True)
        self.message.setAlignment(Qt.AlignmentFlag.AlignCenter)

        elapsed_row = QHBoxLayout()
        elapsed_row.setContentsMargins(0, 0, 0, 0)
        elapsed_row.setSpacing(6)
        elapsed_row.addStretch()
        elapsed_text = QLabel("距离上次站立已经过去")
        elapsed_text.setObjectName("elapsed")
        self.elapsed_value = QLabel()
        self.elapsed_value.setObjectName("elapsedValue")
        self.elapsed_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.elapsed_value.setTextFormat(Qt.TextFormat.RichText)
        elapsed_row.addWidget(elapsed_text)
        elapsed_row.addWidget(self.elapsed_value)
        elapsed_row.addStretch()

        done_button = QPushButton("已站立")
        done_button.clicked.connect(self.mark_done)

        layout.addWidget(title)
        layout.addWidget(self.image, stretch=1, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.message)
        layout.addLayout(elapsed_row)
        layout.addWidget(done_button)

    def show_reminder(self) -> None:
        self.message.setText(random.choice(MESSAGES))
        self.refresh_elapsed()
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.x() + screen.width() - self.width() - 32,
            screen.y() + screen.height() - self.height() - 48,
        )
        self.show()
        self.raise_()
        self.activateWindow()
        self.refresh_timer.start()

    def refresh_elapsed(self) -> None:
        self.elapsed_value.setText(elapsed_html(self.elapsed_provider()))

    def mark_done(self) -> None:
        self.refresh_timer.stop()
        self.hide()
        self.on_done()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self.refresh_timer.stop()

    def closeEvent(self, event: QCloseEvent) -> None:
        event.ignore()
        self.show()
        self.raise_()
        self.activateWindow()


class MascotImage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.pixmap = QPixmap(str(resource_path("assets/standing_mascot.png")))

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self.pixmap.isNull():
            scaled = self.pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
        else:
            self.paint_fallback(painter)
        painter.end()

    def paint_fallback(self, painter: QPainter) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#f9efd7"))
        painter.drawEllipse(26, 22, 228, 220)

        painter.setBrush(QColor("#7bdcb5"))
        painter.drawRoundedRect(92, 92, 96, 116, 40, 40)
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(106, 112, 18, 18)
        painter.drawEllipse(156, 112, 18, 18)
        painter.setBrush(QColor("#283044"))
        painter.drawEllipse(113, 119, 7, 7)
        painter.drawEllipse(163, 119, 7, 7)

        painter.setBrush(QColor("#ff8f7a"))
        painter.drawEllipse(82, 142, 18, 12)
        painter.drawEllipse(180, 142, 18, 12)

        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(120, 152, 40, 18, 9, 9)

        painter.setBrush(QColor("#7bdcb5"))
        painter.drawRoundedRect(62, 138, 40, 14, 7, 7)
        painter.drawRoundedRect(178, 138, 40, 14, 7, 7)
        painter.drawRoundedRect(106, 204, 18, 38, 9, 9)
        painter.drawRoundedRect(156, 204, 18, 38, 9, 9)

        painter.setBrush(QColor("#ffcf5a"))
        painter.drawEllipse(190, 54, 34, 34)


class SettingsWindow(QMainWindow):
    def __init__(
        self,
        config_provider: Callable[[], ReminderConfig],
        on_save: Callable[[ReminderConfig], None],
        on_auto_start_changed: Callable[[bool], None],
        status_provider: Callable[[], str],
        elapsed_provider: Callable[[], str],
    ) -> None:
        super().__init__()
        self.config_provider = config_provider
        self.on_save = on_save
        self.on_auto_start_changed = on_auto_start_changed
        self.status_provider = status_provider
        self.elapsed_provider = elapsed_provider
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(420, 360)
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background: #f6f8fb;
                color: #283044;
                font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
                font-size: 15px;
            }
            QLabel#heading {
                font-size: 22px;
                font-weight: 700;
            }
            QLabel#status {
                background: #eaf7f0;
                border: 1px solid #bfe7d2;
                border-radius: 8px;
                color: #176b4a;
                padding: 9px 12px;
            }
            QLabel#elapsedInfo {
                color: #4b5565;
                font-size: 13px;
            }
            QLabel#elapsedValue {
                background: #eef4fb;
                border: 1px solid #d7e2ef;
                border-radius: 5px;
                color: #344054;
                font-size: 13px;
                font-weight: 600;
                padding: 2px 7px;
            }
            QTimeEdit, QSpinBox {
                background: white;
                border: 1px solid #d7deea;
                border-radius: 6px;
                padding: 8px 10px;
                min-height: 32px;
                selection-background-color: #d8f3e7;
                selection-color: #12382a;
            }
            QTimeEdit:hover, QSpinBox:hover {
                border-color: #9bb7e5;
            }
            QTimeEdit:focus, QSpinBox:focus {
                border-color: #2eb67d;
            }
            QPushButton {
                background: #3366cc;
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: 700;
                padding: 10px 18px;
            }
            QPushButton:hover {
                background: #2855ad;
            }
            QWidget#formRow, QWidget#stepper {
                background: transparent;
            }
            QPushButton#stepUp, QPushButton#stepDown {
                background: #eef2f7;
                border: 1px solid #d7deea;
                border-radius: 5px;
                color: #344054;
                font-size: 11px;
                font-weight: 800;
                padding: 0;
            }
            QPushButton#stepUp:hover, QPushButton#stepDown:hover {
                background: #e4f4ed;
                border-color: #8fd6b8;
                color: #176b4a;
            }
            QCheckBox {
                color: #344054;
                font-size: 12px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 12px;
                height: 12px;
                border: 1px solid #9aa8b7;
                border-radius: 2px;
                background: #ffffff;
            }
            QCheckBox::indicator:hover {
                border-color: #2eb67d;
            }
            QCheckBox::indicator:checked {
                background: #2eb67d;
                border-color: #2eb67d;
                image: none;
            }
            """
        )

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(18)

        heading = QLabel("站立提醒设置")
        heading.setObjectName("heading")

        self.status_label = QLabel()
        self.status_label.setObjectName("status")
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.elapsed_value_label = QLabel()
        self.elapsed_value_label.setObjectName("elapsedValue")
        self.elapsed_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.elapsed_value_label.setTextFormat(Qt.TextFormat.RichText)

        self.start_edit = QTimeEdit()
        self.start_edit.setDisplayFormat("HH:mm")
        self.start_edit.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.start_edit.setFixedWidth(132)

        self.end_edit = QTimeEdit()
        self.end_edit.setDisplayFormat("HH:mm")
        self.end_edit.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.end_edit.setFixedWidth(132)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(MIN_INTERVAL_MINUTES, MAX_INTERVAL_MINUTES)
        self.interval_spin.setSuffix(" 分钟")
        self.interval_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.interval_spin.setFixedWidth(132)

        self.auto_start_check = QCheckBox("开机自启动")
        self.auto_start_check.setFixedHeight(24)
        self.auto_start_check.toggled.connect(self.on_auto_start_toggled)

        form_rows = [
            ("上班开始", self.start_edit),
            ("上班结束", self.end_edit),
            ("提醒间隔", self.interval_spin),
        ]
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.addWidget(heading)
        header_row.addStretch()
        header_row.addWidget(self.auto_start_check, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(header_row)
        layout.addWidget(self.status_label)
        elapsed_row = QHBoxLayout()
        elapsed_row.setContentsMargins(0, 0, 0, 0)
        elapsed_row.setSpacing(6)
        elapsed_row.addStretch()
        elapsed_text = QLabel("距离上次站立已经过去")
        elapsed_text.setObjectName("elapsedInfo")
        elapsed_row.addWidget(elapsed_text)
        elapsed_row.addWidget(self.elapsed_value_label)
        elapsed_row.addStretch()
        layout.addLayout(elapsed_row)
        for label_text, editor in form_rows:
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            label = QLabel(label_text)
            label.setFixedWidth(90)
            label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            group = QWidget()
            group.setObjectName("formRow")
            group.setFixedWidth(276)
            group_layout = QHBoxLayout(group)
            group_layout.setContentsMargins(0, 0, 0, 0)
            group_layout.setSpacing(12)
            group_layout.addWidget(label)
            group_layout.addWidget(self.make_stepper(editor))
            group_layout.addStretch()
            row.addStretch()
            row.addWidget(group)
            row.addStretch()
            layout.addLayout(row)

        button_row = QHBoxLayout()
        button_row.addStretch()
        save_button = QPushButton("保存")
        save_button.setMinimumWidth(220)
        save_button.clicked.connect(self.save)
        button_row.addWidget(save_button)
        button_row.addStretch()

        hint = QLabel("点击保存后请关闭本窗口")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color: #667085; font-size: 12px;")

        layout.addStretch()
        layout.addLayout(button_row)
        layout.addWidget(hint)
        self.setCentralWidget(root)
        self.load()

        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(1_000)
        self.refresh_timer.timeout.connect(self.refresh_status)

    def make_stepper(self, editor: QAbstractSpinBox) -> QWidget:
        container = QWidget()
        container.setObjectName("stepper")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        buttons = QVBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(4)

        up_button = QPushButton("▲")
        up_button.setObjectName("stepUp")
        up_button.setFixedSize(30, 22)
        up_button.clicked.connect(editor.stepUp)

        down_button = QPushButton("▼")
        down_button.setObjectName("stepDown")
        down_button.setFixedSize(30, 22)
        down_button.clicked.connect(editor.stepDown)

        buttons.addWidget(up_button)
        buttons.addWidget(down_button)
        layout.addWidget(editor)
        layout.addLayout(buttons)
        return container

    def load(self) -> None:
        config = self.config_provider()
        start = QTime.fromString(config.work_start, "HH:mm")
        end = QTime.fromString(config.work_end, "HH:mm")
        self.start_edit.setTime(start if start.isValid() else QTime(9, 0))
        self.end_edit.setTime(end if end.isValid() else QTime(18, 0))
        self.interval_spin.setValue(config.interval_minutes or DEFAULT_CONFIG.interval_minutes)
        self.set_auto_start_checked(config.auto_start)
        self.refresh_status()

    def set_auto_start_checked(self, enabled: bool) -> None:
        self.auto_start_check.blockSignals(True)
        self.auto_start_check.setChecked(enabled)
        self.auto_start_check.blockSignals(False)

    def on_auto_start_toggled(self, enabled: bool) -> None:
        self.on_auto_start_changed(enabled)

    def refresh_status(self) -> None:
        self.status_label.setText(self.status_provider())
        self.elapsed_value_label.setText(elapsed_html(self.elapsed_provider()))

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.refresh_status()
        self.refresh_timer.start()

    def save(self) -> None:
        config = ReminderConfig(
            work_start=format_qtime(self.start_edit.time()),
            work_end=format_qtime(self.end_edit.time()),
            interval_minutes=self.interval_spin.value(),
            auto_start=self.config_provider().auto_start,
        )
        self.on_save(config)
        self.refresh_status()
        self.show_saved_dialog()

    def show_saved_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(APP_NAME)
        dialog.setModal(True)
        dialog.setFixedSize(260, 140)
        dialog.setStyleSheet(
            """
            QDialog {
                background: #f8fafc;
                color: #283044;
                font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
                font-size: 14px;
            }
            QPushButton {
                background: #3366cc;
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: 700;
                min-width: 92px;
                padding: 8px 18px;
            }
            QPushButton:hover {
                background: #2855ad;
            }
            """
        )
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(16)

        message = QLabel("设置已保存。")
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(message)

        button_row = QHBoxLayout()
        button_row.addStretch()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(dialog.accept)
        button_row.addWidget(ok_button)
        button_row.addStretch()
        layout.addLayout(button_row)
        dialog.exec()

    def closeEvent(self, event: QCloseEvent) -> None:
        event.ignore()
        self.refresh_timer.stop()
        self.hide()
