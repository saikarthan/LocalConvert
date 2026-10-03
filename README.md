<div align="center">

# 🔒 LocalConvert

**A 100% Local, Privacy-First File Toolbox for Everyone.**  
*Created by **K. Sai Keerthan | Security Researcher***  
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

Whether you are on **Mobile (Android/iOS)** or **Desktop (Windows/Mac/Linux)**, LocalConvert processes files in local memory using HTML5 Canvas & WebAPIs. It works completely offline with WiFi turned off.

---

## ⚡ Instant Usage (Zero Installation)

No terminal, no command line, no apps needed.

### Option A: Open `localconvert.html` Directly
1. Download [`localconvert.html`](localconvert.html) from this repository.
2. Double-click or tap the file on your **Phone or PC**.
3. It opens instantly in **Chrome, Safari, Edge, or Brave**.
4. Start converting files right away — **100% offline & private**!

### Option B: Use GitHub Pages (1-Click Web)
- Simply open the live **GitHub Pages** link in your browser.
- All code executes inside your browser window. **Zero bytes are transmitted to any backend.**

---

## 💻 Optional: Local Python Server

If you prefer running the full suite with extended server capabilities (such as batch OCR, PDF parsing, or audio conversion):

```bash
# 1. Clone the repository
git clone https://github.com/saikarthan/LocalConvert.git
cd LocalConvert

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch LocalConvert
python app.py
```
> The application will automatically open at `http://127.0.0.1:5001`.

---

## 🛠️ Features (60+ Local Tools)

- 🖼️ **Image Tools**: JPG / PNG / WebP / BMP conversion, Image Compression, Resizing, Cropping, Rotation, EXIF & Metadata Stripping (removes GPS/camera tags), Base64 encoding/decoding.
- 📄 **PDF Tools**: Merge, Split, Rotate, Extract Pages, Page Counting, Compress, Watermark, Text to PDF, JPG to PDF.
- 🔤 **Text Tools**: Word & Character Counter, Case Converter, Remove Duplicate Lines, Line Sorting, Whitespace Cleaner, Find & Replace, Text Statistics.
- 🛠️ **Dev Tools**: JSON Formatter & Minifier, CSV ↔ JSON, URL Encoder/Decoder, Base64 String, UUID Generator, Password Generator, Color Converter (HEX/RGB/HSL).

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
  <sub>Built with ❤️ for privacy and user security everywhere by <b>K. Sai Keerthan | Security Researcher</b>.</sub>
</div>
