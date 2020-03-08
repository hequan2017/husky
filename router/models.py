from django.db import models
from django.contrib.auth.models import Permission


class UserMenu(models.Model):
    """用户菜单"""
    index = models.IntegerField(default=999, verbose_name=u'菜单索引', help_text=u'决定菜单显示顺序')
    path = models.CharField(max_length=50, null=True, blank=True, verbose_name=u'菜单路径')
    title = models.CharField(max_length=20, verbose_name=u'菜单名称')
    icon = models.CharField(max_length=10, null=True, blank=True, verbose_name=u'菜单图标')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children',
                               verbose_name=u'父级菜单')
    permission = models.ForeignKey(Permission, null=True, blank=True, on_delete=models.SET_NULL, verbose_name=u'菜单关联权限')

    class Meta:
        db_table = 'users_menu'
        verbose_name = u'用户菜单'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.title

    def get_vue_menu(self):
        """
        获取vue菜单需要的字典格式：       一级菜单：{'index': 1, title': '服务器资源', 'icon': 'desktop', 'children': []}
        二级菜单：{'index': 2, 'title': '服务器资源', 'children': []}
        ...
        叶子菜单：{'index': 10, 'title': '服务器资源', 'path': '<与路由的path对应>'}
        """
        if self.children.all():
            if self.icon:
                return {'index': self.index, 'title': self.title, 'icon': self.icon, 'children': {}}
            else:
                return {'index': self.index, 'title': self.title, 'children': {}}
        else:
            return {'index': self.index, 'title': self.title, 'path': self.path}

    def is_root_menu(self):
        """是否根节点菜单"""
        if not self.parent:
            return True
        return False

    def is_leaf_menu(self):
        """是否叶子节点菜单"""
        if not self.children.all():
            return True
        return False

    def get_self_parent(self, node):
        """递归获取父级节点"""
        if not node.parent:
            return node
        else:
            return self.get_self_parent(node.parent)

    def get_root_node(self):
        """获取根节点对象，即最顶层的菜单"""
        if not self.parent:
            return self
        else:
            return self.get_self_parent(self.parent)

    def _get_all_parents(self, node, parent_nodes):
        """递归查找所有父级节点"""
        if node.parent:
            parent_nodes.add(node.parent)
            return self._get_all_parents(node.parent, parent_nodes)
        else:
            return parent_nodes

    def get_all_parent_nodes(self, own=False):
        """获取所有父级节点对象的列表，参数own控制"列表中是否加入自身"""
        parent_nodes = set()
        if own:
            parent_nodes.add(self)
        if self.parent:
            parent_nodes.add(self.parent)
            return self._get_all_parents(self.parent, parent_nodes)
        return parent_nodes


class UserRouter(models.Model):
    """用户路由"""
    path = models.CharField(max_length=50, verbose_name=u'路由路径')
    name = models.CharField(max_length=30, verbose_name=u'路由英文名称')
    title = models.CharField(max_length=30, verbose_name=u'路由中文标题')
    auth = models.BooleanField(default=True, verbose_name=u'是否需要验证')
    component = models.CharField(max_length=50, verbose_name=u'路由关联的页面组件')
    permission = models.ForeignKey(Permission, null=True, blank=True, on_delete=models.SET_NULL, verbose_name=u'路由关联权限')

    class Meta:
        db_table = 'users_router'
        verbose_name = u'用户路由'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.title

    def get_vue_router_dict(self):
        """组装vue路由字典"""
        return {
            'path': self.path,
            'name': self.name,
            'meta': {
                'title': self.title,
                'auth': self.auth
            },
            'component': self.component
        }
