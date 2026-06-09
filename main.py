from __future__ import annotations

import json
import random
import sys
from datetime import datetime, time, timedelta
from pathlib import Path

from PySide6.QtCore import QStandardPaths, Qt, QTime, QTimer
from PySide6.QtGui import QAction, QCloseEvent, QColor, QIcon, QPainter, QPixmap
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStyle,
    QSystemTrayIcon,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)


APP_NAME = "站立提醒工具"
INSTANCE_KEY = "StandingReminderTool.Chen.SingleInstance"
DEFAULT_CONFIG = {
    "work_start": "09:00",
    "work_end": "18:00",
    "interval_minutes": 60,
}

MESSAGES = [
    "椅子说它想独处三分钟，你先起来走走吧。",
    "检测到久坐能量过高，请立刻释放一点活力。",
    "腿腿申请上线，站起来让它们活动一下。",
    "脖子和肩膀开了个小会，一致建议你起身伸展。",
    "恭喜触发健康彩蛋：站起来，深呼吸。",
    "办公桌不会跑，但你可以走两步。",
]


def resource_path(relative_path: str) -> Path:
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base_path / relative_path


def config_path() -> Path:
    location = QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation)
    path = Path(location) if location else Path.home() / "AppData" / "Roaming" / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path / "config.json"


def parse_time(value: str) -> time:
    hour, minute = value.split(":", 1)
    return time(int(hour), int(minute))


def format_qtime(value: QTime) -> str:
    return f"{value.hour():02d}:{value.minute():02d}"


def format_elapsed(delta: timedelta) -> str:
    total_seconds = max(0, int(delta.total_seconds()))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}小时{minutes}分钟"
    if minutes:
        return f"{minutes}分钟"
    return f"{seconds}秒"


def app_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#2eb67d"))
    painter.drawEllipse(6, 6, 52, 52)

    painter.setBrush(QColor("#ffffff"))
    painter.drawRoundedRect(29, 16, 6, 29, 3, 3)
    painter.drawRoundedRect(21, 25, 22, 6, 3, 3)
    painter.drawEllipse(24, 11, 16, 16)

    painter.setBrush(QColor("#ffcf5a"))
    painter.drawEllipse(42, 10, 12, 12)
    painter.end()
    return QIcon(pixmap)


class ReminderPopup(QWidget):
    def __init__(self, on_done, elapsed_provider) -> None:
        super().__init__(
            None,
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint,
        )
        self.on_done = on_done
        self.elapsed_provider = elapsed_provider
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

        self.image = MascotWidget()
        self.image.setFixedSize(280, 280)

        self.message = QLabel()
        self.message.setObjectName("message")
        self.message.setWordWrap(True)
        self.message.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.elapsed = QLabel()
        self.elapsed.setObjectName("elapsed")
        self.elapsed.setAlignment(Qt.AlignmentFlag.AlignCenter)

        done_button = QPushButton("已站立")
        done_button.clicked.connect(self.mark_done)

        layout.addWidget(title)
        layout.addWidget(self.image, stretch=1, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.message)
        layout.addWidget(self.elapsed)
        layout.addWidget(done_button)

    def show_reminder(self) -> None:
        self.message.setText(random.choice(MESSAGES))
        self.elapsed.setText(f"（距离上次站立已经过去 {self.elapsed_provider()}）")
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.x() + screen.width() - self.width() - 32,
            screen.y() + screen.height() - self.height() - 48,
        )
        self.show()
        self.raise_()
        self.activateWindow()

    def mark_done(self) -> None:
        self.hide()
        self.on_done()

    def closeEvent(self, event: QCloseEvent) -> None:
        event.ignore()
        self.hide()
        self.on_done()


class MascotWidget(QWidget):
    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
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
        painter.end()


class SettingsWindow(QMainWindow):
    def __init__(self, app: "StandingReminderApp") -> None:
        super().__init__()
        self.app = app
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(420, 300)
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
            QPushButton#secondary {
                background: #eef2f7;
                color: #283044;
            }
            QPushButton#secondary:hover {
                background: #e2e8f0;
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
            """
        )

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(18)

        heading = QLabel("站立提醒设置")
        heading.setObjectName("heading")

        self.start_edit = QTimeEdit()
        self.start_edit.setDisplayFormat("HH:mm")
        self.start_edit.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.start_edit.setFixedWidth(132)
        self.end_edit = QTimeEdit()
        self.end_edit.setDisplayFormat("HH:mm")
        self.end_edit.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.end_edit.setFixedWidth(132)
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 120)
        self.interval_spin.setSuffix(" 分钟")
        self.interval_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.interval_spin.setFixedWidth(132)

        form_rows = [
            ("上班开始", self.start_edit),
            ("上班结束", self.end_edit),
            ("提醒间隔", self.interval_spin),
        ]
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

        layout.insertWidget(0, heading)
        layout.addStretch()
        layout.addLayout(button_row)
        layout.addWidget(hint)
        self.setCentralWidget(root)
        self.load()

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
        config = self.app.config
        start = QTime.fromString(config["work_start"], "HH:mm")
        end = QTime.fromString(config["work_end"], "HH:mm")
        self.start_edit.setTime(start if start.isValid() else QTime(9, 0))
        self.end_edit.setTime(end if end.isValid() else QTime(18, 0))
        self.interval_spin.setValue(int(config.get("interval_minutes", DEFAULT_CONFIG["interval_minutes"])))

    def save(self) -> None:
        self.app.config = {
            "work_start": format_qtime(self.start_edit.time()),
            "work_end": format_qtime(self.end_edit.time()),
            "interval_minutes": self.interval_spin.value(),
        }
        self.app.save_config()
        self.app.reset_reminder_clock()
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
        self.hide()


class StandingReminderApp:
    def __init__(self) -> None:
        self.qt_app = QApplication(sys.argv)
        self.qt_app.setApplicationName(APP_NAME)
        self.icon = app_icon()
        self.qt_app.setWindowIcon(self.icon)
        self.qt_app.setQuitOnLastWindowClosed(False)

        self.server = self.create_single_instance_server()
        self.config = self.load_config()
        self.last_reminder_at = datetime.now()
        self.last_stood_at = datetime.now()

        self.popup = ReminderPopup(self.mark_stood, self.elapsed_since_last_stood)
        self.settings = SettingsWindow(self)
        self.tray = self.create_tray()

        self.timer = QTimer()
        self.timer.setInterval(30_000)
        self.timer.timeout.connect(self.tick)
        self.timer.start()

    def create_single_instance_server(self) -> QLocalServer:
        socket = QLocalSocket()
        socket.connectToServer(INSTANCE_KEY)
        if socket.waitForConnected(200):
            socket.write(b"show")
            socket.flush()
            socket.waitForBytesWritten(200)
            sys.exit(0)

        QLocalServer.removeServer(INSTANCE_KEY)
        server = QLocalServer()
        if not server.listen(INSTANCE_KEY):
            QMessageBox.warning(None, APP_NAME, "程序已经在运行。")
            sys.exit(0)
        server.newConnection.connect(self.handle_second_instance)
        return server

    def handle_second_instance(self) -> None:
        connection = self.server.nextPendingConnection()
        if connection:
            connection.close()
        self.show_settings()

    def create_tray(self) -> QSystemTrayIcon:
        icon = self.icon
        if icon.isNull():
            icon = self.qt_app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)

        tray = QSystemTrayIcon(icon)
        tray.setToolTip(APP_NAME)
        self.tray_menu = QMenu()

        self.show_settings_action = QAction("显示设置", self.tray_menu)
        self.show_settings_action.triggered.connect(self.show_settings)
        self.quit_action = QAction("关闭程序", self.tray_menu)
        self.quit_action.triggered.connect(self.quit)

        self.tray_menu.addAction(self.show_settings_action)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction(self.quit_action)
        tray.setContextMenu(self.tray_menu)
        tray.activated.connect(self.on_tray_activated)
        tray.show()
        return tray

    def on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.DoubleClick,
            QSystemTrayIcon.ActivationReason.Trigger,
        ):
            self.show_settings()

    def load_config(self) -> dict:
        path = config_path()
        if not path.exists():
            return DEFAULT_CONFIG.copy()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return {**DEFAULT_CONFIG, **data}
        except (OSError, json.JSONDecodeError):
            return DEFAULT_CONFIG.copy()

    def save_config(self) -> None:
        config_path().write_text(
            json.dumps(self.config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def is_work_time(self, now: datetime | None = None) -> bool:
        now = now or datetime.now()
        start = parse_time(self.config["work_start"])
        end = parse_time(self.config["work_end"])
        current = now.time().replace(second=0, microsecond=0)
        if start <= end:
            return start <= current <= end
        return current >= start or current <= end

    def tick(self) -> None:
        if self.popup.isVisible() or not self.is_work_time():
            return
        interval = timedelta(minutes=int(self.config.get("interval_minutes", DEFAULT_CONFIG["interval_minutes"])))
        if datetime.now() - self.last_reminder_at >= interval:
            self.show_reminder_now()

    def show_reminder_now(self) -> None:
        self.last_reminder_at = datetime.now()
        self.popup.show_reminder()

    def show_settings(self) -> None:
        self.settings.load()
        self.settings.show()
        self.settings.raise_()
        self.settings.activateWindow()

    def reset_reminder_clock(self) -> None:
        self.last_reminder_at = datetime.now()

    def mark_stood(self) -> None:
        self.last_stood_at = datetime.now()
        self.reset_reminder_clock()

    def elapsed_since_last_stood(self) -> str:
        return format_elapsed(datetime.now() - self.last_stood_at)

    def quit(self) -> None:
        self.tray.hide()
        self.server.close()
        QLocalServer.removeServer(INSTANCE_KEY)
        self.qt_app.quit()

    def run(self) -> int:
        self.tray.showMessage(APP_NAME, "我在托盘区待命，到点会提醒你活动一下。")
        QTimer.singleShot(300, self.show_settings)
        return self.qt_app.exec()


def main() -> int:
    app = StandingReminderApp()
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
