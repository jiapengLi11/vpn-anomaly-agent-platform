import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from traffic_agent.api import app
from traffic_agent.billing import BillingDenied, BillingService, billing


class BillingServiceTest(unittest.TestCase):
    def setUp(self):
        self.service = BillingService()

    def test_new_account_has_five_free_operations_and_sixth_is_denied(self):
        for index in range(5):
            authorization = self.service.authorize('user', f'analysis-{index}', 'ANALYSIS')
            usage = self.service.settle(authorization, 500, 100)
            self.assertEqual(usage['billingMode'], 'FREE_QUOTA')
            self.assertEqual(usage['chargeFen'], 0)
        with self.assertRaises(BillingDenied):
            self.service.authorize('user', 'analysis-6', 'ANALYSIS')
        self.assertEqual(self.service.summary('user')['account']['freeRemaining']['ANALYSIS'], 0)

    def test_failed_operation_releases_reserved_quota(self):
        authorization = self.service.authorize('user', 'cancelled', 'KNOWLEDGE_QA')
        self.service.release(authorization)
        summary = self.service.summary('user')
        self.assertEqual(summary['account']['freeRemaining']['KNOWLEDGE_QA'], 5)
        self.assertEqual(summary['totals']['calls'], 0)

    def test_sandbox_payment_is_idempotent_and_paid_usage_refunds_reserve(self):
        order = self.service.create_order('user', 'WECHAT', 1000)
        self.service.simulate_paid('user', order['orderId'])
        self.service.simulate_paid('user', order['orderId'])
        for index in range(5):
            self.service.settle(self.service.authorize('user', f'free-{index}', 'KNOWLEDGE_QA'))
        authorization = self.service.authorize('user', 'paid', 'KNOWLEDGE_QA')
        usage = self.service.settle(authorization, 1200, 300)
        self.assertEqual(usage['chargeFen'], 4)
        self.assertEqual(self.service.summary('user')['account']['balanceFen'], 996)

    def test_duplicate_request_does_not_charge_twice(self):
        authorization = self.service.authorize('user', 'same-request', 'ANALYSIS')
        self.assertIs(authorization, self.service.authorize('user', 'same-request', 'ANALYSIS'))
        first = self.service.settle(authorization)
        self.assertIsNone(self.service.authorize('user', 'same-request', 'ANALYSIS'))
        self.assertEqual(self.service.summary('user')['totals']['calls'], 1)
        self.assertEqual(first['requestId'], 'same-request')


class BillingApiTest(unittest.TestCase):
    def setUp(self):
        billing.reset()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        billing.reset()

    def test_summary_order_and_simulated_callback(self):
        summary = self.client.get('/api/billing/summary').json()
        self.assertEqual(summary['account']['freeRemaining'], {'ANALYSIS': 5, 'KNOWLEDGE_QA': 5})
        created = self.client.post('/api/billing/orders', json={
            'channel': 'ALIPAY', 'amountFen': 3000}).json()
        self.assertEqual(created['environment'], 'SANDBOX')
        paid = self.client.post(f"/api/billing/orders/{created['orderId']}/simulate-paid").json()
        self.assertEqual(paid['order']['status'], 'PAID')
        self.assertEqual(paid['summary']['account']['balanceFen'], 3000)

    def test_knowledge_endpoint_enforces_free_limit(self):
        for index in range(5):
            response = self.client.post('/api/knowledge/answer', json={
                'requestId': f'knowledge-{index}', 'question': 'UDP', 'provider': 'demo'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['billing']['billingMode'], 'FREE_QUOTA')
        denied = self.client.post('/api/knowledge/answer', json={
            'requestId': 'knowledge-6', 'question': 'UDP', 'provider': 'demo'})
        self.assertEqual(denied.status_code, 402)
        self.assertEqual(denied.json()['detail']['code'], 'INSUFFICIENT_CREDIT')


if __name__ == '__main__':
    unittest.main()
