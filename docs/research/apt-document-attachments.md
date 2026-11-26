# What distinguishes the official act document from its attachments in the APT register?

Research answer for issue 16, child of issue 14. Primary sources only: official OpenAPI document and live public API responses, read on 2026-11-26.

## Answer

The register models one act with two PDF renditions, discovered through `GET /api/pap/files/{objectId}`:

1. `documentoUnico` has `tipoFile: "UNICO"`. It is exactly one server-generated consultation copy of the whole act, titled with the PAP protocol number, with URL `.../download/unico/{siteId}/{objectId}`.
2. `files[]` entries have `tipoFile: "ALLEGATO"`. They are the originally uploaded files, titled with the original filename, with URL `.../download/single/{siteId}/{objectId}/{hash}/{filename}`.

The public portal labels the first group as "Documenti in consultazione" and the second as "Allegati originali". The repository's `document_url` maps to the consultation copy; `attachment_urls` map to the original uploaded files.

A missing official document is possible and is the normal state outside the publication window. In a probe of 370 records with natura `200152`, all 14 currently published acts had one UNICO and one ALLEGATO, while 356 expired or annulled acts returned `documentoUnico: null` and `files: []`. The download URL of an expired act can answer HTTP 200 with an HTML refusal body, so status code alone is not enough: verify `Content-Type` and `%PDF-` magic bytes.

## Evidence

- The discovery endpoint `POST /api/pap/filter` carries no document fields. Document classification requires one additional `GET /api/pap/files/{objectId}` per act.
- The files endpoint exposes `results[0].documentoUnico` and `results[0].files`. The OpenAPI response type is untyped `KapiApiResponse<object>`; `tipoFile` is an empirical convention, not a documented schema field.
- For act 791962, `documentoUnico.tipoFile` was `UNICO`, `mimeType` was `application/pdf`, and the URL was `.../download/unico/6500/791962`. Its `files[0].tipoFile` was `ALLEGATO`, with a server-assigned hash and original filename in the URL.
- Both renditions were 9-page PDFs; the UNICO was slightly larger and its served filename contained `documento-di-consultazione-con-filigrana`.
- The rendered portal detail page showed the same split under "Documenti in consultazione" and "Allegati originali".
- Absence of a document is indistinguishable from an unknown id: both return HTTP 200 with the same empty shape.

## Relevance to the backfill

The archived part of the register generally returns no PDF documents through the files endpoint. The backfill can still publish act metadata and official detail links, but it must handle acts with no retrievable PDF without treating the empty response as an API error.

## Not verified

- Whether an act can carry two or more ALLEGATO PDFs was not observed.
- Non-PDF attachments were not observed.
- Whether documents are deleted or merely withheld after expiry is not stated by the API or portal.
- The corpus probe covered 370 of 739 records plus a 40-record spread sample; it was not a full census.
- The plain detail URL in the repository default omits the working `/dettaglio-pap` suffix. This is an observation only; no code was changed.

## Sources

- https://siopi.publisys.it/kapi-aptbasilicata/v3/api-docs
- Live `POST https://siopi.publisys.it/kapi-aptbasilicata/api/pap/filter`
- Live `GET https://siopi.publisys.it/kapi-aptbasilicata/api/pap/files/{objectId}`
- Live PDF endpoints under `https://siopi.publisys.it/katti-aptbasilicata/public/pap/edoc/download/`
- Rendered portal pages under `https://siopi.publisys.it/sito-aptbasilicata/albo-pretorio/`
