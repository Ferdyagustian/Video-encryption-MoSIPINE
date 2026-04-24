import cv2
import numpy as np
import time

# Hanya mengimpor mesin utama dari sipine
from sipine import sine_pwlcm_map, generate_keystream

def permutasi_citra(img_flat, total_pixel):
    x = 0.555555
    p = 0.3678
    beta = 0.99
    chaos_values = np.zeros(total_pixel)
    
    for _ in range(1000):
        x = sine_pwlcm_map(x, p, beta)
    for i in range(total_pixel):
        x = sine_pwlcm_map(x, p, beta)
        chaos_values[i] = x
        
    indeks_acak = np.argsort(chaos_values)
    img_scrambled_flat = np.zeros_like(img_flat)
    img_scrambled_flat[indeks_acak] = img_flat
    return img_scrambled_flat

def difusi(img_scrambled_flat, total_pixel):
    kunci_acak = generate_keystream(0.123456789, 0.987654321, 0.3678, 0.99, 1000, total_pixel)
    cipher_flat = np.zeros(total_pixel, dtype=np.uint8)
    c_prev = 128
    
    for i in range(total_pixel):
        cipher_flat[i] = img_scrambled_flat[i] ^ kunci_acak[i] ^ c_prev
        c_prev = cipher_flat[i]
    return cipher_flat

def hitung_npcr_uaci(c1_flat, c2_flat):
    # WAJIB int32 agar tidak terjadi kebocoran memori saat pengurangan (10 - 200 = -190)
    c1_int = c1_flat.astype(np.int32)
    c2_int = c2_flat.astype(np.int32)
    total_pixel = len(c1_int)

    # 1. NPCR (Persentase jumlah piksel yang berubah)
    array_beda = (c1_int != c2_int).astype(np.int32)
    npcr = (np.sum(array_beda) / total_pixel) * 100.0

    # 2. UACI (Rata-rata intensitas perubahannya)
    selisih_absolut = np.abs(c1_int - c2_int)
    uaci = (np.sum(selisih_absolut) / (255.0 * total_pixel)) * 100.0

    return npcr, uaci

def uji_serangan_diferensial(nama_file):
    print(f"=== UJI AVALANCHE EFFECT (NPCR & UACI) ===")
    
    img = cv2.imread(nama_file, cv2.IMREAD_GRAYSCALE)
    if img is None:
        print(f"GAGAL: File '{nama_file}' tidak ditemukan.")
        return
        
    total_pixel = img.shape[0] * img.shape[1]
    img_flat = img.flatten()

    waktu_mulai = time.time()

    # LANGKAH 1: Enkripsi Gambar Asli (Cipher 1)
    print("\n[1] Mengenkripsi gambar asli...")
    hasil_permutasi_1 = permutasi_citra(img_flat, total_pixel)
    cipher_1 = difusi(hasil_permutasi_1, total_pixel)

    # LANGKAH 2: Ubah 1 Piksel Saja pada Gambar Asli
    print("[2] Mengubah 1 piksel pada gambar asli secara diam-diam...")
    img_flat_modifikasi = np.copy(img_flat)
    
    # Menambah nilai piksel ke-0 dengan angka 1 (memanipulasi LSB)
    piksel_lama = img_flat_modifikasi[0]
    img_flat_modifikasi[0] = (piksel_lama + 1) % 256 
    
    # LANGKAH 3: Enkripsi Gambar yang Dimodifikasi (Cipher 2)
    print("[3] Mengenkripsi gambar yang telah dimodifikasi...")
    hasil_permutasi_2 = permutasi_citra(img_flat_modifikasi, total_pixel)
    cipher_2 = difusi(hasil_permutasi_2, total_pixel)

    # LANGKAH 4: Bandingkan Cipher 1 dan Cipher 2
    print("\n[4] Membandingkan perbedaan antara Cipher 1 dan Cipher 2...")
    npcr, uaci = hitung_npcr_uaci(cipher_1, cipher_2)
    durasi = time.time() - waktu_mulai

    # --- HASIL LAPORAN ---
    print("\n" + "="*50)
    print(f"NPCR : {npcr:.5f} %  (Standar Lulus: ~99.6094%)")
    print(f"UACI : {uaci:.5f} %  (Standar Lulus: ~33.4635%)")
    print(f"Waktu Uji: {durasi:.2f} detik")
    print("="*50)
    
    if npcr > 99.5:
        print("\n[KESIMPULAN: LULUS]")
        print("Satu perubahan piksel kecil menyebabkan kerusakan total pada seluruh hasil enkripsi!")
    else:
        print("\n[KESIMPULAN: GAGAL]")

if __name__ == "__main__":
    # Ganti dengan gambar target Anda
    file_target = "kucing.jpg" 
    uji_serangan_diferensial(file_target)