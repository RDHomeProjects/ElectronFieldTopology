"""Camera/ROI contracts and real encoding; synthetic controls only."""
from pathlib import Path
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from electron_field_topology import sf_focused_orbits as m


def fixture_mesh():
 from electron_field_topology.sf_renderer import triangles
 axis=np.linspace(-3,3,25);x,y,z=np.meshgrid(axis,axis,axis,indexing='ij')
 # A software geometry fixture, not a numerical Hopfion or research result.
 density=np.exp(-((np.sqrt(x*x+y*y)-1.4)**2+z*z)/.2)
 mesh,color=triangles(density,np.sin(x),[-3]*3,[.25]*3,.3)
 return mesh,color


class FocusedOrbitTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)

 def test_default_is_smooth_and_loop_has_no_large_jump(self):
  c=m.config();a=m.angles(c)
  self.assertEqual(len(a),600);np.testing.assert_allclose(np.diff(a),.6)
  self.assertAlmostEqual((a[0]-a[-1])%360,.6)
  self.assertEqual(c['fps'],30);self.assertEqual(c['seconds'],20)

 def test_invalid_production_quality_and_unknown_settings_rejected(self):
  for settings in [{'fps':2},{'seconds':1},{'width':1919},{'wedge_degrees':190},{'unknown':1}]:
   with self.assertRaises(ValueError):m.config(settings)

 def test_fixed_time_and_iteration_labels(self):
  row={'kind':'physical-time','time':.2,'step':20}
  self.assertIn('model t=0.2',m.frozen_label(row));self.assertIn('camera motion only',m.frozen_label(row))
  self.assertIn('iteration 450',m.frozen_label({'kind':'static','iteration':450}))

 def test_rotation_safe_bounds_contain_every_vertex(self):
  mesh,color=fixture_mesh();center,half,metadata=m.fit_bounds(mesh)
  self.assertTrue(np.all(mesh>=center-half));self.assertTrue(np.all(mesh<=center+half))
  self.assertLess(half,3);self.assertFalse(metadata['physical_box_modified'])

 def test_view_bound_fit_translates_with_contour(self):
  mesh,_=fixture_mesh();a,h,_=m.fit_bounds(mesh);b,k,_=m.fit_bounds(mesh+np.array([7.,-4.,2.]))
  np.testing.assert_allclose(b-a,[7,-4,2]);self.assertAlmostEqual(h,k)

 def test_wedge_is_fixed_data_space_and_never_changes_geometry(self):
  mesh,_=fixture_mesh();original=mesh.copy();center,half,_=m.fit_bounds(mesh)
  mask=m.wedge_mask(mesh,center,m.config())
  self.assertTrue(mask.any() and not mask.all());np.testing.assert_array_equal(mesh,original)
  self.assertFalse(m.wedge_mask(mesh,center,m.config({'wedge_degrees':0})).any())

 def test_native_roi_and_absolute_threshold_preserved(self):
  axes=[np.linspace(-4,4,33),np.linspace(-5,5,33),np.linspace(-6,6,33)]
  x,y,z=np.meshgrid(*axes,indexing='ij');e=np.exp(-((x-.6)**2+(y+.3)**2/.8+z*z/.5))
  n=np.stack((np.sin(.2*x),np.zeros_like(x),np.cos(.2*x)),axis=-1)
  level=.37
  with patch.object(m,'derive',return_value={'energy':e}):verts,col,meta=m.contour_geometry(n,np.zeros_like(n),[8,10,12],level,81)
  self.assertEqual(meta['absolute_energy_level'],level)
  self.assertTrue(all(v<33 for v in meta['native_crop_grid']))
  self.assertEqual(meta['native_crop_grid'],meta['display_crop_grid'])
  self.assertFalse(meta['triangle_deletion'])
  self.assertAlmostEqual((verts[:,:,0].min()+verts[:,:,0].max())/2,.6,delta=.06)
  self.assertAlmostEqual((verts[:,:,1].min()+verts[:,:,1].max())/2,-.3,delta=.06)

 def test_display_coarsening_happens_inside_roi(self):
  axis=np.linspace(-4,4,41);x,y,z=np.meshgrid(axis,axis,axis,indexing='ij');e=np.exp(-(x*x+y*y+z*z)/3)
  n=np.zeros((41,41,41,3));n[...,2]=1
  with patch.object(m,'derive',return_value={'energy':e}):verts,col,meta=m.contour_geometry(n,n*0,[8]*3,.1,13)
  self.assertTrue(max(meta['native_crop_grid'])>13);self.assertEqual(max(meta['display_crop_grid']),13)

 def test_scene_single_geometry_panel_and_screen_fill(self):
  import matplotlib.pyplot as plt
  vertices,colors=fixture_mesh();row={'q':0,'seed':'SOFTWARE FIXTURE ONLY','kind':'static','iteration':0,'sha256':'a'*64,'lengths':[30]*3}
  meta={'absolute_energy_level':.3,'native_grid':[25]*3,'display_crop_grid':[25]*3}
  cfg=m.config({'width':640,'height':360},fixture=True)
  fig,ax,counter,bounds=m.scene(vertices,colors,row,meta,cfg)
  self.assertEqual(sum(getattr(axis,'name','')=='3d' for axis in fig.axes),1)
  self.assertEqual(len(fig.axes),2) # 3D view and small colour legend; no static diagnostic panels.
  fractions=np.asarray(bounds['projected_fit_samples_fraction'])
  self.assertLessEqual(fractions.max(),.80);self.assertGreater(fractions.max(),.70)
  plt.close(fig)

 @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'ffmpeg unavailable')
 def test_actual_smooth_frames_encode_and_decode(self):
  import matplotlib.pyplot as plt
  verts,color=fixture_mesh();row={'q':0,'seed':'SOFTWARE FIXTURE ONLY','kind':'static','iteration':0,'sha256':'a'*64,'lengths':[30]*3}
  cfg=m.config({'width':320,'height':180,'fps':30,'seconds':1},fixture=True)
  fig,ax,counter,bounds=m.scene(verts,color,row,{'absolute_energy_level':.3,'native_grid':[25]*3,'display_crop_grid':[25]*3},cfg)
  result=m.render_segment(fig,ax,counter,self.root/'segment.mp4',0,6,cfg,self.root/'status.json')
  plt.close(fig)
  self.assertEqual(int(result['probe']['streams'][0]['nb_read_frames']),6)
  self.assertEqual(result['full_decode'],'passed')

 def test_fit_bounds_rejects_degenerate_geometry(self):
  with self.assertRaises(ValueError):m.fit_bounds(np.zeros((2,3,3)))


if __name__=='__main__':unittest.main()
