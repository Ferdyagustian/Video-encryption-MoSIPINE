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
from video_core import encrypt_video_to_binary, decrypt_binary_to_video, extract_sample_frames, extract_single_frame_from_bin
from ai_optimizer import predict_best_keys

PREVIEW_SIZE = (280, 180)  # Ukuran thumbnail preview

def _create_placeholder():
    """Buat gambar dummy dengan ukuran piksel agar Label tidak meledak ukurannya."""
    img = PIL.Image.new('RGB', PREVIEW_SIZE, color='#d0d0d0')
    return PIL.ImageTk.PhotoImage(img)

class VideoPlayer:
    """Kelas untuk mengelola pemutaran Video (.mp4 dkk) atau Biner (.bin) di Tkinter."""
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
            
        if path.endswith(".bin"):
            self.is_bin = True
            try:
                with open(self.source_path, 'rb') as f:
                    hdr = f.read(16)
                    if len(hdr) == 16:
                        w, h, _, fps = struct.unpack('<IIIf', hdr)
                        self.bin_w, self.bin_h, self.bin_fps = w, h, fps
                        raw = f.read(w * h * 3)
                        if len(raw) == w * h * 3:
                            frame = np.frombuffer(raw, dtype=np.uint8).reshape((h, w, 3))
                            self._show_frame(frame)
            except Exception as e:
                print("Error loading bin frame:", e)
        else:
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
                    self.bin_file.read(16) # Skip header
            else:
                if self.cap is None or not self.cap.isOpened():
                    self.cap = cv2.VideoCapture(self.source_path)
            self._play_loop()

    def replay(self):
        if not self.source_path: return
        
        if self.is_bin:
            if self.bin_file and not self.bin_file.closed:
                self.bin_file.seek(16)
            else:
                self.bin_file = open(self.source_path, 'rb')
                self.bin_file.seek(16)
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
    root.geometry("800x670")
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
    for txt, val in [("MO-SiPINE","mosipine"), ("Sine Only","sine"), ("PWLCM Only","pwlcm")]:
        Radiobutton(mf, text=txt, variable=mode_var,
                    value=val, font=("Segoe UI", 10)).pack(side=LEFT, padx=10)

    # ── Parameter Box ────────────────────────────────────────────────
    param_frame = LabelFrame(root, text=" Parameter Terbaik (Hasil Prediksi AI) ", font=("Segoe UI", 10, "bold"))
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
    btn_ai.grid(row=0, column=0, padx=10)

    btn_save_key = Button(btn_frame, text="💾 Simpan Key AI",
                          font=("Segoe UI", 11, "bold"), bg="#5cb85c", fg="white", 
                          activebackground="#4cae4c", padx=15, pady=8,
                          state=DISABLED, cursor="hand2")
    btn_save_key.grid(row=0, column=1, padx=10)

    btn_save_bin = Button(btn_frame, text="⬇️ Unduh Video Biner (.bin)",
                          font=("Segoe UI", 11, "bold"), bg="#5bc0de", fg="white", 
                          activebackground="#31b0d5", padx=15, pady=8,
                          state=DISABLED, cursor="hand2")
    btn_save_bin.grid(row=0, column=2, padx=10)

    _key_path_holder = [None]
    _bin_path_holder = [None]

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
            title="Simpan File Video Biner Terenkripsi",
            defaultextension=".bin",
            initialfile="video_rahasia.bin",
            filetypes=[("Binary File", "*.bin"), ("All Files", "*.*")])
        if dst:
            import shutil
            shutil.copy2(src, dst)
            messagebox.showinfo("Berhasil", f"Video sukses disimpan ke:\n{dst}")

    btn_save_bin.config(command=save_bin)

    def proses_ai_dan_enkripsi():
        v_path = video_path_var.get()
        if not v_path: return
        mode = mode_var.get()
        
        # Hentikan semua pemutaran jika ada
        player_in.stop()
        player_out.stop()
        
        btn_ai.config(state=DISABLED)
        btn_save_key.config(state=DISABLED)
        progress['value'] = 0

        def run():
            try:
                # FASE 1: AI
                status_var.set("Status: 🤖 AI sedang memprediksi kunci terbaik (10 detik)...")
                root.update()
                best_keys, best_entropy = predict_best_keys(mode=mode, timeout=10.0)

                param_vars['x1'].set(f"{best_keys.get('x1', 0):.10f}")
                param_vars['x2'].set(f"{best_keys.get('x2', 0):.10f}")
                param_vars['p'].set(f"{best_keys.get('p', 0.25):.10f}")
                param_vars['beta'].set(f"{best_keys.get('beta', 0):.10f}")
                param_vars['entropy'].set(f"{best_entropy:.8f}")

                os.makedirs("Tempat_gambar", exist_ok=True)
                key_path = os.path.join("Tempat_gambar", "AI_Key_Report.txt")
                with open(key_path, "w", encoding="utf-8") as f:
                    f.write("╔══════════════════════════════════════════╗\n")
                    f.write("║       AI KEY REPORT — MO-SiPINE          ║\n")
                    f.write("╚══════════════════════════════════════════╝\n\n")
                    f.write(f"Mode Enkripsi : {mode.upper()}\n")
                    f.write(f"Entropy Score : {best_entropy:.10f}  (ideal: 8.0)\n\n")
                    f.write("──── SALIN NILAI INI UNTUK DEKRIPSI ────\n")
                    f.write(f"x1   = {best_keys.get('x1', 0):.10f}\n")
                    f.write(f"x2   = {best_keys.get('x2', 0):.10f}\n")
                    f.write(f"p    = {best_keys.get('p', 0.25):.10f}\n")
                    f.write(f"beta = {best_keys.get('beta', 0):.10f}\n")
                _key_path_holder[0] = key_path

                # FASE 2: Enkripsi
                status_var.set("Status: 🔒 Mengenkripsi frame video menjadi biner...")
                root.update_idletasks()
                out_bin = os.path.join("Tempat_gambar", "video_terenkripsi.bin")
                # Gunakan teks di layar yang dipotong 10 desimal persis seperti .txt agar keystream akurat
                float_params = {k: float(param_vars[k].get()) for k in ('x1','x2','p','beta')}

                start_time = time.time()
                def cb(curr, total):
                    progress['value'] = (curr / total) * 100
                    elapsed = time.time() - start_time
                    if curr > 0 and elapsed > 0:
                        fps_proc = curr / elapsed
                        rem_frames = total - curr
                        eta = int(rem_frames / fps_proc) if fps_proc > 0 else 0
                        mins, secs = divmod(eta, 60)
                        eta_str = f"{mins}m {secs}s" if mins > 0 else f"{secs} dtk"
                        status_var.set(f"Status: 🔒 Enkripsi frame {curr}/{total} - Estimasi Sisa: {eta_str}")
                    else:
                        status_var.set(f"Status: 🔒 Enkripsi frame {curr}/{total}...")
                    root.update_idletasks()

                encrypt_video_to_binary(v_path, out_bin, mode, float_params, cb)

                # FASE 3: Preview Output
                status_var.set("Status: 📸 Memuat preview frame terenkripsi...")
                root.update_idletasks()
                
                # Load the newly created .bin wrapper into Player Kanan
                player_out.load_source(out_bin)
                player_out.lbl_text.config(text="")
                _bin_path_holder[0] = out_bin

                durasi = time.time() - start_time
                mnt, dtk = divmod(int(durasi), 60)
                dur_str = f"{mnt} menit {dtk} detik" if mnt else f"{dtk} detik"
                status_var.set(f"Status: ✅ Selesai! Waktu Enkripsi: {dur_str}")
                btn_save_key.config(state=NORMAL)
                btn_save_bin.config(state=NORMAL)
                # Simpan ke session
                if session is not None:
                    session['video_asli'] = v_path
                    session['video_bin']  = out_bin
                    session['mode']       = mode
                    session['kunci']      = {k: float(param_vars[k].get()) for k in ('x1','x2','p','beta')}
                if on_done:
                    on_done()
                messagebox.showinfo("Berhasil", f"Enkripsi Video Selesai!\nWaktu: {dur_str}\nSilakan simpan Key AI dan Video Biner.")
            except Exception as e:
                status_var.set(f"Status: ❌ Error: {e}")
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

    Label(root, text="Dekripsi Biner → Video (.avi)",
          font=("Segoe UI", 16, "bold")).pack(pady=(12, 4))
    Label(root, text="Muat kunci dari file AI_Key_Report.txt untuk mendekripsi secara akurat",
          font=("Segoe UI", 10), fg="gray").pack()

    # ── Pilih file ───────────────────────────────────────────────────
    ff = Frame(root)
    ff.pack(pady=10)
    bin_path_var = StringVar()
    Label(ff, text="File .bin :", font=("Segoe UI", 10)).grid(row=0, column=0, padx=4)
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
    Label(kanan, text="Video Hasil Dekripsi (.avi)", font=("Segoe UI", 10, "bold")).pack(pady=5)
    player_dec = VideoPlayer(kanan)

    def browse_bin():
        path = filedialog.askopenfilename(
            title="Pilih File Binary Terenkripsi",
            filetypes=[("Binary File", "*.bin"), ("All Files", "*.*")])
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
    
    btn_save_avi = Button(btn_frame2, text="⬇️ Unduh Video (.avi)",
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
            defaultextension=".avi",
            initialfile="video_terdekripsi.avi",
            filetypes=[("Video File", "*.avi"), ("All Files", "*.*")])
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
                status_var.set("Status: 🔓 Menyusun video asli...")
                root.update()
                out_vid = os.path.join("Tempat_gambar", "video_terdekripsi.avi")

                start_time = time.time()
                def cb(curr, total):
                    progress['value'] = (curr / total) * 100
                    elapsed = time.time() - start_time
                    if curr > 0 and elapsed > 0:
                        fps_proc = curr / elapsed
                        rem_frames = total - curr
                        eta = int(rem_frames / fps_proc) if fps_proc > 0 else 0
                        mins, secs = divmod(eta, 60)
                        eta_str = f"{mins}m {secs}s" if mins > 0 else f"{secs} dtk"
                        status_var.set(f"Status: 🔓 Restorasi frame {curr}/{total} - Estimasi Sisa: {eta_str}")
                    else:
                        status_var.set(f"Status: 🔓 Restorasi frame {curr}/{total}...")
                    root.update_idletasks()

                decrypt_binary_to_video(b_path, out_vid, mode, float_params, cb)

                player_dec.load_source(out_vid)
                player_dec.lbl_text.config(text="")
                _avi_path_holder[0] = out_vid

                durasi = time.time() - start_time
                mnt, dtk = divmod(int(durasi), 60)
                dur_str = f"{mnt} menit {dtk} detik" if mnt else f"{dtk} detik"
                status_var.set(f"Status: ✅ Selesai! Waktu Dekripsi: {dur_str}")
                btn_save_avi.config(state=NORMAL)
                if session is not None:
                    session['video_bin'] = b_path
                if on_done:
                    on_done()
                messagebox.showinfo("Berhasil", f"Dekripsi Selesai!\nWaktu: {dur_str}\nSilakan simpan (unduh) Video utuh Anda.")
            except Exception as e:
                status_var.set(f"Status: ❌ Error: {e}")
                messagebox.showerror("Error", str(e))
            finally:
                btn_dec.config(state=NORMAL)

        threading.Thread(target=run, daemon=True).start()

    btn_dec.config(command=proses_dekripsi)


# ═══════════════════════════════════════════════════════════════════════════════
# FUNGSI UJI KUALITAS BERBASIS FRAME VIDEO
# ═══════════════════════════════════════════════════════════════════════════════

def _ujiuniform(arr_flat):
    """Chi-Square uji uniform distribusi piksel."""
    E = len(arr_flat) / 256
    counts = collections.Counter(arr_flat.tolist())
    chi2 = sum(((counts.get(i, 0) - E) ** 2) / E for i in range(256))
    return chi2

def _pearson_rgb(arr2d, direction="hor"):
    """Hitung korelasi Pearson per channel arah horisontal/vertikal/diagonal."""
    h, w = arr2d.shape
    if direction == "hor":
        x = arr2d[:, :-1].flatten()
        y = arr2d[:, 1:].flatten()
    elif direction == "ver":
        x = arr2d[:-1, :].flatten()
        y = arr2d[1:, :].flatten()
    else:  # diagonal
        x = arr2d[:-1, :-1].flatten()
        y = arr2d[1:, 1:].flatten()
    if len(x) < 2:
        return 0.0
    r, _ = pearsonr(x.astype(float), y.astype(float))
    return r

def _entropy_channel(arr_flat):
    return skimage.measure.shannon_entropy(arr_flat)

def _psnr_mse(arr1, arr2):
    """MSE dan PSNR antara dua array uint8."""
    mse = np.mean((arr1.astype(float) - arr2.astype(float)) ** 2)
    if mse == 0:
        return float('inf'), 0.0
    psnr = 20 * math.log10(255.0 / math.sqrt(mse))
    return psnr, mse

def _npcr_uaci(arr1, arr2):
    """NPCR (%) dan UACI (%) antara dua array uint8 RGB."""
    diff = (arr1 != arr2).astype(float)
    npcr = diff.mean() * 100.0
    uaci = (np.abs(arr1.astype(float) - arr2.astype(float)) / 255.0).mean() * 100.0
    return npcr, uaci


def pencet_uji_video(session, frame_key, frame_ratio, label, parent=None):
    """
    Jendela Uji Kualitas Citra dari frame video.
    - session: dict SESSION berisi path video_asli, video_bin, kunci, mode
    - frame_key: kunci SESSION untuk path PNG frame plain ('frame_awal','frame_tengah','frame_akhir')
    - frame_ratio: float 0-1, posisi frame di video (0.10, 0.50, 0.90)
    - label: string deskripsi frame untuk judul
    """
    win = Toplevel(parent)
    win.title(f"Uji Kualitas Citra — Frame {label}")
    win.geometry("860x680")
    win.resizable(True, True)
    win.configure(bg="#f0f4f8")

    BG_W  = "#f0f4f8"
    FNT_H = ("Segoe UI", 13, "bold")
    FNT_N = ("Segoe UI", 10)
    FNT_S = ("Segoe UI", 9)

    # ── Header ────────────────────────────────────────────────────────────
    tk_lbl = Label(win, text=f"Uji Kualitas Citra — Frame {label}",
                   font=FNT_H, bg=BG_W, fg="#2c3e5c")
    tk_lbl.pack(pady=(14, 2))
    Label(win, text="Frame asli (plain) vs frame terenkripsi (cipher) dari video",
          font=FNT_S, bg=BG_W, fg="gray").pack()

    # ── Pilih File (jika belum ada di session) ────────────────────────────
    frm_pick = Frame(win, bg=BG_W)
    frm_pick.pack(pady=6, padx=20, fill="x")

    vid_var = StringVar(value=session.get("video_asli") or "")
    bin_var = StringVar(value=session.get("video_bin")  or "")

    def browse_vid():
        p = filedialog.askopenfilename(title="Pilih Video Asli",
            filetypes=[("Video", "*.mp4 *.avi *.mov *.mkv"), ("All", "*.*")])
        if p:
            vid_var.set(p)
            session["video_asli"] = p

    def browse_bin():
        p = filedialog.askopenfilename(title="Pilih File .bin Terenkripsi",
            filetypes=[("Binary", "*.bin"), ("All", "*.*")])
        if p:
            bin_var.set(p)
            session["video_bin"] = p

    Label(frm_pick, text="Video Asli:", font=FNT_S, bg=BG_W).grid(row=0, column=0, sticky="e", padx=4)
    Entry(frm_pick, textvariable=vid_var, width=52, state="readonly",
          font=FNT_S).grid(row=0, column=1, padx=4)
    Button(frm_pick, text="Browse…", font=FNT_S, command=browse_vid,
           bd=1, relief="ridge", bg="#dce4ed", cursor="hand2").grid(row=0, column=2)

    Label(frm_pick, text="File .bin :", font=FNT_S, bg=BG_W).grid(row=1, column=0, sticky="e", padx=4, pady=3)
    Entry(frm_pick, textvariable=bin_var, width=52, state="readonly",
          font=FNT_S).grid(row=1, column=1, padx=4)
    Button(frm_pick, text="Browse…", font=FNT_S, command=browse_bin,
           bd=1, relief="ridge", bg="#dce4ed", cursor="hand2").grid(row=1, column=2)

    # ── Preview dua frame (plain vs cipher) ───────────────────────────────
    frm_prev = Frame(win, bg=BG_W)
    frm_prev.pack(pady=6)

    SZ_PREV = (200, 140)
    dummy_img = PIL.Image.new("RGB", SZ_PREV, "#c8d6e0")
    dummy_ph  = PIL.ImageTk.PhotoImage(dummy_img)

    lbl_plain  = Label(frm_prev, image=dummy_ph, bg=BG_W)
    lbl_plain._ph = dummy_ph
    lbl_plain.grid(row=0, column=0, padx=20)
    Label(frm_prev, text="Frame Plain (Asli)", font=FNT_S, bg=BG_W).grid(row=1, column=0)

    lbl_cipher = Label(frm_prev, image=dummy_ph, bg=BG_W)
    lbl_cipher._ph = dummy_ph
    lbl_cipher.grid(row=0, column=1, padx=20)
    Label(frm_prev, text="Frame Cipher (Terenkripsi)", font=FNT_S, bg=BG_W).grid(row=1, column=1)

    def _show_preview(path, lbl_widget):
        try:
            img = PIL.Image.open(path).convert("RGB").resize(SZ_PREV, PIL.Image.LANCZOS)
            ph  = PIL.ImageTk.PhotoImage(img)
            lbl_widget.config(image=ph)
            lbl_widget._ph = ph
        except Exception:
            pass

    # ── Progress bar (Fase 4.5) ───────────────────────────────────────────
    prog = ttk.Progressbar(win, orient=HORIZONTAL, length=700, mode="determinate")
    prog.pack(pady=4, padx=20)
    status_uji = StringVar(value="Siap. Tekan 'Mulai Uji' untuk memulai.")
    Label(win, textvariable=status_uji, font=FNT_S, bg=BG_W, fg="#00529b").pack()

    # ── ScrolledText Hasil ────────────────────────────────────────────────
    txt = scrolledtext.ScrolledText(win, width=100, height=12, font=("Consolas", 9),
                                    bg="#1e2a38", fg="#c8e6c9", insertbackground="white")
    txt.pack(padx=14, pady=6, fill="both", expand=True)

    hasil_cache = {}  # simpan hasil untuk ekspor

    # ── Tombol bawah ──────────────────────────────────────────────────────
    frm_btn = Frame(win, bg=BG_W)
    frm_btn.pack(pady=8)

    def export_laporan():
        if not hasil_cache:
            messagebox.showwarning("Peringatan", "Jalankan uji terlebih dahulu.", parent=win)
            return
        dst = filedialog.asksaveasfilename(
            title="Simpan Laporan Uji Kualitas",
            defaultextension=".txt",
            initialfile=f"Laporan_Uji_Frame_{label.replace(' ','_').replace('~','').replace('%','')}.txt",
            filetypes=[("Text File", "*.txt"), ("All Files", "*.*")])
        if not dst:
            return
        with open(dst, "w", encoding="utf-8") as f:
            f.write(txt.get("1.0", "end"))
        messagebox.showinfo("Berhasil", f"Laporan disimpan:\n{dst}", parent=win)

    btn_uji = Button(frm_btn, text="▶ Mulai Uji", font=("Segoe UI", 10, "bold"),
                     bg="#4a90d9", fg="white", activebackground="#357abd",
                     padx=14, pady=6, bd=1, relief="ridge", cursor="hand2")
    btn_uji.grid(row=0, column=0, padx=10)

    btn_exp = Button(frm_btn, text="📄 Ekspor Laporan .txt",
                     font=("Segoe UI", 10, "bold"),
                     bg="#5cb85c", fg="white", activebackground="#4cae4c",
                     padx=14, pady=6, bd=1, relief="ridge", cursor="hand2",
                     command=export_laporan)
    btn_exp.grid(row=0, column=1, padx=10)

    Button(frm_btn, text="Tutup", font=FNT_N, bg="#dce4ed", activebackground="#bfcfdf",
           padx=14, pady=6, bd=1, relief="ridge", cursor="hand2",
           command=win.destroy).grid(row=0, column=2, padx=10)

    # ── Logika Uji ────────────────────────────────────────────────────────
    def run_uji():
        vid_path = vid_var.get()
        bin_path = bin_var.get()
        if not vid_path or not os.path.exists(vid_path):
            messagebox.showerror("Error", "Pilih file video asli terlebih dahulu.", parent=win)
            return
        if not bin_path or not os.path.exists(bin_path):
            messagebox.showerror("Error", "Pilih file .bin terlebih dahulu.", parent=win)
            return

        btn_uji.config(state=DISABLED)
        prog["value"] = 0
        txt.config(state=NORMAL)
        txt.delete("1.0", END)
        hasil_cache.clear()

        def _run():
            try:
                steps = 8

                # Step 1: Ekstrak frame plain
                status_uji.set(f"[1/{steps}] Mengekstrak frame plain dari video...")
                prog["value"] = 1 / steps * 100
                win.update_idletasks()

                plain_path = os.path.join("Tempat_gambar", f"uji_plain_{frame_key}.png")
                cap = cv2.VideoCapture(vid_path)
                total_f = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                target_f = max(0, min(int(total_f * frame_ratio), total_f - 1))
                cap.set(cv2.CAP_PROP_POS_FRAMES, target_f)
                ret, frm = cap.read()
                cap.release()
                if not ret:
                    raise Exception("Gagal membaca frame dari video asli.")
                PIL.Image.fromarray(cv2.cvtColor(frm, cv2.COLOR_BGR2RGB)).save(plain_path)
                session[frame_key] = plain_path

                # Step 2: Ekstrak frame cipher dari .bin
                status_uji.set(f"[2/{steps}] Mengekstrak frame cipher dari .bin...")
                prog["value"] = 2 / steps * 100
                win.update_idletasks()

                cipher_path = os.path.join("Tempat_gambar", f"uji_cipher_{frame_key}.png")
                extract_single_frame_from_bin(bin_path, frame_ratio, cipher_path)

                # Tampilkan preview
                _show_preview(plain_path,  lbl_plain)
                _show_preview(cipher_path, lbl_cipher)

                # Buka gambar sebagai numpy array
                im_plain  = PIL.Image.open(plain_path).convert("RGB")
                im_cipher = PIL.Image.open(cipher_path).convert("RGB")

                arr_plain  = np.array(im_plain,  dtype=np.uint8)
                arr_cipher = np.array(im_cipher, dtype=np.uint8)
                H, W, _ = arr_plain.shape

                # Channel arrays flat
                Pr = arr_plain[:,:,0].flatten()
                Pg = arr_plain[:,:,1].flatten()
                Pb = arr_plain[:,:,2].flatten()
                Cr = arr_cipher[:,:,0].flatten()
                Cg = arr_cipher[:,:,1].flatten()
                Cb = arr_cipher[:,:,2].flatten()

                # Step 3: Histogram
                status_uji.set(f"[3/{steps}] Menghitung histogram...")
                prog["value"] = 3 / steps * 100
                win.update_idletasks()

                for channel, data, color, name in [
                    ("R", Pr, "red",   "Plain_R"),
                    ("G", Pg, "green", "Plain_G"),
                    ("B", Pb, "blue",  "Plain_B"),
                    ("R", Cr, "red",   "Cipher_R"),
                    ("G", Cg, "green", "Cipher_G"),
                    ("B", Cb, "blue",  "Cipher_B"),
                ]:
                    fig, ax = plt.subplots(figsize=(4,2.5))
                    ax.hist(data, bins=256, range=(0,255), color=color, alpha=0.8)
                    ax.set_title(f"Histogram {name}")
                    ax.set_xlim(0, 255)
                    fig.tight_layout()
                    fig.savefig(os.path.join("Tempat_gambar", f"hist_{name}.png"), dpi=80)
                    plt.close(fig)

                # Step 4: Korelasi
                status_uji.set(f"[4/{steps}] Menghitung korelasi Pearson...")
                prog["value"] = 4 / steps * 100
                win.update_idletasks()

                def corr_all(arr2d):
                    return {
                        "H": _pearson_rgb(arr2d, "hor"),
                        "V": _pearson_rgb(arr2d, "ver"),
                        "D": _pearson_rgb(arr2d, "dia"),
                    }
                corr_pr = corr_all(arr_plain[:,:,0])
                corr_pg = corr_all(arr_plain[:,:,1])
                corr_pb = corr_all(arr_plain[:,:,2])
                corr_cr = corr_all(arr_cipher[:,:,0])
                corr_cg = corr_all(arr_cipher[:,:,1])
                corr_cb = corr_all(arr_cipher[:,:,2])

                # Step 5: Chi-Square Uniform
                status_uji.set(f"[5/{steps}] Menghitung Chi-Square (Uniform)...")
                prog["value"] = 5 / steps * 100
                win.update_idletasks()

                uni_pr = _ujiuniform(Pr); uni_pg = _ujiuniform(Pg); uni_pb = _ujiuniform(Pb)
                uni_cr = _ujiuniform(Cr); uni_cg = _ujiuniform(Cg); uni_cb = _ujiuniform(Cb)

                # Step 6: Entropi
                status_uji.set(f"[6/{steps}] Menghitung entropi Shannon...")
                prog["value"] = 6 / steps * 100
                win.update_idletasks()

                ent_p = (_entropy_channel(Pr) + _entropy_channel(Pg) + _entropy_channel(Pb)) / 3
                ent_c = (_entropy_channel(Cr) + _entropy_channel(Cg) + _entropy_channel(Cb)) / 3

                # Step 7: PSNR, MSE, NPCR, UACI
                status_uji.set(f"[7/{steps}] Menghitung PSNR, MSE, NPCR, UACI...")
                prog["value"] = 7 / steps * 100
                win.update_idletasks()

                psnr_val, mse_val = _psnr_mse(arr_plain, arr_cipher)
                npcr_val, uaci_val = _npcr_uaci(arr_plain, arr_cipher)

                # Step 8: Tampilkan hasil
                status_uji.set(f"[8/{steps}] Menyusun laporan...")
                prog["value"] = 8 / steps * 100
                win.update_idletasks()

                sep  = "═" * 70
                sep2 = "─" * 70
                lines = [
                    sep,
                    f"  LAPORAN UJI KUALITAS CITRA — FRAME {label.upper()}",
                    f"  Video  : {os.path.basename(vid_path)}",
                    f"  File   : {os.path.basename(bin_path)}",
                    f"  Ukuran : {W} x {H} piksel",
                    sep,
                    "",
                    "  ┌── HISTOGRAM ──────────────────────────────────────────────────┐",
                    "  │ Disimpan di folder Tempat_gambar/hist_*.png                   │",
                    "  └───────────────────────────────────────────────────────────────┘",
                    "",
                    "  ┌── KOEFISIEN KORELASI PEARSON ─────────────────────────────────┐",
                    "  │        Horizontal     Vertikal     Diagonal                    │",
                    f"  │ Plain  R: {corr_pr['H']:+.6f}   {corr_pr['V']:+.6f}   {corr_pr['D']:+.6f}",
                    f"  │        G: {corr_pg['H']:+.6f}   {corr_pg['V']:+.6f}   {corr_pg['D']:+.6f}",
                    f"  │        B: {corr_pb['H']:+.6f}   {corr_pb['V']:+.6f}   {corr_pb['D']:+.6f}",
                    sep2,
                    f"  │ Cipher R: {corr_cr['H']:+.6f}   {corr_cr['V']:+.6f}   {corr_cr['D']:+.6f}",
                    f"  │        G: {corr_cg['H']:+.6f}   {corr_cg['V']:+.6f}   {corr_cg['D']:+.6f}",
                    f"  │        B: {corr_cb['H']:+.6f}   {corr_cb['V']:+.6f}   {corr_cb['D']:+.6f}",
                    "  └───────────────────────────────────────────────────────────────┘",
                    "",
                    "  ┌── CHI-SQUARE (DISTRIBUSI UNIFORM) ────────────────────────────┐",
                    f"  │ Plain   R: {uni_pr:.4f}   G: {uni_pg:.4f}   B: {uni_pb:.4f}",
                    f"  │ Cipher  R: {uni_cr:.4f}   G: {uni_cg:.4f}   B: {uni_cb:.4f}",
                    "  │ (Nilai lebih kecil = distribusi lebih seragam)                │",
                    "  └───────────────────────────────────────────────────────────────┘",
                    "",
                    "  ┌── ENTROPI SHANNON (rata-rata R+G+B) ──────────────────────────┐",
                    f"  │ Plain    : {ent_p:.6f}",
                    f"  │ Cipher   : {ent_c:.6f}  (ideal: 7.999~8.0)",
                    "  └───────────────────────────────────────────────────────────────┘",
                    "",
                    "  ┌── PSNR & MSE (Plain vs Cipher) ───────────────────────────────┐",
                    f"  │ MSE      : {mse_val:.4f}",
                    f"  │ PSNR     : {psnr_val:.4f} dB  (rendah = enkripsi kuat)",
                    "  └───────────────────────────────────────────────────────────────┘",
                    "",
                    "  ┌── NPCR & UACI (Sensitivitas Kunci) ───────────────────────────┐",
                    f"  │ NPCR     : {npcr_val:.4f} %  (ideal ≥ 99.60%)",
                    f"  │ UACI     : {uaci_val:.4f} %  (ideal ≈ 33.46%)",
                    "  └───────────────────────────────────────────────────────────────┘",
                    "",
                    sep,
                ]
                report = "\n".join(lines) + "\n"
                hasil_cache["report"] = report

                txt.insert(END, report)
                txt.config(state=DISABLED)
                prog["value"] = 100
                status_uji.set("✅ Uji selesai! Klik 'Ekspor Laporan .txt' untuk menyimpan.")

            except Exception as e:
                status_uji.set(f"❌ Error: {e}")
                messagebox.showerror("Error", str(e), parent=win)
            finally:
                btn_uji.config(state=NORMAL)

        threading.Thread(target=_run, daemon=True).start()

    btn_uji.config(command=run_uji)
