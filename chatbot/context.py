"""
context.py — Live AWS user context.

Fetches budget, instance counts, session cost, and reserved EC2 capacity
for a given user email. Injected into the system prompt on every request.
"""
import logging
import os

import boto3

from chatbot import data_cache as dc

logger = logging.getLogger(__name__)

_REGION        = os.environ.get('CHATBOT_AWS_REGION', 'us-east-1')
_sts_client    = boto3.client('sts',     region_name=_REGION)
_budget_client = boto3.client('budgets', region_name=_REGION)
_ec2_client    = boto3.client('ec2',     region_name=_REGION)


def get_reserved_instances() -> dict:
    """Return {instance_type: count} for all active EC2 reserved instances."""
    reserved = {}
    try:
        resp = _ec2_client.describe_reserved_instances(
            Filters=[{'Name': 'state', 'Values': ['active']}]
        )
        for ri in resp.get('ReservedInstances', []):
            itype = ri.get('InstanceType', '')
            count = ri.get('InstanceCount', 0)
            if itype and count > 0:
                reserved[itype] = reserved.get(itype, 0) + count
    except Exception as e:
        logger.debug("context: reserved instance lookup failed: " + str(e))
    return reserved


def get_user_context(email: str) -> dict:
    """
    Fetch live budget, instance counts, session cost, and reserved capacity.
    Returns a dict with all fields populated (defaults on failure).
    """
    context = {
        'budget_limit':    500,
        'consumed':        0,
        'forecasted':      0,
        'remaining':       500,
        'instance_count':  0,
        'stopped_count':   0,
        'total_cost_used': 0.0,
        'reserved':        {},
    }

    # --- Budget ---
    try:
        account_id = _sts_client.get_caller_identity()['Account']
        username_prefix = email.split('@')[0].lower()
        resp = _budget_client.describe_budgets(AccountId=account_id, MaxResults=99)
        for b in resp.get('Budgets', []):
            if username_prefix in b['BudgetName'].lower():
                context['budget_limit'] = int(round(float(b['BudgetLimit']['Amount']), 0))
                cs = b.get('CalculatedSpend', {})
                context['consumed']   = int(round(float(cs.get('ActualSpend',    {}).get('Amount', 0)), 0))
                context['forecasted'] = int(round(float(cs.get('ForecastedSpend', {}).get('Amount', 0)), 0))
                break
        context['remaining'] = max(0, context['budget_limit'] - context['consumed'])
    except Exception as e:
        logger.warning("context: budget fetch failed: " + str(e))

    # --- Instance counts + session cost from result.json ---
    try:
        data = dc.result_json()
        active     = []
        stopped    = []
        total_cost = 0.0
        for bucket in ('Running', 'Provisioning', 'Inprogress'):
            for i in data.get(bucket, []):
                if i.get('CREATEDBY', '').lower() == email.lower():
                    active.append(i)
                    try:
                        total_cost += float(i.get('costUtilised') or i.get('costUtilized') or 0)
                    except (TypeError, ValueError):
                        pass
        for i in data.get('Stopped', []):
            if i.get('CREATEDBY', '').lower() == email.lower():
                stopped.append(i)
        context['instance_count']  = len(active)
        context['stopped_count']   = len(stopped)
        context['total_cost_used'] = round(total_cost, 2)
    except Exception as e:
        logger.debug("context: result.json read failed: " + str(e))

    # --- Reserved EC2 instances ---
    context['reserved'] = get_reserved_instances()

    return context
