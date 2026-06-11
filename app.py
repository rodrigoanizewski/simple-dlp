import threading
import queue
import json
import os
from flask import Flask, request, Response, stream_with_context, render_template
from yt_dlp import YoutubeDL

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    url = data.get('url', '')

    if not url:
        return Response(
            "data: " + json.dumps({"status": "error", "message": "No URL provided"}) + "\n\n",
            mimetype='text/event-stream'
        )

    q = queue.Queue()

    def progress_hook(d):
        q.put(d)

    def run_download():
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'merge_output_format': 'mp4',
            'outtmpl': os.path.join(os.path.expanduser('~'), 'Downloads', '%(title)s.%(ext)s'),
            'noplaylist': True,
            'quiet': True,
            'progress_hooks': [progress_hook],
        }
        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            q.put({"status": "error", "message": str(e)})
        finally:
            q.put(None)

    thread = threading.Thread(target=run_download)
    thread.start()

    def generate():
        yield "data: " + json.dumps({"status": "waiting"}) + "\n\n"

        while True:
            item = q.get()
            if item is None:
                break
            if item.get('status') == 'error':
                yield "data: " + json.dumps({"status": "error", "message": item.get('message', 'Unknown error')}) + "\n\n"
                break
            status = item.get('status', 'downloading')
            if status == 'downloading':
                progress = {
                    "status": "downloading",
                    "percent_str": item.get('_percent_str', '').strip(),
                    "speed_str": item.get('_speed_str', '').strip(),
                    "eta_str": item.get('_eta_str', '').strip(),
                }
                yield "data: " + json.dumps(progress) + "\n\n"
            elif status == 'finished':
                yield "data: " + json.dumps({"status": "finished"}) + "\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')


if __name__ == '__main__':
    app.run(debug=True)
