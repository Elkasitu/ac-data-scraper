import json
import requests

from lxml import etree
from pathlib import Path


BASE_URL = "https://animalcrossing.fandom.com/wiki/"
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
AVAILABILITY_TAG = "availability"
UID_TAG = "id"


def get_resources():
    with open("resources.json", "r") as f:
        return json.load(f)


def init_directories():
    Path('./images/').mkdir(exist_ok=True)
    Path('./data/').mkdir(exist_ok=True)


def get_table(parsed, table_xpath):
    return parsed.xpath(table_xpath)[0]


def get_rows(table):
    return table.iterchildren(tag='tr')


def get_full_size_src(img):
    i = img.find('revision') - 1
    return img[:i]


def save_image(img, image_path):
    url = get_full_size_src(img.get('src'))
    name = img.get('data-image-key').replace('-', '_').lower()
    r = requests.get(url, stream=True)
    if r.status_code == 200:
        with image_path.joinpath(name).open('wb') as f:
            for chunk in r:
                f.write(chunk)
        return name
    raise ValueError("Could not process image %r" % img)


def get_col_text(col):
    return max(col.xpath("descendant::text()")).strip()


def build_tree(resource, image_path):
    parsed = etree.HTML(requests.get(BASE_URL + resource['endpoint']).text)
    rows = get_rows(get_table(parsed, resource['table_xpath']))
    record_list = etree.Element("RecordList")
    uid_offset = resource['uid_offset']
    uid = 1

    headers = [col.text.strip().lower() for col in next(rows).iterchildren(tag='th')]
    for row in rows:
        record = etree.Element("Record")
        # Initialize availability tag before the loop as it will be updated when a month
        # column is encountered
        availability = etree.Element(AVAILABILITY_TAG)
        availability.text = '0' * 12

        # Update record id
        el = etree.Element(UID_TAG)
        el.text = f'{uid_offset + uid}'
        uid += 1
        record.append(el)

        for header, col in zip(headers, row):
            if header in MONTHS:
                text = get_col_text(col)
                if text == '✓':
                    text = '1'
                elif text == '-':
                    text = '0'
                index = MONTHS.index(header)
                availability.text = availability.text[:index] + text + availability.text[index + 1:]
            else:
                el = etree.Element(header.replace(' ', '_'))

                img = col.xpath('descendant::img[last()]')
                if img and header == 'image':
                    name = save_image(img[0], image_path)
                    el.text = name
                else:
                    text = get_col_text(col)
                    el.text = text
                record.append(el)
        record.append(availability)
        record_list.append(record)
    return record_list


def convert_to_resource(s):
    """Converts a string into a valid resource string, e.g. converts "as-d f(g)" into "as_d_fg"."""
    to_underscore = [' ', '-']
    to_remove = ['\'', '(', ')']
    for c in to_underscore:
        s = s.replace(c, '_')
    for c in to_remove:
        s = s.replace(c, '')
    return s


def names_to_resources(tree):
    """Converts the name and location fields so instead of <name>Some Fish</name> they become <name>some_fish</name>"""
    for name in tree.iter('name'):
        name.text = convert_to_resource(name.text)

    for location in tree.iter('location'):
        location.text = convert_to_resource(location.text)


def main():
    init_directories()
    resources = get_resources()
    for game in resources:
        game_resources = resources[game]
        image_path = Path(f'./images/{game}/')
        data_path = Path(f'./data/{game}/')
        image_path.mkdir()
        data_path.mkdir()

        for resource in game_resources:
            res = game_resources[resource]
            tree = build_tree(res, image_path)
            names_to_resources(tree)
            with data_path.joinpath(resource + '.xml').open('wb') as f:
                f.write(etree.tostring(tree, pretty_print=True))


if __name__ == '__main__':
    main()
