# Display Setup

## Installation

1.  Enable SPI interface:
    ```bash
    sudo raspi-config nonint do_spi 0
    ```
2.  Ensure you have created and activated a virtual environment (see [../README.md](../README.md)).
3.  Install required Python packages:
    ```bash
    pip3 install displayhatmini rpi-lgpio pillow
    ```

## Troubleshooting

**Error:** `RuntimeError: Cannot determine SOC peripheral base address.`

This error can occur due to conflicting GPIO library versions.

**Cause:** Sometimes, system-wide installations conflict with virtual environment installations. Attempting `pip uninstall lgpio` might show:

```
Found existing installation : lgpio 0.2.2.0
Not uninstalling lgpio at /usr/lib/python3/dist-packages, outside environment /home/yxh/Documents/mfalock/venv/
Can't uninstall 'lgpio'. No files were found to uninstall.
```

**Solution:** Remove the system-wide package:

```bash
sudo apt remove --purge python3-lgpio