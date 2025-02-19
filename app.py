from flask import Flask, request, jsonify, render_template, send_from_directory
import subprocess
import os
import uuid
import re

app = Flask(__name__, template_folder="templates", static_folder="static")

# Thư mục lưu video cắt
OUTPUT_DIR = "downloads"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_video_info(youtube_url):
    """ Lấy danh sách chất lượng video, thời lượng và tiêu đề """
    command = ["yt-dlp", "-F", youtube_url]
    result = subprocess.run(command, capture_output=True, text=True)

    # Lấy thời lượng và tiêu đề video
    duration_command = ["yt-dlp", "--get-duration", youtube_url]
    duration_result = subprocess.run(duration_command, capture_output=True, text=True)
    duration = duration_result.stdout.strip()

    title_command = ["yt-dlp", "--get-title", youtube_url]
    title_result = subprocess.run(title_command, capture_output=True, text=True)
    title = title_result.stdout.strip()

    # Lọc danh sách định dạng (bỏ qua các định dạng m3u8)
    lines = result.stdout.split("\n")
    formats = []
    for line in lines:
        if line.strip().split(" ")[0].isdigit():
            format_info = line.strip()
            # Bỏ qua các định dạng m3u8
            if "m3u8" not in format_info.lower():
                formats.append(format_info)

    return {
        "title": title,
        "duration": duration,
        "formats": "\n".join(formats),
    }

def get_video_url(youtube_url, format_code):
    """ Lấy URL trực tiếp của video với độ phân giải được chọn """
    command = ["yt-dlp", "-f", format_code, "-g", youtube_url]
    result = subprocess.run(command, capture_output=True, text=True)
    return result.stdout.strip()

def download_segment(video_url, start_time, end_time, output_path):
    """ Cắt và tải đoạn video bằng ffmpeg """
    command = [
        "ffmpeg", "-ss", start_time, "-i", video_url, "-to", end_time,
        "-c", "copy", output_path
    ]
    subprocess.run(command)

@app.route("/")
def index():
    return render_template("index.html")

@app.route('/load_formats', methods=['POST'])
def load_formats():
    try:
        data = request.json
        youtube_url = data.get("url")

        if not youtube_url:
            return jsonify({"error": "Thiếu URL"}), 400

        video_info = get_video_info(youtube_url)
        return jsonify(video_info)
    except Exception as e:
        return jsonify({"error": f"Lỗi khi lấy thông tin video: {str(e)}"}), 500

def validate_time_format(time_str):
    """ Kiểm tra định dạng thời gian HH:MM:SS """
    return re.match(r"^\d{2}:\d{2}:\d{2}$", time_str) is not None

@app.route('/download', methods=['POST'])
def download():
    try:
        data = request.json
        youtube_url = data.get("url")
        format_code = data.get("format")
        start_time = data.get("start_time")
        end_time = data.get("end_time")

        if not youtube_url or not format_code or not start_time or not end_time:
            return jsonify({"error": "Thiếu thông tin"}), 400

        if not validate_time_format(start_time) or not validate_time_format(end_time):
            return jsonify({"error": "Thời gian không hợp lệ (HH:MM:SS)"}), 400

        video_url = get_video_url(youtube_url, format_code)
        if not video_url:
            return jsonify({"error": "Không lấy được link video"}), 500

        file_name = f"{uuid.uuid4()}.mp4"
        output_file = os.path.join(OUTPUT_DIR, file_name)

        download_segment(video_url, start_time, end_time, output_file)

        return jsonify({
            "message": "Đã xong!",
            "file": file_name
        })
    except Exception as e:
        return jsonify({"error": f"Lỗi khi tải video: {str(e)}"}), 500

@app.route('/download_file/<filename>')
def download_file(filename):
    """ API cho phép tải file đã tải về """
    return send_from_directory(OUTPUT_DIR, filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
