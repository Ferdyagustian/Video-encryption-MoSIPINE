import numpy as np
import matplotlib.pyplot as plt

# Definisi Fungsi Komposisi Sine-PWLCM
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

    x_next = (beta * np.sin(np.pi * f_x) * 32342.3232) % 1.0
    return x_next

# Parameter untuk Bifurkasi
iterasi_buang = 2000
iterasi_plot = 1500
x0 = 0.123456
beta = 0.99  

# Rentang parameter p dari 0.01 hingga 0.49 (p tidak boleh 0 atau >= 0.5)
p_values = np.linspace(0.01, 0.49, 1000)
x_plot = []
p_plot = []

for p in p_values:
    x = x0
    # Buang iterasi awal
    for _ in range(iterasi_buang):
        x = sine_pwlcm_map(x, p, beta)
    
    # Simpan titik untuk diplot
    for _ in range(iterasi_plot):
        x = sine_pwlcm_map(x, p, beta)
        x_plot.append(x)
        p_plot.append(p)

# Menampilkan Grafik
plt.figure(figsize=(10, 6))
plt.scatter(p_plot, x_plot, s=0.1, color='blue', alpha=0.5)
plt.title("Diagram Bifurkasi ModuloSine-PWLCM terhadap parameter p")
plt.xlabel("Parameter p")
plt.ylabel("Nilai x_n")
plt.show()