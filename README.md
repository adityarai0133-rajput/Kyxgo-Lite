<div align="center">

# ⚡ Kyxgo Lite — Ultra-Fast Offline Study & Code Knowledge Engine

**100% Offline Desktop Search & Study Assistant for Low-End Windows PCs (< 60 MB RAM)**  
*No Internet • No Cloud • No Ads • No Subscriptions • Zero Tracking*

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6?logo=windows)](../../releases)
[![RAM Usage: <60MB](https://img.shields.io/badge/RAM%20Usage-%3C%2060%20MB-brightgreen)]()
[![Offline: 100%](https://img.shields.io/badge/Internet-Not%20Required-success)]()
[![Engine: SQLite FTS5](https://img.shields.io/badge/Search%20Engine-SQLite%20FTS5-orange)]()

[**📥 Download KyxgoLite.exe (Latest Release)**](../../releases) • [**🐞 Report Issue**](../../issues) • [**📖 Documentation**](#-how-kyxgo-lite-works)

</div>

---

## 🔍 What is Kyxgo Lite?

**Kyxgo Lite** is an open-source, lightweight, **offline-first desktop knowledge and study assistant** developed by **Aditya Rai (Kyxgo Technology)**. Unlike heavy local LLM tools (such as Ollama or GPT4All) that require 8GB–16GB RAM and high-end GPUs, **Kyxgo Lite runs smoothly under 60 MB RAM** on any 2GB or 4GB RAM Windows laptop or desktop.

Powered by an embedded **SQLite FTS5 (Full-Text Search)** engine with Porter stemming and extractive sentence scoring, Kyxgo Lite indexes your local **`.txt`, `.md`, `.py` (Python code), and text-based `.pdf` files** to deliver instant, accurate answers and formulas in under **0.01 seconds**—completely offline.

---

## 🚀 Key Features & Highlights

- **⚡ Lightning-Fast Offline Search (0.01s):** Uses SQLite FTS5 BM25 ranking and smart sentence/formula extraction to pinpoint exact definitions and equations from thousands of pages.
- **🪶 Ultra-Low RAM Footprint (< 60 MB):** Built with pure Python standard libraries and native Tkinter—zero Electron or heavy PyTorch bloat.
- **📚 Multi-Format Local Indexing:** Automatically scans and indexes **TXT, Markdown (MD), Python (PY), and text-based PDF** study notes and codebases.
- **🔒 Dual Privacy Modes (Saved vs. Temp RAM Mode):**
  - **Saved Mode:** Stores chat history locally in an SQLite vault with **1-click single chat deletion** and **Wipe All** support.
  - **Temp RAM Mode (`:memory:`):** Runs 100% inside volatile RAM—closing the app leaves **zero files or traces** on your hard drive.
- **🧠 Hinglish & English Follow-Up Context:** Understands short follow-up queries (e.g., *"formula batao"*, *"explain more"*, *"iska unit"*) using active topic context.
- **📦 Standalone Windows `.exe`:** No Python setup or command-line knowledge required—just download and double-click.

---

## 📊 Kyxgo Lite vs. Traditional Offline AI Tools

| Feature | Kyxgo Lite | Heavy Local LLMs (Ollama / GPT4All) |
| :--- | :--- | :--- |
| **Minimum RAM Required** | **2 GB RAM (< 60 MB App Usage)** | 8 GB – 16 GB RAM |
| **GPU Requirement** | **None (Runs on any CPU)** | Dedicated GPU recommended |
| **Response Speed** | **Instant (~10 milliseconds)** | 5 – 30 seconds per reply |
| **Internet Required** | **0% (100% Offline)** | Only for model downloads (4GB+) |
| **Zero-Trace RAM Mode** | **Built-in (`:memory:` DB)** | Not available |
| **Setup Size** | **~15 MB Single `.exe`** | 4 GB – 10 GB+ |

---

## 📋 Technical Capability Matrix

| Capability | Status | Details |
| :--- | :--- | :--- |
| Offline Full-Text Search (SQLite FTS5) | ✅ Supported | Porter stemming + Unicode tokenization |
| Crisp Answer & Formula Extraction | ✅ Supported | Extracts top relevant sentences & equations |
| `.txt`, `.md`, `.py` File Indexing | ✅ Supported | Recursive folder & subfolder scanning |
| Text-Based `.pdf` Indexing | ✅ Supported | Fast text extraction via `pypdf` |
| Scanned / Image-Only PDF (OCR) | ❌ Not Included | Excluded intentionally to keep RAM < 60 MB |
| Single Chat & Full History Wipe | ✅ Supported | Instant local database deletion |
| RAM-Only Temporary Session | ✅ Supported | Automatic memory flush on window exit |

---

## 📥 Installation & Quick Start

### Option 1: Windows Standalone Executable (Recommended)
1. Visit the **[GitHub Releases](../../releases)** page.
2. Download **`KyxgoLite.exe`**.
3. Double-click **`KyxgoLite.exe`** to launch—it automatically creates a `my_notes` folder with a sample guide.
4. Click **📂 Pick Folder** anytime to index your own NCERT PDFs, coaching notes, or Python projects.

### Option 2: Run from Python Source
```bash
git clone [https://github.com/adityarai0133/Kyxgo-Lite.git](https://github.com/adityarai0133/Kyxgo-Lite.git)
cd Kyxgo-Lite
pip install -r requirements.txt
python kyxgo_app.py
