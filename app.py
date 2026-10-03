import io, os, re, time, uuid, shutil, zipfile, pathlib
import tempfile, threading, subprocess, webbrowser

from flask import Flask, request, jsonify, Response, render_template
from werkzeug.exceptions import HTTPException
from pypdf import PdfReader, PdfWriter
from PIL import Image, ImageOps

try:
    import pymupdf as fitz
except ImportError:
    import fitz

from pdf2docx import Converter
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.colors import Color
from reportlab.lib.pagesizes import A4, LETTER

try:
    from pillow_heif import register_heif_opener
    register_heif_opener(); HAS_HEIC = True
except Exception:
    HAS_HEIC = False

try:
    from pptx import Presentation
    HAS_PPTX = True
except Exception:
    HAS_PPTX = False

try:
    import qrcode
    HAS_QR = True
except Exception:
    HAS_QR = False

try:
    import pytesseract
    HAS_OCR = True
except Exception:
    HAS_OCR = False

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024**3

# Detect Android / Termux
IS_TERMUX = os.path.isdir("/data/data/com.termux")


@app.after_request
def add_security_headers(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("X-XSS-Protection", "1; mode=block")
    resp.headers.setdefault("Referrer-Policy", "no-referrer")
    resp.headers.setdefault("Permissions-Policy",
                            "geolocation=(), microphone=(), camera=(), payment=()")
    resp.headers.setdefault("Content-Security-Policy",
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "connect-src 'self'; "
        "font-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self';")
    return resp


TEMP = os.path.join(tempfile.gettempdir(), "localconvert")
os.makedirs(TEMP, exist_ok=True)


class ToolError(Exception):
    pass

# ---------------- helpers ----------------

def safe_name(name):
    base = os.path.splitext(os.path.basename(name))[0]
    return re.sub(r"[^A-Za-z0-9_\- ]", "_", base).strip() or "file"

def base_of(p):
    return os.path.splitext(os.path.basename(p))[0]

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def to_int(v, what="value"):
    try:
        return int(str(v).strip())
    except Exception:
        raise ToolError(f"'{v}' is not a valid {what}")

def find_ffmpeg():
    p = shutil.which("ffmpeg")
    if p:
        return p
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return None

def find_soffice():
    for c in [shutil.which("soffice"), shutil.which("soffice.exe"),
              r"C:\Program Files\LibreOffice\program\soffice.exe",
              r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
              "/usr/bin/soffice", "/usr/local/bin/soffice",
              "/Applications/LibreOffice.app/Contents/MacOS/soffice"]:
        if c and os.path.exists(c):
            return c
    return None

FFMPEG = find_ffmpeg()
SOFFICE = find_soffice()

def open_pdf(path, password=""):
    r = PdfReader(path)
    if r.is_encrypted and int(r.decrypt(password or "")) == 0:
        raise ToolError("password-protected PDF - use unlock first (or enter the right password)")
    return r

def hex_bg(s):
    s = (s or "").lstrip("#").strip()
    if not re.fullmatch(r"[0-9a-fA-F]{6}", s):
        return (255, 255, 255)
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))

def flatten_bg(img, bg=(255, 255, 255)):
    if img.mode in ("RGBA", "LA", "P") or "transparency" in img.info:
        img = img.convert("RGBA")
        base = Image.new("RGB", img.size, bg)
        base.paste(img, mask=img.split()[-1])
        return base
    return img if img.mode == "RGB" else img.convert("RGB")

def overlay(w, h, draw):
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=(w, h))
    draw(c, w, h)
    c.save()
    buf.seek(0)
    return PdfReader(buf).pages[0]

def ffmpeg_run(args, src, dst):
    if not FFMPEG:
        raise ToolError("ffmpeg not found - run: pip install imageio-ffmpeg")
    try:
        r = subprocess.run([FFMPEG, "-y", "-i", src] + args + [dst],
                           capture_output=True, timeout=3600)
    except subprocess.TimeoutExpired:
        raise ToolError("ffmpeg timed out")
    if r.returncode != 0:
        raise ToolError(r.stderr.decode(errors="ignore")[-200:])

def parse_ranges(s, n):
    rngs = []
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            a, b = to_int(a, "page number"), to_int(b, "page number")
        else:
            a = b = to_int(part, "page number")
        a, b = clamp(a - 1, 0, n - 1), clamp(b, 1, n)
        if a <= b:
            rngs.append((a, b))
    if not rngs:
        raise ToolError("no valid ranges - example: 1-3, 5, 8-10")
    return rngs

# ---------------- image tools ----------------

IMG_FMT = {"png": "PNG", "jpg": "JPEG", "webp": "WEBP", "bmp": "BMP", "tiff": "TIFF"}

def t_img_to(paths, opts, wd):
    to = opts.get("to", "png")
    fmt, ext = IMG_FMT[to], "." + to
    q = clamp(to_int(opts.get("quality") or 92, "quality"), 5, 100)
    bg = hex_bg(opts.get("bg"))
    outs = []
    for p in paths:
        img = Image.open(p)
        if fmt in ("JPEG", "BMP"):
            img = flatten_bg(img, bg)
        dst = os.path.join(wd, base_of(p) + ext)
        if fmt in ("JPEG", "WEBP"):
            img.save(dst, fmt, quality=q)
        else:
            img.save(dst, fmt)
        outs.append((dst, os.path.basename(dst)))
    return outs

def t_img_compress(paths, opts, wd):
    q = clamp(to_int(opts.get("quality") or 70, "quality"), 5, 95)
    outs = []
    for p in paths:
        img = Image.open(p)
        ext = os.path.splitext(p)[1].lower()
        if ext in (".jpg", ".jpeg"):
            img, fmt, oext = flatten_bg(img), "JPEG", ".jpg"
        elif ext == ".webp":
            fmt, oext = "WEBP", ".webp"
        elif ext == ".png":
            fmt, oext = "PNG", ".png"
        else:
            raise ToolError("compress supports jpg, png, webp")
        dst = os.path.join(wd, base_of(p) + "_min" + oext)
        if fmt == "PNG":
            img.save(dst, fmt, optimize=True)
        else:
            img.save(dst, fmt, quality=q)
        outs.append((dst, os.path.basename(dst)))
    return outs

def t_compress_jpg(paths, opts, wd):
    q = clamp(to_int(opts.get("quality") or 70, "quality"), 5, 95)
    outs = []
    for p in paths:
        img = flatten_bg(Image.open(p))
        dst = os.path.join(wd, base_of(p) + "_q" + str(q) + ".jpg")
        img.save(dst, "JPEG", quality=q, optimize=True)
        outs.append((dst, os.path.basename(dst)))
    return outs

def t_compress_png(paths, opts, wd):
    as_ = opts.get("as", "webp")
    q = clamp(to_int(opts.get("quality") or 80, "quality"), 5, 95)
    outs = []
    for p in paths:
        img = Image.open(p)
        if as_ == "jpg":
            img = flatten_bg(img)
            dst = os.path.join(wd, base_of(p) + "_q.jpg")
            img.save(dst, "JPEG", quality=q, optimize=True)
        elif as_ == "png":
            dst = os.path.join(wd, base_of(p) + "_min.png")
            img.save(dst, "PNG", optimize=True)
        else:
            dst = os.path.join(wd, base_of(p) + "_small.webp")
            img.save(dst, "WEBP", quality=q, method=6)
        outs.append((dst, os.path.basename(dst)))
    return outs

def t_img_resize(paths, opts, wd):
    tw = to_int(opts["width"], "width") if opts.get("width") else None
    th = to_int(opts["height"], "height") if opts.get("height") else None
    pc = float(opts["percent"]) if opts.get("percent") else None
    outs = []
    for p in paths:
        img = Image.open(p)
        w0, h0 = img.size
        if pc:
            tw2, th2 = max(1, round(w0 * pc / 100)), max(1, round(h0 * pc / 100))
        elif tw and th:
            tw2, th2 = tw, th
        elif tw:
            tw2, th2 = tw, max(1, round(h0 * tw / w0))
        elif th:
            tw2, th2 = max(1, round(w0 * th / h0)), th
        else:
            raise ToolError("set width, height or percent")
        img = img.resize((tw2, th2), Image.LANCZOS)
        ext = os.path.splitext(p)[1].lower()
        if ext in (".jpg", ".jpeg"):
            img = flatten_bg(img)
        dst = os.path.join(wd, f"{base_of(p)}_{tw2}px{ext}")
        img.save(dst)
        outs.append((dst, os.path.basename(dst)))
    return outs

def t_img_rotate(paths, opts, wd):
    rot = to_int(opts.get("angle") or 0, "angle")
    flip = opts.get("flip", "none")
    outs = []
    for p in paths:
        img = Image.open(p)
        if rot:
            img = img.transpose(getattr(Image.Transpose, "ROTATE_" + str(rot)))
        if flip == "h":
            img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        elif flip == "v":
            img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        ext = os.path.splitext(p)[1].lower()
        if ext in (".jpg", ".jpeg"):
            img = flatten_bg(img)
        dst = os.path.join(wd, base_of(p) + "_rot" + ext)
        img.save(dst)
        outs.append((dst, os.path.basename(dst)))
    return outs

def t_heic(paths, opts, wd):
    if not HAS_HEIC:
        raise ToolError("HEIC support missing - run: pip install pillow-heif")
    q = clamp(to_int(opts.get("quality") or 90, "quality"), 5, 100)
    outs = []
    for p in paths:
        img = ImageOps.exif_transpose(Image.open(p))
        if img.mode != "RGB":
            img = img.convert("RGB")
        dst = os.path.join(wd, base_of(p) + ".jpg")
        img.save(dst, "JPEG", quality=q)
        outs.append((dst, os.path.basename(dst)))
    return outs

# ---------------- pdf tools ----------------

def t_merge(paths, opts, wd):
    w = PdfWriter()
    for p in paths:
        for pg in open_pdf(p).pages:
            w.add_page(pg)
    dst = os.path.join(wd, "merged.pdf")
    w.write(dst)
    return [(dst, "merged.pdf")]

def t_split(paths, opts, wd):
    r = open_pdf(paths[0])
    n = len(r.pages)
    base = base_of(paths[0])
    if opts.get("mode") == "ranges":
        rngs = parse_ranges(opts.get("ranges", ""), n)
    else:
        rngs = [(i, i + 1) for i in range(n)]
    outs = []
    for i, (a, b) in enumerate(rngs, 1):
        w = PdfWriter()
        for j in range(a, b):
            w.add_page(r.pages[j])
        name = f"{base}_p{i}.pdf"
        p = os.path.join(wd, name)
        w.write(p)
        outs.append((p, name))
    return outs

def _raster_pdf(doc, dpi, q, dst):
    new = fitz.open()
    for pg in doc:
        pix = pg.get_pixmap(dpi=dpi, colorspace=fitz.csRGB, alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=q)
        npg = new.new_page(width=pg.rect.width, height=pg.rect.height)
        npg.insert_image(npg.rect, stream=buf.getvalue())
    new.save(dst, garbage=4, deflate=True)
    new.close()

def t_compress(paths, opts, wd):
    doc = fitz.open(paths[0])
    if doc.is_encrypted and int(doc.authenticate("")) == 0:
        raise ToolError("password-protected PDF")
    dst = os.path.join(wd, base_of(paths[0]) + "_compressed.pdf")
    lvl = opts.get("level", "light")
    if lvl == "strong":
        _raster_pdf(doc, 100, 55, dst)
    elif lvl == "medium":
        _raster_pdf(doc, 150, 72, dst)
    else:
        doc.save(dst, garbage=4, deflate=True, deflate_images=True,
                 deflate_fonts=True, clean=True)
    doc.close()
    return [(dst, os.path.basename(dst))]

def t_pdf_to_docx(paths, opts, wd):
    src = paths[0]
    open_pdf(src)
    dst = os.path.join(wd, base_of(src) + ".docx")
    cv = Converter(src)
    try:
        cv.convert(dst)
    finally:
        cv.close()
    return [(dst, os.path.basename(dst))]

def t_pdf_to_jpg(paths, opts, wd):
    doc = fitz.open(paths[0])
    if doc.is_encrypted and int(doc.authenticate("")) == 0:
        raise ToolError("password-protected PDF")
    dpi = clamp(to_int(opts.get("dpi") or 150, "dpi"), 50, 400)
    q = clamp(to_int(opts.get("quality") or 90, "quality"), 50, 100)
    base = base_of(paths[0])
    outs = []
    for i, pg in enumerate(doc, 1):
        pix = pg.get_pixmap(dpi=dpi, colorspace=fitz.csRGB, alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        dst = os.path.join(wd, f"{base}_{i}.jpg")
        img.save(dst, "JPEG", quality=q)
        outs.append((dst, os.path.basename(dst)))
    doc.close()
    return outs

def t_img_pdf(paths, opts, wd):
    page = {"a4": A4, "letter": LETTER}.get(opts.get("size", "fit"))
    margin = max(0.0, float(opts.get("margin") or 0)) * 72 / 25.4
    dst = os.path.join(wd, base_of(paths[0]) + ".pdf")
    c = rl_canvas.Canvas(dst)
    first = True
    for p in paths:
        img = ImageOps.exif_transpose(Image.open(p))
        if img.mode in ("CMYK", "YCbCr"):
            img = img.convert("RGB")
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA" if (img.mode == "P" and "transparency" in img.info)
                              or img.mode == "LA" else "RGB")
        iw, ih = img.size
        if page:
            pw, ph = page
            aw, ah = pw - 2 * margin, ph - 2 * margin
            sc = min(aw / iw, ah / ih)
            dw, dh = iw * sc, ih * sc
            x, y = margin + (aw - dw) / 2, margin + (ah - dh) / 2
        else:
            dw, dh = iw * 0.75, ih * 0.75
            x = y = 0
            pw, ph = dw, dh
        if not first:
            c.showPage()
        first = False
        c.setPageSize((pw, ph))
        tmp = os.path.join(wd, uuid.uuid4().hex + ".png")
        img.save(tmp, "PNG")
        c.drawImage(tmp, x, y, dw, dh, mask="auto")
        os.remove(tmp)
    c.save()
    return [(dst, os.path.basename(dst))]

def t_office_pdf(paths, opts, wd):
    if not SOFFICE:
        raise ToolError("LibreOffice not found - install it once from libreoffice.org, "
                        "then restart this tool (needed for Office to PDF)")
    outs = []
    for p in paths:
        profile = os.path.join(wd, "lo_" + uuid.uuid4().hex[:8])
        os.makedirs(profile, exist_ok=True)
        try:
            subprocess.run(
                [SOFFICE, f"-env:UserInstallation={pathlib.Path(profile).as_uri()}",
                 "--headless", "--norestore", "--convert-to", "pdf", "--outdir", wd, p],
                capture_output=True, timeout=300)
        except subprocess.TimeoutExpired:
            raise ToolError("conversion timed out")
        out = os.path.join(wd, base_of(p) + ".pdf")
        if not os.path.exists(out):
            raise ToolError("LibreOffice failed - close any open LibreOffice window and retry")
        outs.append((out, os.path.basename(out)))
    return outs

def t_rotate(paths, opts, wd):
    deg = to_int(opts.get("angle") or 90, "angle")
    r = open_pdf(paths[0])
    n = len(r.pages)
    sel = set(range(n))
    if (opts.get("pages") or "").strip():
        sel = set()
        for a, b in parse_ranges(opts["pages"], n):
            sel.update(range(a, b))
    w = PdfWriter()
    for i, pg in enumerate(r.pages):
        if i in sel:
            pg.rotate(deg)
        w.add_page(pg)
    dst = os.path.join(wd, base_of(paths[0]) + "_rotated.pdf")
    w.write(dst)
    return [(dst, os.path.basename(dst))]

def t_extract(paths, opts, wd):
    if not (opts.get("ranges") or "").strip():
        raise ToolError("enter pages to keep - e.g. 2, 5-7, 12")
    r = open_pdf(paths[0])
    n = len(r.pages)
    w = PdfWriter()
    for a, b in parse_ranges(opts["ranges"], n):
        for j in range(a, b):
            w.add_page(r.pages[j])
    if len(w.pages) == 0:
        raise ToolError("nothing selected")
    dst = os.path.join(wd, base_of(paths[0]) + "_extract.pdf")
    w.write(dst)
    return [(dst, os.path.basename(dst))]

def t_count(paths, opts, wd):
    files = [{"name": os.path.basename(p), "pages": len(open_pdf(p).pages)} for p in paths]
    return {"report": {"files": files, "total": sum(f["pages"] for f in files)}}

def t_watermark(paths, opts, wd):
    txt = (opts.get("text") or "").strip()
    if not txt:
        raise ToolError("enter watermark text")
    txt = txt.encode("latin-1", "ignore").decode() or "watermark"
    pos = opts.get("position", "diagonal")
    size = clamp(to_int(opts.get("size") or 40, "size"), 8, 200)
    op = clamp(to_int(opts.get("opacity") or 25, "opacity"), 5, 100) / 100
    r = open_pdf(paths[0])
    w = PdfWriter()
    for pg in r.pages:
        W, H = float(pg.mediabox.width), float(pg.mediabox.height)
        def draw(c, W, H):
            c.setFillColor(Color(0.5, 0.5, 0.5, alpha=op))
            c.setFont("Helvetica", size)
            if pos == "diagonal":
                c.translate(W / 2, H / 2); c.rotate(45)
                c.drawCentredString(0, 0, txt)
            elif pos == "top":
                c.drawCentredString(W / 2, H - size - 10, txt)
            elif pos == "bottom":
                c.drawCentredString(W / 2, 15, txt)
            else:
                c.drawCentredString(W / 2, H / 2 - size / 3, txt)
        pg.merge_page(overlay(W, H, draw))
        w.add_page(pg)
    dst = os.path.join(wd, base_of(paths[0]) + "_watermarked.pdf")
    w.write(dst)
    return [(dst, os.path.basename(dst))]

def t_page_numbers(paths, opts, wd):
    r = open_pdf(paths[0])
    w = PdfWriter()
    for i, pg in enumerate(r.pages, 1):
        W, H = float(pg.mediabox.width), float(pg.mediabox.height)
        def draw(c, W, H, i=i):
            c.setFont("Helvetica", 10)
            c.drawCentredString(W / 2, 24, str(i))
        pg.merge_page(overlay(W, H, draw))
        w.add_page(pg)
    dst = os.path.join(wd, base_of(paths[0]) + "_numbered.pdf")
    w.write(dst)
    return [(dst, os.path.basename(dst))]

def t_protect(paths, opts, wd):
    pw = opts.get("password")
    if not pw:
        raise ToolError("enter a password")
    r = open_pdf(paths[0])
    w = PdfWriter()
    for pg in r.pages:
        w.add_page(pg)
    w.encrypt(pw, algorithm="AES-256")
    dst = os.path.join(wd, base_of(paths[0]) + "_protected.pdf")
    w.write(dst)
    return [(dst, os.path.basename(dst))]

def t_unlock(paths, opts, wd):
    r = PdfReader(paths[0])
    if r.is_encrypted and int(r.decrypt(opts.get("password") or "")) == 0:
        raise ToolError("wrong password")
    w = PdfWriter()
    for pg in r.pages:
        w.add_page(pg)
    dst = os.path.join(wd, base_of(paths[0]) + "_unlocked.pdf")
    w.write(dst)
    return [(dst, os.path.basename(dst))]

def t_repair(paths, opts, wd):
    try:
        doc = fitz.open(paths[0])
    except Exception:
        raise ToolError("file too damaged to open")
    if doc.is_encrypted and int(doc.authenticate("")) == 0:
        raise ToolError("password-protected PDF")
    dst = os.path.join(wd, base_of(paths[0]) + "_repaired.pdf")
    doc.save(dst, garbage=4)
    doc.close()
    return [(dst, os.path.basename(dst))]

def t_pdf_pptx(paths, opts, wd):
    if not HAS_PPTX:
        raise ToolError("missing dependency - run: pip install python-pptx")
    doc = fitz.open(paths[0])
    if doc.is_encrypted and int(doc.authenticate("")) == 0:
        raise ToolError("password-protected PDF")
    prs = Presentation()
    SW, SH = 12192000, 6858000
    prs.slide_width, prs.slide_height = SW, SH
    blank = prs.slide_layouts[6]
    DPI = 144
    for pg in doc:
        pix = pg.get_pixmap(dpi=DPI, colorspace=fitz.csRGB, alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        tmp = os.path.join(wd, uuid.uuid4().hex + ".jpg")
        img.save(tmp, "JPEG", quality=88)
        slide = prs.slides.add_slide(blank)
        iw = pix.width / DPI * 914400
        ih = pix.height / DPI * 914400
        sc = min(SW / iw, SH / ih)
        w, h = int(iw * sc), int(ih * sc)
        slide.shapes.add_picture(tmp, (SW - w) // 2, (SH - h) // 2, width=w, height=h)
    doc.close()
    dst = os.path.join(wd, base_of(paths[0]) + ".pptx")
    prs.save(dst)
    return [(dst, os.path.basename(dst))]

# ---------------- qr ----------------

def t_qr(paths, opts, wd):
    if not HAS_QR:
        raise ToolError("missing dependency - run: pip install qrcode")
    data = (opts.get("data") or "").strip()
    if not data:
        raise ToolError("enter text or a URL")
    ecc = {"L": qrcode.constants.ERROR_CORRECT_L, "M": qrcode.constants.ERROR_CORRECT_M,
           "Q": qrcode.constants.ERROR_CORRECT_Q, "H": qrcode.constants.ERROR_CORRECT_H
           }.get(opts.get("ecc", "M"), qrcode.constants.ERROR_CORRECT_M)
    qr = qrcode.QRCode(error_correction=ecc, box_size=12, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    if opts.get("fmt") == "svg":
        from qrcode.image.svg import SvgPathImage
        img = qr.make_image(image_factory=SvgPathImage)
        dst = os.path.join(wd, "qr.svg")
    else:
        img = qr.make_image(fill_color="black", back_color="white")
        dst = os.path.join(wd, "qr.png")
    img.save(dst)
    return [(dst, os.path.basename(dst))]

# ---------------- video ----------------

def t_video_mp3(paths, opts, wd):
    dst = os.path.join(wd, base_of(paths[0]) + ".mp3")
    ffmpeg_run(["-vn", "-acodec", "libmp3lame", "-q:a", "2"], paths[0], dst)
    return [(dst, os.path.basename(dst))]

def t_video_wav(paths, opts, wd):
    dst = os.path.join(wd, base_of(paths[0]) + ".wav")
    ffmpeg_run(["-vn", "-acodec", "pcm_s16le"], paths[0], dst)
    return [(dst, os.path.basename(dst))]

def t_video_compress(paths, opts, wd):
    dst = os.path.join(wd, base_of(paths[0]) + "_small.mp4")
    ffmpeg_run(["-vf", "scale=-2:720", "-c:v", "libx264", "-preset", "veryfast",
                "-crf", "28", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart"],
               paths[0], dst)
    return [(dst, os.path.basename(dst))]

# ---------------- exif / metadata strip ----------------

def t_exif_strip(paths, opts, wd):
    outs = []
    for p in paths:
        orig = Image.open(p)
        ext = os.path.splitext(p)[1].lower()
        mode = orig.mode
        if mode == "P":
            orig = orig.convert("RGBA")
            mode = "RGBA"
        # Rebuild from raw pixel data — drops ALL embedded metadata (EXIF, GPS, ICC, XMP, etc.)
        clean = Image.new(mode, orig.size)
        clean.putdata(list(orig.getdata()))
        fmt_map = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG",
                   ".webp": "WEBP", ".bmp": "BMP", ".tiff": "TIFF"}
        fmt = fmt_map.get(ext, "PNG")
        if fmt == "JPEG":
            clean = clean.convert("RGB")
        dst = os.path.join(wd, base_of(p) + "_clean" + ext)
        if fmt in ("JPEG", "WEBP"):
            clean.save(dst, fmt, quality=95)
        else:
            clean.save(dst, fmt)
        outs.append((dst, os.path.basename(dst)))
    return outs

# ---------------- text to pdf ----------------

def t_text_pdf(paths, opts, wd):
    pg = {"a4": A4, "letter": LETTER}.get(opts.get("size", "a4"), A4)
    fontsize = clamp(to_int(opts.get("fontsize") or 11, "font size"), 6, 72)
    pw, ph = pg
    margin = 72.0
    line_h = fontsize * 1.45
    max_w = max(10, int((pw - 2 * margin) / (fontsize * 0.601)))
    outs = []
    for p in paths:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            raw = f.read()
        lines = raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        dst = os.path.join(wd, base_of(p) + ".pdf")
        c = rl_canvas.Canvas(dst, pagesize=pg)
        c.setFont("Courier", fontsize)
        y = ph - margin
        for line in lines:
            while len(line) > max_w:
                c.drawString(margin, y, line[:max_w])
                line = line[max_w:]
                y -= line_h
                if y < margin:
                    c.showPage(); c.setFont("Courier", fontsize); y = ph - margin
            c.drawString(margin, y, line)
            y -= line_h
            if y < margin:
                c.showPage(); c.setFont("Courier", fontsize); y = ph - margin
        c.save()
        outs.append((dst, os.path.basename(dst)))
    return outs

# ---------------- ocr ----------------

def t_ocr(paths, opts, wd):
    if not HAS_OCR:
        raise ToolError(
            "Tesseract OCR not installed.\n"
            "1. Install Tesseract: https://github.com/tesseract-ocr/tesseract/wiki\n"
            "2. pip install pytesseract"
        )
    lang = (opts.get("lang") or "eng").strip()
    all_text = []
    for p in paths:
        ext = os.path.splitext(p)[1].lower()
        if ext == ".pdf":
            doc = fitz.open(p)
            if doc.is_encrypted and int(doc.authenticate("")) == 0:
                raise ToolError("password-protected PDF")
            for i, pg in enumerate(doc):
                pix = pg.get_pixmap(dpi=200, colorspace=fitz.csRGB, alpha=False)
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                txt = pytesseract.image_to_string(img, lang=lang)
                all_text.append(f"--- Page {i + 1} ---\n{txt}" if len(doc) > 1 else txt)
            doc.close()
        else:
            txt = pytesseract.image_to_string(Image.open(p), lang=lang)
            all_text.append(txt)
    combined = "\n\n".join(t.strip() for t in all_text if t.strip())
    if not combined:
        raise ToolError("no text detected — check language code or image quality")
    dst = os.path.join(wd, base_of(paths[0]) + "_ocr.txt")
    with open(dst, "w", encoding="utf-8") as f:
        f.write(combined)
    return [(dst, os.path.basename(dst))]

# ---------------- audio converter ----------------

def t_audio_convert(paths, opts, wd):
    to = opts.get("to", "mp3")
    codec_args = {
        "mp3":  ["-acodec", "libmp3lame", "-q:a", "2"],
        "wav":  ["-acodec", "pcm_s16le"],
        "flac": ["-acodec", "flac"],
        "aac":  ["-acodec", "aac", "-b:a", "192k"],
        "ogg":  ["-acodec", "libvorbis", "-q:a", "6"],
        "m4a":  ["-acodec", "aac", "-b:a", "192k", "-movflags", "+faststart"],
        "opus": ["-acodec", "libopus", "-b:a", "128k"],
    }
    if to not in codec_args:
        raise ToolError(f"unsupported format: {to}")
    outs = []
    for p in paths:
        dst = os.path.join(wd, base_of(p) + "." + to)
        ffmpeg_run(["-vn"] + codec_args[to], p, dst)
        outs.append((dst, os.path.basename(dst)))
    return outs

TOOLS = {
    "jpg-to-png": t_img_to, "png-to-jpg": t_img_to, "webp-to-jpg": t_img_to,
    "jpg-to-webp": t_img_to, "png-to-webp": t_img_to, "img-convert": t_img_to,
    "img-compress": t_img_compress, "compress-jpg": t_compress_jpg,
    "compress-png": t_compress_png, "img-resize": t_img_resize,
    "img-rotate": t_img_rotate, "heic-to-jpg": t_heic,
    "jpg-to-pdf": t_img_pdf, "png-to-pdf": t_img_pdf,
    "merge-pdf": t_merge, "split-pdf": t_split, "rotate-pdf": t_rotate,
    "extract-pages": t_extract, "page-counter": t_count, "compress-pdf": t_compress,
    "watermark-pdf": t_watermark, "pdf-to-jpg": t_pdf_to_jpg,
    "pdf-to-word": t_pdf_to_docx, "pdf-to-docs": t_pdf_to_docx,
    "pdf-to-pptx": t_pdf_pptx, "word-to-pdf": t_office_pdf,
    "excel-to-pdf": t_office_pdf, "ppt-to-pdf": t_office_pdf,
    "protect-pdf": t_protect, "unlock-pdf": t_unlock,
    "page-numbers": t_page_numbers, "repair-pdf": t_repair,
    "qr-code": t_qr,
    "video-to-mp3": t_video_mp3, "video-to-wav": t_video_wav,
    "compress-video": t_video_compress,
    "exif-strip": t_exif_strip,
    "text-to-pdf": t_text_pdf,
    "ocr": t_ocr,
    "audio-convert": t_audio_convert,
}
MULTI = {"merge-pdf", "jpg-to-pdf", "png-to-pdf", "page-counter", "word-to-pdf",
         "excel-to-pdf", "ppt-to-pdf", "jpg-to-png", "png-to-jpg", "webp-to-jpg",
         "jpg-to-webp", "png-to-webp", "img-convert", "img-compress", "img-resize",
         "img-rotate", "compress-jpg", "compress-png", "heic-to-jpg",
         "exif-strip", "audio-convert", "text-to-pdf"}
NOFILE = {"qr-code"}

# ---------------- routes ----------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/process", methods=["POST"])
def process():
    tool = request.form.get("tool", "")
    files = [f for f in request.files.getlist("files") if f and f.filename]
    if tool not in TOOLS:
        return jsonify(error="unknown tool"), 400
    if not files and tool not in NOFILE:
        return jsonify(error="no file selected"), 400
    if tool not in MULTI and len(files) > 1:
        return jsonify(error="this tool takes a single file"), 400
    opts = {k: v for k, v in request.form.items() if k != "tool"}

    job = os.path.join(TEMP, uuid.uuid4().hex)
    os.makedirs(job, exist_ok=True)
    try:
        paths = []
        for f in files:
            ext = os.path.splitext(f.filename)[1].lower()
            p = os.path.join(job, uuid.uuid4().hex[:6] + "_" + safe_name(f.filename) + ext)
            f.save(p)
            paths.append(p)
        res = TOOLS[tool](paths, opts, job)
    except ToolError as e:
        shutil.rmtree(job, ignore_errors=True)
        return jsonify(error=str(e)), 400
    except Exception as e:
        shutil.rmtree(job, ignore_errors=True)
        return jsonify(error=str(e)[:300] or "conversion failed"), 500

    if isinstance(res, dict):
        shutil.rmtree(job, ignore_errors=True)
        return jsonify(res)

    if isinstance(res, tuple):
        res = [res]
    if len(res) == 1:
        out_path, out_name = res[0]
    else:
        out_path = os.path.join(job, "result.zip")
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
            for p, n in res:
                z.write(p, n)
        out_name = "result.zip"

    def stream():
        try:
            with open(out_path, "rb") as f:
                while chunk := f.read(512 * 1024):
                    yield chunk
        finally:
            shutil.rmtree(job, ignore_errors=True)

    return Response(stream(), mimetype="application/octet-stream",
                    headers={"Content-Disposition": f'attachment; filename="{out_name}"',
                             "Content-Length": str(os.path.getsize(out_path))})

@app.errorhandler(413)
def too_big(e):
    return jsonify(error="file too large (2 GB max)"), 413

@app.errorhandler(Exception)
def boom(e):
    if isinstance(e, HTTPException):
        return jsonify(error=e.description), e.code
    return jsonify(error=str(e)[:300]), 500

def cleanup_old():
    now = time.time()
    for d in os.listdir(TEMP):
        p = os.path.join(TEMP, d)
        if os.path.isdir(p) and now - os.path.getmtime(p) > 2 * 3600:
            shutil.rmtree(p, ignore_errors=True)

if __name__ == "__main__":
    import atexit
    atexit.register(lambda: shutil.rmtree(TEMP, ignore_errors=True))
    cleanup_old()
    port = 5001
    print("ffmpeg:      ", "ok" if FFMPEG else "MISSING - pip install imageio-ffmpeg")
    print("libreoffice: ", "ok" if SOFFICE else "not found (word/excel/ppt to pdf needs it)")
    print("heic:        ", "ok" if HAS_HEIC else "MISSING - pip install pillow-heif")
    print("pptx:        ", "ok" if HAS_PPTX else "MISSING - pip install python-pptx")
    print("qrcode:      ", "ok" if HAS_QR else "MISSING - pip install qrcode")
    print("ocr:         ", "ok" if HAS_OCR else "MISSING - pip install pytesseract  (+ Tesseract binary from tesseract-ocr.github.io)")
    if IS_TERMUX:
        # On Android open via termux-open-url (needs Termux:API from F-Droid)
        threading.Timer(2.0, lambda: subprocess.run(
            ["termux-open-url", f"http://127.0.0.1:{port}"],
            stderr=subprocess.DEVNULL
        )).start()
    else:
        threading.Timer(1.5, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
    print(f"running at http://127.0.0.1:{port}  (Ctrl+C to stop)")
    app.run(host="127.0.0.1", port=port, threaded=True, debug=False)
