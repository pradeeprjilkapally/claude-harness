# Handoff

The baton between agents (or between a human and an agent). The `handoff` skill
writes this block; the `resume` skill reads it and continues from exactly here.

Gitignored by default — it is session state, not project history.

---

## Owner: <none>

Nothing in flight.

<!--
Format, written by the `handoff` skill:

## Owner: <agent or person taking over>
Date:     <when the baton was passed>
Branch:   <branch the work is on>
Task:     <NN-DDMMYY from task.md>
Done:     <what is finished and verified — not what was attempted>
Left:     <what remains, in the order it should be done>
Next:     <the single next action, concrete enough to start cold>
Blockers: <anything the incoming owner cannot resolve alone>
-->
