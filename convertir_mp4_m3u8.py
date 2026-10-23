import subprocess
import os

def convert_to_hls(input_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    output_m3u8 = os.path.join(output_dir, "viewUmbral.m3u8")

    cmd = [
        "ffmpeg",
        "-i", input_path,
        "-c", "copy",           # ✅ corrección aquí
        "-start_number", "0",
        "-hls_time", "5",
        "-hls_list_size", "0",
        "-f", "hls",
        output_m3u8
    ]

    subprocess.run(cmd, check=True)
    print(f"HLS generado en: {output_m3u8}")

# Ejemplo de uso
convert_to_hls("C:/Users/sajhy/Downloads/CamtasiaStudio/viewUmbral.mp4", "E:/ArcGisTrabajo/Reproyeccion/videoconver")
