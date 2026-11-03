"""Linux process identity handling; no external application or process is controlled."""
from pathlib import Path
import os
from electron_field_topology.sf_motion_local import process_identity,alive


def test_start_time_identity_handles_parentheses_and_zombies(monkeypatch):
    fields=['S']+['0']*18+['123456']+['0']*5
    monkeypatch.setattr(Path,'read_text',lambda self:'boot-1' if str(self).endswith('boot_id') else '17 (a name with ) parentheses) '+' '.join(fields))
    namespace=['pid:[123]'];monkeypatch.setattr(os,'readlink',lambda path:namespace[0])
    assert process_identity(17)=='boot-1:pid:[123]:123456'
    assert alive({'pid':17,'process_identity':'boot-1:pid:[123]:123456'})
    assert not alive({'pid':17,'process_identity':'999'})
    namespace[0]='pid:[456]'
    assert not alive({'pid':17,'process_identity':'boot-1:pid:[123]:123456'})
    fields[0]='Z';assert process_identity(17) is None


def test_missing_process_never_authorizes_a_signal(monkeypatch):
    def missing(self):raise FileNotFoundError
    monkeypatch.setattr(Path,'read_text',missing)
    assert not alive({'pid':17,'process_identity':None})


def test_unverifiable_background_child_is_stopped_with_foreground_fallback(tmp_path,monkeypatch):
    import pytest
    import electron_field_topology.sf_motion_local as local
    class Child:
        pid=17
        terminated=False
        def terminate(self):self.terminated=True
        def wait(self):return 0
    child=Child()
    monkeypatch.setattr(local,'ART',tmp_path/'artifacts')
    monkeypatch.setattr(local,'process_identity',lambda pid:None)
    monkeypatch.setattr(local.subprocess,'Popen',lambda *args,**kwargs:child)
    with pytest.raises(ValueError,match='foreground'):local.launch(tmp_path/'cfg',tmp_path/'profile')
    assert child.terminated
