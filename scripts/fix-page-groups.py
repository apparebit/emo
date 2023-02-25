# (C) 2023 by Robert Grimm. Released under Apache-2.0 license.

import json
from pathlib import Path
import subprocess
import sys
import tempfile

def degroup(document):
    """
    If the document contains a single page and that page is associated with a
    so-called "page group object", remove that object from the document. Unlike
    solutions suggested on Stack Overflow, this function does *not* other
    objects of the same name appearing elsewhere in the PDF object graph.
    """
    objects = document['qpdf'][1]

    def resolve(ref):
        key = ref if ref == 'trailer' else f'obj:{ref}'
        if key not in objects:
            raise KeyError(f'{ref} cannot be resolved')
        return objects[key]

    def resolve_value(ref, typ=None):
        o = resolve(ref)
        if 'value' not in o:
            raise ValueError(f'{ref} does not reference object')
        v = o['value']
        if typ is not None and v['/Type'] != typ:
            raise ValueError(f'{ref} points to object of type {v["/Type"]} not {typ}')
        return v

    trailer = resolve_value('trailer')
    root = resolve_value(trailer['/Root'], '/Catalog')
    pages = resolve_value(root['/Pages'], '/Pages')['/Kids']
    page_count = len(pages)
    if page_count > 1:
        raise ValueError(f'PDF has {page_count} pages instead of just one')

    page = resolve_value(pages[0], '/Page')
    if not '/Group' in page:
        return False

    del page['/Group']
    return True


def rewrite(input, intermediate, output):
    """
    Convert the PDF file with path `input` into the an equivalent JSON file with
    path `intermediate`, remove the page group object, and then convert the
    updated JSON file back into a PDF with path `output`.
    """
    subprocess.run(
        ['qpdf', input, '--json-output', intermediate],
        stdout=sys.stdout,
        stderr=sys.stderr,
        check=True,
    )

    with open(intermediate, mode='r', encoding='utf8') as file:
        document = json.load(file)
    if not isinstance(document, dict):
        raise ValueError(f'{document} is a {type(document)} not dict')
    changed = degroup(document)
    if not changed:
        print(f'{input}: nothing to do')
        return
    with open(intermediate, mode='w', encoding='utf8') as file:
        json.dump(document, file)

    subprocess.run(
        ['qpdf', intermediate, '--json-input', output],
        stdout=sys.stdout,
        stderr=sys.stderr,
        check=True,
    )
    print(f'{input} -> {output}')


def main(argv):
    """Fix the PDF files specified as command line arguments."""

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        for arg in argv:
            input = Path(arg)
            if input.suffix != '.pdf':
                continue

            intermediate = tmpdir / f'{input.stem}.tmp.json'
            output = input.with_stem(f'{input.stem}.new')

            try:
                rewrite(input, intermediate, output)
            except Exception as ex:
                print(f'error:{input}: {ex.args[0]}')


if __name__== '__main__':
    main(sys.argv[1:])
