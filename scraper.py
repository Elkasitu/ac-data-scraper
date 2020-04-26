import collections
import functools
import itertools
import json
import re
import requests

from lxml import etree
from pathlib import Path


BASE_URL = "https://animalcrossing.fandom.com/wiki/"
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
AVAILABILITY_TAG = "availability"
UID_TAG = "id"
TRANSLATABLE_TAGS = {'specific': ['name'], 'generic': ['location']}
RESERVED_KEYWORDS = ["char"]


def get_resources():
    with open("resources.json", "r") as f:
        return json.load(f)


def init_directories():
    Path('./images/').mkdir(exist_ok=True)
    Path('./data/').mkdir(exist_ok=True)
    Path('./values/').mkdir(exist_ok=True)


def get_tables(parsed, table_xpath):
    return parsed.xpath(table_xpath)


def get_rows(tables):
    return itertools.chain(*[t.iterchildren(tag='tr') for t in tables])


def get_full_size_src(img):
    i = img.find('revision') - 1
    return img[:i]


def save_image(img, image_path):
    url = get_full_size_src(img.get('src'))
    name = sanitize(img.get('data-image-key'))
    request = requests.get(url, stream=True)
    if request.status_code == 200:
        try:
            with image_path.joinpath(name).open('wb') as f:
                for chunk in request:
                    f.write(chunk)
            return name
        except Exception:
            import pdb; pdb.set_trace()
            pass
    raise ValueError("Could not process image %r (rate-limited?)" % img)


def get_col_text(col):
    return max(col.xpath("descendant::text()")).strip()


def build_tree(resource, image_path):
    parsed = etree.HTML(requests.get(BASE_URL + resource['endpoint']).text)
    rows = get_rows(get_tables(parsed, resource['table_xpath']))
    record_list = etree.Element("RecordList")
    uid_offset = resource['uid_offset']
    uid = 1

    headers = [col.text.strip().lower() for col in next(rows).iterchildren(tag='th')]
    for row in rows:
        if row.find('th') is not None:
            # there may be table heads interspersed between actual content, we don't
            # care about this stuff normally
            continue
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
                el = etree.Element(sanitize(header))

                img = col.xpath('descendant::img[last()]')
                if img and header == 'image':
                    name = save_image(img[0], image_path)
                    el.text = name
                elif header == 'price':
                    text = get_col_text(col)
                    if not text.isdigit():
                        text = text.split()[0]
                        text = text.replace(',', '')
                    el.text = text
                else:
                    text = get_col_text(col)
                    el.text = text
                record.append(el)
        if availability.text != ('0' * 12):
            record.append(availability)
        record_list.append(record)
    return record_list


def sanitize(s):
    """ Converts non-alphanumeric characters to _ """
    res = re.sub(r'\W(?!(png|jpg))', '_', s).lower()
    if res in RESERVED_KEYWORDS:
        res = f'_{res}'
    return res


def term_to_xml(term, value):
    node = etree.Element('string')
    node.attrib['name'] = term
    node.text = value.replace('\'', '\\\'')
    return node


def extract_terms(source, target, _type):
    """
    Extract translatable terms from source tree, puts them into target tree if they're not in
    done_terms
    """
    existing_terms = {e.attrib['name'] for e in target}
    for term in itertools.chain(*[source.iter(tag) for tag in TRANSLATABLE_TAGS[_type]]):
        sanitized = sanitize(term.text)
        if sanitized and sanitized not in existing_terms:
            target.append(term_to_xml(sanitized, term.text))
            existing_terms.add(sanitized)
        term.text = sanitized


def main():
    init_directories()
    resources = get_resources()
    resource_factory = functools.partial(etree.Element, 'resources')
    l18n_dict = collections.defaultdict(resource_factory)
    generic_l18n = etree.Element('resources')

    for game in resources:
        game_resources = resources[game]
        image_path = Path(f'./images/{game}/')
        data_path = Path(f'./data/{game}/')
        image_path.mkdir()
        data_path.mkdir()

        for resource in game_resources:
            res = game_resources[resource]
            tree = build_tree(res, image_path)
            t_res = resource
            if resource.endswith(("_nh", "_sh")):
                t_res = resource.split('_')[0]
            extract_terms(tree, l18n_dict[t_res], 'specific')
            extract_terms(tree, generic_l18n, 'generic')
            with data_path.joinpath(resource + '.xml').open('wb') as f:
                f.write(etree.tostring(tree, pretty_print=True))

    for k, v in l18n_dict.items():
        with Path(f'./values/{k}_strings.xml').open('wb') as f:
            f.write(etree.tostring(v, pretty_print=True))

    with Path("./values/strings.xml").open('wb') as f:
        f.write(etree.tostring(generic_l18n, pretty_print=True))


if __name__ == '__main__':
    main()
