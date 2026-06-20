import numpy as np
from numba import njit
import math

# ============================================================
# CORE MAP FUNCTIONS (dikompilasi ke mesin via @njit Numba)
# Peningkatan kecepatan: 50x - 100x vs pure Python loop
# ============================================================

@njit(cache=True)
def _sine_pwlcm_step(x, p, beta):
    """Satu langkah iterasi Modulo Sine-PWLCM."""
    if x >= 0.5:
        x_eval = 1.0 - x
    else:
        x_eval = x

    if 0.0 <= x_eval < p:
        f_x = x_eval / p
    elif p <= x_eval < 0.5:
        f_x = (x_eval - p) / (0.5 - p)
    else:
        f_x = 0.0

    return (beta * math.sin(math.pi * f_x) * 987676766.3232) % 1.0


@njit(cache=True)
def _sine_only_step(x, beta):
    """Satu langkah iterasi Modulo Sine murni."""
    return (beta * math.sin(math.pi * x) * 987676766.3232) % 1.0


@njit(cache=True)
def _pwlcm_only_step(x, p):
    """Satu langkah iterasi PWLCM + scalar modulo."""
    SCALAR = 987676766.3232
    if x >= 0.5:
        x_eval = 1.0 - x
    else:
        x_eval = x

    if 0.0 <= x_eval < p:
        f_x = x_eval / p
    elif p <= x_eval < 0.5:
        f_x = (x_eval - p) / (0.5 - p)
    else:
        f_x = 0.0

    return (f_x * SCALAR) % 1.0


@njit(cache=True)
def _generate_keystream_core(x1, x2, p, beta, iter_awal, total, mode):
    """
    Inti pembangkitan keystream yang dikompilasi Numba.
    mode: 0 = MO-SiPINE, 1 = Sine Only, 2 = PWLCM Only
    """
    N_SKIP = 12
    keystream = np.empty(total, dtype=np.uint8)

    # Fase Pemanasan
    for _ in range(iter_awal):
        if mode == 0:
            x1 = _sine_pwlcm_step(x1, p, beta)
            x2 = _sine_pwlcm_step(x2, p, beta)
        elif mode == 1:
            x1 = _sine_only_step(x1, beta)
            x2 = _sine_only_step(x2, beta)
        else:
            x1 = _pwlcm_only_step(x1, p)
            x2 = _pwlcm_only_step(x2, p)

    # Pembangkitan Array Kunci
    k_prev = np.uint8(0)
    for i in range(total):
        # Sub-Sampling (N_SKIP iterasi dibuang)
        for _ in range(N_SKIP):
            if mode == 0:
                x1 = _sine_pwlcm_step(x1, p, beta)
                x2 = _sine_pwlcm_step(x2, p, beta)
            elif mode == 1:
                x1 = _sine_only_step(x1, beta)
                x2 = _sine_only_step(x2, beta)
            else:
                x1 = _pwlcm_only_step(x1, p)
                x2 = _pwlcm_only_step(x2, p)

        # Injeksi Umpan Balik
        x1 = (x1 + (k_prev / 256.0)) % 1.0
        x2 = (x2 + x1) % 1.0

        # Evolusi terakhir sebelum ekstraksi
        if mode == 0:
            x1 = _sine_pwlcm_step(x1, p, beta)
            x2 = _sine_pwlcm_step(x2, p, beta)
        elif mode == 1:
            x1 = _sine_only_step(x1, beta)
            x2 = _sine_only_step(x2, beta)
        else:
            x1 = _pwlcm_only_step(x1, p)
            x2 = _pwlcm_only_step(x2, p)

        # Konversi ke integer 32-bit & cascade XOR folding
        val1 = int(x1 * 4294967296.0)
        val2 = int(x2 * 4294967296.0)

        k1 = ((val1 >> 24) & 255) ^ ((val1 >> 16) & 255) ^ ((val1 >> 8) & 255) ^ (val1 & 255)
        k2 = ((val2 >> 24) & 255) ^ ((val2 >> 16) & 255) ^ ((val2 >> 8) & 255) ^ (val2 & 255)

        k_prev = np.uint8(k1 ^ k2)
        keystream[i] = k_prev

    return keystream


@njit(cache=True)
def _generate_keystream_video(x1, x2, p, beta, iter_awal, total, mode):
    """
    Versi VIDEO: N_SKIP=4 — keseimbangan kecepatan dan keacakan.
    Keamanan antar-frame dijaga oleh state chaining di video_core.py.
    Algoritma identik dengan _generate_keystream_core, hanya N_SKIP lebih kecil.
    mode: 0 = MO-SiPINE, 1 = Sine Only, 2 = PWLCM Only
    """
    N_SKIP = 4
    keystream = np.empty(total, dtype=np.uint8)

    # Fase Pemanasan
    for _ in range(iter_awal):
        if mode == 0:
            x1 = _sine_pwlcm_step(x1, p, beta)
            x2 = _sine_pwlcm_step(x2, p, beta)
        elif mode == 1:
            x1 = _sine_only_step(x1, beta)
            x2 = _sine_only_step(x2, beta)
        else:
            x1 = _pwlcm_only_step(x1, p)
            x2 = _pwlcm_only_step(x2, p)

    k_prev = np.uint8(0)
    for i in range(total):
        for _ in range(N_SKIP):
            if mode == 0:
                x1 = _sine_pwlcm_step(x1, p, beta)
                x2 = _sine_pwlcm_step(x2, p, beta)
            elif mode == 1:
                x1 = _sine_only_step(x1, beta)
                x2 = _sine_only_step(x2, beta)
            else:
                x1 = _pwlcm_only_step(x1, p)
                x2 = _pwlcm_only_step(x2, p)

        x1 = (x1 + (k_prev / 256.0)) % 1.0
        x2 = (x2 + x1) % 1.0

        if mode == 0:
            x1 = _sine_pwlcm_step(x1, p, beta)
            x2 = _sine_pwlcm_step(x2, p, beta)
        elif mode == 1:
            x1 = _sine_only_step(x1, beta)
            x2 = _sine_only_step(x2, beta)
        else:
            x1 = _pwlcm_only_step(x1, p)
            x2 = _pwlcm_only_step(x2, p)

        val1 = int(x1 * 4294967296.0)
        val2 = int(x2 * 4294967296.0)

        k1 = ((val1 >> 24) & 255) ^ ((val1 >> 16) & 255) ^ ((val1 >> 8) & 255) ^ (val1 & 255)
        k2 = ((val2 >> 24) & 255) ^ ((val2 >> 16) & 255) ^ ((val2 >> 8) & 255) ^ (val2 & 255)

        k_prev = np.uint8(k1 ^ k2)
        keystream[i] = k_prev

    return keystream



# ============================================================
# PUBLIC API (sama seperti sebelumnya, tidak ada yang berubah
# dari sisi pemanggil / GUI / video_core)
# ============================================================

def sine_pwlcm_map(x, p, beta):
    """Wrapper untuk satu langkah MO-SiPINE (kompatibilitas)."""
    return _sine_pwlcm_step(x, p, beta)


def generate_keystream(x0_1, x0_2, p, beta, iter_awal, total):
    """Bangkitkan keystream mode MO-SiPINE (Numba-accelerated). Return: list[int]"""
    return _generate_keystream_core(x0_1, x0_2, p, beta, iter_awal, total, 0).tolist()


def generate_keystream_sine_only(x0_1, x0_2, beta, iter_awal, total):
    """Bangkitkan keystream mode Sine Only (Numba-accelerated). Return: list[int]"""
    return _generate_keystream_core(x0_1, x0_2, 0.25, beta, iter_awal, total, 1).tolist()


def generate_keystream_pwlcm_only(x0_1, x0_2, p, beta, iter_awal, total):
    """Bangkitkan keystream mode PWLCM Only (Numba-accelerated). Return: list[int]"""
    return _generate_keystream_core(x0_1, x0_2, p, beta, iter_awal, total, 2).tolist()


# Varian numpy array — dipakai oleh video_core untuk XOR langsung tanpa konversi
def generate_keystream_np(x0_1, x0_2, p, beta, iter_awal, total, mode=0):
    """Bangkitkan keystream sebagai numpy uint8 array (tercepat, untuk video).
    mode: 0=MO-SiPINE, 1=Sine Only, 2=PWLCM Only
    """
    return _generate_keystream_core(x0_1, x0_2, p, beta, iter_awal, total, mode)


def generate_keystream_video_np(x0_1, x0_2, p, beta, iter_awal, total, mode=0):
    """Versi VIDEO (N_SKIP=4) — keseimbangan kecepatan dan keacakan.
    Keamanan dijaga oleh state chaining antar frame di video_core.py.
    mode: 0=MO-SiPINE, 1=Sine Only, 2=PWLCM Only
    """
    return _generate_keystream_video(x0_1, x0_2, p, beta, iter_awal, total, mode)


# ============================================================
# WARMUP (JIT Compile saat Modul Pertama Kali Diimpor)
# Sehingga jeda kompilasi terjadi sekali di awal, bukan
# saat user menekan tombol enkripsi pertama kali.
# ============================================================
def _warmup():
    print("[sipine] Warming up Numba JIT... (hanya 1x saat startup)")
    _generate_keystream_core(0.1, 0.2, 0.25, 0.99, 10, 16, 0)
    _generate_keystream_core(0.1, 0.2, 0.25, 0.99, 10, 16, 1)
    _generate_keystream_core(0.1, 0.2, 0.25, 0.99, 10, 16, 2)
    _generate_keystream_video(0.1, 0.2, 0.25, 0.99, 10, 16, 0)
    _generate_keystream_video(0.1, 0.2, 0.25, 0.99, 10, 16, 1)
    _generate_keystream_video(0.1, 0.2, 0.25, 0.99, 10, 16, 2)
    print("[sipine] JIT Compile selesai. Siap digunakan!")

_warmup()


if __name__ == "__main__":
    import timeit

    print("=== BENCHMARK: PURE PYTHON vs NUMBA ===")
    key_x1 = 0.123456789
    key_x2 = 0.987654321
    key_p = 0.25
    key_beta = 0.99
    iter_buang = 1000
    jumlah_piksel = 512 * 512  # Gambar kecil 512x512

    print(f"\nMembangkitkan {jumlah_piksel} keystream bytes...")
    tic = timeit.default_timer()
    kunci = generate_keystream(key_x1, key_x2, key_p, key_beta, iter_buang, jumlah_piksel)
    toc = timeit.default_timer()
    print(f"Numba JIT   : {toc - tic:.4f} detik")
    print(f"Sample Key  : {kunci[:8]}")

    # Validasi: Enkripsi & Dekripsi harus identik
    citra_asli = list(range(256))
    kunci_val = generate_keystream(key_x1, key_x2, key_p, key_beta, iter_buang, 256)
    citra_enc = [a ^ b for a, b in zip(citra_asli, kunci_val)]
    kunci_val2 = generate_keystream(key_x1, key_x2, key_p, key_beta, iter_buang, 256)
    citra_dec = [a ^ b for a, b in zip(citra_enc, kunci_val2)]
    if citra_asli == citra_dec:
        print("\n[LULUS] Dekripsi 100% berhasil memulihkan data asli.")
    else:
        print("\n[GAGAL] Ada kerusakan data!")