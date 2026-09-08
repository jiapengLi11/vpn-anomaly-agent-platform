from __future__ import annotations

import math
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


PRICE_VERSION = 'sandbox-2026-09-v1'
FREE_LIMITS = {'ANALYSIS': 5, 'KNOWLEDGE_QA': 5}
PRICING = {
    'ANALYSIS': {'baseFen': 50, 'inputFenPerMillion': 200, 'outputFenPerMillion': 800},
    'KNOWLEDGE_QA': {'baseFen': 2, 'inputFenPerMillion': 100, 'outputFenPerMillion': 400},
}
MAX_TOKEN_BUDGET = {'ANALYSIS': (8000, 2200), 'KNOWLEDGE_QA': (6000, 2200)}
RECHARGE_AMOUNTS = {1000, 3000, 10000}


class BillingDenied(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class Authorization:
    authorization_id: str
    user_id: str
    request_id: str
    operation: str
    mode: str
    reserved_fen: int


class BillingService:
    """Thread-safe sandbox ledger. Replace storage, not domain rules, for production."""

    def __init__(self):
        self._lock = threading.RLock()
        self.reset()

    def reset(self):
        with self._lock:
            self._accounts = {}
            self._authorizations = {}
            self._completed = {}
            self._usage = []
            self._orders = {}

    def _account(self, user_id):
        return self._accounts.setdefault(user_id, {
            'userId': user_id, 'balanceFen': 0, 'freeRemaining': dict(FREE_LIMITS),
            'createdAt': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        })

    @staticmethod
    def _token_charge(operation, prompt_tokens, completion_tokens):
        price = PRICING[operation]
        return (price['baseFen'] + math.ceil(prompt_tokens * price['inputFenPerMillion'] / 1_000_000)
                + math.ceil(completion_tokens * price['outputFenPerMillion'] / 1_000_000))

    def authorize(self, user_id, request_id, operation):
        if operation not in PRICING:
            raise ValueError('unsupported operation')
        with self._lock:
            if request_id in self._completed:
                return None
            if request_id in self._authorizations:
                return self._authorizations[request_id]
            account = self._account(user_id)
            if account['freeRemaining'][operation] > 0:
                account['freeRemaining'][operation] -= 1
                mode, reserved = 'FREE_QUOTA', 0
            else:
                max_prompt, max_completion = MAX_TOKEN_BUDGET[operation]
                reserved = self._token_charge(operation, max_prompt, max_completion)
                if account['balanceFen'] < reserved:
                    raise BillingDenied('INSUFFICIENT_CREDIT', '免费额度已用完，请充值后继续使用。')
                account['balanceFen'] -= reserved
                mode = 'PAID_BALANCE'
            authorization = Authorization(str(uuid.uuid4()), user_id, request_id, operation, mode, reserved)
            self._authorizations[request_id] = authorization
            return authorization

    def settle(self, authorization, prompt_tokens=0, completion_tokens=0):
        if authorization is None:
            return self._completed.get('')
        with self._lock:
            existing = self._completed.get(authorization.request_id)
            if existing:
                return existing
            current = self._authorizations.pop(authorization.request_id, None)
            if not current:
                raise ValueError('authorization is not active')
            charge = 0 if current.mode == 'FREE_QUOTA' else self._token_charge(
                current.operation, prompt_tokens, completion_tokens)
            account = self._account(current.user_id)
            if current.mode == 'PAID_BALANCE':
                account['balanceFen'] += current.reserved_fen - charge
            usage = {
                'usageId': str(uuid.uuid4()), 'requestId': current.request_id,
                'operation': current.operation, 'billingMode': current.mode,
                'promptTokens': prompt_tokens, 'completionTokens': completion_tokens,
                'totalTokens': prompt_tokens + completion_tokens, 'chargeFen': charge,
                'priceVersion': PRICE_VERSION,
                'occurredAt': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            }
            self._usage.append(usage)
            self._completed[current.request_id] = usage
            return usage

    def release(self, authorization):
        if authorization is None:
            return
        with self._lock:
            current = self._authorizations.pop(authorization.request_id, None)
            if not current:
                return
            account = self._account(current.user_id)
            if current.mode == 'FREE_QUOTA':
                account['freeRemaining'][current.operation] += 1
            else:
                account['balanceFen'] += current.reserved_fen

    def create_order(self, user_id, channel, amount_fen):
        if channel not in {'WECHAT', 'ALIPAY'} or amount_fen not in RECHARGE_AMOUNTS:
            raise ValueError('unsupported sandbox order')
        now = datetime.now(timezone.utc)
        order = {
            'orderId': f'PAY-{uuid.uuid4().hex[:12].upper()}', 'userId': user_id,
            'channel': channel, 'amountFen': amount_fen, 'status': 'PENDING',
            'environment': 'SANDBOX', 'createdAt': now.isoformat(timespec='seconds'),
            'expiresAt': (now + timedelta(minutes=15)).isoformat(timespec='seconds'),
        }
        with self._lock:
            self._orders[order['orderId']] = order
        return dict(order)

    def simulate_paid(self, user_id, order_id):
        with self._lock:
            order = self._orders.get(order_id)
            if not order or order['userId'] != user_id:
                raise KeyError('order not found')
            if order['status'] == 'PAID':
                return dict(order)
            if order['status'] != 'PENDING':
                raise ValueError('order cannot be paid')
            order['status'] = 'PAID'
            order['paidAt'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
            self._account(user_id)['balanceFen'] += order['amountFen']
            return dict(order)

    def summary(self, user_id):
        with self._lock:
            account = dict(self._account(user_id))
            account['freeRemaining'] = dict(account['freeRemaining'])
            usage = [dict(item) for item in self._usage]
            orders = [dict(order) for order in self._orders.values() if order['userId'] == user_id]
        today = datetime.now(timezone.utc).date()
        daily = []
        for offset in range(6, -1, -1):
            day = today - timedelta(days=offset)
            rows = [item for item in usage if item['occurredAt'][:10] == day.isoformat()]
            daily.append({'date': day.isoformat(), 'calls': len(rows),
                          'tokens': sum(item['totalTokens'] for item in rows),
                          'chargeFen': sum(item['chargeFen'] for item in rows)})
        return {
            'account': account, 'priceVersion': PRICE_VERSION, 'pricing': PRICING,
            'rechargeAmountsFen': sorted(RECHARGE_AMOUNTS), 'dailyUsage': daily,
            'usage': list(reversed(usage[-20:])), 'orders': list(reversed(orders[-10:])),
            'totals': {'calls': len(usage), 'tokens': sum(item['totalTokens'] for item in usage),
                       'chargeFen': sum(item['chargeFen'] for item in usage)},
            'paymentEnvironment': 'SANDBOX',
        }


billing = BillingService()
