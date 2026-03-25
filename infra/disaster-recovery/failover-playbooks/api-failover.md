# API Failover Playbook

1. Confirm active incident severity and impacted region.
2. Redirect ingress to healthy replica or standby stack.
3. Validate /health and synthetic user journeys.
4. Reconcile queues and in-flight jobs.
5. Communicate status update and expected timeline.
6. Begin root-cause analysis after service stabilization.
