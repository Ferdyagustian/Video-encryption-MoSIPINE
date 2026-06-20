"""
generator_nist.py
Generator bitstream untuk Uji NIST SP 800-22 Rev 1a.

Menggunakan fungsi Numba yang SAMA dengan enkripsi video aktual
(_generate_keystream_video, N_SKIP=4) sehingga hasil uji
merepresentasikan keacakan keystream yang benar-benar digunakan.
"""

import numpy as np
import time
import sys
import os
from sipine import generate_keystream_video_np, sine_pwlcm_map

# ── Parameter kunci chaos ────────────────────────────────────────────────────────
x1_awal      = 0.123456789
x2_awal      = 0.987654321
p_param      = 0.3678
beta_param   = 0.99
iterasi_buang = 1000              # Fase pemanasan — buang transient awal
total_bit_dihasilkan = 1_000_000  # 1 Megabit = 125,000 bytes

# ── N_SKIP = 4 (sinkron dengan _generate_keystream_video di sipine.py) ────────────
N_SKIP_INFO = 4   # hanya untuk tampilan; nilai nyata ada di dalam fungsi Numba


# ─────────────────────────────────────────────────────────────────────────────────
def hitung_progress(current, total, waktu_mulai):
    """Menampilkan progress bar di terminal."""
    persen    = (current / total) * 100
    bar_len   = 40
    filled    = int(bar_len * current // total)
    bar       = '#' * filled + '-' * (bar_len - filled)
    elapsed   = time.time() - waktu_mulai
    eta       = (elapsed / current) * (total - current) if current > 0 else 0
    sys.stdout.write(f'\r  [{bar}] {persen:5.1f}% | ETA: {eta:.1f}s ')
    sys.stdout.flush()


def validasi_entropy_awal(x0, p, beta, n=500):
    """
    Estimasi kasar eksponen Lyapunov (harus > 0 untuk chaos).
    Dijalankan sebelum pembangkitan untuk deteksi parameter buruk.
    """
    x   = x0
    dx  = 1e-8
    sum_log = 0.0
    valid   = 0

    # Buang transient
    for _ in range(200):
        x = sine_pwlcm_map(x, p, beta)

    for _ in range(n):
        x_next    = sine_pwlcm_map(x, p, beta)
        x_next_dx = sine_pwlcm_map(x + dx, p, beta)
        deriv     = abs((x_next_dx - x_next) / dx)
        if deriv > 0:
            sum_log += np.log(deriv)
            valid   += 1
        x = x_next

    return sum_log / valid if valid > 0 else 0.0


def hitung_statistik_bitstream(arr_bytes: np.ndarray):
    """
    Hitung statistik dasar dari numpy uint8 array (bukan string, lebih efisien memori).
    Return dict berisi total_bits, count_0, count_1, rasio, entropy, autocorr.
    """
    # Unpack ke bit array (0/1) menggunakan numpy — jauh lebih cepat dari string
    bits      = np.unpackbits(arr_bytes)   # shape: (N*8,), dtype uint8
    n         = len(bits)
    count_1   = int(bits.sum())
    count_0   = n - count_1
    rasio_1   = count_1 / n
    rasio_0   = count_0 / n

    # Shannon Entropy (bit)
    entropy = 0.0
    if rasio_0 > 0:
        entropy -= rasio_0 * np.log2(rasio_0)
    if rasio_1 > 0:
        entropy -= rasio_1 * np.log2(rasio_1)

    # Autocorrelation lag-1 — sampel 10,000 bit pertama saja
    sample_size = min(10_000, n)
    b_f  = bits[:sample_size].astype(np.float64)
    b_m  = b_f - b_f.mean()
    var  = np.var(b_m)
    if var > 0:
        autocorr_val = float(
            np.correlate(b_m[:-1], b_m[1:]) / ((sample_size - 1) * var)
        )
    else:
        autocorr_val = 0.0

    return {
        'total_bits'         : n,
        'count_0'            : count_0,
        'count_1'            : count_1,
        'rasio_0'            : rasio_0,
        'rasio_1'            : rasio_1,
        'entropy'            : entropy,
        'autocorrelation_lag1': autocorr_val,
    }


# ─────────────────────────────────────────────────────────────────────────────────
# MAIN GENERATION
# ─────────────────────────────────────────────────────────────────────────────────

print("=" * 65)
print("   GENERATOR BITSTREAM CHAOTIC — MO-SiPINE")
print(f"   N_SKIP={N_SKIP_INFO} | Konsisten dengan enkripsi video aktual")
print("=" * 65)
print()
print(f"  Parameter:")
print(f"    x1_awal       = {x1_awal}")
print(f"    x2_awal       = {x2_awal}")
print(f"    p             = {p_param}")
print(f"    beta          = {beta_param}")
print(f"    N_SKIP        = {N_SKIP_INFO} (via generate_keystream_video_np)")
print(f"    Iterasi buang = {iterasi_buang}")
print(f"    Total bit     = {total_bit_dihasilkan:,}")
print()

# ── [1/4] Validasi Lyapunov ─────────────────────────────────────────────────────
print("[1/4] Validasi parameter chaos (Eksponen Lyapunov)...")
lyap = validasi_entropy_awal(x1_awal, p_param, beta_param)
if lyap > 0:
    print(f"  [OK] Lyapunov ~ {lyap:.4f} (POSITIF — chaos terkonfirmasi)")
else:
    print(f"  [!!] PERINGATAN: Lyapunov ~ {lyap:.4f} (NON-POSITIF — kemungkinan periodik!)")
    print(f"       Pertimbangkan ganti parameter sebelum melanjutkan.")
print()

# ── [2/4] Bangkitkan keystream via Numba (satu panggilan) ───────────────────────
total_byte_output = total_bit_dihasilkan // 8   # 125,000 bytes

print(f"[2/4] Membangkitkan {total_byte_output:,} bytes via Numba JIT (N_SKIP={N_SKIP_INFO})...")
waktu_gen = time.time()

# Satu panggilan tunggal — Numba menghandle sub-sampling dan feedback injection
# Mode 0 = MO-SiPINE (Modulo Sine-PWLCM)
keystream_bytes: np.ndarray = generate_keystream_video_np(
    x1_awal, x2_awal, p_param, beta_param,
    iterasi_buang, total_byte_output,
    mode=0
)

durasi_gen = time.time() - waktu_gen
kecepatan  = total_byte_output / durasi_gen if durasi_gen > 0 else float('inf')
print(f"  [OK] {len(keystream_bytes):,} bytes selesai ({durasi_gen:.3f}s | {kecepatan:,.0f} byte/dtk)")
print()

# ── [3/4] Simpan output ─────────────────────────────────────────────────────────
print("[3/4] Menyimpan output...")

# Output 1: Bitstream string — format standar untuk software NIST STS
nama_file_txt = 'Hasil_Uji_NIST_SubSampling.txt'
waktu_io = time.time()

# Konversi numpy uint8 → bitstring menggunakan np.unpackbits (paling efisien)
bits_array    = np.unpackbits(keystream_bytes)             # shape (1_000_000,)
# Tulis langsung ke file sebagai karakter '0'/'1' tanpa membuat string raksasa di RAM
with open(nama_file_txt, 'w', buffering=1 << 16) as f:    # buffer 64KB
    # Proses per blok 50,000 bit agar tidak memakan RAM lebih dari perlu
    BLOK = 50_000
    for start in range(0, len(bits_array), BLOK):
        chunk = bits_array[start:start + BLOK]
        f.write(''.join(map(str, chunk.tolist())))

# Output 2: Raw bytes — untuk analisis lanjut / tool eksternal
nama_file_bin = 'Hasil_Uji_NIST_SubSampling.bin'
with open(nama_file_bin, 'wb') as f:
    f.write(keystream_bytes.tobytes())

durasi_io = time.time() - waktu_io
print(f"  [OK] {nama_file_txt} ({os.path.getsize(nama_file_txt):,} bytes)")
print(f"  [OK] {nama_file_bin} ({os.path.getsize(nama_file_bin):,} bytes)")
print(f"  [OK] I/O selesai ({durasi_io:.3f}s)")
print()

# ── [4/4] Statistik bitstream ───────────────────────────────────────────────────
print("[4/4] Statistik bitstream:")
stats = hitung_statistik_bitstream(keystream_bytes)

print(f"  Total bit         : {stats['total_bits']:,}")
print(f"  Jumlah bit '0'    : {stats['count_0']:,} ({stats['rasio_0']:.6f})")
print(f"  Jumlah bit '1'    : {stats['count_1']:,} ({stats['rasio_1']:.6f})")
print(f"  Shannon Entropy   : {stats['entropy']:.6f} bit (ideal = 1.000000)")
print(f"  Autocorr (lag-1)  : {stats['autocorrelation_lag1']:.6f} (ideal ≈ 0.000)")

bias = abs(stats['rasio_1'] - 0.5)
if bias < 0.005:
    print(f"  Bias              : {bias:.6f} — SANGAT BAIK [OK]")
elif bias < 0.01:
    print(f"  Bias              : {bias:.6f} — BAIK [OK]")
else:
    print(f"  Bias              : {bias:.6f} — PERLU PERHATIAN [!!]")

print()
print("=" * 65)
durasi_total = durasi_gen + durasi_io
print(f"  SELESAI! Total waktu proses: {durasi_total:.3f} detik")
print(f"  File utama untuk NIST STS : {nama_file_txt}")
print("=" * 65)