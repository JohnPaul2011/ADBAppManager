import os
import subprocess
import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout,
                        QHBoxLayout, QPushButton, QLabel, QListWidget, QComboBox,
                        QFileDialog, QWidget, QLineEdit, QProgressDialog)
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QByteArray, Qt, QSize, QTimer, QThread, Signal
import platform

ADB_PATH = os.getenv("ADB_PATH", "adb.exe")  # Allow override via environment variable

phone_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-smartphone-icon lucide-smartphone"><rect width="14" height="20" x="5" y="2" rx="2" ry="2"/><path d="M12 18h.01"/></svg>"""
refresh_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-refresh-ccw-icon lucide-refresh-ccw"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 16h5v5"/></svg>"""

def svg_icon(svg: str, size=64):
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)

def parse_adb_devices(adb_output: str) -> list:
    devices = []
    lines = adb_output.strip().split('\n')
    device_section_started = False
    for line in lines:
        line = line.strip()
        if not line or line.startswith('*'):
            continue
        if "List of devices attached" in line:
            device_section_started = True
            continue
        if device_section_started:
            parts = line.split()
            if len(parts) >= 2 and parts[0] != "List":
                devices.append(parts[0])
    return devices


# ── Worker threads so the UI doesn't freeze during installs/exports ──────────

class InstallWorker(QThread):
    finished = Signal(str, bool)   # (message, success)
    progress = Signal(str)         # label update while running

    def __init__(self, adb_path, device_id, apk_paths):
        super().__init__()
        self.adb_path = adb_path
        self.device_id = device_id
        self.apk_paths = apk_paths  # list of file paths

    def run(self):
        try:
            if len(self.apk_paths) == 1:
                # Single APK install
                self.progress.emit(f"Installing {os.path.basename(self.apk_paths[0])}...")
                subprocess.check_output(
                    [self.adb_path, "-s", self.device_id, "install", "-r", self.apk_paths[0]],
                    text=True, stderr=subprocess.STDOUT
                )
            else:
                # Split APK install (multiple .apk files — use install-multiple)
                self.progress.emit(f"Installing split APK ({len(self.apk_paths)} files)...")
                subprocess.check_output(
                    [self.adb_path, "-s", self.device_id, "install-multiple", "-r"] + self.apk_paths,
                    text=True, stderr=subprocess.STDOUT
                )
            self.finished.emit("App installed successfully!", True)
        except subprocess.CalledProcessError as e:
            self.finished.emit(f"Install failed: {e.output.strip()[:80]}", False)


class ExportWorker(QThread):
    finished = Signal(str, bool)
    progress = Signal(str)

    def __init__(self, adb_path, device_id, app, dest_folder):
        super().__init__()
        self.adb_path = adb_path
        self.device_id = device_id
        self.app = app
        self.dest_folder = dest_folder

    def run(self):
        try:
            output = subprocess.check_output(
                [self.adb_path, "-s", self.device_id, "shell", "pm", "path", self.app],
                text=True
            )
            apk_paths = [p.strip().replace("package:", "") for p in output.strip().split('\n') if p.strip()]
            is_split = len(apk_paths) > 1
            dest = os.path.join(self.dest_folder, self.app) if is_split else self.dest_folder

            if is_split:
                os.makedirs(dest, exist_ok=True)

            for apk in apk_paths:
                self.progress.emit(f"Pulling {os.path.basename(apk)}...")
                subprocess.check_output(
                    [self.adb_path, "-s", self.device_id, "pull", apk, dest],
                    text=True
                )
                if not is_split:
                    filename = os.path.basename(apk)
                    src = os.path.join(dest, filename)
                    dst = os.path.join(dest, f"{self.app}.apk")
                    os.rename(src, dst)

            self.finished.emit(f"Exported to: {dest}", True)
        except subprocess.CalledProcessError:
            self.finished.emit("Failed to export app.", False)


# ── Main window ───────────────────────────────────────────────────────────────

class AppDialog(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ADB App Manager")
        self.setFixedSize(480, 340)
        self.setWindowIcon(svg_icon(phone_svg))

        self._worker = None  # keep reference so thread isn't GC'd

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # ── Top bar ──────────────────────────────────────────────────────────
        topbar = QHBoxLayout()

        label = QLabel("ADB App Manager")
        label.setStyleSheet("font-weight: bold; text-align: left;")
        topbar.addWidget(label)

        self.devices_list = QComboBox()
        self.devices_list.currentIndexChanged.connect(self.on_device_selected)
        topbar.addWidget(self.devices_list)

        refresh_btn = QPushButton()
        refresh_btn.setFixedSize(25, 25)
        refresh_btn.clicked.connect(self.on_refresh_clicked)
        refresh_btn.setIcon(svg_icon(refresh_svg))
        refresh_btn.setIconSize(QSize(18, 18))
        refresh_btn.setFlat(True)
        refresh_btn.setStyleSheet("border: none;")
        topbar.addWidget(refresh_btn)

        layout.addLayout(topbar)

        # ── Search ───────────────────────────────────────────────────────────
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search installed apps...")
        self.search_bar.textChanged.connect(self.on_search_text_changed)
        layout.addWidget(self.search_bar)

        # ── App list ─────────────────────────────────────────────────────────
        self.apps_list = QListWidget()
        layout.addWidget(self.apps_list)

        # ── Bottom bar ───────────────────────────────────────────────────────
        button_layout = QHBoxLayout()

        self.status_label = QLabel()
        button_layout.addWidget(self.status_label)
        button_layout.addStretch()

        import_btn = QPushButton("Import / Install")
        import_btn.setToolTip("Install an APK (or multiple split APKs) from your PC onto the device")
        import_btn.clicked.connect(self.on_import_clicked)
        button_layout.addWidget(import_btn)

        export_btn = QPushButton("Export")
        export_btn.setToolTip("Pull the selected app's APK from the device to your PC")
        export_btn.clicked.connect(self.on_export_clicked)
        button_layout.addWidget(export_btn)

        layout.addLayout(button_layout)

        self.on_refresh_clicked()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def show_status(self, text, color="red", duration=4000):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 11px;")
        QTimer.singleShot(duration, lambda: self.status_label.clear())

    def _set_buttons_enabled(self, enabled: bool):
        for btn in self.findChildren(QPushButton):
            btn.setEnabled(enabled)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def on_refresh_clicked(self):
        try:
            adb_output = subprocess.check_output([ADB_PATH, "devices"], text=True)
            devices = parse_adb_devices(adb_output)
            self.devices_list.blockSignals(True)
            self.devices_list.clear()
            self.devices_list.addItems(devices)
            self.devices_list.blockSignals(False)
            if devices:
                self.on_device_selected(0)
            else:
                self.apps_list.clear()
                self.show_status("No devices found.", color="orange")
        except subprocess.CalledProcessError:
            self.show_status("ADB error: could not list devices.")

    def on_device_selected(self, index):
        device_id = self.devices_list.currentText()
        if not device_id:
            return
        try:
            adb_output = subprocess.check_output(
                [ADB_PATH, "-s", device_id, "shell", "pm", "list", "packages"],
                text=True
            )
            apps = sorted(
                line.replace("package:", "").strip()
                for line in adb_output.strip().split('\n') if line.strip()
            )
            self.apps_list.clear()
            self.apps_list.addItems(apps)
            self.show_status(f"{len(apps)} packages loaded.", color="green", duration=2000)
        except subprocess.CalledProcessError:
            self.show_status("Failed to list packages.")

    def on_search_text_changed(self, text):
        for i in range(self.apps_list.count()):
            item = self.apps_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    # ── Import / Install ──────────────────────────────────────────────────────

    def on_import_clicked(self):
        device_id = self.devices_list.currentText()
        if not device_id:
            self.show_status("No device selected.")
            return

        # Let the user pick one or more APK files
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select APK file(s) to install",
            "",
            "APK files (*.apk);;All files (*.*)"
        )

        if not files:
            return

        self._set_buttons_enabled(False)
        self.show_status(f"Installing {len(files)} file(s)...", color="blue", duration=30000)

        self._worker = InstallWorker(ADB_PATH, device_id, files)
        self._worker.progress.connect(lambda msg: self.show_status(msg, color="blue", duration=30000))
        self._worker.finished.connect(self._on_install_finished)
        self._worker.start()

    def _on_install_finished(self, message, success):
        self._set_buttons_enabled(True)
        color = "green" if success else "red"
        self.show_status(message, color=color)
        if success:
            # Refresh package list so newly installed app shows up
            self.on_device_selected(self.devices_list.currentIndex())

    # ── Export ────────────────────────────────────────────────────────────────

    def on_export_clicked(self):
        device_id = self.devices_list.currentText()
        if not device_id:
            self.show_status("No device selected.")
            return

        selected_items = self.apps_list.selectedItems()
        if not selected_items:
            self.show_status("Please select an app to export.")
            return

        app_name = selected_items[0].text()
        folder = QFileDialog.getExistingDirectory(self, "Select destination folder", "", QFileDialog.ShowDirsOnly)
        if not folder:
            return

        self._set_buttons_enabled(False)
        self.show_status(f"Exporting {app_name}...", color="blue", duration=30000)

        self._worker = ExportWorker(ADB_PATH, device_id, app_name, folder)
        self._worker.progress.connect(lambda msg: self.show_status(msg, color="blue", duration=30000))
        self._worker.finished.connect(self._on_export_finished)
        self._worker.start()

    def _on_export_finished(self, message, success):
        self._set_buttons_enabled(True)
        self.show_status(message, color="green" if success else "red")


if __name__ == "__main__":
    if platform.system() == 'Windows':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("myapp.adbmanager.1")
    app = QApplication(sys.argv)
    dialog = AppDialog()
    dialog.show()
    sys.exit(app.exec())