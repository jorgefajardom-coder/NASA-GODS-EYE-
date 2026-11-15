# Python-only scientific planning context (F03.3-C2)

ScientificContext binds one immutable PlanRequest snapshot, its immutable
ResourceBudget, a published-format AgentProfile, explicit model ID, registry and
scenario SHA256, phase, and separate tuples of pending service/wait Activity.
It loads actual profile/scenario bytes through from_files; direct construction's
hashes are caller provenance assertions, not authentication or scientific approval.
The executable model file and selected profile content also contribute to its
fingerprint. Legacy ROS messages and nodes do not transport or select this context.

service_time_s is only a duration consistency check, never an activity selector.
The service tuple must explicitly sum to that duration. Waiting has explicit kinds
and durations separately; all work is fixed at the goal, not arrival-time dependent.
Every activity ID must be unique across both tuples. At most 256 entries are
accepted. Invalid kinds/durations go through the existing science API validation.
Caller-supplied lists become tuples; published AgentProfile freezes parameter maps.

OUTBOUND retains original goal work; SERVICE starts at the goal with unfinished
work; RETURN is an explicit one-leg request without goal service/waits. There is
no consumption ledger, replenishment, authorization, time-window or route-stopover
model. A future execution/ROS binding requires Jesus and David review.

Context admission binds the complete request, model and agent. Geometric limits
may be more conservative than the scientific profile, never less: directed slopes,
step, radius, localization and sigma remain compulsory. Coefficients are unchanged,
profiles remain proposed, and constructor success does not assert MODEL agreement.
Ground scientific search is limited to human/rover; standalone drone cost estimates
remain available in ScientificCosts without establishing flight planning safety.

The scientific import remains lazy in the planner: legacy callers need no mission
import. No package manifest or runtime dependency is enabled. Before installed ROS
activation, Jesus must reconcile planning-to-mission deployment and explicit context
transport; David must separately approve numerical semantics/profiles. Scope and
delivery gates under AGENTS.md remain; no submission readiness is claimed.
