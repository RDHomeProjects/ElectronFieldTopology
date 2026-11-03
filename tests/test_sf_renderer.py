"""Preview interpolation, independent VTK ordering, and real offline movie tests."""
import copy
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import pytest
from PIL import Image
from electron_field_topology.sf_preview import resample,write_vti
from electron_field_topology.sf_renderer import triangles,render
from electron_field_topology.sf_time_run import run


def test_vtk_point_order_and_array_components(tmp_path):
    indices=np.indices((3,4,5));a=indices[0]+10*indices[1]+100*indices[2]
    vec=np.stack((a,a+1,a+2),axis=-1).astype(np.float32)
    path=tmp_path/'frame.vti';write_vti(path,{'energy_density':a,'field':vec},[0,0,0],[1,2,3],.25,5)
    root=ET.parse(path).getroot();arrays={x.attrib['Name']:x for x in root.findall('.//PointData/DataArray')}
    actual=np.fromstring(arrays['energy_density'].text,sep=' ')
    expected=np.array([x+10*y+100*z for z in range(5) for y in range(4) for x in range(3)])
    np.testing.assert_array_equal(actual,expected)
    actual_v=np.fromstring(arrays['field'].text,sep=' ').reshape(-1,3)
    np.testing.assert_array_equal(actual_v,np.stack((expected,expected+1,expected+2),axis=-1))
    assert root.find('ImageData').attrib['WholeExtent']=='0 2 0 3 0 4'


def test_sampling_does_not_modify_solver_arrays():
    a=np.arange(9**3*3,dtype=float).reshape(9,9,9,3);before=a.copy()
    b=resample(a,(5,5,5),'periodic');b[:]=0
    np.testing.assert_array_equal(a,before)


def test_surface_of_linear_field_is_on_exact_plane():
    xyz=np.indices((4,4,4)).transpose(1,2,3,0).astype(float)
    tri,colors=triangles(xyz[...,0],xyz[...,1],[0,0,0],[1,1,1],1.5)
    assert len(tri)>0 and np.max(abs(tri[:,:,0]-1.5))<1e-14
    assert np.isfinite(tri).all() and np.isfinite(colors).all()


def test_real_offline_gif_and_rerender_changes_no_scientific_data(tmp_path):
    c={'case_id':'renderer-test','grid':[9,9,9],'lengths':[2*np.pi]*3,'boundary':'periodic',
       'dt':.01,'steps':2,'diagnostic_every':1,'checkpoint_every':1,
       'initial':{'kind':'wave','modes':[{'amplitude':.3,'wave_numbers':[1,0,0]},
                   {'amplitude':.2,'wave_numbers':[0,1,0],'phase':.7}]}}
    profile={'export':{'grid':[7,7,7],'every_steps':1,'vtk':True},
             'presentation':{'width':700,'height':450,'colors':8,'max_frames':3}}
    run(c,tmp_path/'solver',profile);before=(tmp_path/'solver/final.npz').read_bytes()
    result=render(tmp_path/'solver',tmp_path/'render',profile)
    assert len(result['frames'])==3
    with Image.open(tmp_path/'render/wave.gif') as gif:
        assert gif.n_frames==3 and gif.size==(700,450)
    with Image.open(tmp_path/'render/preview.png') as png:assert png.size==(700,450)
    import re,base64,io
    page=(tmp_path/'render/viewer.html').read_text()
    embedded=json.loads(re.search(r'<script id="frames" type="application/json">(.*?)</script>',page,re.S).group(1))
    assert len(embedded)==3 and 'slider.oninput' in page
    for frame in embedded:
        with Image.open(io.BytesIO(base64.b64decode(frame['image'].split(',',1)[1]))) as png:
            assert png.size==(700,450)
    assert (tmp_path/'solver/final.npz').read_bytes()==before
    manifest=json.loads((tmp_path/'solver/preview/manifest.json').read_text())
    assert len(ET.parse(tmp_path/'solver/preview/series.pvd').getroot().findall('.//DataSet'))==3
    # Corrupt a preview copy: renderer refuses it without touching the solver checkpoint.
    frame=tmp_path/'solver/preview'/manifest['frames'][0]['npz']
    frame.write_bytes(frame.read_bytes()+b'corrupt')
    with pytest.raises(ValueError,match='SHA-256'):render(tmp_path/'solver',tmp_path/'bad',profile)
    assert (tmp_path/'solver/final.npz').read_bytes()==before
