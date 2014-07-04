# -*- coding: utf-8 -*-
import re
import itertools

from django import forms
from django.utils.translation import ugettext as _
from django.forms.formsets import formset_factory, BaseFormSet, \
    TOTAL_FORM_COUNT, INITIAL_FORM_COUNT

import form_utils.forms

from cla_common.forms import MultipleFormsForm
from cla_common.money_interval.forms import MoneyIntervalField

from ..fields import RadioBooleanField, MoneyField

from .base import CheckerWizardMixin, EligibilityMixin


OWNED_BY_CHOICES = [
    (1, 'Owned by me'),
    (0, 'Joint names')
]


class YourFinancesFormMixin(EligibilityMixin, CheckerWizardMixin):
    form_tag = 'your_finances'

    def _prepare_for_init(self, kwargs):
        super(YourFinancesFormMixin, self)._prepare_for_init(kwargs)

        # pop these from kwargs
        self.has_partner = kwargs.pop('has_partner', True)
        self.has_property = kwargs.pop('has_property', True)
        self.has_children = kwargs.pop('has_children', True)
        self.has_benefits = kwargs.pop('has_benefits', False)


class YourCapitalPropertyForm(CheckerWizardMixin, forms.Form):
    worth = MoneyField(
        label=_(u"How much is it worth?"), required=True
    )
    mortgage_left = MoneyField(
        label=_(u"How much is left to pay on the mortgage?"),
        required=True
    )
    owner = RadioBooleanField(
        label=_(u"Is the property owned by you or is it in joint names?"),
        choices=OWNED_BY_CHOICES, required=True
    )
    share = forms.IntegerField(
        label=_(u'What is your share of the property?'),
        min_value=0, max_value=100
    )
    disputed = RadioBooleanField(
        label=_(u"Is this property disputed?"), required=True
    )


class YourCapitalSavingsForm(CheckerWizardMixin, forms.Form):
    bank = MoneyField(
        label=_(u"How much money do you have saved in a bank or building society?")
    )
    investments = MoneyField(
        label=_(u"What is the total value of any investments (shares or ISAs) you have?")
    )
    valuable_items = MoneyField(
        label=_(u"What is the total value of any items you have worth over £500?")
    )
    money_owed = MoneyField(
        label=_(u"How much money do you have owed to you?")
    )


class YourCapitalPartnerSavingsForm(CheckerWizardMixin, forms.Form):
    bank = MoneyField(
        label=_(u"How much money does your partner have saved in a bank or building society?")
    )
    investments = MoneyField(
        label=_(u"What is the total value of any investments (shares or ISAs) your partner has?")
    )
    valuable_items = MoneyField(
        label=_(u"What is the total value of any items your partner has worth over £500?")
    )
    money_owed = MoneyField(
        label=_(u"How much money does your partner have owed to them?")
    )

class FirstRequiredFormSet(BaseFormSet):
    def __init__(self, *args, **kwargs):
        super(FirstRequiredFormSet, self).__init__(*args, **kwargs)
        if self.forms:
            self.forms[0].empty_permitted = False

class YourCapitalForm(YourFinancesFormMixin, MultipleFormsForm):

    YourCapitalPropertyFormSet = formset_factory(
        YourCapitalPropertyForm,
        extra=3,
        max_num=3,
        validate_max=True,
        formset=FirstRequiredFormSet
    )

    formset_list = (
        ('property', YourCapitalPropertyFormSet),
    )

    forms_list = (
        ('your_savings', YourCapitalSavingsForm),
        ('partners_savings', YourCapitalPartnerSavingsForm),
    )

    def _prepare_for_init(self, kwargs):
        super(YourCapitalForm, self)._prepare_for_init(kwargs)

        new_forms_list = dict(self.forms_list)
        new_formset_list = dict(self.formset_list)
        if not self.has_partner:
            del new_forms_list['partners_savings']
        if not self.has_property:
            del new_formset_list['property']

        self.forms_list = new_forms_list.items()
        self.formset_list = new_formset_list.items()

    @property
    def total_capital_assets(self):
        return self._get_total_capital_assets(self.cleaned_data)

    def _get_total_capital_assets(self, cleaned_data):
        # used for display at the moment but maybe should come from a
        # common calculator lib so both front end and backend can share it

        total_of_savings = 0
        total_of_property = 0

        own_savings, partner_savings = self.get_savings(cleaned_data)
        total_of_savings = sum(itertools.chain(own_savings.values(), partner_savings.values()))

        properties = self.get_properties(cleaned_data)
        for property in properties:
            share = property['share']
            value = property['value']
            mortgage_left = property['mortgage_left']
            if share > 0:
                share = share / 100.0

                total_of_property +=  int(max(value - mortgage_left, 0) * share)

        return total_of_property + total_of_savings

    @property
    def cleaned_data(self):
        cleaned_data = super(YourCapitalForm, self).cleaned_data
        cleaned_data.update({
            'total_capital_assets': self._get_total_capital_assets(cleaned_data)
        })

        return cleaned_data

    def _get_savings(self, key, cleaned_data):
        if key in cleaned_data:
            return {
                'bank_balance': cleaned_data.get(key, {}).get('bank', 0),
                'asset_balance': cleaned_data.get(key, {}).get('valuable_items', 0),
                'credit_balance': cleaned_data.get(key, {}).get('money_owed', 0),
                'investment_balance': cleaned_data.get(key, {}).get('investments', 0),
            }

    def get_savings(self, cleaned_data):
        your_savings = self._get_savings('your_savings', cleaned_data)
        partner_savings = self._get_savings('partners_savings', cleaned_data) or {}
        return your_savings, partner_savings

    def get_properties(self, cleaned_data):
        def _transform(property):
            return {
                'mortgage_left': property.get('mortgage_left'),
                'share': property.get('share'),
                'value': property.get('worth'),
                'disputed': property.get('disputed')
            }
        properties = cleaned_data.get('property', [])
        return [_transform(p) for p in properties if p]

    def save(self):
        # eligibility check reference should be set otherwise => error
        self.check_that_reference_exists()

        data = self.cleaned_data
        your_savings, partner_savings = self.get_savings(data)
        post_data = {
            'property_set': self.get_properties(data),
            'you': {
                'savings': your_savings
            }
        }
        if partner_savings:
            post_data.update({
                'partner': {
                    'savings': partner_savings
                }
            })

        response = self.connection.eligibility_check(self.reference).patch(post_data)
        return {
            'eligibility_check': response
        }


class YourSingleIncomeForm(CheckerWizardMixin, forms.Form):
    earnings = MoneyIntervalField(
        label=_(u"Earnings last month"), min_value=0
    )

    tax = MoneyIntervalField(label=_(u"Tax paid"), min_value=0)
    ni = MoneyIntervalField(label=_(u"National Insurance Contribution"), min_value=0)

    other_income = MoneyIntervalField(
        label=_(u"Other income last month"), min_value=0
    )

    self_employed = RadioBooleanField(
        label=_(u"Are you self employed?"), initial=0
    )


class YourDependentsForm(CheckerWizardMixin, forms.Form):
    dependants_old = forms.IntegerField(
        label=_(u'Children aged 16 and over'), required=True,
        min_value=0, max_value=50
    )

    dependants_young = forms.IntegerField(
        label=_(u'Children aged 15 and under'), required=True,
        min_value=0, max_value=50
    )


class YourIncomeForm(YourFinancesFormMixin, MultipleFormsForm):
    forms_list = (
        ('your_income', YourSingleIncomeForm),
        ('partners_income', YourSingleIncomeForm),
        ('dependants', YourDependentsForm)
    )

    def _prepare_for_init(self, kwargs):
        super(YourIncomeForm, self)._prepare_for_init(kwargs)

        new_forms_list = dict(self.forms_list)
        if not self.has_partner:
            del new_forms_list['partners_income']
        if not self.has_children:
            del new_forms_list['dependants']

        self.forms_list = new_forms_list.items()

    def _get_total_earnings(self, cleaned_data):
        total = 0
        for i in self.get_incomes(cleaned_data):
            total += i['other_income']['per_month']
            total += i['earnings']['per_month']

        return total

    @property
    def total_earnings(self):
        return self._get_total_earnings(self.cleaned_data)

    @property
    def cleaned_data(self):
        cleaned_data = super(YourIncomeForm, self).cleaned_data
        cleaned_data.update({
            'total_earnings': self._get_total_earnings(cleaned_data)
        })

        return cleaned_data

    def get_income(self, key, cleaned_data):
        income = {
            'earnings': cleaned_data.get(key, {}).get('earnings', {'per_interval_value': 0, 'per_month': 0, 'interval_period': 'per_month'}),
            'other_income': cleaned_data.get(key, {}).get('other_income', {'per_interval_value': 0, 'per_month': 0, 'interval_period': 'per_month'}),
            'self_employed': cleaned_data.get(key, {}).get('self_employed', False)
        }

        return income

    def get_incomes(self, cleaned_data):
        your_income = self.get_income('your_income', cleaned_data)
        partner_income = self.get_income('partners_income', cleaned_data) or {}
        return your_income, partner_income

    def _get_allowances(self, key, cleaned_data):
        if key in cleaned_data:

            return {
                'income_tax': cleaned_data.get(key, {}).get('tax', {'per_interval_value': 0, 'per_month': 0, 'interval_period': 'per_month'}),
                'national_insurance': cleaned_data.get(key, {}).get('ni', {'per_interval_value': 0, 'per_month': 0, 'interval_period': 'per_month'}),
            }

    def get_allowances(self, cleaned_data):
        your_allowances = self._get_allowances('your_income', cleaned_data)
        partner_allowances = self._get_allowances('partners_income', cleaned_data) or {}
        return your_allowances, partner_allowances

    def get_dependants(self, cleaned_data):
        return cleaned_data.get('dependants', {})

    def save(self):
        # eligibility check reference should be set otherwise => error
        self.check_that_reference_exists()

        data = self.cleaned_data
        your_income, partner_income = self.get_incomes(data)
        your_allowances, partner_allowances = self.get_allowances(data)

        dependants = self.get_dependants(data)
        post_data = {
            'dependants_young': dependants.get('dependants_young', 0),
            'dependants_old': dependants.get('dependants_old', 0),
            'you': {
                'income': your_income,
                'deductions': your_allowances
            }
        }
        if partner_income:
            post_data.update({
                'partner': {
                    'income': partner_income,
                    'deductions': partner_allowances
                }
            })

        response = self.connection.eligibility_check(self.reference).patch(post_data)
        return {
            'eligibility_check': response
        }


class YourSingleAllowancesForm(CheckerWizardMixin, form_utils.forms.BetterForm):
    mortgage = MoneyIntervalField(label=_(u"Mortgage"), help_text=_(u"Homeowner repayments to a bank or building society. Check your most recent mortgage or bank statement."), min_value=0)
    rent = MoneyIntervalField(label=_(u"Rent"), help_text=_(u"Money you pay your landlord to live in your home. Check your most recent bank statement or rent book."), min_value=0)
    maintenance = MoneyIntervalField(label=_(u"Maintenance"), help_text=_(u"Regular payments you make to an ex-partner to help with their living costs or the living costs of your child who no longer lives with you."), min_value=0)
    childcare = MoneyIntervalField(label=_(u"Childcare"), help_text=_(u"Money you pay for your child to be looked after while you work or study."), min_value=0)
    criminal_legalaid_contributions = MoneyField(
        label=_(u"Contribution order"), help_text=_(u"Money you pay towards the cost of legal help following a criminal conviction."), min_value=0
    )

    class Meta:
        fieldsets = [('housing', {'fields': ['mortgage', 'rent'], 'legend': 'Housing costs', 'classes': ['FieldGroup']}),
                     ('', {'fields': ['maintenance', 'childcare', 'criminal_legalaid_contributions']})]


class YourSinglePartnerAllowancesForm(YourSingleAllowancesForm):
    def __init__(self, *args, **kwargs):
        super(YourSinglePartnerAllowancesForm, self).__init__(*args, **kwargs)
        self.fields["mortgage"].help_text = _(u"Homeowner repayments to a bank or building society. Check most recent mortgage or bank statements.")
        self.fields["rent"].help_text = _(u"Money your partner pays your landlord. Check most recent bank statements or rent book.")
        self.fields["maintenance"].help_text = _(u"Regular payments made to an ex-partner to help with their living costs or the living costs of a child who no longer lives with your partner.")
        self.fields["childcare"].help_text = _(u"Money your partner pays for a child to be looked after while they work or study.")
        self.fields["criminal_legalaid_contributions"].help_text = _(u"Money your partner pays towards the cost of legal help following a criminal conviction.")


class YourAllowancesForm(YourFinancesFormMixin, MultipleFormsForm):
    forms_list = (
        ('your_allowances', YourSingleAllowancesForm),
        ('partners_allowances', YourSinglePartnerAllowancesForm)
    )

    def _prepare_for_init(self, kwargs):
        super(YourAllowancesForm, self)._prepare_for_init(kwargs)

        new_forms_list = dict(self.forms_list)
        if not self.has_partner:
            del new_forms_list['partners_allowances']

        self.forms_list = new_forms_list.items()

    def _get_allowances(self, key, cleaned_data):
        if key in cleaned_data:

            return {
                'mortgage': cleaned_data.get(key, {}).get('mortgage', {}),
                'rent': cleaned_data.get(key, {}).get('rent', {}),
                'maintenance': cleaned_data.get(key, {}).get('maintenance', {}),
                'childcare': cleaned_data.get(key, {}).get('childcare', {}),
                'criminal_legalaid_contributions': cleaned_data.get(key, {}).get('criminal_legalaid_contributions', 0),
            }

    def get_allowances(self, cleaned_data):
        your_allowances = self._get_allowances('your_allowances', cleaned_data)
        partner_allowances = self._get_allowances('partners_allowances', cleaned_data) or {}
        return your_allowances, partner_allowances

    def save(self):
        # eligibility check reference should be set otherwise => error
        self.check_that_reference_exists()

        data = self.cleaned_data

        your_allowances, partner_allowances = self.get_allowances(data)
        post_data = {
            'you': {
                'deductions': your_allowances
            }
        }

        if partner_allowances:
            post_data.update({
                'partner': {
                    'deductions': partner_allowances
                }
            })

        response = self.connection.eligibility_check(self.reference).patch(post_data)
        return {
            'eligibility_check': response
        }
