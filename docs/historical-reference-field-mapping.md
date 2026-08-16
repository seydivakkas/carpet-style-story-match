# Historical Reference Field Mapping Matrix

Mapping rules from A6 normalized museum object sources to A7 HistoricalReferenceMetadata.

| A6 Source Field | A7 Historical Field | Mapping Type | Inference Allowed? | Notes |
|---|---|---|---|---|
| `provider_key` + `official_object_id` | `reference_key` | Deterministic String (`ref-{prov}-{oid}`) | NO | Unique reference identifier |
| `institution_name` | `institution_name` | Direct | NO | Museum display name |
| `official_object_id` | `object_identifier` | Direct | NO | Institutional object ID |
| `accession_number` | `accession_number` | Direct / Nullable | NO | Source accession number |
| `object_title` | `object_title` | Direct | NO | Source object title |
| `culture` | `culture` | Direct / Nullable | NO | Source-reported culture string |
| `period` | `period` | Direct / Nullable | NO | Source-reported period string |
| `dynasty_or_tradition` | `dynasty_or_tradition` | Direct / Nullable | NO | Source-reported dynasty string |
| `date_display` | `date_display` | Direct / Nullable | NO | Source-reported date string |
| `None` | `date_start_year` | Nullable | NO | Zero regex date guesses |
| `None` | `date_end_year` | Nullable | NO | Zero regex date guesses |
| `geography` | `geography` | Direct / Nullable | NO | Source-reported geography |
| `medium` | `medium` | Direct / Nullable | NO | Source-reported materials |
| `dimensions_text` | `dimensions_text` | Direct / Nullable | NO | Source-reported dimensions |
| `department` | `department` | Direct / Nullable | NO | Museum department |
| `credit_line` | `credit_line` | Direct / Nullable | NO | Museum credit line |
| `object_url` | `object_url` | Direct | NO | Museum object web URL |
| `primary_image_source_url` | `source_image_url` | Direct / Metadata Only | NO | Remote image URL for preview |
| `rights.rights_statement` | `rights_statement` | Direct / Nullable | NO | Rights statement |
| `rights.open_access` | `open_access` | Direct / Nullable | NO | Open Access boolean |

