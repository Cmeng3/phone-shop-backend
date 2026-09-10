from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, F
from django.db.models.functions import Lower
from product.models import ProductLine
from brand.models import Brand


class Command(BaseCommand):
    help = 'Read-only audit of legacy shop relationships and duplicate login emails. Run before upgrading.'

    def handle(self, *args, **options):
        problems = []
        lines = list(ProductLine.objects.exclude(category__tenant_id=F('brand__tenant_id')).values_list('pk', flat=True))
        if lines:
            problems.append(f'Product lines with mismatched shops: {lines}')
        brands = list(Brand.objects.filter(tenant__isnull=True).values_list('pk', flat=True))
        if brands:
            problems.append(f'Brands without a shop: {brands}')
        duplicates = get_user_model().objects.exclude(email='').annotate(normalized_email=Lower('email')).values('normalized_email').annotate(total=Count('pk')).filter(total__gt=1).count()
        if duplicates:
            problems.append(f'Duplicate email groups: {duplicates}. Give each account a distinct email before API login.')
        if problems:
            raise CommandError('\n'.join(problems))
        self.stdout.write(self.style.SUCCESS('Legacy shop relationships and login emails passed.'))
