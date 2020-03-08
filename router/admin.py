from django.contrib import admin
from django.contrib.auth.models import Permission
from router.models import UserMenu
from router.models import UserRouter


class PermissionAdmin(admin.ModelAdmin):
    fields = ['name', 'content_type', 'codename']
    list_display = ['name', 'content_type', 'codename']
    list_per_page = 20
    search_fields = ('name', 'codename')


class UserMenuAdmin(admin.ModelAdmin):
    fields = ['index', 'path', 'parent', 'title', 'icon', 'permission']
    list_display = ['index', 'path', 'parent', 'title', 'icon', 'permission']
    ordering = ('index',)
    list_per_page = 20
    search_fields = ('path', 'title')
    list_display_links = ('title',)


class UserRouterAdmin(admin.ModelAdmin):
    fields = ['path', 'name', 'title', 'auth', 'component', 'permission']
    list_display = ['path', 'name', 'title', 'auth', 'component', 'permission']
    list_per_page = 20
    search_fields = ('path', 'title', 'name')
    list_display_links = ('title',)


admin.site.register(Permission, PermissionAdmin)
admin.site.register(UserMenu, UserMenuAdmin)
admin.site.register(UserRouter, UserRouterAdmin)