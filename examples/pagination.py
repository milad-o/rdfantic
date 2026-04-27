"""Pagination — use Page[Model] and paginate() to slice through graph results."""

from rdflib import RDF, XSD, Graph, Literal, Namespace

from rdfantic import GraphModel, paginate, predicate

SCHEMA = Namespace("http://schema.org/")
EX = Namespace("http://example.org/")


class BookView(GraphModel):
    rdf_type = SCHEMA["Book"]
    name: str = predicate(SCHEMA["name"])
    author: str | None = predicate(SCHEMA["author"])


# -- Build a graph with 15 books --------------------------------------

g = Graph()
for i in range(15):
    subj = EX[f"book{i:02d}"]
    g.add((subj, RDF.type, SCHEMA["Book"]))
    g.add((subj, SCHEMA["name"], Literal(f"Book {i}", datatype=XSD.string)))
    g.add((subj, SCHEMA["author"], Literal(f"Author {i % 5}", datatype=XSD.string)))

# -- Paginate through all books ----------------------------------------

page_size = 5
offset = 0

while True:
    page = paginate(BookView, g, offset=offset, limit=page_size)
    page_num = offset // page_size + 1
    print(f"Page {page_num} (offset={page.offset}, total={page.total}):")

    for book in page.items:
        print(f"  {book.name} by {book.author}")

    offset += page_size
    if offset >= page.total:
        break
    print()

# -- Page serializes cleanly for JSON responses ------------------------

first_page = paginate(BookView, g, offset=0, limit=3)
data = first_page.model_dump()
print(f"\nSerialized page keys: {list(data.keys())}")
print(f"Items in first page: {len(data['items'])}")
print(f"Total: {data['total']}")
