It's a fork from https://github.com/Frutto-Hub/akniga.org_book_downloader

# Akniga-grabber book downloader
Akniga.org book downloader is a python script and GUI for downloading books from akniga.org.

# Required
- Python3 (https://www.python.org/downloads)
- pip (https://pip.pypa.io/en/stable/installing/)
- virtualenv (https://pypi.python.org/pypi/virtualenv)
- Chrome web browser (https://www.google.com/intl/en_en/chrome/).
- ffmpeg
- - [Here](https://www.youtube.com/watch?v=jZLqNocSQDM) is a tutorial on how to install ffmpeg for Windows users.
- - Make sure you've added ffmpeg.exe path to PATH environment variable as on the video
- Optional git client (https://git-scm.com/downloads)

# Installation
[Download](https://github.com/fabrikant/akniga.org_book_downloader/archive/refs/heads/main.zip) and extract the source code

or use command
```
git clone https://github.com/fabrikant/akniga.org_book_downloader
```
Change to the directory with the file akniga_dl.py and install all dependencies:

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
or start script 
```
#Linux
./install.sh
#Windows
insatll.bat
```

# Usage:
GUI interface
```
#Linux
./GUI.sh
#Windows
GUI.bat
```
CLI interface:
```
#Linux
source .venv/bin/activate
python akniga_dl.py <book_url> <output_folder>
#Windows
.venv\Scripts\activate
python akniga_dl.py <book_url> <output_folder>
```
Where:
- <book_url> is a url to book you want to download
- <output_folder> is an absolute path to download folder


