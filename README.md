<div align="center">

# 🔒 LocalConvert

**A 100% Local, Privacy-First File Toolbox for Everyone.**  
*Convert, edit, compress, and process files directly inside your browser — 0 servers, 0 uploads, 0 tracking.*

[![Privacy First](https://img.shields.io/badge/Privacy-100%25_Local-brightgreen?style=flat-square)](#)
[![No Data Uploads](https://img.shields.io/badge/Data_Transmission-Zero-blue?style=flat-square)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](#contributing)

[Features](#-features) • [Instant Usage](#-instant-usage-zero-installation) • [Local Server Setup](#-optional-local-python-server) • [Contributing](#-contributing)

</div>

---

## 🌟 Why LocalConvert?

Most online file converters force you to upload private documents, photos, and records to remote third-party servers. 

**LocalConvert is built on a single core principle:**  
*Your files should never leave your device.*

Whether you are on **Desktop (Windows/Mac/Linux)**, LocalConvert processes files locally using your Python environment. It works completely offline with no internet connection.

---

## ⚡ Quick Start (Zero Setup)

### 🪟 Windows
Double-click **`run.bat`**

### 🍎 Mac / 🐧 Linux
Run **`./run.sh`**

> The app automatically installs missing dependencies on first launch, starts a local server at `http://127.0.0.1:5000`, and opens your browser automatically.

---

## 💻 Manual Setup (Optional)

```bash
# 1. Clone the repository
git clone https://github.com/saikarthan/LocalConvert.git
cd LocalConvert

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch LocalConvert
python app.py
```
> The application will automatically open at `http://127.0.0.1:5000`.

---

## 🛠️ Features (60+ Local Tools)

- 🖼️ **Image Tools**: JPG / PNG / WebP / BMP conversion, Image Compression, Resizing, Cropping, Rotation, EXIF & Metadata Stripping (removes GPS/camera tags), Base64 encoding/decoding.
- 📄 **PDF Tools**: Merge, Split, Rotate, Extract Pages, Page Counting, Compress, Watermark, Text to PDF, JPG to PDF, PDF to Word, PDF to PowerPoint, Password Protection.
- 🎥 **Video & Audio**: Extract Audio (MP3/WAV), Compress Video, Audio Format Converter.
- 🔤 **Text Tools**: Word & Character Counter, Case Converter, Remove Duplicate Lines, Line Sorting, Whitespace Cleaner, Find & Replace, Text Statistics.
- 🛠️ **Dev Tools**: JSON Formatter & Minifier, CSV ↔ JSON, URL Encoder/Decoder, Base64 String, UUID Generator, Password Generator, QR Code Generator, Color Converter (HEX/RGB/HSL).

---

## 🤝 Contributing

**LocalConvert is open to everyone across the world!**  
Whether you want to add a new tool, improve the UI, fix a bug, or write documentation, your contributions are warmly welcomed.

### How to Contribute:
1. **Fork** the repository.
2. Create a new branch: `git checkout -b feature/awesome-tool`
3. Commit your changes: `git commit -m 'Add awesome local tool'`
4. Push to the branch: `git push origin feature/awesome-tool`
5. Open a **Pull Request**.

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.

<div align="center">
  <sub>Built with ❤️ for privacy and user security everywhere. — K. Sai Keerthan | Security Researcher</sub>
</div>
