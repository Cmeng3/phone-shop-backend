# Source and use-case diagram review

Reviewed all six supplied images and all Python source, routes, models, serializers, services, settings, migrations, dependency declarations and the existing README. This workspace contains a Django backend; no frontend source was present.

## Diagram coverage

All paths below start with `/api/v1/` and omit a trailing slash.

| Image | Requested behavior | Implemented API |
| --- | --- | --- |
| 1. Shop Owner | Email/phone login, logout, profile view/edit, password change; search/create/edit/delete categories and brands; search/filter/create/edit/delete products | `auth/login`, `auth/logout`, `auth/profile`, `auth/change-password`; `categories`, `brands`, `products` and their detail routes |
| 2. Super Admin overview | Authentication, tenant/product/role/user management and profile | Authentication endpoints plus `tenants`, `products`, `roles`, `role-requests`, `users` |
| 3. Super Admin Auth | Email/phone login; edit username/email; change password | Login accepts `identifier` and `password`; profile accepts username/email/phone; password change requires current and new password |
| 4. Tenant Management | Search/filter/create/edit/delete tenants; manage their categories/brands; password-confirmed deletion | `tenants?search=&status=&type=`, `categories?tenant_id=`, `brands?tenant_id=`; admin DELETE requests require the acting admin's `admin_password` |
| 5. Roles Management | Search/create/edit/delete role configurations, password-confirmed deletion, approve/reject requests | `roles`, `role-requests`, `role-requests/{id}/approve`, `role-requests/{id}/reject` |
| 6. User Management | Search, role/status filters, user details, role change, delete, ban/unban; admin-password checks | `users?search=&role_id=&status=`, `users/{id}`, `change-role`, `ban`, `unban`; change-role, ban and delete require `admin_password` |

## Corrections to the diagrams

1. **Shop Owner:** email/phone and password are login input fields, not independent user goals. Show one **Log in** use case and describe those fields in its specification. Prefer verbs such as **Manage categories**, **View profile**, and **Change password** over the noun-only ovals. Add a system boundary around the system's use cases, with the actor outside.
2. **Super Admin overview:** the actor and high-level capabilities are clear. Add a system boundary and use consistent action names. Its Product Management detail is absent from the supplied pictures; the implementation uses the catalog CRUD described by the owner diagram, across shops.
3. **Super Admin Auth:** add the Super Admin actor outside the boundary and associate it with the actions. Connect **View profile**, **Edit profile**, and **Change password** as meaningful goals. Move credential fields into the use-case description.
4. **Tenant Management:** replace the **Password** oval with **Confirm admin password**. An `include` arrow from **Delete tenant/category/brand** to that mandatory confirmation is appropriate. Specify whether deleting a shop also deletes its catalog and what happens to its users.
5. **Roles Management:** use the same project/system title as the other diagrams rather than the unexplained “Solace” title. Add the Super Admin actor for configuration/review and a requester actor for **Submit role request**. Define the permissions a role grants and the PENDING/APPROVED/REJECTED lifecycle.
6. **User Management:** add the Super Admin actor and boundary. **Role** and **Status** are filter criteria, so describe them as inputs to **Filter users**. Rename **Users Detail** to **View user details**. Specify what a ban does to an existing login and whether super admins can be modified.

Across the pictures, use `include` for mandatory shared behavior and `extend` for optional behavior inserted at a defined extension point. A CRUD menu hierarchy alone does not establish an `extend` relationship. Search/create/edit/delete can instead be direct actor-associated use cases grouped in a package. Use the conventional lowercase `«include»` and `«extend»` labels consistently.

## Implementation assumptions

- A tenant represents one shop. Each ordinary user has at most one assigned shop and one catalog role. Several owners may share a shop.
- Django's `is_superuser` defines the Super Admin actor. A role name, even “Super Admin,” never grants platform administration.
- Configurable roles currently grant one capability: `can_manage_catalog`. A role with that capability implements the Shop Owner actor. Fine-grained permissions were not specified by these diagrams.
- Authenticated users assigned to active shops can submit role requests and list available roles. They can read only their own requests. Only super admins approve or reject them; each user can have one pending request.
- Approval changes the user's catalog role and revokes their API token. Approval and rejection are final; repeated decisions return an error. Approval does not itself require a password because the diagram does not show one.
- Super admins can create users to onboard shop owners. The User Management diagram omits creation, but onboarding requires it. No public registration endpoint is exposed.
- Products have a shop, category, brand, optional product line, name, per-shop SKU, description, price, stock, optional image, and availability status. Currency, serial numbers/IMEIs, variants, suppliers, orders, payments and reporting were not specified and are outside this implementation.
- Brand names, category names/slugs and product SKUs are unique within a shop. Product relationships must point to the same shop. Ownership cannot be changed through catalog edits.
- Inactive shops cannot access catalog APIs. Their users can still log in and maintain their own profile.
- Deletion is permanent. Products protect their referenced categories, brands and product lines from deletion. Delete products first when removing a shop's catalog. Tenant deletion clears user shop assignments; it does not delete user accounts. Assigned/requested roles cannot be deleted until references are removed.
- Super admin deletion of catalog records, including products/product lines, requires password confirmation. Owners can delete their own unreferenced catalog records without that extra check.
- User management cannot delete, ban, unban or reassign super admin accounts, including the acting admin. Unban requires admin authorization but no password, matching image 6.
- API authentication uses one revocable token per account. Password changes, bans, role changes and approved requests invalidate it. There is no token expiration/refresh workflow in the diagrams.

## Source findings and corrections

| Priority | Original finding | Correction |
| --- | --- | --- |
| Critical | Existing APIViews had no explicit permissions; DRF had no restrictive defaults. Anonymous requests could access tenant/catalog data and mutations. | Token authentication and authenticated defaults; explicit Super Admin and CatalogAccess permissions. |
| Critical | Catalog services returned every shop's records, and relationship fields accepted arbitrary shop IDs. | Scoped querysets, derived owner tenant assignment, immutable ownership, and relationship validation on create and partial/full updates. |
| High | Auth, profiles, users, roles and requests were absent. | New accounts app extends the existing Django user with a Profile; existing auth tables and migrations remain in place. |
| High | Product serializer was a placeholder and only ProductLine existed. | Product model, migration, validated serializer and CRUD/search/filter routes. |
| High | Tenant/category/brand deletion and all diagram password confirmations were missing. | DELETE and administration actions with current acting-admin password checks and protected-reference errors. |
| High | CategorySerializer allowed an omitted/null tenant although the model required it. | Shop-owner tenant is derived; super admins must supply a tenant; null is rejected before saving. |
| Medium | Global category/brand uniqueness prevented different shops using the same name. | Forward migrations introduce per-shop database constraints and validation. |
| Medium | IDs were generated by reading the lexicographically highest row, allowing concurrent collisions, overflow errors and reuse after deletion. | A persistent, transaction-locked sequence bootstraps from numeric legacy suffixes; existing IDs and formats are retained. |
| Medium | DEBUG was an uncast string; ALLOWED_HOSTS was empty; a second database configuration overwrote the first. | Explicit boolean handling with DJANGO_DEBUG override, configurable hosts, one validated DB_ENGINE choice. Removed the obsolete commented secret. |
| Medium | Missing media configuration and no API behavior tests. | Media settings, development image serving and 17 workflow tests on SQLite and PostgreSQL. |

The former repeated APIViews are replaced inside the existing apps. Original service modules remain as internal ORM helpers and are not authorization boundaries. API changes preserve the `{code, message, source, data}` JSON envelope, add pagination metadata and field errors, and use HTTP 204 for successful deletion.

## Validation and remaining operational boundaries

- 17 workflow tests passed against both an in-memory SQLite database and a separate disposable PostgreSQL database.
- Django system checks and `makemigrations --check --dry-run` passed.
- The read-only `check_shop_data` command passed against the configured existing database before upgrade.
- Tests cover role and tenant workflows, authentication/revocation, cross-shop reads/writes/deletes, product relationship validation, protected deletion, password confirmation, login throttling and wire response compatibility.
- Parallel transaction stress testing, deployment configuration and frontend integration were not performed. PostgreSQL tests exercise transactions but are not concurrent load tests.
- Existing owners must receive explicit shop and role assignments. The migration cannot infer ownership from the supplied pictures or legacy schema.
- The pre-existing historical brand migration `0002` uses a hard-coded tenant default of `1`. It was already applied in this database and was preserved. For a different legacy database, audit unassigned brands before applying that historical migration.
- Production token traffic must use HTTPS. Configure media hosting separately in production. The default login throttle uses Django's local cache; a deployment with multiple workers needs a shared cache and gateway rate limiting.

Implementation references: [Django: extending the existing User](https://docs.djangoproject.com/en/6.0/topics/auth/customizing/#extending-the-existing-user-model) and [DRF token authentication](https://www.django-rest-framework.org/api-guide/authentication/#tokenauthentication).
