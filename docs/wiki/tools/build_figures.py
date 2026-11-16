"""Rebuild pedagogical Wiki graphics. AI-use declarations: ../../AI_USAGE.md.

Documentation only: reads frozen public/model inputs; never runs a mission.
Requirements: matplotlib, numpy, Pillow. Optional isolated local dependency path.
"""
from __future__ import annotations

import hashlib
import io
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LOCAL_DEPS = ROOT / ".local/wiki-figure-deps"
if LOCAL_DEPS.exists():
    sys.path.insert(0, str(LOCAL_DEPS))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Rectangle
import numpy as np
from PIL import Image, ImageDraw, ImageFont, PngImagePlugin

sys.path.insert(0, str(ROOT / "src/mge_mission"))
from mge_mission.models import estimate_activity, estimate_segment, load_profiles

WIKI = ROOT / "docs/wiki"
OUT = WIKI / "assets"
EXPERIMENT = ROOT / "evidence/mission-cost-experiment-20261115-local-v2/experiment.json"
DEM = ROOT / "evidence/overnight-mission-research-20261115-v3/public/bunsen-512.npz"
PROFILES = ROOT / "config/science_profiles.proposed.json"
BLUE, ORANGE, GREEN, PURPLE, RED = "#20639b", "#c66c21", "#28766b", "#76539c", "#b24747"
INK, PAPER = "#253647", "#fbfaf7"
plt.rcParams.update({"font.size": 12, "axes.labelsize": 12, "axes.titlesize": 15,
                     "figure.facecolor": PAPER, "axes.facecolor": PAPER,
                     "text.color": INK, "axes.labelcolor": INK,
                     "axes.spines.top": False, "axes.spines.right": False})
FONT = ImageFont.truetype(str(Path(matplotlib.get_data_path()) / "fonts/ttf/DejaVuSans.ttf"), 20)
RECORDS = []


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def figure(title, subtitle="", width=11, height=6.5):
    fig = plt.figure(figsize=(width, height), dpi=120)
    title_size = min(21, 21 * width / 11 * 72 / max(len(title), 72))
    fig.suptitle(title, x=.065, y=.965, ha="left", fontsize=title_size)
    if subtitle:
        fig.text(.065, .91, subtitle, fontsize=11)
    return fig


def stamped(fig, kind):
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", facecolor=PAPER)
    plt.close(fig)
    image = Image.open(buffer).convert("RGB")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, image.height - 48, image.width, image.height), fill="#1b2633")
    draw.text((22, image.height - 36), f"AI-generated | {kind}", font=FONT, fill="white")
    return image


def register(name, image, kind, source, frames=1):
    path = OUT / name
    if path.suffix == ".png":
        meta = PngImagePlugin.PngInfo()
        meta.add_text("Description", f"AI-generated; {kind}; {source}")
        meta.add_text("Software", "OpenAI Codex-assisted reproducible Wiki figure script")
        image.save(path, pnginfo=meta)
    RECORDS.append({"file": name, "kind": kind, "source": source, "frames": frames,
                    "visible_watermark": f"AI-generated | {kind}", "sha256": sha(path)})


def save(fig, name, kind="Conceptual diagram", source="Project explanatory schematic"):
    register(name, stamped(fig, kind), kind, source)


def animation(name, frames, kind, source, duration=220):
    path = OUT / name
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=duration,
                   loop=0, disposal=2, optimize=False,
                   comment=f"AI-generated; {kind}; {source}".encode())
    register(name, frames[0], kind, source, len(frames))
    register(name.replace(".gif", "-poster.png"), frames[-1], kind, source)


def box(ax, xy, text, width=.25, height=.17, color=BLUE):
    x, y = xy
    ax.add_patch(FancyBboxPatch((x, y), width, height, boxstyle="round,pad=.012",
                               facecolor=color + "17", edgecolor=color, linewidth=1.7, clip_on=False))
    ax.text(x + width / 2, y + height / 2, text, ha="center", va="center", fontsize=12)


def arrow(ax, start, end, color=INK):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=16,
                                linewidth=1.7, color=color))


def diagrams():
    fig = figure("From a scientific question to an accountable decision",
                 "Learning objective: follow the role of evidence through one mission cycle")
    ax = fig.add_axes([.06, .2, .88, .65]); ax.axis("off")
    items = [(.02,.65,"Scientific question\nWhat contrast matters?",BLUE),
             (.37,.65,"Orbital prior\nWhat is estimated?",PURPLE),
             (.72,.65,"Candidate itinerary\nCan we return?",GREEN),
             (.72,.16,"Local observation\nWhat changed?",ORANGE),
             (.37,.16,"Mission decision\nKeep, divert or return",BLUE),
             (.02,.16,"Recorded result\nWhat can we conclude?",GREEN)]
    for x,y,t,c in items: box(ax,(x,y),t,color=c)
    for a,b in [((.28,.735),(.35,.735)),((.63,.735),(.70,.735)),((.845,.63),(.845,.35)),
                ((.70,.245),(.64,.245)),((.35,.245),(.29,.245))]: arrow(ax,a,b)
    fig.text(.07,.14,"The question determines the observation; the resource ledger constrains the action.",fontsize=12)
    save(fig,"research-loop.png")

    fig=figure("Scientific interest is a chain of evidence",
               "Three Jezero priorities; the columns distinguish published findings from proposed mission questions")
    ax=fig.add_axes([.05,.16,.9,.68]);ax.axis("off")
    rows=[("Bright Angel–Neretva","Mineral / organic associations","Compare exposed contacts\nand alteration textures"),
          ("Hawksbill–Hogwallow","Delta-front stratigraphy","Compare beds, clasts\nand lateral facies"),
          ("Bunsen–Margin Unit","Carbonate / silica context","Document rock textures\nand candidate sample context")]
    for i,(site,finding,question) in enumerate(rows):
        y=.73-i*.28
        box(ax,(.01,y),site,.28,.19,BLUE);box(ax,(.36,y),finding,.28,.19,GREEN)
        box(ax,(.71,y),question,.28,.19,ORANGE)
        arrow(ax,(.30,y+.095),(.34,y+.095));arrow(ax,(.65,y+.095),(.69,y+.095))
    fig.text(.065,.12,"A geological question guides a sensor request; a height map supplies geometry.",fontsize=11)
    save(fig,"jezero-evidence-chain.png",source="Hurowitz et al.2025; Stack et al.2024; NASA Bunsen field report2024; conceptual synthesis")

    fig=figure("Two resolutions, two different meanings",
               "Teaching grid: finer numerical sampling does not add independent orbital information")
    for left,n,title in [(.08,5,"20 m product sampling"),(.56,25,"4 m computational sampling")]:
        ax=fig.add_axes([left,.25,.35,.53]);x,y=np.meshgrid(np.arange(n),np.arange(n))
        image=(x+y)/(2*n);image=image.astype(float);image[:max(1,n//5),:max(1,n//5)]=np.nan
        ax.imshow(image,origin="lower",cmap="terrain",extent=[0,100,0,100],vmin=0,vmax=1)
        for k in np.linspace(0,100,n+1):ax.axhline(k,c="white",lw=.35);ax.axvline(k,c="white",lw=.35)
        ax.set_title(title);ax.set_xlabel("East (m)");ax.set_ylabel("North (m)")
        ax.text(2,2,"NoData",color=INK,fontsize=10)
    fig.text(.08,.15,"Same 100 × 100 m extent. Shading is synthetic. NoData remains unavailable.",fontsize=12)
    save(fig,"terrain-scale.png",source="USGS CTX DTM metadata; schematic fields, not measured heights")

    fig=figure("Choose a time scale for each agent",
               "Allocation examples are scenario inputs; these bars do not measure vehicle endurance")
    ax=fig.add_axes([.16,.24,.76,.55]);names=["Human EVA","Rover work period","Drone sortie"]
    approved=np.array([1200,1200,180])/60;proposed=np.array([2100,23400,150])/60
    y=np.arange(3)
    ax.barh(y-.16,approved,.28,label="Approved control",color=BLUE)
    ax.barh(y+.16,proposed,.28,label="Bunsen proposal",color=ORANGE)
    for i,(a,b) in enumerate(zip(approved,proposed)):
        ax.text(a+3,i-.16,f"{a:g} min",va="center",fontsize=10)
        ax.text(b+3,i+.16,f"{b:g} min",va="center",fontsize=10)
    ax.set_yticks(y,names);ax.invert_yaxis();ax.set_xlim(0,450);ax.set_xlabel("Allocated time (minutes)");ax.legend(loc="lower right")
    fig.text(.08,.14,"Larger-map proposals remain proposed; a drone sortie is one campaign activity.",fontsize=12)
    save(fig,"agent-timescales.png",source="JZ-APP-20261114-01; docs/agent_campaign_proposal.md, proposed regional allocations")

    fig=figure("A documented sample is a workflow",
               "The 600 s total follows D-RATS experience; the internal phase split is a project assumption")
    ax=fig.add_axes([.23,.3,.69,.46]);ax.barh([1],[420],color=BLUE,label="Context / documentation: light-work model")
    ax.barh([1],[180],left=[420],color=ORANGE,label="Acquisition: heavy-work model")
    ax.barh([0],[120],color=GREEN,label="Separate approved B check-in")
    ax.text(210,1,"420 s",ha="center",va="center",color="white");ax.text(510,1,"180 s",ha="center",va="center",color="white")
    ax.text(60,0,"120 s",ha="center",va="center",color="white")
    ax.set_yticks([0,1],["Primary check-in","Documented sample"]);ax.set_xlim(0,620);ax.set_xlabel("Duration (s)")
    ax.legend(loc="upper center",bbox_to_anchor=(.5,-.26),frameon=False,fontsize=10)
    save(fig,"activity-cycle.png",source="Hurtado et al.2011 D-RATS; activity_duration.pilot.json; not a measured phase split")

    fig=figure("Eligibility precedes assignment",
               "A discovered target becomes a task through capabilities, precedence and resource checks")
    ax=fig.add_axes([.05,.18,.90,.65]);ax.axis("off")
    for xy,label,c in [((.02,.63),"Public discovery\nwith evidence",BLUE),((.37,.63),"Rover inspection\ncompleted",ORANGE),
                       ((.37,.15),"Primary B work\ncompleted",GREEN),((.72,.63),"Human sample\neligible candidate",PURPLE),
                       ((.72,.15),"Capability + budget\nreturn + reserves fit",BLUE)]:box(ax,xy,label,color=c)
    for a,b in [((.28,.715),(.35,.715)),((.63,.715),(.70,.715)),((.63,.245),(.72,.62)),((.845,.34),(.845,.61))]:arrow(ax,a,b)
    ax.text(.14,.27,"Three gates jointly\nsupport eligibility",ha="center",fontsize=12)
    save(fig,"task-precedence.png")

    fig=figure("An experiment should isolate a question",
               "Paired strategies use the same declared world; records retain successful and rejected cases")
    ax=fig.add_axes([.06,.19,.88,.65]);ax.axis("off")
    labels=["Freeze inputs\nSHA · seeds · ranges","Generate world\npublic prior + hypotheses","Run paired strategies\nno / corridor / alternatives",
            "Reveal observation\nfootprint + time + cost","Compare decisions\ngeometry + eligibility + margins","Audit conclusion\nrepeat with held-out seeds"]
    for i,label in enumerate(labels):
        row=i//3;col=i%3 if row==0 else 2-i%3
        box(ax,(.01+.35*col,.64-.48*row),label,width=.27,color=[BLUE,PURPLE,GREEN,ORANGE,BLUE,GREEN][i])
    for a,b in [((.29,.725),(.34,.725)),((.64,.725),(.69,.725)),((.83,.62),(.83,.36)),((.69,.245),(.64,.245)),((.34,.245),(.29,.245))]:arrow(ax,a,b)
    save(fig,"experimental-design.png")

    fig=figure("Different evidence answers different questions",
               "Read the validation level together with the result and its recorded inputs")
    ax=fig.add_axes([.09,.2,.82,.65]);ax.axis("off")
    levels=[("Physical experiment","How does the real system behave?"),("Same-run integrated execution","Do producers, authority and consumers agree?"),
            ("Model-consistent analytical case","What follows from the declared equations and inputs?"),("Software / contract checks","Does the implementation satisfy tested invariants?")]
    for i,(name,q) in enumerate(levels):
        y=.78-i*.22;ax.add_patch(Rectangle((.04,y-.08),.91,.16,fc=[PURPLE,ORANGE,GREEN,BLUE][i]+"18",ec=[PURPLE,ORANGE,GREEN,BLUE][i]))
        ax.text(.065,y+.018,name,fontsize=14);ax.text(.065,y-.035,q,fontsize=11)
    save(fig,"evidence-ladder.png")


def model_figures():
    profiles=load_profiles(PROFILES);human=profiles["human_1"];rover=profiles["rover_1"]
    rows={kind:{str(dz):estimate_segment(p,(0,0,0),(100,0,dz)).__dict__ for dz in [-5,0,5]}
          for kind,p in [("human",human),("rover",rover)]}
    fig=figure("A directed route has two different costs",
               "Worked model example: 100 m horizontal displacement with −5, 0 or +5 m height change")
    axes=fig.subplots(1,3);fig.subplots_adjust(left=.08,right=.97,bottom=.27,top=.80,wspace=.50)
    for ax,kind,key,label in zip(axes,["human","human","rover"],["time_s","energy_wh","energy_wh"],
                               ["Human time (s)","Human metabolic energy (Wh)","Rover electrical energy (Wh)"]):
        vals=[rows[kind][str(dz)][key] for dz in [-5,0,5]]
        ax.bar(["Downhill","Flat","Uphill"],vals,color=[GREEN,BLUE,ORANGE]);ax.set_ylabel(label);ax.tick_params(axis="x",labelrotation=25)
        for i,v in enumerate(vals):ax.text(i,v+max(vals)*.025,f"{v:.2f}",ha="center",fontsize=10)
        ax.set_ylim(0,max(vals)*1.20)
    fig.text(.07,.14,"Time is symmetric here; climb work is directed. Neither model receives downhill energy credit.",fontsize=11)
    save(fig,"directed-costs.png","Model calculation","Existing estimate_segment; config/science_profiles.proposed.json")

    up=estimate_segment(human,(0,0,0),(100,0,5));down=estimate_segment(human,(100,0,5),(0,0,0))
    service=estimate_activity(human,"inspect",120);sample=estimate_activity(human,"sample",180)
    fig=figure("Return and reserve occupy separate parts of the budget",
               "Synthetic teaching itinerary: 100 m uphill, check-in, then directed return")
    axes=fig.subplots(1,3);fig.subplots_adjust(left=.08,right=.98,bottom=.28,top=.80,wspace=.4)
    for ax,key,capacity,reserve,unit in zip(axes,["time_s","energy_wh","oxygen_l"],[600,80,20],[120,20,5],["s","metabolic Wh","equivalent O₂ L"]):
        values=[getattr(up,key),getattr(service,key),getattr(down,key),reserve];left=0
        for value,color,label in zip(values,[BLUE,ORANGE,GREEN,PURPLE],["Outbound","Check-in","Return","Reserve"]):
            ax.barh([0],[value],left=left,color=color,label=label);left+=value
        ax.axvline(capacity,color=INK,lw=1.6,ls="--",label="Allocation");ax.set_xlim(0,capacity*1.07);ax.set_yticks([]);ax.set_xlabel(unit)
        ax.set_title(f"Committed {left:.2f}\nAllocation {capacity:g}",fontsize=12)
    handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,loc="lower center",bbox_to_anchor=(.5,.14),ncol=5,frameon=False,fontsize=10)
    save(fig,"resource-ledger.png","Model calculation","Synthetic teaching allocation; existing scientific estimator")

    fig=figure("Sensitivity asks where a decision changes",
               "One-factor calculation: a 180 s heavy-work acquisition interval added to the teaching itinerary")
    ax=fig.add_axes([.10,.28,.78,.50]);d=np.linspace(60,200,141)
    # The fixed grade is 5%; height grows with distance. Base travel duration scales linearly.
    t=(up.time_s+down.time_s)*d/100+service.time_s+sample.time_s+120
    e=(up.energy_wh+down.energy_wh)*d/100+service.energy_wh+sample.energy_wh+20
    o=(up.oxygen_l+down.oxygen_l)*d/100+service.oxygen_l+sample.oxygen_l+5
    for values,cap,color,label in [(t,600,BLUE,"Time / allocation"),(e,80,ORANGE,"Energy / allocation"),(o,20,GREEN,"Oxygen / allocation")]:
        ax.plot(d,values/cap,color=color,lw=2.5,label=label)
    ax.axhline(1,c=RED,ls="--",lw=1.5);ax.set_xlabel("One-way horizontal distance at 5% grade (m)");ax.set_ylabel("Requirement including reserve / allocation")
    ax.legend(loc="upper left",fontsize=10);ax.grid(alpha=.15)
    fig.text(.10,.14,"All three ratios must stay at or below 1. This is a calculated teaching sweep, not a frequency estimate.",fontsize=10)
    save(fig,"sensitivity.png","Model calculation","Scientific estimator teaching sweep; constant 5% grade, fixed allocations")
    return rows


def public_case():
    raw=json.loads(EXPERIMENT.read_text(encoding="utf-8"));terrain=np.load(DEM)
    z=np.where(terrain["valid_mask"],terrain["elevation_m"],np.nan)
    timeline=raw["timeline"];poses=np.array([t["poses"]["human_1"] for t in timeline]);times=np.array([t["sim_time_s"] for t in timeline])
    A=poses[0];B=np.array([-238,-82]);observation=raw["observations"][0]["typed_observation"]
    def base(ax,full=False):
        extent=[-256,256,-256,256] if full else [-256,0,-256,0]
        data=z if full else z[:64,:64]
        img=ax.imshow(data,origin="lower",extent=extent,cmap="terrain",interpolation="nearest",vmin=np.nanmin(z),vmax=np.nanmax(z))
        ax.scatter([A[0],B[0]],[A[1],B[1]],c=[BLUE,GREEN],s=48,zorder=6)
        ax.annotate("A",A[:2],xytext=(7,-12),textcoords="offset points",fontsize=13)
        ax.annotate("B",B,xytext=(7,3),textcoords="offset points",fontsize=13)
        ax.set_xlabel("East (m)");ax.set_ylabel("North (m)");return img
    fig=figure("Window size should serve the mission question",
               "Same analytical itinerary, absolute ENU coordinates and public CTX prior")
    axes=fig.subplots(1,2);fig.subplots_adjust(left=.08,right=.85,bottom=.23,top=.81,wspace=.30)
    for ax,full in zip(axes,[True,False]):
        base(ax,full);ax.plot(poses[:,0],poses[:,1],c=BLUE,lw=1.5)
        ax.add_patch(Circle((-230,-182),12,fill=False,ec=ORANGE,lw=1.8))
        ax.set_title("512 m / 128² cells" if full else "256 m / 64² cells")
    axes[0].add_patch(Rectangle((-256,-256),256,256,fill=False,ec=RED,lw=1.5))
    color_ax=fig.add_axes([.89,.27,.018,.49])
    fig.colorbar(axes[0].images[0],cax=color_ax,label="Elevation (m, source datum)")
    fig.text(.08,.14,"Two paired requests retained identical geometry and costs. The smaller raster has 75% fewer cells.",fontsize=11)
    save(fig,"scale-crop.png","SIMULATED analytical case","Recorded Bunsen case; public CTX prior; crop-comparison.json")

    fig=figure("One observation changes the admissible corridor",
               "Recorded analytical case: observed obstacle, detour, primary check-in and return")
    ax=fig.add_axes([.09,.22,.57,.60]);img=base(ax)
    for phase,color,label in [("OUTBOUND_PREFIX",BLUE,"Reached prefix"),("DETOUR_TO_B",ORANGE,"Detour to B"),("RETURN_TO_A",PURPLE,"Return to A")]:
        p=np.array([t["poses"]["human_1"] for t in timeline if t["phase"]==phase])
        if len(p):ax.plot(p[:,0],p[:,1],c=color,lw=2,label=label)
    ax.add_patch(Circle((-230,-182),12,fill=False,ec=RED,lw=1.7,label="12 m observation footprint"))
    ax.scatter([-230],[-174],marker="s",c=RED,s=40,label="Observed obstacle",zorder=8)
    ax.set_xlim(-250,-208);ax.set_ylim(-232,-65);ax.legend(loc="center left",bbox_to_anchor=(1.02,.55),fontsize=10,frameon=False)
    fig.text(.70,.34,"68 simulated steps\n283.04 m traversed\n1,226.89 s total\n73 cost intervals",fontsize=13,linespacing=1.7)
    save(fig,"case-route.png","SIMULATED analytical case","experiment.json timeline; public CTX prior; no geological target registration")

    fig=figure("Resources are carried through the whole itinerary",
               "Recorded remaining allocation; dashed lines show the separate fixed reserves")
    axes=fig.subplots(3,1,sharex=True);fig.subplots_adjust(left=.13,right=.95,bottom=.22,top=.82,hspace=.30)
    for ax,key,reserve,label,color in zip(axes,["time_s","energy_wh","oxygen_l"],[420,45,9],["Time (s)","Metabolic Wh","Equivalent O₂ L"],[BLUE,ORANGE,GREEN]):
        values=[t["remaining"]["human_1"][key] for t in timeline]
        ax.plot(times,values,color=color,lw=2);ax.axhline(reserve,c=RED,ls="--",lw=1.2)
        ax.set_ylabel(label,fontsize=10);ax.grid(alpha=.15)
        ax.axvline(observation["timestamp_sim_s"],color=INK,alpha=.4,ls=":")
    axes[-1].set_xlabel("Simulation time (s)")
    fig.text(.13,.12,"The 600 s coordination wait and both 120 s service intervals retain their full costs.",fontsize=11)
    save(fig,"case-resources.png","SIMULATED analytical case","experiment.json nonresetting remaining resources")

    frames=[]
    sample_times=np.r_[np.linspace(0,600,5),np.linspace(600.281,raw['timeline'][-1]['sim_time_s'],43)]
    for time in sample_times:
        idx=max(0,int(np.searchsorted(times,time,side="right")-1));state=timeline[idx]
        fig=figure("Adaptation on the same recorded mission",
                   f"SIMULATED | t = {time:,.1f} s | {state['phase'].replace('_',' ').lower()}",9,6)
        ax=fig.add_axes([.09,.23,.52,.57]);base(ax)
        ax.plot(poses[:idx+1,0],poses[:idx+1,1],c=BLUE,lw=2,label="Reached positions")
        path=np.array(state.get("active_path",[]))
        if len(path):ax.plot(path[:,0],path[:,1],c=ORANGE,ls="--",lw=1.5)
        if state["map_version"]>=2:
            ax.add_patch(Circle((-230,-182),12,fill=False,ec=RED,lw=1.4))
            ax.scatter([-230],[-174],c=RED,marker="s",s=36,zorder=7)
        p=state["poses"]["human_1"];ax.scatter([p[0]],[p[1]],c=INK,s=70,zorder=9)
        ax.set_xlim(-252,-205);ax.set_ylim(-235,-65)
        remaining=state["remaining"]["human_1"]
        fig.text(.66,.70,f"Map version {state['map_version']}\n\nRemaining\n{remaining['time_s']:.1f} s\n{remaining['energy_wh']:.2f} metabolic Wh\n{remaining['oxygen_l']:.2f} equivalent O₂ L",fontsize=12,linespacing=1.5)
        fig.text(.09,.13,"Time sampling is condensed for teaching; source timestamps and costs are preserved.",fontsize=10)
        frames.append(stamped(fig,"SIMULATED analytical case"))
    animation("adaptation.gif",frames,"SIMULATED analytical case","Recorded timeline; public prior and revealed observations only",180)
    return raw


def conceptual_animations():
    frames=[]
    for i in range(12):
        stage=min(2,i//4);fig=figure("A prior becomes a revised belief",
            ["1. Plan over valid estimates","2. Acquire a bounded observation","3. Revise only the observed footprint"][stage],9,6)
        ax=fig.add_axes([.09,.24,.56,.56]);grid=np.zeros((10,16));grid[8:,1:3]=np.nan
        ax.imshow(grid,origin="lower",cmap="Blues",vmin=-.8,vmax=1,extent=[0,16,0,10])
        for k in range(17):ax.axvline(k,c="white",lw=.7)
        for k in range(11):ax.axhline(k,c="white",lw=.7)
        ax.plot([1,7,14],[2,6,8],c=BLUE,lw=2,ls="--")
        if stage>=1:ax.add_patch(Circle((7,6),2,fill=False,ec=ORANGE,lw=2))
        if stage>=2:
            ax.add_patch(Rectangle((7,6),1,1,color=RED));ax.plot([1,6,8,14],[2,4,5,8],c=GREEN,lw=2)
        ax.set_xlabel("Column (illustrative grid)");ax.set_ylabel("Row")
        fig.text(.70,.64,["Valid prior cells\nremain estimates.","A footprint carries\nidentity, time and\nmeasurements.","An obstacle changes\nroute eligibility;\nNoData persists."][stage],fontsize=13,linespacing=1.7)
        fig.text(.09,.13,"Synthetic teaching grid. No soil property or measured sensor accuracy is inferred.",fontsize=10)
        frames.append(stamped(fig,"Conceptual simulation"))
    animation("prior-observation.gif",frames,"Conceptual simulation","Synthetic grid; causal observation concept",350)
    frames=[]
    labels=["Observe","Validate input","Update map","Check active route","Check return + reserves","Authorize decision"]
    for step in range(6):
        fig=figure("An observation initiates a decision, not an automatic route",
                   "Conceptual state progression; the mission authority retains the final decision",9,6)
        ax=fig.add_axes([.09,.23,.82,.59]);ax.axis("off")
        for j,label in enumerate(labels):
            row=j//3;col=j%3 if row==0 else 2-j%3;x=.01+.35*col;y=.65-.46*row
            box(ax,(x,y),label,.27,.18,ORANGE if j==step else BLUE)
            if j==step:ax.text(x+.135,y-.06,"current stage",ha="center",fontsize=10,color=ORANGE)
        for a,b in [((.29,.74),(.34,.74)),((.64,.74),(.69,.74)),((.83,.63),(.83,.39)),((.69,.28),(.64,.28)),((.34,.28),(.29,.28))]:arrow(ax,a,b)
        fig.text(.09,.13,"Return takes precedence when optional work no longer fits the remaining allocation.",fontsize=10)
        frames.append(stamped(fig,"Conceptual diagram"))
    animation("mission-decisions.gif",frames,"Conceptual diagram","Mission authority causal sequence",650)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    diagrams();values=model_figures();raw=public_case();conceptual_animations()
    hero=OUT/"cooperative-exploration.png"
    if hero.exists():
        RECORDS.append({"file":hero.name,"kind":"Conceptual illustration","source":"image_gen; generic unbranded scene, not measured terrain",
                        "frames":1,"visible_watermark":"AI-generated / Conceptual illustration","sha256":sha(hero)})
    metadata={"schema":"mge-wiki-assets-1.0.0","generated_with":"OpenAI Codex-assisted code and image_gen",
              "documentation_reference_main_sha":"9013bebf2400d605f5a3d68e79dadbd5d1c57d03",
              "case_planner_source_sha":"64985e7b4b69ac9683661db4842885d5a8293695",
              "source_run_id":raw["run_id"],"input_sha256":{p.relative_to(ROOT).as_posix():sha(p) for p in [EXPERIMENT,DEM,PROFILES,Path(__file__),
                  ROOT/"docs/science_approvals/jezero_scenario_20261114.json",ROOT/"config/activity_duration.pilot.json",
                  ROOT/"docs/agent_campaign_proposal.md",ROOT/"evidence/mission-3d-video-20261115-local/map-analysis/crop-comparison.json"]},
              "versions":{"python":sys.version.split()[0],"matplotlib":matplotlib.__version__,"numpy":np.__version__,"pillow":Image.__version__},
              "directed_model_examples":values,"assets":RECORDS,
              "all_GIF_frames_stamped":True,"technical_implementation_changed":False,"published":False}
    (OUT/"manifest.json").write_text(json.dumps(metadata,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"assets":len(RECORDS),"GIFs":sum(r["file"].endswith('.gif') for r in RECORDS),"run_id":raw["run_id"]}))


if __name__=="__main__":main()
