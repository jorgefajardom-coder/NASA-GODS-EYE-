"""Advisory policy adapter. The injected MissionNode/Manager remain the sole authority."""
import json,math
from pathlib import Path
from mge_mission.models import export_planner_profiles
from .adapter import SnapshotStore
from .core import MotionProfile,PlanRequest,ResourceBudget,RouteResult,RouteStatus,SearchLimits
from .replan import ReplanPolicy,ReplanConfig,ReplanState,ReplanEvent,EventKind,MissionPhase,RemainingResources

def request(value):
    return PlanRequest(run_id=value.run_id,request_id=value.request_id,agent_id=value.agent_id,
        agent_kind=value.agent_kind.lower(),start=value.start.coordinates(),goal=value.goal.coordinates(),
        return_to=value.return_to.coordinates(),require_return=value.require_return,mode=value.mode,
        map_version=value.map_version,service_time_s=value.service_time_s,reserve_time_s=value.reserve_time_s,
        budget=ResourceBudget(value.agent_kind.lower(),value.time_budget_s,value.energy_budget_wh,
                             value.reserve_wh,value.oxygen_budget_l,value.reserve_oxygen_l))

def result(value):
    return RouteResult(run_id=value.run_id,request_id=value.request_id,route_id=value.route_id,
        agent_id=value.agent_id,mode=value.mode,map_version_used=value.map_version_used,
        status=RouteStatus(value.status),reason_code=value.reason_code,detail=value.detail,
        outbound_path=tuple(p.coordinates() for p in value.outbound_path),
        return_path=tuple(p.coordinates() for p in value.return_path),travel_time_s=value.travel_time_s,
        energy_est_wh=value.energy_est_wh,oxygen_est_l=value.oxygen_est_l,
        min_clearance_m=value.min_clearance_m,reserve_time_s=value.reserve_time_s,
        reserve_wh=value.reserve_wh,reserve_oxygen_l=value.reserve_oxygen_l)

def on_segment(p,a,b):
    d=tuple(y-x for x,y in zip(a,b));n=sum(x*x for x in d)
    if n==0:return math.dist(p,a)<=1e-5
    t=sum((x-y)*z for x,y,z in zip(p,a,d))/n
    return -1e-8<=t<=1+1e-8 and math.dist(p,tuple(x+t*y for x,y in zip(a,d)))<=1e-5

class ScientificReplanBridge:
    def __init__(self,node,configuration):
        from sensor_msgs.msg import Image
        from nav_msgs.msg import OccupancyGrid
        from rclpy.qos import QoSProfile,ReliabilityPolicy,DurabilityPolicy
        config=json.loads(Path(configuration).read_text())
        if config.get("status")!="illustrative" or config.get("schema_version")!="mge-replan-policy-1.0.0":
            raise ValueError("an explicit illustrative replan policy is required")
        self.node=node;self.store=SnapshotStore();self.policy=ReplanPolicy(ReplanConfig(**config['policy']),limits=SearchLimits(timeout_s=.25,max_labels=20000))
        projected=export_planner_profiles(node._profiles)['profiles']
        self.motion={key:MotionProfile(**value) for key,value in projected.items()}
        self.active=None;self.template=None;self.cursor=1;self.sequence=0;self.cached_key=None;self.cached_grid=None;self.last_evaluation=None
        q=QoSProfile(depth=1,reliability=ReliabilityPolicy.RELIABLE,durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.subscriptions=[node.create_subscription(Image,'/mge/terrain/'+name,
              lambda message,layer=name:self.ingest('image',layer,message),q) for name in ('belief','sigma')]
        self.subscriptions += [node.create_subscription(OccupancyGrid,'/mge/terrain/traversability/'+kind,
              lambda message,kind=kind:self.ingest('mask',kind,message),q) for kind in ('human','rover','drone')]

    def ready(self):
        snapshot=self.node._manager.snapshot()
        agent=next((a for a in snapshot.agents if a.agent_id==snapshot.primary_agent_id),None)
        with self.store.lock:
            return (agent is not None and self.store.meta is not None and not self.store.error
                and self.store.meta.map_version==snapshot.map_version
                and {'belief','sigma',agent.kind} <= set(self.store.layers))

    def bind(self):
        context=self.node._manager.replan_context()
        if context is None:return
        plan,route,_=context
        if self.active is None or self.active[1].route_id!=route.route_id:self.cursor=1
        self.active=(plan,route)
        if self.template is None:self.template=request(plan)

    def meta(self,message):
        self.store.ingest_meta(message)

    def ingest(self,kind,name,message):
        with self.node._lock:
            try:
                accepted=(self.store.ingest_image(name,message) if kind=='image' else self.store.ingest_mask(name,message))
                if accepted and self.store.batch_key != self.cached_key and self.ready():self.evaluate('MAP')
            except (ValueError,TypeError,KeyError) as exc:
                self.store.invalidate(str(exc))
                self.node._policy_stop('POLICY_SNAPSHOT_INVALID')

    def evaluate(self,kind):
        self.bind()
        if self.active is None or self.template is None:return
        plan,route=self.active;manager=self.node._manager;snapshot=manager.snapshot()
        if snapshot.mission_state in {'COMPLETE','ABORTED'}:return
        agent=next((a for a in snapshot.agents if a.agent_id==plan.agent_id),None)
        if agent is None:return
        if self.store.batch_key != self.cached_key:
            grid,reason=self.store.snapshot(agent.kind)
            if grid is None:return
            self.cached_key,self.cached_grid=self.store.batch_key,grid
        grid=self.cached_grid
        if grid is None or grid.map_version!=snapshot.map_version:return
        current=manager.remaining_primary_budgets()
        pose=agent.position.coordinates();active=result(route);leg=active.outbound_path
        # Monotonic first matching forward segment, never nearest-waypoint snapping.
        for index in range(max(0,self.cursor-1),max(0,len(leg)-1)):
            if on_segment(pose,leg[index],leg[index+1]):self.cursor=index+1;break
        remaining=RemainingResources(agent.kind,current.time_s,current.energy_wh,current.reserve_wh,current.oxygen_l,current.reserve_oxygen_l)
        state=ReplanState(self.template,request(plan),active,MissionPhase(plan.candidate_phase),pose,
                         self.cursor,remaining,plan.service_time_s)
        signature=(self.cached_key,route.route_id,plan.candidate_phase,pose,self.cursor,remaining,plan.service_time_s)
        if signature==self.last_evaluation and self.policy._pending is None:return
        self.last_evaluation=signature
        self.sequence+=1
        decision=self.policy.evaluate(terrain=grid,profile=self.motion[plan.agent_id],state=state,
            event=ReplanEvent(f'{snapshot.run_id}:policy:{self.sequence}',snapshot.run_id,snapshot.map_version,EventKind(kind)),
            now_s=self.node._clock_s,scientific_profile=manager.profiles[plan.agent_id],service_activity=plan.service_activity)
        if decision.invalidate_active or decision.action.value=='STOP_REQUIRED':
            phase=decision.candidate_phase.value if decision.candidate_phase is not None else plan.candidate_phase
            self.node._policy_stop(decision.reason_code,candidate_phase=phase)
        elif decision.action.value=='REPLAN':
            self.node._policy_stop(decision.reason_code,candidate_phase=decision.candidate_phase.value if decision.candidate_phase else plan.candidate_phase)
