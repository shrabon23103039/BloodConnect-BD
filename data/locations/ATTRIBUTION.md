# Bangladesh administrative location snapshot: attribution and status

## Source attribution

Bangladesh Administrative Divisions Dataset, Open Admin Data (`https://github.com/open-admin-data/bangladesh-administrative-divisions`), version `2026.09`, repository commit `1731ee8585a32ad62f5c898f8e8e3f7659b1aa5a` (released 2026-09-08; retrieved 2026-11-21).

Data from Open Admin Data (https://openadmindata.org/bd/) — CC BY 4.0. Please cite: https://github.com/open-admin-data/bangladesh-administrative-divisions

Adaptation: retained only division, district and upazila records; preserved the dataset's `id` as `source_id`, English and Bengali names, and parent path; omitted coordinates, postal codes, unions and other fields. The candidate snapshot is `bangladesh-admin-2026.09.json`. Its SHA-256 is `72b9e8ffc34f5b7e1c5d7abc7b4179ea5d1bee95e1df98e099b0345a5b4f2fd5`. Raw-file hashes: divisions `4620EC88088A5F214AE98092B32C261FFECC2014E9F3EE441A4DF059C57ADE43`; districts `E2560D0E0D1EEB969CFE212588F189609DC1E45D90CCDB5BA924B343F6A47051`; upazilas `FFC2A3FD1217E7C45964D1BF33D2B3C20415C4EA7E3B5ACA60437D56F16DFE2A9`.

The dataset is licensed under Creative Commons Attribution 4.0 International. See [`CC-BY-4.0.txt`](CC-BY-4.0.txt). Changes were made as described above. The dataset author's README identifies Open Admin Data as source, but supplies per-record source URLs only for the 8 divisions; provenance for 64 districts and 495 upazilas is not individually enumerated.

## Validation and known limitations

The checked-out data files contain 8 divisions, 64 districts and 495 upazilas. Structural checks found zero duplicate IDs, identifier/code mismatches, missing or wrong-level parent references, ancestor-path errors, missing English/Bengali names, or declared child-count mismatches. The repository's `all-flat.csv` has only 72 rows (8 divisions and 64 districts); it omits upazilas, which were taken from `all-upazila.json`. The data IDs are retained as Open Admin Data identifiers and are not represented as official BBS geocodes.

This snapshot omits eight upazilas subsequently named in 2026 public government/BSS reports: Mokamtala, Matamuhuri, Ruhia, Bhully, Chandraganj, Bangra, Fatikchhari North and South Gafargaon. The reports do not agree on the current official total/effective status, while a separate 2026-07-20 community snapshot lists 502 upazilas and 74 thanas and also has naming variants. Therefore this candidate snapshot is retained for audit/reproducibility but all 567 imported rows are currently inactive. It must not power donor/profile location selection until the current official hierarchy, effective units, names/parents and usable source identifiers are reconciled.
