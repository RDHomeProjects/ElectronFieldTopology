import sys,unittest,tempfile,shutil,json
from pathlib import Path
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;ROOT=R.parents[4];sys.path.insert(0,str(R))
from verify_assessment import verify,checksums,RUN_PATH
class IntegrityControls(unittest.TestCase):
 def test_live_compact_and_original_gates(self):
  v=verify(ROOT);self.assertEqual(v['higher_q_motion_cases'],0);self.assertEqual(v['q2_original_gates_each_milestone'],7)
 def test_damaged_archive_member_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   target=Path(td);shutil.copytree(ROOT/RUN_PATH,target/RUN_PATH)
   p=target/RUN_PATH/'evidence.zip';b=bytearray(p.read_bytes());b[len(b)//2]^=1;p.write_bytes(b)
   with self.assertRaisesRegex(ValueError,'Checksum differs'):verify(target)
 def test_changed_numerical_source_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   target=Path(td);shutil.copytree(ROOT/RUN_PATH,target/RUN_PATH);shutil.copytree(ROOT/'src',target/'src')
   p=target/'src/electron_field_topology/sf_time.py';p.write_text(p.read_text()+'\n# altered\n')
   with self.assertRaisesRegex(ValueError,'Numerical source changed'):verify(target)
 def test_unsafe_checksum_path_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);(p/'SHA256SUMS').write_text('0'*64+'  ../escape\n')
   with self.assertRaisesRegex(ValueError,'Unsafe'):checksums(p)
if __name__=='__main__':unittest.main(verbosity=2)
