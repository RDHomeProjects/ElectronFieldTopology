# Offline renderer and solver export profile

Prepared: 2026-11-02T12:37:39.053069+00:00 UTC; 2026-11-02T23:37:39.053069+11:00 Australia/Melbourne. The first renderer runs **after** the
solver. It is a separate CLI application using the locked Matplotlib/Pillow stack,
without a GPU/OpenGL server, ParaView installation or new numerical dependency.

## Configuration ownership

[The basic profile](../experiments/configs/renderers/basic.json) has two sections.

| Section | Read by | Settings |
|---|---|---|
| export | Solver's preview writer | enabled; every_steps; preview grid; fields; selected case_ids and solver_grids; VTK output |
| presentation | Renderer only | frame_stride; max_frames; coarser display grid; field/component; colour count/map; contour fraction; camera; frame rate and image size |

Neither section contains solver dt, calculation grid, precision, force terms,
tolerances or stopping decisions. Unknown export/physical keys are rejected rather
than accidentally applied. Invalid display-only settings do not alter a solver run.
All requested physical steps and calculation resolutions still execute when their
preview is excluded. Initial and final display frames are included with normal
cadence exports. Actual saved times are recorded; integration steps are not adjusted
to hit display times. Unrecorded intermediate states cannot be recovered by changing
a renderer setting later.

`colors` is the number of field colormap levels: 8, 16, 32 etc.; 0 selects a continuous
map. It does not quantize physics or preview scalar values. The GIF can contain extra
annotation/antialiasing colours. `grid` in presentation may reduce the saved preview
sampling, but cannot request unavailable higher resolution. Presentation changes
require only rerendering. Export changes apply to the next calculation/export pass.

## Data and external applications

Each preview frame is a Float32 NPZ plus optional standard VTK XML ImageData (.vti).
A .pvd collection records physical model times for external ParaView playback.
Vector components use x-fast VTK point ordering, independently tested on known arrays.
Available arrays: field n (internal direction), field_rate dn/dt, continuum
energy_density, energy_flux and optional discrete hamiltonian_density. Physics states
and checkpoints remain float64 at the independently specified calculation grid.

manifest.json records source run/config identity, preview dimensions, actual times,
frame SHA-256 hashes, UTC/Melbourne dates, and scalar diagnostics measured on the full
calculation. The renderer authenticates NPZ hashes and never rewrites source files.
No visualization array is reused for force calculations, acceptance or topology tests.

The basic renderer displays a fixed-threshold energy isosurface coloured by an
internal-field component, a central slice, and full-calculation conservation curves.
Colour range and energy threshold are fixed across selected frames. This uses a
display-only linear marching-tetrahedra surface, not a knot-invariant certificate.
Maximum triangle count and coarser sampling are presentation approximations only.

Outputs: wave.gif, preview.png, render.json and **viewer.html**. The HTML contains
its own PNG frames and works offline without a server/CDN. It provides play/pause,
frame stepping, a time slider and playback-speed selection. Its camera is fixed at
render time; use a new camera profile to rerender, or open the PVD in ParaView for
interactive 3D camera control. Movie playback speed is separate from simulated time.
Every frame includes simulation time/model units, source dimensions and run/render
UTC/Melbourne timestamps. No interpolated physical-time states are invented.

## First local trial

Run from a clean committed handoff checkout with frozen dependencies:

```bash
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1 uv run --frozen python -m electron_field_topology.sf_time_run \
  --config experiments/configs/sf-time/wave-demo.json \
  --profile experiments/configs/renderers/basic.json --output artifacts/my-wave

uv run --frozen python -m electron_field_topology.sf_renderer \
  --input artifacts/my-wave --output artifacts/my-render

xdg-open artifacts/my-render/viewer.html
```

The default trial evolves a 25³ periodic wave using the full nonlinear physical-time
integrator and exports 26 sampled 17³ frames over 75 steps, t=0..1.5 model units.
It requires none of the retained workstation soliton fields. The renderer and solver
do not run concurrently. The handoff also contains a small completed example so the
renderer can be tested without running the solver first.

Change the field palette without another solve:

```bash
uv run --frozen python -m electron_field_topology.sf_renderer \
  --input artifacts/my-wave --output artifacts/my-render-8 --colors 8
```

For an installed ParaView, `paraview artifacts/my-wave/preview/series.pvd` opens the
same saved time series. This is optional; the default renderer/player needs no such
installation. No native ParaView GUI benchmark or full paper algorithm reproduction
is claimed by the XML export tests.

## Sources and interpretation

Helgeland and Elboth, *High-Quality and Interactive Animations of 3D Time-Varying Vector
Fields* (2006), [DOI](https://doi.org/10.1109/TVCG.2006.95),
[author-uploaded full text](https://www.researchgate.net/publication/6723735_High-Quality_and_Interactive_Animations_of_3D_Time-Varying_Vector_Fields),
motivate separating data preparation and rendering and controlling visual clutter.
This basic surface/slice renderer does not implement their particle-advection and
texture-convolution algorithm. An internal SF unit vector is not a material velocity;
no particle trajectory is inferred from its arrows.

VTK's [XML specification](https://docs.vtk.org/en/latest/vtk_file_formats/vtkxml_file_format.html)
defines ImageData and point arrays; ParaView's [animation guide](https://docs.paraview.org/en/latest/UsersGuide/animation.html)
defines time-series playback. Matplotlib's [PillowWriter](https://matplotlib.org/stable/api/_as_gen/matplotlib.animation.PillowWriter.html)
provides offline GIF output. Scalar diagnostics remain authoritative over appearance.

## ParaView display setup verified on the workstation

Recorded: UTC 2026-11-02T15:29:15.448567+00:00; Australia/Melbourne 2026-11-03T02:29:15.448567+11:00.

Open the preview `series.pvd` with all accompanying VTI files in the same folder.
Select the source and click Apply. In the representation dropdown change **Outline
to Volume**, then select **energy_density** for colouring. Reset Camera (R with the
pointer over the view), then Play. The outline box alone does not display its interior
field. Slice offers a cross-section if volume opacity hides detail.

The maintainer confirmed Outline -> Volume resolved the initial blank/outline-only
view in ParaView5.11.2. This establishes display compatibility for the wave example,
not numerical/scientific acceptance of future knot trajectories.
