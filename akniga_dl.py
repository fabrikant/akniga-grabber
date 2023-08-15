import os
import sys
import subprocess
import json
import brotli
import shutil
import requests
from pathlib import Path
from pathvalidate import sanitize_filename
from selenium.webdriver.chrome.service import Service as ChromeService
from seleniumwire import webdriver
from webdriver_manager.chrome import ChromeDriverManager


def download_cover(cover_url, cover_file_name):
    big_picture_url = cover_url.replace("100x100crop", "400x")
    # try to download big picture
    res = requests.get(big_picture_url, stream=True)
    if res.status_code == 200:
        with open(cover_file_name, 'wb') as f:
            shutil.copyfileobj(res.raw, f)
    else:
        # big picture not found, try to download preview
        res = requests.get(cover_url, stream=True)
        if res.status_code == 200:
            with open(cover_file_name, 'wb') as f:
                shutil.copyfileobj(res.raw, f)


def download_book(book_url, output_folder):
    # create output folder
    Path(output_folder).mkdir(exist_ok=True)

    print('starting browser')
    service = ChromeService(executable_path=ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.add_argument('headless')

    driver = webdriver.Chrome(service=service, options=options)
    print('parsing the page: ' + book_url)
    driver.get(book_url)

    all_requests = driver.requests

    # find request with book json data
    book_json_requests = [r for r in all_requests if r.method == 'POST' and r.path.startswith('/ajax/b/')]

    # assert that we have only 1 request found
    assert len(book_json_requests) == 1
    book_json = json.loads(brotli.decompress(book_json_requests[0].response.body))

    # add book id to book json dictionary for convenience
    book_json['id'] = book_json_requests[0].url.split('/')[-1]

    m3u8_url = ''
    # find request for m3u8 file
    for request in all_requests:
        if 'm3u8' in request.url:
            m3u8_url = request.url
            break

    driver.quit()

    if not m3u8_url:
        print('m3u8 file not found. Exiting...')
        exit()

    # sanitize (make valid) book title
    book_json['title'] = sanitize_filename(book_json['title'])
    book_folder = Path(output_folder) / book_json['title']

    # create new folder with book title
    Path(book_folder).mkdir(exist_ok=True)

    # create full book folder, full book .mp3 file will be downloaded there
    full_book_folder = book_folder / 'full book'
    Path(full_book_folder).mkdir(exist_ok=True)

    # download cover picture
    cover_url = book_json['preview']
    cover_file_name = full_book_folder / 'cover.jpg'
    download_cover(cover_url, cover_file_name)

    # download full audio file
    full_book_file_path = full_book_folder / book_json['title']
    ffmpeg_command = ['ffmpeg', '-y', '-hide_banner', '-i', m3u8_url, f'{full_book_file_path}.mp3']
    subprocess.run(ffmpeg_command)

    # separate audio file into chapters
    print(book_json)
    for chapter in json.loads(book_json['items']):
        chapter_path = book_folder / sanitize_filename(chapter['title'])

        # cut the chapter
        command_cut = ['ffmpeg', '-y', '-hide_banner', '-i', f'{full_book_file_path}.mp3', '-codec', 'copy',
                       '-ss', str(chapter['time_from_start']), '-to', str(chapter['time_finish']),
                       f'{chapter_path}_no_meta.mp3']
        subprocess.run(command_cut)

        # add metadata
        command_metadata = ['ffmpeg', '-y', '-hide_banner', '-i', f'{chapter_path}_no_meta.mp3']
        if Path(cover_file_name).exists():
            command_metadata = command_metadata + ['-i', cover_file_name, '-map', '0:0', '-map', '1:0']
        command_metadata = command_metadata + ['-codec', 'copy', '-id3v2_version', '3',
                                               '-metadata', 'title=' + chapter['title'],
                                               '-metadata', 'album=' + book_json['titleonly'],
                                               '-metadata', 'artist=' + book_json['author'],
                                               f'{chapter_path}.mp3']
        subprocess.run(command_metadata)
        # remove no_meta file
        os.remove(f'{chapter_path}_no_meta.mp3')

    # remove full book folder
    shutil.rmtree(full_book_folder, ignore_errors=True)


if __name__ == '__main__':
    # check command line agruments
    if len(sys.argv) < 2:
        print("usage: python akniga_dl.py <book_url> [<output_folder>]")
        exit(1)

    # parse command line arguments
    if len(sys.argv) > 2:
        out_folder = sys.argv[2]
    else:
        out_folder = '.'

    download_book(sys.argv[1], out_folder)
