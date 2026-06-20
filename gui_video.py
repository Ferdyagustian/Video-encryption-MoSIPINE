# pylint: disable=no-member
import os
import math
import threading
import collections
from tkinter import *
from tkinter import filedialog, messagebox, ttk, scrolledtext
import PIL.Image
import PIL.ImageTk
import cv2
import numpy as np
import struct
import time
import skimage.measure
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import pearsonr
from video_core import encrypt_video_audio_to_VEN2, decrypt_VEN2_to_video_audio, extract_sample_frames, extract_single_frame_from_bin
from ai_optimizer import predict_best_keys

PREVIEW_SIZE = (280, 180)  # Ukuran thumbnail preview

def _create_placeholder():
    """Buat gambar dummy dengan ukuran piksel agar Label tidak meledak ukurannya."""
    img = PIL.Image.new('RGB', PREVIEW_SIZE, color='#d0d0d0')
    return PIL.ImageTk.PhotoImage(img)

class VideoPlayer:
    """Kelas untuk mengelola pemutaran Video (.mp4 dkk) atau VEN2 (.bin) di Tkinter."""
    def __init__(self, parent_frame, preview_size=PREVIEW_SIZE):
        self.preview_size = preview_size
        
        # Container Image
        self.f_img = Frame(parent_frame, width=self.preview_size[0], height=self.preview_size[1])
        self.f_img.pack()
        self.f_img.pack_propagate(False)
        
        self.dummy_photo = _create_placeholder()
        self.canvas = Label(self.f_img, image=self.dummy_photo)
        self.canvas.place(x=0, y=0)
        self.lbl_text = Label(self.f_img, text="(belum dipilih)", bg="#d0d0d0", fg="#555")
        self.lbl_text.place(relx=0.5, rely=0.5, anchor=CENTER)

        # Container Button Controls
        self.btn_frame = Frame(parent_frame)
        self.btn_frame.pack(pady=4)
        
        self.btn_play = Button(self.btn_frame, text="▶ Play", command=self.toggle_play, state=DISABLED, font=("Segoe UI", 8), cursor="hand2")
        self.btn_play.pack(side=LEFT, padx=2)
        self.btn_replay = Button(self.btn_frame, text="🔄 Ulang", command=self.replay, state=DISABLED, font=("Segoe UI", 8), cursor="hand2")
        self.btn_replay.pack(side=LEFT, padx=2)
        
        # State
        self.source_path = None
        self.cap = None
        self.is_bin = False
        self.bin_file = None
        self.bin_w = 0
        self.bin_h = 0
        self.bin_fps = 30
        self.data_offset = 36   # 36 = format VEN2 baru
        self.is_playing = False
        self._after_id = None

    def _show_frame(self, frame):
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = PIL.Image.fromarray(frame_rgb)
        pil_img = pil_img.resize(self.preview_size, PIL.Image.LANCZOS)
        photo = PIL.ImageTk.PhotoImage(pil_img)
        self.canvas.config(image=photo)
        self.canvas.image = photo 
        self.lbl_text.config(text="")

    def load_source(self, path):
        self.stop()
        self.source_path = path
        if not path or not os.path.exists(path):
            return

        # ── Deteksi format .bin ──────────────────────────────────────────────
        _use_custom_bin = False
        _detected_offset = 36
        if path.lower().endswith(".bin"):
            try:
                with open(path, 'rb') as _f:
                    _peek = _f.read(36)

                # Prioritas 1: Header VEN2 baru (36 byte)
                if len(_peek) >= 36 and _peek[:4] == b'VEN2':
                    _, _w, _h, _tf, _fps_v = struct.unpack('<4sIIIf', _peek[:20])
                    if 8 <= _w <= 7680 and 8 <= _h <= 4320 and 0 < _fps_v <= 120 and _tf > 0:
                        _use_custom_bin = True
                        _detected_offset = 36
            except Exception:
                pass

        if _use_custom_bin:
            self.is_bin = True
            self.data_offset = _detected_offset
            try:
                with open(self.source_path, 'rb') as f:
                    hdr_full = f.read(_detected_offset)
                    w, h, fps = 0, 0, 30.0  # default sebelum parsing header
                    if _detected_offset == 36 and hdr_full[:4] == b'VEN2':
                        # Format VEN2 baru
                        _, w, h, _, fps = struct.unpack('<4sIIIf', hdr_full[:20])
                    self.bin_w, self.bin_h, self.bin_fps = w, h, fps
                    raw = f.read(w * h * 3)
                    if len(raw) == w * h * 3:
                        frame = np.frombuffer(raw, dtype=np.uint8).reshape((h, w, 3))
                        self._show_frame(frame)
            except Exception as e:
                print("Error loading bin frame:", e)
        else:
            # Gunakan OpenCV untuk .mp4, .avi, dll.
            self.is_bin = False
            self.cap = cv2.VideoCapture(self.source_path)
            ret, frame = self.cap.read()
            if ret:
                self._show_frame(frame)

        self.btn_play.config(state=NORMAL)
        self.btn_replay.config(state=NORMAL)
        self.btn_play.config(text="▶ Play")
        self.is_playing = False

    def toggle_play(self):
        if not self.source_path: return
        
        if self.is_playing:
            self.is_playing = False
            self.btn_play.config(text="▶ Play")
            if self._after_id:
                self.canvas.after_cancel(self._after_id)
                self._after_id = None
        else:
            self.is_playing = True
            self.btn_play.config(text="⏸ Pause")
            if self.is_bin:
                if self.bin_file is None or self.bin_file.closed:
                    self.bin_file = open(self.source_path, 'rb')
                    self.bin_file.read(self.data_offset)  # Skip header VEN2 (36 byte)
            else:
                if self.cap is None or not self.cap.isOpened():
                    self.cap = cv2.VideoCapture(self.source_path)
            self._play_loop()

    def replay(self):
        if not self.source_path: return
        
        if self.is_bin:
            if self.bin_file and not self.bin_file.closed:
                self.bin_file.seek(self.data_offset)  # Seek ke setelah header
            else:
                self.bin_file = open(self.source_path, 'rb')
                self.bin_file.seek(self.data_offset)
        else:
            if self.cap:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        
        if not self.is_playing:
            self.toggle_play()

    def stop(self):
        self.is_playing = False
        if self._after_id:
            self.canvas.after_cancel(self._after_id)
            self._after_id = None
        if self.cap:
            self.cap.release()
            self.cap = None
        if self.bin_file:
            self.bin_file.close()
            self.bin_file = None
            
        self.btn_play.config(text="▶ Play", state=DISABLED)
        self.btn_replay.config(state=DISABLED)

    def _play_loop(self):
        if not self.is_playing: return
        
        frame = None
        delay = 33
        
        if self.is_bin:
            if self.bin_file and not self.bin_file.closed:
                bytes_to_read = self.bin_w * self.bin_h * 3
                raw = self.bin_file.read(bytes_to_read)
                if raw and len(raw) == bytes_to_read:
                    frame = np.frombuffer(raw, dtype=np.uint8).reshape((self.bin_h, self.bin_w, 3))
                    delay = int(1000 / self.bin_fps) if self.bin_fps > 0 else 33
                else:
                    self.is_playing = False
                    self.btn_play.config(text="▶ Play")
                    return
        else:
            if self.cap and self.cap.isOpened():
                ret, f = self.cap.read()
                if ret:
                    frame = f
                    fps = self.cap.get(cv2.CAP_PROP_FPS)
                    if not fps or fps <= 0: fps = 30
                    delay = int(1000 / fps)
                else:
                    self.is_playing = False
                    self.btn_play.config(text="▶ Play")
                    if self.cap:
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    return

        if frame is not None:
            self._show_frame(frame)
            self._after_id = self.canvas.after(delay, self._play_loop)

def pencet6(session=None, on_done=None):
    """Window: Enkripsi Video dengan AI Parameter Predictor."""
    root = Toplevel()
    root.geometry("900x750")
    root.title("Enkripsi Video  |  AI Parameter Predictor")
    root.resizable(False, False)

    Label(root, text="Enkripsi Video dengan AI Parameter Predictor",
          font=("Segoe UI", 16, "bold")).pack(pady=(12, 4))
    Label(root, text="AI akan otomatis mencari kunci terbaik (10 detik)",
          font=("Segoe UI", 10), fg="gray").pack()

    # ── Baris pilih file ────────────────────────────────────────────
    ff = Frame(root)
    ff.pack(pady=10)
    video_path_var = StringVar()
    Label(ff, text="File Video:", font=("Segoe UI", 10)).grid(row=0, column=0, padx=4)
    Entry(ff, textvariable=video_path_var, width=50,
          state='readonly', font=("Segoe UI", 10)).grid(row=0, column=1, padx=4)

    # ── Frame Preview (input) ────────────────────────────────────────
    pf = Frame(root)
    pf.pack(pady=5)
    
    kiri = Frame(pf)
    kiri.grid(row=0, column=0, padx=20)
    Label(kiri, text="Video Input Asli", font=("Segoe UI", 10, "bold")).pack(pady=5)
    player_in = VideoPlayer(kiri)

    kanan = Frame(pf)
    kanan.grid(row=0, column=1, padx=20)
    Label(kanan, text="Video Terenkripsi (Raw Biner)", font=("Segoe UI", 10, "bold")).pack(pady=5)
    player_out = VideoPlayer(kanan)

    def browse_video():
        path = filedialog.askopenfilename(
            title="Pilih File Video",
            filetypes=[("Video Files", "*.mp4 *.mov *.avi *.mkv"), ("All Files", "*.*")])
        if not path: return
        video_path_var.set(path)
        player_in.load_source(path)
        btn_ai.config(state=NORMAL)

    Button(ff, text="Browse…", font=("Segoe UI", 9), command=browse_video).grid(row=0, column=2, padx=4)

    # ── Mode Enkripsi ────────────────────────────────────────────────
    mode_var = StringVar(value="mosipine")
    mf = Frame(root)
    mf.pack(pady=5)
    Label(mf, text="Mode:", font=("Segoe UI", 10, "bold")).pack(side=LEFT, padx=10)
    for txt, val in [("SIP Map","mosipine"), ("Sine Only","sine"), ("PWLCM Only","pwlcm")]:
        Radiobutton(mf, text=txt, variable=mode_var,
                    value=val, font=("Segoe UI", 10)).pack(side=LEFT, padx=10)

    # ── Mode Parameter (AI / Manual) ─────────────────────────────────
    param_mode_var = StringVar(value="ai")
    pmf = Frame(root)
    pmf.pack(pady=5)
    Label(pmf, text="Input Parameter:", font=("Segoe UI", 10, "bold")).pack(side=LEFT, padx=10)
    for txt, val in [("Otomatis (AI Predictor)", "ai"), ("Manual", "manual")]:
        Radiobutton(pmf, text=txt, variable=param_mode_var,
                    value=val, font=("Segoe UI", 10)).pack(side=LEFT, padx=10)

    # ── Parameter Box ────────────────────────────────────────────────
    param_frame = LabelFrame(root, text=" Parameter Kunci ", font=("Segoe UI", 10, "bold"))
    param_frame.pack(fill="x", padx=40, pady=5)
    
    param_vars = {k: StringVar(value="—") for k in ('x1','x2','p','beta','entropy')}
    labels = [("x1", 0, 0), ("x2", 0, 2), ("p", 1, 0), ("β (beta)", 1, 2), ("Entropi Info", 2, 0)]
    widgets_enc = {}
    for lbl, r, c in labels:
        l_w = Label(param_frame, text=f"{lbl}:", font=("Segoe UI", 9))
        l_w.grid(row=r, column=c, padx=10, pady=5, sticky=E)
        key = lbl.replace("β (beta)","beta").replace("Entropi Info","entropy")
        e_w = Entry(param_frame, textvariable=param_vars[key], width=20,
              state='readonly', font=("Segoe UI", 10, "bold"),
              readonlybackground="#f4f7f6")
        e_w.grid(row=r, column=c+1, padx=5, pady=5)
        widgets_enc[key] = (l_w, e_w)

    def toggle_fields_enc(*args):
        for k in ('p', 'beta'):
            widgets_enc[k][0].grid()
            widgets_enc[k][1].grid()
        m = mode_var.get()
        if m == "sine":
            widgets_enc['p'][0].grid_remove()
            widgets_enc['p'][1].grid_remove()
        elif m == "pwlcm":
            widgets_enc['beta'][0].grid_remove()
            widgets_enc['beta'][1].grid_remove()

    mode_var.trace_add("write", toggle_fields_enc)
    toggle_fields_enc()

    # ── Progress & status ────────────────────────────────────────────
    progress = ttk.Progressbar(root, orient=HORIZONTAL, length=600, mode='determinate')
    progress.pack(pady=10)
    status_var = StringVar(value="Status: Menunggu file video…")
    Label(root, textvariable=status_var, font=("Segoe UI", 10), fg="#00529b").pack()

    # ── Tombol bawah ─────────────────────────────────────────────────
    btn_frame = Frame(root)
    btn_frame.pack(pady=5)

    btn_ai = Button(btn_frame, text="🤖 Mulai AI Predict & Enkripsi Video",
                    font=("Segoe UI", 11, "bold"), bg="#4a90d9", fg="white",
                    activebackground="#357abd", padx=15, pady=8,
                    state=DISABLED, cursor="hand2")
    btn_ai.grid(row=0, column=0, padx=10, pady=(0, 10))

    def toggle_param_mode(*args):
        mode_param = param_mode_var.get()
        state_entry = 'readonly' if mode_param == "ai" else 'normal'
        bg_entry = "#f4f7f6" if mode_param == "ai" else "white"
        
        for key in ('x1', 'x2', 'p', 'beta', 'entropy'):
            if key in widgets_enc:
                widgets_enc[key][1].config(state='normal')
                widgets_enc[key][1].config(bg=bg_entry)
                if mode_param == "manual" and key == "entropy":
                    if param_vars['entropy'].get() == "":
                        param_vars['entropy'].set("—")
                    widgets_enc[key][1].config(state='readonly')
                else:
                    widgets_enc[key][1].config(state=state_entry)
                    
        if mode_param == "ai":
            btn_ai.config(text="🤖 Mulai AI Predict & Enkripsi Video")
        else:
            btn_ai.config(text="🔒 Mulai Enkripsi Video (Manual)")

    param_mode_var.trace_add("write", toggle_param_mode)
    toggle_param_mode()

    btn_save_key = Button(btn_frame, text="💾 Simpan Key AI",
                          font=("Segoe UI", 11, "bold"), bg="#5cb85c", fg="white", 
                          activebackground="#4cae4c", padx=15, pady=8,
                          state=DISABLED, cursor="hand2")
    btn_save_key.grid(row=0, column=1, padx=10, pady=(0, 10))

    btn_save_bin = Button(btn_frame, text="⬇️ Unduh File Terenkripsi",
                          font=("Segoe UI", 11, "bold"), bg="#5bc0de", fg="white", 
                          activebackground="#31b0d5", padx=15, pady=8,
                          state=DISABLED, cursor="hand2")
    btn_save_bin.grid(row=1, column=0, padx=10, pady=0)

    btn_export_noise = Button(btn_frame, text="🎬 Export Preview Noise (.mp4)",
                              font=("Segoe UI", 11, "bold"), bg="#f0ad4e", fg="white", 
                              activebackground="#eea236", padx=15, pady=8,
                              state=DISABLED, cursor="hand2")
    btn_export_noise.grid(row=1, column=1, padx=10, pady=0)

    _key_path_holder  = [None]
    _bin_path_holder  = [None]

    def save_key():
        src = _key_path_holder[0]
        if not src or not os.path.exists(src):
            messagebox.showwarning("Peringatan", "Key belum tersedia.")
            return
        dst = filedialog.asksaveasfilename(
            title="Simpan Key AI",
            defaultextension=".txt",
            initialfile="AI_Key_Report.txt",
            filetypes=[("Text File", "*.txt"), ("All Files", "*.*")])
        if dst:
            import shutil
            shutil.copy2(src, dst)
            messagebox.showinfo("Berhasil", f"Key berhasil disimpan ke:\n{dst}")

    btn_save_key.config(command=save_key)

    def save_bin():
        src = _bin_path_holder[0]
        if not src or not os.path.exists(src):
            messagebox.showwarning("Peringatan", "File biner belum tersedia.")
            return
            
        dst = filedialog.asksaveasfilename(
            title="Simpan File Video VEN2 Terenkripsi",
            defaultextension=".bin",
            initialfile="video_rahasia.bin",
            filetypes=[("Binary File", "*.bin"), ("All Files", "*.*")])
        if dst:
            import shutil
            shutil.copy2(src, dst)
            messagebox.showinfo("Berhasil", f"Video sukses disimpan ke:\n{dst}")

    btn_save_bin.config(command=save_bin)

    def export_noise():
        src = _bin_path_holder[0]
        if not src or not os.path.exists(src):
            messagebox.showwarning("Peringatan", "File biner belum tersedia.")
            return
            
        dst = filedialog.asksaveasfilename(
            title="Export Preview Noise",
            defaultextension=".mp4",
            initialfile="preview_noise.mp4",
            filetypes=[("Video File", "*.mp4"), ("All Files", "*.*")])
        if not dst: return

        btn_ai.config(state=DISABLED)
        btn_save_key.config(state=DISABLED)
        btn_save_bin.config(state=DISABLED)
        btn_export_noise.config(state=DISABLED)
        progress['value'] = 0
        status_var.set("Status: [EXPORT] Mengekspor video noise (tanpa dekripsi)...")

        def run_export():
            try:
                from video_core import export_bin_to_noise_video
                start_time = time.time()
                
                def cb(perc):
                    progress['value'] = perc
                    root.update_idletasks()

                export_bin_to_noise_video(src, dst, cb)
                
                durasi = time.time() - start_time
                status_var.set(f"Status: [OK] Selesai Export! ({int(durasi)} dtk)")
                messagebox.showinfo("Berhasil", f"Video preview noise sukses diexport ke:\n{dst}")
            except Exception as e:
                status_var.set(f"Status: [ERROR] Gagal export: {e}")
                messagebox.showerror("Error", str(e))
            finally:
                btn_ai.config(state=NORMAL)
                btn_save_key.config(state=NORMAL)
                btn_save_bin.config(state=NORMAL)
                btn_export_noise.config(state=NORMAL)

        threading.Thread(target=run_export, daemon=True).start()

    btn_export_noise.config(command=export_noise)

    def proses_ai_dan_enkripsi():
        v_path = video_path_var.get()
        if not v_path: return
        mode = mode_var.get()

        player_in.stop()
        player_out.stop()

        btn_ai.config(state=DISABLED)
        btn_save_key.config(state=DISABLED)
        progress['value'] = 0

        def run():
            try:
                p_mode = param_mode_var.get()
                os.makedirs("Tempat_gambar", exist_ok=True)
                key_path = os.path.join("Tempat_gambar", "AI_Key_Report.txt")

                if p_mode == "ai":
                    # FASE 1: AI Predict
                    status_var.set("Status: [AI] Memprediksi kunci terbaik (10 detik)...")
                    root.update()
                    best_keys, best_entropy = predict_best_keys(mode=mode, timeout=10.0)

                    param_vars['x1'].set(f"{best_keys.get('x1', 0):.10f}")
                    param_vars['x2'].set(f"{best_keys.get('x2', 0):.10f}")
                    param_vars['p'].set(f"{best_keys.get('p', 0.25):.10f}")
                    param_vars['beta'].set(f"{best_keys.get('beta', 0):.10f}")
                    param_vars['entropy'].set(f"{best_entropy:.8f}")

                    with open(key_path, "w", encoding="utf-8") as kf:
                        kf.write("\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\n")
                        kf.write("\u2551       AI KEY REPORT \u2014 MO-SiPINE          \u2551\n")
                        kf.write("\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\n\n")
                        kf.write(f"Mode Enkripsi : {mode.upper()}\n")
                        kf.write(f"Entropy Score : {best_entropy:.10f}  (ideal: 8.0)\n\n")
                        kf.write("\u2500\u2500\u2500\u2500 SALIN NILAI INI UNTUK DEKRIPSI \u2500\u2500\u2500\u2500\n")
                        kf.write(f"x1   = {best_keys.get('x1', 0):.10f}\n")
                        kf.write(f"x2   = {best_keys.get('x2', 0):.10f}\n")
                        kf.write(f"p    = {best_keys.get('p', 0.25):.10f}\n")
                        kf.write(f"beta = {best_keys.get('beta', 0):.10f}\n")
                    _key_path_holder[0] = key_path

                    float_params = {k: float(param_vars[k].get()) for k in ('x1','x2','p','beta')}
                else:
                    # FASE 1: MANUAL (Validasi & Hitung Entropi)
                    status_var.set("Status: [MANUAL] Validasi parameter & menghitung entropi...")
                    root.update()
                    try:
                        x1_v = float(param_vars['x1'].get())
                        x2_v = float(param_vars['x2'].get())
                        p_v = float(param_vars['p'].get()) if param_vars['p'].get() and mode != "sine" else 0.25
                        beta_v = float(param_vars['beta'].get()) if param_vars['beta'].get() and mode != "pwlcm" else 0.0
                    except ValueError:
                        root.after(0, lambda: messagebox.showerror("Error", "Semua parameter harus berupa angka (Float) dan tidak boleh kosong!", parent=root))
                        status_var.set("Status: Menunggu file video…")
                        root.after(0, lambda: btn_ai.config(state=NORMAL))
                        return

                    float_params = {'x1': x1_v, 'x2': x2_v, 'p': p_v, 'beta': beta_v}

                    from ai_optimizer import calculate_entropy
                    from sipine import generate_keystream, generate_keystream_sine_only, generate_keystream_pwlcm_only
                    
                    try:
                        if mode == "sine":
                            ks = generate_keystream_sine_only(x1_v, x2_v, beta_v, 1000, 10000)
                        elif mode == "pwlcm":
                            ks = generate_keystream_pwlcm_only(x1_v, x2_v, p_v, beta_v, 1000, 10000)
                        else:
                            ks = generate_keystream(x1_v, x2_v, p_v, beta_v, 1000, 10000)
                        manual_entropy = calculate_entropy(ks)
                        param_vars['entropy'].set(f"{manual_entropy:.8f}")
                    except Exception as e:
                        manual_entropy = 0.0
                        param_vars['entropy'].set("Error")
                        print("Error calculate entropy manual:", e)

                    with open(key_path, "w", encoding="utf-8") as kf:
                        kf.write("\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\n")
                        kf.write("\u2551     MANUAL KEY REPORT \u2014 MO-SiPINE        \u2551\n")
                        kf.write("\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\n\n")
                        kf.write(f"Mode Enkripsi : {mode.upper()}\n")
                        kf.write(f"Entropy Score : {manual_entropy:.10f}  (ideal: 8.0)\n\n")
                        kf.write("\u2500\u2500\u2500\u2500 SALIN NILAI INI UNTUK DEKRIPSI \u2500\u2500\u2500\u2500\n")
                        kf.write(f"x1   = {x1_v:.10f}\n")
                        kf.write(f"x2   = {x2_v:.10f}\n")
                        if mode != "sine":
                            kf.write(f"p    = {p_v:.10f}\n")
                        if mode != "pwlcm":
                            kf.write(f"beta = {beta_v:.10f}\n")
                    _key_path_holder[0] = key_path

                start_time = time.time()

                # FASE 2 & 3: Ekstrak Audio dan Enkripsi menjadi VEN2 Tunggal (.bin)
                from video_core import encrypt_video_audio_to_VEN2
                
                out_bin = os.path.join("Tempat_gambar", "video_terenkripsi.bin")
                status_var.set("Status: [VIDEO+AUDIO] Memproses ekstrak dan enkripsi...")
                root.update_idletasks()

                def progress_cb(perc):
                    progress['value'] = perc
                    elapsed = time.time() - start_time
                    if perc > 0 and elapsed > 0:
                        eta = int((100 - perc) / (perc / elapsed))
                        m2, s2 = divmod(eta, 60)
                        eta_str = f"{m2}m {s2}s" if m2 else f"{s2} dtk"
                        status_var.set(f"Status: Enkripsi berjalan {perc:.1f}% - Sisa: {eta_str}")
                    else:
                        status_var.set(f"Status: Enkripsi berjalan {perc:.1f}%...")
                    root.update_idletasks()

                encrypt_video_audio_to_VEN2(v_path, out_bin, mode, float_params, progress_cb)
                _bin_path_holder[0] = out_bin

                # FASE 5: Preview
                progress['value'] = 100
                player_out.load_source(out_bin)
                player_out.lbl_text.config(text="")

                durasi = time.time() - start_time
                mnt, dtk = divmod(int(durasi), 60)
                dur_str = f"{mnt} menit {dtk} detik" if mnt else f"{dtk} detik"
                
                try:
                    import cv2
                    cap = cv2.VideoCapture(v_path)
                    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    cap.release()
                    sz = os.path.getsize(v_path) / (1024 * 1024)
                    fps_val = total_frames / durasi if durasi > 0 else 0
                    mbps = sz / durasi if durasi > 0 else 0
                    perf_str = f" | FPS: {fps_val:.1f} | {mbps:.2f} MB/s"
                except Exception:
                    perf_str = ""
                    
                status_var.set(f"Status: [OK] Selesai! Waktu: {dur_str}{perf_str}")
                btn_save_key.config(state=NORMAL)
                btn_save_bin.config(state=NORMAL)
                btn_export_noise.config(state=NORMAL)

                if session is not None:
                    session['video_asli'] = v_path
                    session['video_bin']  = out_bin
                    session['mode']       = mode
                    session['kunci']      = float_params
                if on_done:
                    on_done()

                messagebox.showinfo("Berhasil",
                    f"Enkripsi Selesai!\nKinerja: {perf_str.strip(' |')}\nWaktu: {dur_str}\nOutput: video_terenkripsi.bin\n\n"
                    f"File .bin sudah memuat video dan audio (jika ada).\nSimpan Key AI dan file output.")
            except Exception as e:
                status_var.set(f"Status: [ERROR] {e}")
                messagebox.showerror("Error", str(e))
            finally:
                btn_ai.config(state=NORMAL)

        threading.Thread(target=run, daemon=True).start()
    btn_ai.config(command=proses_ai_dan_enkripsi)


def pencet7(session=None, on_done=None):
    """Window: Dekripsi Binary .bin kembali ke Video."""
    root = Toplevel()
    root.geometry("800x670")
    root.title("Dekripsi Video  |  Binary → Video")
    root.resizable(False, False)

    Label(root, text="Dekripsi BIN → Video (.mp4)",
          font=("Segoe UI", 16, "bold")).pack(pady=(12, 4))
    Label(root, text="Muat kunci dari file AI_Key_Report.txt untuk mendekripsi secara akurat",
          font=("Segoe UI", 10), fg="gray").pack()

    # ── Pilih file ───────────────────────────────────────────────────
    ff = Frame(root)
    ff.pack(pady=10)
    bin_path_var = StringVar()
    Label(ff, text="File Enkripsi:", font=("Segoe UI", 10)).grid(row=0, column=0, padx=4)
    Entry(ff, textvariable=bin_path_var, width=50,
          state='readonly', font=("Segoe UI", 10)).grid(row=0, column=1, padx=4)

    # ── Preview ──────────────────────────────────────────────────────
    pf = Frame(root)
    pf.pack(pady=5)
    
    kiri = Frame(pf)
    kiri.grid(row=0, column=0, padx=20)
    Label(kiri, text="Video Terenkripsi (Raw Biner)", font=("Segoe UI", 10, "bold")).pack(pady=5)
    player_enc = VideoPlayer(kiri)

    kanan = Frame(pf)
    kanan.grid(row=0, column=1, padx=20)
    Label(kanan, text="Video Hasil Dekripsi (.mp4)", font=("Segoe UI", 10, "bold")).pack(pady=5)
    player_dec = VideoPlayer(kanan)

    def browse_bin():
        path = filedialog.askopenfilename(
            title="Pilih File Terenkripsi (.bin, .mkv, atau .mp4)",
            filetypes=[
                ("Semua Format Terenkripsi", "*.bin *.mkv *.mp4"),
                ("Binary File", "*.bin"),
                ("MKV File (dengan audio)", "*.mkv"),
                ("MP4 File", "*.mp4"),
                ("All Files", "*.*"),
            ])
        if not path: return
        bin_path_var.set(path)
        player_enc.load_source(path)
        btn_dec.config(state=NORMAL)

    Button(ff, text="Browse…", font=("Segoe UI", 9), command=browse_bin).grid(row=0, column=2, padx=4)

    # ── Mode ─────────────────────────────────────────────────────────
    mode_var = StringVar(value="mosipine")
    mf = Frame(root)
    mf.pack(pady=5)
    Label(mf, text="Mode:", font=("Segoe UI", 10, "bold")).pack(side=LEFT, padx=10)
    for txt, val in [("MO-SiPINE","mosipine"), ("Sine Only","sine"), ("PWLCM Only","pwlcm")]:
        Radiobutton(mf, text=txt, variable=mode_var,
                    value=val, font=("Segoe UI", 10)).pack(side=LEFT, padx=10)

    # ── Input Parameter ──────────────────────────────────────────────
    param_frame = LabelFrame(root, text=" Parameter Kunci ", font=("Segoe UI", 10, "bold"))
    param_frame.pack(fill="x", padx=40, pady=5)
    
    def load_key_from_file():
        path = filedialog.askopenfilename(
            title="Pilih AI_Key_Report.txt",
            filetypes=[("Text File", "*.txt"), ("All Files", "*.*")])
        if not path: return
        try:
            with open(path, 'r', encoding="utf-8") as f:
                content = f.read()
            for line in content.splitlines():
                if line.startswith("Mode Enkripsi :"):
                    loaded_mode = line.split(":")[-1].strip().lower()
                    mode_var.set(loaded_mode)
            for key in ('x1', 'x2', 'p', 'beta'):
                for line in content.splitlines():
                    if line.strip().startswith(f"{key}"):
                        val = line.split("=")[-1].strip()
                        param_vars[key].set(val)
            messagebox.showinfo("Berhasil", "Key dan Mode berhasil dimuat dari file!")
        except Exception as e:
            messagebox.showerror("Error", f"Gagal membaca file key:\n{e}")

    Button(param_frame, text="📂 Muat Otomatis Dari AI_Key_Report.txt",
           font=("Segoe UI", 10, "bold"), bg="#4a90d9", fg="white", activebackground="#357abd",
           command=load_key_from_file, cursor="hand2").grid(row=0, column=0, columnspan=4, pady=(10, 5), padx=10, sticky=E+W)

    param_vars = {k: StringVar() for k in ('x1','x2','p','beta')}
    labels = [("x1", 1, 0), ("x2", 1, 2), ("p", 2, 0), ("β (beta)", 2, 2)]
    widgets_dec = {}
    for lbl, r, c in labels:
        l_w = Label(param_frame, text=f"{lbl}:", font=("Segoe UI", 9))
        l_w.grid(row=r, column=c, padx=10, pady=5, sticky=E)
        key = lbl.replace("β (beta)", "beta")
        e_w = Entry(param_frame, textvariable=param_vars[key], width=20,
              font=("Segoe UI", 10, "bold"))
        e_w.grid(row=r, column=c+1, padx=5, pady=5)
        widgets_dec[key] = (l_w, e_w)

    def toggle_fields_dec(*args):
        for k in ('p', 'beta'):
            widgets_dec[k][0].grid()
            widgets_dec[k][1].grid()
        m = mode_var.get()
        if m == "sine":
            widgets_dec['p'][0].grid_remove()
            widgets_dec['p'][1].grid_remove()
        elif m == "pwlcm":
            widgets_dec['beta'][0].grid_remove()
            widgets_dec['beta'][1].grid_remove()

    mode_var.trace_add("write", toggle_fields_dec)
    toggle_fields_dec()

    # ── Progress ─────────────────────────────────────────────────────
    progress = ttk.Progressbar(root, orient=HORIZONTAL, length=600, mode='determinate')
    progress.pack(pady=10)
    status_var = StringVar(value="Status: Pilih file .bin dan muat kunci...")
    Label(root, textvariable=status_var, font=("Segoe UI", 10), fg="#00529b").pack()

    # ── Tombol Dekripsi ──────────────────────────────────────────────
    btn_frame2 = Frame(root)
    btn_frame2.pack(pady=5)

    btn_dec = Button(btn_frame2, text="🔓 Mulai Dekripsi Video",
                     font=("Segoe UI", 11, "bold"), bg="#f0ad4e", fg="white",
                     activebackground="#eea236", padx=20, pady=8,
                     state=DISABLED, cursor="hand2")
    btn_dec.grid(row=0, column=0, padx=10)
    
    btn_save_avi = Button(btn_frame2, text="⬇️ Unduh Video (.mp4)",
                          font=("Segoe UI", 11, "bold"), bg="#5bc0de", fg="white", 
                          activebackground="#31b0d5", padx=20, pady=8,
                          state=DISABLED, cursor="hand2")
    btn_save_avi.grid(row=0, column=1, padx=10)

    _avi_path_holder = [None]

    def save_avi():
        src = _avi_path_holder[0]
        if not src or not os.path.exists(src):
            messagebox.showwarning("Peringatan", "File video belum tersedia.")
            return
        dst = filedialog.asksaveasfilename(
            title="Simpan Video Dekripsi",
            defaultextension=".mp4",
            initialfile="video_terdekripsi.mp4",
            filetypes=[("Video File", "*.mp4"), ("All Files", "*.*")])
        if dst:
            import shutil
            shutil.copy2(src, dst)
            messagebox.showinfo("Berhasil", f"Video sukses disimpan ke:\n{dst}")

    btn_save_avi.config(command=save_avi)

    def proses_dekripsi():
        b_path = bin_path_var.get()
        if not b_path: return
        try:
            float_params = {k: float(v.get()) for k, v in param_vars.items() if v.get().strip()}
            if 'p' not in float_params: float_params['p'] = 0.25
        except ValueError:
            messagebox.showerror("Error", "Nilai parameter belum terisi atau salah format!")
            return

        player_enc.stop()
        player_dec.stop()

        btn_dec.config(state=DISABLED)
        mode = mode_var.get()
        progress['value'] = 0

        def run():
            try:
                start_time = time.time()
                
                # FASE 1: Dekripsi VIDEO dan AUDIO (.bin → .mp4)
                from video_core import decrypt_VEN2_to_video_audio
                
                status_var.set("Status: [DEKRIPSI] Mendekripsi file biner terpadu...")
                root.update_idletasks()
                out_vid = os.path.join("Tempat_gambar", "video_terdekripsi.mp4")

                def cb(perc):
                    progress['value'] = perc
                    elapsed = time.time() - start_time
                    if perc > 0 and elapsed > 0:
                        eta = int((100 - perc) / (perc / elapsed))
                        m2, s2 = divmod(eta, 60)
                        eta_str = f"{m2}m {s2}s" if m2 else f"{s2} dtk"
                        status_var.set(f"Status: [DEKRIPSI] Berjalan {perc:.1f}% - Sisa: {eta_str}")
                    else:
                        status_var.set(f"Status: [DEKRIPSI] Berjalan {perc:.1f}%...")
                    root.update_idletasks()

                # Fungsi baru yang mendekripsi file .bin yang terpadu (video + audio jika ada)
                decrypt_VEN2_to_video_audio(b_path, out_vid, mode, float_params, cb)

                _avi_path_holder[0] = out_vid
                
                # FASE 2: Preview
                progress['value'] = 100
                player_dec.load_source(out_vid)
                player_dec.lbl_text.config(text="")

                durasi = time.time() - start_time
                mnt, dtk = divmod(int(durasi), 60)
                dur_str = f"{mnt} menit {dtk} detik" if mnt else f"{dtk} detik"
                
                try:
                    import cv2
                    cap = cv2.VideoCapture(out_vid)
                    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    cap.release()
                    sz = os.path.getsize(b_path) / (1024 * 1024)
                    fps_val = total_frames / durasi if durasi > 0 else 0
                    mbps = sz / durasi if durasi > 0 else 0
                    perf_str = f" | FPS: {fps_val:.1f} | {mbps:.2f} MB/s"
                except Exception:
                    perf_str = ""

                status_var.set(f"Status: [OK] Selesai! Waktu Dekripsi: {dur_str}{perf_str}")
                btn_save_avi.config(state=NORMAL)

                if session is not None:
                    session['video_bin'] = b_path
                if on_done:
                    on_done()

                messagebox.showinfo("Berhasil",
                    f"Dekripsi Selesai!\nKinerja: {perf_str.strip(' |')}\nWaktu: {dur_str}\nOutput: video_terdekripsi.mp4")
            except Exception as e:
                status_var.set(f"Status: [ERROR] {e}")
                messagebox.showerror("Error", str(e))
            finally:
                btn_dec.config(state=NORMAL)

        threading.Thread(target=run, daemon=True).start()
    btn_dec.config(command=proses_dekripsi)


# ═══════════════════════════════════════════════════════════════════════════════
# FUNGSI UJI KUALITAS BERBASIS FRAME VIDEO (GABUNGAN 3 FRAME)
# ═══════════════════════════════════════════════════════════════════════════════

def _ujiuniform_v(arr_flat):
    E = len(arr_flat) / 256
    c = collections.Counter(arr_flat.tolist())
    return sum(((c.get(i,0)-E)**2)/E for i in range(256))

def _uaci_v(arr1, arr2):
    d = np.abs(arr1.astype(float) - arr2.astype(float)) / 255.0
    r = d[:,:,0].mean()*100; g = d[:,:,1].mean()*100; b = d[:,:,2].mean()*100
    return (r+g+b)/3

def _npcr_v(arr1, arr2):
    r = (arr1[:,:,0]!=arr2[:,:,0]).mean()*100
    g = (arr1[:,:,1]!=arr2[:,:,1]).mean()*100
    b = (arr1[:,:,2]!=arr2[:,:,2]).mean()*100
    return (r+g+b)/3

def _pearson_v(ch2d, direction):
    if direction=="hor":   x,y = ch2d[:,:-1].flatten(), ch2d[:,1:].flatten()
    elif direction=="ver": x,y = ch2d[:-1,:].flatten(), ch2d[1:,:].flatten()
    else:                  x,y = ch2d[:-1,:-1].flatten(), ch2d[1:,1:].flatten()
    if len(x)<2: return 0.0
    x, y = x.astype(float), y.astype(float)
    std_x, std_y = np.std(x), np.std(y)
    if std_x == 0 and std_y == 0:
        return 1.0 if np.array_equal(x, y) else 0.0
    if std_x == 0 or std_y == 0:
        return 0.0
    r, _ = pearsonr(x, y)
    return float(r) if not np.isnan(r) else 0.0

def _pearson_temporal(arr1, arr2):
    if arr1.shape != arr2.shape: return 0.0
    x, y = arr1.flatten().astype(float), arr2.flatten().astype(float)
    if len(x) < 2: return 0.0
    std_x, std_y = np.std(x), np.std(y)
    if std_x == 0 and std_y == 0:
        return 1.0 if np.array_equal(x, y) else 0.0
    if std_x == 0 or std_y == 0:
        return 0.0
    r, _ = pearsonr(x, y)
    return float(r) if not np.isnan(r) else 0.0

def _psnr_mse_v(arr1, arr2):
    mse = np.mean((arr1.astype(float)-arr2.astype(float))**2)
    if mse==0: return float('inf'), 0.0
    return 20*math.log10(255.0/math.sqrt(mse)), mse

def _entropy_v(ch_flat): return skimage.measure.shannon_entropy(ch_flat)

# Helper untuk meminta input file dari user dan mengekstrak frame
def _prompt_and_extract_frames(parent):
    # Meminta input video asli
    vid = filedialog.askopenfilename(title="Pilih Video Asli", filetypes=[("Video Files", "*.mp4 *.avi *.mov *.mkv"), ("All Files", "*.*")], parent=parent)
    if not vid: return None

    # Meminta input file bin
    bin_f = filedialog.askopenfilename(title="Pilih File Terenkripsi (.bin)", filetypes=[("Binary Files", "*.bin"), ("All Files", "*.*")], parent=parent)
    if not bin_f: return None

    paths = {}
    from video_core import extract_sample_frames, extract_single_frame_from_bin
    
    # Ekstrak plain frame
    try:
        p1, p2, p3 = extract_sample_frames(vid, "Tempat_gambar")
        paths["plain"] = [p1, p2, p3]
    except Exception as e:
        messagebox.showerror("Error", f"Gagal ekstrak frame asli:\n{e}", parent=parent)
        return None

    # Ekstrak cipher frame
    try:
        c1 = "Tempat_gambar/cipher_awal.png"
        c2 = "Tempat_gambar/cipher_tengah.png"
        c3 = "Tempat_gambar/cipher_akhir.png"
        extract_single_frame_from_bin(bin_f, 0.10, c1)
        extract_single_frame_from_bin(bin_f, 0.50, c2)
        extract_single_frame_from_bin(bin_f, 0.90, c3)
        paths["cipher"] = [c1, c2, c3]
    except Exception as e:
        messagebox.showerror("Error", f"Gagal ekstrak frame cipher:\n{e}", parent=parent)
        return None

    return paths

# ── HELPERS BERSAMA ───────────────────────────────────────────────────────────
def _detect_type(fp):
    ext = os.path.splitext(fp)[1].lower()
    base = os.path.basename(fp).lower()
    if ext == ".bin":  return "🔒 Gambar Terenkripsi (.bin)"
    if "terdekripsi" in base and ext in (".mp4", ".avi", ".mkv"): return f"🔓 Gambar Terdekripsi ({ext})"
    if ext in (".mp4", ".mov", ".mkv", ".avi"): return f"🎬 Gambar Asli ({ext})"
    return "🖼️ Citra/Gambar"

def _extract_3_frames(fp, slot, parent_win):
    """Ekstrak frame pada 10%, 50%, 90% dari video/bin/citra. Return list 3 path."""
    labels = [("awal", 0.10), ("tengah", 0.50), ("akhir", 0.90)]
    result = []
    os.makedirs("Tempat_gambar", exist_ok=True)
    for lbl, ratio in labels:
        out = f"Tempat_gambar/c{slot}_{lbl}.png"
        try:
            if fp.lower().endswith(".bin"):
                extract_single_frame_from_bin(fp, ratio, out)
            elif fp.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
                cap = cv2.VideoCapture(fp)
                total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                if total > 0:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, int(total * ratio))
                ret, frame = cap.read(); cap.release()
                if ret: cv2.imwrite(out, frame)
                else: out = None
            else:
                PIL.Image.open(fp).convert("RGB").save(out)
        except Exception:
            out = None
        result.append(out)
    return result

def _extract_key_frames(fp, slot, parent_win, n_frames=10):
    """Ekstrak N pasang frame (t dan t+1) dinamis (Key-Frame) dari video/bin/citra. Return list of tuple(path_t, path_t1)."""
    ratios = [i / max(1, n_frames-1) for i in range(n_frames)]
    result = []
    os.makedirs("Tempat_gambar", exist_ok=True)
    for i, ratio in enumerate(ratios):
        out_t = f"Tempat_gambar/c{slot}_kf_{i}_t.png"
        out_next = f"Tempat_gambar/c{slot}_kf_{i}_next.png"
        try:
            if fp.endswith(".bin"):
                import struct
                with open(fp, 'rb') as fbin:
                    header = fbin.read(36)
                    # Deteksi format VEN2
                    if len(header) >= 36 and header[:4] == b"VEN2":
                        _, width, height, total, _, _, _, _, _, _ = struct.unpack('<4sIIIfIHIHI', header)
                    else:
                        raise ValueError("Header file .bin tidak valid atau korup")
                idx = max(0, min(int(total * ratio), total - 2))
                extract_single_frame_from_bin(fp, idx / max(1, total - 1), out_t)
                extract_single_frame_from_bin(fp, (idx + 1) / max(1, total - 1), out_next)
            elif fp.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
                cap = cv2.VideoCapture(fp)
                total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                if total > 1:
                    idx = max(0, min(int(total * ratio), total - 2))
                    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                    ret1, f1 = cap.read()
                    ret2, f2 = cap.read()
                    if ret1 and ret2:
                        cv2.imwrite(out_t, f1)
                        cv2.imwrite(out_next, f2)
                    else: out_t = None
                else: out_t = None
                cap.release()
            else:
                PIL.Image.open(fp).convert("RGB").save(out_t)
                PIL.Image.open(fp).convert("RGB").save(out_next)
        except Exception as e:
            out_t = None
        if out_t and os.path.exists(out_t) and os.path.exists(out_next):
            result.append((out_t, out_next))
    return result

def _make_slot_2img(parent, slot, title, data, FW=110, FH=100):
    """Buat grup LabelFrame dengan 3 canvas preview + label tipe + tombol pilih."""
    grp = LabelFrame(parent, text=f"  {title}  ", font=("Segoe UI", 10, "bold"), padx=6, pady=6)
    fc = Frame(grp); fc.pack()
    caps = ["Awal\n(~10%)", "Tengah\n(~50%)", "Akhir\n(~90%)"]
    cvs = []
    for i, cap in enumerate(caps):
        cf = Frame(fc); cf.grid(row=0, column=i, padx=3)
        cv_ = Canvas(cf, width=FW, height=FH, bg="#f0f0f0", highlightthickness=1, highlightbackground="#bbb")
        cv_.pack()
        Label(cf, text=cap, font=("Segoe UI", 7), fg="#555", justify="center").pack()
        cvs.append(cv_)
    data[slot]["canvases"] = cvs
    Label(grp, textvariable=data[slot]["type_var"],
          font=("Segoe UI", 9, "italic"), fg="#1a5fa8").pack(pady=(5, 2))

    def pick(s=slot, win=parent):
        fp = filedialog.askopenfilename(
            parent=win, title=f"Pilih File untuk {title}",
            filetypes=[("Video/Bin/Image", "*.mp4 *.avi *.bin *.mov *.mkv *.png *.jpg *.jpeg *.bmp"),
                       ("All Files", "*.*")])
        if not fp: return
        pairs = _extract_key_frames(fp, s, win, n_frames=10)
        data[s]["paths"] = [p[0] for p in pairs]
        data[s]["paths_next"] = [p[1] for p in pairs]
        data[s]["type_var"].set(_detect_type(fp))
        disp = [pairs[0][0], pairs[len(pairs)//2][0], pairs[-1][0]] if len(pairs)>=3 else (([p[0] for p in pairs] + [None]*3)[:3])
        for cv_, p in zip(data[s]["canvases"], disp):
            cv_.delete("all")
            if p and os.path.exists(p):
                try:
                    im = PIL.Image.open(p).resize((FW, FH), PIL.Image.LANCZOS)
                    ph = PIL.ImageTk.PhotoImage(im)
                    cv_.create_image(FW//2, FH//2, image=ph); cv_.image = ph
                except Exception: pass

    Button(grp, text=f"Pilih {title}", font=("Segoe UI", 10),
           padx=10, pady=6, bd=1, relief="ridge",
           bg="#e1e7ed", activebackground="#cfd8e3", command=pick).pack(pady=(3, 0))
    return grp


# ── 1. UJI HISTOGRAM & KORELASI ───────────────────────────────────────────────
def uji_histogram_korelasi_video(session, parent):
    statt = Toplevel(parent)
    statt.geometry("1020x560")
    statt.title("Uji Kualitas Hasil Dekripsi Citra")
    statt.resizable(False, False)

    Label(statt, font=("Segoe UI", 15), text="Uji Kualitas Citra Digital",
          bd=1, relief="ridge").pack(pady=12)

    data = {
        1: {"paths": [], "type_var": StringVar(value="(belum dipilih)"), "canvases": []},
        2: {"paths": [], "type_var": StringVar(value="(belum dipilih)"), "canvases": []},
    }
    grp_frm = Frame(statt); grp_frm.pack(pady=5)
    _make_slot_2img(grp_frm, 1, "Citra 1", data).grid(row=0, column=0, padx=20)
    _make_slot_2img(grp_frm, 2, "Citra 2", data).grid(row=0, column=1, padx=20)

    def run():
        if not data[1]["paths"] or not data[2]["paths"]:
            messagebox.showwarning("Peringatan", "Pilih Citra 1 dan Citra 2 terlebih dahulu!", parent=statt)
            return
        tab = Toplevel(statt)
        tab.geometry("1600x1000")
        tab.title("Hasil Uji Histogram & Korelasi")

        try:
            arrs1 = []
            for p in data[1]["paths"]:
                # NEAREST: mempertahankan nilai pixel asli — kritis untuk analisis statistik
                if os.path.exists(p): arrs1.append(np.array(PIL.Image.open(p).convert("RGB").resize((320, 240), PIL.Image.NEAREST)))
            arrs2 = []
            for p in data[2]["paths"]:
                if os.path.exists(p): arrs2.append(np.array(PIL.Image.open(p).convert("RGB").resize((320, 240), PIL.Image.NEAREST)))
        except Exception as e:
            messagebox.showerror("Error", f"Gagal membaca citra:\n{e}", parent=statt); tab.destroy(); return

        if not arrs1 or not arrs2:
            messagebox.showerror("Error", "Gagal membaca citra!", parent=statt); tab.destroy(); return

        arr1 = arrs1[len(arrs1) // 2]   # frame tengah untuk histogram
        arr2 = arrs2[len(arrs2) // 2]

        def avg_p(arrs, ch, d): return sum(_pearson_v(a[:, :, ch], d) for a in arrs) / len(arrs)
        c1v=[avg_p(arrs1,0,d) for d in ("hor","ver","dia")]
        c2v=[avg_p(arrs1,1,d) for d in ("hor","ver","dia")]
        c3v=[avg_p(arrs1,2,d) for d in ("hor","ver","dia")]
        c4v=[avg_p(arrs2,0,d) for d in ("hor","ver","dia")]
        c5v=[avg_p(arrs2,1,d) for d in ("hor","ver","dia")]
        c6v=[avg_p(arrs2,2,d) for d in ("hor","ver","dia")]

        for ch,arr,color,suf in [(0,arr1,"red",""),(1,arr1,"green",""),(2,arr1,"blue",""),
                                  (0,arr2,"red","1"),(1,arr2,"green","1"),(2,arr2,"blue","1")]:
            tag={"red":"Red","green":"Green","blue":"Blue"}[color]
            fname=f"Tempat_gambar/{tag}{suf}_manual.png"
            plt.figure(figsize=(4,3))
            plt.hist(arr[:,:,ch].flatten(), bins=256, range=(0,255), color=color, edgecolor='none')
            plt.title(f"Histogram {tag}"); plt.xlim(0,255)
            plt.savefig(fname, dpi=120, bbox_inches='tight'); plt.close()

        t1 = data[1]["type_var"].get(); t2 = data[2]["type_var"].get()
        Fr1=Frame(tab,width=1600,height=50); Fr1.pack(side=TOP)
        Label(Fr1,text=f"Histogram {t1}",font=("Segoe UI",14,"bold")).grid(pady=5)
        Fr2=Frame(tab,width=1600,height=235); Fr2.pack(side=TOP)
        for col,(tag,suf) in enumerate([("Red",""),("Green",""),("Blue","")]):
            fname=f"Tempat_gambar/{tag}{suf}_manual.png"
            im=PIL.Image.open(fname).resize((300,225),PIL.Image.LANCZOS)
            gif_f=fname.replace(".png",".gif"); im.save(gif_f)
            c_=Canvas(Fr2,height=235,width=310); c_.grid(row=0,column=col)
            ph=PhotoImage(file=gif_f,master=c_); lbl=Label(c_,image=ph); lbl.image=ph; lbl.grid(row=0,column=0)

        Fr3=Frame(tab,width=1600,height=50); Fr3.pack(side=TOP)
        Label(Fr3,text=f"Histogram {t2}",font=("Segoe UI",14,"bold")).grid(pady=5)
        Fr4=Frame(tab,width=1600,height=235); Fr4.pack(side=TOP)
        for col,(tag,suf) in enumerate([("Red","1"),("Green","1"),("Blue","1")]):
            fname=f"Tempat_gambar/{tag}{suf}_manual.png"
            im=PIL.Image.open(fname).resize((300,225),PIL.Image.LANCZOS)
            gif_f=fname.replace(".png",".gif"); im.save(gif_f)
            c_=Canvas(Fr4,height=235,width=310); c_.grid(row=0,column=col)
            ph=PhotoImage(file=gif_f,master=c_); lbl=Label(c_,image=ph); lbl.image=ph; lbl.grid(row=0,column=0)

        n = f"(avg {len(arrs1)} frame)"
        Fr5=Frame(tab,width=1600,height=130); Fr5.pack(side=TOP, pady=10)
        Label(Fr5,text=f"Korel. {t1}\n{n}",font=("Segoe UI",9),bd=1,relief="ridge").place(x=10,y=50)
        for ci,txt in enumerate(["R","G","B"]): Label(Fr5,text=txt,font=("Segoe UI",10),bd=1,relief="ridge").place(x=220,y=30+ci*30)
        for ci,lt in enumerate(["Horizontal","Vertikal","Diagonal"]): Label(Fr5,text=lt,font=("Segoe UI",10),bd=1,relief="ridge").place(x=260+ci*100,y=0)
        for ci,row in enumerate([c1v,c2v,c3v]):
            for di,val in enumerate(row): Label(Fr5,text=f"{val:.5f}"[:7],font=("Segoe UI",10),bd=1,relief="ridge").place(x=260+di*100,y=30+ci*30)
        Label(Fr5,text=f"Korel. {t2}\n{n}",font=("Segoe UI",9),bd=1,relief="ridge").place(x=590,y=50)
        for ci,txt in enumerate(["R","G","B"]): Label(Fr5,text=txt,font=("Segoe UI",10),bd=1,relief="ridge").place(x=800,y=30+ci*30)
        for ci,lt in enumerate(["Horizontal","Vertikal","Diagonal"]): Label(Fr5,text=lt,font=("Segoe UI",10),bd=1,relief="ridge").place(x=840+ci*100,y=0)
        for ci,row in enumerate([c4v,c5v,c6v]):
            for di,val in enumerate(row): Label(Fr5,text=f"{val:.5f}"[:7],font=("Segoe UI",10),bd=1,relief="ridge").place(x=840+di*100,y=30+ci*30)
        psnr,mse=_psnr_mse_v(arr1,arr2)
        Label(Fr5,text=f"Nilai MSE  : {mse:.2f}",font=("Segoe UI",11,"bold"),bd=1,relief="ridge",bg="#e8f0fe",padx=10,pady=4).place(x=1150,y=30)
        Label(Fr5,text=f"Nilai PSNR : {psnr:.4f} dB",font=("Segoe UI",11,"bold"),bd=1,relief="ridge",bg="#e8f0fe",padx=10,pady=4).place(x=1150,y=80)

    btn_frm = Frame(statt); btn_frm.pack(pady=8)
    Button(btn_frm,padx=12,pady=7,bd=1,relief="ridge",bg="#e1e7ed",activebackground="#cfd8e3",
           fg="black",font=("Segoe UI",10),width=22,text="Uji Histogram & Korelasi",command=run).grid(row=0,column=0,padx=5)
    Button(btn_frm,padx=12,pady=7,bd=1,relief="ridge",bg="#e1e7ed",activebackground="#cfd8e3",
           fg="black",font=("Segoe UI",10),width=10,text="Keluar",command=statt.destroy).grid(row=0,column=1,padx=5)


# ── 2. UJI DISTRIBUSI KORELASI (SCATTER PLOT) ─────────────────────────────────
def uji_distribusi_scatter_video(session, parent):
    statt = Toplevel(parent)
    statt.geometry("560x480")
    statt.title("Uji Keacakan (Distribusi Korelasi)")
    statt.resizable(False, False)

    Label(statt, font=("Segoe UI", 14), text="Uji Keacakan (Distribusi Korelasi)",
          bd=1, relief="ridge").pack(pady=12)

    FW, FH = 110, 100
    data = {1: {"paths": [], "type_var": StringVar(value="(belum dipilih)"), "canvases": []}}

    grp = LabelFrame(statt, text="  Pilih File Video/Bin/Citra  ",
                     font=("Segoe UI", 10, "bold"), padx=8, pady=8)
    grp.pack(pady=6)
    fc = Frame(grp); fc.pack()
    caps = ["Awal\n(~10%)", "Tengah\n(~50%)", "Akhir\n(~90%)"]
    cvs = []
    for i, cap in enumerate(caps):
        cf = Frame(fc); cf.grid(row=0, column=i, padx=3)
        cv_ = Canvas(cf, width=FW, height=FH, bg="#f0f0f0",
                     highlightthickness=1, highlightbackground="#bbb")
        cv_.pack()
        Label(cf, text=cap, font=("Segoe UI", 7), fg="#555", justify="center").pack()
        cvs.append(cv_)
    data[1]["canvases"] = cvs
    Label(grp, textvariable=data[1]["type_var"],
          font=("Segoe UI", 9, "italic"), fg="#1a5fa8").pack(pady=(5, 2))

    def pick():
        fp = filedialog.askopenfilename(
            parent=statt, title="Pilih File",
            filetypes=[("Video/Bin/Image", "*.mp4 *.avi *.bin *.mov *.mkv *.png *.jpg *.jpeg *.bmp"),
                       ("All Files", "*.*")])
        if not fp: return
        fps = _extract_3_frames(fp, 1, statt)
        data[1]["paths"] = [p for p in fps if p]
        data[1]["type_var"].set(_detect_type(fp))
        for cv_, p in zip(data[1]["canvases"], fps):
            cv_.delete("all")
            if p and os.path.exists(p):
                try:
                    im = PIL.Image.open(p).resize((FW, FH), PIL.Image.LANCZOS)
                    ph = PIL.ImageTk.PhotoImage(im)
                    cv_.create_image(FW//2, FH//2, image=ph); cv_.image = ph
                except Exception: pass

    Button(grp, text="Pilih File", font=("Segoe UI", 10),
           padx=10, pady=6, bd=1, relief="ridge",
           bg="#e1e7ed", activebackground="#cfd8e3", command=pick).pack(pady=(3, 0))

    def run():
        if not data[1]["paths"]:
            messagebox.showwarning("Peringatan", "Pilih file terlebih dahulu!", parent=statt); return
        mid = data[1]["paths"][min(1, len(data[1]["paths"])-1)]
        try:
            # Baca frame PENUH tanpa subsampling agar seluruh pixel diplot (kepadatan maksimal)
            img_full = PIL.Image.open(mid).convert("RGB")
            arr1 = np.array(img_full)
        except Exception as e:
            messagebox.showerror("Error", f"Gagal membaca citra:\n{e}", parent=statt); return
        t = data[1]["type_var"].get()
        tab = Toplevel(statt)
        tab.geometry("1000x870")
        tab.title(f"Hasil Uji Distribusi Korelasi — {t}")
        channels = [(arr1[:,:,0],"red"),(arr1[:,:,1],"green"),(arr1[:,:,2],"blue")]
        dirs = [("hor","Horizontal"),("ver","Vertikal"),("dia","Diagonal")]
        Fr1=Frame(tab,width=1000,height=70); Fr1.pack(side=TOP)
        Label(Fr1,text=f"Uji Korelasi Pearson — {t}",font=("Segoe UI",13,"bold")).grid(row=0,column=0,columnspan=3,pady=8)
        for ci,(_,dtxt) in enumerate(dirs):
            Label(Fr1,text=dtxt,font=("Segoe UI",12)).grid(row=1,column=ci,padx=80)
        for ri,(ch,color) in enumerate(channels):
            Fr=Frame(tab,width=1000,height=240); Fr.pack(side=TOP)
            for ci,(dkey,_) in enumerate(dirs):
                if dkey=="hor":   x,y=ch[:,:-1].flatten(),ch[:,1:].flatten()
                elif dkey=="ver": x,y=ch[:-1,:].flatten(),ch[1:,:].flatten()
                else:             x,y=ch[:-1,:-1].flatten(),ch[1:,1:].flatten()
                fname=f"Tempat_gambar/scatter_{color}_{dkey}_manual.png"
                fig,ax=plt.subplots(figsize=(4,4))
                # Plot SELURUH titik piksel tanpa random choice (bisa >1-2 juta titik)
                # s=5.0 dan alpha=1.0 menjamin plot membentuk "full block" warna solid tanpa ada spot putih
                ax.scatter(x, y, color=color, s=5.0, alpha=1.0, linewidths=0, rasterized=True)
                ax.set_xlim(0,255); ax.set_ylim(0,255)
                ax.set_aspect('equal')
                fig.savefig(fname,dpi=150,bbox_inches='tight',pad_inches=0.05); plt.close(fig)
                im=PIL.Image.open(fname).resize((220,220),PIL.Image.LANCZOS)
                gif_f=fname.replace(".png",".gif"); im.save(gif_f)
                c_=Canvas(Fr,height=235,width=300); c_.grid(row=0,column=ci)
                ph=PhotoImage(file=gif_f,master=c_)
                lbl=Label(c_,image=ph); lbl.image=ph; lbl.pack()

    btn_frm = Frame(statt); btn_frm.pack(pady=8)
    Button(btn_frm,padx=12,pady=7,bd=1,relief="ridge",bg="#e1e7ed",activebackground="#cfd8e3",
           fg="black",font=("Segoe UI",10),width=20,text="Uji Distribusi Korelasi",command=run).grid(row=0,column=0,padx=5)
    Button(btn_frm,padx=12,pady=7,bd=1,relief="ridge",bg="#e1e7ed",activebackground="#cfd8e3",
           fg="black",font=("Segoe UI",10),width=10,text="Keluar",command=statt.destroy).grid(row=0,column=1,padx=5)


# ── 3. UJI STATISTIK (UNIFORM, ENTROPI, NPCR, UACI) ───────────────────────────
def uji_statistik_video(session, parent):
    statt = Toplevel(parent)
    statt.geometry("1020x560")
    statt.title("Uji Statistik Citra Digital (Entropi, NPCR, UACI)")
    statt.resizable(False, False)

    Label(statt, font=("Segoe UI", 15), text="Uji Statistik Citra Digital",
          bd=1, relief="ridge").pack(pady=12)

    data = {
        1: {"paths": [], "type_var": StringVar(value="(belum dipilih)"), "canvases": []},
        2: {"paths": [], "type_var": StringVar(value="(belum dipilih)"), "canvases": []},
    }
    grp_frm = Frame(statt); grp_frm.pack(pady=5)
    _make_slot_2img(grp_frm, 1, "Citra 1", data).grid(row=0, column=0, padx=20)
    _make_slot_2img(grp_frm, 2, "Citra 2", data).grid(row=0, column=1, padx=20)

    def run():
        if not data[1]["paths"] or not data[2]["paths"]:
            messagebox.showwarning("Peringatan", "Pilih Citra 1 dan Citra 2 terlebih dahulu!", parent=statt); return
        try:
            arrs1 = []
            for p in data[1]["paths"]:
                # NEAREST: preserves original pixel values — kritis untuk analisis statistik
                # LANCZOS akan menginterpolasi pixel → distribusi palsu (entropy turun artifisial)
                if os.path.exists(p): arrs1.append(np.array(PIL.Image.open(p).convert("RGB").resize((320, 240), PIL.Image.NEAREST)))
            arrs2 = []
            for p in data[2]["paths"]:
                if os.path.exists(p): arrs2.append(np.array(PIL.Image.open(p).convert("RGB").resize((320, 240), PIL.Image.NEAREST)))
        except Exception as e:
            messagebox.showerror("Error", f"Gagal membaca citra:\n{e}", parent=statt); return

        if not arrs1 or not arrs2:
            messagebox.showerror("Error","Gagal membaca citra!",parent=statt); return
            
        arrs1_next = []
        for p in data[1].get("paths_next", []):
            if os.path.exists(p): arrs1_next.append(np.array(PIL.Image.open(p).convert("RGB").resize((320, 240), PIL.Image.NEAREST)))
        arrs2_next = []
        for p in data[2].get("paths_next", []):
            if os.path.exists(p): arrs2_next.append(np.array(PIL.Image.open(p).convert("RGB").resize((320, 240), PIL.Image.NEAREST)))
            
        def avg_e(arrs,ch): return sum(_entropy_v(a[:,:,ch].flatten()) for a in arrs)/len(arrs)
        def avg_c(arrs,ch): return sum(_ujiuniform_v(a[:,:,ch].flatten()) for a in arrs)/len(arrs)
        e1=(avg_e(arrs1,0)+avg_e(arrs1,1)+avg_e(arrs1,2))/3
        e2=(avg_e(arrs2,0)+avg_e(arrs2,1)+avg_e(arrs2,2))/3
        u1r=avg_c(arrs1,0);u1g=avg_c(arrs1,1);u1b=avg_c(arrs1,2)
        u2r=avg_c(arrs2,0);u2g=avg_c(arrs2,1);u2b=avg_c(arrs2,2)
        pairs=list(zip(arrs1,arrs2))
        npcr_val=sum(_npcr_v(a,b) for a,b in pairs)/len(pairs)
        uaci_val=sum(_uaci_v(a,b) for a,b in pairs)/len(pairs)
        
        pairs_t1 = list(zip(arrs1, arrs1_next))
        pairs_t2 = list(zip(arrs2, arrs2_next))
        corr_t1 = (sum(_pearson_temporal(a, b) for a, b in pairs_t1) / max(1, len(pairs_t1))) if pairs_t1 else 0.0
        corr_t2 = (sum(_pearson_temporal(a, b) for a, b in pairs_t2) / max(1, len(pairs_t2))) if pairs_t2 else 0.0
        
        n=f"(avg {len(arrs1)} key-frame)"; t1=data[1]["type_var"].get(); t2=data[2]["type_var"].get()
        hasil=Toplevel(statt); hasil.geometry("960x400"); hasil.title("Hasil Uji Statistik Kualitas Citra")
        F1=Frame(hasil); F1.pack(side=TOP,pady=10)
        F2=Frame(hasil); F2.pack(side=TOP)
        Label(F1,font=("Segoe UI",14,"bold"),text=f"Hasil Uji Statistik — {n}").pack()
        Label(F1,font=("Segoe UI",9,"italic"),fg="#555",text=f"Citra 1: {t1}    |    Citra 2: {t2}").pack()
        rows=[
            ("Metrik Uji",      "Citra 1",       "Citra 2",        "Keterangan"),
            ("NPCR (%)",        "—",             f"{npcr_val:.4f}%","Ideal ≥ 99.6%"),
            ("UACI (%)",        "—",             f"{uaci_val:.4f}%","Ideal ≈ 33.4%"),
            ("Entropi (rata2)", f"{e1:.5f}",      f"{e2:.5f}",      "Ideal = 8.0"),
            ("Korelasi Temporal",f"{corr_t1:.5f}",f"{corr_t2:.5f}", "Ideal ≈ 0.0 (Cipher)"),
            ("Chi-Square R",    f"{u1r:.2f}",     f"{u2r:.2f}",     "Distribusi seragam"),
            ("Chi-Square G",    f"{u1g:.2f}",     f"{u2g:.2f}",     "Distribusi seragam"),
            ("Chi-Square B",    f"{u1b:.2f}",     f"{u2b:.2f}",     "Distribusi seragam"),
        ]
        for ri,row in enumerate(rows):
            bg="#dce4ed" if ri==0 else ("#f2f5f8" if ri%2==0 else "white")
            fnt=("Segoe UI",11,"bold") if ri==0 else ("Segoe UI",11)
            for ci,val in enumerate(row):
                Label(F2,font=fnt,text=val,bd=1,relief="ridge",width=22,bg=bg,pady=4).grid(row=ri,column=ci,sticky="nsew")

    btn_frm=Frame(statt); btn_frm.pack(pady=8)
    Button(btn_frm,padx=12,pady=7,bd=1,relief="ridge",bg="#e1e7ed",activebackground="#cfd8e3",
           fg="black",font=("Segoe UI",10),width=16,text="Uji Statistik",command=run).grid(row=0,column=0,padx=5)
    Button(btn_frm,padx=12,pady=7,bd=1,relief="ridge",bg="#e1e7ed",activebackground="#cfd8e3",
           fg="black",font=("Segoe UI",10),width=10,text="Keluar",command=statt.destroy).grid(row=0,column=1,padx=5)


# ═══════════════════════════════════════════════════════════════════════════════
# ENKRIPSI & DEKRIPSI AUDIO STANDALONE
# ═══════════════════════════════════════════════════════════════════════════════

def enkripsi_audio_standalone(session=None, on_done=None):
    """Window: Enkripsi file WAV/audio secara mandiri menggunakan MO-SiPINE."""
    root = Toplevel()
    root.geometry("600x560")
    root.title("Enkripsi Audio  |  SIP Map")
    root.resizable(False, False)

    Label(root, text="Enkripsi Audio  —  MO-SiPINE",
          font=("Segoe UI", 16, "bold")).pack(pady=(14, 2))
    Label(root, text="Enkripsi file WAV menggunakan keystream chaos XOR",
          font=("Segoe UI", 10), fg="gray").pack()

    # ── Pilih file audio ────────────────────────────────────────────────────
    ff = Frame(root); ff.pack(pady=10)
    wav_path_var = StringVar()
    Label(ff, text="File Audio (WAV):", font=("Segoe UI", 10)).grid(row=0, column=0, padx=4, sticky=E)
    Entry(ff, textvariable=wav_path_var, width=42,
          state='readonly', font=("Segoe UI", 10)).grid(row=0, column=1, padx=4)

    def browse_wav():
        path = filedialog.askopenfilename(
            title="Pilih File Audio",
            filetypes=[("WAV Files", "*.wav"), ("All Files", "*.*")])
        if not path: return
        wav_path_var.set(path)
        btn_enc.config(state=NORMAL)

    Button(ff, text="Browse…", font=("Segoe UI", 9), command=browse_wav).grid(row=0, column=2, padx=4)

    # ── Mode enkripsi ────────────────────────────────────────────────────────
    mode_var = StringVar(value="mosipine")
    mf = Frame(root); mf.pack(pady=6)
    Label(mf, text="Mode:", font=("Segoe UI", 10, "bold")).pack(side=LEFT, padx=10)
    for txt, val in [("SIP Map","mosipine"), ("Sine Only","sine"), ("PWLCM Only","pwlcm")]:
        Radiobutton(mf, text=txt, variable=mode_var,
                    value=val, font=("Segoe UI", 10)).pack(side=LEFT, padx=8)

    # ── Parameter kunci ──────────────────────────────────────────────────────
    pf = LabelFrame(root, text=" Parameter Kunci (Chaos) ", font=("Segoe UI", 10, "bold"))
    pf.pack(fill="x", padx=40, pady=6)

    param_vars = {k: StringVar() for k in ('x1', 'x2', 'p', 'beta')}
    defaults   = {'x1': '0.1', 'x2': '0.9', 'p': '0.25', 'beta': '0.7'}
    for k, v in defaults.items():
        param_vars[k].set(v)

    labels_cfg = [("x1", 0, 0), ("x2", 0, 2), ("p", 1, 0), ("β (beta)", 1, 2)]
    widgets_enc = {}
    for lbl, r, c in labels_cfg:
        key = lbl.replace("β (beta)", "beta")
        l_w = Label(pf, text=f"{lbl}:", font=("Segoe UI", 9))
        l_w.grid(row=r, column=c, padx=10, pady=5, sticky=E)
        e_w = Entry(pf, textvariable=param_vars[key], width=18, font=("Segoe UI", 10))
        e_w.grid(row=r, column=c+1, padx=5, pady=5)
        widgets_enc[key] = (l_w, e_w)

    def toggle_fields(*args):
        for k in ('p', 'beta'):
            widgets_enc[k][0].grid(); widgets_enc[k][1].grid()
        m = mode_var.get()
        if m == "sine":
            widgets_enc['p'][0].grid_remove(); widgets_enc['p'][1].grid_remove()
        elif m == "pwlcm":
            widgets_enc['beta'][0].grid_remove(); widgets_enc['beta'][1].grid_remove()
    mode_var.trace_add("write", toggle_fields)
    toggle_fields()

    # ── Tombol muat key dari file ────────────────────────────────────────────
    def load_key_from_file():
        path = filedialog.askopenfilename(
            title="Pilih AI_Key_Report.txt",
            filetypes=[("Text File", "*.txt"), ("All Files", "*.*")])
        if not path: return
        try:
            with open(path, 'r', encoding="utf-8") as f:
                content = f.read()
            for line in content.splitlines():
                if line.startswith("Mode Enkripsi :"):
                    mode_var.set(line.split(":")[-1].strip().lower())
            for key in ('x1', 'x2', 'p', 'beta'):
                for line in content.splitlines():
                    if line.strip().startswith(f"{key} ") or line.strip().startswith(f"{key}="):
                        val = line.split("=")[-1].strip()
                        param_vars[key].set(val)
            messagebox.showinfo("Berhasil", "Key berhasil dimuat!", parent=root)
        except Exception as e:
            messagebox.showerror("Error", f"Gagal membaca key:\n{e}", parent=root)

    Button(pf, text="📂 Muat dari AI_Key_Report.txt",
           font=("Segoe UI", 9), bg="#4a90d9", fg="white",
           command=load_key_from_file, cursor="hand2").grid(
               row=2, column=0, columnspan=4, pady=(4, 8), padx=10, sticky=E+W)

    # ── Progress & status ────────────────────────────────────────────────────
    progress = ttk.Progressbar(root, orient=HORIZONTAL, length=520, mode='determinate')
    progress.pack(pady=10)
    status_var = StringVar(value="Status: Pilih file WAV dan isi parameter kunci…")
    Label(root, textvariable=status_var, font=("Segoe UI", 9),
          fg="#00529b", wraplength=560).pack()

    # ── Tombol enkripsi ──────────────────────────────────────────────────────
    btn_frame = Frame(root); btn_frame.pack(pady=10)
    _out_holder = [None]

    btn_enc = Button(btn_frame, text="🔒 Enkripsi Audio",
                     font=("Segoe UI", 11, "bold"), bg="#4a90d9", fg="white",
                     activebackground="#357abd", padx=15, pady=8,
                     state=DISABLED, cursor="hand2")
    btn_enc.grid(row=0, column=0, padx=10)

    btn_save = Button(btn_frame, text="⬇️ Simpan .bin",
                      font=("Segoe UI", 11, "bold"), bg="#5bc0de", fg="white",
                      activebackground="#31b0d5", padx=15, pady=8,
                      state=DISABLED, cursor="hand2")
    btn_save.grid(row=0, column=1, padx=10)

    def save_bin():
        src = _out_holder[0]
        if not src or not os.path.exists(src):
            messagebox.showwarning("Peringatan", "File belum tersedia.", parent=root); return
        dst = filedialog.asksaveasfilename(
            title="Simpan Audio Terenkripsi",
            defaultextension=".bin",
            initialfile="audio_terenkripsi.bin",
            filetypes=[("Binary File", "*.bin"), ("All Files", "*.*")])
        if dst:
            import shutil; shutil.copy2(src, dst)
            messagebox.showinfo("Berhasil", f"File disimpan ke:\n{dst}", parent=root)
    btn_save.config(command=save_bin)

    def proses_enkripsi():
        wav = wav_path_var.get()
        if not wav: return
        try:
            float_params = {k: float(param_vars[k].get()) for k in ('x1','x2','p','beta')
                            if param_vars[k].get().strip()}
            if 'p' not in float_params: float_params['p'] = 0.25
        except ValueError:
            messagebox.showerror("Error", "Parameter tidak valid!", parent=root); return

        mode = mode_var.get()
        btn_enc.config(state=DISABLED)
        progress['value'] = 0

        def run():
            try:
                from audio_core import encrypt_audio
                os.makedirs("Tempat_gambar", exist_ok=True)
                out_bin = os.path.join("Tempat_gambar", "audio_terenkripsi.bin")
                status_var.set("Status: [AUDIO] Mengenkripsi audio…")
                root.update_idletasks()
                encrypt_audio(wav, out_bin, mode, float_params)
                progress['value'] = 100
                _out_holder[0] = out_bin
                status_var.set(f"Status: [OK] Selesai! → {os.path.basename(out_bin)}")
                btn_save.config(state=NORMAL)
                if session is not None:
                    session['audio_bin'] = out_bin
                    session['mode']      = mode
                    session['kunci']     = float_params
                if on_done: on_done()
                messagebox.showinfo("Berhasil",
                    f"Enkripsi audio selesai!\nOutput: {out_bin}", parent=root)
            except Exception as e:
                status_var.set(f"Status: [ERROR] {e}")
                messagebox.showerror("Error", str(e), parent=root)
            finally:
                btn_enc.config(state=NORMAL)

        import threading
        threading.Thread(target=run, daemon=True).start()

    btn_enc.config(command=proses_enkripsi)


def dekripsi_audio_standalone(session=None, on_done=None):
    """Window: Dekripsi file .bin audio kembali ke WAV menggunakan MO-SiPINE."""
    root = Toplevel()
    root.geometry("600x540")
    root.title("Dekripsi Audio  |  MO-SiPINE")
    root.resizable(False, False)

    Label(root, text="Dekripsi Audio  —  MO-SiPINE",
          font=("Segoe UI", 16, "bold")).pack(pady=(14, 2))
    Label(root, text="Kembalikan file .bin terenkripsi menjadi WAV",
          font=("Segoe UI", 10), fg="gray").pack()

    # ── Pilih file bin ───────────────────────────────────────────────────────
    ff = Frame(root); ff.pack(pady=10)
    bin_path_var = StringVar()
    Label(ff, text="File Audio (.bin):", font=("Segoe UI", 10)).grid(row=0, column=0, padx=4, sticky=E)
    Entry(ff, textvariable=bin_path_var, width=42,
          state='readonly', font=("Segoe UI", 10)).grid(row=0, column=1, padx=4)

    def browse_bin():
        path = filedialog.askopenfilename(
            title="Pilih File Audio Terenkripsi (.bin)",
            filetypes=[("Binary File", "*.bin"), ("All Files", "*.*")])
        if not path: return
        bin_path_var.set(path)
        btn_dec.config(state=NORMAL)

    Button(ff, text="Browse…", font=("Segoe UI", 9), command=browse_bin).grid(row=0, column=2, padx=4)

    # ── Mode dekripsi ────────────────────────────────────────────────────────
    mode_var = StringVar(value="mosipine")
    mf = Frame(root); mf.pack(pady=6)
    Label(mf, text="Mode:", font=("Segoe UI", 10, "bold")).pack(side=LEFT, padx=10)
    for txt, val in [("MO-SiPINE","mosipine"), ("Sine Only","sine"), ("PWLCM Only","pwlcm")]:
        Radiobutton(mf, text=txt, variable=mode_var,
                    value=val, font=("Segoe UI", 10)).pack(side=LEFT, padx=8)

    # ── Parameter kunci ──────────────────────────────────────────────────────
    pf = LabelFrame(root, text=" Parameter Kunci (harus sama dengan enkripsi) ", font=("Segoe UI", 10, "bold"))
    pf.pack(fill="x", padx=40, pady=6)

    param_vars = {k: StringVar() for k in ('x1', 'x2', 'p', 'beta')}

    def load_key_from_file():
        path = filedialog.askopenfilename(
            title="Pilih AI_Key_Report.txt",
            filetypes=[("Text File", "*.txt"), ("All Files", "*.*")])
        if not path: return
        try:
            with open(path, 'r', encoding="utf-8") as f:
                content = f.read()
            for line in content.splitlines():
                if line.startswith("Mode Enkripsi :"):
                    mode_var.set(line.split(":")[-1].strip().lower())
            for key in ('x1', 'x2', 'p', 'beta'):
                for line in content.splitlines():
                    if line.strip().startswith(f"{key} ") or line.strip().startswith(f"{key}="):
                        val = line.split("=")[-1].strip()
                        param_vars[key].set(val)
            messagebox.showinfo("Berhasil", "Key berhasil dimuat!", parent=root)
        except Exception as e:
            messagebox.showerror("Error", f"Gagal membaca key:\n{e}", parent=root)

    Button(pf, text="📂 Muat Otomatis dari AI_Key_Report.txt",
           font=("Segoe UI", 10, "bold"), bg="#4a90d9", fg="white",
           command=load_key_from_file, cursor="hand2").grid(
               row=0, column=0, columnspan=4, pady=(10, 5), padx=10, sticky=E+W)

    labels_cfg = [("x1", 1, 0), ("x2", 1, 2), ("p", 2, 0), ("β (beta)", 2, 2)]
    widgets_dec = {}
    for lbl, r, c in labels_cfg:
        key = lbl.replace("β (beta)", "beta")
        l_w = Label(pf, text=f"{lbl}:", font=("Segoe UI", 9))
        l_w.grid(row=r, column=c, padx=10, pady=5, sticky=E)
        e_w = Entry(pf, textvariable=param_vars[key], width=18, font=("Segoe UI", 10))
        e_w.grid(row=r, column=c+1, padx=5, pady=5)
        widgets_dec[key] = (l_w, e_w)

    def toggle_fields(*args):
        for k in ('p', 'beta'):
            widgets_dec[k][0].grid(); widgets_dec[k][1].grid()
        m = mode_var.get()
        if m == "sine":
            widgets_dec['p'][0].grid_remove(); widgets_dec['p'][1].grid_remove()
        elif m == "pwlcm":
            widgets_dec['beta'][0].grid_remove(); widgets_dec['beta'][1].grid_remove()
    mode_var.trace_add("write", toggle_fields)
    toggle_fields()

    # ── Progress & status ────────────────────────────────────────────────────
    progress = ttk.Progressbar(root, orient=HORIZONTAL, length=520, mode='determinate')
    progress.pack(pady=10)
    status_var = StringVar(value="Status: Pilih file .bin dan muat parameter kunci…")
    Label(root, textvariable=status_var, font=("Segoe UI", 9),
          fg="#00529b", wraplength=560).pack()

    # ── Tombol dekripsi ──────────────────────────────────────────────────────
    btn_frame = Frame(root); btn_frame.pack(pady=10)
    _out_holder = [None]

    btn_dec = Button(btn_frame, text="🔓 Dekripsi Audio",
                     font=("Segoe UI", 11, "bold"), bg="#f0ad4e", fg="white",
                     activebackground="#eea236", padx=15, pady=8,
                     state=DISABLED, cursor="hand2")
    btn_dec.grid(row=0, column=0, padx=10)

    btn_save = Button(btn_frame, text="⬇️ Simpan .wav",
                      font=("Segoe UI", 11, "bold"), bg="#5bc0de", fg="white",
                      activebackground="#31b0d5", padx=15, pady=8,
                      state=DISABLED, cursor="hand2")
    btn_save.grid(row=0, column=1, padx=10)

    def save_wav():
        src = _out_holder[0]
        if not src or not os.path.exists(src):
            messagebox.showwarning("Peringatan", "File belum tersedia.", parent=root); return
        dst = filedialog.asksaveasfilename(
            title="Simpan Audio Terdekripsi",
            defaultextension=".wav",
            initialfile="audio_terdekripsi.wav",
            filetypes=[("WAV File", "*.wav"), ("All Files", "*.*")])
        if dst:
            import shutil; shutil.copy2(src, dst)
            messagebox.showinfo("Berhasil", f"File disimpan ke:\n{dst}", parent=root)
    btn_save.config(command=save_wav)

    def proses_dekripsi():
        b_path = bin_path_var.get()
        if not b_path: return
        try:
            float_params = {k: float(param_vars[k].get()) for k in ('x1','x2','p','beta')
                            if param_vars[k].get().strip()}
            if 'p' not in float_params: float_params['p'] = 0.25
        except ValueError:
            messagebox.showerror("Error", "Parameter tidak valid!", parent=root); return

        mode = mode_var.get()
        btn_dec.config(state=DISABLED)
        progress['value'] = 0

        def run():
            try:
                from audio_core import decrypt_audio
                os.makedirs("Tempat_gambar", exist_ok=True)
                out_wav = os.path.join("Tempat_gambar", "audio_terdekripsi.wav")
                status_var.set("Status: [AUDIO] Mendekripsi audio…")
                root.update_idletasks()
                decrypt_audio(b_path, out_wav, mode, float_params)
                progress['value'] = 100
                _out_holder[0] = out_wav
                status_var.set(f"Status: [OK] Selesai! → {os.path.basename(out_wav)}")
                btn_save.config(state=NORMAL)
                if on_done: on_done()
                messagebox.showinfo("Berhasil",
                    f"Dekripsi audio selesai!\nOutput: {out_wav}", parent=root)
            except Exception as e:
                status_var.set(f"Status: [ERROR] {e}")
                messagebox.showerror("Error", str(e), parent=root)
            finally:
                btn_dec.config(state=NORMAL)

        import threading
        threading.Thread(target=run, daemon=True).start()

    btn_dec.config(command=proses_dekripsi)


# ═══════════════════════════════════════════════════════════════════════════════
# UJI KUALITAS AUDIO — SNR, PSNR, MSE, KORELASI, ENTROPI, WAVEFORM
# ═══════════════════════════════════════════════════════════════════════════════

def uji_kualitas_audio(session=None, parent=None):
    """
    Window: Input File Uji Kualitas Audio Enkripsi MO-SiPINE.
    """
    import io
    import scipy.io.wavfile as wavfile
    import shutil

    win_input = Toplevel(parent)
    win_input.title("Input File Uji Kualitas Audio")
    win_input.geometry("750x300")
    win_input.resizable(False, False)

    Label(win_input, text="Uji Kualitas Audio — MO-SiPINE", font=("Segoe UI", 16, "bold")).pack(pady=(15, 5))
    Label(win_input, text="Pilih file WAV untuk diuji, atau unduh (download) file otomatis dari sesi sebelumnya.", fg="gray").pack(pady=(0, 15))

    TEMPDIR = "Tempat_gambar"
    default_asli = os.path.abspath(os.path.join(TEMPDIR, "audio_asli.wav"))
    default_noise = os.path.abspath(os.path.join(TEMPDIR, "audio_noise.wav"))
    default_dec = os.path.abspath(os.path.join(TEMPDIR, "audio_terdekripsi.wav"))

    var_asli = StringVar(value=default_asli if os.path.exists(default_asli) else "")
    var_noise = StringVar(value=default_noise if os.path.exists(default_noise) else "")
    var_dec = StringVar(value=default_dec if os.path.exists(default_dec) else "")

    frm = Frame(win_input)
    frm.pack(pady=5, padx=20, fill="x")

    def make_row(row, label_text, var, default_name):
        Label(frm, text=label_text, font=("Segoe UI", 10, "bold")).grid(row=row, column=0, sticky="w", pady=8)
        Entry(frm, textvariable=var, width=40, font=("Segoe UI", 10)).grid(row=row, column=1, padx=10, pady=8)
        
        def _browse():
            p = filedialog.askopenfilename(filetypes=[("WAV Audio", "*.wav"), ("All Files", "*.*")])
            if p: var.set(p)
        Button(frm, text="Browse", command=_browse, bg="#e0e0e0").grid(row=row, column=2, padx=5, pady=8)
        
        def _download():
            src = var.get()
            if not src or not os.path.exists(src):
                messagebox.showwarning("Peringatan", "File tidak ditemukan untuk di-download!", parent=win_input)
                return
            dst = filedialog.asksaveasfilename(defaultextension=".wav", initialfile=default_name, filetypes=[("WAV Audio", "*.wav")])
            if dst:
                shutil.copy2(src, dst)
                messagebox.showinfo("Berhasil", f"File berhasil didownload ke:\n{dst}", parent=win_input)
        Button(frm, text="⬇️ Download", command=_download, bg="#5bc0de", fg="white").grid(row=row, column=3, pady=8)

    make_row(0, "1. Audio Asli:", var_asli, "audio_asli_download.wav")
    make_row(1, "2. Audio Terenkripsi (Noise):", var_noise, "audio_noise_download.wav")
    make_row(2, "3. Audio Terdekripsi:", var_dec, "audio_terdekripsi_download.wav")

    def run_uji():
        PATH_ASLI = var_asli.get()
        PATH_NOISE = var_noise.get()
        PATH_DEC = var_dec.get()

        if not PATH_ASLI or not os.path.exists(PATH_ASLI):
            messagebox.showerror("Error", "File Audio Asli harus diisi dan valid!", parent=win_input)
            return
            
        win_input.destroy()

        # ── Load audio data ──────────────────────────────────────────────────────
        def load_mono_float(path):
            try:
                rate, data = wavfile.read(path)
                if data.dtype == np.int16:
                    data = data.astype(np.float64) / 32768.0
                elif data.dtype == np.int32:
                    data = data.astype(np.float64) / 2147483648.0
                else:
                    data = data.astype(np.float64)
                if data.ndim == 2:
                    data = data[:, 0]
                return rate, data
            except Exception as e:
                return None, None

        rate_a, arr_asli  = load_mono_float(PATH_ASLI)
        rate_n, arr_noise = load_mono_float(PATH_NOISE) if os.path.exists(PATH_NOISE) else (None, None)
        rate_d, arr_dec   = load_mono_float(PATH_DEC)   if os.path.exists(PATH_DEC)   else (None, None)

        if arr_asli is None:
            messagebox.showerror("Error", "Gagal membaca Audio Asli.", parent=parent)
            return

        # ── Hitung metrik ────────────────────────────────────────────────────────
        def _entropy_bits(arr):
            hist, _ = np.histogram(arr, bins=256, range=(-1.0, 1.0))
            hist = hist[hist > 0].astype(np.float64)
            prob = hist / hist.sum()
            return -np.sum(prob * np.log2(prob))

        def _snr_db(ref, sig):
            noise = ref - sig[:len(ref)] if len(sig) >= len(ref) else ref[:len(sig)] - sig
            ref_c = ref[:len(noise)]
            p_sig = np.mean(ref_c ** 2)
            p_noi = np.mean(noise ** 2)
            if p_noi < 1e-15:
                return float('inf')
            return 10.0 * np.log10(p_sig / p_noi)

        def _psnr(ref, sig):
            n = min(len(ref), len(sig))
            mse = np.mean((ref[:n] - sig[:n]) ** 2)
            if mse < 1e-15:
                return float('inf')
            return 20.0 * np.log10(1.0 / np.sqrt(mse))

        def _mse(ref, sig):
            n = min(len(ref), len(sig))
            return np.mean((ref[:n] - sig[:n]) ** 2)

        def _pearson(ref, sig):
            n = min(len(ref), len(sig))
            if n < 2:
                return 0.0
            a, b = ref[:n], sig[:n]
            num = np.mean((a - a.mean()) * (b - b.mean()))
            den = a.std() * b.std()
            return num / den if den > 1e-15 else 0.0

        ent_asli  = _entropy_bits(arr_asli)
        ent_noise = _entropy_bits(arr_noise) if arr_noise is not None else None
        ent_dec   = _entropy_bits(arr_dec)   if arr_dec   is not None else None

        snr_enc  = _snr_db(arr_asli, arr_noise)  if arr_noise is not None else None
        psnr_enc = _psnr(arr_asli, arr_noise)    if arr_noise is not None else None
        mse_enc  = _mse(arr_asli, arr_noise)     if arr_noise is not None else None
        corr_enc = _pearson(arr_asli, arr_noise) if arr_noise is not None else None

        snr_dec  = _snr_db(arr_asli, arr_dec)  if arr_dec is not None else None
        psnr_dec = _psnr(arr_asli, arr_dec)    if arr_dec is not None else None
        mse_dec  = _mse(arr_asli, arr_dec)     if arr_dec is not None else None
        corr_dec = _pearson(arr_asli, arr_dec) if arr_dec is not None else None

        # ── Bangun window Hasil ──────────────────────────────────────────────────
        win = Toplevel(parent)
        win.title("Hasil Uji Kualitas Audio — MO-SiPINE")
        win.geometry("960x820")
        win.resizable(True, True)

        Label(win, text="Hasil Uji Kualitas Audio  —  MO-SiPINE", font=("Segoe UI", 16, "bold")).pack(pady=(10, 2))
        Label(win, text="Perbandingan: Audio Asli | Audio Noise (Terenkripsi) | Audio Terdekripsi", font=("Segoe UI", 10), fg="gray").pack()

        try:
            fig, axes = plt.subplots(3, 1, figsize=(10, 4.2), dpi=88, facecolor='#f4f7fa')
            fig.subplots_adjust(hspace=0.55, left=0.07, right=0.97, top=0.91, bottom=0.10)
            N_PLOT = 8000

            data_plot = [
                (arr_asli,  "Audio Asli",            "#2a6bc4"),
                (arr_noise, "Audio Terenkripsi (Noise)", "#e05c2a"),
                (arr_dec,   "Audio Terdekripsi",      "#2aad60"),
            ]

            for i, (arr, lbl, col) in enumerate(data_plot):
                ax = axes[i]
                ax.set_facecolor('#edf2f7')
                if arr is not None:
                    seg = arr[:N_PLOT]
                    t = np.linspace(0, len(seg) / (rate_a or 44100), len(seg))
                    ax.plot(t, seg, color=col, linewidth=0.6)
                    ax.set_ylim(-1.1, 1.1)
                else:
                    ax.text(0.5, 0.5, "(tidak tersedia)", ha='center', va='center', transform=ax.transAxes, color='gray')
                ax.set_title(lbl, fontsize=9, fontweight='bold', color='#253555', pad=3)
                ax.set_ylabel("Amp", fontsize=7, color='#556')
                ax.tick_params(labelsize=7)
                ax.grid(True, linewidth=0.4, alpha=0.5)

            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=88)
            buf.seek(0)
            plt.close(fig)
            img_ph = PIL.ImageTk.PhotoImage(PIL.Image.open(buf))
            lbl_plot = Label(win, image=img_ph, bg='#f4f7fa')
            lbl_plot.image = img_ph
            lbl_plot.pack(pady=6)
        except Exception as e:
            Label(win, text=f"[Gagal render waveform: {e}]", fg="red").pack()

        frm_tbl = Frame(win)
        frm_tbl.pack(pady=4, padx=20, fill="x")

        def fmt(v, prec=6, suffix=""):
            if v is None: return "—"
            if v == float('inf'): return "∞"
            return f"{v:.{prec}f}{suffix}"

        headers = ["Metrik", "Asli vs Terenkripsi", "Asli vs Terdekripsi", "Keterangan"]
        rows = [
            ("SNR (dB)",         fmt(snr_enc, 4),  fmt(snr_dec, 4), "Enkripsi: rendah ✓ | Dekripsi: tinggi ✓"),
            ("PSNR (dB)",        fmt(psnr_enc, 4), fmt(psnr_dec, 4), "Enkripsi: rendah ✓ | Dekripsi: tinggi ✓"),
            ("MSE",              fmt(mse_enc, 6),  fmt(mse_dec, 8), "Enkripsi: tinggi ✓ | Dekripsi: ≈0 ✓"),
            ("Korelasi Pearson", fmt(corr_enc, 6), fmt(corr_dec, 6), "Enkripsi: ≈0 ✓ | Dekripsi: ≈1 ✓"),
            ("Entropi Asli",     fmt(ent_asli, 5), "—", "Ideal ≈ 4–5 bit (audio normal)"),
            ("Entropi Noise",    fmt(ent_noise, 5) if ent_noise is not None else "—", "—", "Ideal ≈ 8 bit (noise seragam)"),
            ("Entropi Dekripsi", "—", fmt(ent_dec, 5) if ent_dec is not None else "—", "Harus ≈ Entropi Asli"),
        ]

        col_widths = [22, 22, 22, 38]
        for ci, h in enumerate(headers):
            Label(frm_tbl, text=h, font=("Segoe UI", 10, "bold"), bg="#dce4ed", fg="#253555", bd=1, relief="ridge", width=col_widths[ci], pady=3).grid(row=0, column=ci, sticky="nsew")

        for ri, row in enumerate(rows):
            bg = "#f2f5f8" if ri % 2 == 0 else "white"
            for ci, val in enumerate(row):
                Label(frm_tbl, text=val, font=("Segoe UI", 10), bg=bg, bd=1, relief="ridge", width=col_widths[ci], pady=2).grid(row=ri+1, column=ci, sticky="nsew")

        Button(win, text="Tutup", font=("Segoe UI", 10), bg="#d8e2ec", activebackground="#b8ccdc", padx=20, pady=4, cursor="hand2", command=win.destroy).pack(pady=5)

    Button(win_input, text="📊 Proses Uji Kualitas Audio", font=("Segoe UI", 12, "bold"), bg="#4a90d9", fg="white", activebackground="#357abd", padx=20, pady=10, cursor="hand2", command=run_uji).pack(pady=10)

