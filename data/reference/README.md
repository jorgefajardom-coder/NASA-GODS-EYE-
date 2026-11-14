# Evaluator-only reference boundary

Owner: Daniel. This directory reserves the private evaluator/simulated-observation input boundary. Data files are ignored by Git by default. Only this note and the local ignore policy are tracked.

Do not load, publish or export reference arrays into planning, mission, gateway, normal public web mode, or the prior/belief archive. The simulator may use authorized reference data to generate explicitly simulated observations; the planner receives only the resulting public observation/belief data.

A separate evaluation tool, explicit local paths and access checks remain to be implemented. An ignored directory is an organizational convention, not an operating-system security boundary. Keep license and checksum records for the actual evaluator source; metadata is not permission to redistribute the asset.
