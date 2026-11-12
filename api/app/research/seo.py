"""The same description projection as web/utils/blog.ts, not the article lead."""
import re


def description(text, maximum=155):
    clean = re.sub(r'[\s\ufeff]+', ' ', text).strip()
    # JavaScript slices UTF-16 code units, including when an emoji is present.
    units = clean.encode('utf-16-le')
    if len(units) // 2 <= maximum:
        return clean
    cut = units[:(maximum - 1) * 2].decode('utf-16-le', errors='surrogatepass')
    end = max(cut.rfind(' '), 80)
    return re.sub(r'[\s,;:.\-]+$', '', cut[:end]) + '…'
