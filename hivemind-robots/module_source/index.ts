// Hive mind module for SpacetimeDB 2.x (TypeScript).
// Coordinates are in centimeters on a 100 x 100 table. (0,0) is the arm's corner.
import { schema, table, t } from 'spacetimedb/server';

const robot = table(
  { name: 'robot', public: true },
  {
    id: t.string().primaryKey(),
    kind: t.string(),
    card_json: t.string(),
    x: t.f64(),
    y: t.f64(),
    battery: t.f64(),
    status: t.string(), // free | busy | offline
    last_seen_us: t.u64(),
  }
);

const thought = table(
  { name: 'thought', public: true },
  {
    id: t.u64().primaryKey().autoInc(),
    robot_id: t.string(),
    job_id: t.u64(),
    observation: t.string(),
    reasoning: t.string(),
    created_us: t.u64(),
  }
);

const job = table(
  { name: 'job', public: true },
  {
    id: t.u64().primaryKey().autoInc(),
    kind: t.string(), // pick_up
    description: t.string(),
    x: t.f64(),
    y: t.f64(),
    object_cm: t.f64(),
    status: t.string(), // open | assigned | done | no_robot
    assigned_to: t.string(),
    parent_job: t.u64(),
    attempts: t.u32(),
    note: t.string(),
    created_us: t.u64(),
  }
);

const bid = table(
  { name: 'bid', public: true },
  {
    id: t.u64().primaryKey().autoInc(),
    job_id: t.u64().index('btree'),
    robot_id: t.string(),
    can_help: t.bool(),
    action: t.string(), // grab | push_to_zone | none
    eta_s: t.f64(),
    plan: t.string(),
    reasoning: t.string(),
    verdict: t.string(), // pending | valid | rejected: ... | winner
    created_us: t.u64(),
  }
);

const assignment = table(
  { name: 'assignment', public: true },
  {
    id: t.u64().primaryKey().autoInc(),
    job_id: t.u64(),
    robot_id: t.string(),
    action: t.string(),
    plan: t.string(),
    status: t.string(), // active | done | failed
    note: t.string(),
    created_us: t.u64(),
    finished_us: t.u64(),
  }
);

const spacetimedb = schema({ robot, thought, job, bid, assignment });
export default spacetimedb;

// ---------- helpers (not exported) ----------
function nowUs(ctx: any): bigint {
  const ts: any = ctx.timestamp;
  if (ts && ts.microsSinceUnixEpoch !== undefined) return BigInt(ts.microsSinceUnixEpoch);
  if (ts && ts.__timestamp_micros_since_unix_epoch__ !== undefined) return BigInt(ts.__timestamp_micros_since_unix_epoch__);
  return 0n;
}
const ONLINE_US = 15_000_000n; // robot counts as online if seen in the last 15 s

function parseCard(r: any): any {
  try { return JSON.parse(r.card_json); } catch { return {}; }
}
function isOnline(ctx: any, r: any): boolean {
  return r.status !== 'offline' && nowUs(ctx) - BigInt(r.last_seen_us) < ONLINE_US;
}
function hiveSays(ctx: any, jobId: bigint, observation: string, reasoning: string) {
  ctx.db.thought.insert({ id: 0n, robot_id: 'HIVE', job_id: jobId, observation, reasoning, created_us: nowUs(ctx) });
}
// Checks a bid against the robot's capability card. Returns '' if valid, or the reason it is rejected.
function checkBid(ctx: any, j: any, b: any): string {
  if (!b.can_help) return 'robot says it cannot help';
  const r = ctx.db.robot.id.find(b.robot_id);
  if (!r) return 'robot not registered';
  if (!isOnline(ctx, r)) return 'robot offline';
  if (r.status === 'busy') return 'robot busy';
  const card = parseCard(r);
  if (b.action === 'grab') {
    if (!card.can_lift) return 'card says it cannot lift';
    if (card.max_object_cm !== undefined && j.object_cm > card.max_object_cm) return 'object too big for its claw';
    if (!card.can_move) {
      const z = card.zone || {};
      const d = Math.hypot(j.x - z.x, j.y - z.y);
      if (!(d <= z.r)) return `object is ${Math.round(d)} cm from its base, reach is ${z.r} cm`;
    }
    return '';
  }
  if (b.action === 'push_to_zone') {
    if (!card.can_move) return 'card says it cannot move';
    if (card.max_push_cm !== undefined && j.object_cm > card.max_push_cm) return 'object too big to push';
    return '';
  }
  return `unknown action "${b.action}"`;
}
// Grabbing finishes the job, pushing only helps, so grab wins ties.
function rank(action: string): number { return action === 'grab' ? 0 : 1; }

function decide(ctx: any, jobId: bigint) {
  const j = ctx.db.job.id.find(jobId);
  if (!j || j.status !== 'open') return;
  let best: any = null;
  for (const b of ctx.db.bid.job_id.filter(jobId)) {
    const why = checkBid(ctx, j, b);
    b.verdict = why === '' ? 'valid' : `rejected: ${why}`;
    ctx.db.bid.id.update(b);
    if (why === '' && (!best || rank(b.action) < rank(best.action) || (rank(b.action) === rank(best.action) && b.eta_s < best.eta_s))) best = b;
  }
  if (!best) {
    j.status = 'no_robot';
    j.note = 'No robot can handle this. Alerting staff.';
    ctx.db.job.id.update(j);
    hiveSays(ctx, jobId, `Job ${jobId}: no robot can handle this`, 'Every bid failed the capability check. Alerting staff.');
    return;
  }
  best.verdict = 'winner';
  ctx.db.bid.id.update(best);
  j.status = 'assigned';
  j.assigned_to = best.robot_id;
  ctx.db.job.id.update(j);
  const r = ctx.db.robot.id.find(best.robot_id);
  if (r) { r.status = 'busy'; ctx.db.robot.id.update(r); }
  ctx.db.assignment.insert({ id: 0n, job_id: jobId, robot_id: best.robot_id, action: best.action, plan: best.plan,
    status: 'active', note: '', created_us: nowUs(ctx), finished_us: 0n });
  hiveSays(ctx, jobId, `Job ${jobId} goes to ${best.robot_id}`, `${best.robot_id} will ${best.plan} (about ${best.eta_s.toFixed(1)} s).`);
}

// ---------- reducers ----------
export const register_robot = spacetimedb.reducer(
  { id: t.string(), kind: t.string(), card_json: t.string(), x: t.f64(), y: t.f64(), battery: t.f64() },
  (ctx, { id, kind, card_json, x, y, battery }) => {
    JSON.parse(card_json); // throws if the card is not valid JSON
    const row = { id, kind, card_json, x, y, battery, status: 'free', last_seen_us: nowUs(ctx) };
    if (ctx.db.robot.id.find(id)) ctx.db.robot.id.update(row); else ctx.db.robot.insert(row);
  }
);

export const update_robot = spacetimedb.reducer(
  { id: t.string(), x: t.f64(), y: t.f64(), battery: t.f64() },
  (ctx, { id, x, y, battery }) => {
    const r = ctx.db.robot.id.find(id);
    if (!r) throw new Error(`robot ${id} not registered`);
    r.x = x; r.y = y; r.battery = battery; r.last_seen_us = nowUs(ctx);
    if (r.status === 'offline') r.status = 'free';
    ctx.db.robot.id.update(r);
  }
);

export const set_robot_offline = spacetimedb.reducer({ id: t.string() }, (ctx, { id }) => {
  const r = ctx.db.robot.id.find(id);
  if (r) { r.status = 'offline'; ctx.db.robot.id.update(r); }
});

export const post_thought = spacetimedb.reducer(
  { robot_id: t.string(), job_id: t.u64(), observation: t.string(), reasoning: t.string() },
  (ctx, { robot_id, job_id, observation, reasoning }) => {
    ctx.db.thought.insert({ id: 0n, robot_id, job_id, observation, reasoning, created_us: nowUs(ctx) });
  }
);

export const create_job = spacetimedb.reducer(
  { kind: t.string(), description: t.string(), x: t.f64(), y: t.f64(), object_cm: t.f64(), parent_job: t.u64() },
  (ctx, { kind, description, x, y, object_cm, parent_job }) => {
    const row = ctx.db.job.insert({ id: 0n, kind, description, x, y, object_cm, status: 'open', assigned_to: '',
      parent_job, attempts: 0, note: '', created_us: nowUs(ctx) });
    hiveSays(ctx, row.id, `New job ${row.id}: ${description}`, `At (${x.toFixed(0)}, ${y.toFixed(0)}) cm. Waiting for bids.`);
  }
);

export const submit_bid = spacetimedb.reducer(
  { job_id: t.u64(), robot_id: t.string(), can_help: t.bool(), action: t.string(), eta_s: t.f64(), plan: t.string(), reasoning: t.string() },
  (ctx, { job_id, robot_id, can_help, action, eta_s, plan, reasoning }) => {
    const j = ctx.db.job.id.find(job_id);
    if (!j) throw new Error(`job ${job_id} not found`);
    if (j.status !== 'open') throw new Error(`job ${job_id} is ${j.status}, not open`);
    for (const old of ctx.db.bid.job_id.filter(job_id)) if (old.robot_id === robot_id) ctx.db.bid.id.delete(old.id);
    ctx.db.bid.insert({ id: 0n, job_id, robot_id, can_help, action, eta_s, plan, reasoning, verdict: 'pending', created_us: nowUs(ctx) });
    // Decide right away once every online robot has bid.
    const bidders = new Set<string>();
    for (const b of ctx.db.bid.job_id.filter(job_id)) bidders.add(b.robot_id);
    let allIn = true;
    for (const r of ctx.db.robot.iter()) if (isOnline(ctx, r) && !bidders.has(r.id)) allIn = false;
    if (allIn) decide(ctx, job_id);
  }
);

// Anyone can call this. It does nothing if the job was already decided.
export const decide_job = spacetimedb.reducer({ job_id: t.u64() }, (ctx, { job_id }) => decide(ctx, job_id));

export const complete_job = spacetimedb.reducer(
  { job_id: t.u64(), robot_id: t.string(), note: t.string(), x: t.f64(), y: t.f64() },
  (ctx, { job_id, robot_id, note, x, y }) => {
    const j = ctx.db.job.id.find(job_id);
    if (!j) throw new Error(`job ${job_id} not found`);
    if (j.assigned_to !== robot_id) throw new Error(`job ${job_id} belongs to ${j.assigned_to}, not ${robot_id}`);
    let action = '';
    for (const a of ctx.db.assignment.iter()) {
      if (a.job_id === job_id && a.robot_id === robot_id && a.status === 'active') {
        a.status = 'done'; a.note = note; a.finished_us = nowUs(ctx); action = a.action;
        ctx.db.assignment.id.update(a);
      }
    }
    j.status = 'done'; j.note = note;
    ctx.db.job.id.update(j);
    const r = ctx.db.robot.id.find(robot_id);
    if (r) { r.status = 'free'; ctx.db.robot.id.update(r); }
    if (action === 'push_to_zone') {
      // The object is now somewhere new, so the hive opens a follow up job for it.
      const child = ctx.db.job.insert({ id: 0n, kind: j.kind, description: `Delivered by ${robot_id}: ${j.description}`,
        x, y, object_cm: j.object_cm, status: 'open', assigned_to: '', parent_job: job_id, attempts: 0, note: '', created_us: nowUs(ctx) });
      hiveSays(ctx, child.id, `${robot_id} delivered job ${job_id}. New job ${child.id}`, `Object is now at (${x.toFixed(0)}, ${y.toFixed(0)}) cm. Waiting for bids.`);
    } else {
      hiveSays(ctx, job_id, `Job ${job_id} done by ${robot_id}`, note);
    }
  }
);

export const fail_job = spacetimedb.reducer(
  { job_id: t.u64(), robot_id: t.string(), reason: t.string(), x: t.f64(), y: t.f64() },
  (ctx, { job_id, robot_id, reason, x, y }) => {
    const j = ctx.db.job.id.find(job_id);
    if (!j) throw new Error(`job ${job_id} not found`);
    for (const a of ctx.db.assignment.iter()) {
      if (a.job_id === job_id && a.robot_id === robot_id && a.status === 'active') {
        a.status = 'failed'; a.note = reason; a.finished_us = nowUs(ctx);
        ctx.db.assignment.id.update(a);
      }
    }
    const r = ctx.db.robot.id.find(robot_id);
    if (r) { r.status = 'free'; ctx.db.robot.id.update(r); }
    for (const b of [...ctx.db.bid.job_id.filter(job_id)]) ctx.db.bid.id.delete(b.id);
    j.attempts = j.attempts + 1;
    j.x = x; j.y = y; j.assigned_to = '';
    if (j.attempts >= 3) {
      j.status = 'no_robot'; j.note = `Failed ${j.attempts} times. Alerting staff.`;
      hiveSays(ctx, job_id, `Job ${job_id} failed ${j.attempts} times`, 'Alerting staff.');
    } else {
      j.status = 'open'; j.note = `Reopened: ${reason}`;
      hiveSays(ctx, job_id, `Job ${job_id} reopened`, `${robot_id} failed: ${reason}`);
    }
    ctx.db.job.id.update(j);
  }
);

// Clears jobs, bids, thoughts and assignments between demo runs. Robots stay.
export const reset_demo = spacetimedb.reducer(ctx => {
  for (const x of [...ctx.db.bid.iter()]) ctx.db.bid.id.delete(x.id);
  for (const x of [...ctx.db.assignment.iter()]) ctx.db.assignment.id.delete(x.id);
  for (const x of [...ctx.db.thought.iter()]) ctx.db.thought.id.delete(x.id);
  for (const x of [...ctx.db.job.iter()]) ctx.db.job.id.delete(x.id);
  for (const r of [...ctx.db.robot.iter()]) { r.status = 'free'; ctx.db.robot.id.update(r); }
});
