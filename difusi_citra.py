import numpy as np
import cv2
import matplotlib.pyplot as plt
import time

# Memanggil fungsi mesin keystream dari file induk Anda
from sipine import generate_keystream

def difusi_cbc_xor(img_flat, keystream):
    """
    Melakukan proses Difusi menggunakan teknik Cipher Block Chaining (CBC).
    Setiap piksel di-XOR dengan Kunci, lalu di-XOR lagi dengan piksel terenkripsi sebelumnya.
    Ini menjamin efek "Butterfly" (Sensitivitas Plaintext) yang mutlak.
    """
    total_pixel = len(img_flat)
    cipher_flat = np.zeros(total_pixel, dtype=np.uint8)
    
    # Nilai Vektor Inisialisasi (Bisa dianggap sebagai bagian dari kunci rahasia)
    c_prev = 128 
    
    # Proses Difusi berantai
    for i in range(total_pixel):
        # Operasi XOR (^) antara: Piksel Asli ^ Kunci Acak ^ Piksel Sandi Sebelumnya
        cipher_flat[i] = img_flat[i] ^ keystream[i] ^ c_prev
        
        # Simpan nilai saat ini untuk mengunci piksel berikutnya
        c_prev = cipher_flat[i]
        
    return cipher_flat

def enkripsi_difusi(nama_file_scrambled):
    print(f"Membaca gambar permutasi: {nama_file_scrambled}...")
    
    # Baca gambar hasil tahapan sebelumnya
    img_scrambled = cv2.imread(nama_file_scrambled, cv2.IMREAD_GRAYSCALE)
    if img_scrambled is None:
        print("GAGAL: File gambar permutasi tidak ditemukan!")
        return

    tinggi, lebar = img_scrambled.shape
    total_pixel = tinggi * lebar
    print(f"Resolusi: {lebar} x {tinggi} ({total_pixel} piksel)")

    waktu_mulai = time.time()

    # 1. Ratakan matriks 2D menjadi 1D untuk diproses
    img_flat = img_scrambled.flatten()

    # 2. Bangkitkan Keystream dari Modulo-Sine-PWLCM
    # (Pastikan argumen sesuai dengan file sipine.py Anda)
    key_x1 = 0.123456789   
    key_x2 = 0.987654321
    key_p = 0.3678        
    key_beta = 0.99       
    iter_buang = 1000  
    
    print("Membangkitkan Keystream (Kunci 8-bit)... Ini mungkin memakan waktu beberapa detik.")
    kunci_acak = generate_keystream(key_x1, key_x2, key_p, key_beta, iter_buang, total_pixel)

    # 3. Eksekusi Difusi CBC-XOR
    print("Melakukan proses Difusi warna piksel...")
    cipher_flat = difusi_cbc_xor(img_flat, kunci_acak)

    # 4. Kembalikan bentuk ke Matriks 2D Citra
    cipher_img = cipher_flat.reshape((tinggi, lebar))
    
    durasi = time.time() - waktu_mulai
    print(f"Difusi selesai dalam {durasi:.3f} detik!")

    # 5. Tampilkan Perbandingan Visual dan Simpan
    plt.figure(figsize=(10, 5))
    
    plt.subplot(1, 2, 1)
    plt.title("Gambar Permutasi (Input)")
    plt.imshow(img_scrambled, cmap='gray')
    plt.axis('off')

    plt.subplot(1, 2, 2)
    plt.title("Hasil Difusi Final (Cipher-Image)")
    plt.imshow(cipher_img, cmap='gray')
    plt.axis('off')

    plt.tight_layout()
    plt.show()

    # Simpan hasil akhir enkripsi (Wajib menggunakan format .png agar piksel tidak terkompresi/rusak)
    cv2.imwrite("citra_terenkripsi_final.png", cipher_img)
    print("Gambar terenkripsi berhasil disimpan sebagai 'citra_terenkripsi_final.png'")

if __name__ == "__main__":
    # Targetkan file gambar yang sudah diacak posisinya dari skrip sebelumnya
    file_target = "hasil_permutasi.png" 
    enkripsi_difusi(file_target)