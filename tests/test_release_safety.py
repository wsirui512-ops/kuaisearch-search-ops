import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from publish import publish_bundle

class ReleaseSafety(unittest.TestCase):
    def test_failed_bundle_restores_old_and_removes_new_target(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);pairs=[]
            for i in range(3):
                a,b=p/f'new{i}',p/f'published{i}';a.write_text('new')
                if i!=1:b.write_text('old')
                pairs.append((a,b))
            count=0
            def fail_third(a,b):
                nonlocal count
                count+=1
                if count==3:raise OSError('injected disk failure')
                os.replace(a,b)
            with self.assertRaises(OSError):publish_bundle(pairs,p,replace=fail_third)
            self.assertEqual(pairs[0][1].read_text(),'old')
            self.assertFalse(pairs[1][1].exists())
            self.assertEqual(pairs[2][1].read_text(),'old')

    def test_missing_staged_file_keeps_old(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);target=p/'old';target.write_text('old')
            with self.assertRaises(FileNotFoundError):publish_bundle([(p/'missing',target)],p)
            self.assertEqual(target.read_text(),'old')

if __name__=='__main__':unittest.main()
