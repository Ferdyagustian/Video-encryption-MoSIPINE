---
name: NIST SP 800-22 Statistical Test Reference
description: Reference guide for all 15 NIST SP 800-22 Rev 1a statistical tests, including minimum bit requirements, interpretation, and common pitfalls for chaotic map generators.
---

# NIST SP 800-22 Rev 1a — Statistical Test Reference

## Overview
NIST SP 800-22 defines 15 statistical tests to evaluate the randomness of binary sequences.
A sequence "passes" a test if its **p-value ≥ α** (significance level, typically α = 0.01).

## Test Summary Table

| # | Test Name | Min Bits | Description |
|---|-----------|----------|-------------|
| 1 | **Frequency (Monobit)** | 100 | Proporsi 0 dan 1 harus mendekati 50:50 |
| 2 | **Frequency Within Block** | 100 | Proporsi 1 dalam blok M-bit harus ≈ M/2 |
| 3 | **Runs** | 100 | Jumlah run (urutan bit yang sama) harus sesuai ekspektasi |
| 4 | **Longest Run of Ones** | 128 | Run terpanjang dari "1" tidak boleh terlalu panjang |
| 5 | **Binary Matrix Rank** | 38,912 | Rank matriks biner harus terdistribusi sesuai |
| 6 | **Discrete Fourier Transform (Spectral)** | 1,000 | Tidak boleh ada peak dominan di domain frekuensi |
| 7 | **Non-Overlapping Template Matching** | ~1M | Kemunculan template tertentu harus sesuai ekspektasi |
| 8 | **Overlapping Template Matching** | ~1M | Sama tapi template boleh overlap |
| 9 | **Maurer's Universal** | 387,840 | Ukuran kompresi harus tinggi (entropi tinggi) |
| 10 | **Linear Complexity** | ~1M | LFSR terpendek harus sangat panjang |
| 11 | **Serial** | ~1M | Distribusi pola m-bit harus uniform. Menghasilkan 2 p-values. |
| 12 | **Approximate Entropy** | ~1M | Entropi blok harus tinggi dan konsisten |
| 13 | **Cumulative Sums** | 100 | Random walk kumulatif tidak boleh drift terlalu jauh |
| 14 | **Random Excursion** | ~1M | Jumlah kunjungan ke state tertentu dalam random walk. 8 p-values. |
| 15 | **Random Excursion Variant** | ~1M | Variasi frekuensi kunjungan di random walk. 18 p-values. |

## Common Pitfalls untuk Chaotic Map Generators

### 1. Finite-Precision Degradation
- Floating-point 64-bit memiliki presisi ~15 digit desimal
- Chaotic map bisa collapse ke periodic orbit setelah banyak iterasi
- **Solusi**: Perturbation/feedback injection setiap iterasi

### 2. Drift Injection Statis
- Menambahkan konstanta yang sama setiap iterasi = pattern
- **Solusi**: Gunakan feedback dari output sebelumnya

### 3. Bit Extraction Terlalu Sempit
- Hanya mengambil 8 dari 32 bit → membuang entropi
- **Solusi**: Cascade XOR Folding — XOR semua 4 byte

### 4. Sub-Sampling Tidak Cukup
- N_SKIP terlalu kecil → korelasi antar sample masih ada
- **Solusi**: N_SKIP minimal 12-20, tergantung autocorrelation

### 5. Post-Perturbation Evolution
- Setelah injeksi perturbasi, HARUS jalankan minimal 1 iterasi map lagi
- Jika langsung diambil, perturbasi belum melewati fungsi non-linear

## Interpretasi Hasil

- **p-value ≥ 0.01**: LULUS (sequence random pada α=0.01)
- **p-value < 0.01**: GAGAL (ada pola statistik yang terdeteksi)
- **p-value mendekati 1.0**: Terlalu "perfect" — bisa jadi suspicious

## Multi-Stream Testing (Rekomendasi NIST)
- Bagi bitstream panjang menjadi N stream
- Uji masing-masing stream
- Hitung proporsi stream yang lulus
- Proporsi harus ≥ (1 - α) - 3√(α(1-α)/N)
- Contoh: Untuk N=10 stream, α=0.01 → threshold ≈ 0.870
