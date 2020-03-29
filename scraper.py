import requests

from lxml import etree


BASE_URL = "https://animalcrossing.fandom.com/wiki/"
ENDPOINTS = {
    'fish': 'Fish_(New_Horizons)',
}
HEADER_XPATH = "//div[@title='Northern Hemisphere']/table[@class='roundy']//th"
TABLE_XPATH = "//div[@title='{hemisphere}']/table[@class='roundy']/tr/td/table"
HEMISPHERES = ["Northern Hemisphere", "Southern Hemisphere"]


def get_raw(resource):
    return requests.get(BASE_URL + ENDPOINTS[resource]).text


def parse(raw):
    return etree.HTML(raw)


def get_table(parsed, hemisphere=HEMISPHERES[0]):
    return parsed.xpath(TABLE_XPATH.format(hemisphere=hemisphere))[0]


def get_rows(table):
    return table.iterchildren(tag='tr')


def get_headers(parsed):
    return [col.text.strip().lower() for col in parsed.xpath(HEADER_XPATH)]


def save_image(img):
    url = img.get('src')
    name = img.get('data-image-key')
    r = requests.get(url, stream=True)
    if r.status_code == 200:
        with open(f'images/{name}', 'wb') as f:
            for chunk in r:
                f.write(chunk)
        return name
    raise ValueError("Could not process image %r" % img)


def get_fish():
    parsed = parse(get_raw('fish'))
    headers = get_headers(parsed)
    rows = get_rows(get_table(parsed))
    fishes = etree.Element("fishes")

    for row in rows:
        if row.find('th') is not None:
            # skip the header since we already parsed it
            continue
        fish = etree.Element("fish")
        for header, col in zip(headers, row):
            el = etree.Element(header.replace(' ', '_'))

            img = col.xpath('descendant::img[last()]')
            if img:
                name = save_image(img[0])
                el.text = name
            else:
                text = max(col.xpath("descendant::text()")).strip()
                if text == '✓':
                    text = 'true'
                elif text == '-':
                    text = 'false'
                el.text = text
            fish.append(el)
        fishes.append(fish)
    return fishes


if __name__ == '__main__':
    fishes = get_fish()
    with open("fishes.xml", "wb") as f:
        f.write(etree.tostring(fishes, pretty_print=True))
