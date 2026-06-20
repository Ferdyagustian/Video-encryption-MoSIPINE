"""
gui_video_main.py
Main window GUI Video Enkripsi SIP Map (Video-Only).
"""
import os
import tkinter as tk

os.makedirs("Tempat_gambar", exist_ok=True)

# ── Session State Global ───────────────────────────────────────────────────────
SESSION = {
    "video_asli": None,
    "video_bin":  None,
    "kunci":      {},
    "mode":       "mosipine",
}

from gui_video import (pencet6, pencet7,  # type: ignore[import]
                        uji_histogram_korelasi_video, uji_distribusi_scatter_video,
                        uji_statistik_video, uji_kualitas_audio)

# ── Konstanta Gaya ─────────────────────────────────────────────────────────────
BG       = "#eaeff4"
BG_BTN   = "#d8e2ec"
BG_HOVER = "#b8ccdc"
FG_TITLE = "#253555"
FG_SUB   = "#2c3e5c"


def _make_btn(parent, text, cmd, width=15, pady=8):
    b = tk.Button(parent, text=text, command=cmd,
                  font=("Segoe UI", 10), bg=BG_BTN,
                  activebackground=BG_HOVER,
                  bd=1, relief="ridge",
                  padx=10, pady=pady,
                  width=width, cursor="hand2")
    b.bind("<Enter>", lambda e: b.config(bg=BG_HOVER))
    b.bind("<Leave>", lambda e: b.config(bg=BG_BTN))
    return b


def _separator(parent):
    tk.Frame(parent, bg="#aabbcc", height=1).pack(fill="x", padx=40, pady=8)


def build_main():
    root = tk.Tk()
    root.title("SIP Map — Video Encryptor")
    root.geometry("480x700")
    root.resizable(False, False)
    root.configure(bg=BG)

    # ══ JUDUL ══════════════════════════════════════════════════════════════════
    tk.Label(root,
             text="KRIPTOGRAFI\nBERBASIS\nSIP Map",
             font=("Segoe UI", 22, "bold"),
             fg=FG_TITLE, bg=BG, justify="center").pack(pady=(30, 10))

    _separator(root)

    # ══ STATUS BAR ════════════════════════════════════════════════════════════
    status_var = tk.StringVar(value="Belum ada video yang dipilih.")
    frm_status = tk.Frame(root, bg="#d0dcea", bd=0)
    frm_status.pack(fill="x", padx=22, pady=(0, 6))
    tk.Label(frm_status, textvariable=status_var,
             font=("Segoe UI", 8), bg="#d0dcea", fg=FG_SUB,
             anchor="w", wraplength=430).pack(fill="x", padx=8, pady=4)

    def refresh_status():
        v = SESSION.get("video_asli")
        b = SESSION.get("video_bin")
        parts = []
        if v: parts.append(f"Video: {os.path.basename(v)}")
        if b: parts.append(f"Bin: {os.path.basename(b)}")
        status_var.set("  |  ".join(parts) if parts else "Belum ada video yang dipilih.")

    # ══ SEKSI VIDEO & AI ═══════════════════════════════════════════════════════
    tk.Label(root, text="Video & AI",
             font=("Segoe UI", 12, "bold"),
             fg=FG_SUB, bg=BG).pack(pady=(6, 4))

    frm_vid = tk.Frame(root, bg=BG)
    frm_vid.pack(pady=4)

    _make_btn(frm_vid, "Enkripsi Video",
              lambda: pencet6(session=SESSION, on_done=refresh_status),
              width=14).grid(row=0, column=0, padx=12)
    _make_btn(frm_vid, "Dekripsi Video",
              lambda: pencet7(session=SESSION, on_done=refresh_status),
              width=14).grid(row=0, column=1, padx=12)

    _separator(root)

    # ══ SEKSI UJI KUALITAS ═════════════════════════════════════════════════════
    tk.Label(root, text="Uji Kualitas",
             font=("Segoe UI", 12, "bold"),
             fg=FG_SUB, bg=BG).pack(pady=(2, 8))

    frm_uji = tk.Frame(root, bg=BG)
    frm_uji.pack(pady=2)

    _make_btn(frm_uji,
              "Uji Kualitas\n(Histogram & Korelasi)",
              lambda: uji_histogram_korelasi_video(SESSION, root),
              width=25, pady=10).grid(row=0, column=0, pady=4)

    _make_btn(frm_uji,
              "Uji Distribusi\nKorelasi",
              lambda: uji_distribusi_scatter_video(SESSION, root),
              width=25, pady=10).grid(row=1, column=0, pady=4)

    _make_btn(frm_uji,
              "Uji Statistik\n(Uniform, Entropi, dll)",
              lambda: uji_statistik_video(SESSION, root),
              width=25, pady=10).grid(row=2, column=0, pady=4)

    _make_btn(frm_uji,
              "Uji Kualitas Audio\n(SNR, PSNR, Waveform)",
              lambda: uji_kualitas_audio(session=SESSION, parent=root),
              width=25, pady=10).grid(row=3, column=0, pady=4)

    _separator(root)

    # ══ KELUAR ═════════════════════════════════════════════════════════════════
    _make_btn(root, "Keluar", root.destroy, width=14, pady=8).pack(pady=8)

    root.mainloop()


if __name__ == "__main__":
    build_main()
