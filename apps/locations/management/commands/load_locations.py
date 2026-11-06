"""Load an offline, human-reviewed JSON location snapshot."""

import json
from datetime import date
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlparse

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.locations.models import Location, LocationLevel


LEVEL_ORDER = {
    LocationLevel.DIVISION: 0,
    LocationLevel.DISTRICT: 1,
    LocationLevel.UPAZILA: 2,
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
    validated = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise CommandError(f"Record {index + 1} must be a JSON object.")
        try:
            level = record["level"]
            name_en = record["name_en"].strip()
            name_bn = record.get("name_bn")
            parent_path = record.get("parent_path", [])
        except (KeyError, AttributeError) as error:
            raise CommandError(f"Record {index + 1} is missing a valid name or level.") from error
        if level not in LocationLevel.values:
            raise CommandError(f"Record {index + 1} has an unknown level.")
        expected_parent_depth = LEVEL_ORDER[level]
        if not isinstance(parent_path, list) or len(parent_path) != expected_parent_depth:
            raise CommandError(f"Record {index + 1} has an invalid parent path for {level}.")
        if any(not isinstance(name, str) or not name.strip() for name in parent_path):
            raise CommandError(f"Record {index + 1} has an invalid parent path.")
        if not name_en or len(name_en) > 120:
            raise CommandError(f"Record {index + 1} has an invalid English name.")
        if name_bn is not None and (not isinstance(name_bn, str) or len(name_bn) > 120):
            raise CommandError(f"Record {index + 1} has an invalid Bengali name.")

        path = tuple(_key(part) for part in [*parent_path, name_en])
        if path in normalized:
            raise CommandError(f"Duplicate normalized location path at record {index + 1}.")
        if expected_parent_depth:
            parent_path_key = path[:-1]
            if parent_path_key not in normalized:
                raise CommandError(f"Record {index + 1} references a parent that is missing or appears later.")
            expected_parent = (
                LocationLevel.DIVISION if level == LocationLevel.DISTRICT
                else LocationLevel.DISTRICT
            )
            if normalized[parent_path_key]["level"] != expected_parent:
                raise CommandError(f"Record {index + 1} has a parent at the wrong level.")

        item = {
            "level": level,
            "name_en": name_en,
            "name_bn": name_bn.strip() if name_bn else None,
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
                existing = Location.objects.filter(
                    level=item["level"],
                    parent=parent,
                    name_en__iexact=item["name_en"],
                ).first()
                if existing is None:
                    location = Location.objects.create(
                        name_en=item["name_en"],
                        name_bn=item["name_bn"],
                        level=item["level"],
                        parent=parent,
                        source_name=source["name"],
                        source_version=source["version"],
                    )
                    created += 1
                else:
                    before = (
                        existing.name_bn,
                        existing.source_name,
                        existing.source_version,
                        existing.is_active,
                    )
                    existing.name_bn = item["name_bn"]
                    existing.source_name = source["name"]
                    existing.source_version = source["version"]
                    existing.is_active = True
                    existing.save()
                    after = (
                        existing.name_bn,
                        existing.source_name,
                        existing.source_version,
                        existing.is_active,
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
