from django.contrib import admin
from workflows.models import State, Transition, Workflow


class WorkflowAdmin(admin.ModelAdmin):
    fields = ('name', 'description', 'abbr', 'init_state')
    list_display = ('name', 'description', 'abbr', 'init_state')


class StateAdmin(admin.ModelAdmin):
    fields = ('name', 'workflow', 'transition')
    list_display = ('name', 'workflow')


class TransitionAdmin(admin.ModelAdmin):
    fields = ('name', 'workflow', 'destination', 'condition')
    list_display = ('name', 'workflow', 'destination', 'condition')


admin.site.register(State, StateAdmin)
admin.site.register(Transition, TransitionAdmin)
admin.site.register(Workflow, WorkflowAdmin)