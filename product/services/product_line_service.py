from product.models import ProductLine


def create_product_line(data):
    return ProductLine.objects.create(**data)


def get_all_product_lines():
    return ProductLine.objects.select_related('category', 'brand').all().order_by('-created_at')


def get_product_line_by_id(product_line_id):
    try:
        return ProductLine.objects.select_related('category', 'brand').get(id=product_line_id)
    except (ProductLine.DoesNotExist, ValueError):
        return None


def update_product_line(product_line: ProductLine, data: dict):
    for field, value in data.items():
        setattr(product_line, field, value)
    product_line.save()
    return product_line


def delete_product_line(product_line: ProductLine):
    product_line.delete()
    return True
