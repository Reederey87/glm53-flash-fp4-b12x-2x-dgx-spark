"""Reject incomplete diagnostic evidence without guessing missing counters."""
import tempfile
from pathlib import Path
import types
import unittest
from unittest.mock import patch
import kernel_memory_counters as K


def zone(present=100,managed=90):
    return (f'Node 0, zone Normal\n pages free 30\n present {present}\n managed {managed}\n'
            +'\n'.join(f' cpu: {cpu}\n'+''.join(f' {key}: {value}\n' for key,value in
                [('count',40),('high',20),('batch',4),('high_min',16),('high_max',80),('vm stats threshold',2)]) for cpu in (0,1)))


def vmstat():
    return '\n'.join(f'{name} 10' for name in ('nr_free_pages','nr_anon_pages','nr_shmem',
        'nr_active_file','nr_inactive_file','pgfree',*sorted(K.PGALLOC)))+'\n'


def buddy(orders=14):return 'Node 0, zone Normal '+' '.join(['1']*orders)+'\n'


class Counters(unittest.TestCase):
    def test_meminfo_units_missing_duplicate(self):
        text=''.join(f'{name}: 2 kB\n' for name in K.MEM)
        self.assertTrue(all(n==2048 for n in K.parse_meminfo(text).values()))
        for bad in (text.replace('MemFree: 2 kB\n',''),text+'MemFree: 2 kB\n',text.replace('kB','MB')):
            with self.assertRaises(ValueError):K.parse_meminfo(bad)

    def test_every_pgalloc_field_required(self):
        text=vmstat();self.assertEqual(set(K.parse_vmstat(text))&K.PGALLOC,K.PGALLOC)
        for name in K.PGALLOC:
            with self.assertRaises(ValueError):K.parse_vmstat(text.replace(f'{name} 10\n',''))
        for bad in (text+'pgalloc_dma 1\n',text+'pgalloc_unknown 1\n'):
            with self.assertRaises(ValueError):K.parse_vmstat(bad)

    def test_present_but_unmanaged_is_populated(self):
        rows=K.parse_zoneinfo(zone(managed=0),[0,1]);self.assertEqual(len(rows[0]['cpus']),2)
        self.assertGreater(rows[0]['cpus'][0]['count'],rows[0]['cpus'][0]['high'])

    def test_zone_missing_duplicate_and_truncated_rejected(self):
        text=zone()
        for bad in (text.replace(' present 100\n',''),text.replace(' vm stats threshold: 2\n','',1),
                    text.replace(' cpu: 1',' cpu: 0'),text+text,text[:text.rfind(' high_max:')]):
            with self.assertRaises(ValueError):K.parse_zoneinfo(bad,[0,1])

    def test_empty_zone_has_no_pagesets(self):
        self.assertEqual(K.parse_zoneinfo('Node 0, zone DMA32\n pages free 0\n present 0\n managed 0\n',[0,1])[0]['cpus'],[])
        with self.assertRaises(ValueError):K.parse_zoneinfo(zone(present=0,managed=0),[0,1])

    def test_buddy_all_orders_required_even_uniform_truncation(self):
        self.assertEqual(len(K.parse_buddyinfo(buddy())[0]['free_blocks']),14)
        for bad in (buddy(1),buddy(13),buddy(15),buddy()+buddy(),buddy(13)+buddy(13).replace('Normal','DMA')):
            with self.assertRaises(ValueError):K.parse_buddyinfo(bad)

    def test_cpu_range_coverage(self):
        self.assertEqual(K.online_cpus('0-1,3'),[0,1,3])
        for bad in ('0,0','2-1','4096','0-1,1',''):
            with self.assertRaises(ValueError):K.online_cpus(bad)

    def test_bounded_read(self):
        with tempfile.TemporaryDirectory() as directory:
            file=Path(directory)/'counter';file.write_text('12345')
            self.assertEqual(K.bounded(file,5),'12345')
            with self.assertRaises(ValueError):K.bounded(file,4)

    def test_snapshot_includes_parse_time_and_keeps_inventories_separate(self):
        raw={'meminfo':''.join(f'{name}: 2 kB\n' for name in K.MEM),'vmstat':vmstat(),
             'zoneinfo':zone(),'buddyinfo':buddy()}
        def read(path,cap):
            name=path.rsplit('/',1)[-1]
            return {'online':'0-1','min_free_kbytes':'1048576','stat_interval':'1','percpu_pagelist_high_fraction':'0'}.get(name,raw.get(name))
        clock=[0]
        def slow(text):clock[0]=2_000_000_000;return real(text)
        real=K.parse_vmstat
        with patch.object(K,'bounded',side_effect=read),patch.object(K.os,'sysconf',return_value=4096),\
             patch.object(K.os,'uname',return_value=types.SimpleNamespace(release='6.17.0-1031-nvidia')),\
             patch.object(K.time,'monotonic_ns',side_effect=lambda:clock[0]):
            result=K.snapshot();self.assertEqual(result['pcp_count_bytes'],80*4096)
            self.assertEqual(result['buddy_list_bytes'],((1<<14)-1)*4096)
            self.assertFalse(result['available_headroom_qualified'])
            with patch.object(K,'parse_vmstat',side_effect=slow):
                with self.assertRaisesRegex(ValueError,'exceeded'):K.snapshot()


if __name__=='__main__':unittest.main()
