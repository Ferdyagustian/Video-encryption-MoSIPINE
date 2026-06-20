"""
ai_optimizer.py
Heuristic-search optimizer untuk mencari kunci chaos terbaik (maks. Shannon Entropy).
Menggunakan fungsi Numba yang sama dengan enkripsi aktual (generate_keystream).

Peningkatan v2:
  1. Narrowing Refinement — setelah kandidat terbaik ditemukan, pencarian berikutnya
     dilakukan di sekitar kandidat tersebut (Gaussian perturbation) agar konvergensi
     lebih cepat. Setiap REFINE_INTERVAL iterasi gagal, kembali ke global random search.
  2. Lyapunov n=300 — estimasi eksponen Lyapunov lebih akurat, mengurangi false positive
     pada filter chaotic sehingga evaluasi entropy tidak sia-sia.
  3. sample_size=50_000 — estimasi entropy lebih stabil dan representatif, menghindari
     kandidat yang terlihat baik pada sample kecil tapi buruk pada data nyata.
"""

import time
import math
import random
import numpy as np
from sipine import (
    generate_keystream,
    generate_keystream_sine_only,
    generate_keystream_pwlcm_only,
    sine_pwlcm_map,
)

# ─────────────────────────────────────────────────────────────────────────────────
# Konstanta narrowing refinement
_REFINE_STD      = 0.05   # Standar deviasi Gaussian saat refinement lokal
_REFINE_INTERVAL = 10     # Jumlah iterasi gagal sebelum kembali ke global search


def calculate_entropy(data: list | np.ndarray) -> float:
    """
    Hitung Shannon Entropy dari array data byte.
    Nilai mendekati 8.0 menunjukkan keacakan tertinggi.
    Menggunakan np.bincount agar O(N) dan tanpa alokasi dict.
    """
    if len(data) == 0:
        return 0.0
    counts = np.bincount(data, minlength=256).astype(np.float64)
    total  = counts.sum()
    probs  = counts[counts > 0] / total           # hanya nilai non-nol
    return float(-np.sum(probs * np.log2(probs)))  # Shannon entropy


def _lyapunov_estimate(x0: float, p: float, beta: float, n: int = 300) -> float:
    """
    Estimasi eksponen Lyapunov menggunakan finite-difference.
    Return > 0 berarti sistem chaotic.

    n=300 memberikan estimasi lebih akurat dibanding n=150,
    mengurangi false positive kandidat non-chaotic yang lolos filter.
    """
    x  = x0
    dx = 1e-8
    acc = 0.0
    valid = 0

    # Buang transient agar titik awal berada di attraktor
    for _ in range(100):
        x = sine_pwlcm_map(x, p, beta)

    for _ in range(n):
        xn    = sine_pwlcm_map(x, p, beta)
        xn_dx = sine_pwlcm_map(x + dx, p, beta)
        d     = abs((xn_dx - xn) / dx)
        if d > 0:
            acc   += math.log(d)
            valid += 1
        x = xn

    return acc / valid if valid > 0 else 0.0


def _clamp(val: float, lo: float, hi: float) -> float:
    """Batasi nilai dalam rentang [lo, hi]."""
    return max(lo, min(hi, val))


def _perturb_near(best_keys: dict, mode: str) -> tuple:
    """
    Bangkitkan kandidat baru di sekitar best_keys menggunakan
    Gaussian perturbation (narrowing refinement).
    """
    std = _REFINE_STD
    x1   = _clamp(random.gauss(best_keys['x1'],   std), 0.00001, 0.99999)
    x2   = _clamp(random.gauss(best_keys['x2'],   std), 0.00001, 0.99999)
    beta = _clamp(random.gauss(best_keys['beta'],  std), 0.70000, 1.00000)

    if mode in ("mosipine", "pwlcm"):
        p = _clamp(random.gauss(best_keys['p'], std), 0.00001, 0.49999)
    else:
        p = 0.25   # tidak digunakan pada mode sine

    return x1, x2, p, beta


# ─────────────────────────────────────────────────────────────────────────────────
def predict_best_keys(mode: str = "mosipine", timeout: float = 10.0,
                      sample_size: int = 50_000):
    """
    Cari parameter kunci optimal (x1, x2, p, beta) selama `timeout` detik
    menggunakan Heuristic Search dengan Narrowing Refinement.
    Tujuan: maksimalkan Shannon Entropy keystream.

    Strategi:
      - Fase Global  : sampling fully-random hingga kandidat pertama ditemukan.
      - Fase Lokal   : setelah ada kandidat terbaik, perturbasi Gaussian di
                       sekitarnya (radius _REFINE_STD). Jika _REFINE_INTERVAL
                       iterasi berturut-turut tidak ada peningkatan, kembali ke
                       global search (restart otomatis).
      - Filter Lyapunov n=300 : hanya kandidat chaotic yang dievaluasi.
      - sample_size=50_000    : estimasi entropy stabil dan representatif.
      - Early-exit jika entropy >= 7.999.

    Return: (best_keys: dict, best_entropy: float)
    """
    start_time    = time.time()
    best_entropy  = -1.0
    best_keys     = None
    iter_awal     = 1000   # Sama dengan iter_bakar di video_core.py

    # Threshold early-exit jika entropi sudah hampir sempurna
    ENTROPY_TARGET = 7.999

    print(f"AI Optimizer v2: mode={mode.upper()}, timeout={timeout}s, "
          f"sample={sample_size:,} bytes, iter_awal={iter_awal}")
    print(f"  [Heuristic] Lyapunov n=300 | Narrowing std={_REFINE_STD} | "
          f"Restart setiap {_REFINE_INTERVAL} gagal berturut-turut")

    total_tries   = 0
    chaos_count   = 0
    no_improve    = 0      # hitung iterasi tanpa peningkatan (untuk restart)
    refine_mode   = False  # True = fase lokal, False = fase global

    while (time.time() - start_time) < timeout:

        # ── Tentukan kandidat: global random atau narrowing lokal ────────────
        if refine_mode and best_keys is not None:
            x1, x2, p, beta = _perturb_near(best_keys, mode)
        else:
            # Global random search
            x1   = random.uniform(0.00001, 0.99999)
            x2   = random.uniform(0.00001, 0.99999)
            p    = random.uniform(0.00001, 0.49999)
            beta = random.uniform(0.70000, 1.00000)   # Beta tinggi → chaos penuh

        total_tries += 1

        # ── Filter: hanya parameter yang chaotic (Lyapunov n=300) ────────────
        if mode in ("mosipine", "pwlcm"):
            lyap = _lyapunov_estimate(x1, p, beta, n=300)
            if lyap <= 0:
                no_improve += 1
                if no_improve >= _REFINE_INTERVAL:
                    refine_mode = False   # kembali ke global search
                    no_improve  = 0
                continue
            chaos_count += 1
        else:
            # Sine only — p tidak digunakan, validasi dengan p=0.25
            lyap = _lyapunov_estimate(x1, 0.25, beta, n=300)
            if lyap <= 0:
                no_improve += 1
                if no_improve >= _REFINE_INTERVAL:
                    refine_mode = False
                    no_improve  = 0
                continue
            chaos_count += 1

        # ── Bangkitkan keystream dan hitung entropy (sample_size=50_000) ─────
        try:
            if mode == "sine":
                ks = generate_keystream_sine_only(x1, x2, beta, iter_awal, sample_size)
            elif mode == "pwlcm":
                ks = generate_keystream_pwlcm_only(x1, x2, p, beta, iter_awal, sample_size)
            else:   # mosipine (default)
                ks = generate_keystream(x1, x2, p, beta, iter_awal, sample_size)

            current_entropy = calculate_entropy(ks)

            if current_entropy > best_entropy:
                best_entropy = current_entropy
                no_improve   = 0
                refine_mode  = True   # beralih ke fase lokal

                if mode == "sine":
                    best_keys = {'x1': x1, 'x2': x2, 'beta': beta}
                elif mode == "pwlcm":
                    best_keys = {'x1': x1, 'x2': x2, 'p': p, 'beta': beta}
                else:
                    best_keys = {'x1': x1, 'x2': x2, 'p': p, 'beta': beta}

                print(f"  [UPDATE] Entropi={best_entropy:.6f} | "
                      f"x1={x1:.6f}, x2={x2:.6f}, "
                      f"p={p:.6f}, beta={beta:.6f}")

                # Early exit jika sudah sangat mendekati ideal
                if best_entropy >= ENTROPY_TARGET:
                    print(f"  [OPTIMAL] Entropi {best_entropy:.6f} ≥ "
                          f"{ENTROPY_TARGET} — early exit.")
                    break
            else:
                no_improve += 1
                if no_improve >= _REFINE_INTERVAL:
                    refine_mode = False   # kembali ke global search
                    no_improve  = 0

        except Exception:
            no_improve += 1
            if no_improve >= _REFINE_INTERVAL:
                refine_mode = False
                no_improve  = 0
            continue  # Abaikan kandidat yang menyebabkan error numerik

    elapsed   = time.time() - start_time
    chaos_pct = (chaos_count / total_tries * 100) if total_tries > 0 else 0
    print(f"AI Selesai! Entropi terbaik: {best_entropy:.6f} | "
          f"{total_tries} kandidat ({chaos_pct:.1f}% chaotic) dalam {elapsed:.1f}s")
    return best_keys, best_entropy
