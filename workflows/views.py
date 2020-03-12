
from rest_framework import permissions
from rest_framework.views import APIView
from django.http import JsonResponse
from django.db import IntegrityError
from django.db import transaction
from django.db.models import Q
from workflows.models import Workflow
from workflows.models import DevelopVersionWorkflow
from workflows.models import WorkflowStateEvent
from workflows.utils import init_workflow
from workflows.utils import check_approve_perm
from workflows.utils import do_transition
from workflows.utils import relate_approve_user_to_wse
from workflows.utils import get_workflow_chain
from workflows.utils import get_workflow_chain_with_wse
from workflows.utils import get_approve_pending_cnt



import json


class WorkflowSubmit(APIView):
    """
    工单提交
    :param: {
        'workflow_id': 1,          # 流程id
        'apply_form_data': {       # 申请表单内容
            ...
        },
    }
    """
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, version):
        result = {
            'code': 0,
            'msg': '请求成功',
            'data': {}
        }
        try:
            with transaction.atomic():
                # 校验操作权限
                # if not check_user_sso_perm(request.user, 'workflows.workflow_submit'):
                #     raise PermissionError
                # pass

                raw_data = request.data
                workflow_abbr = raw_data.get('workflow_abbr', '')
                workflow = Workflow.objects.get(abbr=workflow_abbr)
                workflow_abbr = workflow.abbr

                # 发版申请
                if workflow_abbr == 'develop_version':
                    title = raw_data.get('title')
                    test_content = raw_data.get('test_content', '')
                    dev_content = raw_data.get('dev_content', '')
                    # 保存申请单内容
                    obj = DevelopVersionWorkflow.objects.create(
                        title=title,
                        creator=request.user,
                        workflow=workflow,
                        test_content=test_content,
                        dev_content=dev_content
                    )
                    # 创建流程事件
                    wse = WorkflowStateEvent.objects.create(
                        content_object=obj, create_time=obj.create_time, creator=request.user, title=obj.title,
                        state=workflow.init_state, is_current=True)
                    # 初始化工单流
                    init_workflow(workflow, obj, wse)

        except PermissionError:
            result = {
                'code': 403,
                'msg': '权限受限',
                'data': {}
            }
        except Workflow.DoesNotExist as e:
            result = {
                'code': 403,
                'msg': str(e),
                'data': {}
            }
        except IntegrityError:
            result = {
                'code': 200,
                'msg': '记录重复',
                'data': {}
            }
        except Exception as e:
            result = {
                'code': 500,
                'msg': str(e),
                'data': {}
            }
        finally:
            return JsonResponse(result)


class WorkflowApprove(APIView):
    """
    工单审批
    :param: {
        'wse_id': 2,                # 必选，审批的流程事件id
        'select': '同意',           # 必选，审批选项
        'opinion': '意见',          # 非必选，审批文字意见
        'approve_form_data': {      # 非必选，审批表单内容
            ...
        }
    }
    """
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, version):
        result = {
            'code': 0,
            'msg': '请求成功',
            'data': {}
        }
        try:
            with transaction.atomic():
                approve_user = request.user
                raw_data = request.data
                wse_id = raw_data.get('wse_id')
                wse = WorkflowStateEvent.objects.get(pk=wse_id)
                dev_content = raw_data.get('dev_content', '')
                code_merge = raw_data.get('code_merge', '')
                # 如果有研发人员填写内容，则需要保存
                if dev_content:
                    wse.content_object.dev_content = dev_content
                if code_merge:
                    wse.content_object.code_merge = code_merge
                wse.content_object.save(update_fields=['dev_content', 'code_merge'])
                # 审批权限检验
                success, msg = check_approve_perm(wse, approve_user)
                if not success:
                    raise Exception(msg)
                # 流程流转
                select = raw_data.get('select')
                opinion = raw_data.get('opinion', None)
                success, msg, new_wse = do_transition(wse, select, opinion, approve_user)
                if success:
                    # 关联新审批人
                    relate_approve_user_to_wse(new_wse.state, new_wse.content_object, new_wse)
                    if new_wse.users.all():
                        # 发送钉钉通知给下一批审批人员
                        pass
                    else:
                        # 工单审批完成，继续下一步操作
                        pass
                else:
                    raise Exception(msg)

        except WorkflowStateEvent.DoesNotExist as e:
            result = {
                'code': 500,
                'msg': str(e),
                'data': {}
            }
        except PermissionError:
            result = {
                'code': 403,
                'msg': '权限受限',
                'data': {}
            }
        except IntegrityError:
            result = {
                'code': 200,
                'msg': '记录重复',
                'data': {}
            }
        except Exception as e:
            result = {
                'code': 500,
                'msg': str(e),
                'data': {}
            }
        finally:
            return JsonResponse(result)


class CheckValidTitle(APIView):
    """
    检查工单标题是否有效，相同类型申请标题必须唯一
    """
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, version):
        result = {
            'code': 0,
            'msg': '请求成功',
            'data': {
                'is_valid': True,
            }
        }
        try:
            raw_data = request.data
            workflow_abbr = raw_data.get('workflow_abbr')
            title = raw_data.get('title', '')

            if workflow_abbr == 'develop_version':
                if DevelopVersionWorkflow.objects.filter(title=title):
                    result['data']['is_valid'] = False

        except PermissionError:
            result = {
                'code': 403,
                'msg': '权限受限',
                'data': {}
            }
        except Exception as e:
            result = {
                'code': 500,
                'msg': str(e),
                'data': {}
            }
        finally:
            return JsonResponse(result)


class GetApproveChain(APIView):
    """
    获取工单审批链
    """

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, version):
        result = {
            'code': 0,
            'msg': '请求成功',
            'data': {
                'chain': [],
                'active': 0
            }
        }
        try:
            raw_data = request.data
            wse_id = raw_data.get('wse_id', '')
            # 如果有传入wse_id，则根据wse_id生成审批链，并计算当前审批链的状态
            if wse_id:
                wse = WorkflowStateEvent.objects.get(pk=wse_id)
                active, chain = get_workflow_chain_with_wse(wse)
                chain = [
                    {
                        'title': c['state'].name,
                        'description': c['approve_result'] if c['approve_result'] else ', '.join(
                            [u.username for u in c['users']])
                    } for c in chain
                ]

                result['data']['active'] = active
                result['data']['chain'] = chain

            # 否则使用通用方法获取
            else:
                workflow_abbr = raw_data.get('workflow_abbr', '')
                workflow = Workflow.objects.get(abbr=workflow_abbr)
                chain = get_workflow_chain(workflow.id)
                chain = [
                            {
                                'title': c['state'].name,
                                'description': '审批人：' + ', '.join([u.username for u in c['users']])
                            } for c in chain if c['state'].name != '完成'
                        ] + [
                            {
                                'title': c['state'].name, 'description': ', '.join([u.username for u in c['users']])
                            } for c in chain if c['state'].name == '完成'
                        ]
                result['data']['chain'] = chain

        except PermissionError:
            result = {
                'code': 403,
                'msg': '权限受限',
                'data': {}
            }
        except Exception as e:
            result = {
                'code': 500,
                'msg': str(e),
                'data': {}
            }
        finally:
            return JsonResponse(result)


class ListMyApplied(APIView):
    """我的已申请列表数据"""

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, version):
        result = {
            'code': 0,
            'msg': '请求成功',
            'data': {
                'columns': [],
                'row_data': [],
                'total': 0
            }
        }
        try:
            raw_data = request.data
            pagination = raw_data.get('pagination', {})
            current_page = pagination.get('currentPage', 1)
            page_size = pagination.get('pageSize', 10)
            table_filter = raw_data.get('tableFilter', {})
            whole_search = table_filter.get('wholeSearch', '')
            workflowFilterValue = table_filter.get('workflowFilterValue', [])

            # 拼接筛选条件
            sub_query_and = Q()
            sub_query_or = Q()
            if whole_search:
                sub_query_or.add(Q(title__icontains=whole_search), Q.OR)
                sub_query_or.add(Q(creator__username__icontains=whole_search), Q.OR)
                sub_query_or.add(Q(state__name__icontains=whole_search), Q.OR)
                sub_query_or.add(Q(develop_version__workflow__name__icontains=whole_search), Q.OR)
            sub_query = sub_query_and & sub_query_or

            # 获取表头
            result['data']['columns'] = [
                {'title': '工单类型', 'key': 'workflow'},
                {'title': '工单标题', 'key': 'title', 'showOverflowTooltip': True},
                {'title': '创建时间', 'key': 'create_time'},
                {'title': '申请人', 'key': 'creator'},
                {'title': '审批节点', 'key': 'state'},
                {'title': '审批状态', 'key': 'state_value'},
            ]
            # 获取所有数据行
            row_data = [
                wse.show_apply_history() for wse in
                WorkflowStateEvent.objects.filter(creator=request.user, is_current=True).filter(sub_query).order_by(
                    '-create_time')
            ]
            # 工单类型筛选
            if workflowFilterValue:
                row_data = [row for row in row_data if row['workflow_id'] in workflowFilterValue]

            total = len(row_data)
            result['data']['total'] = total

            # 分页
            row_data = row_data[(current_page - 1) * page_size:current_page * page_size]
            result['data']['row_data'] = row_data

        except PermissionError:
            result = {
                'code': 403,
                'msg': '权限受限',
                'data': {}
            }
        except Exception as e:
            result = {
                'code': 500,
                'msg': str(e),
                'data': {}
            }
        finally:
            return JsonResponse(result)


class ListWorkflow(APIView):
    """工单类型列表数据"""

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, version):
        result = {
            'code': 0,
            'msg': '请求成功',
            'data': {
                'workflow': [],
            }
        }
        try:
            result['data']['workflow'] = [
                {'text': w.name, 'value': w.id}
                for w in Workflow.objects.all()
            ]

        except PermissionError:
            result = {
                'code': 403,
                'msg': '权限受限',
                'data': {}
            }
        except Exception as e:
            result = {
                'code': 500,
                'msg': str(e),
                'data': {}
            }
        finally:
            return JsonResponse(result)


class WorkflowDetail(APIView):
    """工单详情数据"""

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, version):
        result = {
            'code': 0,
            'msg': '请求成功',
            'data': {
                'workflowDetail': {},
            }
        }
        try:
            raw_data = request.data
            wse_id = raw_data.get('wse_id')
            wse = WorkflowStateEvent.objects.get(pk=wse_id)
            obj = wse.content_object
            workflow = wse.content_object.workflow

            if workflow.abbr == 'develop_version':
                result['data']['workflowDetail'] = {
                    'wse_id': wse_id,
                    'title': obj.title,
                    'test_content': obj.test_content,
                    'dev_content': obj.dev_content,
                    'code_merge': obj.is_code_merge(),
                }

        except PermissionError:
            result = {
                'code': 403,
                'msg': '权限受限',
                'data': {}
            }
        except Exception as e:
            result = {
                'code': 500,
                'msg': str(e),
                'data': {}
            }
        finally:
            return JsonResponse(result)


class ListMyApprovePending(APIView):
    """我的待审批列表数据"""

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, version):
        result = {
            'code': 0,
            'msg': '请求成功',
            'data': {
                'columns': [],
                'row_data': [],
                'total': 0
            }
        }
        try:
            raw_data = request.data
            pagination = raw_data.get('pagination', {})
            current_page = pagination.get('currentPage', 1)
            page_size = pagination.get('pageSize', 10)
            table_filter = raw_data.get('tableFilter', {})
            whole_search = table_filter.get('wholeSearch', '')
            workflowFilterValue = table_filter.get('workflowFilterValue', [])

            # 拼接筛选条件
            sub_query_and = Q()
            sub_query_or = Q()
            if whole_search:
                sub_query_or.add(Q(title__icontains=whole_search), Q.OR)
                sub_query_or.add(Q(creator__username__icontains=whole_search), Q.OR)
                sub_query_or.add(Q(state__name__icontains=whole_search), Q.OR)
                sub_query_or.add(Q(develop_version__workflow__name__icontains=whole_search), Q.OR)
            sub_query = sub_query_and & sub_query_or

            # 获取表头
            result['data']['columns'] = [
                {'title': '工单类型', 'key': 'workflow'},
                {'title': '工单标题', 'key': 'title', 'showOverflowTooltip': True},
                {'title': '创建时间', 'key': 'create_time'},
                {'title': '申请人', 'key': 'creator'},
                {'title': '审批节点', 'key': 'state'},
                {'title': '审批状态', 'key': 'state_value'},
            ]
            # 获取所有数据行
            row_data = [
                wse.show_apply_history() for wse in
                WorkflowStateEvent.objects.filter(sub_query).filter(is_current=True).order_by('-create_time')
                if request.user in wse.get_current_state_approve_user_list()
                   and wse.state_value is None
            ]
            if workflowFilterValue:
                row_data = [row for row in row_data if row['workflow_id'] in workflowFilterValue]

            total = len(row_data)
            result['data']['total'] = total

            # 分页
            row_data = row_data[(current_page - 1) * page_size:current_page * page_size]
            result['data']['row_data'] = row_data

        except PermissionError:
            result = {
                'code': 403,
                'msg': '权限受限',
                'data': {}
            }
        except Exception as e:
            result = {
                'code': 500,
                'msg': str(e),
                'data': {}
            }
        finally:
            return JsonResponse(result)


class ListMyApproved(APIView):
    """我的审批记录列表数据"""
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, version):
        result = {
            'code': 0,
            'msg': '请求成功',
            'data': {
                'columns': [],
                'row_data': [],
                'total': 0
            }
        }
        try:
            raw_data = request.data
            pagination = raw_data.get('pagination', {})
            current_page = pagination.get('currentPage', 1)
            page_size = pagination.get('pageSize', 10)
            table_filter = raw_data.get('tableFilter', {})
            whole_search = table_filter.get('wholeSearch', '')
            workflowFilterValue = table_filter.get('workflowFilterValue', [])

            # 拼接筛选条件
            sub_query_and = Q()
            sub_query_or = Q()
            if whole_search:
                sub_query_or.add(Q(title__icontains=whole_search), Q.OR)
                sub_query_or.add(Q(creator__username__icontains=whole_search), Q.OR)
                sub_query_or.add(Q(state__name__icontains=whole_search), Q.OR)
                sub_query_or.add(Q(develop_version__workflow__name__icontains=whole_search), Q.OR)
            sub_query = sub_query_and & sub_query_or

            # 获取表头
            result['data']['columns'] = [
                {'title': '工单类型', 'key': 'workflow'},
                {'title': '工单标题', 'key': 'title', 'showOverflowTooltip': True},
                {'title': '审批时间', 'key': 'approve_time'},
                {'title': '申请人', 'key': 'creator'},
                {'title': '审批节点', 'key': 'state'},
                {'title': '审批状态', 'key': 'state_value'},
            ]
            # 获取所有数据行
            row_data = [
                wse.show_apply_history() for wse in
                WorkflowStateEvent.objects.filter(approve_user=request.user).filter(sub_query).order_by(
                    '-approve_time')
            ]
            # 工单类型筛选
            if workflowFilterValue:
                row_data = [row for row in row_data if row['workflow_id'] in workflowFilterValue]

            total = len(row_data)
            result['data']['total'] = total

            # 分页
            row_data = row_data[(current_page - 1) * page_size:current_page * page_size]
            result['data']['row_data'] = row_data

        except PermissionError:
            result = {
                'code': 403,
                'msg': '权限受限',
                'data': {}
            }
        except Exception as e:
            result = {
                'code': 500,
                'msg': str(e),
                'data': {}
            }
        finally:
            return JsonResponse(result)


class GetApprovePendingCnt(APIView):
    """获取请求用户待审批工单数量数据"""

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, version):
        result = {
            'code': 0,
            'msg': '请求成功',
            'data': {
                'pending_cnt': 0,
            }
        }
        try:
            pending_cnt = get_approve_pending_cnt(request.user)
            result['data']['pending_cnt'] = pending_cnt

        except PermissionError:
            result = {
                'code': 403,
                'msg': '权限受限',
                'data': {}
            }
        except Exception as e:
            result = {
                'code': 500,
                'msg': str(e),
                'data': {}
            }
        finally:
            return JsonResponse(result)