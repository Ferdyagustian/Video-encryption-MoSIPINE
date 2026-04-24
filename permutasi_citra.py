import numpy as np
import cv2
import matplotlib.pyplot as plt
import time

# Memanggil fungsi MSPM dari file sipine.py Anda
from sipine import sine_pwlcm_map 

def generate_permutation_indices(x0, p, beta, iter_awal, total_pixel):
    """
    Fungsi untuk menciptakan peta koordinat acak menggunakan MSPM.
    Berbeda dengan keystream, di sini kita mengambil nilai desimal (float) murninya.
    """
    x = x0
    chaos_values = np.zeros(total_pixel)
    
    # 1. Pemanasan (Transient Discard)
    for _ in range(iter_awal):
        x = sine_pwlcm_map(x, p, beta)
        
    # 2. Ekstraksi Nilai Chaos
    for i in range(total_pixel):
        x = sine_pwlcm_map(x, p, beta)
        chaos_values[i] = x
        
    indeks_acak = np.argsort(chaos_values)
    return indeks_acak

def permutasi_gambar(nama_file_gambar):
    print(f"Membaca gambar: {nama_file_gambar}...")
    
    # 1. Baca gambar dalam format Grayscale (Hitam Putih) agar lebih mudah dipahami
    img = cv2.imread(nama_file_gambar, cv2.IMREAD_GRAYSCALE)
    if img is None:
        print("GAGAL: File gambar tidak ditemukan!")
        return

    tinggi, lebar = img.shape
    total_pixel = tinggi * lebar
    print(f"Resolusi: {lebar} x {tinggi} ({total_pixel} piksel)")

    waktu_mulai = time.time()

    # 2. Ratakan gambar 2D menjadi 1D (Array lurus)
    img_flat = img.flatten()

    # 3. Bangkitkan Indeks Acak (Kunci Permutasi)
    kunci_x0 = 0.555555
    kunci_p = 0.3678
    kunci_beta = 0.99
    
    print("Membangkitkan peta koordinat chaos...")
    indeks_acak = generate_permutation_indices(kunci_x0, kunci_p, kunci_beta, 1000, total_pixel)

    # 4. PROSES PERMUTASI (Pengacakan Posisi)
    print("Mengacak posisi piksel...")
    img_scrambled_flat = np.zeros_like(img_flat)
    
    # Teknik pemetaan 1-ke-1 super cepat menggunakan NumPy
    img_scrambled_flat[indeks_acak] = img_flat

    # 5. Kembalikan bentuknya ke 2D
    img_scrambled = img_scrambled_flat.reshape((tinggi, lebar))
    
    durasi = time.time() - waktu_mulai
    print(f"Permutasi selesai dalam {durasi:.3f} detik!")

    # 6. Tampilkan Hasil Visual
    plt.figure(figsize=(10, 5))
    
    plt.subplot(1, 2, 1)
    plt.title("Gambar Asli (Plain-image)")
    plt.imshow(img, cmap='gray')
    plt.axis('off')

    plt.subplot(1, 2, 2)
    plt.title("Hasil Permutasi (Scrambled)")
    plt.imshow(img_scrambled, cmap='gray')
    plt.axis('off')

    plt.tight_layout()

    # (Opsional) Simpan hasil gambar sebelum plt.show() memblokir eksekusi
    cv2.imwrite("hasil_permutasi.png", img_scrambled)
    print("Gambar hasil permutasi berhasil disimpan sebagai 'hasil_permutasi.png'")

    plt.show()

if __name__ == "__main__":
    # GANTI 'kucing.jpg' DENGAN NAMA FILE GAMBAR YANG ADA DI LAPTOP ANDA
    file_target = "kucing.jpg" 
    permutasi_gambar(file_target)