# ADB App Manager

A Windows-only graphical user interface (GUI) for managing Android applications using ADB (Android Debug Bridge). This tool allows you to easily install, export, and manage apps on connected Android devices.

## Features

- **Device Management**: Automatically detect and select from connected Android devices
- **App Listing**: View all installed packages on the selected device
- **App Search**: Filter installed apps by name in real-time
- **Install Apps**: Install single APK files or split APK bundles to your device
- **Export Apps**: Extract APK files from your device to your computer
- **Modern GUI**: Clean, intuitive interface built with PySide6
- **Visual Feedback**: Status messages keep you informed of operation progress

## Requirements

- **Windows 7 or later**
- **ADB** (Android Debug Bridge) - installed and available in PATH or via `ADB_PATH` environment variable
- **Android Device** - connected via USB with USB debugging enabled
- **Python 3.7+** (only if running from source code)

## Dependencies

```
PySide6
```

Install dependencies with:
```bash
pip install PySide6
```

## Installation

### Option 1: Using the Executable (Recommended)

1. Download the `.exe` file
2. Install ADB (Android SDK Platform-Tools) or ensure it's in your PATH
3. Double-click `ADB_App_Manager.exe` to launch

### Option 2: Running from Source Code

1. Clone or download this project
2. Install Python 3.7 or later
3. Install ADB (Android SDK Platform-Tools)
4. Install required Python packages:
   ```bash
   pip install PySide6
   ```
5. Run the application:
   ```bash
   python main.py
   ```

## Usage

### Basic Workflow

1. **Connect Your Device**: Connect your Android device via USB and enable USB debugging
2. **Launch the App**: Run `python main.py`
3. **Refresh Devices**: Click the refresh button to detect connected devices
4. **Select Device**: Choose your device from the dropdown
5. **Browse Apps**: The app list will populate with installed packages

### Installing Apps

1. Click **"Import / Install"**
2. Select one or more APK files from your computer
3. Click "Open" - the app will install to your selected device
4. Wait for the installation to complete (check the status message)

### Exporting Apps

1. Select an app from the list
2. Click **"Export"**
3. Choose a destination folder
4. The app's APK will be saved to your computer
5. Split APKs will be saved in a folder named after the app

### Searching Apps

- Type in the search bar to filter installed packages
- Search is case-insensitive and filters in real-time

## Configuration

### Custom ADB Path

By default, the app uses `adb.exe` from your PATH. To specify a custom ADB location:

```bash
set ADB_PATH=C:\path\to\adb.exe
python main.py
```

Or set the environment variable in Windows Settings before running the `.exe` file.

## Troubleshooting

### "No devices found"
- Ensure your Android device is connected via USB
- Enable USB debugging on your device (Settings → Developer Options → USB Debugging)
- Run `adb devices` in terminal to verify connection

### "ADB error: could not list devices"
- Verify ADB is installed and in your PATH
- Check the `ADB_PATH` environment variable if using a custom location
- Restart ADB server: `adb kill-server` then `adb start-server`

### Installation fails
- Ensure the APK is compatible with your device's Android version
- Check if there's sufficient storage on the device

### Export fails
- Verify you have read permissions to the app's APK
- Some system apps may not be exportable
- Check the destination folder has write permissions


## Notes
- **Windows only** - This application is designed and tested for Windows 7 and later

## Support

For issues or questions, ensure:
1. You're running on Windows 7 or later
2. ADB is properly installed and accessible
3. Your device is connected and USB debugging is enabled
4. If running from source, all Python dependencies are installed and you have Python 3.7 or later
