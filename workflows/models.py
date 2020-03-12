from django.db import models
from system.models import Users as User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericRelation


class Workflow(models.Model):
    """
    工单类型表
    """
    name = models.CharField(max_length=100, unique=True, verbose_name=u'流程名')
    abbr = models.CharField(max_length=20, unique=True, default='', verbose_name=u'缩写')
    description = models.CharField(max_length=100, default='', verbose_name=u'工单的描述')
    init_state = models.ForeignKey("State", on_delete=models.SET_NULL, related_name='workflow_init_state', blank=True,
                                   null=True, verbose_name=u'初始状态')

    class Meta:
        db_table = 'workflow'
        verbose_name = u'工单类型表'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class State(models.Model):
    """状态表
    关联到对应的流程
    常见的状态:
    测试审核，研发审核，运维审核，完成
    """
    name = models.CharField(max_length=100, verbose_name=u'状态名')
    workflow = models.ForeignKey("Workflow", on_delete=models.PROTECT, verbose_name=u'对应的流程名')
    transition = models.ManyToManyField("Transition", verbose_name=u'状态转化')

    class Meta:
        db_table = 'workflow_state'
        verbose_name = u'状态表'
        verbose_name_plural = verbose_name

    def get_pre_state(self):
        try:
            return self.transition.get(condition='拒绝').destination
        except:
            return None

    def get_latter_state(self):
        try:
            return self.transition.get(condition='同意').destination
        except:
            return None

    def __str__(self):
        return self.workflow.name + ':' + self.name


class StateObjectUserRelation(models.Model):
    """obj和状态和的用户关系
    """
    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    state = models.ForeignKey("State", on_delete=models.PROTECT, verbose_name=u'关联状态')
    users = models.ManyToManyField(User, verbose_name=u'关联用户')

    def __str__(self):
        return "%s:%s:%s" % (self.content_type.name, self.object_id, self.state.name)

    class Meta:
        unique_together = ("content_type", "object_id", "state")
        db_table = 'state_object_user'


class Transition(models.Model):
    """流程转化,从一个流程转化到另一个流程
    **Attributes:**
    name
        在流程内一个唯一的转化名称
    workflow
        转化归属的流程，必须是一个流程实例
    destination
        当转化发生后的目标指向状态
    condition
        发生转化的条件
    """
    name = models.CharField(max_length=100, verbose_name=u'转化名称')
    workflow = models.ForeignKey("Workflow", on_delete=models.PROTECT, verbose_name=u'所属的流程')
    destination = models.ForeignKey("State", on_delete=models.PROTECT, related_name='transition_destination',
                                    verbose_name=u'目标状态指向')
    condition = models.CharField(max_length=100, verbose_name=u'发生转化的条件')

    class Meta:
        db_table = 'workflow_transition'
        unique_together = ('workflow', 'name')
        verbose_name = u'状态转化表'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.workflow.name + ':' + self.name


class WorkflowStateEvent(models.Model):
    """流程转化的日志
    记录了每个流程转化到相应的state时的结果
    增加了额外的create_time， creator， title这三个属性
    这三个属性本来是任意申请的必须字段，他们的值都是相同的
    在创建wse的时候，把obj的这三个属性值赋值过来
    这样做的目的是为了在"我的待审批"和"我的审批记录"中可以通过关键字查找
    """
    DING_STATUS = (
        (0, '未发送'),
        (1, '已发送'),
    )
    IS_CANCEL = (
        (0, '未取消'),
        (1, '已取消')
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    state = models.ForeignKey("State", blank=True, null=True, on_delete=models.SET_NULL)
    create_time = models.DateTimeField()
    approve_time = models.DateTimeField(blank=True, null=True)
    creator = models.ForeignKey(User, verbose_name=u'工单发起人', on_delete=models.PROTECT)
    title = models.CharField(max_length=500, verbose_name=u'标题')
    is_current = models.BooleanField(default=False, verbose_name=u'是否为当前状态')
    approve_user = models.ForeignKey(User, related_name='approve_user_user', blank=True, null=True,
                                     verbose_name=u'审批的用户', on_delete=models.PROTECT)
    state_value = models.CharField(max_length=10, blank=True, null=True, verbose_name=u'state的审批值')
    ding_notice = models.IntegerField(choices=DING_STATUS, default=0, verbose_name=u'是否已经发送过钉钉通知')
    opinion = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'审批意见')
    users = models.ManyToManyField(User, related_name='wse_approve_users', verbose_name=u'指定的审批用户,每次审批后从sor中copy')
    is_cancel = models.IntegerField(choices=IS_CANCEL, default=0, verbose_name=u'工单流程是否取消')

    class Meta:
        db_table = 'workflow_state_event'
        verbose_name = u'流程转化的日志'
        verbose_name_plural = verbose_name
        unique_together = ("content_type", "object_id", "state")

    def __str__(self):
        return '%s-%s-%s' % (self.content_object.title, self.state, self.state_value)

    def get_current_state_approve_user_list(self):
        return self.users.all()

    def show_apply_history(self):
        if self.state.name == '完成':
            state_value = '完成'
        else:
            state_value = self.state_value if self.state_value else '审批中'

        return {
            'wse_id': self.id,
            'workflow_id': self.content_object.workflow.id,
            'abbr': self.content_object.workflow.abbr,
            'workflow': self.content_object.workflow.name,
            'title': self.title,
            'create_time': str(self.create_time),
            'approve_time': str(self.approve_time),
            'creator': self.creator.username,
            'state': self.state.name,
            'state_value': state_value
        }

    def get_opinion(self):
        return self.opinion if self.opinion else '未填写'

    def get_approve_result(self):
        if self.state.name == '完成':
            return ''
        else:
            approve_user = self.approve_user.username + ' ' if self.approve_user else ', '.join([u.username for u in self.users.all()])
            state_value = self.state_value + ' ' + str(self.approve_time)[:19] if self.state_value else ' 审批中'
            if state_value == '拒绝':
                state_value += '，原因：' + self.get_opinion()
            return approve_user + state_value


class DevelopVersionWorkflow(models.Model):
    """发版申请单"""
    workflow = models.ForeignKey(Workflow, on_delete=models.PROTECT, verbose_name=u'所属工作流')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name=u'创建时间')
    creator = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=u'申请人')
    title = models.CharField(max_length=100, unique=True, verbose_name=u'标题')
    test_content = models.TextField(default='', verbose_name=u'测试人员填写内容')
    dev_content = models.TextField(default='', verbose_name=u'开发人员填写内容')
    code_merge = models.BooleanField(null=True, blank=True, verbose_name=u'代码是否已合并')
    wse = GenericRelation(WorkflowStateEvent, related_query_name='develop_version')

    class Meta:
        db_table = 'workflow_develop_version'
        verbose_name = u'发版申请单'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.workflow.name + '-' + self.title

    def is_code_merge(self):
        if self.code_merge:
            return '1'
        elif self.code_merge is None:
            return ''
        else:
            return '0'
