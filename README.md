![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![Linux](https://img.shields.io/badge/OS-Linux-black?logo=linux&logoColor=white)
![Aiogram](https://img.shields.io/badge/Framework-Aiogram_3.x-269539?logo=telegram&logoColor=white)
![TCPDump](https://img.shields.io/badge/Tool-TCPDump-red)

> **[🇷🇺 Читать инструкцию на русском языке (Russian Docs)](README_RUS.md)**

A powerful Telegram bot for network traffic analysis and management. It allows you to capture traffic (`.pcap`) in real-time, analyze logs remotely, identify DDoS attacks, and inspect DNS/HTTPS queries directly from your phone.

---

## ✨ Features

*   **🔴 Real-time Capture:** Record network traffic for a specified duration (`/capture`).
*   **📂 Log Management:** List, download, and delete `.pcap` files.
*   **📊 Traffic Analysis:**
    *   **Top IPs:** Identify most active IP addresses (useful for detecting DDoS).
    *   **DNS & SNI:** See which domains and sites are being requested.
    *   **User-Agents:** Identify devices (iPhone, Android, Bots).
*   **🌍 GeoIP Lookup:** Automatically fetch Country, ISP, and Organization for suspicious IPs.
*   **🔒 Admin Only:** Restricted access via Telegram User ID.

---

## ⚙️ Prerequisites

*   **OS:** Linux (Ubuntu, Debian, CentOS, etc.)
*   **Python:** 3.8+
*   **Tools:** `tcpdump` must be installed.
*   **Root Privileges:** Required for `tcpdump` to listen to network interfaces.

## 🚀 Installation

1.  **Clone the repository or upload files:**
    ```bash
    mkdir -p ~/tcpdumpLOGS/bot
    cd ~/tcpdumpLOGS/bot
    # Upload main.py here
    ```

2.  **Create a Virtual Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install aiogram aiohttp
    ```

4.  **Configuration:**
    Open `main.py` and edit the configuration section:
    ```python
    API_TOKEN = 'YOUR_BOT_TOKEN'
    ADMIN_ID = 123456789  # Your Telegram ID
    LOGS_DIR = '/home/username/tcpdumpLOGS/'
    ```

## 🛠 Usage

1.  **Start the bot:**
    ```bash
    sudo ./venv/bin/python main.py
    ```
    *(Sudo is required for traffic capturing)*

2.  **Telegram Commands:**
    *   `/start` - Welcome guide.
    *   `/capture` - Start recording traffic (specify duration in seconds).
    *   `/stats` - Open the file analysis menu.
    *   `/download` - Download `.pcap` files.

---

## 🔄 Run as a Service (Systemd)

To keep the bot running 24/7 (uptime), create a system service.

1.  **Create service file:**
    ```bash
    sudo nano /etc/systemd/system/tcpdumpbot.service
    ```

2.  **Paste the configuration:**
    *(Adjust paths to your actual location)*
    ```ini
    [Unit]
    Description=Telegram Bot for TCPDump
    After=network.target

    [Service]
    User=root
    WorkingDirectory=/home/flexebat/tcpdumpLOGS/bot
    ExecStart=/home/flexebat/tcpdumpLOGS/bot/venv/bin/python /home/flexebat/tcpdumpLOGS/bot/main.py
    Restart=always
    RestartSec=5

    [Install]
    WantedBy=multi-user.target
    ```

3.  **Enable and Start:**
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable tcpdumpbot
    sudo systemctl start tcpdumpbot
    ```

---
