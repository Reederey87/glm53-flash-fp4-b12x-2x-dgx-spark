import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from flare_trace_check import trace


def fixture(serial=False):
    rows = [{'event':'manifest','schema':1,'started_at_ns':0,
             'graphs':[{'graph':0,'kind':'Prefill'}]}]
    visits = [(slot,chunk) for slot in range(4) for chunk in range(4)] if serial else [
        (slot,chunk) for chunk in range(4) for slot in range(4)]
    for i,(slot,chunk) in enumerate(visits):
        rows.append({'event':'completion','graph':0,'fence':i+1,'at_ns':100+i,
                     'selected_at_ns':i,'commit_ns':i+1,'wall_ns':1,'gpu_ns':1,
                     'lanes':[{'slot':slot,'generation':9,'start_position':chunk*2,'tokens':2}]})
    rows.append({'event':'complete','complete':True,'dropped_updates':0,'truncated':False,
                 'reason':'stopped','completions':16,'at_ns':200})
    return rows


class CompletionTraceTests(unittest.TestCase):
    def test_order_changes_without_changing_prompt_work(self):
        balanced = trace(fixture(), length=8)
        serial = trace(fixture(True), length=8)
        self.assertEqual(balanced['total_prompt_work'], serial['total_prompt_work'])
        self.assertEqual([r['cohort_prompt_tokens_completed'] for r in balanced['prompt_finishes']], [26,28,30,32])
        self.assertEqual([r['cohort_prompt_tokens_completed'] for r in serial['prompt_finishes']], [8,16,24,32])

    def test_missing_overlapping_or_reused_generation_is_rejected(self):
        for key,value in [('start_position',1),('generation',10),('tokens',1)]:
            rows = fixture()
            rows[5]['lanes'][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                trace(rows,length=8)
        rows=fixture();del rows[5];rows[-1]['completions']-=1
        with self.assertRaisesRegex(ValueError,'missing, duplicated or overlapping'):
            trace(rows,length=8)

    def test_joint_completion_does_not_invent_lane_order(self):
        rows=fixture()
        together=[rows[0]]
        for i in range(4):
            row=copy.deepcopy(rows[1+i*4])
            row['lanes']=[lane for source in rows[1+i*4:5+i*4] for lane in source['lanes']]
            together.append(row)
        together.append(dict(rows[-1],completions=4))
        result=trace(together,length=8)
        self.assertEqual([r['cohort_prompt_tokens_completed'] for r in result['prompt_finishes']], [32]*4)

    def test_missing_footer_drops_clock_and_count_errors_are_rejected(self):
        base=fixture()
        variants=[base[:-1]]
        for field,value in [('dropped_updates',1),('truncated',True),('completions',15)]:
            rows=copy.deepcopy(base);rows[-1][field]=value;variants.append(rows)
        rows=copy.deepcopy(base);rows[3]['at_ns']=1;variants.append(rows)
        rows=copy.deepcopy(base);rows[3]['graph']=99;variants.append(rows)
        for rows in variants:
            with self.assertRaises(ValueError):trace(rows,length=8)


if __name__ == '__main__':
    unittest.main()
