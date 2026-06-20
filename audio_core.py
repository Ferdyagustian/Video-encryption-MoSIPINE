"""
audio_core.py
Backend enkripsi dan dekripsi audio WAV menggunakan keystream MO-SiPINE.
Desain identik dengan video_core.py namun bekerja pada sample 1D audio.
"""

import os
import struct
import subprocess
import numpy as np
import scipy.io.wavfile as wavfile

from sipine import generate_keystream_video_np

# ── Mode constants (sesuai sipine.py) ─────────────────────────────────────────
_MODE = {"mosipine": 0, "sine": 1, "pwlcm": 2}

# ── Auto-detect ffmpeg path ────────────────────────────────────────────────────
_FFMPEG_FALLBACK_PATHS = [
    r"C:\Users\LENOVO LOQ\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\ffmpeg-8.1-full_build\bin\ffmpeg.exe",
    r"C:\ffmpeg\bin\ffmpeg.exe",
    r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
]

# Cache path ffmpeg agar tidak di-probe ulang setiap panggilan fungsi
_FFMPEG_PATH_CACHE: str | None = None

def _get_ffmpeg() -> str:
    """
    Return path ke ffmpeg yang valid.
    Hasil di-cache setelah ditemukan pertama kali untuk efisiensi.
    Urutan cek: 1) cache, 2) 'ffmpeg' di PATH, 3) lokasi fallback.
    """
    global _FFMPEG_PATH_CACHE
    if _FFMPEG_PATH_CACHE is not None:
        return _FFMPEG_PATH_CACHE

    # Coba 'ffmpeg' dari PATH sistem
    try:
        res = subprocess.run(
            ["ffmpeg", "-version"],  # ← literal string, bukan rekursi
            capture_output=True,
            timeout=5
        )
        if res.returncode == 0:
            _FFMPEG_PATH_CACHE = "ffmpeg"
            return _FFMPEG_PATH_CACHE
    except Exception:
        pass

    # Cari di lokasi fallback
    for p in _FFMPEG_FALLBACK_PATHS:
        if os.path.exists(p):
            _FFMPEG_PATH_CACHE = p
            return _FFMPEG_PATH_CACHE

    raise RuntimeError(
        "ffmpeg tidak ditemukan! Pastikan ffmpeg sudah terinstall dan "
        "restart terminal/IDE Anda setelah instalasi."
    )

# ── Magic header identifier untuk file audio terenkripsi ──────────────────────
_AUDIO_MAGIC = b"AUENC"

# ── Struktur Header Audio (24 byte total) ──────────────────────────────────────
# [Magic 5B] [SampleRate I 4B] [NumChannels H 2B] [NumSamples I 4B]
# [BitDepth H 2B] [Stereo/Mono flag H 2B] [Padding 5B]
_HEADER_FMT  = "<5sIHIHH5s"
_HEADER_SIZE = struct.calcsize(_HEADER_FMT)  # = 24 bytes


def _get_keystream(x1, x2, p, beta, iter_bakar, total, mode_str):
    """Kembalikan keystream numpy uint8 menggunakan MO-SiPINE (versi video, N_SKIP=1)."""
    mode_int = _MODE.get(mode_str, 0)
    return generate_keystream_video_np(x1, x2, p, beta, iter_bakar, total, mode_int)


# ══════════════════════════════════════════════════════════════════════════════
# FUNGSI PUBLIK
# ══════════════════════════════════════════════════════════════════════════════

def extract_audio_from_video(video_path, out_wav_path):
    """
    Ekstrak stream audio dari file video menggunakan ffmpeg.
    Output: WAV PCM 16-bit, 44100 Hz.
    Raise RuntimeError jika ffmpeg tidak tersedia atau video tidak punya audio.
    """
    result = subprocess.run(
        [
            _get_ffmpeg(), "-y",
            "-i", video_path,
            "-vn",                    # skip video stream
            "-acodec", "pcm_s16le",   # format PCM 16-bit LE
            "-ar",  "44100",          # sample rate standar
            "-ac",  "2",              # stereo (2 channel); jika mono akan diupscale
            out_wav_path
        ],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        # Coba deteksi apakah memang tidak ada audio stream
        if "no streams" in result.stderr.lower() or "does not contain" in result.stderr.lower():
            raise RuntimeError("Video ini tidak memiliki stream audio.")
        raise RuntimeError(
            f"ffmpeg gagal mengekstrak audio:\n{result.stderr[-500:]}"
        )
    if not os.path.exists(out_wav_path):
        raise RuntimeError("ffmpeg tidak menghasilkan file WAV. Video mungkin tidak punya audio.")


def encrypt_audio(wav_path, out_bin_path, mode, params, progress_callback=None):
    """
    Baca file WAV, enkripsi sample-nya dengan XOR keystream MO-SiPINE,
    dan simpan sebagai file .bin dengan header kustom.

    Header (24 byte):
        [AUENC 5B][sample_rate I][channels H][num_samples I][bit_depth H][stereo_flag H][pad 5B]
    """
    sample_rate, data = wavfile.read(wav_path)

    # Normalize ke int16
    if data.dtype != np.int16:
        data = data.astype(np.int16)

    # Flatten ke 1D byte array untuk XOR
    stereo = (data.ndim == 2)
    channels = data.shape[1] if stereo else 1
    num_samples = data.shape[0]
    raw_bytes = data.tobytes()  # selalu int16 → 2 byte per sample per channel
    total_bytes = len(raw_bytes)

    x1   = float(params['x1'])
    x2   = float(params['x2'])
    p    = float(params.get('p', 0.25))
    beta = float(params['beta'])

    # Bangkitkan keystream dengan panjang = total_bytes
    ks = _get_keystream(x1, x2, p, beta, 1000, total_bytes, mode)

    # XOR vektorisasi
    raw_arr    = np.frombuffer(raw_bytes, dtype=np.uint8)
    cipher_arr = raw_arr ^ ks

    # Tulis ke file
    with open(out_bin_path, 'wb') as f:
        header = struct.pack(
            _HEADER_FMT,
            _AUDIO_MAGIC,
            sample_rate,
            channels,
            num_samples,
            16,                         # bit depth
            int(stereo),                # 1 = stereo, 0 = mono
            b'\x00' * 5                 # padding
        )
        f.write(header)
        f.write(cipher_arr.tobytes())

    if progress_callback:
        progress_callback(total_bytes, total_bytes)

    return True


def decrypt_audio(bin_path, out_wav_path, mode, params, progress_callback=None):
    """
    Baca file .bin audio terenkripsi, dekripsi XOR, dan simpan kembali sebagai WAV.
    Proses identik dengan enkripsi (XOR simetris).
    """
    if not os.path.exists(bin_path):
        raise FileNotFoundError(f"File audio VEN2 tidak ditemukan: {bin_path}")

    with open(bin_path, 'rb') as f:
        raw_header = f.read(_HEADER_SIZE)
        if len(raw_header) < _HEADER_SIZE:
            raise ValueError("File audio VEN2 korup atau format tidak sesuai.")

        magic, sample_rate, channels, num_samples, bit_depth, stereo_flag, _ = \
            struct.unpack(_HEADER_FMT, raw_header)

        if magic != _AUDIO_MAGIC:
            raise ValueError(
                "Bukan file audio enkripsi MO-SiPINE. Magic bytes tidak cocok."
            )

        cipher_bytes = f.read()

    total_bytes = len(cipher_bytes)

    x1   = float(params['x1'])
    x2   = float(params['x2'])
    p    = float(params.get('p', 0.25))
    beta = float(params['beta'])

    # Bangkitkan keystream identik
    ks = _get_keystream(x1, x2, p, beta, 1000, total_bytes, mode)

    # XOR → data asli
    cipher_arr = np.frombuffer(cipher_bytes, dtype=np.uint8)
    plain_arr  = cipher_arr ^ ks

    # Reshape ke int16 sesuai format asli
    plain_int16 = plain_arr.view(np.int16)
    if stereo_flag:
        plain_int16 = plain_int16.reshape((-1, channels))

    wavfile.write(out_wav_path, sample_rate, plain_int16)

    if progress_callback:
        progress_callback(total_bytes, total_bytes)

    return True


def audio_to_noise_wav(bin_path, out_noise_wav_path):
    """
    Konversi file audio terenkripsi (.bin) menjadi file WAV berisi noise
    (untuk disematkan ke video terenkripsi).
    Membaca raw cipher bytes, perlakukan sebagai int16 audio biasa.
    """
    if not os.path.exists(bin_path):
        raise FileNotFoundError(f"File audio VEN2 tidak ditemukan: {bin_path}")

    with open(bin_path, 'rb') as f:
        raw_header = f.read(_HEADER_SIZE)
        if len(raw_header) < _HEADER_SIZE:
            raise ValueError("File audio VEN2 korup.")

        magic, sample_rate, channels, num_samples, bit_depth, stereo_flag, _ = \
            struct.unpack(_HEADER_FMT, raw_header)

        cipher_bytes = f.read()

    # Treat cipher bytes langsung sebagai audio int16 (akan jadi noise)
    cipher_arr = np.frombuffer(cipher_bytes, dtype=np.int16)
    if stereo_flag and channels == 2:
        try:
            cipher_arr = cipher_arr.reshape((-1, 2))
        except ValueError:
            pass  # biarkan flat jika reshape gagal

    wavfile.write(out_noise_wav_path, sample_rate, cipher_arr)
    return True


def mux_video_audio(video_path, audio_path, out_path):
    """
    Gabungkan file video dan audio menjadi satu file menggunakan ffmpeg.
    Codec audio: AAC (untuk output yang sudah terdekripsi / audio normal).
    """
    result = subprocess.run(
        [
            _get_ffmpeg(), "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            out_path
        ],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg gagal menggabungkan video+audio:\n{result.stderr[-500:]}"
        )
    if not os.path.exists(out_path):
        raise RuntimeError("ffmpeg tidak menghasilkan file output.")
    return True


def mux_video_audio_lossless(video_path, audio_path, out_path):
    """
    Gabungkan file video dan audio terenkripsi menjadi satu file MKV
    menggunakan codec FLAC (lossless).
    WAJIB digunakan untuk output enkripsi agar byte cipher audio tidak
    berubah saat proses AAC encode/decode (yang bersifat lossy).
    """
    result = subprocess.run(
        [
            _get_ffmpeg(), "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "flac",   # LOSSLESS — byte cipher harus terjaga persis
            "-shortest",
            out_path
        ],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg gagal menggabungkan video+audio (lossless):\n{result.stderr[-500:]}"
        )
    if not os.path.exists(out_path):
        raise RuntimeError("ffmpeg tidak menghasilkan file output lossless.")
    return True


def demux_video_audio(mp4_path, out_video_path, out_audio_bin_path, mode, params):
    """
    Pisahkan video terenkripsi .mp4 menjadi:
    - file video mentah (.avi) berisi stream video terenkripsi
    - file audio noise (.wav sementara) → dienkripsi ulang kembali ke .bin

    CATATAN: Karena video dalam .mp4 adalah stream terenkripsi yang di-copy
    langsung (codec copy), kita cukup re-extract via ffmpeg.
    Audio noise WAV → enkripsi kembali ke .bin untuk didekripsi.
    """
    # 1. Ekstrak stream video sebagai .avi
    res_v = subprocess.run(
        [
            _get_ffmpeg(), "-y",
            "-i", mp4_path,
            "-an",          # no audio
            "-vcodec", "copy",
            out_video_path
        ],
        capture_output=True, text=True
    )
    if res_v.returncode != 0:
        raise RuntimeError(f"ffmpeg gagal mengekstrak stream video:\n{res_v.stderr[-400:]}")

    # 2. Ekstrak audio noise WAV
    noise_wav_tmp = out_audio_bin_path.replace(".bin", "_noise_tmp.wav")
    res_a = subprocess.run(
        [
            _get_ffmpeg(), "-y",
            "-i", mp4_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "44100",
            noise_wav_tmp
        ],
        capture_output=True, text=True
    )
    if res_a.returncode != 0:
        raise RuntimeError(f"ffmpeg gagal mengekstrak audio:\n{res_a.stderr[-400:]}")

    # 3. Re-enkripsi audio noise WAV → .bin
    # (karena XOR simetris, mengenkripsi cipher = mendapatkan plain)
    encrypt_audio(noise_wav_tmp, out_audio_bin_path, mode, params)

    # Hapus file temp
    try:
        os.remove(noise_wav_tmp)
    except Exception:
        pass

    return True
