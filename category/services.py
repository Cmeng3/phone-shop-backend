from .models import Category


def create_category(data):
    return Category.objects.create(**data)

def update_category(category: Category, data: dict):
    for field, value in data.items():
        setattr(category, field, value)
    category.save()
    return category
    
def get_all_categories():
    return Category.objects.all().order_by('-created_at')


def get_category_by_id(category_id):
    try:
        return Category.objects.get(id=category_id)
    except (Category.DoesNotExist, ValueError):
        return None

