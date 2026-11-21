"""Independent contracts for visual provenance, coordinates and actual media decoding."""
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from electron_field_topology import sf_visual_collection as vis


class VisualTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.row={'id':'control','q':0,'seed':'software-control','stage':'fixture, not project result','iteration':0,'nodes':9,'lengths':[8.,8.,8.],'home_path':'control.npz','model':'SF-relativistic-neutral-v1','kind':'static','outcome':'software fixture','interpretation':'Not a retained scientific candidate.'}
  xyz=np.indices((9,9,9));theta=.2*np.sin(xyz[0]*.4)*np.sin(xyz[1]*.3)*np.sin(xyz[2]*.5)
  self.n=np.stack((np.sin(theta),np.zeros_like(theta),np.cos(theta)),axis=-1)
  for axis in range(3):
   sl=[slice(None)]*3;sl[axis]=[0,1,7,8];self.n[tuple(sl)]=[0,0,1]
  self.path=self.root/'control.npz';self.write()

 def write(self,**kw):
  np.savez_compressed(self.path,field=self.n,field_rate=np.zeros_like(self.n),h=1.,iteration=0,model_id='SF-relativistic-neutral-v1',expected_q=0,**kw)
  self.row['sha256']=vis.sha(self.path)

 def test_source_authentication_and_no_source_rewrites(self):
  original=self.path.read_bytes();p=vis.resolve(self.row,self.root)
  n,v=vis.load_state(self.row,p);self.assertEqual(self.path.read_bytes(),original)
  np.testing.assert_array_equal(n,self.n);self.assertTrue(np.all(v==0))
  self.path.write_bytes(b'changed')
  with self.assertRaisesRegex(ValueError,'hash'):vis.resolve(self.row,self.root)

 def test_wrong_q_grid_precision_and_iteration_rejected(self):
  for key,value in [('q',1),('nodes',11),('iteration',50),('model','wrong')]:
   row=dict(self.row,**{key:value})
   with self.assertRaises(ValueError):vis.load_state(row,self.path)
  self.n=self.n.astype(np.float32);self.write()
  with self.assertRaisesRegex(ValueError,'precision'):vis.load_state(self.row,self.path)

 def test_saved_physical_time_is_not_inferred(self):
  self.write(time=.2,step=20)
  row=dict(self.row,kind='physical-time',time=.2,step=20)
  vis.load_state(row,self.path)
  for key,value in [('time',.3),('step',30)]:
   with self.assertRaises(ValueError):vis.load_state(dict(row,**{key:value}),self.path)

 def test_missing_file_and_active_screen_exclusion(self):
  self.assertIsNone(vis.resolve(dict(self.row,home_path='missing.npz'),self.root))
  with self.assertRaises(ValueError):vis.resolve(dict(self.row,home_path='adaptive-q-screen/live.npz'),self.root)

 def test_native_density_matches_existing_operator_and_preserves_input(self):
  from electron_field_topology.sf_time import Grid,densities
  old=self.n.copy();g=Grid((9,9,9),(8.,8.,8.),'fixed');v=np.zeros_like(self.n)
  expected=densities(self.n,v,g)['energy_density']
  actual=vis.derive(self.n,v,g.lengths,curves=False)
  np.testing.assert_allclose(expected,actual['energy'],rtol=1e-13,atol=1e-15)
  np.testing.assert_array_equal(self.n,old)
  moving=.01*np.cross(self.n,np.array([1.,0.,0.]));moving[g.fixed_mask()]=0
  np.testing.assert_allclose(densities(self.n,moving,g)['energy_density'],vis.derive(self.n,moving,g.lengths,curves=False)['energy'],rtol=1e-13,atol=1e-15)

 def test_anisotropic_coordinates_and_array_ordering(self):
  from electron_field_topology.sf_renderer import triangles
  xyz=np.indices((4,5,6)).transpose(1,2,3,0)
  tri,colors=triangles(xyz[...,0],xyz[...,1],[-2,-3,-4],[2,3,4],1.25)
  self.assertGreater(len(tri),0)
  np.testing.assert_allclose(tri[:,:,0],.5)
  self.assertGreater(tri[:,:,1].max(),3)
  self.assertGreater(tri[:,:,2].max(),12)

 def test_negative_acceleration_example_is_not_force_map(self):
  from electron_field_topology.sf_time import Grid,acceleration
  g=Grid((9,9,9),(8.,8.,8.),'fixed')
  expected=np.linalg.norm(acceleration(self.n,np.zeros_like(self.n),g)[1],axis=-1)
  data=vis.derive(self.n,np.zeros_like(self.n),g.lengths,curves=False)
  np.testing.assert_allclose(data['acceleration'],expected)
  self.assertGreater(data['acceleration'].max(),0)

 def test_recursive_seal_includes_child_checksum_files(self):
  child=self.root/'child';child.mkdir();(child/'value.csv').write_bytes(b'a,b\n1,2\n')
  vis.seal(child);vis.seal(self.root);vis.verify_seal(self.root)
  (child/'SHA256SUMS').write_text('tampered\n')
  with self.assertRaises(ValueError):vis.verify_seal(self.root)

 def test_lf_csv_and_unlisted_payload_rejected(self):
  (self.root/'a.csv').write_bytes(b'a\r\n');vis.seal(self.root)
  with self.assertRaisesRegex(ValueError,'LF'):vis.verify_seal(self.root)
  (self.root/'a.csv').write_bytes(b'a\n');vis.seal(self.root);(self.root/'extra').write_text('x')
  with self.assertRaises(ValueError):vis.verify_seal(self.root)

 def test_heavy_work_defaults_to_deferred(self):
  with self.assertRaisesRegex(ValueError,'deferred'):vis.resource_guard(self.root)

 def test_offline_viewer_escapes_labels_and_contains_no_fetch(self):
  from PIL import Image
  p=self.root/'frame.png';Image.new('RGB',(16,16),'red').save(p)
  viewer=self.root/'viewer.html';vis.offline_player([('</script> one',p),('two',p)],viewer,'<fixture>','optimizer')
  text=viewer.read_text();self.assertNotIn('fetch(',text);self.assertIn('\\u003c/script>',text);self.assertIn('&lt;fixture&gt;',text)

 @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'ffmpeg/ffprobe unavailable')
 def test_actual_h264_encoding_and_full_decoding(self):
  from PIL import Image
  frames=[]
  for i,color in enumerate(['red','blue']):
   p=self.root/f'{i}.png';Image.new('RGB',(160,90),color).save(p);frames.append(p)
  result=vis.encode(frames,self.root/'test.mp4')
  self.assertEqual(result['streams'][0]['codec_name'],'h264');self.assertEqual(result['actual_full_decode'],'passed')

 def test_high_resolution_static_and_presentation_ranges(self):
  from PIL import Image
  cfg={'width':3840,'height':2160,'display_nodes':9,'max_triangles':2000,'axis_half_length':14.,'azimuth':-55.,'recorded_at':vis.stamp()}
  data=vis.derive(self.n,np.zeros_like(self.n),[8.]*3,curves=False)
  p=self.root/'spatial.png';r=vis.plot_state(self.row,self.n,data,p,cfg,float(data['energy'].max())*.3)
  with Image.open(p) as image:self.assertEqual(image.size,(3840,2160))
  self.assertEqual(r['field_color_range'],[-1,1]);self.assertEqual(r['acceleration_range'],[1e-8,1e2])

 def test_declared_animation_kinds_have_explicit_labels(self):
  from PIL import Image
  p=self.root/'frame.png';Image.new('RGB',(16,16)).save(p)
  for kind in ['physical-time','optimizer','camera-only']:
   target=self.root/(kind+'.html');vis.offline_player([('actual recorded label',p)],target,'control',kind)
   self.assertIn(kind,target.read_text());self.assertIn('not physical spinning',target.read_text())


if __name__=='__main__':unittest.main()
