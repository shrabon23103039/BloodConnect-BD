"""Load an offline, human-reviewed JSON location snapshot."""

import json
from datetime import date
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlparse

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.locations.models import Location, LocationLevel


ALLOWED_PARENT_LEVELS = {
    LocationLevel.DIVISION: set(),
    LocationLevel.DISTRICT: {LocationLevel.DIVISION},
    LocationLevel.UPAZILA: {LocationLevel.DISTRICT},
    LocationLevel.UNION: {LocationLevel.UPAZILA},
    LocationLevel.CITY_CORPORATION: {LocationLevel.DISTRICT},
    LocationLevel.ZONE: {LocationLevel.CITY_CORPORATION},
    LocationLevel.WARD: {LocationLevel.CITY_CORPORATION, LocationLevel.ZONE},
}


def _key(value):
    return value.strip().casefold()


def validate_dataset(document, *, reviewed):
    if not reviewed:
        raise CommandError("Refusing import without explicit --reviewed confirmation.")
    if not isinstance(document, dict) or not isinstance(document.get("source"), dict):
        raise CommandError("The JSON document must contain source metadata and records.")
    source = document["source"]
    required_source_fields = ("name", "version", "url", "reviewed_by", "reviewed_at")
    if any(not isinstance(source.get(field), str) or not source[field].strip()
           for field in required_source_fields):
        raise CommandError("Source name, version, URL, reviewer and review date are required.")
    source = {key: value.strip() for key, value in source.items() if isinstance(value, str)}
    try:
        date.fromisoformat(source["reviewed_at"])
    except ValueError as error:
        raise CommandError("Review date must use YYYY-MM-DD format.") from error
    if len(source["name"]) > 120 or len(source["version"]) > 60:
        raise CommandError("Source name or version exceeds the database field limit.")
    parsed_url = urlparse(source["url"])
    if parsed_url.scheme not in {"https", "http"} or not parsed_url.netloc:
        raise CommandError("Source URL must use HTTP or HTTPS.")
    records = document.get("records")
    if not isinstance(records, list) or not records:
        raise CommandError("At least one location record is required.")

    normalized = {}
    source_ids = set()
    validated = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise CommandError(f"Record {index + 1} must be a JSON object.")
        try:
            level = record["level"]
            name_en = record["name_en"].strip()
            name_bn = record.get("name_bn")
            parent_path = record.get("parent_path", [])
            source_id = record.get("source_id")
        except (KeyError, AttributeError) as error:
            raise CommandError(f"Record {index + 1} is missing a valid name or level.") from error
        if level not in LocationLevel.values:
            raise CommandError(f"Record {index + 1} has an unknown level.")
        if not isinstance(parent_path, list):
            raise CommandError(f"Record {index + 1} has an invalid parent path for {level}.")
        if bool(ALLOWED_PARENT_LEVELS[level]) != bool(parent_path):
            raise CommandError(f"Record {index + 1} has an invalid parent path for {level}.")
        if any(not isinstance(name, str) or not name.strip() for name in parent_path):
            raise CommandError(f"Record {index + 1} has an invalid parent path.")
        if not name_en or len(name_en) > 120:
            raise CommandError(f"Record {index + 1} has an invalid English name.")
        if name_bn is not None and (not isinstance(name_bn, str) or len(name_bn) > 120):
            raise CommandError(f"Record {index + 1} has an invalid Bengali name.")
        if source_id is not None:
            if not isinstance(source_id, str) or not source_id.strip() or len(source_id) > 32:
                raise CommandError(f"Record {index + 1} has an invalid source ID.")
            source_id = source_id.strip()
            if source_id in source_ids:
                raise CommandError(f"Duplicate source ID at record {index + 1}.")
            source_ids.add(source_id)

        path = tuple(_key(part) for part in [*parent_path, name_en])
        if path in normalized:
            raise CommandError(f"Duplicate normalized location path at record {index + 1}.")
        if parent_path:
            parent_path_key = path[:-1]
            if parent_path_key not in normalized:
                raise CommandError(f"Record {index + 1} references a parent that is missing or appears later.")
            if normalized[parent_path_key]["level"] not in ALLOWED_PARENT_LEVELS[level]:
                raise CommandError(f"Record {index + 1} has a parent at the wrong level.")

        item = {
            "level": level,
            "name_en": name_en,
            "name_bn": name_bn.strip() if name_bn else None,
            "source_id": source_id,
            "path": path,
            "parent_path": path[:-1],
        }
        normalized[path] = item
        validated.append(item)
    return source, validated


class Command(BaseCommand):
    help = "Import an offline JSON snapshot after a reviewer has confirmed its provenance and hierarchy."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, type=Path)
        parser.add_argument(
            "--reviewed",
            action="store_true",
            help="Confirm a human reviewed the source, version, names and hierarchy.",
        )
        parser.add_argument(
            "--activate",
            action="store_true",
            help="Reactivate matching inactive rows after current-source review.",
        )

    def handle(self, *args, **options):
        file_path = options["file"]
        try:
            raw_document = file_path.read_bytes()
            document = json.loads(raw_document.decode("utf-8"))
        except OSError as error:
            raise CommandError("Unable to read location snapshot.") from error
        except json.JSONDecodeError as error:
            raise CommandError("Location snapshot is not valid JSON.") from error

        source, records = validate_dataset(document, reviewed=options["reviewed"])
        created = updated = unchanged = 0
        by_path = {}
        with transaction.atomic():
            for item in records:
                parent = by_path.get(item["parent_path"])
                named_matches = list(
                    Location.objects.filter(
                        level=item["level"],
                        parent=parent,
                        name_en__iexact=item["name_en"],
                    )[:2]
                )
                if len(named_matches) > 1:
                    raise CommandError(
                        f"Location path {' > '.join(part.title() for part in item['path'])!r} "
                        "matches multiple existing rows; resolve the duplicate rows before importing."
                    )

                existing = None
                if item["source_id"]:
                    existing = Location.objects.filter(
                        source_name=source["name"], source_id=item["source_id"]
                    ).first()
                    if existing and (
                        existing.level != item["level"]
                        or existing.name_en.casefold() != item["name_en"].casefold()
                        or existing.parent_id != (parent.id if parent else None)
                    ):
                        raise CommandError(
                            f"Source ID {item['source_id']} conflicts with an existing location; refusing to remap it."
                        )
                    if existing and named_matches and named_matches[0].pk != existing.pk:
                        raise CommandError(
                            f"Source ID {item['source_id']} and location name match different existing rows; "
                            "reconcile the source identity before importing."
                        )
                    if existing is None and named_matches:
                        matched = named_matches[0]
                        raise CommandError(
                            f"Location {' > '.join(part.title() for part in item['path'])!r} already exists "
                            f"as source {matched.source_name!r} with source ID {matched.source_id!r}; "
                            f"incoming source {source['name']!r} ID {item['source_id']!r} cannot be matched by name. "
                            "Reconcile the source ID or explicitly resolve the existing row before importing."
                        )
                elif named_matches:
                    matched = named_matches[0]
                    if matched.source_name != source["name"]:
                        raise CommandError(
                            f"Location {' > '.join(part.title() for part in item['path'])!r} already belongs "
                            f"to source {matched.source_name!r}; incoming source {source['name']!r} cannot reuse "
                            "it by name. Reconcile the source identity before importing."
                        )
                    if matched.source_id is not None:
                        raise CommandError(
                            f"Location {' > '.join(part.title() for part in item['path'])!r} already has source ID "
                            f"{matched.source_id!r}, but the incoming record has no source ID. Reconcile the "
                            "source identity before importing."
                        )
                    existing = matched

                if existing is None:
                    corporation_scope = None
                    if item["level"] == LocationLevel.WARD:
                        corporation_scope = (
                            parent if parent.level == LocationLevel.CITY_CORPORATION else parent.parent
                        )
                    location = Location.objects.create(
                        name_en=item["name_en"],
                        name_bn=item["name_bn"],
                        level=item["level"],
                        parent=parent,
                        corporation_scope=corporation_scope,
                        source_name=source["name"],
                        source_version=source["version"],
                        source_id=item["source_id"],
                        is_active=options["activate"],
                    )
                    created += 1
                else:
                    before = (
                        existing.name_bn,
                        existing.source_name,
                        existing.source_version,
                        existing.source_id,
                        existing.is_active,
                        existing.corporation_scope_id,
                    )
                    existing.name_bn = item["name_bn"]
                    existing.source_version = source["version"]
                    if item["level"] == LocationLevel.WARD:
                        existing.corporation_scope = (
                            parent if parent.level == LocationLevel.CITY_CORPORATION else parent.parent
                        )
                    if options["activate"]:
                        existing.is_active = True
                    existing.save()
                    after = (
                        existing.name_bn,
                        existing.source_name,
                        existing.source_version,
                        existing.source_id,
                        existing.is_active,
                        existing.corporation_scope_id,
                    )
                    location = existing
                    if before == after:
                        unchanged += 1
                    else:
                        updated += 1
                by_path[item["path"]] = location

        self.stdout.write(
            self.style.SUCCESS(
                f"Loaded {len(records)} reviewed location rows from {source['name']} ({source['version']}): "
                f"{created} created, {updated} updated, {unchanged} unchanged. "
                f"Snapshot SHA-256: {sha256(raw_document).hexdigest()}"
            )
        )
