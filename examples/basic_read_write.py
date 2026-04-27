"""Basic read/write — define a model, build a graph, read it back, write it out."""

from rdflib import RDF, XSD, Graph, Literal, Namespace

from rdfantic import GraphModel, predicate

# -- Namespaces --------------------------------------------------------

SCHEMA = Namespace("http://schema.org/")
EX = Namespace("http://example.org/")

# -- Models ------------------------------------------------------------


class PersonView(GraphModel):
    rdf_type = SCHEMA["Person"]
    name: str = predicate(SCHEMA["name"])
    email: str | None = predicate(SCHEMA["email"])


class MovieView(GraphModel):
    rdf_type = SCHEMA["Movie"]
    name: str = predicate(SCHEMA["name"])
    director: PersonView = predicate(SCHEMA["director"])
    genres: set[str] = predicate(SCHEMA["genre"])
    year: int | None = predicate(SCHEMA["year"])


# -- Build a small graph -----------------------------------------------

g = Graph()
g.bind("schema", SCHEMA)
g.bind("ex", EX)

# A person
g.add((EX["nolan"], RDF.type, SCHEMA["Person"]))
g.add((EX["nolan"], SCHEMA["name"], Literal("Christopher Nolan", datatype=XSD.string)))
g.add((EX["nolan"], SCHEMA["email"], Literal("nolan@example.org", datatype=XSD.string)))

# A movie
g.add((EX["inception"], RDF.type, SCHEMA["Movie"]))
g.add((EX["inception"], SCHEMA["name"], Literal("Inception", datatype=XSD.string)))
g.add((EX["inception"], SCHEMA["director"], EX["nolan"]))
g.add((EX["inception"], SCHEMA["genre"], Literal("Sci-Fi", datatype=XSD.string)))
g.add((EX["inception"], SCHEMA["genre"], Literal("Thriller", datatype=XSD.string)))
g.add((EX["inception"], SCHEMA["year"], Literal(2010, datatype=XSD.integer)))

# -- Read from graph ---------------------------------------------------

movie = MovieView.from_graph(g, EX["inception"])

print(f"Title:    {movie.name}")
print(f"Year:     {movie.year}")
print(f"Genres:   {sorted(movie.genres)}")
print(f"Director: {movie.director.name}")
print(f"Email:    {movie.director.email}")
print(f"Subject:  {movie.subject}")
print()

# -- Write to a new graph ---------------------------------------------

g2 = Graph()
movie.to_graph(g2, subject=EX["inception"])

print(f"Triples written: {len(g2)}")
print()
for s, p, o in sorted(g2):
    print(f"  {s} {p} {o}")

# -- Round-trip check --------------------------------------------------

movie2 = MovieView.from_graph(g2, EX["inception"])
assert movie2.name == movie.name
assert movie2.year == movie.year
assert movie2.genres == movie.genres
assert movie2.director.name == movie.director.name
print("\nRound-trip OK!")
