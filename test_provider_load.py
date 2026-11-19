import asyncio
import unittest
import provider_load as p

class Clock:
    def __init__(self):self.value=0.0
    def __call__(self):return self.value
    async def sleep(self,seconds):self.value+=seconds

class BudgetTests(unittest.TestCase):
    def test_invalid_count(self):
        for value in [True,0,-1,101,1.0,'2']:
            with self.subTest(value=value),self.assertRaises(p.LoadStopped):p.CallBudget(calls=value,seconds=2)
    def test_invalid_seconds(self):
        for value in [True,0,-1,301,float('nan'),float('inf'),'2']:
            with self.subTest(value=value),self.assertRaises(p.LoadStopped):p.CallBudget(calls=1,seconds=value)
    def test_slots_never_refunded(self):
        b=p.CallBudget(calls=1,seconds=2);b.reserve()
        with self.assertRaises(p.LoadStopped):b.reserve()
    def test_expired(self):
        c=Clock();b=p.CallBudget(calls=1,seconds=2,now=c);c.value=2
        with self.assertRaises(p.LoadStopped):b.remaining()
    def test_backwards(self):
        c=Clock();b=p.CallBudget(calls=1,seconds=2,now=c);c.value=-1
        with self.assertRaises(p.LoadStopped):b.remaining()
    def test_private_repr(self):
        self.assertEqual(repr(p.CallBudget(calls=1,seconds=2)),'<CallBudget private>')

class QueueTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.c=Clock();self.q=p.SerialQueue(now=self.c,sleep=self.c.sleep)
    def budget(self,calls=5,seconds=30):return p.CallBudget(calls=calls,seconds=seconds,now=self.c)
    async def test_order_spacing_and_result(self):
        starts=[]
        async def op():starts.append(self.c());return 'private'
        b=self.budget()
        self.assertEqual(await self.q.run(op,b),'private')
        self.assertEqual(await self.q.run(op,b),'private')
        self.assertEqual(starts,[0,2])
    async def test_error_generic_no_retry_and_next_job_runs(self):
        calls=[]
        async def bad():calls.append(1);raise ValueError('private-account-value')
        with self.assertRaises(p.LoadStopped) as cm:await self.q.run(bad,self.budget())
        self.assertNotIn('private-account-value',str(cm.exception));self.assertIsNone(cm.exception.__context__)
        async def good():return 7
        self.assertEqual(await self.q.run(good,self.budget()),7);self.assertEqual(calls,[1])
    async def test_nonawaitable_stops(self):
        with self.assertRaises(p.LoadStopped):await self.q.run(lambda:4,self.budget())
    async def test_pending_cap(self):
        q=p.SerialQueue(max_pending=1,interval=0);entered=asyncio.Event();finish=asyncio.Event()
        async def hold():entered.set();await finish.wait()
        t=asyncio.create_task(q.run(hold,p.CallBudget(calls=1,seconds=5)))
        await entered.wait()
        with self.assertRaises(p.LoadStopped):await q.run(hold,p.CallBudget(calls=1,seconds=5))
        finish.set();await t
    async def test_serial_no_concurrent_operation(self):
        q=p.SerialQueue(interval=0);active=0;highest=0
        async def op():
            nonlocal active,highest
            active+=1;highest=max(highest,active);await asyncio.sleep(0);active-=1
        b=p.CallBudget(calls=5,seconds=5)
        await asyncio.gather(*(q.run(op,b) for _ in range(5)))
        self.assertEqual(highest,1)
    async def test_cancel_running_propagates_and_releases(self):
        q=p.SerialQueue(interval=0);entered=asyncio.Event()
        async def hold():entered.set();await asyncio.Event().wait()
        t=asyncio.create_task(q.run(hold,p.CallBudget(calls=1,seconds=5)));await entered.wait();t.cancel()
        with self.assertRaises(asyncio.CancelledError):await t
        async def good():return 8
        self.assertEqual(await q.run(good,p.CallBudget(calls=1,seconds=5)),8)
    async def test_cancel_waiting_does_not_release_others_lock(self):
        q=p.SerialQueue(interval=0);entered=asyncio.Event();finish=asyncio.Event()
        async def hold():entered.set();await finish.wait()
        a=asyncio.create_task(q.run(hold,p.CallBudget(calls=1,seconds=5)));await entered.wait()
        b=asyncio.create_task(q.run(hold,p.CallBudget(calls=1,seconds=5)));await asyncio.sleep(0);b.cancel()
        with self.assertRaises(asyncio.CancelledError):await b
        self.assertTrue(q._lock.locked());finish.set();await a;self.assertEqual(q._pending,0)
    async def test_spacing_larger_than_budget_refuses_without_run(self):
        calls=[]
        async def op():calls.append(1)
        await self.q.run(op,self.budget())
        with self.assertRaises(p.LoadStopped):await self.q.run(op,self.budget(seconds=1))
        self.assertEqual(calls,[1])
    async def test_early_sleep_rejects(self):
        async def early(_):pass
        q=p.SerialQueue(now=self.c,sleep=early)
        async def op():return 1
        await q.run(op,self.budget())
        with self.assertRaises(p.LoadStopped):await q.run(op,self.budget())
    async def test_backward_queue_clock_refuses(self):
        async def op():return 1
        await self.q.run(op,self.budget());self.c.value=-1
        with self.assertRaises(p.LoadStopped):await self.q.run(op,p.CallBudget(calls=1,seconds=5,now=self.c))
    async def test_cooperative_timeout_cancels_and_consumes_slot(self):
        q=p.SerialQueue(interval=0);cancelled=[]
        async def slow():
            try:await asyncio.sleep(2)
            finally:cancelled.append(True)
        b=p.CallBudget(calls=1,seconds=.02)
        with self.assertRaises(p.LoadStopped):await q.run(slow,b)
        self.assertEqual(cancelled,[True]);self.assertEqual(q._pending,0)
    async def test_invalid_queue_config(self):
        for kwargs in [{'interval':float('nan')},{'interval':-1},{'max_pending':True},{'max_pending':0},{'max_pending':65},{'now':None},{'sleep':None}]:
            with self.subTest(kwargs=kwargs),self.assertRaises(p.LoadStopped):p.SerialQueue(**kwargs)
    async def test_slot_exhaustion_no_second_operation(self):
        calls=[]
        async def op():calls.append(1)
        b=self.budget(calls=1)
        await self.q.run(op,b)
        with self.assertRaises(p.LoadStopped):await self.q.run(op,b)
        self.assertEqual(calls,[1])

if __name__=='__main__':unittest.main()
