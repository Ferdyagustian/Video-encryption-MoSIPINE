import numpy as np
import matplotlib.pyplot as plt
from sipine import sine_pwlcm_map  #

# Parameter Utama
x0 = 0.123456
beta = 0.99
iterasi_buang = 2000
iterasi = 1000
dx = 1e-7  # Delta x untuk turunan numerik

# Menggunakan 1000 titik agar resolusi grafik sama halusnya dengan diagram bifurkasi
p_values = np.linspace(0.01, 0.49, 1000)
lyapunov_exponents = []

print("Menghitung Eksponen Lyapunov. Mohon tunggu...")

for p in p_values:
    x = x0
    # Buang iterasi awal
    for _ in range(iterasi_buang):
        x = sine_pwlcm_map(x, p, beta)

    sum_log_deriv = 0
    valid_iters = 0
    
    for _ in range(iterasi):
        x_next = sine_pwlcm_map(x, p, beta)
        x_next_dx = sine_pwlcm_map(x + dx, p, beta)
        
        # Turunan numerik
        turunan = abs((x_next_dx - x_next) / dx)
        
        # Menghindari log(0) untuk mencegah error saat sistem menyentuh nilai kritis
        if turunan > 0:
            sum_log_deriv += np.log(turunan)
            valid_iters += 1
            
        x = x_next
        
    # Menghitung rata-rata Eksponen Lyapunov
    if valid_iters > 0:
        lyapunov_exponents.append(sum_log_deriv / valid_iters)
    else:
        lyapunov_exponents.append(0)

# Menampilkan Grafik
plt.figure(figsize=(12, 6))
plt.plot(p_values, lyapunov_exponents, color='red', linewidth=1.5)
plt.axhline(0, color='black', linestyle='--')  # Garis batas nol
plt.title("Diagram Eksponen Lyapunov Modulo Sine-PWLCM terhadap parameter p")
plt.xlabel("Parameter p")
plt.ylabel("Eksponen Lyapunov (\u03bc)")
plt.xlim(0, 0.5)
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()