import cv2
import numpy as np
import matplotlib.pyplot as plt

def hitung_korelasi(img, arah='horizontal', jumlah_sampel=4000):
    """
    Mengambil pasangan piksel yang bersebelahan secara acak dan menghitung
    Koefisien Korelasi Pearson.
    """
    h, w = img.shape
    
    # Membangkitkan titik koordinat acak
    if arah == 'horizontal':
        baris = np.random.randint(0, h, jumlah_sampel)
        kolom = np.random.randint(0, w - 1, jumlah_sampel) # w-1 agar tidak mentok di kanan
        x = img[baris, kolom]
        y = img[baris, kolom + 1]
        
    elif arah == 'vertikal':
        baris = np.random.randint(0, h - 1, jumlah_sampel) # h-1 agar tidak mentok di bawah
        kolom = np.random.randint(0, w, jumlah_sampel)
        x = img[baris, kolom]
        y = img[baris + 1, kolom]
        
    elif arah == 'diagonal':
        baris = np.random.randint(0, h - 1, jumlah_sampel)
        kolom = np.random.randint(0, w - 1, jumlah_sampel)
        x = img[baris, kolom]
        y = img[baris + 1, kolom + 1]
        
    else:
        raise ValueError("Arah tidak valid!")

    # Kalkulasi Korelasi Pearson menggunakan NumPy
    korelasi = np.corrcoef(x, y)[0, 1]
    
    return korelasi, x, y

def jalankan_uji_korelasi(file_asli, file_cipher):
    print("=== MENGANALISIS KORELASI PIKSEL (H, V, D) ===")
    
    # Baca citra (Pastikan ada di folder yang sama)
    img_asli = cv2.imread(file_asli, cv2.IMREAD_GRAYSCALE)
    img_cipher = cv2.imread(file_cipher, cv2.IMREAD_GRAYSCALE)
    
    if img_asli is None or img_cipher is None:
        print("GAGAL: File gambar tidak ditemukan!")
        return

    # Jumlah sampel standar jurnal (3000 - 5000)
    N_SAMPEL = 4000
    arah_list = ['horizontal', 'vertikal', 'diagonal']
    
    hasil_asli = {}
    hasil_cipher = {}
    plot_data = {}

    print(f"Mengambil {N_SAMPEL} sampel acak untuk setiap arah...\n")
    
    # Menghitung korelasi
    for arah in arah_list:
        corr_a, x_a, y_a = hitung_korelasi(img_asli, arah, N_SAMPEL)
        corr_c, x_c, y_c = hitung_korelasi(img_cipher, arah, N_SAMPEL)
        
        hasil_asli[arah] = corr_a
        hasil_cipher[arah] = corr_c
        
        plot_data[arah] = {'asli_x': x_a, 'asli_y': y_a, 'cipher_x': x_c, 'cipher_y': y_c}

    # === CETAK TABEL LAPORAN KE TERMINAL ===
    print("-" * 65)
    print(f"{'Arah Uji':<15} | {'Citra Asli':<20} | {'Citra Terenkripsi':<20}")
    print("-" * 65)
    for arah in arah_list:
        print(f"{arah.capitalize():<15} | {hasil_asli[arah]:<20.5f} | {hasil_cipher[arah]:<20.5f}")
    print("-" * 65)

    # Validasi Kelulusan
    rata_rata_cipher = np.mean([abs(hasil_cipher['horizontal']), abs(hasil_cipher['vertikal']), abs(hasil_cipher['diagonal'])])
    if rata_rata_cipher <= 0.05:
        print("\n[STATUS: LULUS] Korelasi citra terenkripsi hancur mendekati angka 0.000!")
    else:
        print("\n[STATUS: GAGAL] Masih ada korelasi yang terdeteksi.")

    # === VISUALISASI GRAFIK SCATTER (SCATTER PLOT) ===
    # Ini adalah grafik wajib untuk masuk ke jurnal
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    fig.suptitle('Distribusi Korelasi Piksel Bersebelahan', fontsize=16)

    baris_judul = ['Citra Asli (Plain-image)', 'Citra Terenkripsi (Cipher-image)']
    
    for i, arah in enumerate(arah_list):
        # Baris 1: Citra Asli
        axes[0, i].scatter(plot_data[arah]['asli_x'], plot_data[arah]['asli_y'], s=2, c='blue', alpha=0.5)
        axes[0, i].set_title(f"{arah.capitalize()}\n(Korelasi: {hasil_asli[arah]:.4f})")
        axes[0, i].set_xlabel("Piksel (x,y)")
        axes[0, i].set_ylabel("Piksel Tetangga")
        axes[0, i].set_xlim(0, 255); axes[0, i].set_ylim(0, 255)
        
        # Baris 2: Citra Terenkripsi
        axes[1, i].scatter(plot_data[arah]['cipher_x'], plot_data[arah]['cipher_y'], s=2, c='red', alpha=0.5)
        axes[1, i].set_title(f"{arah.capitalize()}\n(Korelasi: {hasil_cipher[arah]:.4f})")
        axes[1, i].set_xlabel("Piksel (x,y)")
        axes[1, i].set_ylabel("Piksel Tetangga")
        axes[1, i].set_xlim(0, 255); axes[1, i].set_ylim(0, 255)

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.show()

if __name__ == "__main__":
    # Ganti dengan nama file gambar Anda
    file_gambar_asli = "kucing.jpg" 
    file_gambar_sandi = "citra_terenkripsi_final.png" 
    
    jalankan_uji_korelasi(file_gambar_asli, file_gambar_sandi)