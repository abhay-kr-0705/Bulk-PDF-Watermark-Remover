# Bulk PDF Watermark Remover & Link Adder

A standalone desktop application and Python script that gives you fine-grained control over modifying thousands of PDFs at once. With its modern GUI, you can seamlessly mirror directory structures, erase stubborn logos, stamp custom text/image watermarks, and insert clickable footer links across massive collections of PDF files.

## Features

- **Blazing Fast**: Uses `PyMuPDF` (`fitz`) to rapidly process thousands of PDFs in nested folders.
- **Maintain Directory Structures**: Automatically mirrors your input folder (with all subfolders!) into the output folder.
- **Single File Processing**: Easily process an entire folder structure, or target a single specific PDF document.
- **Smart Logo Eraser**: Upload a specific image (like an old watermark logo). The program will scan all pages and remove it.
- **Add Custom Watermarks**:
  - **Text Mode**: Input any string, scale font size, tweak opacity (0.1 to 1.0), adjust angular rotation, and place it anywhere (Top-Left, Center, Bottom-Right, etc.).
  - **Image Mode**: Upload your own watermark image, adjust the scaling %, set opacity, and place it anywhere on the page.
  - **Tiled (Everywhere)**: Mathematically maps and repeats your text or image in a staggered, seamlessly offset grid across the entire page (supports diagonal text rotation mapping).
- **Interactive Live Preview**: Features a real-time, split-screen UI that instantly renders how your watermark will look on the exact target PDF.
  - **Zoom Support**: Hover and scroll your mouse wheel to zoom in (up to 5x) for precise pixel alignment.
  - **Pan & Drag**: Click and hold to drag the zoomed-in canvas around to verify margins and corners effortlessly.
- **Clickable Footer Links**: Add custom text to the bottom of every page that hyperlinks to your destination URL.
- **Responsive GUI**: Built with `customtkinter` on a background thread so the UI never freezes while processing. Tracks exact file progress.

## How to use

### Option 1: Standalone Application 
Simply download the `Bulk_PDF_Watermark.exe` file from the `dist/` directory. Double-click to launch it on any Windows machine. No Python or IDE required!

### Option 2: Run via CLI / Python
1. Clone this repository:
   ```bash
   git clone https://github.com/abhay-kr-0705/Bulk-PDF-Watermark-Remover.git
   cd Bulk-PDF-Watermark-Remover
   ```
2. Set up a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
3. Run the GUI:
   ```bash
   python main_app.py
   ```

## Development & Building

If you want to package your own `.exe` file after modifying the code, run:
```bash
pyinstaller --noconsole --onefile --name "Bulk_PDF_Watermark" main_app.py
```
This will compile everything and generate an `.exe` inside the `dist` folder. 
