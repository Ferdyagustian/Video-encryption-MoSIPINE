import cv2
import numpy as np
import matplotlib.pyplot as plt

def hitung_entropi(img_flat):
    """
    Fungsi untuk menghitung Entropi Informasi Shannon.
    H = - sum( p(i) * log2(p(i)) )
    """
    # 1. Hitung frekuensi kemunculan tiap nilai piksel (0-255)
    nilai_unik, jumlah = np.unique(img_flat, return_counts=True)
    
    # 2. Hitung probabilitas tiap nilai
    probabilitas = jumlah / len(img_flat)
    
    # 3. Hitung Entropi
    entropi = -np.sum(probabilitas * np.log2(probabilitas))
    return entropi

def analisis_histogram_dan_entropi(file_asli, file_cipher):
    print("=== MENGANALISIS STATISTIK DAN ENTROPI CITRA ===")

    # A. BACA FILE GAMBAR
    img_asli = cv2.imread(file_asli, cv2.IMREAD_GRAYSCALE)
    if img_asli is None:
        print(f"Error: File '{file_asli}' tidak ditemukan!")
        return

    img_cipher = cv2.imread(file_cipher, cv2.IMREAD_GRAYSCALE)
    if img_cipher is None:
        print(f"Error: File '{file_cipher}' tidak ditemukan!")
        return

    # Ratakan matriks untuk perhitungan matematis
    flat_asli = img_asli.flatten()
    flat_cipher = img_cipher.flatten()

    # B. HITUNG ENTROPI INFORMASI
    print("\nMenghitung Entropi...")
    entropi_asli = hitung_entropi(flat_asli)
    entropi_cipher = hitung_entropi(flat_cipher)

    print("-" * 50)
    print(f"Entropi Citra Asli       : {entropi_asli:.4f} bit")
    print(f"Entropi Citra Terenkripsi: {entropi_cipher:.4f} bit")
    print("-" * 50)
    
    # Evaluasi Akademis
    if entropi_cipher >= 7.99:
         print("[STATUS LULUS] Entropi sangat mendekati nilai ideal 8.0.")
    else:
         print("[STATUS GAGAL] Entropi masih kurang.")

    # C. PLOTTING VISUALISASI HISTOGRAM
    plt.figure(figsize=(12, 8))
    plt.suptitle("Analisis Keamanan Statistik Enkripsi Citra", fontsize=16)

    # --- Kolom Kiri: Citra Asli ---
    plt.subplot(2, 2, 1)
    plt.title(f"Citra Asli\n(Entropi: {entropi_asli:.4f})")
    plt.imshow(img_asli, cmap='gray')
    plt.axis('off')

    plt.subplot(2, 2, 3)
    plt.title("Histogram Citra Asli")
    # Membuat grafik batang (bins=256 karena rentang warna 0-255)
    plt.hist(flat_asli, bins=256, range=[0, 256], color='blue', alpha=0.7)
    plt.xlabel("Intensitas Piksel (0-255)")
    plt.ylabel("Jumlah Frekuensi")
    plt.grid(alpha=0.3)

    # --- Kolom Kanan: Citra Terenkripsi ---
    plt.subplot(2, 2, 2)
    plt.title(f"Citra Terenkripsi (Difusi)\n(Entropi: {entropi_cipher:.4f})")
    plt.imshow(img_cipher, cmap='gray')
    plt.axis('off')

    plt.subplot(2, 2, 4)
    plt.title("Histogram Citra Terenkripsi")
    plt.hist(flat_cipher, bins=256, range=[0, 256], color='red', alpha=0.7)
    plt.xlabel("Intensitas Piksel (0-255)")
    plt.ylabel("Jumlah Frekuensi")
    plt.grid(alpha=0.3)

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.show()

if __name__ == "__main__":
    # Ganti dengan nama file gambar Anda yang sebenarnya
    file_gambar_asli = "kucing.jpg" 
    file_gambar_sandi = "citra_terenkripsi_final.png" 
    
    analisis_histogram_dan_entropi(file_gambar_asli, file_gambar_sandi)