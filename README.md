It's a fork from https://github.com/Frutto-Hub/akniga.org_book_downloader

# Akniga.org book downloader
Akniga.org book downloader is a simple python script for downloading books from akniga.org.

You can install all essential packages with simple command in terminal:
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
or start script 
```
./install.sh
```



ffmpeg is also required
* [Here](https://www.youtube.com/watch?v=jZLqNocSQDM) is a tutorial on how to install ffmpeg for Windows users.
* Make sure you've added ffmpeg.exe path to PATH environment variable as on the video

# Usage:
GUI interface

```
source .venv/bin/activate
python akniga_gui.py
```

CLI interface:

```
source .venv/bin/activate
python akniga_dl.py <book_url> [<output_folder>]
```
Where:
- <book_url> is a url to book you want to download
- <output_folder> is an absolute path to download folder (optional)


