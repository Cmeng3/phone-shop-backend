from typing import Type
from django.db.models import Model
from django.db import transaction
from common.models import IdSequence


class BaseIdGenerator:
    """
    Base class for incremental formatted ID generation (e.g. 'PREFIX-0001' or 'PREFIX0001').
    """
    prefix: str = ""
    delimiter: str = "-"
    padding: int = 4
    field_name: str = "id"
    model_class: Type[Model] = None

    @classmethod
    def generate(
        cls,
        model_class: Type[Model] = None,
        prefix: str = None,
        field_name: str = None,
        padding: int = None,
        delimiter: str = None,
    ) -> str:
        model = model_class or cls.model_class
        pfx = prefix if prefix is not None else cls.prefix
        field = field_name if field_name is not None else cls.field_name
        pad = padding if padding is not None else cls.padding
        delim = delimiter if delimiter is not None else cls.delimiter

        if not model or not pfx:
            raise ValueError("Both model_class and prefix must be specified.")

        prefix_with_delim = f"{pfx}{delim}"
        filter_kwargs = {f"{field}__startswith": prefix_with_delim}
        key = f'{model._meta.label_lower}:{field}:{prefix_with_delim}'
        with transaction.atomic():
            if not IdSequence.objects.filter(pk=key).exists():
                # Bootstrap from legacy rows using numeric order, including overflow.
                maximum = 0
                for value in model.objects.filter(**filter_kwargs).values_list(field, flat=True):
                    suffix = str(value)[len(prefix_with_delim):]
                    if suffix.isascii() and suffix.isdigit():
                        maximum = max(maximum, int(suffix))
                IdSequence.objects.get_or_create(key=key, defaults={'value': maximum})
            sequence = IdSequence.objects.select_for_update().get(pk=key)
            sequence.value += 1
            sequence.save(update_fields=['value'])
            return f'{prefix_with_delim}{sequence.value:0{pad}d}'


class CategoryIdGenerator(BaseIdGenerator):
    """
    ID Generator for Categories. Generates IDs in the format 'CAT-0001'.
    """
    prefix = "CAT"
    delimiter = "-"
    padding = 4
    field_name = "id"

    @classmethod
    def generate(cls, model_class: Type[Model] = None) -> str:
        if model_class is None:
            from category.models import Category
            model_class = Category
        return super().generate(model_class=model_class)


class BrandIdGenerator(BaseIdGenerator):
    """
    ID Generator for Brands. Generates IDs in the format 'BRA00001' (no dash).
    """
    prefix = "BRA"
    delimiter = ""
    padding = 5
    field_name = "id"

    @classmethod
    def generate(cls, model_class: Type[Model] = None) -> str:
        if model_class is None:
            from brand.models import Brand
            model_class = Brand
        return super().generate(model_class=model_class)
