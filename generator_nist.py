import numpy as np
import time
import sys
import os
import hashlib
from sipine import sine_pwlcm_map

x1_awal = 0.123456789
x2_awal = 0.987654321
p_param = 0.3678
beta_param = 0.99
iterasi_buang = 1000
total_bit_dihasilkan = 1_000_000  # 1 Megabit

# Jumlah Lompatan Sub-Sampling
N_SKIP = 16


def hitung_progress(current, total, waktu_mulai):
    """Menampilkan progress bar di terminal."""
    persen = (current / total) * 100
    bar_len = 40
    filled = int(bar_len * current // total)
    bar = '#' * filled + '-' * (bar_len - filled)
    elapsed = time.time() - waktu_mulai
    if current > 0:
        eta = (elapsed / current) * (total - current)
    else:
        eta = 0
    sys.stdout.write(f'\r  [{bar}] {persen:5.1f}% | ETA: {eta:.1f}s ')
    sys.stdout.flush()


def validasi_entropy_awal(x0, p, beta, n=500):
    """Estimasi kasar apakah parameter menghasilkan chaos (Lyapunov > 0)."""
    x = x0
    dx = 1e-8
    sum_log = 0
    valid = 0
    
    for _ in range(200):  # Buang transient
        x = sine_pwlcm_map(x, p, beta)
    
    for _ in range(n):
        x_next = sine_pwlcm_map(x, p, beta)
        x_next_dx = sine_pwlcm_map(x + dx, p, beta)
        deriv = abs((x_next_dx - x_next) / dx)
        if deriv > 0:
            sum_log += np.log(deriv)
            valid += 1
        x = x_next
    
    if valid > 0:
        lyap = sum_log / valid
        return lyap
    return 0.0


def hitung_statistik_bitstream(bitstream_str):
    """Menghitung statistik dasar bitstream."""
    n = len(bitstream_str)
    count_1 = bitstream_str.count('1')
    count_0 = n - count_1
    rasio_1 = count_1 / n
    rasio_0 = count_0 / n
    
    # Entropy per-bit (Shannon)
    entropy = 0.0
    if rasio_0 > 0:
        entropy -= rasio_0 * np.log2(rasio_0)
    if rasio_1 > 0:
        entropy -= rasio_1 * np.log2(rasio_1)
    
    # Autocorrelation lag-1
    sample_size = min(10000, n)
    bits = np.array([int(b) for b in bitstream_str[:sample_size]], dtype=np.float64)
    bits_shifted = bits - np.mean(bits)
    if np.std(bits_shifted) > 0:
        autocorr = np.correlate(bits_shifted[:sample_size-1], bits_shifted[1:sample_size]) / ((sample_size-1) * np.var(bits_shifted))
        autocorr_val = autocorr[0]
    else:
        autocorr_val = 0.0
    
    return {
        'total_bits': n,
        'count_0': count_0,
        'count_1': count_1,
        'rasio_0': rasio_0,
        'rasio_1': rasio_1,
        'entropy': entropy,
        'autocorrelation_lag1': autocorr_val
    }


print("=" * 65)
print("   GENERATOR BITSTREAM CHAOTIC - SINE-PWLCM")
print("   Dengan SHA-256 Post-Processing (Whitening)")
print("=" * 65)
print()
print(f"  Parameter:")
print(f"    x1_awal       = {x1_awal}")
print(f"    x2_awal       = {x2_awal}")
print(f"    p             = {p_param}")
print(f"    beta          = {beta_param}")
print(f"    N_SKIP        = {N_SKIP}")
print(f"    Iterasi buang = {iterasi_buang}")
print(f"    Total bit     = {total_bit_dihasilkan:,}")
print()

print("[1/5] Validasi parameter chaos...")
lyap = validasi_entropy_awal(x1_awal, p_param, beta_param)
if lyap > 0:
    print(f"  [OK] Eksponen Lyapunov ~ {lyap:.4f} (POSITIF - chaos terkonfirmasi)")
else:
    print(f"  [!!] PERINGATAN: Lyapunov ~ {lyap:.4f} (NON-POSITIF - kemungkinan periodik!)")
    print(f"    Sistem mungkin tidak chaotic. Pertimbangkan ganti parameter.")
print()

print(f"[2/5] Pemanasan sistem ({iterasi_buang} iterasi)...")
waktu_mulai = time.time()

x1 = x1_awal
x2 = x2_awal

for _ in range(iterasi_buang):
    x1 = sine_pwlcm_map(x1, p_param, beta_param)
    x2 = sine_pwlcm_map(x2, p_param, beta_param)

print(f"  [OK] Pemanasan selesai ({time.time() - waktu_mulai:.3f}s)")
print()


print(f"[3/5] Membangkitkan {total_bit_dihasilkan:,} bit...")
print(f"       Tahap 1: Raw chaos generation")
print(f"       Tahap 2: SHA-256 whitening")
waktu_gen = time.time()


total_byte_output = total_bit_dihasilkan // 8  # 125,000 bytes

BLOCK_SIZE = 128
jumlah_blok = (total_byte_output + 31) // 32   # ceil(125000/32) = 3907
raw_bytes_needed = jumlah_blok * BLOCK_SIZE     # 3907 * 128 = 500,096 raw bytes

raw_pool = bytearray()
k_prev = 0

for i in range(raw_bytes_needed):
    
    # FASE 1: MENGADUK CHAOS (Sub-Sampling)
    for _ in range(N_SKIP):
        x1 = sine_pwlcm_map(x1, p_param, beta_param)
        x2 = sine_pwlcm_map(x2, p_param, beta_param)

    x1 = (x1 + (k_prev / 256.0)) % 1.0
    x2 = (x2 + x1) % 1.0

    x1 = sine_pwlcm_map(x1, p_param, beta_param)
    x2 = sine_pwlcm_map(x2, p_param, beta_param)

    val1 = int(x1 * 4294967296.0)  # 2^32
    val2 = int(x2 * 4294967296.0)
    
    k1 = ((val1 >> 24) & 255) ^ ((val1 >> 16) & 255) ^ ((val1 >> 8) & 255) ^ (val1 & 255)
    k2 = ((val2 >> 24) & 255) ^ ((val2 >> 16) & 255) ^ ((val2 >> 8) & 255) ^ (val2 & 255)

    k_prev = k1 ^ k2
    raw_pool.append(k_prev)
    
    if (i + 1) % max(1, raw_bytes_needed // 100) == 0:
        hitung_progress(i + 1, raw_bytes_needed, waktu_gen)

sys.stdout.write('\r' + ' ' * 70 + '\r')
durasi_raw = time.time() - waktu_gen
print(f"  [OK] Raw chaos: {len(raw_pool):,} bytes ({durasi_raw:.2f}s)")

waktu_hash = time.time()
whitened_bytes = bytearray()

for i in range(0, len(raw_pool) - BLOCK_SIZE + 1, BLOCK_SIZE):
    block = bytes(raw_pool[i:i + BLOCK_SIZE])
    
    digest = hashlib.sha256(block).digest()
    whitened_bytes.extend(digest)
    
    if len(whitened_bytes) >= total_byte_output:
        break

# Potong tepat sesuai kebutuhan
whitened_bytes = whitened_bytes[:total_byte_output]

durasi_hash = time.time() - waktu_hash
print(f"  [OK] SHA-256 whitening: {len(whitened_bytes):,} bytes ({durasi_hash:.3f}s)")

# Konversi ke bitstream string
bitstream_list = []
for b in whitened_bytes:
    bitstream_list.append(format(b, '08b'))

durasi_gen_total = time.time() - waktu_gen
print(f"  [OK] Total generasi: {durasi_gen_total:.2f}s - {total_byte_output / durasi_gen_total:,.0f} byte/detik")
print()

print("[4/5] Menyimpan output...")

bitstream_final = "".join(bitstream_list)

# Output 1: Binary string file (untuk uji NIST)
nama_file_txt = 'Hasil_Uji_NIST_SubSampling.txt'
with open(nama_file_txt, 'w') as f:
    f.write(bitstream_final)

# Output 2: Raw bytes file (untuk analisis lanjut)
nama_file_bin = 'Hasil_Uji_NIST_SubSampling.bin'
with open(nama_file_bin, 'wb') as f:
    f.write(whitened_bytes)

print(f"  [OK] {nama_file_txt} ({os.path.getsize(nama_file_txt):,} bytes)")
print(f"  [OK] {nama_file_bin} ({os.path.getsize(nama_file_bin):,} bytes)")
print()

print("[5/5] Statistik bitstream:")
stats = hitung_statistik_bitstream(bitstream_final)

print(f"  Total bit         : {stats['total_bits']:,}")
print(f"  Jumlah bit '0'    : {stats['count_0']:,} ({stats['rasio_0']:.6f})")
print(f"  Jumlah bit '1'    : {stats['count_1']:,} ({stats['rasio_1']:.6f})")
print(f"  Shannon Entropy   : {stats['entropy']:.6f} bit (ideal = 1.000000)")
print(f"  Autocorr (lag-1)  : {stats['autocorrelation_lag1']:.6f} (ideal ~ 0.000)")

# Penilaian cepat
bias = abs(stats['rasio_1'] - 0.5)
if bias < 0.005:
    print(f"  Bias              : {bias:.6f} - SANGAT BAIK [OK]")
elif bias < 0.01:
    print(f"  Bias              : {bias:.6f} - BAIK [OK]")
else:
    print(f"  Bias              : {bias:.6f} - PERLU PERHATIAN [!!]")

print()
print("=" * 65)
durasi_total = time.time() - waktu_mulai
print(f"  SELESAI! Total waktu: {durasi_total:.2f} detik")
print(f"  File utama: {nama_file_txt}")
print("=" * 65)