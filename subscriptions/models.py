"""Models for the Flexible Subscriptions app."""
from datetime import timedelta
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# Convenience references for units for plan recurrence billing
# ----------------------------------------------------------------------------
ONCE = '0'
SECOND = '1'
MINUTE = '2'
HOUR = '3'
DAY = '4'
WEEK = '5'
MONTH = '6'
YEAR = '7'
RECURRENCE_UNIT_CHOICES = (
    (ONCE, 'once'),
    (SECOND, 'second'),
    (MINUTE, 'minute'),
    (HOUR, 'hour'),
    (DAY, 'day'),
    (WEEK, 'week'),
    (MONTH, 'month'),
    (YEAR, 'year'),
)


class RetryManager(models.Manager):
    def first_try(self):
        return self.get(iteration=1)

    def next(self, current):
        try:
            return self.get(iteration=current+1)
        except ObjectDoesNotExist:
            return None


class PaymentRetry(models.Model):
    iteration = models.PositiveSmallIntegerField()

    retry_offset = models.PositiveSmallIntegerField(
        help_text="Number of days in which the payment is to be retried"
    )

    objects = RetryManager()

    @property
    def pretty_offset(self):
        if self.retry_offset == 0:
            return 'immediately'
        elif self.retry_offset == 1:
            return 'the next day'
        else:
            return 'in {} days'.format(self.retry_offset)

    def __str__(self) -> str:
        return self.pretty_offset

    class Meta:
        verbose_name_plural = 'Payment Retries'


class PlanTag(models.Model):
    """A tag for a subscription plan."""
    tag = models.CharField(
        help_text=_('the tag name'),
        max_length=64,
        unique=True,
    )

    class Meta:
        ordering = ('tag',)

    def __str__(self):
        return self.tag


class SubscriptionPlan(models.Model):
    """Details for a subscription plan."""
    id = models.UUIDField(
        default=uuid4,
        editable=False,
        primary_key=True,
        verbose_name='ID',
    )
    plan_name = models.CharField(
        help_text=_('the name of the subscription plan'),
        max_length=128,
    )
    slug = models.SlugField(
        blank=True,
        help_text=_('slug to reference the subscription plan'),
        max_length=128,
        null=True,
        unique=True,
    )
    plan_description = models.CharField(
        blank=True,
        help_text=_('a description of the subscription plan'),
        max_length=512,
        null=True,
    )
    group = models.ForeignKey(
        Group,
        blank=True,
        help_text=_('the Django auth group for this plan'),
        null=True,
        on_delete=models.SET_NULL,
        related_name='plans',
    )
    tags = models.ManyToManyField(
        PlanTag,
        blank=True,
        help_text=_('any tags associated with this plan'),
        related_name='plans',
    )
    grace_period = models.PositiveIntegerField(
        default=0,
        help_text=_(
            'how many days after the subscription ends before the '
            'subscription expires'
        ),
    )

    class Meta:
        ordering = ('plan_name',)
        permissions = (
            ('subscriptions', 'Can interact with subscription details'),
        )

    def __str__(self):
        return self.plan_name

    def display_tags(self):
        """Displays tags as a string (truncates if more than 3)."""
        if self.tags.count() > 3:
            return '{}, ...'.format(
                ', '.join(tag.tag for tag in self.tags.all()[:3])
            )

        return ', '.join(tag.tag for tag in self.tags.all()[:3])


class PaymentCurrency(models.Model):
    """PaymentCurrency
    custom model for storing and managing currencies
    """
    SIGN_POSITION_CHOICES = [
        ('0', 'Currency and value are surrounded by parentheses.'),
        ('1', 'The sign should precede the value and currency symbol.'),
        ('2', 'The sign should follow the value and currency symbol.'),
        ('3', 'The sign should immediately precede the value.'),
        ('4', 'The sign should immediately follow the value.'),
    ]

    locale = models.CharField(max_length=5)
    currency_symbol = models.CharField(
        max_length=8,
        help_text="The symbol used for this currency."
    )
    int_curr_symbol = models.CharField(
        max_length=8,
        help_text="The symbol used for this currency for international formatting."
    )
    p_cs_precedes = models.BooleanField(
        default=True,
        help_text="Whether the currency symbol precedes positive values"
    )
    n_cs_precedes = models.BooleanField(
        default=True,
        help_text="Whether the currency symbol precedes negative values."
    )
    p_sep_by_space = models.BooleanField(
        default=True,
        help_text="Whether the currency symbol is separated from positive values by a space."
    )
    n_sep_by_space = models.BooleanField(
        default=True,
        help_text="Whether the currency symbol is separated from negative values by a space."
    )
    mon_decimal_point = models.CharField(
        max_length=1,
        help_text="The character used for decimal points."
    )
    mon_thousands_sep = models.CharField(
        max_length=1,
        help_text="The character used for separating groups of numbers."
    )
    mon_grouping = models.PositiveSmallIntegerField(
        default=3,
        help_text="The number of digits per groups."
    )
    frac_digits = models.PositiveSmallIntegerField(
        default=2,
        help_text="The number of digits following the decimal place. Use 0 if this is a non-decimal currency."
    )
    int_frac_digits = models.PositiveSmallIntegerField(
        default=2,
        help_text="The number of digits following the decimal place for international formatting. Use 0 if this is a non-decimal currency."
    )
    positive_sign = models.CharField(
        max_length=1,
        null=True,
        default="",
        help_text="The symbol to use for the positive sign."
    )
    negative_sign = models.CharField(
        max_length=1,
        default="-",
        help_text="The symbol to use for the negative sign."
    )
    p_sign_posn = models.CharField(
        max_length=1,
        choices=SIGN_POSITION_CHOICES,
        default=SIGN_POSITION_CHOICES[0][0],
        help_text="How the positive sign should be positioned relative to the currency symbol and value."
    )
    n_sign_posn = models.CharField(
        max_length=1,
        choices=SIGN_POSITION_CHOICES,
        default=SIGN_POSITION_CHOICES[0][0],
        help_text="How the negative sign should be positioned relative to the currency symbol and value."
    )

    class Meta:
        verbose_name_plural = "Payment Currencies"

    def __str__(self):
        return self.int_curr_symbol


class PlanCostManager():
    def get_basic(self, group):
        """
        Returns the free plan cost for a given group

        Args:
            group (Group): Auth group, defaults to talent

        Returns the appropriate PlanCost
        """
        queryset = self.get_queryset()
        try:
            if not group:
                group, _ = Group.objects.get_or_create(name="Talent")
            return queryset.get(plan__group=group, cost=0)
        except ObjectDoesNotExist:
            return None


class PlanCost(models.Model):
    """Cost and frequency of billing for a plan."""
    id = models.UUIDField(
        default=uuid4,
        editable=False,
        primary_key=True,
        verbose_name='ID',
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        help_text=_('the subscription plan for these cost details'),
        on_delete=models.CASCADE,
        related_name='costs',
    )
    slug = models.SlugField(
        blank=True,
        help_text=_('slug to reference these cost details'),
        max_length=128,
        null=True,
        unique=True,
    )
    recurrence_period = models.PositiveSmallIntegerField(
        default=1,
        help_text=_('how often the plan is billed (per recurrence unit)'),
        validators=[MinValueValidator(1)],
    )
    recurrence_unit = models.CharField(
        choices=RECURRENCE_UNIT_CHOICES,
        default=MONTH,
        max_length=1,
    )
    currency = models.ForeignKey(
        "subscriptions.PaymentCurrency",
        verbose_name=_("currency"),
        on_delete=models.CASCADE,
        null=True
    )
    cost = models.DecimalField(
        blank=True,
        decimal_places=4,
        help_text=_('the cost per recurrence of the plan'),
        max_digits=19,
        null=True,
    )

    active = models.BooleanField(default=True)

    objects = PlanCostManager()

    def __str__(self):
        return '{} @ {} {} {}'.format(
            self.plan.plan_name,
            self.currency.currency_symbol,
            self.cost_as_float,
            self.display_billing_frequency_text
        )

    class Meta:
        ordering = ('recurrence_unit', 'recurrence_period', 'cost',)

    @property
    def display_recurrent_unit_text(self):
        """Converts recurrence_unit integer to text."""
        conversion = {
            ONCE: 'one-time',
            SECOND: 'per second',
            MINUTE: 'per minute',
            HOUR: 'per hour',
            DAY: 'per day',
            WEEK: 'per week',
            MONTH: 'per month',
            YEAR: 'per year',
        }

        return conversion[self.recurrence_unit]

    @property
    def display_billing_frequency_text(self):
        """Generates human-readable billing frequency."""
        conversion = {
            ONCE: 'one-time',
            SECOND: {'singular': 'per second', 'plural': 'seconds'},
            MINUTE: {'singular': 'per minute', 'plural': 'minutes'},
            HOUR: {'singular': 'per hour', 'plural': 'hours'},
            DAY: {'singular': 'per day', 'plural': 'days'},
            WEEK: {'singular': 'per week', 'plural': 'weeks'},
            MONTH: {'singular': 'per month', 'plural': 'months'},
            YEAR: {'singular': 'per year', 'plural': 'years'},
        }

        if self.recurrence_unit == ONCE:
            return conversion[ONCE]

        if self.recurrence_period == 1:
            return conversion[self.recurrence_unit]['singular']

        return 'every {} {}'.format(
            self.recurrence_period,
            conversion[self.recurrence_unit]['plural']
        )

    def next_billing_datetime(self, current):
        """Calculates next billing date for provided datetime.

            Parameters:
                current (datetime): The current datetime to compare
                    against.

            Returns:
                datetime: The next time billing will be due.
        """
        if self.recurrence_unit == SECOND:
            delta = timedelta(seconds=self.recurrence_period)
        elif self.recurrence_unit == MINUTE:
            delta = timedelta(minutes=self.recurrence_period)
        elif self.recurrence_unit == HOUR:
            delta = timedelta(hours=self.recurrence_period)
        elif self.recurrence_unit == DAY:
            delta = timedelta(days=self.recurrence_period)
        elif self.recurrence_unit == WEEK:
            delta = timedelta(weeks=self.recurrence_period)
        elif self.recurrence_unit == MONTH:
            # Adds the average number of days per month as per:
            # http://en.wikipedia.org/wiki/Month#Julian_and_Gregorian_calendars
            # This handle any issues with months < 31 days and leap years
            delta = timedelta(
                days=30.4368 * self.recurrence_period
            )
        elif self.recurrence_unit == YEAR:
            # Adds the average number of days per year as per:
            # http://en.wikipedia.org/wiki/Year#Calendar_year
            # This handle any issues with leap years
            delta = timedelta(
                days=365.2425 * self.recurrence_period
            )
        else:
            # If no recurrence period, no next billing datetime
            return None

        return current + delta

    @property
    def cost_as_float(self):
        """returns a float interpretation of cost"""
        if self.cost:
            return float(self.cost)

        return float(0.0)


class UserSubscriptionManager(models.Manager):
    """Model manager for UserSubscription"""

    def attach_subscription(self, plan_cost: PlanCost, user):
        # attach basic to user
        return UserSubscription.objects.create(
            user=user,
            subscription=plan_cost,
            active=True,
            date_billing_start=timezone.now()
        )

    def failed_renewals(self):
        """
        compiles a set of usersubscriptions with renewal_status=retry

        returns {
            user_subscription: uuid,
            last_payment: id
        }
        """
        queryset = self.filter(
            active=True,
            cancelled=False,
            renewal_status=UserSubscription.RETRYING
        )

        output = []

        # determine if q is for retry based on its retry offset
        for user_subscription in queryset.iterator():
            if user_subscription.for_retry:
                output.append(user_subscription.id)

        return output

    def to_charge(self):
        """selects UserSubscriptions that are due for billing"""
        now = timezone.now()
        queryset = self.filter(
            active=True,
            cancelled=False,
            date_billing_next__lte=now
        ).values_list("id", flat=True)

        return list(queryset)


class UserSubscription(models.Model):
    """Details of a user's specific subscription."""

    RUNNING = 'R'
    RETRYING = 'T'
    FAILED = 'F'

    RENEWAL_CHOICES = (
        (RUNNING, 'Running'),
        (RETRYING, 'Retrying subscription renewal'),
        (FAILED, 'Failed')
    )

    id = models.UUIDField(
        default=uuid4,
        editable=False,
        primary_key=True,
        verbose_name='ID',
    )
    user = models.ForeignKey(
        get_user_model(),
        help_text=_('the user this subscription applies to'),
        null=True,
        on_delete=models.CASCADE,
        related_name='subscriptions',
    )
    subscription = models.ForeignKey(
        PlanCost,
        help_text=_('the plan costs and billing frequency for this user'),
        null=True,
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )
    date_billing_start = models.DateTimeField(
        blank=True,
        help_text=_('the date to start billing this subscription'),
        null=True,
        verbose_name='billing start date',
    )
    date_billing_end = models.DateTimeField(
        blank=True,
        help_text=_('the date to finish billing this subscription'),
        null=True,
        verbose_name='billing start end',
    )
    date_billing_last = models.DateTimeField(
        blank=True,
        help_text=_('the last date this plan was billed'),
        null=True,
        verbose_name='last billing date',
    )
    date_billing_next = models.DateTimeField(
        blank=True,
        help_text=_('the next date billing is due'),
        null=True,
        verbose_name='next start date',
    )
    active = models.BooleanField(
        default=True,
        help_text=_('whether this subscription is active or not'),
    )
    cancelled = models.BooleanField(
        default=False,
        help_text=_('whether this subscription is cancelled or not'),
    )

    renewal_status = models.CharField(
        max_length=1,
        default=RUNNING,
        choices=RENEWAL_CHOICES
    )

    objects = UserSubscriptionManager()

    retry = models.ForeignKey(
        PaymentRetry,
        verbose_name="retry",
        on_delete=models.CASCADE,
        null=True,
        default=None
    )

    @property
    def transaction_ago(self) -> int:
        """transaction_ago
        calculates the days difference between self.transaction_date
        and timezone.now

        returns an int derived from diff.days
        """

        difference: timedelta = timezone.now() - self.date_billing_last

        return difference.days

    @property
    def for_retry(self) -> bool:
        """
        if the difference is less than the attached retry in days,
        then it's due for a retry
        """

        if not self.retry:
            return False

        return self.transaction_ago >= self.retry.retry_offset

    def __str__(self) -> str:
        return '{} for {}'.format(
            self.user,
            self.subscription.plan
        )

    class Meta:
        ordering = ('user', 'date_billing_start',)


class SubscriptionTransaction(models.Model):
    PAYMENT = 'P'
    REFUND = 'R'
    CANCEL = 'C'
    TRANSACTION_TYPES = [
        (PAYMENT, 'Payment'),
        (REFUND, 'Refund'),
        (CANCEL, 'Cancellation'),
    ]

    """Details for a subscription plan billing."""
    id = models.UUIDField(
        default=uuid4,
        editable=False,
        primary_key=True,
        verbose_name='ID',
    )
    user = models.ForeignKey(
        get_user_model(),
        help_text=_('the user that this subscription was billed for'),
        null=True,
        on_delete=models.SET_NULL,
        related_name='subscription_transactions'
    )
    subscription = models.ForeignKey(
        PlanCost,
        help_text=_('the plan costs that were billed'),
        null=True,
        on_delete=models.SET_NULL,
        related_name='transactions'
    )
    date_transaction = models.DateTimeField(
        help_text=_('the datetime the transaction was billed'),
        verbose_name='transaction date',
    )
    amount = models.DecimalField(
        blank=True,
        decimal_places=4,
        help_text=_('how much was billed for the user'),
        max_digits=19,
        null=True,
    )

    # when creating an object and setting the value,
    # SubscriptionTransaction(transaction_type=SubscriptionTransaction.PAYMENT)
    transaction_type = models.CharField(
        default="P",
        max_length=2,
        choices=TRANSACTION_TYPES
    )

    def __str__(self):
        return '{} for {} @ {} {}'.format(
            self.user,
            self.subscription.plan.plan_name,
            self.subscription.currency.currency_symbol,
            self.amount,
        )

    class Meta:
        ordering = ('date_transaction', 'user',)


class PlanList(models.Model):
    """Model to record details of a display list of SubscriptionPlans."""
    title = models.TextField(
        blank=True,
        help_text=_('title to display on the subscription plan list page'),
        null=True,
    )
    slug = models.SlugField(
        blank=True,
        help_text=_('slug to reference the subscription plan list'),
        max_length=128,
        null=True,
        unique=True,
    )
    subtitle = models.TextField(
        blank=True,
        help_text=_('subtitle to display on the subscription plan list page'),
        null=True,
    )
    header = models.TextField(
        blank=True,
        help_text=_('header text to display on the subscription plan list page'),
        null=True,
    )
    footer = models.TextField(
        blank=True,
        help_text=_('header text to display on the subscription plan list page'),
        null=True,
    )
    active = models.BooleanField(
        default=True,
        help_text=_('whether this plan list is active or not.'),
    )

    def __str__(self):
        return self.title


class PlanListDetail(models.Model):
    """Model to add additional details to plans when part of PlanList."""
    plan = models.ForeignKey(
        PlanCost,
        on_delete=models.CASCADE,
        related_name='plan_list_details',
    )
    plan_list = models.ForeignKey(
        PlanList,
        on_delete=models.CASCADE,
        related_name='plan_list_details',
    )
    html_content = models.TextField(
        blank=True,
        help_text=_('HTML content to display for plan'),
        null=True,
    )
    subscribe_button_text = models.CharField(
        blank=True,
        default='Subscribe',
        max_length=128,
        null=True,
    )
    order = models.PositiveIntegerField(
        default=1,
        help_text=_('Order to display plan in (lower numbers displayed first)'),
    )

    active = models.BooleanField(default=True)

    def __str__(self):
        return 'Plan List {} - {}'.format(
            self.plan_list, self.plan
        )
