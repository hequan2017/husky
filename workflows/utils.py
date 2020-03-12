# -*- coding: utf-8 -*-
from workflows.models import Workflow
from workflows.models import StateObjectUserRelation
from workflows.models import WorkflowStateEvent
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Group

import datetime


def get_approve_user_by_state_name(state_name):
    """
    根据审批节点的名称获取审批用户
    如：审批节点名称为“测试”，则查找角色名称为“测试cmdb”下的用户
    """
    sso_role_name = state_name + 'cmdb'
    sso_role = Group.objects.get(name=sso_role_name)
    if not sso_role:
        raise Exception('查询审批角色 {} 失败，请联系管理员！'.format(sso_role_name))
    return sso_role.user_set.all()


def recursive_latter_state(curr_state, chain_list):
    """
    递归获取后续审批节点
    return [
        {
            'state': state_obj1,
            'users': [user_obj1, user_obj2]
        },
        {
            'state': state_obj2,
            'users': [user_obj3, user_obj4]
        }
    ]
    """
    chain_list.append(
        {
            'state': curr_state,
            'users': [] if curr_state.name == '完成' else get_approve_user_by_state_name(curr_state.name),
            'approve_result': ''
        }
    )
    if curr_state.get_latter_state():
        return recursive_latter_state(curr_state.get_latter_state(), chain_list)
    else:
        return chain_list


def get_workflow_chain(workflow_id):
    """生成审批链"""
    workflow = Workflow.objects.get(pk=workflow_id)
    chain_list = []
    return recursive_latter_state(curr_state=workflow.init_state, chain_list=chain_list)


def get_sor(state, obj):
    """根据state和obj从StateObjectUserRelation中获取一条记录"""

    ctype = ContentType.objects.get_for_model(obj)
    try:
        sor = StateObjectUserRelation.objects.get(content_type=ctype, object_id=obj.id, state=state)
    except StateObjectUserRelation.DoesNotExist:
        return None
    return sor


def init_workflow(workflow, obj, wse):
    """
    初始化工单：
    1. 创建工单整个生命周期经历的状态链，及每个状态对应的审批人
    2. 关联初始审批节点的审批人
    """
    # 创建工单整个生命周期经历的状态链，及每个状态对应的审批人
    chain_list = get_workflow_chain(workflow.id)
    for chain in chain_list:
        sor = StateObjectUserRelation.objects.create(content_object=obj, state=chain['state'])
        if chain['state'].name != '完成':
            sor.users.add(*chain['users'])
    # 关联初始审批节点的审批人
    relate_approve_user_to_wse(state=workflow.init_state, obj=obj, wse=wse)


def relate_approve_user_to_wse(state, obj, wse):
    """审批事件关联审批用户"""
    sor = get_sor(state=state, obj=obj)
    if sor:
        users = tuple(sor.users.all())
        wse.users.add(*users)


def check_approve_perm(wse, approve_user):
    """检查流程事件当前状态是否允许审批，提交审批人是否有权限审批"""
    if not wse.is_current:
        return False, '流程事件wse id = {}，当前状态不允许审批'.format(wse.id)
    if approve_user not in wse.users.all():
        return False, '您没有权限审批'
    return True, '检查通过'


def get_approved_user(obj, next_state_user):
    """根据workflow和申请的obj
    从state或者sor中获取所有的需要审批的用户，如果之前的用户已经审批过，返回用户
    不然，返回None
    """

    ctype = ContentType.objects.get_for_model(obj)
    list_wse = WorkflowStateEvent.objects.filter(content_type=ctype, object_id=obj.id)
    for wse in list_wse:
        if wse.approve_user in next_state_user:
            return wse.approve_user
    return None


def do_transition(wse, select, opinion, approve_user):
    """流程流转"""
    success = True
    msg = 'ok'
    new_wse = ''
    try:
        if select == '同意':
            # 创建新的流程事件
            transition = wse.state.transition.get(condition=select)
            new_wse = WorkflowStateEvent.objects.create(content_object=wse.content_object, state=transition.destination,
                                                        create_time=wse.create_time, creator=wse.creator,
                                                        title=wse.title, is_current=True, opinion=opinion)
            # 当前的流程事件设置为已经审批过
            wse.is_current = False
            wse.state_value = transition.condition
            wse.approve_user = approve_user
            wse.approve_time = datetime.datetime.now()
            wse.opinion = opinion
            wse.save()

            # 如果下一个审批节点的审批用户还是自己
            # 或者是下一个节点审批人是工单发起人自身
            # 或者是下一个节点的审批用户已经审批过之前的节点
            next_state_user = []
            sor = get_sor(state=new_wse.state, obj=new_wse.content_object)
            if sor:
                next_state_user = sor.users.all()

            if approve_user in next_state_user:
                success, msg, new_wse = do_transition(new_wse, select, opinion, approve_user)
            elif new_wse.creator in next_state_user:
                success, msg, new_wse = do_transition(new_wse, select, opinion, new_wse.creator)
            else:
                approved_user = get_approved_user(new_wse.content_object, next_state_user)
                if approved_user:
                    success, msg, new_wse = do_transition(new_wse, select, opinion, approve_user)

        elif select == '拒绝':
            # 如果拒绝，则流程终止，不再创建新的流程事件
            wse.approve_user = approve_user
            wse.state_value = select
            wse.opinion = opinion
            wse.approve_time = datetime.datetime.now()
            wse.save()
            new_wse = wse
        else:
            raise Exception('未知的审批选项')

    except Exception as e:
        success = False
        msg = str(e)
    finally:
        return success, msg, new_wse


def get_workflow_chain_with_wse(wse):
    """根据流程事件wse生成审批链，包括每个审批节点的审批选项（同意、拒绝、审批中）"""
    wse_objs = wse.content_object.wse.all()
    active = wse_objs.count()
    # 当前的审批进度链
    current_chain = [{'state': wse.state, 'users': wse.users.all(), 'approve_result': wse.get_approve_result()} for wse
                     in wse_objs]
    # 整个审批过程的审批链
    common_chain = get_workflow_chain(wse.content_object.workflow.id)
    if len(current_chain) == len(common_chain):
        return active, current_chain
    # 当前审批链与整个审批链进行对比
    for curr_ch in current_chain:
        for com_ch in common_chain:
            if curr_ch['state'] == com_ch['state']:
                com_ch['approve_result'] = curr_ch['approve_result']
                break
    return active, common_chain


def get_approve_pending_cnt(user):
    """获取用户的待审批工单数量"""
    pending_cnt = len([wse for wse in WorkflowStateEvent.objects.filter(is_current=True) if
                       user in wse.get_current_state_approve_user_list()
                       and wse.state_value is None])
    return pending_cnt
