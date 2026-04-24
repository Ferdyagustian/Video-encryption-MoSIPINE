from PIL import Image
from tkinter.filedialog import askdirectory
from tkinter import *
import numpy as np
import PIL, os, timeit
os.makedirs('Tempat_gambar', exist_ok=True)
import matplotlib.pyplot as plt
from tkinter import scrolledtext
from scipy.stats import pearsonr
from sklearn.metrics import mean_squared_error
import collections, skimage, math
from tkinter import filedialog
import tkinter as tk
import skimage.measure
from sipine import sine_pwlcm_map, generate_keystream

def ujiuniform(Red, Green, Blue, tinggi, lebar):
    E = tinggi*lebar/256
    Hasilr, Hasilg, Hasilb = 0, 0, 0
    Ar = np.zeros(256)
    Ag = np.zeros(256)
    Ab = np.zeros(256)
    i = 0
    elements_count = collections.Counter(Red)
    for key, value in elements_count.items():
        Ar[i] = value
        i+=1
    i = 0
    elements_count = collections.Counter(Green)
    for key, value in elements_count.items():
        Ag[i] = value
        i+=1
    i = 0
    elements_count = collections.Counter(Blue)
    for key, value in elements_count.items():
        Ab[i] = value
        i+=1
    for i in range(256):
        Hitungr = ((Ar[i]-E)**2)/E
        Hasilr = Hasilr + Hitungr
        Hitungg = ((Ag[i]-E)**2)/E
        Hasilg = Hasilg + Hitungg
        Hitungb = ((Ab[i]-E)**2)/E
        Hasilb = Hasilb + Hitungb
    return(Hasilr, Hasilg, Hasilb)

def uaci(loc1,loc2):
    image1 = loc1
    image2 = loc2
    pixel1=image1.load()
    pixel2=image2.load()
    width,height=image1.size
    value1=0.0
    value2=0.0
    value3=0.0
    for y in range(0,height):
        for x in range(0,width):
            value1=(abs(pixel1[x,y][0]-pixel2[x,y][0])/255)+value1
            value2=(abs(pixel1[x,y][1]-pixel2[x,y][1])/255)+value2
            value3=(abs(pixel1[x,y][2]-pixel2[x,y][2])/255)+value3

    value1= (value1/(width*height))*100
    value11= str(value1)
    value2= (value2/(width*height))*100
    value22= str(value2)
    value3= (value3/(width*height))*100
    value33= str(value3)
    value4 = (value1+value2+value3)/3
    value4 = float(value4)
    value44 = str(value4)
    
    return value44

def rateofchange(height,width,pixel1,pixel2,matrix,i):

    for y in range(0,height):
        for x in range(0,width):
            #print(x,y)
            if pixel1[x,y][i] == pixel2[x,y][i]:
                matrix[x,y]=0
            else:
                matrix[x,y]=1
    return matrix

def sumofpixel(height,width,pixel1,pixel2,ematrix,i):
    matrix=rateofchange(height,width,pixel1,pixel2,ematrix,i)
    psum=0
    for y in range(0,height):
        for x in range(0,width):
            psum=matrix[x,y]+psum
    return psum

def npcrv(loc1,loc2):
    c1 = loc1
    c2 = loc2
    width, height = c1.size
    pixel1 = c1.load()
    pixel2 = c2.load()
    ematrix = np.empty([width, height])
    hasil=(((sumofpixel(height,width,pixel1,pixel2,ematrix,0)/(height*width))*100)+((sumofpixel(height,width,pixel1,pixel2,ematrix,1)/(height*width))*100)+((sumofpixel(height,width,pixel1,pixel2,ematrix,2)/(height*width))*100))/3
    per= str(hasil)
    return per

def nilai(x):
    a = int(x)
    return a

def XOR(x,y):
  if x == '1' and y == '1':
    return '0'
  elif x == '1' and y == '0':
    return '1'
  elif x == '0' and y == '1':
    return '1'
  elif x == '0' and y == '0':
    return '0'

def to_int(x):
    return ord(x)

def to_binary(x):
      a = str(bin(x))[2:]
      if len(a) == 8:
          return a
      else:
          b = 8 - len(a)
          return '0'*b + a
      
def to_decimal(n):
    return int(n, 2)

def pencet1():     
    root = Toplevel()
    root.geometry("600x600")
    root.title("Program Enkripsi Citra Modulo Sine-PWLCM")
    
    Main = Frame(root, width = 600, height = 600)
    Main.pack()

    Main1 = Frame(Main, width = 600, height = 600)
    Main1.pack(side = LEFT)

    
    F1 = Frame(Main1, width = 600, height = 20)
    F1.pack()
    
    F3 = Frame(Main1, width = 600, height = 200)
    F3.pack(side=TOP)
    
    F5 = Frame(Main1, width = 600, height = 20)
    F5.pack(side = TOP)
    
    F4 = Frame(Main1, width = 600, height = 50)
    F4.pack(side=TOP)
    
    F2 = Frame(Main1, width = 600, height = 200)
    F2.pack(side = TOP)
    
    F6 = Frame(Main1, width = 600, height = 100)
    F6.pack(side = BOTTOM)
    
    
    def OpenFile():
        c1 = Canvas(F2, height = 250, width = 250)
        c1.grid(row=5, column=0)
        
        c3 = Canvas(F2, height = 250, width = 250)
        c3.grid(row = 5, column = 3)
        
        File = filedialog.askopenfilename(initialdir = "/",title = "Select file")
        im = PIL.Image.open(File, 'r')
        im.save("Tempat_gambar/Citra - Untuk Enkripsi.png")
        im = im.resize((200,200)) 
        im.save("Tempat_gambar/Citra - Untuk Enkripsi.gif")
        gif1 = PhotoImage(file="Tempat_gambar/Citra - Untuk Enkripsi.gif")
        label212 = Label(c1, image=gif1)
        label212.image = gif1
        label212.grid(row=3, column=1)
        b10.config(state = ACTIVE)
        
    tampilan = Label(F4, text = "Proses Enkripsi", font = ("Segoe UI", 15))
    tampilan.place(x = 228, y = 0)
    
    Nama = Label(F1, font=("Segoe UI",16), text="Parameter Chaos", fg="Black")
    Nama.grid(row=0, column=0)
    
    def encrypt():
        c3 = Canvas(F2, height = 250, width = 250)
        c3.grid(row = 5, column = 3)
        tic=timeit.default_timer()
        im = PIL.Image.open("Tempat_gambar/Citra - Untuk Enkripsi.png", 'r')
        width, height = im.size
        # Konversi gambar ke grayscale L list pixel
        pixel_values = list(im.convert("L").getdata())
        im.load()
        array = np.asarray(im)
        P_g = []
    
        P_g = np.array([nilai(pixel_values[i]) for i in range(height*width)]).reshape(height, width)

        # Ambil parameter dari input GUI
        x0_1_val = float(input_x0_1.get())
        x0_2_val = float(input_x0_2.get())
        p_val = float(input_p.get())
        beta_val = float(input_beta.get())
        iterasi = int(input_i.get())

        # Bangkitkan keystream menggunakan Modulo Sine-PWLCM (sipine.py)
        total = height * width
        kunci_acak = generate_keystream(x0_1_val, x0_2_val, p_val, beta_val, iterasi, total)
        A = np.array(kunci_acak).reshape(height, width)
        
        # Enkripsi XOR langsung
        enkripsi_g = np.zeros((height,width), dtype=np.uint8)
        for i in range (height):
            for j in range (width):
                enkripsi_g[i,j] = int(P_g[i][j]) ^ int(A[i][j])
    
        GambarCoba = PIL.Image.fromarray(enkripsi_g, mode='L')
        GambarCoba.save("Tempat_gambar/Citra - Hasil Enkripsi.png")
        
        toc=timeit.default_timer()
        GambarCoba.save("Tempat_gambar/Citra - Hasil Enkripsi.gif")
        
        im = PIL.Image.open("Tempat_gambar/Citra - Hasil Enkripsi.png", 'r')
        im = im.resize((200,200)) 
        Hasil123 = im.save("Tempat_gambar/Citra - Hasil Enkripsi.gif")
        gif2 = PhotoImage(file="Tempat_gambar/Citra - Hasil Enkripsi.gif")
    
        label232 = Label(F2, image=gif2)
        label232.image = gif2
        label232.grid(row=5, column=3)
        a = str(toc - tic)
        l33 =Label(F6, font=("Segoe UI",8), text='Waktu: ' +' '+ a[:5] + ' detik', bd=1, relief="ridge")
        l33.grid(row = 0, column=1)
        b4.config(state = ACTIVE)
        
    def saveimage():
        im = PIL.Image.open("Tempat_gambar/Citra - Hasil Enkripsi.png")
        if im.mode != "RGBA":
            im = im.convert("RGBA")
        txt = PIL.Image.new('RGBA', im.size, (255,255,255,0))
    
        file = filedialog.asksaveasfile(mode='w', defaultextension=".png", filetypes=(("PNG file", "*.png"),("All Files", "*.*") ))
        if file:
            abs_path = os.path.abspath(file.name)
            out = PIL.Image.alpha_composite(im, txt)
            out.save(abs_path)
            
    input_x0_1 = DoubleVar()
    l =Label(F3, font=("Segoe UI",10), text="x0_1", bd=1, relief="ridge")
    l.grid(row =2, column =1)
    e =Entry(F3,font=("Segoe UI",10), textvariable=input_x0_1, width=15)
    e.grid(row =2, column =2)
    lh1 = Label(F3, font=("Segoe UI",8), text="(0 < x < 1)", fg="gray")
    lh1.grid(row =2, column =5)
    
    input_x0_2 = DoubleVar()
    l2 =Label(F3, font=("Segoe UI",10), text="x0_2", bd=1, relief="ridge")
    l2.grid(row =2, column =3)
    e2 =Entry(F3,font=("Segoe UI",10), textvariable=input_x0_2, width=15)
    e2.grid(row =2, column =4)
    lh2 = Label(F3, font=("Segoe UI",8), text="(0 < x < 1)", fg="gray")
    lh2.grid(row =2, column =6)
    
    input_p = DoubleVar()
    l3 =Label(F3, font=("Segoe UI",10), text="p", bd=1, relief="ridge")
    l3.grid(row =3, column =1)
    e3 =Entry(F3,font=("Segoe UI",10), textvariable=input_p, width=15)
    e3.grid(row =3, column =2)
    lh3 = Label(F3, font=("Segoe UI",8), text="(0 < p < 0.5)", fg="gray")
    lh3.grid(row =3, column =5)
    
    input_beta = DoubleVar()
    l4 =Label(F3, font=("Segoe UI",10), text="\u03B2 (beta)", bd=1, relief="ridge")
    l4.grid(row =3, column =3)
    e4 =Entry(F3,font=("Segoe UI",10), textvariable=input_beta, width=15)
    e4.grid(row =3, column =4)
    lh4 = Label(F3, font=("Segoe UI",8), text="(0 < \u03B2 \u2264 1)", fg="gray")
    lh4.grid(row =3, column =6)
    
    input_i = DoubleVar()
    l5 =Label(F3, font=("Segoe UI",10), text="Iter", bd=1, relief="ridge")
    l5.grid(row =4, column =1)
    e5 =Entry(F3,font=("Segoe UI",10), textvariable=input_i, width=15)
    e5.grid(row =4, column =2)
    lh5 = Label(F3, font=("Segoe UI",8), text="(min: 100)", fg="gray")
    lh5.grid(row =4, column =5)
    
    l22 = Label(F3, text = '')
    l22.grid(row = 0, column = 7)
    
    c1 = Canvas(F2, height = 250, width = 250)
    c1.grid(row=5, column=0)
    
    c3 = Canvas(F2, height = 250, width = 250)
    c3.grid(row = 5, column = 3)
    
    b3 = Button(F2, text = "Open", padx=15, pady=8, bd=1, relief="ridge", bg="#e1e7ed", activebackground="#cfd8e3", command = OpenFile)
    b3.grid(row = 4, column = 0)
    
    b10 = Button(F2, text = 'Run', padx=15, pady=8, bd=1, relief="ridge", bg="#e1e7ed", activebackground="#cfd8e3", command = encrypt, state = DISABLED)
    b10.grid(row = 4, column =2)
    
    b4 = Button(F2, text = "Save", padx=15, pady=8, bd=1, relief="ridge", bg="#e1e7ed", activebackground="#cfd8e3", command = saveimage, state = DISABLED)
    b4.grid(row = 4, column = 3)
    
    b61 = Label(F6, text = "\t")
    b61.grid(row = 0, column = 1)
    
    b7 = Button(F6, text = "Exit", padx=15, pady=8, bd=1, relief="ridge", bg="#e1e7ed", activebackground="#cfd8e3", command = root.destroy)
    b7.grid(row = 1, column = 1)
    
    root.mainloop()
    
def pencet2():
    root = Toplevel()
    root.geometry("600x600")
    root.title("Program Dekripsi Citra Modulo Sine-PWLCM")
    
    Main = Frame(root, width = 600, height = 600)
    Main.pack()

    Main1 = Frame(Main, width = 600, height = 600)
    Main1.pack(side = LEFT)

    F1 = Frame(Main1, width = 600, height = 20)
    F1.pack()
    
    F3 = Frame(Main1, width = 600, height = 200)
    F3.pack(side=TOP)
    
    F5 = Frame(Main1, width = 600, height = 20)
    F5.pack(side = TOP)
    
    F4 = Frame(Main1, width = 600, height = 50)
    F4.pack(side=TOP)
    
    F2 = Frame(Main1, width = 600, height = 200)
    F2.pack(side = TOP)
    
    F6 = Frame(Main1, width = 600, height = 100)
    F6.pack(side = BOTTOM)
    
    def OpenFile():
        c1 = Canvas(F2, height = 250, width = 250)
        c1.grid(row=5, column=0)
        
        c3 = Canvas(F2, height = 250, width = 250)
        c3.grid(row = 5, column = 3)
        
        File = filedialog.askopenfilename(initialdir = "/",title = "Select file")
        im = PIL.Image.open(File, 'r')
        im.save("Tempat_gambar/Citra - Untuk Dekripsi.png")
        im = im.resize((200,200)) 
        im.save("Tempat_gambar/Citra - Untuk Dekripsi.gif")
        gif1 = PhotoImage(file="Tempat_gambar/Citra - Untuk Dekripsi.gif")
        label212 = Label(c1, image=gif1)
        label212.image = gif1
        label212.grid(row=3, column=1)
        b2.config(state = ACTIVE)
    
    tampilan = Label(F4, text = "Proses Dekripsi", font = ("Segoe UI", 15))
    tampilan.place(x = 228, y = 0)
    
    Nama = Label(F1, font=("Segoe UI",16), text="Parameter Chaos", fg="Black")
    Nama.grid(row=0, column=0)
    
    def encrypt():
        c3 = Canvas(F2, height = 250, width = 250)
        c3.grid(row = 5, column = 3)
        tic=timeit.default_timer()
        im = PIL.Image.open("Tempat_gambar/Citra - Untuk Dekripsi.png", 'r')
        width, height = im.size
        # Konversi gambar ke grayscale L list pixel
        pixel_values = list(im.convert("L").getdata())
        im.load()
        P_g = np.array([nilai(pixel_values[i]) for i in range(height*width)]).reshape(height, width)
        
        # Ambil parameter dari input GUI
        x0_1_val = float(input_x0_1.get())
        x0_2_val = float(input_x0_2.get())
        p_val = float(input_p.get())
        beta_val = float(input_beta.get())
        iterasi = int(input_i.get())

        # Bangkitkan keystream menggunakan Modulo Sine-PWLCM (sipine.py)
        total = height * width
        kunci_acak = generate_keystream(x0_1_val, x0_2_val, p_val, beta_val, iterasi, total)
        A = np.array(kunci_acak).reshape(height, width)

        # Dekripsi XOR langsung 
        enkripsi_g = np.zeros((height, width), dtype=np.uint8)
        for i in range(height):
            for j in range(width):
                enkripsi_g[i,j] = int(P_g[i][j]) ^ int(A[i][j])
    
        GambarCoba = PIL.Image.fromarray(enkripsi_g, mode='L')
        GambarCoba.save("Tempat_gambar/Citra - Hasil Dekripsi.png")
        
        toc=timeit.default_timer()
        GambarCoba.save("Tempat_gambar/Citra - Hasil Dekripsi.gif")
        
        im = PIL.Image.open("Tempat_gambar/Citra - Hasil Dekripsi.png", 'r')
        im = im.resize((200,200)) 
        Hasil123 = im.save("Tempat_gambar/Citra - Hasil Dekripsi.gif")
        gif2 = PhotoImage(file="Tempat_gambar/Citra - Hasil Dekripsi.gif")
    
        label232 = Label(F2, image=gif2)
        label232.image = gif2
        label232.grid(row=5, column=3)
        a = str(toc - tic)
        l33 =Label(F6, font=("Segoe UI",8), text='Waktu: ' +' '+ a[:5] + ' detik', bd=1, relief="ridge")
        l33.grid(row = 0, column=1)
        b3.config(state = ACTIVE)
        
    def saveimage():
        im = PIL.Image.open("Tempat_gambar/Citra - Hasil Dekripsi.png")
        if im.mode != "RGBA":
            im = im.convert("RGBA")
        txt = PIL.Image.new('RGBA', im.size, (255,255,255,0))
    
        file = filedialog.asksaveasfile(mode='w', defaultextension=".png", filetypes=(("PNG file", "*.png"),("All Files", "*.*") ))
        if file:
            abs_path = os.path.abspath(file.name)
            out = PIL.Image.alpha_composite(im, txt)
            out.save(abs_path)
            
    input_x0_1 = DoubleVar()
    l =Label(F3, font=("Segoe UI",10), text="x0_1", bd=1, relief="ridge")
    l.grid(row =2, column =1)
    e =Entry(F3,font=("Segoe UI",10), textvariable=input_x0_1, width=15)
    e.grid(row =2, column =2)
    lh1 = Label(F3, font=("Segoe UI",8), text="(0 < x < 1)", fg="gray")
    lh1.grid(row =2, column =5)
    
    input_x0_2 = DoubleVar()
    l2 =Label(F3, font=("Segoe UI",10), text="x0_2", bd=1, relief="ridge")
    l2.grid(row =2, column =3)
    e2 =Entry(F3,font=("Segoe UI",10), textvariable=input_x0_2, width=15)
    e2.grid(row =2, column =4)
    lh2 = Label(F3, font=("Segoe UI",8), text="(0 < x < 1)", fg="gray")
    lh2.grid(row =2, column =6)
    
    input_p = DoubleVar()
    l3 =Label(F3, font=("Segoe UI",10), text="p", bd=1, relief="ridge")
    l3.grid(row =3, column =1)
    e3 =Entry(F3,font=("Segoe UI",10), textvariable=input_p, width=15)
    e3.grid(row =3, column =2)
    lh3 = Label(F3, font=("Segoe UI",8), text="(0 < p < 0.5)", fg="gray")
    lh3.grid(row =3, column =5)
    
    input_beta = DoubleVar()
    l4 =Label(F3, font=("Segoe UI",10), text="\u03B2 (beta)", bd=1, relief="ridge")
    l4.grid(row =3, column =3)
    e4 =Entry(F3,font=("Segoe UI",10), textvariable=input_beta, width=15)
    e4.grid(row =3, column =4)
    lh4 = Label(F3, font=("Segoe UI",8), text="(0 < \u03B2 \u2264 1)", fg="gray")
    lh4.grid(row =3, column =6)
    
    input_i = DoubleVar()
    l5 =Label(F3, font=("Segoe UI",10), text="Iter", bd=1, relief="ridge")
    l5.grid(row =4, column =1)
    e5 =Entry(F3,font=("Segoe UI",10), textvariable=input_i, width=15)
    e5.grid(row =4, column =2)
    lh5 = Label(F3, font=("Segoe UI",8), text="(min: 100)", fg="gray")
    lh5.grid(row =4, column =5)
    
    l22 = Label(F3, text = '')
    l22.grid(row = 0, column = 7)
    
    c1 = Canvas(F2, height = 250, width = 250)
    c1.grid(row=5, column=0)
    
    c3 = Canvas(F2, height = 250, width = 250)
    c3.grid(row = 5, column = 3)
    
    b1 = Button(F2, text = "Open", padx=15, pady=8, bd=1, relief="ridge", bg="#e1e7ed", activebackground="#cfd8e3", command = OpenFile)
    b1.grid(row = 4, column = 0)
    
    b2 = Button(F2, text = 'Run', padx=15, pady=8, bd=1, relief="ridge", bg="#e1e7ed", activebackground="#cfd8e3", command = encrypt, state = DISABLED)
    b2.grid(row = 4, column =2)
    
    b3 = Button(F2, text = "Save", padx=15, pady=8, bd=1, relief="ridge", bg="#e1e7ed", activebackground="#cfd8e3", command = saveimage, state = DISABLED)
    b3.grid(row = 4, column = 3)
    
    b4 = Button(F6, text = "Exit", padx=15, pady=8, bd=1, relief="ridge", bg="#e1e7ed", activebackground="#cfd8e3", command = root.destroy)
    b4.grid (row = 1, column = 1)
    
    root.mainloop()
        
def pencet3():
    statt = Toplevel()
    statt.geometry("1000x500")
    statt.title("Uji Kualitas Hasil Dekripsi Citra")
    
    Frr1 = Frame(statt, width = 500, height = 100)
    Frr1.pack(side=TOP)
    
    Frr2 = Frame(statt, width = 500, height = 200)
    Frr2.pack(side=TOP)
    
    Frr3 = Frame(statt, width = 500, height = 200)
    Frr3.pack(side=TOP)
    
    Judul1 = Label(Frr1, font=("Segoe UI",15), text="Uji Kualitas Citra Digital", bd=10)
    Judul1.pack()
    
    ll4 = Label(Frr2, text = "\t")
    ll4.grid(row = 0, column = 1)
    ll5 = Label(Frr2, text = "\t\t")
    ll5.grid(row = 0, column = 3)
    ll6 = Label(Frr2, text = "\t")
    ll6.grid(row = 0, column = 5)
    c1 = Canvas(Frr2, height = 300, width = 300, bg="white")
    c1.grid(row=0, column=2)
    c3 = Canvas(Frr2, height = 300, width = 300, bg="white")
    c3.grid(row = 0, column = 4)
    
    def gambar1():
        File = filedialog.askopenfilename(initialdir = "/",title = "Select file")
        im = PIL.Image.open(File, 'r')
        im.save("Tempat_gambar/img1.png")
        im = im.resize((300,300))
        im.save("Tempat_gambar/img1.gif")
        gif1 = PhotoImage(master=c1 , file="Tempat_gambar/img1.gif")
        label = Label(c1, image=gif1)
        label.image = gif1
        label.grid(row=1, column=0)
        
    def gambar2():
        File = filedialog.askopenfilename(initialdir = "/",title = "Select file")
        im = PIL.Image.open(File, 'r')
        im.save("Tempat_gambar/img2.png")
        im = im.resize((300,300))
        im.save("Tempat_gambar/img2.gif")
        gif1 = PhotoImage(master=c3 , file="Tempat_gambar/img2.gif")
        label = Label(c3, image=gif1)
        label.image = gif1
        label.grid(row=1, column=0)
        
    def hasil():
        stat = Toplevel()
        stat.geometry("1600x1000")
    
        im1 = PIL.Image.open("Tempat_gambar/img1.png", "r").convert("RGB")
        width, height = im1.size
        pixel_values = list(im1.getdata())
        im1.load()
        array = np.asarray(im1)
    
        P_r = []
        P_g = []
        P_b = []
    
        P_r = np.array([nilai(pixel_values[i][0]) for i in range(height*width)])
        P_g = np.array([nilai(pixel_values[i][1]) for i in range(height*width)])
        P_b = np.array([nilai(pixel_values[i][2]) for i in range(height*width)])
        
        P_r1 = []
        P_g1 = []
        P_b1 = []
    
        P_r1 = np.array([nilai(pixel_values[i][0]) for i in range(height*width)]).reshape(array.shape[0], array.shape[1])
        P_g1 = np.array([nilai(pixel_values[i][1]) for i in range(height*width)]).reshape(array.shape[0], array.shape[1])
        P_b1 = np.array([nilai(pixel_values[i][2]) for i in range(height*width)]).reshape(array.shape[0], array.shape[1])
    
        x_horr = []
        y_horr = []
        x_horg = []
        y_horg = []
        x_horb = []
        y_horb = []
    
        for i in range (height):
            for j in range (width):
                if j<width-1:
                    x_horr.append(P_r1[i][j])
                    x_horg.append(P_g1[i][j])
                    x_horb.append(P_b1[i][j])
                if j+1<width:
                    y_horr.append(P_r1[i][j+1])
                    y_horg.append(P_g1[i][j+1])
                    y_horb.append(P_b1[i][j+1])
    
        x_verr = []
        y_verr = []
        x_verg = []
        y_verg = []
        x_verb = []
        y_verb = []
    
        for i in range (height):
            for j in range (width):
                if i<height-1:
                    x_verr.append(P_r1[i][j])
                    x_verg.append(P_g1[i][j])
                    x_verb.append(P_b1[i][j])
                    
        for i in range(height):
            for j in range(width):
                if i+1<height:
                    y_verr.append(P_r1[i+1][j])
                    y_verg.append(P_g1[i+1][j])
                    y_verb.append(P_b1[i+1][j])
                    
        x_diar = []
        y_diar = []
        x_diag = []
        y_diag = []
        x_diab = []
        y_diab = []
    
        for i in range (height):
            for j in range (width):
                if j<(width-1) and i<(height-1):
                    x_diar.append(P_r1[i][j])
                    x_diag.append(P_g1[i][j])
                    x_diab.append(P_b1[i][j])
    
                if j+1<width and i+1<height:
                    y_diar.append(P_r1[i+1][j+1])
                    y_diag.append(P_g1[i+1][j+1])
                    y_diab.append(P_b1[i+1][j+1])
           
        a1 = pearsonr(x_horr,y_horr)
        a2 = pearsonr(x_horg,y_horg)
        a3 = pearsonr(x_horb,y_horb)
        a4 = pearsonr(x_verr,y_verr)
        a5 = pearsonr(x_verg,y_verg)
        a6 = pearsonr(x_verb,y_verb)
        a7 = pearsonr(x_diar,y_diar)
        a8 = pearsonr(x_diag,y_diag)
        a9 = pearsonr(x_diab,y_diab)
        
        cov1 = str(a1[0])
        cov2 = str(a2[0])
        cov3 = str(a3[0])
        cov4 = str(a4[0])
        cov5 = str(a5[0])
        cov6 = str(a6[0])
        cov7 = str(a7[0])
        cov8 = str(a8[0])
        cov9 = str(a9[0])
        
        plt.figure()
        plt.hist(P_r, bins = 25, color = "red")
        plt.savefig('Tempat_gambar/Red.png')
        plt.close()
        plt.figure()
        plt.hist(P_g, bins = 25, color = "green")
        plt.savefig('Tempat_gambar/Green.png')
        plt.close()
        plt.figure()
        plt.hist(P_b, bins = 25, color = "blue")
        plt.savefig('Tempat_gambar/Blue.png')
        plt.close()
    
        im2 = PIL.Image.open("Tempat_gambar/img2.png", "r").convert("RGB")
        width, height = im2.size
        pixel_values = list(im2.getdata())
        im2.load()
        array = np.asarray(im2)
    
        P_r = []
        P_g = []
        P_b = []
    
        P_r = np.array([nilai(pixel_values[i][0]) for i in range(height*width)])
        P_g = np.array([nilai(pixel_values[i][1]) for i in range(height*width)])
        P_b = np.array([nilai(pixel_values[i][2]) for i in range(height*width)])
        
        P_r1 = []
        P_g1 = []
        P_b1 = []
    
        P_r1 = np.array([nilai(pixel_values[i][0]) for i in range(height*width)]).reshape(array.shape[0], array.shape[1])
        P_g1 = np.array([nilai(pixel_values[i][1]) for i in range(height*width)]).reshape(array.shape[0], array.shape[1])
        P_b1 = np.array([nilai(pixel_values[i][2]) for i in range(height*width)]).reshape(array.shape[0], array.shape[1])
    
        x_horr = []
        y_horr = []
        x_horg = []
        y_horg = []
        x_horb = []
        y_horb = []
    
        for i in range (height):
            for j in range (width):
                if j<width-1:
                    x_horr.append(P_r1[i][j])
                    x_horg.append(P_g1[i][j])
                    x_horb.append(P_b1[i][j])
                if j+1<width:
                    y_horr.append(P_r1[i][j+1])
                    y_horg.append(P_g1[i][j+1])
                    y_horb.append(P_b1[i][j+1])
    
        x_verr = []
        y_verr = []
        x_verg = []
        y_verg = []
        x_verb = []
        y_verb = []
    
        for i in range (height):
            for j in range (width):
                if i<height-1:
                    x_verr.append(P_r1[i][j])
                    x_verg.append(P_g1[i][j])
                    x_verb.append(P_b1[i][j])
                    
        for i in range(height):
            for j in range(width):
                if i+1<height:
                    y_verr.append(P_r1[i+1][j])
                    y_verg.append(P_g1[i+1][j])
                    y_verb.append(P_b1[i+1][j])
                    
        x_diar = []
        y_diar = []
        x_diag = []
        y_diag = []
        x_diab = []
        y_diab = []
    
        for i in range (height):
            for j in range (width):
                if j<(width-1) and i<(height-1):
                    x_diar.append(P_r1[i][j])
                    x_diag.append(P_g1[i][j])
                    x_diab.append(P_b1[i][j])
    
                if j+1<width and i+1<height:
                    y_diar.append(P_r1[i+1][j+1])
                    y_diag.append(P_g1[i+1][j+1])
                    y_diab.append(P_b1[i+1][j+1])
           
        a1 = pearsonr(x_horr,y_horr)
        a2 = pearsonr(x_horg,y_horg)
        a3 = pearsonr(x_horb,y_horb)
        a4 = pearsonr(x_verr,y_verr)
        a5 = pearsonr(x_verg,y_verg)
        a6 = pearsonr(x_verb,y_verb)
        a7 = pearsonr(x_diar,y_diar)
        a8 = pearsonr(x_diag,y_diag)
        a9 = pearsonr(x_diab,y_diab)
        
        
        
        stg1 = str(a1[0])
        stg2 = str(a2[0])
        stg3 = str(a3[0])
        stg4 = str(a4[0])
        stg5 = str(a5[0])
        stg6 = str(a6[0])
        stg7 = str(a7[0])
        stg8 = str(a8[0])
        stg9 = str(a9[0])
    
        plt.figure()
        plt.hist(P_r, bins = 25, color = "red")
        plt.savefig('Tempat_gambar/Red1.png')
        plt.close()
        plt.figure()
        plt.hist(P_g, bins = 25, color = "green")
        plt.savefig('Tempat_gambar/Green1.png')
        plt.close()
        plt.figure()
        plt.hist(P_b, bins = 25, color = "blue")
        plt.savefig('Tempat_gambar/Blue1.png')
        plt.close()
    
        Fr1 = Frame(stat, width = 1600, height = 75)
        Fr1.pack(side = TOP)
    
        L1 = Label(Fr1, text = '\nHistogram Image 1', font = ("Segoe UI", 15, "bold"))
        L1.grid()
    
        Fr2 = Frame(stat, width = 1600, height = 235)
        Fr2.pack(side = TOP)
    
        c11 = Canvas(Fr2, height = 235, width = 235)
        c11.grid(row=5, column=0)
    
        bo1 = Label(Fr2, text = '\t')
        bo1.grid(row = 5, column = 1) 
    
        c21 = Canvas(Fr2, height = 235, width = 235)
        c21.grid(row=5, column=2)
    
        bo2 = Label(Fr2, text = '\t')
        bo2.grid(row = 5, column = 3) 
    
        c31 = Canvas(Fr2, height = 235, width = 235)
        c31.grid(row = 5, column = 4)
    
        im = PIL.Image.open("Tempat_gambar/Red.png", 'r')
        im = im.resize((300,225), PIL.Image.LANCZOS) 
        im.save("Tempat_gambar/Red.gif") 
    
        im = PIL.Image.open("Tempat_gambar/Green.png", 'r')
        im = im.resize((300,225), PIL.Image.LANCZOS)
        im.save("Tempat_gambar/Green.gif")
    
        im = PIL.Image.open("Tempat_gambar/Blue.png", 'r')
        im = im.resize((300,225), PIL.Image.LANCZOS)
        im.save("Tempat_gambar/Blue.gif")
    
        gif10 = PhotoImage(file="Tempat_gambar/Red.gif", master = c11)
        label1 = Label(c11, image=gif10)
        label1.image = gif10
        label1.grid(row=0, column=0)
    
        gif20 = PhotoImage(file="Tempat_gambar/Green.gif", master = c21)
        label2 = Label(c21, image=gif20)
        label2.image = gif20
        label2.grid(row=0, column=2)
    
        gif30 = PhotoImage(file="Tempat_gambar/Blue.gif", master = c31)
        label3 = Label(c31, image=gif30)
        label3.image = gif30
        label3.grid(row=0, column=4)
    
        Fr3 = Frame(stat, width = 1600, height = 75)
        Fr3.pack(side = TOP)
    
        L5 = Label(Fr3, text = '\nHistogram Image 2', font = ("Segoe UI", 15, "bold"))
        L5.grid()
    
        Fr4 = Frame(stat, width = 1600, height = 235)
        Fr4.pack(side = TOP)
    
        c41 = Canvas(Fr4, height = 235, width = 235)
        c41.grid(row=5, column=0)
    
        bo3 = Label(Fr4, text = '\t')
        bo3.grid(row = 5, column = 1) 
    
        c51 = Canvas(Fr4, height = 235, width = 235)
        c51.grid(row=5, column=2)
    
        bo4 = Label(Fr4, text = '\t')
        bo4.grid(row = 5, column = 3) 
    
        c61 = Canvas(Fr4, height = 235, width = 235)
        c61.grid(row = 5, column = 4)
    
        im = PIL.Image.open("Tempat_gambar/Red1.png", 'r')
        im = im.resize((300,225), PIL.Image.LANCZOS) 
        im.save("Tempat_gambar/Red1.gif") 
    
        im = PIL.Image.open("Tempat_gambar/Green1.png", 'r')
        im = im.resize((300,225), PIL.Image.LANCZOS)
        im.save("Tempat_gambar/Green1.gif")
    
        im = PIL.Image.open("Tempat_gambar/Blue1.png", 'r')
        im = im.resize((300,225), PIL.Image.LANCZOS)
        im.save("Tempat_gambar/Blue1.gif")
    
        gif11 = PhotoImage(file="Tempat_gambar/Red1.gif", master = c41)
        label1 = Label(c41, image=gif11)
        label1.image = gif11
        label1.grid(row=0, column=0)
    
        gif21 = PhotoImage(file="Tempat_gambar/Green1.gif", master = c51)
        label2 = Label(c51, image=gif21)
        label2.image = gif21
        label2.grid(row=0, column=2)
    
        gif31 = PhotoImage(file="Tempat_gambar/Blue1.gif", master = c61)
        label3 = Label(c61, image=gif31)
        label3.image = gif31
        label3.grid(row=0, column=4)
    
        Fr5 = Frame(stat, width = 1600, height = 200)
        Fr5.pack(side = TOP)
    
    
        def psnr(img1, img2):
            summation = 0
            n = len(img1)
            for i in range(n):
                difference = img1[i] - img2[i]
                squared = difference**2
                summation = summation + squared
                
            mse = summation/(n**2)
            PIXEL_MAX = 255
            nilaip = 20 * math.log10(PIXEL_MAX / math.sqrt(mse))
            nilaip = str(nilaip)
            mse = str(mse)
    
            lm = Label(Fr5, font=("Segoe UI",10), text='Nilai MSE: ' +' '+ mse[:7], bd=10)
            lm.place(x=900, y=50)
            lp = Label(Fr5, font=("Segoe UI",10), text='Nilai PSNR: ' +' '+ nilaip[:7], bd=10)
            lp.place(x=1100, y=50)
    
        lp1= Label(Fr5, font=("Segoe UI",10), text='Koefisien Korelasi \n Image 1', bd=10)
        lp1.place(x=0, y=50)
        
        ls1= Label(Fr5, font=("Segoe UI",10), text='R', bd=10)
        ls1.place(x=120, y=30)
        
        ls2= Label(Fr5, font=("Segoe UI",10), text='G', bd=10)
        ls2.place(x=120, y=60)
        
        ls3= Label(Fr5, font=("Segoe UI",10), text='B', bd=10)
        ls3.place(x=120, y=90)
        
        lp2= Label(Fr5, font=("Segoe UI",10), text='Horizontal', bd=10)
        lp2.place(x=150, y=0)
        
        lp3= Label(Fr5, font=("Segoe UI",10), text='Vertikal', bd=10)
        lp3.place(x=250, y=0)
        
        lp4= Label(Fr5, font=("Segoe UI",10), text='Diagonal', bd=10)
        lp4.place(x=350, y=0)
        
        lp5= Label(Fr5, font=("Segoe UI",10), text=cov1[:7], bd=10)
        lp5.place(x=150, y=30)
        
        lp6= Label(Fr5, font=("Segoe UI",10), text=cov2[:7], bd=10)
        lp6.place(x=150, y=60)
        
        lp7= Label(Fr5, font=("Segoe UI",10), text=cov3[:7], bd=10)
        lp7.place(x=150, y=90)
        
        lp8= Label(Fr5, font=("Segoe UI",10), text=cov4[:7], bd=10)
        lp8.place(x=250, y=30)
        
        lp9= Label(Fr5, font=("Segoe UI",10), text=cov5[:7], bd=10)
        lp9.place(x=250, y=60)
        
        lp10= Label(Fr5, font=("Segoe UI",10), text=cov6[:7], bd=10)
        lp10.place(x=250, y=90)
        
        lp11= Label(Fr5, font=("Segoe UI",10), text=cov7[:7], bd=10)
        lp11.place(x=350, y=30)
        
        lp12= Label(Fr5, font=("Segoe UI",10), text=cov8[:7], bd=10)
        lp12.place(x=350, y=60)
        
        lp13= Label(Fr5, font=("Segoe UI",10), text=cov9[:7], bd=10)
        lp13.place(x=350, y=90)
        
        lq1= Label(Fr5, font=("Segoe UI",10), text='Koefisien Korelasi \n Image 2', bd=10)
        lq1.place(x=450, y=50)
        
        ls4= Label(Fr5, font=("Segoe UI",10), text='R', bd=10)
        ls4.place(x=570, y=30)
        
        ls5= Label(Fr5, font=("Segoe UI",10), text='G', bd=10)
        ls5.place(x=570, y=60)
        
        ls6= Label(Fr5, font=("Segoe UI",10), text='B', bd=10)
        ls6.place(x=570, y=90)
        
        lq2= Label(Fr5, font=("Segoe UI",10), text='Horizontal', bd=10)
        lq2.place(x=600, y=0)
        
        lq3= Label(Fr5, font=("Segoe UI",10), text='Vertikal', bd=10)
        lq3.place(x=700, y=0)
        
        lq4= Label(Fr5, font=("Segoe UI",10), text='Diagonal', bd=10)
        lq4.place(x=800, y=0)
        
        lq5= Label(Fr5, font=("Segoe UI",10), text=stg1[:7], bd=10)
        lq5.place(x=600, y=30)
        
        lq6= Label(Fr5, font=("Segoe UI",10), text=stg2[:7], bd=10)
        lq6.place(x=600, y=60)
        
        lq7= Label(Fr5, font=("Segoe UI",10), text=stg3[:7], bd=10)
        lq7.place(x=600, y=90)
        
        lq8= Label(Fr5, font=("Segoe UI",10), text=stg4[:7], bd=10)
        lq8.place(x=700, y=30)
        
        lq9= Label(Fr5, font=("Segoe UI",10), text=stg5[:7], bd=10)
        lq9.place(x=700, y=60)
        
        lq10= Label(Fr5, font=("Segoe UI",10), text=stg6[:7], bd=10)
        lq10.place(x=700, y=90)
        
        lq11= Label(Fr5, font=("Segoe UI",10), text=stg7[:7], bd=10)
        lq11.place(x=800, y=30)
        
        lq12= Label(Fr5, font=("Segoe UI",10), text=stg8[:7], bd=10)
        lq12.place(x=800, y=60)
        
        lq13= Label(Fr5, font=("Segoe UI",10), text=stg9[:7], bd=10)
        lq13.place(x=800, y=90)
        
        im = PIL.Image.open("Tempat_gambar/img1.png", 'r')
        width, height = im.size
        pixel_values = list(im.getdata())
        im.load()
        array = np.asarray(im)
        P_r = []
        P_g = []
        P_b = []
        P_r = np.array([nilai(pixel_values[i][0]) for i in range(height*width)])
        P_g = np.array([nilai(pixel_values[i][1]) for i in range(height*width)])
        P_b = np.array([nilai(pixel_values[i][2]) for i in range(height*width)])
        
        im = PIL.Image.open("Tempat_gambar/img2.png", 'r')
        width, height = im.size
        pixel_values = list(im.getdata())
        im.load()
        array = np.asarray(im)
        P_r1 = []
        P_g1 = []
        P_b1 = []
        P_r1 = np.array([nilai(pixel_values[i][0]) for i in range(height*width)])
        P_g1 = np.array([nilai(pixel_values[i][1]) for i in range(height*width)])
        P_b1 = np.array([nilai(pixel_values[i][2]) for i in range(height*width)])
        
        def psnr(a, b, c, d, e, f):
            sum13 = 0
            sum23 = 0
            sum33 = 0
            n = len(P_r1)
            for i in range(n):
                sum1 = (a[i] - b[i])**2
                sum1 = sum1 / (n)
                sum13 += sum1

                sum2 = (c[i] - d[i])**2
                sum2 = sum2 / (n)
                sum23 += sum2

                sum3 = (e[i] - f[i])**2
                sum3 = sum3 / (n)
                sum33 += sum3

            mse = (sum13 + sum23 + sum33)
            
            if mse == 0:
                nilaip = float('inf')
            else:
                PIXEL_MAX = 255.0
                nilaip = 20 * math.log10(PIXEL_MAX / math.sqrt(mse))
            nilaip = str(nilaip)
            mse = str(mse)
            lm = Label(Fr5, font=("Segoe UI",10), text='Nilai MSE: ' +' '+ mse[:7], bd=10)
            lm.place(x=900, y=50)
            lp = Label(Fr5, font=("Segoe UI",10), text='Nilai PSNR: ' +' '+ nilaip[:7], bd=10)
            lp.place(x=1100, y=50)

        psnr(P_r, P_r1, P_g, P_g1, P_b, P_b1)
    
    ll7 = Label(Frr3, text = "\t")
    ll7.pack()
    
    x1 = Button(Frr2,padx=3, pady=3, bd=5, fg="black", font=("Segoe UI",10), width=15, text="Pilih Citra 1", command = gambar1)
    x1.grid(row=1,column=2)
    
    x2 = Button(Frr2,padx=3, pady=3, bd=5, fg="black", font=("Segoe UI",10), width=15, text="Pilih Citra 2", command = gambar2)
    x2.grid(row=1,column=4)
    
    x3 = Button(Frr3,padx=3, pady=3, bd=5, fg="black", font=("Segoe UI",10), width=15, text="Uji Statistik", command = hasil)
    x3.pack()
    
    x4 = Button(Frr3,padx=3, pady=3, bd=5, fg="black", font=("Segoe UI",10), width=15, text="Keluar", command = statt.destroy)
    x4.pack()
    
    statt.mainloop()

def pencet4():
    statt = Toplevel()
    statt.geometry("500x520")
    statt.title("Uji Keacakan (Distribusi Korelasi)")
    
    Frr1 = Frame(statt, width = 500, height = 100)
    Frr1.pack(side=TOP)
    
    Frr2 = Frame(statt, width = 500, height = 200)
    Frr2.pack(side=TOP)
    
    Frr3 = Frame(statt, width = 500, height = 200)
    Frr3.pack(side=TOP)
    
    Judul1 = Label(Frr1, font=("Segoe UI",15), text=" Uji Keacakan (Distribusi Korelasi)", bd=10)
    Judul1.pack()

    c1 = Canvas(Frr2, height = 300, width = 300)
    c1.grid(row=0, column=2)
    
    def gambar1():
        File = filedialog.askopenfilename(initialdir = "/",title = "Select file")
        im = PIL.Image.open(File, 'r')
        im.save("Tempat_gambar/img1.png")
        im = im.resize((300,300))
        im.save("Tempat_gambar/img1.gif")
        gif1 = PhotoImage(master=c1 , file="Tempat_gambar/img1.gif")
        label = Label(c1, image=gif1)
        label.image = gif1
        label.grid(row=1, column=0)
        
    def hasil():
        stat = Toplevel()
        stat.geometry("1000x800")
        
        stat['bg'] = 'light blue'
    
        im1 = PIL.Image.open("Tempat_gambar/img1.png", "r").convert("RGB")
        width, height = im1.size
        pixel_values = list(im1.getdata())
        im1.load()
        array = np.asarray(im1)
        
        P_r1 = []
        P_g1 = []
        P_b1 = []
        
        P_r1 = np.array([nilai(pixel_values[i][0]) for i in range(height*width)]).reshape(array.shape[0], array.shape[1])
        P_g1 = np.array([nilai(pixel_values[i][1]) for i in range(height*width)]).reshape(array.shape[0], array.shape[1])
        P_b1 = np.array([nilai(pixel_values[i][2]) for i in range(height*width)]).reshape(array.shape[0], array.shape[1])
        
        x_horr = []
        y_horr = []
        x_horg = []
        y_horg = []
        x_horb = []
        y_horb = []
        
        for i in range (height):
            for j in range (width):
                if j<width-1:
                    x_horr.append(P_r1[i][j])
                    x_horg.append(P_g1[i][j])
                    x_horb.append(P_b1[i][j])
                if j+1<width:
                    y_horr.append(P_r1[i][j+1])
                    y_horg.append(P_g1[i][j+1])
                    y_horb.append(P_b1[i][j+1])
        
        x_verr = []
        y_verr = []
        x_verg = []
        y_verg = []
        x_verb = []
        y_verb = []
        
        for i in range (height):
            for j in range (width):
                if i<height-1:
                    x_verr.append(P_r1[i][j])
                    x_verg.append(P_g1[i][j])
                    x_verb.append(P_b1[i][j])
        
        for i in range(height):
            for j in range(width):
                if i+1<height:
                    y_verr.append(P_r1[i+1][j])
                    y_verg.append(P_g1[i+1][j])
                    y_verb.append(P_b1[i+1][j])
        
        x_diar = []
        y_diar = []
        x_diag = []
        y_diag = []
        x_diab = []
        y_diab = []
        
        for i in range (height):
            for j in range (width):
                if j<(width-1) and i<(height-1):
                    x_diar.append(P_r1[i][j])
                    x_diag.append(P_g1[i][j])
                    x_diab.append(P_b1[i][j])
        
                if j+1<width and i+1<height:
                    y_diar.append(P_r1[i+1][j+1])
                    y_diag.append(P_g1[i+1][j+1])
                    y_diab.append(P_b1[i+1][j+1])        
                    
       
        Fr1 = Frame(stat, width = 1600, height = 235)
        Fr1.pack(side = TOP)
        
        box = Label(Fr1, font=("Segoe UI", 18),  text = 'Uji Korelasi Pearson')
        box.grid(row = 0, column = 2)
        
        boa = Label(Fr1, font=("Segoe UI", 14), text = 'Horizontal                    ')
        boa.grid(row = 1, column = 0) 
        
        bob = Label(Fr1, font=("Segoe UI", 14), text = 'Vertikal')
        bob.grid(row = 1, column = 2) 
        
        boc = Label(Fr1, font=("Segoe UI", 14), text = '                      Diagonal')
        boc.grid(row = 1, column = 4) 
            
        Fr2 = Frame(stat, width = 1600, height = 235)
        Fr2.pack(side = TOP)
        
        c11 = Canvas(Fr2, height = 235, width = 235)
        c11.grid(row = 1, column=0)
        
        bo1 = Label(Fr2, text = '\t')
        bo1.grid(row = 1, column = 1) 
    
        c12 = Canvas(Fr2, height = 235, width = 235)
        c12.grid(row = 1, column=2)
    
        bo2 = Label(Fr2, text = '\t')
        bo2.grid(row = 1, column = 3) 
    
        c13 = Canvas(Fr2, height = 235, width = 235)
        c13.grid(row = 1, column = 4)     
       
        
        Fr3 = Frame(stat, width = 1600, height = 235)
        Fr3.pack(side = TOP)
            
        c21 = Canvas(Fr3, height = 235, width = 235)
        c21.grid(row = 6, column=0)
    
        bo3 = Label(Fr3, text = '\t')
        bo3.grid(row = 6, column = 1) 
    
        c22 = Canvas(Fr3, height = 235, width = 235)
        c22.grid(row = 6, column=2)
    
        bo4 = Label(Fr3, text = '\t')
        bo4.grid(row = 6, column = 3) 
    
        c23 = Canvas(Fr3, height = 235, width = 235)
        c23.grid(row = 6, column = 4)
        
        
        Fr4 = Frame(stat, width = 1600, height = 235)
        Fr4.pack(side = TOP)
            
        c31 = Canvas(Fr4, height = 235, width = 235)
        c31.grid(row = 6, column=0)
    
        bo5 = Label(Fr4, text = '\t')
        bo5.grid(row = 6, column = 1) 
    
        c32 = Canvas(Fr4, height = 235, width = 235)
        c32.grid(row = 6, column=2)
    
        bo6 = Label(Fr4, text = '\t')
        bo6.grid(row = 6, column = 3) 
    
        c33 = Canvas(Fr4, height = 235, width = 235)
        c33.grid(row = 6, column = 4)
        

        plt.figure(figsize=(6, 6))
        plt.scatter(x_horr, y_horr, color = 'red')
        plt.savefig('Tempat_gambar/Red Hor.png')
        
        plt.figure(figsize=(6, 6))
        plt.scatter(x_verr, y_verr, color = 'red')
        plt.savefig('Tempat_gambar/Red Ver.png')
        
        plt.figure(figsize=(6, 6))
        plt.scatter(x_diar, y_diar, color = 'red')
        plt.savefig('Tempat_gambar/Red Dia.png')
        
        plt.figure(figsize=(6, 6))
        plt.scatter(x_horg, y_horg, color = 'green')
        plt.savefig('Tempat_gambar/Green Hor.png')
        
        plt.figure(figsize=(6, 6))
        plt.scatter(x_verg, y_verg, color = 'green')
        plt.savefig('Tempat_gambar/Green Ver.png')
        
        plt.figure(figsize=(6, 6))
        plt.scatter(x_diag, y_diag, color = 'green')
        plt.savefig('Tempat_gambar/Green Dia.png')
        
        plt.figure(figsize=(6, 6))
        plt.scatter(x_horb, y_horb, color = 'blue')
        plt.savefig('Tempat_gambar/Blue Hor.png')
        
        plt.figure(figsize=(6, 6))
        plt.scatter(x_verb, y_verb, color = 'blue')
        plt.savefig('Tempat_gambar/Blue Ver.png')
        
        plt.figure(figsize=(6, 6))
        plt.scatter(x_diab, y_diab, color = 'blue')
        plt.savefig('Tempat_gambar/Blue Dia.png')
        
        im = PIL.Image.open("Tempat_gambar/Red Hor.png", 'r')
        im = im.resize((200,200), PIL.Image.LANCZOS) 
        im.save("Tempat_gambar/Red Hor.gif") 
            
        gif11 = PhotoImage(file="Tempat_gambar/Red Hor.gif", master = c11)
        label1 = Label(c11, image=gif11)
        label1.image = gif11
        label1.grid(row=0, column=0)
        
        im = PIL.Image.open("Tempat_gambar/Red Ver.png", 'r')
        im = im.resize((200,200), PIL.Image.LANCZOS) 
        im.save("Tempat_gambar/Red Ver.gif") 
            
        gif11 = PhotoImage(file="Tempat_gambar/Red Ver.gif", master = c12)
        label1 = Label(c12, image=gif11)
        label1.image = gif11
        label1.grid(row=0, column=0)
        
        im = PIL.Image.open("Tempat_gambar/Red Dia.png", 'r')
        im = im.resize((200,200), PIL.Image.LANCZOS) 
        im.save("Tempat_gambar/Red Dia.gif") 
            
        gif11 = PhotoImage(file="Tempat_gambar/Red Dia.gif", master = c13)
        label1 = Label(c13, image=gif11)
        label1.image = gif11
        label1.grid(row=0, column=0)
        
        im = PIL.Image.open("Tempat_gambar/Green Hor.png", 'r')
        im = im.resize((200,200), PIL.Image.LANCZOS) 
        im.save("Tempat_gambar/Green Hor.gif") 
            
        gif11 = PhotoImage(file="Tempat_gambar/Green Hor.gif", master = c21)
        label1 = Label(c21, image=gif11)
        label1.image = gif11
        label1.grid(row=0, column=0)
        
        im = PIL.Image.open("Tempat_gambar/Green Ver.png", 'r')
        im = im.resize((200,200), PIL.Image.LANCZOS) 
        im.save("Tempat_gambar/Green Ver.gif") 
            
        gif11 = PhotoImage(file="Tempat_gambar/Green Ver.gif", master = c22)
        label1 = Label(c22, image=gif11)
        label1.image = gif11
        label1.grid(row=0, column=0)
        
        im = PIL.Image.open("Tempat_gambar/Green Dia.png", 'r')
        im = im.resize((200,200), PIL.Image.LANCZOS) 
        im.save("Tempat_gambar/Green Dia.gif") 
            
        gif11 = PhotoImage(file="Tempat_gambar/Green Dia.gif", master = c23)
        label1 = Label(c23, image=gif11)
        label1.image = gif11
        label1.grid(row=0, column=0)
        
        im = PIL.Image.open("Tempat_gambar/Blue Hor.png", 'r')
        im = im.resize((200,200), PIL.Image.LANCZOS) 
        im.save("Tempat_gambar/Blue Hor.gif") 
            
        gif11 = PhotoImage(file="Tempat_gambar/Blue Hor.gif", master = c31)
        label1 = Label(c31, image=gif11)
        label1.image = gif11
        label1.grid(row=0, column=0)
        
        im = PIL.Image.open("Tempat_gambar/Blue Ver.png", 'r')
        im = im.resize((200,200), PIL.Image.LANCZOS) 
        im.save("Tempat_gambar/Blue Ver.gif") 
            
        gif11 = PhotoImage(file="Tempat_gambar/Blue Ver.gif", master = c32)
        label1 = Label(c32, image=gif11)
        label1.image = gif11
        label1.grid(row=0, column=0)
        
        im = PIL.Image.open("Tempat_gambar/Blue Dia.png", 'r')
        im = im.resize((200,200), PIL.Image.LANCZOS) 
        im.save("Tempat_gambar/Blue Dia.gif") 
            
        gif11 = PhotoImage(file="Tempat_gambar/Blue Dia.gif", master = c33)
        label1 = Label(c33, image=gif11)
        label1.image = gif11
        label1.grid(row=0, column=0)

        
    ll7 = Label(Frr3, text = "\t")
    ll7.pack()
    
    x1 = Button(Frr2,padx=3, pady=3, bd=5, fg="black", font=("Segoe UI",10), width=17, text="Pilih File Citra", command = gambar1)
    x1.grid(row=1,column=2)
    
    x3 = Button(Frr3,padx=3, pady=3, bd=5, fg="black", font=("Segoe UI",10), width=17, text="Uji Distribusi Korelasi", command = hasil)
    x3.pack()
    
    Frr4 = Frame(statt, width = 500, height = 200)
    Frr4.pack(side=TOP)
    
    ll7 = Label(Frr4, text = "\t")
    ll7.pack()
    
    x4 = Button(Frr4,padx=3, pady=3, bd=5, fg="black", font=("Segoe UI",10), width=10, text="Keluar", command = statt.destroy)
    x4.pack()
    
    statt.mainloop()

def pencet5():    
    statt = Toplevel()
    statt.geometry("1000x550")
    statt.title("Uji Statistik (Uniform, Entropi, UACI, dan NPCR)")
    
    Frr1 = Frame(statt, width = 500, height = 100)
    Frr1.pack(side=TOP)
    
    Frr2 = Frame(statt, width = 500, height = 200)
    Frr2.pack(side=TOP)
    
    Frr3 = Frame(statt, width = 500, height = 200)
    Frr3.pack(side=TOP)
    
    Judul1 = Label(Frr1, font=("Segoe UI",15), text="Uji Statistik (Uniform, Entropi, UACI, dan NPCR)", bd=10)
    Judul1.pack()
    
    ll4 = Label(Frr2, text = "\t")
    ll4.grid(row = 0, column = 1)
    ll5 = Label(Frr2, text = "\t\t")
    ll5.grid(row = 0, column = 3)
    ll6 = Label(Frr2, text = "\t")
    ll6.grid(row = 0, column = 5)
    c1 = Canvas(Frr2, height = 300, width = 300)
    c1.grid(row=0, column=2)
    c3 = Canvas(Frr2, height = 300, width = 300)
    c3.grid(row = 0, column = 4)
    
    def gambar1():
        File = filedialog.askopenfilename(initialdir = "/",title = "Select file")
        im = PIL.Image.open(File, 'r')
        im.save("Tempat_gambar/img1.png")
        im = im.resize((300,300))
        im.save("Tempat_gambar/img1.gif")
        gif1 = PhotoImage(master=c1 , file="Tempat_gambar/img1.gif")
        label = Label(c1, image=gif1, bg = 'honeydew4')
        label.image = gif1
        label.grid(row=1, column=0)
        
    def gambar2():
        File = filedialog.askopenfilename(initialdir = "/",title = "Select file")
        im = PIL.Image.open(File, 'r')
        im.save("Tempat_gambar/img2.png")
        im = im.resize((300,300))
        im.save("Tempat_gambar/img2.gif")
        gif1 = PhotoImage(master=c3 , file="Tempat_gambar/img2.gif")
        label = Label(c3, image=gif1, bg = 'honeydew4')
        label.image = gif1
        label.grid(row=1, column=0)
        
    def hasil():
        hasil = Toplevel()
        hasil.geometry("550x250")
        hasil.title("Uji Kualitas (Histogram, Koefisien Korelasi, MSE, dan PSNR)")
        
        hasil['bg'] = 'light blue'
        
        F1 = Frame(hasil, width = 400, height = 50)
        F1.pack(side = TOP)
        
        F2 = Frame(hasil, width = 400, height = 250)
        F2.pack(side = TOP)
        
        im1 = PIL.Image.open("Tempat_gambar/img1.png", "r").convert("RGB")
        width1, height1 = im1.size
        pixel_values1 = list(im1.getdata())
        im1.load()
        array1 = np.asarray(im1)
        
        P_r1 = []
        P_g1 = []
        P_b1 = []
        
        P_r1 = np.array([nilai(pixel_values1[i][0]) for i in range(height1*width1)])
        P_g1 = np.array([nilai(pixel_values1[i][1]) for i in range(height1*width1)])
        P_b1 = np.array([nilai(pixel_values1[i][2]) for i in range(height1*width1)])
    
        uni_r1, uni_g1, uni_b1 = ujiuniform(P_r1, P_g1, P_b1, width1, height1)    
        
        ent_r1 = skimage.measure.shannon_entropy(P_r1)
        ent_g1 = skimage.measure.shannon_entropy(P_g1)
        ent_b1 = skimage.measure.shannon_entropy(P_b1)
        ent_1 = (ent_r1 + ent_g1 + ent_b1)/3
    
        im2 = PIL.Image.open("Tempat_gambar/img2.png", "r").convert("RGB")
        width2, height2 = im2.size
        pixel_values2 = list(im2.getdata())
        im2.load()
        array2 = np.asarray(im2)
        
        P_r2 = []
        P_g2 = []
        P_b2 = []
        
        P_r2 = np.array([nilai(pixel_values2[i][0]) for i in range(height2*width2)])
        P_g2 = np.array([nilai(pixel_values2[i][1]) for i in range(height2*width2)])
        P_b2 = np.array([nilai(pixel_values2[i][2]) for i in range(height2*width2)])
        
        uni_r2, uni_g2, uni_b2 = ujiuniform(P_r2, P_g2, P_b2, width2, height2)
        
        ent_r2 = skimage.measure.shannon_entropy(P_r2)
        ent_g2 = skimage.measure.shannon_entropy(P_g2)
        ent_b2 = skimage.measure.shannon_entropy(P_b2)
        
        ent_2 = (ent_r2 + ent_g2 + ent_b2)/3
    
        uaci_result = uaci(im1, im2)
        
        npcr_result = npcrv(im1, im2)
        
        title = Label(F1, font=("Segoe UI",15), text = "Hasil Uji Kualitas")
        title.grid(row = 0, column = 0)
        
        t1 = Label(F2, font=("Segoe UI",12), text = "\t")
        t1.grid(row = 1, column = 0)
        
        t2 = Label(F2, font=("Segoe UI",12), text = "\t")
        t2.grid(row = 1, column = 1)
        
        t3 = Label(F2, font=("Segoe UI",12), text = "\t")
        t3.grid(row = 1, column = 2)
        
        t4 = Label(F2, font=("Segoe UI",12), text = "\t")
        t4.grid(row = 1, column = 3)
        
        t5 = Label(F2, font=("Segoe UI",12), text = "\t")
        t5.grid(row = 1, column = 4)
        
        t6 = Label(F2, font=("Segoe UI",12), text = "\t")
        t6.grid(row = 1, column = 5)
        
        t7 = Label(F2, font=("Segoe UI",12), text = "\t")
        t7.grid(row = 7, column = 6)
        
        t98 = Label(F2, font=("Segoe UI",12), text = "\t")
        t98.grid(row = 7, column = 5)
        
        t99 = Label(F2, font=("Segoe UI",12), text = "\t")
        t99.grid(row = 1, column = 6)
        
        t1_1 = Label(F2, font=("Segoe UI",12), text = "Citra 1")
        t1_1.grid(row = 2, column = 2)
        
        t2_1 = Label(F2, font=("Segoe UI",12), text = "Citra 2")
        t2_1.grid(row = 2, column = 5)
        
        t3_1 = Label(F2, font=("Segoe UI",12), text = "Uniform")
        t3_1.grid(row = 4, column = 0)
        
        t3_2 = Label(F2, font=("Segoe UI",12), text = str(uni_r1)[:7])
        t3_2.grid(row = 4, column = 1)
        
        t3_3 = Label(F2, font=("Segoe UI",12), text = str(uni_g1)[:7])
        t3_3.grid(row = 4, column = 2)
        
        t3_4 = Label(F2, font=("Segoe UI",12), text = str(uni_b1)[:7])
        t3_4.grid(row = 4, column = 3)
        
        t3_5 = Label(F2, font=("Segoe UI",12), text = str(uni_r2)[:7])
        t3_5.grid(row = 4, column = 4)
        
        t3_6 = Label(F2, font=("Segoe UI",12), text = str(uni_g2)[:7])
        t3_6.grid(row = 4, column = 5)
        
        t3_7 = Label(F2, font=("Segoe UI",12), text = str(uni_b2)[:7])
        t3_7.grid(row = 4, column = 6)
        
        t4_0 = Label(F2, font=("Segoe UI",12), text = "Citra 1")
        t4_0.grid(row = 5, column = 2)        
        
        t4_0 = Label(F2, font=("Segoe UI",12), text = "Citra 2")
        t4_0.grid(row = 5, column = 5)  
        
        t4_1 = Label(F2, font=("Segoe UI",12), text = "Entropi")
        t4_1.grid(row = 6, column = 0)
        
        t4_3 = Label(F2, font=("Segoe UI",12), text = str(ent_1)[:5])
        t4_3.grid(row = 6, column = 2)
        
        t4_6 = Label(F2, font=("Segoe UI",12), text = str(ent_2)[:5])
        t4_6.grid(row = 6, column = 5)
    
        t5_1 = Label(F2, font=("Segoe UI",12), text = "R")
        t5_1.grid(row = 3, column = 1)
        
        t6_1 = Label(F2, font=("Segoe UI",12), text = "G")
        t6_1.grid(row = 3, column = 2)
        
        t7_1 = Label(F2, font=("Segoe UI",12), text = "B")
        t7_1.grid(row = 3, column = 3)
        
        t5_1 = Label(F2, font=("Segoe UI",12), text = "R")
        t5_1.grid(row = 3, column = 4)
        
        t8_1 = Label(F2, font=("Segoe UI",12), text = "G")
        t8_1.grid(row = 3, column = 5)
        
        t9_1 = Label(F2, font=("Segoe UI",12), text = "B")
        t9_1.grid(row = 3, column = 6)
        
        hasil_1 = Label(F2, font=("Segoe UI",12), text = "UACI")
        hasil_1.grid(row = 8, column = 1)
        
        hasil_2 = Label(F2, font=("Segoe UI",12), text = "NPCR")
        hasil_2.grid(row = 8, column = 4)
        
        hasil_3 = Label(F2, font=("Segoe UI",12), text = str(uaci_result)[:5])
        hasil_3.grid(row = 8, column = 2)
        
        hasil_4 = Label(F2, font=("Segoe UI",12), text = str(npcr_result)[:4] +"%")
        hasil_4.grid(row = 8, column = 5)
        
        
    ll7 = Label(Frr3, text = "\t")
    ll7.pack()
    
    x1 = Button(Frr2,padx=3, pady=3, bd=5, fg="black", font=("Segoe UI",10), width=15, text="Pilih Citra 1", command = gambar1)
    x1.grid(row=1,column=2)
    
    x2 = Button(Frr2,padx=3, pady=3, bd=5, fg="black", font=("Segoe UI",10), width=15, text="Pilih Citra 2", command = gambar2)
    x2.grid(row=1,column=4)
    
    x3 = Button(Frr3,padx=3, pady=3, bd=5, fg="black", font=("Segoe UI",10), width=15, text="Uji Statistik", command = hasil)
    x3.pack()
    
    Frr4 = Frame(statt, width = 500, height = 200)
    Frr4.pack(side=TOP)
    
    ll8 = Label(Frr4, text = "\t")
    ll8.pack()
    
    x4 = Button(Frr4,padx=3, pady=3, bd=5, fg="black", font=("Segoe UI",10), width=15, text= "Keluar", command = statt.destroy)
    x4.pack()
    
    statt.mainloop()

def roota_destroy():
    roota.destroy()
    
roota = Tk()
roota.geometry("600x500")
roota.title("Program Modulo Sine-PWLCM")

F11 = Frame(roota, width = 850, height = 80)
F11.pack(side=TOP)
    
L1 = Label(F11, text = 'Kriptografi Berbasis Fungsi Modulo Sine-PWLCM', font = ('Segoe UI', 18))
L1.place(x = 65, y = 25)

F21 = Frame(roota, width = 850, height = 375)
F21.pack(side=TOP)

F212 = Frame(F21, width = 400, height = 375)
F212.pack(side=LEFT)

#################################################################################################################
tampilan1 = Label(F212, text = "Enkripsi & Dekripsi", font = ("Segoe UI", 15))
tampilan1.place(x = 120, y = 25)

tombol1 = Button(F212, text = "Enkripsi", padx=4, pady=4, bd=6, command = pencet1)
tombol1.place(x = 119, y = 65)

tombol2 = Button(F212, text = "Dekripsi", padx=4, pady=4, bd=6, command = pencet2)
tombol2.place(x = 224, y = 65)

tampilan2 = Label(F212, text = "Uji Kualitas", font = ("Segoe UI", 15))
tampilan2.place(x = 155, y = 140)

tombol3 = Button(F212, text = "Uji Kualitas\nCitra 1", padx=4, pady=4, bd=6, command = pencet3)
tombol3.place(x = 109, y = 175)

tombol4 = Button(F212, text = "Uji Kualitas\nCitra 2", padx=4, pady=4, bd=6, command = pencet4)
tombol4.place(x = 214, y = 175)

tombol5 = Button(F212, text = "Uji Kualitas\nCitra 3", padx = 4, pady = 4, bd = 6, command = pencet5)
tombol5.place(x = 162, y = 245)

tombol6 = Button(F212, text = "Keluar", padx = 4, pady = 4, bd = 6, command = roota_destroy)
tombol6.place(x = 172, y = 310)

#################################################################################################################



roota.mainloop()