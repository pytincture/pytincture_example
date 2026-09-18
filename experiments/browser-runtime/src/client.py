"""Shared benchmark client. Identical logic under all three runtimes."""
from bridge import decode, encode, request, grid_create, grid_rows, value, set_value, ready, status

books = []
selected = None

async def main():
    global books
    raw = decode(await request('dataset', '{}'))
    books = decode(raw)
    grid_create(encode(books))
    ready(len(books))

async def on_filter(payload=''):
    needle = value('filter').lower()
    filtered = [book for book in books if needle in book['title'].lower()]
    grid_rows(encode(filtered))
    status('Showing ' + str(len(filtered)) + ' books')

async def on_select(payload):
    global selected
    selected = decode(payload)
    set_value('title', selected['title'])
    status('Selected ' + str(selected['id']))

async def on_save(payload=''):
    global selected, books
    if selected is None:
        return
    result = decode(await request('update_book', encode({
        'book_id': selected['id'], 'fields': {'title': value('title')}
    })))
    if not result['ok']:
        status('Save failed')
        return
    selected = result['record']
    books = [selected if book['id'] == selected['id'] else book for book in books]
    await on_filter()
    status('Saved ' + str(selected['id']))
