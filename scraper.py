import json
import requests

from lxml import etree
from pathlib import Path


BASE_URL = "https://animalcrossing.fandom.com/wiki/"


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


def save_image(img, image_path):
    url = img.get('src')
    name = img.get('data-image-key')
    r = requests.get(url, stream=True)
    if r.status_code == 200:
        with image_path.joinpath(name).open('wb') as f:
            for chunk in r:
                f.write(chunk)
        return name
    raise ValueError("Could not process image %r" % img)


def build_tree(resource, image_path):
    parsed = etree.HTML(requests.get(BASE_URL + resource['endpoint']).text)
    rows = get_rows(get_table(parsed, resource['table_xpath']))
    record_list = etree.Element("RecordList")

    headers = [col.text.strip().lower() for col in next(rows).iterchildren(tag='th')]
    for row in rows:
        record = etree.Element("Record")
        for header, col in zip(headers, row):
            el = etree.Element(header.replace(' ', '_'))

            img = col.xpath('descendant::img[last()]')
            if img and header == 'image':
                name = save_image(img[0], image_path)
                el.text = name
            else:
                text = max(col.xpath("descendant::text()")).strip()
                if text == '✓':
                    text = 'true'
                elif text == '-':
                    text = 'false'
                el.text = text
            record.append(el)
        record_list.append(record)
    return record_list


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
            with data_path.joinpath(resource + '.xml').open('wb') as f:
                f.write(etree.tostring(tree, pretty_print=True))


if __name__ == '__main__':
    main()
