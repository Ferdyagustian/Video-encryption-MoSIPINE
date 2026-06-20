import sys

path = 'c:/Skripsi/gui_video.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('defaultextension=".avi",', 'defaultextension=".mp4",')
content = content.replace('filetypes=[("Video File", "*.avi"),', 'filetypes=[("Video File", "*.mp4"),')
content = content.replace('Video Hasil Dekripsi (.avi)', 'Video Hasil Dekripsi (.mp4)')
content = content.replace('preview_noise.avi', 'preview_noise.mp4')
content = content.replace('Export Preview Noise (.avi)', 'Export Preview Noise (.mp4)')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated gui_video.py via script")
