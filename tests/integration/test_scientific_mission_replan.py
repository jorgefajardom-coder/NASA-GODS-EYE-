"""SIMULATED single-human ROS control-loop regression, not scientific acceptance.

Production planner, MissionNode/Manager, policy, kinematic executor and recorder.
The synthetic public-batch publisher is controlled test input, not NASA terrain
or a physical observation producer. Agreement is asserted for this fixture only.
"""
from copy import deepcopy
import hashlib,json,math,os,signal,struct,subprocess,time
from pathlib import Path
import pytest,yaml
rclpy=pytest.importorskip('rclpy')
from builtin_interfaces.msg import Time
from geometry_msgs.msg import Point as WirePoint
from mge_interfaces.msg import AgentState,TerrainMeta,MissionState,MissionEvent
from mge_interfaces.srv import SetMissionGoal
from nav_msgs.msg import OccupancyGrid,Path as WirePath
from sensor_msgs.msg import Image
from rosgraph_msgs.msg import Clock
from rclpy.parameter import Parameter
from rclpy.executors import MultiThreadedExecutor
from rclpy.qos import QoSProfile,ReliabilityPolicy,DurabilityPolicy
from mge_mission.manager import MissionManager
from mge_mission.models import load_profiles
from mge_mission.types import Point
from mge_mission.node import create_node_class
from mge_planning.node import make_node_class
from mge_planning.mission_replan import ScientificReplanBridge
from mge_gateway.contract_replay import read_package,read_public_rasters,to_viewer

ROOT=Path(__file__).resolve().parents[2]
RUN='simulated-human-scientific-replan'

@pytest.mark.parametrize('scenario',['detour','contingency-return','blocked'])
def test_real_authority_stops_before_scientific_replan_and_records_same_run(tmp_path,scenario):
    RUN='simulated-human-scientific-replan-'+scenario
    rclpy.init();owned=[];children=[];calls=[];agents=[];events=[];states=[];paths=[]
    now=[100_000_000_000];version=[1];map_stamp=[100_000_000_000];tick_count=[0];last_tick=[time.monotonic()]
    profiles=load_profiles(ROOT/'config/scenario_demo.yaml')
    manager=MissionManager(RUN,profiles,Point(2.5,5.5,0.),.5,allow_illustrative=True,
        primary_service_time_s=0.,primary_service_activity='wait',planner_model_agreed=True)
    mission=create_node_class(replan_factory=ScientificReplanBridge)(manager=manager,parameter_overrides=[
        Parameter('use_sim_time',value=True),Parameter('profiles_path',value=str(ROOT/'config/scenario_demo.yaml')),
        Parameter('replan_policy_file',value=str(ROOT/'config/replan_policy.illustrative.json'))])
    class Planner(make_node_class()):
        def _plan(self,request,response):
            calls.append((deepcopy(request),None if mission._stop is None else mission._stop.acknowledged))
            return super()._plan(request,response)
    planner=Planner(parameter_overrides=[Parameter('scientific_profiles_path',value=str(ROOT/'config/scenario_demo.yaml')),
        Parameter('allow_illustrative_profiles',value=True),Parameter('snapshot_contract_confirmed',value=True),
        Parameter('allow_continuous_starts',value=True),Parameter('use_sim_time',value=True)])
    peer=rclpy.create_node('scientific_replan_public_input_probe');owned=[mission,planner,peer]
    executor=MultiThreadedExecutor(num_threads=4)
    for node in owned:executor.add_node(node)
    retained=QoSProfile(depth=1,reliability=ReliabilityPolicy.RELIABLE,durability=DurabilityPolicy.TRANSIENT_LOCAL)
    reliable=QoSProfile(depth=50,reliability=ReliabilityPolicy.RELIABLE)
    clock=peer.create_publisher(Clock,'/clock',QoSProfile(depth=1,reliability=ReliabilityPolicy.BEST_EFFORT))
    meta_pub=peer.create_publisher(TerrainMeta,'/mge/terrain/meta',retained)
    image_pub={name:peer.create_publisher(Image,'/mge/terrain/'+name,retained) for name in ('prior','belief','sigma','observed')}
    masks={kind:peer.create_publisher(OccupancyGrid,'/mge/terrain/traversability/'+kind,retained) for kind in ('human','rover','drone')}
    peer.create_subscription(AgentState,'/mge/agents/human_1/state',lambda m:agents.append(deepcopy(m)),reliable)
    peer.create_subscription(MissionEvent,'/mge/mission/events',lambda m:events.append(deepcopy(m)),reliable)
    peer.create_subscription(MissionState,'/mge/mission/state',lambda m:states.append(deepcopy(m)),retained)
    peer.create_subscription(WirePath,'/mge/planner/active_path',lambda m:paths.append(deepcopy(m)),retained)
    goal=peer.create_client(SetMissionGoal,'/mge/mission/set_goal')
    def stamp(ns):return Time(sec=ns//10**9,nanosec=ns%10**9)
    def batch():
        meta=TerrainMeta();meta.header.frame_id='map';meta.header.stamp=stamp(map_stamp[0]);meta.run_id=RUN
        meta.dataset_id='MOCK-synthetic-control-loop';meta.map_version=version[0];meta.rows=meta.cols=20
        meta.resolution_m=1.;meta.nodata_value=-9999.;meta.crs='LOCAL_ENU_SIMULATED';meta.vertical_datum='synthetic flat software-test datum'
        meta.checksum_sha256=hashlib.sha256(bytes(1600)).hexdigest();meta.sources=['SIMULATED deterministic test grid; not NASA observational data']
        meta_pub.publish(meta)
        for name,pub in image_pub.items():
            if name=='observed':
                data=[0]*400
                if version[0]>1:
                    for row in range(20):
                        for col in range(20):
                            if scenario=='blocked' or (scenario=='contingency-return' and col==12) or (row,col)==(5,12):data[row*20+col]=1
                msg=Image(header=meta.header,height=20,width=20,encoding='mono8',step=20,data=bytes(data))
            else:
                values=[.25 if name=='sigma' else 0.]*400
                msg=Image(header=meta.header,height=20,width=20,encoding='32FC1',step=80,data=struct.pack('<400f',*values))
            pub.publish(msg)
        for kind,pub in masks.items():
            data=[0]*400
            if version[0]>1:
                for row in range(20):
                    for col in range(20):
                        if scenario=='blocked' or (scenario=='contingency-return' and col==12) or (row,col)==(5,12):data[row*20+col]=100
            mask=OccupancyGrid(header=meta.header,data=data);mask.info.height=mask.info.width=20
            mask.info.resolution=1.;mask.info.origin.orientation.w=1.;pub.publish(mask)
    def tick():
        time.sleep(max(0.,.02-(time.monotonic()-last_tick[0])));last_tick[0]=time.monotonic()
        now[0]+=50_000_000;clock.publish(Clock(clock=stamp(now[0])));tick_count[0]+=1
        if tick_count[0]%5==0:batch()
    def until(predicate,label,timeout=18.):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            tick();executor.spin_once(timeout_sec=.01)
            if predicate():return
        raise AssertionError(label+'; state='+str(manager.snapshot())+'; calls='+str([(c.request_id,s) for c,s in calls]))
    def child(executable,arguments,logname):
        stream=(tmp_path/logname).open('w');p=subprocess.Popen(['ros2','run',*executable,'--ros-args',*arguments],cwd=ROOT,
            stdout=stream,stderr=subprocess.STDOUT,start_new_session=True);children.append((p,stream));return p
    try:
        until(lambda:manager.map_version==1 and mission._replan.store.snapshot('human')[0] is not None,'initial coherent map')
        agent_file=tmp_path/'agents.yaml';agent_file.write_text(yaml.safe_dump({'agents':[dict(id='human_1',kind='HUMAN',
            x_m=2.5,y_m=5.5,z_m=0.,time_budget_s=3600.,energy_budget_wh=600.,oxygen_budget_l=150.)]}))
        child(['mge_gateway','replay_recorder'],['-p','run_id:='+RUN,'-p','use_sim_time:=true','-p','source_mode:=MOCK','-p','record_dir:='+str(tmp_path/'recorded')],'recorder.log')
        child(['mge_sim','kinematic_executor'],['-p','run_id:='+RUN,'-p','use_sim_time:=true','-p','agents_file:='+str(agent_file)],'executor.log')
        until(lambda:len(manager.snapshot().agents)==1 and goal.service_is_ready() and planner.store.snapshot('human')[0] is not None,'actual executor state and service')
        request=SetMissionGoal.Request();request.request_id='single-human-goal';request.run_id=RUN;request.primary_agent_id='human_1'
        request.base=WirePoint(x=2.5,y=5.5,z=0.);request.goal=WirePoint(x=15.5,y=5.5,z=0.);request.mode='FAST'
        request.time_budget_s,request.energy_budget_wh,request.oxygen_budget_l=3600.,600.,150.
        request.reserve_time_s,request.reserve_wh,request.reserve_oxygen_l=360.,60.,15.
        future=goal.call_async(request);until(future.done,'goal accepted');assert future.result().accepted
        until(lambda:manager.snapshot().route_id and any(m.mode=='MOVING' and m.pose.position.x>2.8 for m in agents),'authorized motion')
        old_route=manager.snapshot().route_id;version[0]=2;map_stamp[0]=now[0];batch()
        until(lambda:any(e.reason_code=='STOP_REQUESTED' for e in events),'stop request')
        until(lambda:manager.snapshot().map_version==2 and (manager.snapshot().mission_state=='BLOCKED' if scenario=='blocked' else manager.snapshot().route_id not in ('',old_route)),'fresh authorization or explicit rejection')
        fresh=manager.snapshot().active_route;new_call,stopped=calls[-1]
        assert stopped is True
        assert new_call.map_version==2 and new_call.start.x>2.5
        assert new_call.reserve_time_s==360. and new_call.reserve_wh==60. and new_call.reserve_oxygen_l==15.
        assert new_call.time_budget_s<3600. and new_call.energy_budget_wh<600. and new_call.oxygen_budget_l<150.
        halted=[m for m in agents if m.mode=='HALTED']
        assert halted and any(math.dist((m.pose.position.x,m.pose.position.y,m.pose.position.z),
            (new_call.start.x,new_call.start.y,new_call.start.z))<1e-6 for m in halted)
        reasons=[e.reason_code for e in events]
        assert reasons.index('STOP_REQUESTED')<reasons.index('STOP_ACKNOWLEDGED')
        assert any(not p.poses for p in paths)
        target_x=15.5 if scenario=='detour' else 2.5
        if scenario=='blocked':
            assert not manager.snapshot().route_id
            assert manager.snapshot().reason_code in {'NO_ADMISSIBLE_PATH','UNVERIFIED_CORRIDOR','INVALID_START','INVALID_START_Z','NO_ADMISSIBLE_START_CONNECTOR'}
            assert agents[-1].mode=='HALTED'
        else:
            until(lambda:any(m.mode=='IDLE' and abs(m.pose.position.x-target_x)<1e-5 and abs(m.pose.position.y-5.5)<1e-5 for m in agents),'resumed motion and actual arrival')
        if scenario!='detour':
            assert not new_call.require_return and new_call.service_time_s==0.
            assert new_call.goal.x==2.5 and manager.snapshot().active_task_kind=='return'
        else:
            assert new_call.require_return and manager.replan_context()[0].candidate_phase=='OUTBOUND'
        assert manager.snapshot().mission_state!='COMPLETE'
        for _ in range(10):tick();executor.spin_once(timeout_sec=.01)
        report=dict(run_id=RUN,source=os.environ.get('MGE_TEST_SOURCE_BASE','working tree; consult validation source lock'),scope='SIMULATED one-human control loop; no scientific/physical/three-role completion',
            real_nodes=['MissionManager','MissionNode','PlanningNode','ReplanPolicy','KinematicExecutor','ReplayRecorder'],
            scenario=scenario,original_route=old_route,replanned_route=fresh.route_id if fresh else None,actual_stopped_start=[new_call.start.x,new_call.start.y,new_call.start.z],
            remaining=[new_call.time_budget_s,new_call.energy_budget_wh,new_call.oxygen_budget_l],
            map_version=2,request_phase='RETURN' if not new_call.require_return else 'OUTBOUND',ros_states=len(agents),halted_states=len(halted),
            reasons=reasons,mission_complete=False,actual_arrival=scenario!='blocked',planner_calls=len(calls),final_state=manager.snapshot().mission_state,final_reason=manager.snapshot().reason_code)
        (tmp_path/'control-loop.json').write_text(json.dumps(report,indent=2)+'\n')
    finally:
        for p,stream in reversed(children):
            if p.poll() is None:
                os.killpg(p.pid,signal.SIGINT)
                try:p.wait(timeout=8)
                except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
            stream.close()
        executor.shutdown(timeout_sec=4)
        for node in owned:node.destroy_node()
        rclpy.shutdown()
    package=tmp_path/'recorded'/RUN
    manifest,records,snapshot=read_package(package);public=read_public_rasters(package,manifest)
    viewer=to_viewer(manifest,records,snapshot,public);assert viewer['status']=='READY'
    target=tmp_path/'viewer';target.mkdir()
    for name in ('manifest','timeline','routes','rasters'):(target/(name+'.json')).write_text(json.dumps(viewer[name],allow_nan=False)+'\n')
    assert {1,2}<=set(int(v) for v in public['versions'])
