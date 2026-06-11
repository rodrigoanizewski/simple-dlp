import threading
import queue
import json
import os
from flask import Flask, request, Response, stream_with_context, render_template
from yt_dlp import YoutubeDL

app = Flask(__name__)


def build_ydl_opts(mode, video_quality, audio_quality, clip_start='', clip_end='', playlist_items=''):
    vq = f'[height<={video_quality}]' if video_quality != 'best' else ''
    aq = f'[abr<={audio_quality}]' if audio_quality != 'best' else ''
    base = os.path.join(os.path.expanduser('~'), 'Downloads', '%(title)s.%(ext)s')

    if mode == 'audio':
        opts = {
            'format': f'bestaudio{aq}[ext=m4a]/bestaudio{aq}',
            'outtmpl': base,
            'quiet': True,
        }
    elif mode == 'video':
        opts = {
            'format': f'bestvideo{vq}[ext=mp4]/bestvideo{vq}',
            'outtmpl': base,
            'quiet': True,
        }
    else:
        opts = {
            'format': f'bestvideo{vq}[ext=mp4]+bestaudio{aq}[ext=m4a]/best{vq}[ext=mp4]/best',
            'merge_output_format': 'mp4',
            'outtmpl': base,
            'quiet': True,
        }

    if clip_start or clip_end:
        start = clip_start or '0:00'
        end = clip_end or ''
        opts['download_sections'] = f'*{start}-{end}' if end else f'*{start}-'

    if playlist_items:
        opts['playlist_items'] = playlist_items
        opts['noplaylist'] = False
    else:
        opts['noplaylist'] = True

    return opts


def format_duration(seconds):
    if seconds is None:
        return ''
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f'{h}:{m:02d}:{s:02d}' if h else f'{m}:{s:02d}'


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    url = data.get('url', '')
    action = data.get('action', 'download')

    if not url:
        return Response(
            "data: " + json.dumps({"status": "error", "message": "No URL provided"}) + "\n\n",
            mimetype='text/event-stream'
        )

    q = queue.Queue()

    if action == 'list':
        def run_list():
            ydl_opts = {
                'quiet': True,
                'noplaylist': False,
            }
            try:
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
            except Exception as e:
                q.put({"status": "error", "message": str(e)})
                q.put(None)
                return

            entries = info.get('entries')
            if entries:
                title = info.get('title', 'Playlist')
                q.put({"status": "playlist_meta", "title": title, "count": len(entries)})
                for i, entry in enumerate(entries, 1):
                    if entry is None:
                        continue
                    q.put({
                        "status": "playlist_entry",
                        "index": i,
                        "title": entry.get('title', f'Video {i}'),
                        "duration": entry.get('duration'),
                        "id": entry.get('id', ''),
                    })
                q.put({"status": "playlist_done"})
            else:
                q.put({
                    "status": "single_video",
                    "title": info.get('title', 'Untitled'),
                    "duration": info.get('duration'),
                })
                q.put({"status": "playlist_done"})
            q.put(None)

        thread = threading.Thread(target=run_list)
        thread.start()
    else:
        mode = data.get('mode', 'video+audio')
        video_quality = data.get('video_quality', 'best')
        audio_quality = data.get('audio_quality', 'best')
        clip_start = data.get('clip_start', '')
        clip_end = data.get('clip_end', '')
        playlist_items = data.get('playlist_items', '')

        def progress_hook(d):
            q.put(d)

        def run_download():
            ydl_opts = build_ydl_opts(mode, video_quality, audio_quality, clip_start, clip_end, playlist_items)
            ydl_opts['progress_hooks'] = [progress_hook]
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
            if item.get('status') in ('playlist_meta', 'playlist_entry', 'playlist_done', 'single_video'):
                yield "data: " + json.dumps(item) + "\n\n"
                continue
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
