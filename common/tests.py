from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from accounts.models import Profile, Role
from tenant.models import Tenant
from brand.models import Brand
from category.models import Category
from product.models import Product
from rest_framework.authtoken.models import Token
from django.core.cache import cache


class CatalogBrowseTests(APITestCase):
    def setUp(self):
        shop = Tenant.objects.create(name='Browse shop', type='PHONE')
        brand = Brand.objects.create(name='Brand', tenant=shop)
        category = Category.objects.create(name='Phones', slug='phones', tenant=shop)
        owner = get_user_model().objects.create_user('browser', 'browser@example.test')
        role = Role.objects.create(name='Catalog manager', can_manage_catalog=True)
        Profile.objects.create(user=owner, tenant=shop, role=role)
        self.client.force_authenticate(owner)
        for index in range(53):
            Product.objects.create(tenant=shop, brand=brand, category=category,
                name=f'Phone {index:02}', sku=f'BROWSE-{index}', price=53-index, stock=index)
        other = Tenant.objects.create(name='Other shop', type='PHONE')
        foreign_brand = Brand.objects.create(name='Other brand', tenant=other)
        foreign_category = Category.objects.create(name='Other category', slug='other', tenant=other)
        Product.objects.create(tenant=other, brand=foreign_brand, category=foreign_category,
            name='Foreign phone', sku='FOREIGN', price=0, stock=0)

    def test_sorting_is_numeric_and_pagination_preserves_owner_scope(self):
        first = self.client.get('/api/v1/products?ordering=price,id')
        second = self.client.get('/api/v1/products?ordering=price,id&page=2')
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data['count'], 53)
        records = first.data['results'] + second.data['results']
        self.assertEqual([float(row['price']) for row in records], list(range(1, 54)))
        self.assertEqual(len({row['id'] for row in records}), 53)
        self.assertNotIn('FOREIGN', [row['sku'] for row in records])

    def test_sorting_combines_with_low_stock_and_search(self):
        response = self.client.get('/api/v1/products?ordering=stock,id&low_stock=true&search=Phone')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row['stock'] for row in response.data['results']], list(range(6)))

    def test_unlisted_sort_fields_do_not_expose_related_data(self):
        response = self.client.get('/api/v1/products?ordering=tenant__name')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 53)


class LoginRouteGuardTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(
            'route-user', 'route@example.test', 'Route-Test-Password-2026!')

    def login(self):
        response = self.client.post('/api/v1/auth/login', {
            'identifier': self.user.email, 'password': 'Route-Test-Password-2026!'
        }, format='json')
        self.assertEqual(response.status_code, 200)
        return response.data['token']

    def test_anonymous_browser_routes_redirect_to_login(self):
        for path in ['/', '/products', '/dashboard', '/profile', '/users', '/admin/',
                     '/media/products/private.png', '/unknown-route']:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 302, path)
            self.assertEqual(response.url, '/login', path)
        self.assertNotEqual(self.client.get('/login').status_code, 302)

    def test_api_navigation_redirects_but_api_clients_receive_401(self):
        response = self.client.get('/api/v1/products', HTTP_ACCEPT='text/html')
        self.assertEqual(response.status_code, 302)
        for path in ['dashboard', 'products', 'brands', 'categories', 'product-lines',
                     'tenants', 'users', 'roles', 'role-requests', 'available-roles', 'auth/profile']:
            self.assertEqual(self.client.get('/api/v1/' + path).status_code, 401, path)

    def test_login_allows_pages_but_cookie_does_not_authorize_api_writes(self):
        token = self.login()
        self.assertNotEqual(self.client.get('/products').status_code, 302)
        self.assertEqual(self.client.post('/api/v1/products', {}, format='json').status_code, 401)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token)
        self.assertEqual(self.client.get('/api/v1/auth/profile').status_code, 200)
        self.assertEqual(self.client.post('/api/v1/auth/logout', {}, format='json').status_code, 200)
        self.assertEqual(self.client.get('/products').status_code, 302)

    def test_revoked_token_and_banned_user_cannot_reuse_browser_cookie(self):
        self.login()
        Token.objects.filter(user=self.user).delete()
        self.assertEqual(self.client.get('/dashboard').status_code, 302)
        self.login()
        self.user.is_active = False
        self.user.save(update_fields=['is_active'])
        self.assertEqual(self.client.get('/profile').status_code, 302)
