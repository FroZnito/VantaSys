# VantaSys Monitor - CPU-Z Edition (v7.0)

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Version](https://img.shields.io/badge/version-v7.0.0-purple)
![License](https://img.shields.io/badge/license-MIT-green)

**VantaSys CPU-Z** is the densest, most detailed system monitor available. It combines "Omniscience" interactivity with "CPU-Z" depth.

![VantaSys Dashboard](https://via.placeholder.com/800x450?text=VantaSys+CPU-Z+Comparison)

## 🧠 New in v7.0 "CPU-Z"

- **Dense Specs**: The CPU tile now shows **Cache Sizes (L2/L3)**, **Socket Type**, and **Microcode Stepping** directly on the dashboard.
- **RAM Inspector**: View individual memory module details (stick count) at a glance.
- **Service Fixes**: The Windows Service manager is now robust and error-proof.
- **Terminal Upgrade**: The Event Log now handles long text with proper wrapping and auto-scroll.

## Key Features

- **Total Observability**: Hardware, Software, Services, Network.
- **Interactive Deep Dives**: Click any tile to inspect internals.
- **Historical Trends**: 5-Min rolling charts.
- **Instant Performance**: Zero-blocking background loads.

## Installation

### Prerequisites

- Python 3.11+
- Windows (Recommended for full Hardware/Service features).

### Quick Start

1. Install Deps:
   ```bash
   pip install -r requirements.txt
   ```
2. Run:
   ```bash
   python app.py --reload
   ```
   Open **http://localhost:8000**.

### Build

```bash
python build.py
```
