from pydantic import BaseModel, model_validator, model_serializer
from typing import Any, Dict

class Mapped:
    """ Hold explicit sub-field → raw-key mappings """
    def __init__(self, mapping: Dict[str, str]):
        self.mapping = mapping

def extract_mapped(
    data: dict[str, Any],
    field_name: str,
    mapping: Dict[str, str],
) -> None:
    collected: dict[str, Any] = {}
    for sub_field, raw_key in mapping.items():
        if raw_key in data:
            collected[sub_field] = data.pop(raw_key)
    if collected:
        data[field_name] = collected

def flatten_mapped(
    nested: dict[str, Any],
    field_name: str,
    mapping: Dict[str, str]
) -> dict[str, Any]:
    flat = {}
    for key, val in nested.items():
        if key == field_name and isinstance(val, dict):
            for sub_field, raw_key in mapping.items():
                if sub_field in val:
                    flat[raw_key] = val[sub_field]
        else:
            flat[key] = val
    return flat

class MappedModel(BaseModel):
    @model_validator(mode='before')
    @classmethod
    def _gather_mapped(cls, data: dict[str, Any]) -> dict[str, Any]:
        for name, field in cls.model_fields.items():
            # **use** field.metadata, not field.field_info
            for meta in field.metadata:
                if isinstance(meta, Mapped):
                    extract_mapped(
                        data,
                        field_name=name,
                        mapping=meta.mapping,
                    )
        return data

    @model_serializer(mode='wrap')
    def _flatten_mapped(self, handler):
        nested = handler(self)
        flat = nested
        for name, field in self.model_fields.items():
            for meta in field.metadata:
                if isinstance(meta, Mapped):
                    flat = flatten_mapped(
                        flat,
                        field_name=name,
                        mapping=meta.mapping,
                    )
        return flat
