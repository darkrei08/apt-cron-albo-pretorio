# APT Basilicata Public Notices

This context publishes public metadata from the APT Basilicata public notices register to a Telegram channel and a generated public index.

## Language

**Source register**:
The official APT Basilicata register that supplies public notice metadata and official PDF links.
_Avoid_: API, endpoint, feed

**Public notice**:
A public act listed in the Source register and identified by its official number, year, category, sector, publication dates, status and official detail link.
_Avoid_: atto, act, record, item

**Notice identity**:
The stable key that keeps one Public notice distinct across runs, using its official id or an official link when the id is absent.
_Avoid_: row, key, document id

**Notice fingerprint**:
The value that represents the current public metadata of a Public notice and determines whether it is new, changed or unchanged.
_Avoid_: hash, checksum, revision

**Notice state**:
The durable record of Notice fingerprints, cached PDF links and PDF links already delivered. It is the only memory of past publications.
_Avoid_: cache, database, log

**PDF link**:
An official source URL for a PDF that belongs to a Public notice. The project publishes the URL and does not keep the PDF file.
_Avoid_: attachment, document blob, file

**Generated index**:
The derived publication of the current Public notices from allowed public fields. It is regenerated from the Source register and reviewed by the Operator before publication.
_Avoid_: archive, feed, catalogue

**Publication surface**:
A destination where Public notice metadata becomes visible to readers. The project distinguishes the Destination channel and the Generated index.
_Avoid_: sink, target, outlet

**Destination channel**:
The Telegram chat that receives the plain-text notice message and the PDF documents for each published Public notice.
_Avoid_: group, target, inbox

**Validation channel**:
A private Telegram chat used to observe real message and document delivery before production use.
_Avoid_: test group, sandbox

**Operator**:
The person responsible for credentials, scheduling, review and the publication, retention and withdrawal decisions.
_Avoid_: user, admin, maintainer

**Schedule owner**:
The named person or system that runs the job, protects credentials and handles failures.
_Avoid_: cron, scheduler

**Withdrawal**:
The event in which a Public notice stops being available from the Source register and may require removal from a Publication surface.
_Avoid_: deletion, expiry

**Retention**:
The policy that decides how long Notice state, Generated index history and published messages remain available.
_Avoid_: cleanup, pruning, archive

**Release gate**:
The set of decisions, checks and evidence that must be satisfied before a production rollout.
_Avoid_: checklist, deployment, sign-off
