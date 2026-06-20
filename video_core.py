# pylint: disable=no-member, invalid-name, missing-function-docstring
# pylint: disable=broad-exception-caught, broad-exception-raised
# pylint: disable=too-many-locals, too-many-statements, too-many-branches
# pylint: disable=import-outside-toplevel, consider-using-with
# pylint: disable=subprocess-run-check, unused-variable, no-else-return
# pylint: disable=multiple-statements, trailing-whitespace, line-too-long
# pylint: disable=missing-module-docstring, too-many-arguments, too-many-positional-arguments
# pylint: disable=consider-using-from-import, trailing-newlines

import os
import struct
import time

import cv2
import numpy as np
from PIL import Image

from sipine import generate_keystream_video_np

# Mode constants (sama dengan di sipine.py _generate_keystream_core)
_MODE = {"mosipine": 0, "sine": 1, "pwlcm": 2}

# Magic bytes untuk header VEN2
_VENC2_MAGIC = b"VEN2"

def _get_keystream(x1, x2, p, beta, iter_bakar, total, mode_str):
    """Pembantu: kembalikan numpy uint8 keystream (N_SKIP=3, versi video)."""
    mode_int = _MODE.get(mode_str, 0)
    return generate_keystream_video_np(x1, x2, p, beta, iter_bakar, total, mode_int)

def encrypt_video_audio_to_VEN2(input_video_path, output_bin_path, mode, params, progress_callback=None):
    """
    Ekstrak video dan audio (jika ada), enkripsi dengan keystream chaos (XOR vektorisasi NumPy),
    dan simpan dalam satu file biner (.bin) yang memuat header kustom, data video, dan data audio.
    """
    import scipy.io.wavfile as wavfile
    from audio_core import extract_audio_from_video
    
    start_time = time.time()
    
    # Buka video untuk dapatkan frame dan metadata
    cap = cv2.VideoCapture(input_video_path)
    if not cap.isOpened():
        raise Exception(f"Gagal membuka video: {input_video_path}")

    width       = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height      = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps         = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames <= 0:
        total_frames = 99999  # Fallback
        
    total_pixels_per_frame = width * height * 3

    # Cek & ekstrak audio ke temp file
    has_audio = 0
    audio_sample_rate = 0
    audio_channels = 0
    num_audio_samples = 0
    audio_raw_bytes = b""
    
    temp_wav_path = os.path.join("Tempat_gambar", "audio_asli.wav")
    try:
        os.makedirs("Tempat_gambar", exist_ok=True)
        extract_audio_from_video(input_video_path, temp_wav_path)
        rate, data = wavfile.read(temp_wav_path)
        if data.dtype != np.int16:
            data = data.astype(np.int16)
            
        audio_sample_rate = rate
        audio_channels = data.shape[1] if data.ndim == 2 else 1
        num_audio_samples = data.shape[0]
        audio_raw_bytes = data.tobytes()
        has_audio = 1
        # sengaja tidak dihapus (os.remove) agar bisa digunakan untuk uji kualitas
    except Exception as e:
        print(f"Info: Tidak ada audio atau gagal ekstrak: {e}")
        has_audio = 0

    x1   = float(params['x1'])
    x2   = float(params['x2'])
    p    = float(params.get('p', 0.25))
    beta = float(params['beta'])
    
    # --- IMPLEMENTASI IV UNTUK MITIGASI TWO-TIME PAD ---
    iv_video = int.from_bytes(os.urandom(4), byteorder='little')
    iv_modifier = iv_video / 4294967295.0
    
    x1_v = (x1 + iv_modifier) % 1.0
    x2_v = (x2 + iv_modifier) % 1.0
    # ---------------------------------------------------
    
    with open(output_bin_path, 'wb') as f:
        # Header VENC2: tepat 36 byte (tambah IV 4 byte di akhir)
        _HEADER_FMT = '<4sIIIfIHIHI'
        header = struct.pack(_HEADER_FMT,
                             _VENC2_MAGIC,
                             width, height, total_frames, fps,
                             audio_sample_rate, audio_channels,
                             num_audio_samples, has_audio,
                             iv_video)
        # Pastikan tepat 36 byte
        assert len(header) == 36, f"Header size mismatch: {len(header)}"
        f.write(header)

        # Enkripsi Video (frame per frame)
        iter_bakar = 1000
        frame_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            ks = _get_keystream(x1_v, x2_v, p, beta, iter_bakar, total_pixels_per_frame, mode)
            cipher_bytes = frame.flatten() ^ ks
            f.write(cipher_bytes.tobytes())

            iter_bakar = 10
            x1_v = (x1_v + 0.0019) % 1.0
            x2_v = (x2_v + 0.0073) % 1.0
            frame_count += 1

            if progress_callback:
                # Video progress: 0 - 80% (jika ada audio), 0 - 100% (jika tidak ada)
                perc = (frame_count / total_frames) * (0.8 if has_audio else 1.0)
                progress_callback(perc * 100)
                
        cap.release()

        # Update total_frames jika beda
        if frame_count != total_frames:
            f.seek(12) # Offset untuk TotalFrames sesudah Magic(4)+Width(4)+Height(4)
            f.write(struct.pack('<I', frame_count))
            f.seek(0, 2) # Kembali ke end of file

        # Enkripsi Audio (jika ada)
        if has_audio:
            if progress_callback: progress_callback(85.0)
            
            # --- IMPLEMENTASI IV UNTUK MITIGASI TWO-TIME PAD ---
            # Domain pemisah untuk audio: User Key + Kebalikan IV
            x1_a = (float(params['x1']) + (1.0 - iv_modifier)) % 1.0
            x2_a = (float(params['x2']) + (1.0 - iv_modifier)) % 1.0
            
            audio_total_bytes = len(audio_raw_bytes)
            ks_audio = _get_keystream(x1_a, x2_a, p, beta, 1000, audio_total_bytes, mode)
            
            audio_arr = np.frombuffer(audio_raw_bytes, dtype=np.uint8)
            cipher_audio_arr = audio_arr ^ ks_audio
            f.write(cipher_audio_arr.tobytes())
            
            # --- Simpan audio_noise.wav untuk uji kualitas ---
            try:
                noise_int16 = cipher_audio_arr.view(np.int16)
                if audio_channels == 2:
                    noise_int16 = noise_int16.reshape((-1, 2))
                wavfile.write(os.path.join("Tempat_gambar", "audio_noise.wav"), audio_sample_rate, noise_int16)
            except Exception as ae:
                print("Info: Gagal menyimpan audio noise:", ae)
            # -------------------------------------------------
            
            if progress_callback: progress_callback(100.0)

    return True


def decrypt_VEN2_to_video_audio(input_bin_path, output_mp4_path, mode, params, progress_callback=None):
    """
    Mendekripsi file .bin (unified) kembali ke video dan menggabungkan audio-nya menggunakan ffmpeg,
    menghasilkan file .mp4 yang berisi video dan audio.
    """
    import scipy.io.wavfile as wavfile
    from audio_core import mux_video_audio, _get_ffmpeg
    import subprocess
    
    if not os.path.exists(input_bin_path):
        raise Exception(f"File biner tidak ditemukan: {input_bin_path}")

    with open(input_bin_path, 'rb') as f:
        # Baca Header VEN2 (36 byte)
        header = f.read(36)
        if len(header) < 36:
            raise Exception("File biner korup (ukuran header kurang dari 36 byte).")

        magic = header[:4]
        if magic == _VENC2_MAGIC:
            _HEADER_FMT = '<4sIIIfIHIHI'
            _, width, height, total_frames, fps, \
            audio_sample_rate, audio_channels, num_audio_samples, \
            has_audio, iv_video = struct.unpack(_HEADER_FMT, header[:36])
            iv_modifier = iv_video / 4294967295.0
        else:
            raise Exception("File bukan format VEN2 terpadu (atau korup).")

        temp_mp4_path = output_mp4_path + ".temp.mp4" if has_audio else output_mp4_path

        # Coba gunakan libx264rgb (lossless penuh, tanpa konversi BGR→YUV)
        # Fallback ke libx264 + yuv444p jika libx264rgb tidak tersedia
        def _build_ffmpeg_lossless_cmd(out_path):
            import subprocess as _sp
            probe = _sp.run(
                [_get_ffmpeg(), '-encoders'],
                stdout=_sp.PIPE, stderr=_sp.PIPE
            )
            if b'libx264rgb' in probe.stdout:
                return [
                    _get_ffmpeg(), '-y',
                    '-f', 'rawvideo', '-vcodec', 'rawvideo',
                    '-s', f'{width}x{height}',
                    '-pix_fmt', 'bgr24',
                    '-r', str(fps),
                    '-i', '-',
                    '-c:v', 'libx264rgb',
                    '-crf', '0',
                    '-preset', 'ultrafast',
                    '-pix_fmt', 'bgr24',
                    out_path
                ]
            else:
                # Fallback: libx264 dengan yuv444p (lossless tanpa chroma subsampling)
                print("Info: libx264rgb tidak tersedia, menggunakan libx264 + yuv444p (lossless).")
                return [
                    _get_ffmpeg(), '-y',
                    '-f', 'rawvideo', '-vcodec', 'rawvideo',
                    '-s', f'{width}x{height}',
                    '-pix_fmt', 'bgr24',
                    '-r', str(fps),
                    '-i', '-',
                    '-c:v', 'libx264',
                    '-crf', '0',
                    '-preset', 'ultrafast',
                    '-pix_fmt', 'yuv444p',
                    out_path
                ]

        ffmpeg_cmd = _build_ffmpeg_lossless_cmd(temp_mp4_path)
        process = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

        x1   = float(params['x1'])
        x2   = float(params['x2'])
        p    = float(params.get('p', 0.25))
        beta = float(params['beta'])
        total_pixels_per_frame = width * height * 3

        x1_v = (x1 + iv_modifier) % 1.0
        x2_v = (x2 + iv_modifier) % 1.0

        iter_bakar = 1000
        for frame_idx in range(total_frames):
            raw = f.read(total_pixels_per_frame)
            if not raw or len(raw) < total_pixels_per_frame:
                break

            cipher = np.frombuffer(raw, dtype=np.uint8)
            ks = _get_keystream(x1_v, x2_v, p, beta, iter_bakar, total_pixels_per_frame, mode)

            plain = cipher ^ ks
            process.stdin.write(plain.tobytes())

            iter_bakar = 10
            x1_v = (x1_v + 0.0019) % 1.0
            x2_v = (x2_v + 0.0073) % 1.0

            if progress_callback:
                perc = ( (frame_idx+1) / total_frames ) * (0.8 if has_audio else 1.0)
                progress_callback(perc * 100)

        process.stdin.close()
        process.wait()

        # Dekripsi Audio jika ada
        if has_audio:
            if progress_callback: progress_callback(85.0)
            
            bytes_to_read = num_audio_samples * audio_channels * 2  # int16 = 2 bytes/sample
            raw_audio = f.read(bytes_to_read)
            
            x1_a = (float(params['x1']) + (1.0 - iv_modifier)) % 1.0
            x2_a = (float(params['x2']) + (1.0 - iv_modifier)) % 1.0
                
            ks_audio = _get_keystream(x1_a, x2_a, p, beta, 1000, len(raw_audio), mode)
            
            cipher_audio_arr = np.frombuffer(raw_audio, dtype=np.uint8)
            plain_audio_arr = cipher_audio_arr ^ ks_audio
            
            plain_int16 = plain_audio_arr.view(np.int16)
            if audio_channels == 2:
                plain_int16 = plain_int16.reshape((-1, 2))
                
            temp_wav_path = output_mp4_path + ".temp.wav"
            wavfile.write(temp_wav_path, audio_sample_rate, plain_int16)
            
            if progress_callback: progress_callback(95.0)
            
            # Mux
            mux_video_audio(temp_mp4_path, temp_wav_path, output_mp4_path)
            
            try:
                import shutil
                os.makedirs("Tempat_gambar", exist_ok=True)
                shutil.copy2(temp_wav_path, os.path.join("Tempat_gambar", "audio_terdekripsi.wav"))
                os.remove(temp_mp4_path)
                os.remove(temp_wav_path)
            except Exception as e:
                print(f"Warning: Gagal menghapus file temp: {e}")
                
            if progress_callback: progress_callback(100.0)

    return True


def export_bin_to_noise_video(input_bin_path, output_avi_path, progress_callback=None):
    """
    Mengekspor file .bin terenkripsi langsung ke file .avi as-is (tanpa dekripsi).
    Ini menghasilkan video semut/noise dan audio noise/static yang bisa diputar di media player biasa.
    """
    import scipy.io.wavfile as wavfile
    from audio_core import mux_video_audio
    
    if not os.path.exists(input_bin_path):
        raise Exception(f"File biner tidak ditemukan: {input_bin_path}")

    with open(input_bin_path, 'rb') as f:
        # Baca Header VEN2
        header = f.read(36)
        if len(header) < 36:
            raise Exception("File bukan format VEN2 terpadu (atau korup).")

        magic = header[:4]
        if magic == _VENC2_MAGIC:
            _HEADER_FMT = '<4sIIIfIHIHI'
            _, width, height, total_frames, fps, \
            audio_sample_rate, audio_channels, num_audio_samples, \
            has_audio, _ = struct.unpack(_HEADER_FMT, header[:36])
        else:
            raise Exception("File bukan format VEN2 terpadu (atau korup).")

        import subprocess
        from audio_core import _get_ffmpeg

        temp_avi_path = output_avi_path + ".temp.mp4" if has_audio else output_avi_path

        # Gunakan FFmpeg lossless (libx264rgb) agar konsisten dengan fungsi dekripsi
        def _build_ffmpeg_noise_cmd(out_path):
            probe = subprocess.run(
                [_get_ffmpeg(), '-encoders'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            if b'libx264rgb' in probe.stdout:
                return [
                    _get_ffmpeg(), '-y',
                    '-f', 'rawvideo', '-vcodec', 'rawvideo',
                    '-s', f'{width}x{height}',
                    '-pix_fmt', 'bgr24',
                    '-r', str(fps),
                    '-i', '-',
                    '-c:v', 'libx264rgb',
                    '-crf', '0',
                    '-preset', 'ultrafast',
                    '-pix_fmt', 'bgr24',
                    out_path
                ]
            else:
                return [
                    _get_ffmpeg(), '-y',
                    '-f', 'rawvideo', '-vcodec', 'rawvideo',
                    '-s', f'{width}x{height}',
                    '-pix_fmt', 'bgr24',
                    '-r', str(fps),
                    '-i', '-',
                    '-c:v', 'libx264',
                    '-crf', '0',
                    '-preset', 'ultrafast',
                    '-pix_fmt', 'yuv444p',
                    out_path
                ]

        ffmpeg_cmd = _build_ffmpeg_noise_cmd(temp_avi_path)
        process = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

        total_pixels_per_frame = width * height * 3

        for frame_idx in range(total_frames):
            raw = f.read(total_pixels_per_frame)
            if not raw or len(raw) < total_pixels_per_frame:
                break

            # Gunakan byte langsung sebagai pixel (noise)
            process.stdin.write(raw)

            if progress_callback:
                perc = ( (frame_idx+1) / total_frames ) * (0.8 if has_audio else 1.0)
                progress_callback(perc * 100)

        process.stdin.close()
        process.wait()

        # Audio Noise
        if has_audio:
            if progress_callback: progress_callback(85.0)
            
            bytes_to_read = num_audio_samples * audio_channels * 2
            raw_audio = f.read(bytes_to_read)
            
            # Gunakan byte langsung sebagai audio (noise)
            noise_audio_arr = np.frombuffer(raw_audio, dtype=np.uint8)
            noise_int16 = noise_audio_arr.view(np.int16)
            
            if audio_channels == 2:
                noise_int16 = noise_int16.reshape((-1, 2))
                
            temp_wav_path = output_avi_path + ".temp.wav"
            wavfile.write(temp_wav_path, audio_sample_rate, noise_int16)
            
            if progress_callback: progress_callback(95.0)
            
            # Mux
            mux_video_audio(temp_avi_path, temp_wav_path, output_avi_path)
            
            try:
                os.remove(temp_avi_path)
                os.remove(temp_wav_path)
            except Exception as e:
                print(f"Warning: Gagal menghapus file temp: {e}")
                
            if progress_callback: progress_callback(100.0)

    return True


# Fungsi fallback lama yang akan dipanggil jika format file bukan format VENC baru
def decrypt_VEN2_to_video(input_bin_path, output_video_path, mode, params,
                            progress_callback=None):
    if not os.path.exists(input_bin_path):
        raise Exception(f"File biner tidak ditemukan: {input_bin_path}")

    with open(input_bin_path, 'rb') as f:
        header = f.read(16)
        if len(header) < 16:
            raise Exception("File biner korup atau format tidak sesuai.")
        width, height, total_frames, fps = struct.unpack('<IIIf', header)

        import subprocess
        from audio_core import _get_ffmpeg

        # Ganti XVID dengan FFmpeg lossless untuk konsistensi MSE = 0
        def _build_ffmpeg_fallback_cmd(out_path):
            probe = subprocess.run(
                [_get_ffmpeg(), '-encoders'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            if b'libx264rgb' in probe.stdout:
                return [
                    _get_ffmpeg(), '-y',
                    '-f', 'rawvideo', '-vcodec', 'rawvideo',
                    '-s', f'{width}x{height}',
                    '-pix_fmt', 'bgr24',
                    '-r', str(fps),
                    '-i', '-',
                    '-c:v', 'libx264rgb',
                    '-crf', '0',
                    '-preset', 'ultrafast',
                    '-pix_fmt', 'bgr24',
                    out_path
                ]
            else:
                return [
                    _get_ffmpeg(), '-y',
                    '-f', 'rawvideo', '-vcodec', 'rawvideo',
                    '-s', f'{width}x{height}',
                    '-pix_fmt', 'bgr24',
                    '-r', str(fps),
                    '-i', '-',
                    '-c:v', 'libx264',
                    '-crf', '0',
                    '-preset', 'ultrafast',
                    '-pix_fmt', 'yuv444p',
                    out_path
                ]

        ffmpeg_cmd = _build_ffmpeg_fallback_cmd(output_video_path)
        process = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

        x1   = float(params['x1'])
        x2   = float(params['x2'])
        p    = float(params.get('p', 0.25))
        beta = float(params['beta'])
        total_pixels = width * height * 3
        bytes_to_read = total_pixels

        iter_bakar = 1000
        for frame_idx in range(total_frames):
            raw = f.read(bytes_to_read)
            if not raw or len(raw) < bytes_to_read:
                break

            cipher = np.frombuffer(raw, dtype=np.uint8)
            ks = _get_keystream(x1, x2, p, beta, iter_bakar, total_pixels, mode)

            plain = cipher ^ ks
            process.stdin.write(plain.tobytes())

            iter_bakar = 10
            x1 = (x1 + 0.0019) % 1.0
            x2 = (x2 + 0.0073) % 1.0

            if progress_callback:
                perc = ((frame_idx + 1) / total_frames) * 100
                progress_callback(perc)

        # Selesaikan FFmpeg setelah semua frame dikirim, masih dalam with block
        process.stdin.close()
        process.wait()

    return True


def extract_sample_frames(video_path, out_dir):
    """
    Ekstrak 3 frame sampel representatif dari video pada posisi 10%, 50%, dan 90%.
    Simpan sebagai PNG di out_dir.
    Return: tuple (path_awal, path_tengah, path_akhir) atau raises Exception jika gagal.
    """
    os.makedirs(out_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise Exception(f"Gagal membuka video: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames <= 0:
        cap.release()
        raise Exception("Video tidak memiliki informasi total frame yang valid.")

    positions = {
        "awal":   max(0, int(total_frames * 0.10)),
        "tengah": max(0, int(total_frames * 0.50)),
        "akhir":  max(0, int(total_frames * 0.90)),
    }

    paths = {}
    for label, frame_idx in positions.items():
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, total_frames - 1))
            ret, frame = cap.read()
        if not ret:
            cap.release()
            raise Exception(f"Gagal membaca frame pada posisi {label} (frame #{frame_idx}).")
        out_path = os.path.join(out_dir, f"frame_sampel_{label}.png")
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        Image.fromarray(frame_rgb).save(out_path)
        paths[label] = out_path

    cap.release()
    return paths["awal"], paths["tengah"], paths["akhir"]


def extract_single_frame_from_bin(bin_path, frame_position_ratio, out_path):
    """
    Ekstrak satu frame dari file .bin terenkripsi (raw VEN2) berdasarkan rasio posisi (0.0–1.0).
    Mendukung format VENC baru dan format lama.
    """
    if not os.path.exists(bin_path):
        raise Exception(f"File biner tidak ditemukan: {bin_path}")

    with open(bin_path, 'rb') as f:
        header_peek = f.read(36)
        if len(header_peek) < 36:
            raise Exception("File biner korup atau format tidak sesuai.")
            
        magic = header_peek[:4]
        
        if magic == _VENC2_MAGIC:
            _HEADER_FMT = '<4sIIIfIHIHI'
            _, width, height, total_frames, fps, \
            _, _, _, _, _ = struct.unpack(_HEADER_FMT, header_peek[:36])
            data_offset = 36
        else:
            raise Exception("File bukan format VEN2 terpadu (atau korup).")

        frame_idx = max(0, min(int(total_frames * frame_position_ratio), total_frames - 1))
        bytes_per_frame = width * height * 3

        f.seek(data_offset + frame_idx * bytes_per_frame)
        raw = f.read(bytes_per_frame)
        if not raw or len(raw) < bytes_per_frame:
            raise Exception(f"Gagal membaca frame #{frame_idx} dari file biner.")

    arr = np.frombuffer(raw, dtype=np.uint8).reshape((height, width, 3))
    img = Image.fromarray(arr[:, :, ::-1])
    img.save(out_path)
    return out_path

