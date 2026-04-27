import cv2
import numpy as np
import struct
import os
from sipine import generate_keystream_video_np
from PIL import Image

# Mode constants (sama dengan di sipine.py _generate_keystream_core)
_MODE = {"mosipine": 0, "sine": 1, "pwlcm": 2}


def _get_keystream(x1, x2, p, beta, iter_bakar, total, mode_str):
    """Pembantu: kembalikan numpy uint8 keystream (N_SKIP=3, versi video)."""
    mode_int = _MODE.get(mode_str, 0)
    return generate_keystream_video_np(x1, x2, p, beta, iter_bakar, total, mode_int)


def encrypt_video_to_binary(input_video_path, output_bin_path, mode, params,
                            progress_callback=None):
    """
    Ekstrak frame video, enkripsi dengan keystream chaos (XOR vektorisasi NumPy),
    dan simpan hasilnya sebagai file biner mentah (.bin).
    Tidak ada audio yang disimpan.
    """
    cap = cv2.VideoCapture(input_video_path)
    if not cap.isOpened():
        raise Exception(f"Gagal membuka video: {input_video_path}")

    width       = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height      = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps         = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames <= 0:
        total_frames = 99999  # Fallback jika header video rusak

    x1   = float(params['x1'])
    x2   = float(params['x2'])
    p    = float(params.get('p', 0.25))
    beta = float(params['beta'])
    total_pixels = width * height * 3  # BGR, 3 channel

    with open(output_bin_path, 'wb') as f:
        # --- Header 16 Byte Kustom: [Width I][Height I][TotalFrames I][FPS f] ---
        f.write(struct.pack('<IIIf', width, height, total_frames, fps))

        iter_bakar = 1000  # Pemanasan panjang hanya pada frame pertama
        frame_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Keystream sebagai numpy uint8 array langsung (tanpa .tolist())
            ks = _get_keystream(x1, x2, p, beta, iter_bakar, total_pixels, mode)

            # XOR vektorisasi NumPy — ratusan kali lebih cepat dari Python loop
            cipher_bytes = frame.flatten() ^ ks

            f.write(cipher_bytes.tobytes())

            # Geser state chaos antar frame (chaining)
            iter_bakar = 10
            x1 = (x1 + 0.0019) % 1.0
            x2 = (x2 + 0.0073) % 1.0
            frame_count += 1

            if progress_callback:
                progress_callback(frame_count, total_frames)

    cap.release()

    # Perbaiki total_frames di header jika fallback dipakai
    if frame_count != total_frames:
        with open(output_bin_path, 'r+b') as f:
            f.seek(8)  # offset ke field TotalFrames
            f.write(struct.pack('<I', frame_count))

    return True


def decrypt_binary_to_video(input_bin_path, output_video_path, mode, params,
                            progress_callback=None):
    """
    Baca file biner mentah (.bin), dekripsi, dan rekonstruksi menjadi video (.avi).
    Proses identik dengan enkripsi (XOR simetris).
    """
    if not os.path.exists(input_bin_path):
        raise Exception(f"File binary tidak ditemukan: {input_bin_path}")

    with open(input_bin_path, 'rb') as f:
        # Baca header metadata
        header = f.read(16)
        if len(header) < 16:
            raise Exception("File binary korup atau format tidak sesuai.")
        width, height, total_frames, fps = struct.unpack('<IIIf', header)

        # VideoWriter Codec (XVID sangat kompatibel pada Windows / OpenCV untuk dibaca ulang)
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        writer = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))

        x1   = float(params['x1'])
        x2   = float(params['x2'])
        p    = float(params.get('p', 0.25))
        beta = float(params['beta'])
        total_pixels = width * height * 3
        bytes_to_read = total_pixels

        iter_bakar = 1000
        for frame_idx in range(total_frames):
            raw = f.read(bytes_to_read)
            if not raw or len(raw) < bytes_to_read:
                break

            cipher = np.frombuffer(raw, dtype=np.uint8)

            # Keystream numpy uint8 langsung
            ks = _get_keystream(x1, x2, p, beta, iter_bakar, total_pixels, mode)

            # XOR vektorisasi — dekripsi simetris
            plain = cipher ^ ks
            frame = plain.reshape((height, width, 3))
            writer.write(frame)

            iter_bakar = 10
            x1 = (x1 + 0.0019) % 1.0
            x2 = (x2 + 0.0073) % 1.0

            if progress_callback:
                progress_callback(frame_idx + 1, total_frames)

    writer.release()
    return True


def extract_sample_frames(video_path, out_dir):
    """
    Ekstrak 3 frame sampel representatif dari video pada posisi 10%, 50%, dan 90%.
    Simpan sebagai PNG di out_dir.
    Return: tuple (path_awal, path_tengah, path_akhir) atau raises Exception jika gagal.
    """
    os.makedirs(out_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise Exception(f"Gagal membuka video: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames <= 0:
        cap.release()
        raise Exception("Video tidak memiliki informasi total frame yang valid.")

    positions = {
        "awal":   max(0, int(total_frames * 0.10)),
        "tengah": max(0, int(total_frames * 0.50)),
        "akhir":  max(0, int(total_frames * 0.90)),
    }

    paths = {}
    for label, frame_idx in positions.items():
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            # Coba frame terakhir yang tersedia
            cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, total_frames - 1))
            ret, frame = cap.read()
        if not ret:
            cap.release()
            raise Exception(f"Gagal membaca frame pada posisi {label} (frame #{frame_idx}).")
        out_path = os.path.join(out_dir, f"frame_sampel_{label}.png")
        # Konversi BGR → RGB sebelum simpan agar warna benar saat dibuka PIL
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        Image.fromarray(frame_rgb).save(out_path)
        paths[label] = out_path

    cap.release()
    return paths["awal"], paths["tengah"], paths["akhir"]


def extract_single_frame_from_bin(bin_path, frame_position_ratio, out_path):
    """
    Ekstrak satu frame dari file .bin terenkripsi (raw biner) berdasarkan rasio posisi (0.0–1.0).
    Frame diambil mentah (terenkripsi) dan disimpan sebagai PNG.
    Return: path file PNG yang disimpan.
    """
    if not os.path.exists(bin_path):
        raise Exception(f"File binary tidak ditemukan: {bin_path}")

    with open(bin_path, 'rb') as f:
        header = f.read(16)
        if len(header) < 16:
            raise Exception("File binary korup atau format tidak sesuai.")
        width, height, total_frames, fps = struct.unpack('<IIIf', header)

        frame_idx = max(0, min(int(total_frames * frame_position_ratio), total_frames - 1))
        bytes_per_frame = width * height * 3

        f.seek(16 + frame_idx * bytes_per_frame)
        raw = f.read(bytes_per_frame)
        if not raw or len(raw) < bytes_per_frame:
            raise Exception(f"Gagal membaca frame #{frame_idx} dari file biner.")

    arr = np.frombuffer(raw, dtype=np.uint8).reshape((height, width, 3))
    # Data sudah BGR (dari OpenCV), konversi ke RGB untuk PIL
    img = Image.fromarray(arr[:, :, ::-1])
    img.save(out_path)
    return out_path
