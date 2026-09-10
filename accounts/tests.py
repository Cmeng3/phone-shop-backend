from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from accounts.models import Profile, Role, RoleRequest
from tenant.models import Tenant
from brand.models import Brand
from category.models import Category
from product.models import Product, ProductLine

User = get_user_model()
PASSWORD = 'Example-Strong-Password-984!'


class WorkflowTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = User.objects.create_superuser('admin', 'admin@example.com', PASSWORD)
        self.shop = Tenant.objects.create(name='Shop A', type='PHONE')
        self.other = Tenant.objects.create(name='Shop B', type='PHONE')
        self.role = Role.objects.create(name='Shop Owner', can_manage_catalog=True)
        self.owner = User.objects.create_user('owner', 'owner@example.com', PASSWORD)
        Profile.objects.create(user=self.owner, email=self.owner.email, phone='+85512345678', tenant=self.shop, role=self.role)
        self.brand = Brand.objects.create(tenant=self.shop, name='Apple')
        self.category = Category.objects.create(tenant=self.shop, name='Phones', slug='phones')
        self.foreign_brand = Brand.objects.create(tenant=self.other, name='Apple')
        self.foreign_category = Category.objects.create(tenant=self.other, name='Phones', slug='phones')

    def auth(self, user):
        self.client.force_authenticate(user=user)

    def post(self, path, data=None):
        return self.client.post('/api/v1/' + path, data or {}, format='json')

    def test_anonymous_and_owner_cannot_administer(self):
        for path in ['brands', 'categories', 'products', 'product-lines', 'tenants', 'users', 'roles', 'role-requests']:
            self.assertEqual(self.client.get('/api/v1/' + path).status_code, 401, path)
        self.auth(self.owner)
        for path in ['tenants', 'users', 'roles']:
            self.assertEqual(self.client.get('/api/v1/' + path).status_code, 403)

    def test_email_phone_login_logout_and_bad_credentials(self):
        for identifier in ['OWNER@EXAMPLE.COM', '+855 12 345 678']:
            response = self.post('auth/login', {'identifier': identifier, 'password': PASSWORD})
            self.assertEqual(response.status_code, 200, response.data)
            key = response.data['token']
            self.client.credentials(HTTP_AUTHORIZATION='Token ' + key)
            self.assertEqual(self.client.get('/api/v1/auth/profile').status_code, 200)
            self.assertEqual(self.post('auth/logout').status_code, 200)
            self.assertEqual(self.client.get('/api/v1/auth/profile').status_code, 401)
            self.client.credentials()
        self.assertIn(self.post('auth/login', {'identifier': 'owner@example.com', 'password': 'wrong'}).status_code, [401, 403])

    def test_superadmin_username_login_with_duplicate_email(self):
        User.objects.create_superuser('second-admin', self.admin.email, PASSWORD)
        self.assertEqual(self.post('auth/login', {'identifier': self.admin.email, 'password': PASSWORD}).status_code, 401)
        for username in ['admin', 'second-admin']:
            response = self.post('auth/login', {'identifier': username, 'password': PASSWORD})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data['user']['username'], username)
            self.assertTrue(response.data['user']['is_superuser'])
        self.assertEqual(self.post('auth/login', {'identifier': 'admin', 'password': 'incorrect'}).status_code, 401)

    def test_user_creation_phone_validation_and_optional_phone(self):
        self.auth(self.admin)
        data = {'username': 'phone-check', 'email': 'phone-check@example.test',
                'password': PASSWORD, 'tenant_id': self.shop.pk, 'role_id': self.role.pk,
                'phone': '012345678'}
        response = self.post('users', data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['errors']['phone'],
                         ['Use international format, for example +85512345678.'])
        self.assertEqual(len(response.content), 179)
        self.assertFalse(User.objects.filter(username='phone-check').exists())
        response = self.post('users', {**data, 'phone': '+855 98 765 432'})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['phone'], '+85598765432')
        response = self.post('users', {**data, 'username': 'no-phone',
                                      'email': 'no-phone@example.test', 'phone': ''})
        self.assertEqual(response.status_code, 201, response.data)

    def test_catalog_isolation_create_search_and_duplicate(self):
        self.auth(self.owner)
        response = self.client.get('/api/v1/brands?search=Apple')
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.brand.pk)
        self.assertEqual(self.client.get('/api/v1/brands/' + self.foreign_brand.pk).status_code, 404)
        self.assertEqual(self.client.patch('/api/v1/brands/' + self.foreign_brand.pk, {'name': 'Stolen'}, format='json').status_code, 404)
        self.assertEqual(self.post('brands', {'name': 'Google', 'tenant_id': self.other.pk}).status_code, 400)
        response = self.post('brands', {'name': 'Google'})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['tenant_id'], self.shop.pk)
        self.assertEqual(self.post('brands', {'name': 'Google'}).status_code, 400)
        self.assertEqual(self.post('categories', {'name': 'Tablets', 'slug': 'tablets'}).status_code, 201)
        self.assertEqual(self.client.get('/api/v1/brands?tenant_id=invalid').status_code, 400)

    def test_product_validation_and_crud(self):
        self.auth(self.owner)
        data = {'name': 'Phone', 'sku': 'PHONE-1', 'category': self.category.pk, 'brand': self.brand.pk, 'price': '125.50', 'stock': 3}
        response = self.post('products', data)
        self.assertEqual(response.status_code, 201, response.data)
        product_id = response.data['id']
        self.assertEqual(self.post('products', {**data, 'sku': 'P2', 'brand': self.foreign_brand.pk}).status_code, 400)
        self.assertEqual(self.post('products', {**data, 'sku': 'P2', 'price': '-1'}).status_code, 400)
        self.assertEqual(self.post('products', {**data, 'sku': 'P2', 'stock': -1}).status_code, 400)
        self.assertEqual(self.post('products', data).status_code, 400)
        self.assertEqual(self.client.get('/api/v1/products?search=Phone&status=AVAILABLE').data['count'], 1)
        response = self.client.patch(f'/api/v1/products/{product_id}', {'stock': 5}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['stock'], 5)
        self.assertEqual(self.client.delete(f'/api/v1/products/{product_id}').status_code, 204)

    def test_product_line_cannot_cross_shops(self):
        self.auth(self.owner)
        response = self.post('product-lines', {'name': 'iPhone', 'category_id': self.category.pk, 'brand_id': self.foreign_brand.pk})
        self.assertEqual(response.status_code, 400)
        response = self.post('product-lines', {'name': 'iPhone', 'category_id': self.category.pk, 'brand_id': self.brand.pk})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self.client.patch(f'/api/v1/product-lines/{response.data["id"]}', {'brand_id': self.foreign_brand.pk}, format='json').status_code, 400)

    def test_admin_deletes_require_password_and_protect_dependencies(self):
        self.auth(self.admin)
        for path in [f'brands/{self.brand.pk}', f'categories/{self.category.pk}', f'tenants/{self.shop.pk}', f'roles/{self.role.pk}']:
            self.assertEqual(self.client.delete('/api/v1/' + path).status_code, 403)
            self.assertEqual(self.client.delete('/api/v1/' + path, {'admin_password': 'wrong'}, format='json').status_code, 403)
        self.assertEqual(self.client.delete(f'/api/v1/roles/{self.role.pk}', {'admin_password': PASSWORD}, format='json').status_code, 400)
        Product.objects.create(tenant=self.shop, category=self.category, brand=self.brand, name='Phone', sku='P', price=1)
        self.assertEqual(self.client.delete(f'/api/v1/brands/{self.brand.pk}', {'admin_password': PASSWORD}, format='json').status_code, 400)
        response = self.post('tenants', {'name': 'Empty', 'type': 'PHONE'})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.client.delete(f'/api/v1/tenants/{response.data["id"]}', {'admin_password': PASSWORD}, format='json').status_code, 204)

    def test_profile_and_password_change_revoke_token(self):
        token = Token.objects.create(user=self.owner)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
        response = self.client.patch('/api/v1/auth/profile', {'username': 'owner-new', 'email': 'new@example.com', 'is_superuser': True, 'tenant_id': self.other.pk}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.owner.refresh_from_db()
        self.assertFalse(self.owner.is_superuser)
        self.assertEqual(self.owner.profile.tenant_id, self.shop.pk)
        self.assertEqual(self.post('auth/change-password', {'current_password': 'wrong', 'new_password': PASSWORD}).status_code, 400)
        self.assertEqual(self.post('auth/change-password', {'current_password': PASSWORD, 'new_password': '123'}).status_code, 400)
        self.assertEqual(self.post('auth/change-password', {'current_password': PASSWORD, 'new_password': 'New-Example-Password-982!'}).status_code, 200)
        self.assertEqual(self.client.get('/api/v1/auth/profile').status_code, 401)

    def test_user_create_ban_unban_and_change_role(self):
        self.auth(self.admin)
        response = self.post('users', {'username': 'new', 'email': 'NEW@example.com', 'phone': '+85598765432', 'password': PASSWORD, 'tenant_id': self.shop.pk, 'role_id': self.role.pk, 'is_superuser': True})
        self.assertEqual(response.status_code, 201, response.data)
        target = User.objects.get(pk=response.data['id'])
        self.assertTrue(target.check_password(PASSWORD))
        self.assertFalse(target.is_superuser)
        self.assertNotIn('password', response.data)
        token = Token.objects.create(user=target)
        for action in ['ban', 'change-role']:
            self.assertEqual(self.post(f'users/{target.pk}/{action}').status_code, 403)
        self.assertEqual(self.post(f'users/{target.pk}/ban', {'admin_password': PASSWORD}).status_code, 200)
        self.assertFalse(Token.objects.filter(key=token.key).exists())
        self.assertEqual(self.client.get('/api/v1/users?status=BANNED').data['count'], 1)
        self.assertEqual(self.post(f'users/{target.pk}/unban').status_code, 200)
        role = Role.objects.create(name='Limited')
        self.assertEqual(self.post(f'users/{target.pk}/change-role', {'admin_password': PASSWORD, 'role_id': role.pk}).status_code, 200)
        self.assertEqual(Profile.objects.get(user=target).role_id, role.pk)
        self.assertEqual(self.client.delete(f'/api/v1/users/{target.pk}', {'admin_password': PASSWORD}, format='json').status_code, 204)
        self.assertEqual(self.post(f'users/{self.admin.pk}/ban', {'admin_password': PASSWORD}).status_code, 403)

    def test_role_request_approve_reject_and_no_self_approval(self):
        role = Role.objects.create(name='Limited')
        self.auth(self.owner)
        response = self.post('role-requests', {'role': role.pk, 'reason': 'Change access'})
        self.assertEqual(response.status_code, 201, response.data)
        pk = response.data['id']
        self.assertEqual(self.post('role-requests', {'role': role.pk}).status_code, 400)
        self.assertEqual(self.post(f'role-requests/{pk}/approve').status_code, 403)
        self.auth(self.admin)
        self.assertEqual(self.post(f'role-requests/{pk}/approve').status_code, 200)
        self.assertEqual(Profile.objects.get(user=self.owner).role_id, role.pk)
        self.assertEqual(self.post(f'role-requests/{pk}/reject').status_code, 400)
        self.owner.refresh_from_db()
        self.auth(self.owner)
        self.assertEqual(self.client.get('/api/v1/products').status_code, 403)
        response = self.post('role-requests', {'role': self.role.pk})
        self.assertEqual(response.status_code, 201)
        self.auth(self.admin)
        self.assertEqual(self.post(f'role-requests/{response.data["id"]}/reject').status_code, 200)
        self.assertEqual(Profile.objects.get(user=self.owner).role_id, role.pk)

    def test_inactive_shop_blocks_owner(self):
        self.shop.status = 'INACTIVE'
        self.shop.save()
        self.owner.refresh_from_db()
        self.auth(self.owner)
        self.assertEqual(self.client.get('/api/v1/products').status_code, 403)

    def test_ids_do_not_reuse_deleted_highest(self):
        previous = self.foreign_brand.pk
        self.foreign_brand.delete()
        new = Brand.objects.create(tenant=self.other, name='Replacement')
        self.assertGreater(int(new.pk[3:]), int(previous[3:]))

    def test_wire_response_keeps_original_envelope(self):
        self.auth(self.owner)
        response = self.client.get('/api/v1/brands')
        payload = response.json()
        self.assertEqual(payload['code'], 200)
        self.assertEqual(payload['source'], 'BRAND')
        self.assertEqual(payload['pagination']['count'], 1)
        self.assertEqual(payload['data'][0]['id'], self.brand.pk)
        payload = self.post('brands', {'name': 'Apple'}).json()
        self.assertEqual(payload['code'], 400)
        self.assertIsNone(payload['data'])
        self.assertIn('errors', payload)

    def test_roles_configuration_and_tenant_filters(self):
        self.auth(self.admin)
        response = self.post('roles', {'name': 'Warehouse', 'can_manage_catalog': False})
        self.assertEqual(response.status_code, 201)
        pk = response.data['id']
        self.assertEqual(self.client.get('/api/v1/roles?search=Warehouse').data['count'], 1)
        self.assertEqual(self.client.patch(f'/api/v1/roles/{pk}', {'name': 'Stock Manager'}, format='json').status_code, 200)
        self.assertEqual(self.client.delete(f'/api/v1/roles/{pk}', {'admin_password': PASSWORD}, format='json').status_code, 204)
        self.assertEqual(self.client.patch(f'/api/v1/tenants/{self.other.pk}', {'status': 'INACTIVE'}, format='json').status_code, 200)
        self.assertEqual(self.client.get('/api/v1/tenants?status=ACTIVE&type=PHONE&search=Shop').data['count'], 1)

    def test_other_owner_cannot_read_request_or_product(self):
        restricted = Role.objects.create(name='Restricted')
        request = RoleRequest.objects.create(user=self.owner, role=restricted)
        other_owner = User.objects.create_user('other', 'other@example.com', PASSWORD)
        Profile.objects.create(user=other_owner, tenant=self.other, role=self.role)
        product = Product.objects.create(tenant=self.shop, category=self.category, brand=self.brand, name='Phone', sku='P1', price=10)
        self.auth(other_owner)
        self.assertEqual(self.client.get('/api/v1/role-requests').data['count'], 0)
        self.assertEqual(self.client.get(f'/api/v1/role-requests/{request.pk}').status_code, 404)
        self.assertEqual(self.client.get(f'/api/v1/products/{product.pk}').status_code, 404)
        self.assertEqual(self.client.delete(f'/api/v1/products/{product.pk}').status_code, 404)

    def test_existing_product_line_cannot_invalidate_products(self):
        line = ProductLine.objects.create(name='Series', category=self.category, brand=self.brand)
        Product.objects.create(tenant=self.shop, category=self.category, brand=self.brand, product_line=line, name='Phone', sku='P1', price=10)
        brand = Brand.objects.create(tenant=self.shop, name='Google')
        self.auth(self.owner)
        self.assertEqual(self.client.patch(f'/api/v1/product-lines/{line.pk}', {'brand_id': brand.pk}, format='json').status_code, 400)
        self.assertEqual(self.client.delete(f'/api/v1/product-lines/{line.pk}').status_code, 400)

    def test_banned_user_cannot_login_and_owner_can_delete_empty_records(self):
        self.owner.is_active = False
        self.owner.save()
        self.assertEqual(self.post('auth/login', {'identifier': self.owner.email, 'password': PASSWORD}).status_code, 401)
        self.owner.is_active = True
        self.owner.save()
        self.auth(self.owner)
        for path in [f'brands/{self.brand.pk}', f'categories/{self.category.pk}']:
            self.assertEqual(self.client.delete('/api/v1/' + path).status_code, 204)

    def test_login_throttle(self):
        for _ in range(10):
            self.assertEqual(self.post('auth/login', {'identifier': 'missing@example.com', 'password': 'wrong'}).status_code, 401)
        self.assertEqual(self.post('auth/login', {'identifier': 'missing@example.com', 'password': 'wrong'}).status_code, 429)

    def test_dashboard_totals_are_scoped_to_the_owner_shop(self):
        Product.objects.create(tenant=self.shop, category=self.category, brand=self.brand, name='Own phone', sku='OWN', price='12.50', stock=4)
        Product.objects.create(tenant=self.other, category=self.foreign_category, brand=self.foreign_brand, name='Other phone', sku='OTHER', price='100.00', stock=10)
        self.auth(self.owner)
        response = self.client.get('/api/v1/dashboard')
        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertEqual(data['products'], 1)
        self.assertEqual(data['units'], 4)
        self.assertEqual(float(data['inventory_value']), 50)
        self.assertEqual(data['low_stock'], 1)
        self.assertEqual(data['recent_products'][0]['name'], 'Own phone')
        self.assertEqual(data['recent_products'][0]['brand_name'], 'Apple')
        self.assertNotIn('tenants', data)
        self.assertEqual(sum(month['count'] for month in data['monthly_products']), 1)
        self.auth(self.admin)
        data = self.client.get('/api/v1/dashboard').data
        self.assertEqual(data['products'], 2)
        self.assertEqual(data['tenants'], 2)
        self.assertEqual(float(data['inventory_value']), 1050)

    def test_dashboard_denies_catalog_access_and_profile_exposes_capability(self):
        self.auth(self.owner)
        data = self.client.get('/api/v1/auth/profile').data
        self.assertEqual(data['tenant_name'], self.shop.name)
        self.assertEqual(data['role_name'], self.role.name)
        self.assertTrue(data['can_manage_catalog'])
        self.role.can_manage_catalog = False
        self.role.save()
        self.owner.refresh_from_db()
        self.assertEqual(self.client.get('/api/v1/dashboard').status_code, 403)

    def test_low_stock_filter_excludes_archived_products(self):
        for index, (stock, status) in enumerate([(0, 'UNAVAILABLE'), (5, 'AVAILABLE'), (6, 'AVAILABLE'), (1, 'ARCHIVED')]):
            Product.objects.create(tenant=self.shop, category=self.category, brand=self.brand, name=f'Phone {index}', sku=f'P{index}', price=1, stock=stock, status=status)
        self.auth(self.owner)
        response = self.client.get('/api/v1/products?low_stock=true')
        self.assertEqual(response.data['count'], 2)
