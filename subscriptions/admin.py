"""Admin views for the Flexible Subscriptions app."""
from django.contrib import admin
from rangefilter.filter import DateRangeFilter

from subscriptions import models
from subscriptions.conf import SETTINGS


class PlanCostInline(admin.TabularInline):
    """Inline admin class for the PlanCost model."""
    model = models.PlanCost
    fields = (
        'slug',
        'recurrence_period',
        'recurrence_unit',
        'currency',
        'cost',
    )
    extra = 0


class SubscriptionPlanAdmin(admin.ModelAdmin):
    """Admin class for the SubscriptionPlan model."""
    fields = (
        'plan_name',
        'slug',
        'plan_description',
        'group',
        'tags',
        'grace_period',
    )
    inlines = [PlanCostInline]
    list_display = (
        'plan_name',
        'group',
        'display_tags',
    )
    prepopulated_fields = {'slug': ('plan_name',)}


class UserSubscriptionAdmin(admin.ModelAdmin):
    """Admin class for the UserSubscription model."""
    fields = (
        'user',
        'subscription',
        'date_billing_start',
        'date_billing_end',
        'date_billing_last',
        'date_billing_next',
        'active',
        'cancelled',
    )
    list_display = (
        'user',
        'subscription',
        'date_billing_last',
        'date_billing_next',
        'active',
        'cancelled',
    )
    list_filter = (
        'user',
        'subscription',
        ('date_billing_last', DateRangeFilter),
        ('date_billing_next', DateRangeFilter),
    )


class TransactionAdmin(admin.ModelAdmin):
    """Admin class for the SubscriptionTransaction model."""
    list_display = (
        'user',
        'subscription',
        'date_transaction',
        'amount',
    )
    list_filter = (
        'user',
        'subscription',
        ('date_transaction', DateRangeFilter),
    )


class PlanListDetailInline(admin.StackedInline):
    """Admin class for the PlanListDetail model."""
    model = models.PlanListDetail
    fields = (
        'plan',
        'html_content',
        'subscribe_button_text',
        'order',
    )
    extra = 1


class PlanListAdmin(admin.ModelAdmin):
    """Admin class for plan lists"""
    fields = (
        'title',
        'slug',
        'subtitle',
        'header',
        'footer',
        'active',
    )
    inlines = [PlanListDetailInline]
    list_display = (
        'title',
        'slug',
        'active',
    )


if SETTINGS['enable_admin']:
    admin.site.register(models.PlanList, PlanListAdmin)
    admin.site.register(models.SubscriptionPlan, SubscriptionPlanAdmin)
    admin.site.register(models.UserSubscription, UserSubscriptionAdmin)
    admin.site.register(models.SubscriptionTransaction, TransactionAdmin)
    admin.site.register(models.PaymentCurrency)
