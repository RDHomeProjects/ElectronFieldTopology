"""Renderer-owned preview contract and read-only exports. No plotting imports."""
import io
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
from scipy.ndimage import map_coordinates
from .sf_checkpoints import atomic_json, timestamp
from .sf_dynamics_admission import sha

FIELDS = {'field':3,'field_rate':3,'energy_density':1,'hamiltonian_density':1,'energy_flux':3}


def export_settings(profile):
    cfg = dict(profile.get('export',{}))
    allowed = {'enabled','every_steps','grid','fields','case_ids','solver_grids','vtk'}
    if set(cfg)-allowed: raise ValueError('Unknown visualization export keys: '+str(set(cfg)-allowed))
    cfg = {'enabled':True,'every_steps':4,'grid':None,'fields':['field','energy_density','energy_flux'],
           'case_ids':[],'solver_grids':[],'vtk':True,**cfg}
    if type(cfg['enabled']) is not bool or type(cfg['vtk']) is not bool:
        raise ValueError('Preview enabled/vtk must be booleans')
    if type(cfg['every_steps']) is not int or cfg['every_steps'] < 1:
        raise ValueError('Positive preview step interval required')
    if (not isinstance(cfg['fields'],list) or not cfg['fields'] or len(set(cfg['fields']))!=len(cfg['fields'])
            or not set(cfg['fields'])<=set(FIELDS)):
        raise ValueError('Known unique preview fields required')
    if cfg['grid'] is not None and (len(cfg['grid'])!=3 or any(type(x) is not int or x<1 for x in cfg['grid'])):
        raise ValueError('Three positive preview dimensions required')
    if not isinstance(cfg['case_ids'],list) or not isinstance(cfg['solver_grids'],list):
        raise ValueError('Explicit case/grid selector lists required')
    return cfg


def resample(a, shape, boundary):
    """Display interpolation only; never alter input arrays or solver mesh."""
    if tuple(shape) == a.shape[:3]: return np.array(a,copy=True)
    axes = [np.arange(m)*(n/m if boundary=='periodic' else (n-1)/max(1,m-1))
            for n,m in zip(a.shape[:3],shape)]
    coords = np.array(np.meshgrid(*axes,indexing='ij'))
    mode = 'grid-wrap' if boundary=='periodic' else 'nearest'
    if a.ndim==3:return map_coordinates(a,coords,order=1,mode=mode)
    return np.stack([map_coordinates(a[...,i],coords,order=1,mode=mode) for i in range(a.shape[-1])],axis=-1)


def write_vti(path, arrays, origin, spacing, time, step):
    """VTK XML ImageData, x-fast point ordering, documented ASCII arrays."""
    shape = next(iter(arrays.values())).shape[:3]
    extent = ' '.join(str(x) for n in shape for x in (0,n-1))
    root = ET.Element('VTKFile',type='ImageData',version='1.0',byte_order='LittleEndian')
    image = ET.SubElement(root,'ImageData',WholeExtent=extent,Origin=' '.join(map(str,origin)),Spacing=' '.join(map(str,spacing)))
    piece = ET.SubElement(image,'Piece',Extent=extent)
    attrs = {}
    if 'energy_density' in arrays:attrs['Scalars']='energy_density'
    if 'energy_flux' in arrays:attrs['Vectors']='energy_flux'
    points = ET.SubElement(piece,'PointData',**attrs)
    for name,a in arrays.items():
        components = 1 if a.ndim==3 else a.shape[-1]
        element = ET.SubElement(points,'DataArray',type='Float32',Name=name,NumberOfComponents=str(components),format='ascii')
        buffer = io.StringIO();np.savetxt(buffer,a.reshape(-1,components,order='F'),fmt='%.9g')
        element.text='\n'+buffer.getvalue()
    ET.SubElement(piece,'CellData')
    field = ET.SubElement(image,'FieldData')
    for name,value in [('TimeValue',time),('SolverStep',step)]:
        node = ET.SubElement(field,'DataArray',type='Float64',Name=name,NumberOfTuples='1',format='ascii');node.text=str(value)
    ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)


class PreviewWriter:
    def __init__(self, output, profile, grid, case_id, provenance):
        self.cfg=export_settings(profile);self.grid=grid;self.out=Path(output);self.frames=[]
        self.enabled = (self.cfg['enabled'] and (not self.cfg['case_ids'] or case_id in self.cfg['case_ids'])
                        and (not self.cfg['solver_grids'] or list(grid.shape) in self.cfg['solver_grids']))
        self.shape=tuple(self.cfg['grid'] or grid.shape)
        if self.enabled and any(m>n for m,n in zip(self.shape,grid.shape)):
            raise ValueError('Preview cannot request a finer grid than its solver input')
        self.spacing=tuple(l/(m if grid.boundary=='periodic' or m==1 else m-1) for m,l in zip(self.shape,grid.lengths))
        self.origin=tuple(-l/2 for l in grid.lengths)
        self.manifest={'format':'EFT-preview-v1','created_at':timestamp(),'case_id':case_id,
                       'source_grid':list(grid.shape),'display_grid':list(self.shape),
                       'origin':self.origin,'spacing':self.spacing,'boundary':grid.boundary,
                       'export':self.cfg,'presentation':profile.get('presentation',{}),'provenance':provenance,
                       'frames':self.frames,'scope':'Float32 display samples only; not scientific checkpoints or topology evidence.'}
        if self.enabled:self.out.mkdir(parents=True,exist_ok=False)

    def due(self,step,final=False):
        return self.enabled and (step%self.cfg['every_steps']==0 or final)

    def write(self,step,time,data,metrics,final=False,initial=False):
        if not self.enabled or not (initial or self.due(step,final)):return
        arrays={name:resample(data[name],self.shape,self.grid.boundary).astype(np.float32) for name in self.cfg['fields']}
        name=f'frame-{step:08d}';npz=self.out/(name+'.npz');written=timestamp()
        np.savez_compressed(npz,**arrays,time=float(time),step=int(step),origin=self.origin,spacing=self.spacing,
                            written_utc=written['utc'],written_melbourne=written['melbourne'])
        row={'step':step,'time':time,'recorded_at':written,'npz':npz.name,'npz_sha256':sha(npz),'diagnostics':metrics}
        if self.cfg['vtk']:
            vti=self.out/(name+'.vti');write_vti(vti,arrays,self.origin,self.spacing,time,step)
            row.update(vti=vti.name,vti_sha256=sha(vti))
        self.frames.append(row);atomic_json(self.out/'manifest.json',self.manifest)

    def finish(self,status='complete'):
        if not self.enabled:return
        self.manifest['finished_at']=timestamp();self.manifest['status']=status
        atomic_json(self.out/'manifest.json',self.manifest)
        if self.cfg['vtk']:
            root=ET.Element('VTKFile',type='Collection',version='0.1',byte_order='LittleEndian')
            collection=ET.SubElement(root,'Collection')
            for f in self.frames:ET.SubElement(collection,'DataSet',timestep=str(f['time']),group='',part='0',file=f['vti'])
            ET.ElementTree(root).write(self.out/'series.pvd',encoding='utf-8',xml_declaration=True)
