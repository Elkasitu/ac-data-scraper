from lxml import etree
from pathlib import Path

import json
import os
import requests


BASE_URL = "http://acnhapi.com/%s"
TRANSLATABLE = ["sp", "de", "fr", "it", "nl"]
TO_ISO = {'sp': 'es', 'de': 'de', 'fr': 'fr', 'it': 'it', 'nl': 'nl'}


def _get_data():
    return {
        'fish': requests.get(BASE_URL % "fish").json(),
        'bugs': requests.get(BASE_URL % "bugs").json(),
        'fossils': requests.get(BASE_URL % "fossils").json(),
    }


def _init_dirs():
    for lang in TRANSLATABLE:
        iso_lang = TO_ISO[lang]
        Path(f'values-{iso_lang.lower()}-r{iso_lang.upper()}').mkdir()


def search_api(current_resource, key, value, trees, res_name):
    for r in current_resource.values():
        if r['file-name'] == key or r['name']['name-en'].lower() == value:
            for k, v in trees.items():
                el = etree.Element('string')
                el.attrib['name'] = key
                el.text = r['name'][f'name-{k}'].replace('\'', '\\\'')
                v[res_name].append(el)
            return


def main():
    # NOTE: for now this only works for ACNH since it uses acnhapi.com in order to get translations
    _init_dirs()
    data = _get_data()
    trees = {lang: dict() for lang in TRANSLATABLE}

    for path in Path('values/').iterdir():
        res_name = path.stem.split('_')[0]
        if res_name in data:
            with path.open('r') as f:
                current_resource = data[res_name]
                base_tree = etree.fromstring(f.read())

                # initialize trees
                for item in trees.values():
                    item[res_name] = etree.Element('resources')

                # try to find the corresponding translation for each resource
                for node in base_tree:
                    key = node.attrib['name']
                    value = node.text.lower()
                    search_api(current_resource, key, value, trees, res_name)

    for lang, res in trees.items():
        iso_lang = TO_ISO[lang]
        p = Path(f'values-{iso_lang.lower()}-r{iso_lang.upper()}')
        for k, t in res.items():
            with p.joinpath(f'{k}_strings.xml').open('wb') as f:
                f.write(etree.tostring(t, pretty_print=True))


if __name__ == '__main__':
    main()