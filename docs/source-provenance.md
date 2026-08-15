# Source Provenance v1 Specification

## Supported Source Types
The `SourceTypeEnum` taxonomy includes:
- `MUSEUM_OBJECT`
- `MUSEUM_CATALOG`
- `ACADEMIC_ARTICLE`
- `ACADEMIC_BOOK`
- `INSTITUTIONAL_PUBLICATION`
- `ARCHIVE_RECORD`
- `OTHER`

## Source Provenance Model
- `source_key`: Unique, human-readable slug (e.g. `met-object-123456`).
- `title`: Title of the object or publication.
- `citation_text`: Human-curated bibliographic citation text. Offline sources (books, archives) do not require a URL.
- `locator`: Page number, figure number, or catalog entry locator (e.g., `p. 117`, `fig. 24`).
- `rights_note`: Licensing or attribution rights notes.

## Provenance Invariants
1. `DOCUMENTED` claims require $\ge 1$ source link.
2. `CONTEXTUAL` claims require $\ge 1$ source link.
3. `CONTESTED` claims require $\ge 2$ distinct source links.
4. `UNKNOWN` claims allow $\ge 0$ source links documenting uncertainty.
5. No long copyrighted text copy is stored; citation, locator, and curator notes suffice.
