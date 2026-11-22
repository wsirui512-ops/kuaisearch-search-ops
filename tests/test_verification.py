import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import verify_docs
import dashboard_contract

class Verification(unittest.TestCase):
    def test_render_manifest_survives_linux_line_endings(self):
        original=dashboard_contract.ROOT
        manifest=dashboard_contract.MANIFEST
        import json
        data=json.loads(manifest.read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)
            paths=list(data['inputs'])+list(data['assets'])+['dashboards/静态看板.pptx']
            for name in paths:
                target=p/name;target.parent.mkdir(parents=True,exist_ok=True)
                raw=(ROOT/name).read_bytes()
                target.write_bytes(raw.replace(b'\r\n',b'\n') if name in data['inputs'] else raw)
            try:
                dashboard_contract.ROOT=p
                dashboard_contract.verify_manifest()
            finally:dashboard_contract.ROOT=original

    def test_stale_home_gap_rejected_in_its_table(self):
        original=verify_docs.ROOT
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);(p/'docs').mkdir();shutil.copytree(ROOT/'outputs_public',p/'outputs_public')
            text=(ROOT/'docs/analysis-report.md').read_text(encoding='utf-8')
            old='| 家居生活 | 905,901 | 4.02% | 3.97% | -0.06pp | -507 |'
            self.assertIn(old,text)
            (p/'docs/analysis-report.md').write_text(text.replace(old,old.replace('-507','-1,463')),encoding='utf-8')
            try:
                verify_docs.ROOT=p
                with self.assertRaisesRegex(AssertionError,'category table'):verify_docs.main()
            finally:verify_docs.ROOT=original

    def test_unconfirmed_labels_cannot_publish(self):
        spec=importlib.util.spec_from_file_location('review',ROOT/'scripts/apply_spotcheck.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as folder:
            module.ROOT=Path(folder)
            with self.assertRaisesRegex(ValueError,'Missing author confirmation'):module.main()
            self.assertFalse((Path(folder)/'outputs_public/spotcheck_summary.csv').exists())

if __name__=='__main__':unittest.main()
