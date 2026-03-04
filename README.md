# 🔋 Inverter Controller for Home Assistant

**A custom Home Assistant integration that allows you to control your inverter dynamically with highly configurable, reactive parameters.**

[![release](https://img.shields.io/github/v/release/MarcelWepper/Inverter-Controller?include_prereleases&style=flat-square)](https://github.com/MarcelWepper/Inverter-Controller/releases)
[![HACS Integration](https://img.shields.io/badge/HACS-Integration-blue.svg?style=flat-square)](https://github.com/hacs/integration)
[![License](https://img.shields.io/github/license/MarcelWepper/Inverter-Controller?style=flat-square&color=orange)](https://github.com/MarcelWepper/Inverter-Controller/blob/main/LICENSE)

[![Open your Home Assistant instance and open the repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=MarcelWepper&repository=Inverter-Controller&category=integration)

## 🚀 Key Features

* **Reactive Power Balancing**: Listens for state changes and adjusts power limits instantly as your house load shifts.
* **Configurable Deadband**: Fine-tune your import and export thresholds to tightly hug your home's actual consumption without oscillating.
* **Advanced Battery Protection**: Prevents "limit windup" spikes in the morning by safely clamping the inverter limit to available solar power when the battery is empty.
* **Stepped Start-up Limiter**: Optional stepped power caps during morning wake-up (100W under 10%, 200W under 15%, 300W under 20% SoC).
* **High SoC Solar Passthrough**: When the battery is full, the inverter limit tracks incoming solar production perfectly to export excess energy while covering the house load.
* **Advanced Statistics**: Provides calculated insights including Estimated House Load, Solar Yield Ratio, and an active Logic State indicator.

---

## ⚙️ Configuration

Go to **Settings > Devices & Services > Add Integration** and search for **Inverter Controller**. After the initial setup, you can change these at any time by clicking **Configure** on the integration.

### Mandatory Entities
* **Grid Power Sensor**: Measures net house power (Positive = Import from grid, Negative = Export to grid).
* **Battery SoC Sensor**: Measures battery percentage (0-100%).
* **Solar Production Sensor**: Measures raw PV power (Watts).
* **Inverter Limit Control**: The `number` or `input_number` entity that sets the inverter's maximum output limit.

### Detailed Configuration Parameters
* **Minimum Power (W)**: The absolute lowest limit the controller will ever set your inverter to (e.g., `100`). Used as the standby floor.
* **Maximum Power (W)**: The absolute highest limit the controller can set (e.g., `800`).
* **Adjustment Step Size**: How many Watts the limit increases/decreases per evaluation cycle (e.g., `50`).
* **Import Threshold (W)**: The deadband for grid import. The controller will only start stepping the limit *up* if your grid import exceeds this number (e.g., `10`).
* **Export Threshold (W)**: The deadband for grid export. The controller will only start stepping the limit *down* if your grid export exceeds this number (e.g., `20`).
* **Solar Passthrough Margin (W)**: During high SoC Boost mode, this amount is subtracted from your raw solar generation to create a safe export buffer (e.g., `50`).
* **Solar Smoothing Alpha (0-1)**: Exponential Moving Average factor. `0.1` is very slow/smooth, `0.9` reacts instantly to passing clouds.
* **Battery Boost Threshold (%)**: When SoC hits this target, the controller enters "Solar Passthrough" mode, exporting excess energy safely (e.g., `95`).
* **Empty Battery Standby Threshold (%)**: The point where the battery is considered "dead". The controller will park the inverter at `min_power` if the sun is down, and activate battery protection limiters when the sun comes up (e.g., `10`).
* **Enable Stepped Start-up Limiter**: A toggle switch for morning behavior:
  * **ON (Stepped)**: Forces strict power limits based on SoC: `100W` under 10%, `200W` under 15%, `300W` under 20%.
  * **OFF (Proportional)**: Smoothly interpolates the allowable battery contribution from 0W at the `Empty Threshold` up to full power at `Empty Threshold + 5%`.