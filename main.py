from __future__ import annotations

import sys
from dataclasses import replace
from datetime import datetime, timedelta

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QStyle, QSystemTrayIcon

from config import APP_NAME, INSTANCE_KEY, ReminderConfig, load_config, save_config
from reminder import ReminderState
from startup import is_auto_start_enabled, set_auto_start_enabled
from widgets import ReminderPopup, SettingsWindow


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


class StandingReminderApp:
    def __init__(self) -> None:
        self.qt_app = QApplication(sys.argv)
        self.qt_app.setApplicationName(APP_NAME)
        self.icon = app_icon()
        self.qt_app.setWindowIcon(self.icon)
        self.qt_app.setQuitOnLastWindowClosed(False)

        self.server = self.create_single_instance_server()
        self.config = replace(load_config(), auto_start=is_auto_start_enabled())
        self.state = ReminderState.create()

        self.popup = ReminderPopup(self.mark_stood, self.elapsed_since_last_stood)
        self.settings = SettingsWindow(
            lambda: self.config,
            self.update_config,
            self.update_auto_start,
            self.status_text,
            self.elapsed_since_last_stood,
        )
        self.tray = self.create_tray()

        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.tick)
        self.schedule_next_check()

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

        self.pause_action = QAction("暂停 1 小时", self.tray_menu)
        self.pause_action.triggered.connect(self.pause_for_one_hour)

        self.mute_today_action = QAction("今日不再提醒", self.tray_menu)
        self.mute_today_action.triggered.connect(self.mute_today)

        self.resume_action = QAction("恢复提醒", self.tray_menu)
        self.resume_action.triggered.connect(self.resume_reminders)

        self.quit_action = QAction("关闭程序", self.tray_menu)
        self.quit_action.triggered.connect(self.quit)

        self.tray_menu.addAction(self.show_settings_action)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction(self.pause_action)
        self.tray_menu.addAction(self.mute_today_action)
        self.tray_menu.addAction(self.resume_action)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction(self.quit_action)
        tray.setContextMenu(self.tray_menu)
        tray.activated.connect(self.on_tray_activated)
        tray.show()
        self.update_tray_actions()
        return tray

    def on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.DoubleClick,
            QSystemTrayIcon.ActivationReason.Trigger,
        ):
            self.show_settings()

    def update_config(self, config: ReminderConfig) -> None:
        self.config = config
        save_config(self.config)
        self.state.reset_clock()
        self.schedule_next_check()

    def update_auto_start(self, enabled: bool) -> None:
        set_auto_start_enabled(enabled)
        self.config = replace(self.config, auto_start=is_auto_start_enabled())
        save_config(self.config)

    def tick(self) -> None:
        if not self.popup.isVisible() and self.state.should_remind(self.config):
            self.show_reminder_now()
        self.schedule_next_check()

    def schedule_next_check(self) -> None:
        delay = 30_000 if self.popup.isVisible() else self.state.next_check_delay_ms(self.config)
        self.timer.start(delay)
        self.update_tray_actions()

    def show_reminder_now(self) -> None:
        self.state.resume()
        self.state.reset_clock()
        self.popup.show_reminder()
        self.update_tray_actions()

    def show_settings(self) -> None:
        self.settings.load()
        self.settings.show()
        self.settings.raise_()
        self.settings.activateWindow()

    def pause_for_one_hour(self) -> None:
        self.popup.hide()
        self.state.pause_for(timedelta(hours=1))
        self.tray.showMessage(APP_NAME, "已暂停 1 小时。")
        self.schedule_next_check()
        self.refresh_settings_status()

    def mute_today(self) -> None:
        self.popup.hide()
        self.state.mute_today()
        self.tray.showMessage(APP_NAME, "今天不再提醒，明天自动恢复。")
        self.schedule_next_check()
        self.refresh_settings_status()

    def resume_reminders(self) -> None:
        self.state.resume()
        self.state.reset_clock()
        self.tray.showMessage(APP_NAME, "提醒已恢复。")
        self.schedule_next_check()
        self.refresh_settings_status()

    def mark_stood(self) -> None:
        self.state.mark_stood()
        self.schedule_next_check()
        self.refresh_settings_status()

    def elapsed_since_last_stood(self) -> str:
        return self.state.elapsed_since_stood()

    def status_text(self) -> str:
        now = datetime.now()
        if self.state.is_paused(now) and self.state.paused_until:
            return f"提醒已暂停，将在 {self.state.paused_until:%H:%M} 自动恢复。"
        if self.state.is_muted_today(now):
            return "今日不再提醒，明天会自动恢复。"
        return "提醒正常运行中。"

    def refresh_settings_status(self) -> None:
        if self.settings.isVisible():
            self.settings.refresh_status()

    def update_tray_actions(self) -> None:
        now = datetime.now()
        paused = self.state.is_paused(now)
        muted = self.state.is_muted_today(now)
        self.pause_action.setEnabled(not paused and not muted)
        self.mute_today_action.setEnabled(not muted)
        self.resume_action.setEnabled(paused or muted)

    def quit(self) -> None:
        self.tray.hide()
        self.server.close()
        QLocalServer.removeServer(INSTANCE_KEY)
        self.qt_app.quit()

    def run(self) -> int:
        QTimer.singleShot(300, self.show_settings)
        return self.qt_app.exec()


def main() -> int:
    app = StandingReminderApp()
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
