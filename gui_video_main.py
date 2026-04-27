"""
gui_video_main.py
Main window GUI Video Enkripsi MO-SiPINE (Video-Only).
Hanya berisi: Enkripsi Video, Dekripsi Video, dan Uji Kualitas Citra (3 frame sampel).
"""
import os
import threading
import tkinter as tk
from tkinter import messagebox
import PIL.Image
import PIL.ImageTk

os.makedirs("Tempat_gambar", exist_ok=True)

# ── Session State Global (dibagikan antar window) ─────────────────────────────
# Disimpan di dict agar mutable di seluruh modul
SESSION = {
    "video_asli": None,       # Path video input asli (.mp4/avi/dll)
    "video_bin":  None,       # Path file .bin hasil enkripsi
    "kunci":      {},         # dict {x1, x2, p, beta}
    "mode":       "mosipine", # mode enkripsi terakhir
    "frame_awal": None,       # Path PNG frame sampel awal
    "frame_tengah": None,     # Path PNG frame sampel tengah
    "frame_akhir": None,      # Path PNG frame sampel akhir
}

# ── Import fungsi dari gui_video ──────────────────────────────────────────────
from gui_video import pencet6, pencet7, pencet_uji_video

# ── Helpers ───────────────────────────────────────────────────────────────────
THUMB_SIZE = (120, 80)
BG        = "#eef1f5"
BG_BTN    = "#dce4ed"
BG_BTN_HV = "#bfcfdf"
FG_TITLE  = "#2c3e5c"
FONT_TITLE = ("Segoe UI", 22, "bold")
FONT_SUB   = ("Segoe UI", 12, "bold")
FONT_BTN   = ("Segoe UI", 10)


def _make_btn(parent, text, command, width=18, **kw):
    btn = tk.Button(
        parent, text=text, command=command,
        font=FONT_BTN, bg=BG_BTN, activebackground=BG_BTN_HV,
        bd=1, relief="ridge", padx=10, pady=8, width=width, cursor="hand2", **kw
    )
    btn.bind("<Enter>", lambda e: btn.config(bg=BG_BTN_HV))
    btn.bind("<Leave>", lambda e: btn.config(bg=BG_BTN))
    return btn


def _load_thumb(path, label_widget):
    """Muat thumbnail dari path ke Label, aman jika file belum ada."""
    try:
        if path and os.path.exists(path):
            img = PIL.Image.open(path).resize(THUMB_SIZE, PIL.Image.LANCZOS)
            photo = PIL.ImageTk.PhotoImage(img)
            label_widget.config(image=photo, text="")
            label_widget._photo = photo  # cegah GC
    except Exception:
        pass


# ── Main Window ───────────────────────────────────────────────────────────────
def build_main():
    root = tk.Tk()
    root.title("MO-SiPINE — Video Encryptor")
    root.geometry("500x820")
    root.resizable(False, False)
    root.configure(bg=BG)

    # ── Judul ─────────────────────────────────────────────────────────────
    frm_title = tk.Frame(root, bg=BG)
    frm_title.pack(pady=(30, 10))
    tk.Label(frm_title, text="KRIPTOGRAFI\nBERBASIS\nMo-SiPINE",
             font=FONT_TITLE, fg=FG_TITLE, bg=BG, justify="center").pack()

    tk.Frame(root, bg="#b0bec5", height=1).pack(fill="x", padx=40, pady=8)

    # ── Status Bar (Fase 4.1) ─────────────────────────────────────────────
    status_var = tk.StringVar(value="Belum ada video yang dipilih.")
    frm_status = tk.Frame(root, bg="#d6e4f0", bd=1, relief="flat")
    frm_status.pack(fill="x", padx=20, pady=(0, 6))
    tk.Label(frm_status, textvariable=status_var,
             font=("Segoe UI", 8), bg="#d6e4f0", fg="#2c3e5c",
             anchor="w", wraplength=440).pack(fill="x", padx=8, pady=4)

    def refresh_status():
        v = SESSION.get("video_asli")
        b = SESSION.get("video_bin")
        parts = []
        if v:
            parts.append(f"Video: {os.path.basename(v)}")
        if b:
            parts.append(f"Bin: {os.path.basename(b)}")
        if parts:
            status_var.set("  |  ".join(parts))
        else:
            status_var.set("Belum ada video yang dipilih.")
        refresh_thumbs()

    # ── Seksi Video & AI ──────────────────────────────────────────────────
    tk.Label(root, text="Video & AI", font=FONT_SUB, bg=BG, fg=FG_TITLE).pack(pady=(6, 2))

    frm_vid = tk.Frame(root, bg=BG)
    frm_vid.pack(pady=4)

    def open_enkripsi():
        pencet6(session=SESSION, on_done=refresh_status)

    def open_dekripsi():
        pencet7(session=SESSION, on_done=refresh_status)

    _make_btn(frm_vid, "Enkripsi Video", open_enkripsi, width=15).grid(row=0, column=0, padx=12)
    _make_btn(frm_vid, "Dekripsi Video", open_dekripsi, width=15).grid(row=0, column=1, padx=12)

    tk.Frame(root, bg="#b0bec5", height=1).pack(fill="x", padx=40, pady=10)

    # ── Seksi Uji Kualitas ────────────────────────────────────────────────
    tk.Label(root, text="Uji Kualitas", font=FONT_SUB, bg=BG, fg=FG_TITLE).pack(pady=(2, 4))

    # Thumbnail Preview 3 Frame (Fase 4.4)
    frm_thumb = tk.Frame(root, bg=BG)
    frm_thumb.pack(pady=4)

    thumb_labels = []
    thumb_captions = ["Citra 1\n(Awal ~10%)", "Citra 2\n(Tengah ~50%)", "Citra 3\n(Akhir ~90%)"]
    for col, cap in enumerate(thumb_captions):
        col_frm = tk.Frame(frm_thumb, bg=BG)
        col_frm.grid(row=0, column=col, padx=10)
        ph = tk.Label(col_frm, bg="#c8d6e0", width=THUMB_SIZE[0], height=THUMB_SIZE[1],
                      text="—", font=("Segoe UI", 8), fg="#666")
        ph.pack()
        tk.Label(col_frm, text=cap, font=("Segoe UI", 8), bg=BG, fg="#5a6a7a",
                 justify="center").pack()
        thumb_labels.append(ph)

    def refresh_thumbs():
        keys = ["frame_awal", "frame_tengah", "frame_akhir"]
        for lbl, key in zip(thumb_labels, keys):
            _load_thumb(SESSION.get(key), lbl)

    def _do_extract_thumbs():
        vid = SESSION.get("video_asli")
        if not vid:
            messagebox.showwarning("Peringatan",
                "Pilih & enkripsi video terlebih dahulu agar sampel frame tersedia.",
                parent=root)
            return
        from video_core import extract_sample_frames
        try:
            p1, p2, p3 = extract_sample_frames(vid, "Tempat_gambar")
            SESSION["frame_awal"]   = p1
            SESSION["frame_tengah"] = p2
            SESSION["frame_akhir"]  = p3
            refresh_thumbs()
        except Exception as e:
            messagebox.showerror("Error", f"Gagal ekstrak frame:\n{e}", parent=root)

    tk.Button(frm_thumb.master, text="🔄 Perbarui Thumbnail Frame Sampel",
              font=("Segoe UI", 8), bg="#c8d6e0", activebackground=BG_BTN_HV,
              bd=1, relief="flat", cursor="hand2",
              command=lambda: threading.Thread(target=_do_extract_thumbs, daemon=True).start()
              ).pack(pady=(2, 6))

    # Tombol Uji Kualitas
    frm_uji = tk.Frame(root, bg=BG)
    frm_uji.pack(pady=6)

    def open_uji(frame_key, frame_ratio, label):
        pencet_uji_video(
            session=SESSION,
            frame_key=frame_key,
            frame_ratio=frame_ratio,
            label=label,
            parent=root
        )

    frm_uji_row1 = tk.Frame(frm_uji, bg=BG)
    frm_uji_row1.pack()
    _make_btn(frm_uji_row1, "Uji Kualitas\nCitra 1",
              lambda: open_uji("frame_awal", 0.10, "Awal (~10%)"), width=14
              ).grid(row=0, column=0, padx=10, pady=4)
    _make_btn(frm_uji_row1, "Uji Kualitas\nCitra 2",
              lambda: open_uji("frame_tengah", 0.50, "Tengah (~50%)"), width=14
              ).grid(row=0, column=1, padx=10, pady=4)

    frm_uji_row2 = tk.Frame(frm_uji, bg=BG)
    frm_uji_row2.pack()
    _make_btn(frm_uji_row2, "Uji Kualitas\nCitra 3",
              lambda: open_uji("frame_akhir", 0.90, "Akhir (~90%)"), width=14
              ).pack(pady=4)

    tk.Frame(root, bg="#b0bec5", height=1).pack(fill="x", padx=40, pady=12)

    # ── Keluar ────────────────────────────────────────────────────────────
    _make_btn(root, "Keluar", root.destroy, width=14).pack(pady=4)

    root.mainloop()


if __name__ == "__main__":
    build_main()
