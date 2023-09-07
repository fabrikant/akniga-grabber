import argparse
import os
import subprocess
import json
import brotli
import shutil
import requests
import logging
from pathlib import Path
from pathvalidate import sanitize_filename
from selenium.webdriver.chrome.service import Service as ChromeService
from seleniumwire import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import urllib.parse


logger = logging.getLogger(__name__)


def ffmpeg_common_command():
    ffmpeg_log_level = 'fatal'
    if logger.root.level == logging.DEBUG:
        ffmpeg_log_level = '‘debug'
    elif logger.root.level == logging.INFO:
        ffmpeg_log_level = 'info'
    elif logger.root.level == logging.WARNING:
        ffmpeg_log_level = 'warning'
    elif logger.root.level == logging.ERROR:
        ffmpeg_log_level = 'error'
    return ['ffmpeg', '-y', '-hide_banner', '-loglevel', ffmpeg_log_level]


def get_cover_filename(dir_path):
    return dir_path / 'cover.jpg'


def download_cover(book_json, tmp_folder):
    cover_url = book_json['preview']
    cover_filename = get_cover_filename(tmp_folder)
    big_picture_url = cover_url.replace("100x100crop", "400x")
    # try to download big picture
    res = requests.get(big_picture_url, stream=True)
    if res.status_code == 200:
        with open(cover_filename, 'wb') as f:
            shutil.copyfileobj(res.raw, f)
    else:
        # big picture not found, try to download preview
        res = requests.get(cover_url, stream=True)
        if res.status_code == 200:
            with open(cover_filename, 'wb') as f:
                shutil.copyfileobj(res.raw, f)
    return cover_filename


def find_mp3_url(book_soup):
    url_mp3 = None
    logger.info('try to parse html')
    attr_name = 'src'
    for audio_tag in book_soup.findAll('audio'):
        if 'src' in audio_tag.attrs:
            url_mp3 = audio_tag.attrs[attr_name]
            logger.info('find mp3 url: {0}'.format(url_mp3))
            break
    return url_mp3


def get_book_requests(book_url: str) -> list:
    logger.info("Getting book requests. Please wait...")
    service = ChromeService(executable_path=ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.add_argument('headless')
    with webdriver.Chrome(service=service, options=options) as driver:
        driver.get(book_url)
        book_requests = driver.requests
        html = driver.page_source
        driver.close()
        return book_requests, html


def analyse_book_requests(book_requests: list) -> tuple:
    logger.info('Analysing book requests...')
    try:
        # find request with book json data
        book_json_requests = [r for r in book_requests if r.method == 'POST' and r.path.startswith('/ajax/b/')]
        # assert that we have only 1 request for book data found
        assert len(book_json_requests) == 1, 'Error: Book data not found. Exiting.'
        logger.info('Book data found')
        book_json = json.loads(brotli.decompress(book_json_requests[0].response.body))
        # find request with m3u8 file
        m3u8_file_requests = [r for r in book_requests if 'm3u8' in r.url]
        m3u8url = None
        if len(m3u8_file_requests) == 1:
            logger.info('m3u8 file found')
            m3u8url = m3u8_file_requests[0].url
        else:
            logger.info('m3u8 file NOT found')
        return book_json, m3u8url
    except AssertionError as message:
        logger.error(message)
        exit(1)


def cut_the_chapter(chapter, input_file, output_folder):
    output_file = output_folder / sanitize_filename('no_meta_{0}.mp3'.format(chapter['title']))
    logger.info('cut the chapter {0} from file {1} time from start {2} time finish {3}'.
                format(chapter['title'], input_file, str(chapter['time_from_start']), str(chapter['time_finish'])))
    command_cut = (ffmpeg_common_command() + ['-i', input_file, '-codec', 'copy',
                    '-ss', str(chapter['time_from_start']), '-to', str(chapter['time_finish']), output_file])
    subprocess.run(command_cut)
    return output_file


def create_mp3_with_metadata(chapter, no_meta_filename, book_folder, tmp_folder, book_json):
    cover_filename = get_cover_filename(tmp_folder)
    chapter_path = book_folder / sanitize_filename('{0}.mp3'.format(chapter['title']))
    logger.info('create mp3 with metadata: {0}'.format(chapter_path))
    command_metadata = ffmpeg_common_command() + ['-i', no_meta_filename]
    if Path(cover_filename).exists():
        command_metadata = command_metadata + ['-i', cover_filename, '-map', '0:0', '-map', '1:0']
    command_metadata = command_metadata + ['-codec', 'copy', '-id3v2_version', '3',
                                           '-metadata', 'title=' + chapter['title'],
                                           '-metadata', 'album=' + book_json['titleonly'],
                                           '-metadata', 'artist=' + book_json['author'],
                                           chapter_path]
    subprocess.run(command_metadata)
    os.remove(no_meta_filename) # remove no_meta file


def download_book_by_mp3_url(mp3_url, book_folder, tmp_folder, book_json):
    mp3_filename = mp3_url.split('/')[-1]
    # url_pattern_path = mp3_url.replace(mp3_filename, '')
    url_pattern_path = '{0}/'.format('/'.join(mp3_url.split('/')[0:-1]))
    url_pattern_filename = '.'+'.'.join(mp3_filename.split('.')[1:])
    count = 0
    chapters = json.loads(book_json['items'])
    for chapter in chapters:
        filename = None
        # download new file
        if count != chapter['file']:
            count = chapter['file']
            # calculate filename
            str_count = '{}'.format(count)
            if count < 10:
                str_count = '{:0>2}'.format(count)
            filename = tmp_folder / (str_count + url_pattern_filename)
            url_string = url_pattern_path+urllib.parse.quote(str_count+url_pattern_filename)
            logger.info('try to download file: '+url_string)
            res = requests.get(url_string, stream=True)
            if res.status_code == 200:
                with open(filename, 'wb') as f:
                    shutil.copyfileobj(res.raw, f)
                logger.info('file has been downloaded and saved as: {0}'.format(filename))
            else:
                logger.error('code: {0} while downloading: {url_string}'.format(res.status_code, url_string))
                exit(1)
        no_meta_filename = cut_the_chapter(chapter, filename, tmp_folder)
        create_mp3_with_metadata(chapter, no_meta_filename, book_folder, tmp_folder, book_json)


def download_book_by_m3u8(m3u8_url, book_folder, tmp_folder, book_json):
    full_book_filename = tmp_folder / 'full_book.mp3'
    ffmpeg_command = ffmpeg_common_command() + ['-i', m3u8_url, full_book_filename]
    subprocess.run(ffmpeg_command)
    # separate audio file into chapters
    for chapter in json.loads(book_json['items']):
        no_meta_filename = cut_the_chapter(chapter, full_book_filename, book_folder)
        create_mp3_with_metadata(chapter, no_meta_filename, book_folder, tmp_folder, book_json)


def create_work_dirs(output_folder, book_json, book_soup):
    # sanitize (make valid) book title
    book_json['title'] = sanitize_filename(book_json['title'])
    book_json['titleonly'] = sanitize_filename(book_json['titleonly'])
    book_json['author'] = sanitize_filename(book_json['author'])
    book_folder = Path(output_folder) / book_json['author'] / book_json['titleonly']

    bs_series = book_soup.findAll('div',{'class':'caption__article--about-block about--series'})
    if len(bs_series) == 1:
        series_name = bs_series[0].find('a').find('span').get_text().split('(')
        if len(series_name) == 2:
            book_json['series_name'] = sanitize_filename(series_name[0].strip(' '))
            book_json['series_number'] = series_name[1].split(')')[0].strip(' ')
            if len(book_json['series_name']) > 0:
                book_folder = Path(output_folder) / book_json['author'] / book_json['series_name'] / book_json['titleonly']
    # create new folder with book title
    Path(book_folder).mkdir(exist_ok=True, parents=True)
    # create tmp folder. It will be removed
    tmp_folder = book_folder / 'tmp'
    Path(tmp_folder).mkdir(exist_ok=True)

    return book_folder, tmp_folder


def download_book(book_url, output_folder):

    logger.info('start downloading book: {0}'.format(book_url))
    # create output folder
    Path(output_folder).mkdir(exist_ok=True)

    book_requests, book_html = get_book_requests(book_url)
    book_json, m3u8_url = analyse_book_requests(book_requests)
    book_soup = BeautifulSoup(book_html, 'html.parser')
    book_folder, tmp_folder = create_work_dirs(output_folder, book_json, book_soup)

    # download cover picture
    download_cover(book_json, tmp_folder)

    if m3u8_url is None: # playlist not found.
        # try to parse html
        mp3_url = find_mp3_url(book_soup)
        if mp3_url is None:
            logger.error('mp3 url not found')
            exit(1)
        else:
            download_book_by_mp3_url(mp3_url, book_folder, tmp_folder, book_json)
    else: # it's ordinary case
        download_book_by_m3u8(m3u8_url, book_folder, tmp_folder, book_json)

    logger.info('The book has been downloaded: {0}'.format(book_folder))
    # remove full book folder
    shutil.rmtree(tmp_folder, ignore_errors=True)
    return book_folder


def parse_series(series_url, output_folder):
    logger.info('the series has been discovered')
    res = requests.get(series_url)
    if res.status_code == 200:
        series_soup = BeautifulSoup(res.text, 'html.parser')
        bs_links_soup = (series_soup.find('div',{'class':'content__main__articles'}).
                findAll('a', {'class':'content__article-main-link tap-link'}))
        for bs_link_soup in bs_links_soup:
            download_book(bs_link_soup['href'], output_folder)
    else:
        logger.error('code: {0} while downloading: {url_string}'.format(res.status_code, series_url))

if __name__ == '__main__':
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
    )
    parser = argparse.ArgumentParser(description='Download a book from akniga.org')
    parser.add_argument('url', help='Book\'s url for downloading')
    parser.add_argument('output', help='Absolute or relative path where book will be downloaded')
    args = parser.parse_args()
    logger.info(args)

    if '/series/' in args.url:
        parse_series(args.url, args.output)
    else:
        download_book(args.url, args.output)
