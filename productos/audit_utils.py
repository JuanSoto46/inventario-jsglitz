# productos/audit_utils.py
from __future__ import annotations

from decimal import Decimal
from datetime import date, datetime
from typing import Any

from django.forms.models import model_to_dict
from django.db.models import Model, QuerySet
from django.utils.timezone import is_aware


def _to_primitive(value: Any) -> Any:
    """Convierte objetos Django y tipos exóticos a algo serializable por JSON."""
    if isinstance(value, Model):
        data = model_to_dict(value)
        data["id"] = value.pk
        data["__model__"] = value._meta.label
        data["__str__"] = str(value)
        return data

    if isinstance(value, QuerySet):
        return [_to_primitive(item) for item in value]

    if isinstance(value, (list, tuple, set)):
        return [_to_primitive(item) for item in value]

    if isinstance(value, dict):
        return {k: _to_primitive(v) for k, v in value.items()}

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, datetime):
        return value.isoformat() if is_aware(value) else value.replace(tzinfo=None).isoformat()

    if isinstance(value, date):
        return value.isoformat()

    return value


def _first_present(field_names: set[str], *candidates: str) -> str | None:
    """Devuelve el primer nombre de campo que exista en el modelo, o None."""
    for c in candidates:
        if c in field_names:
            return c
    return None


def save_audit(
    request,
    *,
    entity_type: str,
    entity_id: int | str | None,
    action: str,
    before: Any = None,
    after: Any = None,
    extra: dict | None = None,
):
    """
    Guarda un registro en AuditLog mapeando nombres a los campos reales del modelo.
    Soporta alias: user/username, object_id/entity_id, model/entity_type,
    before/data_before, after/data_after/changes, extra/metadata/meta, ip/ip_address, user_agent/ua.
    """
    from .models_audit import AuditLog  # import tardío para evitar ciclos

    user = getattr(request, "user", None)
    username = getattr(user, "username", None) if user and getattr(user, "is_authenticated", False) else None

    std = {
        "entity_type": str(entity_type) if entity_type is not None else None,
        "entity_id": str(entity_id) if entity_id is not None else None,
        "action": str(action) if action is not None else None,
        "username": username,
        "before": _to_primitive(before),
        "after": _to_primitive(after),
        "extra": _to_primitive(extra or {}),
        "ip": getattr(request, "META", {}).get("REMOTE_ADDR"),
        "user_agent": getattr(request, "META", {}).get("HTTP_USER_AGENT"),
    }

    model_fields = {
        f.name
        for f in AuditLog._meta.get_fields()
        if not getattr(f, "many_to_many", False) and not getattr(f, "one_to_many", False)
    }

    mapping: dict[str, list[str]] = {
        "entity_type": ["entity_type", "model", "entity", "tipo", "tabla"],
        "entity_id": ["entity_id", "object_id", "obj_id", "pk", "registro_id"],
        "action": ["action", "accion", "acción", "event", "evento"],
        "user_fk": ["user", "actor", "usuario_fk"],
        "username": ["username", "user_name", "usuario", "actor_name"],
        "before": ["before", "data_before", "antes", "old_data", "previo"],
        "after": ["after", "data_after", "despues", "después", "new_data", "cambios", "changes"],
        "extra": ["extra", "metadata", "meta", "info", "context"],
        "ip": ["ip", "ip_address", "remote_addr", "client_ip"],
        "user_agent": ["user_agent", "ua", "agent", "navegador"],
    }

    kwargs: dict[str, Any] = {}

    # entity_type / entity_id / action
    if (dest := _first_present(model_fields, *mapping["entity_type"])) and std["entity_type"] is not None:
        kwargs[dest] = std["entity_type"]
    if (dest := _first_present(model_fields, *mapping["entity_id"])) and std["entity_id"] is not None:
        kwargs[dest] = std["entity_id"]
    if (dest := _first_present(model_fields, *mapping["action"])) and std["action"] is not None:
        kwargs[dest] = std["action"]

    # usuario: FK preferida; si no, username textual
    if (dest := _first_present(model_fields, *mapping["user_fk"])) and user and getattr(user, "is_authenticated", False):
        kwargs[dest] = user
    elif (dest := _first_present(model_fields, *mapping["username"])) and std["username"]:
        kwargs[dest] = std["username"]

    # before / after / extra
    if (dest := _first_present(model_fields, *mapping["before"])) and std["before"] is not None:
        kwargs[dest] = std["before"]
    if (dest := _first_present(model_fields, *mapping["after"])) and std["after"] is not None:
        kwargs[dest] = std["after"]
    if (dest := _first_present(model_fields, *mapping["extra"])) and std["extra"] is not None:
        kwargs[dest] = std["extra"]

    # ip / user_agent
    if (dest := _first_present(model_fields, *mapping["ip"])) and std["ip"]:
        kwargs[dest] = std["ip"]
    if (dest := _first_present(model_fields, *mapping["user_agent"])) and std["user_agent"]:
        kwargs[dest] = std["user_agent"]

    # Solo manda lo que el modelo soporta
    kwargs = {k: v for k, v in kwargs.items() if k in model_fields}

    AuditLog.objects.create(**kwargs)
