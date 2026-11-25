import uuid
from django.db.models import Q

from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from apps.locations.models import Location, LocationLevel


@require_GET
@never_cache
def child_options(request, level):
    """Public reference-data endpoint; return active children only."""
    allowed_parent_levels = {
        LocationLevel.DISTRICT: {LocationLevel.DIVISION},
        LocationLevel.UPAZILA: {LocationLevel.DISTRICT},
        LocationLevel.UNION: {LocationLevel.UPAZILA},
        LocationLevel.CITY_CORPORATION: {LocationLevel.DISTRICT},
        LocationLevel.ZONE: {LocationLevel.CITY_CORPORATION},
        LocationLevel.WARD: {LocationLevel.CITY_CORPORATION, LocationLevel.ZONE},
    }
    parents = allowed_parent_levels.get(level)
    if parents is None:
        return JsonResponse({"results": []}, status=400)

    try:
        parent_id = uuid.UUID(request.GET.get("parent", ""))
    except (ValueError, TypeError, AttributeError):
        return JsonResponse({"results": []})

    parent = Location.objects.filter(pk=parent_id, level__in=parents, is_active=True)
    if level == LocationLevel.DISTRICT:
        pass
    elif level == LocationLevel.CITY_CORPORATION:
        parent = parent.filter(
            parent__level=LocationLevel.DIVISION,
            parent__is_active=True,
        )
    elif level == LocationLevel.UPAZILA:
        parent = parent.filter(
            parent__level=LocationLevel.DIVISION,
            parent__is_active=True,
        )
    elif level == LocationLevel.ZONE:
        parent = parent.filter(
            parent__level=LocationLevel.DISTRICT,
            parent__is_active=True,
            parent__parent__level=LocationLevel.DIVISION,
            parent__parent__is_active=True,
        )
    elif level == LocationLevel.UNION:
        parent = parent.filter(
            parent__level=LocationLevel.DISTRICT,
            parent__is_active=True,
            parent__parent__level=LocationLevel.DIVISION,
            parent__parent__is_active=True,
        )
    elif level == LocationLevel.WARD:
        parent = parent.filter(
            Q(level=LocationLevel.CITY_CORPORATION,
              parent__level=LocationLevel.DISTRICT,
              parent__is_active=True,
              parent__parent__level=LocationLevel.DIVISION,
              parent__parent__is_active=True)
            | Q(level=LocationLevel.ZONE,
                parent__level=LocationLevel.CITY_CORPORATION,
                parent__is_active=True,
                parent__parent__level=LocationLevel.DISTRICT,
                parent__parent__is_active=True,
                parent__parent__parent__level=LocationLevel.DIVISION,
                parent__parent__parent__is_active=True,
                )
        )
    if not parent.exists():
        return JsonResponse({"results": []})

    results = Location.objects.filter(
        parent_id=parent_id, level=level, is_active=True
    ).filter(_active_ancestors_filter(level)).order_by("name_en").values("id", "name_en")
    return JsonResponse({"results": list(results)})


def _active_ancestors_filter(level):
    if level == LocationLevel.DISTRICT:
        return Q(parent__level=LocationLevel.DIVISION, parent__is_active=True)
    if level in {LocationLevel.UPAZILA, LocationLevel.CITY_CORPORATION}:
        return Q(
            parent__level=LocationLevel.DISTRICT,
            parent__is_active=True,
            parent__parent__level=LocationLevel.DIVISION,
            parent__parent__is_active=True,
        )
    if level == LocationLevel.ZONE:
        return Q(
            parent__level=LocationLevel.CITY_CORPORATION,
            parent__is_active=True,
            parent__parent__level=LocationLevel.DISTRICT,
            parent__parent__is_active=True,
            parent__parent__parent__level=LocationLevel.DIVISION,
            parent__parent__parent__is_active=True,
        )
    if level == LocationLevel.UNION:
        return Q(
            parent__level=LocationLevel.UPAZILA,
            parent__is_active=True,
            parent__parent__level=LocationLevel.DISTRICT,
            parent__parent__is_active=True,
            parent__parent__parent__level=LocationLevel.DIVISION,
            parent__parent__parent__is_active=True,
        )
    if level == LocationLevel.WARD:
        return (
            Q(parent__level=LocationLevel.CITY_CORPORATION,
              parent__is_active=True,
              parent__parent__level=LocationLevel.DISTRICT,
              parent__parent__is_active=True,
              parent__parent__parent__level=LocationLevel.DIVISION,
              parent__parent__parent__is_active=True)
            | Q(parent__level=LocationLevel.ZONE,
                parent__is_active=True,
                parent__parent__level=LocationLevel.CITY_CORPORATION,
                parent__parent__is_active=True,
                parent__parent__parent__level=LocationLevel.DISTRICT,
                parent__parent__parent__is_active=True,
                parent__parent__parent__parent__level=LocationLevel.DIVISION,
                parent__parent__parent__parent__is_active=True)
        )
    return Q()
