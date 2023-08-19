import argparse
import os
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


def get_book_requests(book_url: str) -> list:
    print("Getting book requests. Please wait...")
    service = ChromeService(executable_path=ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.add_argument('headless')
    with webdriver.Chrome(service=service, options=options) as driver:
        driver.get(book_url)
        result = driver.requests
        driver.close()
        return result


def analyse_book_requests(book_requests: list) -> tuple:
    print('Analysing book requests...')
    try:
        # find request with book json data
        book_json_requests = [r for r in book_requests if r.method == 'POST' and r.path.startswith('/ajax/b/')]
        # assert that we have only 1 request for book data found
        assert len(book_json_requests) == 1, 'Error: Book data not found. Exiting.'
        print('Book data found')
        # find request with m3u8 file
        m3u8_file_requests = [r for r in book_requests if 'm3u8' in r.url]
        # assert that we have only 1 request for m3u8 file found
        assert len(m3u8_file_requests) == 1, 'Error: m3u8 file request not found. Exiting.'
        print('m3u8 file found')
        book_json = json.loads(brotli.decompress(book_json_requests[0].response.body))
        return book_json, m3u8_file_requests[0].url
    except AssertionError as message:
        print(message)
        exit(1)


def download_book(book_url, output_folder):
    # create output folder
    Path(output_folder).mkdir(exist_ok=True)

    book_requests = get_book_requests(book_url)
    book_json, m3u8_url = analyse_book_requests(book_requests)

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
    print('The book has been downloaded: {0}'.format(book_folder))
    return book_folder


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download a book from akniga.org')
    parser.add_argument('url', help='Book\'s url for downloading')
    parser.add_argument('output', help='Absolute or relative path where book will be downloaded')
    args = parser.parse_args()
    print(args)

    download_book(args.url, args.output)
