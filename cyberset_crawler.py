import random
import time
import re
import os
import shutil
import pandas
import mechanicalsoup

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:93.0) Gecko/20100101 Firefox/93.0'
SLEEP_INTERVAL = (100, 500)
BROWSER = mechanicalsoup.StatefulBrowser(user_agent=USER_AGENT)
CHECKPOINT_FILE = './checkpoint.txt'

def get_page(address, verbose=True):
    time.sleep(random.randint(SLEEP_INTERVAL[0], SLEEP_INTERVAL[1]) * 0.001)
    page = BROWSER.get(address)
    url = page.url
    status = '{} {}'.format(page.status_code, page.reason)
    soup = page.soup
    if verbose:
        print('GET {} {}'.format(url, status))
    return soup

def get_image(address, verbose=True):
    time.sleep(random.randint(SLEEP_INTERVAL[0], SLEEP_INTERVAL[1]) * 0.001)
    image = BROWSER.open(address)
    url = image.url
    status = '{} {}'.format(image.status_code, image.reason)
    content = image.content
    if verbose:
        print('GET {} {}'.format(url, status))
    return content

def remove_duplicates_document(file_in, file_out, verbose=True):
    with open(file_in, 'r') as f:
        total = f.read().splitlines()
    reduced = list(set(total))
    random.shuffle(reduced)
    with open(file_out, 'w') as f:
        for l in reduced:
            f.write('{}\n'.format(l))
    if verbose:
        print('REDUCTION {} {} -> {} {}'.format(file_in, len(total), file_out, len(reduced)))

def remove_duplicates_folder(directory_in, directory_out, verbose=True):
    books = os.listdir(directory_in)
    cards = list()
    for b in books:
        with open('{}/{}/card.txt'.format(directory_in, b), 'r') as f:
            lines = f.read().splitlines()
        card = (lines[0], lines[1], lines[2])
        cards.append(card)
    df = pandas.DataFrame(cards, columns=('title', 'author', 'code'))
    classes = df.groupby(['title','author'])['code'].apply(list).reset_index().values.tolist()
    for c in classes:
        name = '-'.join(c[2])
        os.makedirs('{}/{}'.format(directory_out, name))
        for n in c[2]:
            cover = [x for x in os.listdir('{}/{}'.format(directory_in, n)) if 'cover' in x][0] if len([x for x in os.listdir('{}/{}'.format(directory_in, n)) if 'cover' in x]) > 0 else None
            if cover != None:
                shutil.copyfile('{}/{}/{}'.format(directory_in, n, cover), '{}/{}/{}'.format(directory_out, name, 'cover{}.{}'.format(n[4:], cover.split('.')[-1])))
        with open('{}/{}/card.txt'.format(directory_out, name), 'w') as f:
            f.write('{}\n'.format(c[0]))
            f.write('{}\n'.format(c[1]))
            for n in c[2]:
                f.write('{}\n'.format(n))
    if verbose:
        print('REDUCTION {} {} -> {} {}'.format(directory_in, len(books), directory_out, len(classes)))

def clean_record(string):
    string = string.replace('\'', ' ')
    string = string.replace('-', ' ')
    string = string.replace('/', ' ')
    string = string.replace('\r', ' ')
    string = string.replace('\n', ' ')
    string = string.replace('\t', ' ')
    string = re.sub('\\(.*?\\)', '', string)
    string = re.sub('[^a-zA-Z0-9àèéìòùÀÈÉÌÒÙ ]', '', string)
    string = re.sub(' +', ' ', string)
    string = string.lower().strip()
    return string

def remove_prefix(string, prefix):
    return string[len(prefix):] if string.startswith(prefix) else string

def random_character(*bounds):
    pool = [chr(x) for couple in bounds for x in list(range(ord(couple[0]), ord(couple[1])+1))]
    return random.sample(pool, 1)[0]

def shop_eb(keywords, path):
    search = keywords.strip().lower()
    url = 'http://www.ebay.it/sch/i.html?_nkw={}'.format(search.replace(' ', '+'))
    soup = get_page(url)
    count = int(soup.select('.srp-controls__count-heading')[0].get_text().split(' ')[0].replace('.', ''))
    pictures = [x['src'] for x in soup.select('.srp-results')[0].find_all('img') if x.has_attr('src') and x['src'].split('/')[-2] != 'pics'][0:count]
    if not os.path.exists(path):
        os.makedirs(path)
    for p in pictures:
        name = p.split('/')[-2]
        extension = p.split('.')[-1]
        with open('{}/{}.{}'.format(path, name, extension), 'wb') as f:
            f.write(get_image(p))

def shop_cvl(title, author, directory):
    search_title = title.strip().lower().replace(' ', '%20')
    search_author = author.strip().lower().replace(' ', '%20')
    page = 1
    if not os.path.exists(directory):
        os.makedirs(directory)
    while True:
        url = 'http://www.comprovendolibri.it/cercatitolo200.asp?Xpagina={}&cercatitolo={}&cercaautore={}'.format(page, search_title, search_author)
        soup = get_page(url)
        all_pictures = [x['src'] for x in soup.select('.copertinaOrdini120')]
        pictures = [x for x in all_pictures if x.split('/')[-1] != 'noImg140.jpg' and x.split('/')[-2] != 'books.google.com']
        if len(all_pictures) == 0:
            break
        for p in pictures:
            name = p.split('/')[-1]
            with open('{}/{}'.format(directory, name), 'wb') as f:
                f.write(get_image(p))
        page += 1

def call_catalog_scraper(name, addresses_list, document_name, folder_name, scraper):
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'r') as c:
            lines = c.read().splitlines()
        if len(lines) > 0 and len(lines[0].split(' ')) >= 2 and lines[0].split(' ')[0] == name:
            checkpoint = int(lines[0].split(' ')[1]) + 1
        else:
            checkpoint = 0
    else:
        checkpoint = 0
    access = 'w' if checkpoint == 0 else 'a'
    with open(document_name, access) as d:
        for i in range(checkpoint, len(addresses_list)):
            a = addresses_list[i]
            print('SCRAPING {} {}/{}'.format(name, i+1, len(addresses_list)))
            try:
                scraper(a, d, folder_name)
            except Exception as e:
                print(e)
            d.flush()
            with open(CHECKPOINT_FILE, 'w') as c:
                c.write('{} {} ({}/{})\n'.format(name, i, i+1, len(addresses_list)))
    with open(CHECKPOINT_FILE, 'w') as c:
        c.write('\n')

def call_next_page(soup, function, document, folder):
    following = 'https://www.fantascienza.com{}'.format(soup.select('.next')[0]['href']) if len(soup.select('.next')) != 0 else None
    if following != None:
        function(following, document, folder)

def scrape_letter(address, document, folder):
    soup = get_page(address)
    authors = soup.select('.elenco-autori')
    links = ['https:{}'.format(x['href']) for inner in authors for x in inner.find_all('a')]
    for l in links:
        if l != None:
            document.write('{}\n'.format(l))
    call_next_page(soup, scrape_letter, document, folder)

def scrape_author(address, document, folder):
    soup = get_page(address)
    works = soup.select('#elenco-opere')[0].find_all('h4') if len(soup.select('#elenco-opere')) > 0 else []
    links = ['https:{}'.format(x['href']) for inner in works for x in inner.find_all('a')]
    for l in links:
        if l != None:
            document.write('{}\n'.format(l))
    call_next_page(soup, scrape_author, document, folder)

def scrape_work(address, document, folder):
    soup = get_page(address)
    volumes = soup.select('.lista-edizioni')[0].find_all('h3')
    links = ['https:{}'.format(x['href']) for inner in volumes for x in inner.find_all('a')]
    for l in links:
        if l != None:
            document.write('{}\n'.format(l))
    call_next_page(soup, scrape_work, document, folder)

def scrape_volume(address, document, folder):
    soup = get_page(address)
    title = clean_record(soup.find_all('h1')[0].get_text())
    author = remove_prefix(clean_record(soup.select('.volume-autori')[0].get_text()), 'di ')
    cover = 'https:{}'.format(soup.select('.copertina')[0]['src']) if 'https:{}'.format(soup.select('.copertina')[0]['src']).split('/')[-1] != 'nocover.png' else None
    nilf = ['https:{}'.format(x['href']).split('/')[5] for x in soup.find_all('a') if x.get_text() == 'Permalink'][0]
    path = '{}/{}'.format(folder, nilf)
    if not os.path.exists(path):
        os.makedirs(path)
        with open('{}/card.txt'.format(path), 'w') as f:
            f.write('{}\n'.format(title))
            f.write('{}\n'.format(author))
            f.write('{}\n'.format(nilf))
        if cover != None:
            extension = cover.split('.')[-1]
            with open('{}/cover.{}'.format(path, extension), 'wb') as f:
                f.write(get_image(cover))
    call_next_page(soup, scrape_volume, document, folder)

def scrape_shopping(address, document, folder):
    with open('{}/card.txt'.format(address), 'r') as f:
        lines = f.read().splitlines()
    keywords = '{} {}'.format(lines[0], lines[1])
    shop_eb(keywords, address)

def manual_shop_again(start_from, less_than, directory_name):
    books = os.listdir(directory_name)
    for i, b in enumerate(books):
        if i >= start_from - 1:
            pictures = [x for x in os.listdir('{}/{}'.format(directory_name, b)) if x != 'card.txt']
            if len(pictures) < less_than:
                with open('{}/{}/card.txt'.format(directory_name, b), 'r') as f:
                    lines = f.read().splitlines()
                print('{}. {} {} by {} has {} pictures'.format(i+1, b, lines[0], lines[1], len(pictures)))
                new_k = input('search eb keywords -> ')
                if new_k != '':
                    shop_eb(new_k, '{}/{}'.format(directory_name, b))
                new_t = input('search cvl title -> ')
                new_a = input('search cvl author -> ')
                if new_t != '' or new_a != '':
                    shop_cvl(new_t, new_a, '{}/{}'.format(directory_name, b))

def list_by_author(directory_name):
    books = os.listdir(directory_name)
    collection = list()
    for b in books:
        pictures = [x for x in os.listdir('{}/{}'.format(directory_name, b)) if x != 'card.txt']
        with open('{}/{}/card.txt'.format(directory_name, b), 'r') as f:
            lines = f.read().splitlines()
        collection.append('{} ~ {} ~ {} ~ {}'.format(lines[1], lines[0], b, len(pictures)))
    for c in sorted(collection):
        print(c)

def list_pictures_count(less_than, more_than, directory_name):
    books = os.listdir(directory_name)
    collection = list()
    for b in books:
        pictures = [x for x in os.listdir('{}/{}'.format(directory_name, b)) if x != 'card.txt']
        if len(pictures) < less_than or len(pictures) > more_than:
            with open('{}/{}/card.txt'.format(directory_name, b), 'r') as f:
                lines = f.read().splitlines()
            collection.append('{} ~ {} ~ {} ~ {}'.format(len(pictures), b, lines[0], lines[1]))
    for c in sorted(collection):
        print(c)

def find_weird_records(folder_name, already_clean=False):
    books = os.listdir(folder_name)
    for directory_name in books:
        if len(directory_name) != 10 or not 'NILF' in directory_name:
            print('DIRECTORY ALERT', directory_name)
        samples = os.listdir('{}/{}'.format(folder_name, directory_name))
        for file_name in samples:
            if len(file_name.split('.')) < 2 or (file_name.split('.')[-1].lower() != 'jpg' and file_name != 'card.txt'):
                print('EXTENSION ALERT', '{}/{}'.format(directory_name, file_name))
            if 'cover' in file_name:
                cover_name = file_name
        if not already_clean and cover_name.split('.')[-2][5:] != directory_name[4:]:
            print('COVER ALERT', directory_name)
        if already_clean and cover_name != 'cover.jpg':
            print('COVER ALERT', directory_name)
        with open('{}/{}/card.txt'.format(folder_name, directory_name), 'r') as f:
            lines = f.read().splitlines()
        if len(lines) != 3:
            print('CARD LINES ALERT', directory_name)
        if lines[2] != directory_name:
            print('CARD CODE ALERT', directory_name)

def final_cleaning(source_directory, target_directory):
    directories = os.listdir(source_directory)
    for d in directories:
        destination = '{}/{}'.format(target_directory, d)
        os.makedirs(destination)
        origin = '{}/{}'.format(source_directory, d)
        files = os.listdir(origin)
        for f in files:
            if f == 'card.txt':
                with open('{}/{}'.format(origin, f), 'r') as c:
                    lines = c.read().splitlines()
                old_title = lines[0]
                old_author = lines[1]
                code = lines[2]
                soup = get_page('http://nilf.it/{}'.format(code[4:]))
                original_title = clean_record(soup.find_all('h1')[0].get_text())
                original_author = remove_prefix(clean_record(soup.select('.volume-autori')[0].get_text()), 'di ')
                if old_title.lower() != original_title:
                    print('WARNING found title "{}" instead of "{}"'.format(original_title, old_title))
                    input('->')
                if old_author.lower() != original_author:
                    print('WARNING found author "{}" instead of "{}"'.format(original_author, old_author))
                    input('->')
                with open('{}/{}'.format(destination, f), 'w') as c:
                    c.write('{}\n'.format(original_title))
                    c.write('{}\n'.format(original_author))
                    c.write('{}\n'.format(code))
            elif f[0:5] == 'cover':
                name = 'cover.jpg'
                shutil.copyfile('{}/{}'.format(origin, f), '{}/{}'.format(destination, name))
            else:
                name = random_character(('d','z')) + ''.join(random_character(('a','z'), ('A','Z'), ('0','9')) for i in range(5)) + '.jpg'
                shutil.copyfile('{}/{}'.format(origin, f), '{}/{}'.format(destination, name))
    s_count = 0
    for s in os.listdir(source_directory):
        for f in os.listdir('{}/{}'.format(source_directory, s)):
            if f != 'card.txt' and f[0:5] != 'cover':
                s_count += 1
    t_count = 0
    t_samples = set()
    for t in os.listdir(target_directory):
        for f in os.listdir('{}/{}'.format(target_directory, t)):
            if f != 'card.txt' and f[0:5] != 'cover':
                t_count += 1
                t_samples.add(f)
    print('SAMPLES IN SOURCE: {}'.format(s_count))
    print('SAMPLES IN DESTINATION: {}'.format(t_count))
    print('UNIQUE NAMES IN DESTINATION: {}'.format(len(t_samples)))

# letters = [chr(x) for x in range(ord('A'), ord('Z')+1)]
# letters = ['Q', 'U', 'X']
# random.shuffle(letters)
# call_catalog_scraper('LETTER', ['https://www.fantascienza.com/catalogo/autori/{}/'.format(l) for l in letters], './1_raw_authors.txt', None, scrape_letter)
# remove_duplicates_document('./1_raw_authors.txt', './2_clean_authors.txt')
# input('SCRAPE LETTERS DONE -> ')

# with open('./2_clean_authors.txt', 'r') as f:
#    authors = f.read().splitlines()
# authors = ['https://www.fantascienza.com/catalogo/autori/NILF10014/douglas-adams/']
# call_catalog_scraper('AUTHOR', authors, './3_raw_works.txt', None, scrape_author)
# remove_duplicates_document('./3_raw_works.txt', './4_clean_works.txt')
# input('SCRAPE AUTHORS DONE -> ')

# with open('./4_clean_works.txt', 'r') as f:
#     works = f.read().splitlines()
# call_catalog_scraper('WORK', works, './5_raw_volumes.txt', None, scrape_work)
# remove_duplicates_document('./5_raw_volumes.txt', './6_clean_volumes.txt')
# input('SCRAPE WORKS DONE -> ')

# with open('./6_clean_volumes.txt', 'r') as f:
#     volumes = f.read().splitlines()
# call_catalog_scraper('VOLUME', volumes, './dummy.txt', './7_raw_books', scrape_volume)
# remove_duplicates_folder('7_raw_books', '8_clean_books')
# input('SCRAPE VOLUMES DONE -> ')

# books = ['{}/{}'.format('./8_clean_books', x) for x in os.listdir('./8_clean_books')]
# call_catalog_scraper('SHOPPING', books, './dummy.txt', None, scrape_shopping)
# manual_shop_again(1, 4, './8_clean_books')
# input('SCRAPE SHOPPING DONE -> ')

# list_by_author('./8_clean_books')
# list_pictures_count(4, 20, './8_clean_books')
# find_weird_records('./8_clean_books')

# title = 'innsmouth'
# author = 'lovecraft'
# folder = './sink'
# shop_eb('{} {}'.format(title, author), folder)
# shop_cvl(title, author, folder)

# final_cleaning('./8_clean_books', './9_final_books')

print('DONE')
