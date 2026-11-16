"""Fail-closed metadata and evidence regressions; synthetic diagnostics only."""
from dataclasses import replace
import pytest
from mge_planning.terrain_diagnostics import TerrainEvidence,DiscontinuityEvidence,diagnose
from mge_planning.local_surface import MobilityEvaluation,LocalSurface,evaluate_surface
from tests.planning.test_local_surface import setup_case

@pytest.mark.parametrize("kind",["human","rover"])
def test_coarse_native_support_cannot_certify_centimetre_jump(kind):
 g,p,r,s,l=setup_case(kind,"flat")
 e=TerrainEvidence("SYNTHETIC",20.,"coarse-source")
 d=DiscontinuityEvidence(1.,1.01,0.,.35,e)
 with pytest.raises(ValueError): diagnose(g,p,(1,1),(1,2),e,discontinuity=d)

@pytest.mark.parametrize("field,value",[("source_id",True),("native_resolution_m",True)])
def test_diagnostic_metadata_rejects_boolean(field,value):
 args=dict(source_kind="SYNTHETIC",native_resolution_m=.01,source_id="source")
 args[field]=value
 with pytest.raises(ValueError):TerrainEvidence(**args)

@pytest.mark.parametrize("kind",["human","rover"])
def test_surface_frame_and_authorization_are_fail_closed(kind):
 g,p,r,s,l=setup_case(kind,"flat")
 with pytest.raises(ValueError):replace(s,grid=replace(s.grid,frame_id="other"))
 out=evaluate_surface(terrain=g,request=r,profile=p,surface=s,limits=l,vertical_datum=s.vertical_datum,allow_legacy_cost_model=True)
 with pytest.raises(ValueError):replace(out,authorization=True)
 with pytest.raises(ValueError):replace(g,frame_id="other")
 with pytest.raises(ValueError):replace(s,frame_id="other")

@pytest.mark.parametrize("kind",["human","rover"])
def test_unobserved_boundary_stencil_is_forbidden(kind):
 g,p,r,s,l=setup_case(kind,"flat")
 out=evaluate_surface(terrain=g,request=r,profile=p,surface=s,limits=l,vertical_datum=s.vertical_datum,allow_legacy_cost_model=True)
 assert out.candidate.status.value=="FEASIBLE"
 assert (out.evaluation_grid.traversability[0,:]==100).all()
 assert (out.evaluation_grid.traversability[-1,:]==100).all()
 assert (out.evaluation_grid.traversability[:,0]==100).all()
 assert (out.evaluation_grid.traversability[:,-1]==100).all()
 assert (s.grid.traversability==0).all()

@pytest.mark.parametrize("kind",["human","rover"])
def test_surface_has_no_hidden_replan_policy_dependency(kind,monkeypatch):
 from mge_planning.replan import ReplanPolicy
 monkeypatch.setattr(ReplanPolicy,"evaluate",lambda *a,**k:pytest.fail("unexpected policy dependency"))
 g,p,r,s,l=setup_case(kind,"flat")
 from tests.planning.terrain_fixtures import PROFILES
 out=evaluate_surface(terrain=g,request=r,profile=p,surface=s,limits=l,vertical_datum=s.vertical_datum,scientific_profile=PROFILES[r.agent_id],allow_legacy_cost_model=False)
 assert out.candidate.status.value=="FEASIBLE"
 assert out.authorization is False


@pytest.mark.parametrize("kind",["human","rover"])
def test_freshness_is_not_request_authorization(kind):
 from tests.planning.terrain_fixtures import PROFILES
 g,p,r,s,l=setup_case(kind,"flat")
 out=evaluate_surface(terrain=g,request=r,profile=p,surface=s,limits=l,vertical_datum=s.vertical_datum,scientific_profile=PROFILES[r.agent_id])
 assert out.candidate.status.value=="FEASIBLE"
 changed=replace(out,candidate=replace(out.candidate,request_id="another-request"))
 assert changed.is_current(s,g,l,p,scientific_profile=PROFILES[r.agent_id])
 assert changed.authorization is False
 with pytest.raises(ValueError):replace(changed,authorization=True)
