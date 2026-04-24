import numpy as np

def sine_pwlcm_map(x, p, beta):

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

    # Injeksi Skalar Modulo (Flattening)
    x_next = (beta * np.sin(np.pi * f_x) * 987676766.3232) % 1.0 #sebelumnya -->  beta * np.sin(np.pi * f_x)
    return x_next

def generate_keystream(x0_1, x0_2, p, beta, iter_awal, total):

    x1 = x0_1
    x2 = x0_2
    keystream_array = []
    
    #jumlah iterasi yang dibuang di sela-sela pengambilan bit
    N_SKIP = 12 

    # 1. Pemanasan Sistem (Membuang efek transient/kondisi awal)
    for _ in range(iter_awal):
        x1 = sine_pwlcm_map(x1, p, beta)
        x2 = sine_pwlcm_map(x2, p, beta)

    # 2. Pembangkitan Array Kunci
    k_prev = 0
    for _ in range(total):
        # Fase Aduk (Sub-Sampling)
        for _ in range(N_SKIP):
            x1 = sine_pwlcm_map(x1, p, beta)
            x2 = sine_pwlcm_map(x2, p, beta)
        
        # Injeksi Umpan Balik (Mencegah Loop Periodik)
        x1 = (x1 + (k_prev / 256.0)) % 1.0
        x2 = (x2 + x1) % 1.0

        # Evolusi terakhir sebelum ekstraksi
        x1 = sine_pwlcm_map(x1, p, beta)
        x2 = sine_pwlcm_map(x2, p, beta)

        # Konversi ke integer 32-bit besar
        val1 = int(x1 * 4294967296.0) 
        val2 = int(x2 * 4294967296.0)
        
        # Ekstraksi dan Cascade XOR Folding
        k1 = ((val1 >> 24) & 255) ^ ((val1 >> 16) & 255) ^ ((val1 >> 8) & 255) ^ (val1 & 255)
        k2 = ((val2 >> 24) & 255) ^ ((val2 >> 16) & 255) ^ ((val2 >> 8) & 255) ^ (val2 & 255)
        
        # Dual-State Mixing (Campurkan kedua kunci)
        k_prev = k1 ^ k2
        keystream_array.append(k_prev)

    return keystream_array

if __name__ == "__main__":
    print("=== MENGUJI MODUL SINE-PWLCM (MSPM) ===")
    
    # Parameter Secret Key
    key_x1 = 0.123456789   #(boleh angka berapa saja asalkan rentang 0 < x < 1)
    key_x2 = 0.987654321   #(boleh angka berapa saja asalkan rentang 0 < x < 1)
    key_p = 0.25           #(boleh angka berapa saja asalkan rentang 0 < p < 0.5)
    key_beta = 0.99        #(boleh angka berapa saja asalkan rentang 0 < beta < 1 , dengan idealnya direntang 0.85 <= 1)
    iter_buang = 1000    

    # Simulasi Citra (Gambar) Dummy
    citra_asli = [105, 200, 55, 128, 255]
    jumlah_piksel = len(citra_asli)

    #  Bangkitkan Kunci (Keystream)
    print("Sedang membangkitkan kunci...")
    kunci_acak = generate_keystream(key_x1, key_x2, key_p, key_beta, iter_buang, jumlah_piksel)
    
    # Proses Enkripsi (XOR Plaintext dengan Kunci)
    citra_enkripsi = []
    for i in range(jumlah_piksel):
        cipher_pixel = citra_asli[i] ^ kunci_acak[i]
        citra_enkripsi.append(cipher_pixel)
        
    # 3. Proses Dekripsi (XOR Ciphertext dengan Kunci yang sama)
    citra_dekripsi = []
    for i in range(jumlah_piksel):
        plain_pixel = citra_enkripsi[i] ^ kunci_acak[i]
        citra_dekripsi.append(plain_pixel)

    # Tampilkan Hasil Visual di Terminal
    print("-" * 50)
    print(f"1. Kunci Keystream (8-bit) : {kunci_acak}")
    print(f"2. Citra Asli (Plaintext)  : {citra_asli}")
    print(f"3. Citra Tersandi (Cipher) : {citra_enkripsi}")
    print(f"4. Citra Pulih (Decrypted) : {citra_dekripsi}")
    print("-" * 50)
    
    # Validasi Keberhasilan
    if citra_asli == citra_dekripsi:
        print("[STATUS] LULUS! Algoritma sempurna. Dekripsi mengembalikan citra 100% tanpa cacat.")
    else:
        print("[STATUS] GAGAL! Terjadi kesalahan kehilangan bit.")