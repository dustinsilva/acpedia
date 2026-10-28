"""Narrow, repeatable compatibility edits for the archived ACPedia tables."""
import re
from functools import lru_cache

# Leave examples, comments, and literal code untouched.
PROTECTED = re.compile(r'<!--.*?-->|<(nowiki|pre|source|syntaxhighlight)\b[^>]*>.*?</\1\s*>', re.S | re.I)
COUNTER = re.compile(r'\{\{\s*AUTOINCREMENT\s*\}\}', re.I)
# Only #expr operands need raw category totals; retain display formatting elsewhere.
CATEGORY_OPERAND = re.compile(
    r'(\{\{\s*#expr\s*:\s*\{\{\s*PAGESINCATEGORY\s*:(?:\{\{[^{}]*\}\}|[^{}])*?)(\}\})', re.I)

@lru_cache(maxsize=4)
def image_pattern(names):
    return re.compile(r'(?<![\w.-])(?:' + '|'.join(
        re.escape(name.replace('_', ' ')).replace(r'\ ', '[ _]')
        for name in sorted(names, key=len, reverse=True)) + r')(?![\w.-])')

def repair_wikitext(text, image_replacements=None):
    """Return edited text and counts; a second pass is a no-op.

    Variables is already part of the pinned restoration runtime. Unlike replacing
    counts with constants, this keeps table totals correct when rows are edited.
    """
    counts = {'counter_calls': 0, 'raw_category_operands': 0, 'image_references': 0}
    counter_name = 'acpedia_archive_row'
    # Do not reuse a variable name already present in original content.
    while counter_name in text:
        counter_name += '_'

    def transform(chunk):
        def counter(match):
            counts['counter_calls'] += 1
            return '{{#vardefineecho:' + counter_name + '|{{#expr:{{#var:' + counter_name + '|0}}+1}}}}'
        chunk = COUNTER.sub(counter, chunk)
        def raw(match):
            if re.search(r'\|\s*R\s*$', match[1], re.I):
                return match[0]
            counts['raw_category_operands'] += 1
            return match[1] + '|R' + match[2]
        chunk = CATEGORY_OPERAND.sub(raw, chunk)
        if image_replacements:
            # Exact filename tokens, with equivalent wiki space/underscore syntax.
            pattern = image_pattern(tuple(image_replacements))
            chunk, count = pattern.subn(lambda m: image_replacements[m[0].replace('_', ' ')], chunk)
            counts['image_references'] += count
        return chunk

    parts = []; pos = 0
    for match in PROTECTED.finditer(text):
        parts += [transform(text[pos:match.start()]), match[0]]
        pos = match.end()
    parts.append(transform(text[pos:]))
    result = ''.join(parts)
    if counts['counter_calls']:
        result = '{{#vardefine:' + counter_name + '|0}}' + result
    return result, counts
