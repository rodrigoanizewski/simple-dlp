Act as an expert Senior Python Developer.

I need to build a lightweight, locally-hosted web application that serves as a simple GUI for yt-dlp.

Goal: Download YouTube videos in the highest possible native quality specifically optimized for video editors (Premiere Pro, DaVinci Resolve, After Effects). Do NOT perform any heavy video recoding or codec changes.

Tech Stack:

    Backend: Python with Flask (or FastAPI).

    Frontend: A single HTML file using Tailwind CSS (via CDN) for a clean, modern, dark-mode UI. Use vanilla JavaScript to handle the connection to the backend.

yt-dlp Specific Requirements:

    You must use the yt-dlp Python library, not subprocess command line calls.

    Crucial: Premiere Pro does not support .mkv files. You must instruct yt-dlp to download the best native video and audio, and merge them into an .mp4 container.

    Recommended format string: bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best

    Force the merge format: --merge-output-format mp4

    Save the downloaded files directly to the OS default "Downloads" folder.

UI Requirements:

    Language: English.

    Elements: A text input for the URL, a large "Download High Quality" button, and a status area.

    Feedback: The UI must not freeze during the download. It needs to show basic status updates (e.g., "Downloading...", "Merging...", "Done!").

Deliverables:
Please provide the complete, ready-to-run code in separate blocks (app.py, templates/index.html, and requirements.txt), along with step-by-step instructions on how to run it on any computer.