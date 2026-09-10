from .models import Brand


def create_brand(data):
    return Brand.objects.create(**data)

def update_brand(brand: Brand, data: dict):
    for field, value in data.items():
        setattr(brand, field, value)
    brand.save()
    return brand

def get_all_brands():
    return Brand.objects.all().order_by('-created_at')

def get_brand_by_id(brand_id):
    try:
        return Brand.objects.get(id=brand_id)
    except (Brand.DoesNotExist, ValueError):
        return None
