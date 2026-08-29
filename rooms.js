/**
 * Serves technocore.chat's own `/rooms` aggregates to the browser.
 *
 * A proxy is unavoidable: the upstream service trusts no browser origin, so a page
 * cannot fetch it. What this adds beyond reachability is a shared cache — the
 * upstream meters reads per IP, and every visitor polling directly would spend one
 * budget between them. Here, a hundred open tabs cost one upstream read every few
 * seconds.
 *
 * Read-only, one upstream path, no query surface. `?limit=` is fixed rather than
 * forwarded: a caller cycling it would miss the cache on every request and turn this
 * into an amplifier pointed at the service it depends on.
 */

const UPSTREAM = 'https://technocore.chat/rooms?format=json&limit=48';
const CACHE_MS = 6000;
const TIMEOUT_MS = 8000;

/* Warm instances share one in-flight promise, so overlapping requests during a slow
   upstream read collapse into that read instead of stacking on top of it. */
let memo = null;   // { until, promise }

function fetchRooms() {
  const abort = new AbortController();
  const timer = setTimeout(() => abort.abort(), TIMEOUT_MS);
  return fetch(UPSTREAM, {
    signal: abort.signal,
    headers: { accept: 'application/json' }
  }).then(res => {
    if (!res.ok) throw new Error('upstream ' + res.status);
    return res.json();
  }).finally(() => clearTimeout(timer));
}

function shared() {
  const now = Date.now();
  if (memo && memo.until > now) return memo.promise;
  const promise = fetchRooms();
  memo = { until: now + CACHE_MS, promise };
  /* A rejection must not be cached for the full window, or one blip blinds the page
     for six seconds after the service has already recovered. */
  promise.catch(() => { if (memo && memo.promise === promise) memo = null; });
  return promise;
}

const num = v => (typeof v === 'number' && isFinite(v) ? v : null);

/* Room names and topics are written by anonymous strangers. They are length-capped
   here and rendered with textContent on the page — never as markup, never as a link. */
const str = (v, max) => String(v == null ? '' : v).slice(0, max);

function shapeRoom(r) {
  return {
    room: str(r && r.room, 48),
    topic: str(r && r.topic, 160),
    last_seq: num(r && r.last_seq) || 0,
    bytes: num(r && r.bytes) || 0,
    idle_seconds: num(r && r.idle_seconds) || 0,
    // The engagement figures sit directly on the room record, not nested.
    window: num(r && r.window) || 0,
    zero_response_share: num(r && r.zero_response_share),
    nick_diversity: num(r && r.nick_diversity)
  };
}

export default async function handler(req, res) {
  res.setHeader('cache-control', 'public, max-age=5, stale-while-revalidate=25');
  try {
    const d = await shared();
    const e = (d && d.engagement) || {};
    const n = (d && d.notes) || {};
    res.status(200).json({
      fetched_at: new Date().toISOString(),
      rooms: (Array.isArray(d && d.rooms) ? d.rooms : []).map(shapeRoom),
      total: num(d && d.total) || 0,
      capacity: num(d && d.capacity) || 0,
      bytes: num(d && d.bytes) || 0,
      bytes_capacity: num(d && d.bytes_capacity) || 0,
      notes: { total: num(n.total) || 0, bytes: num(n.bytes) || 0 },
      engagement: {
        window_cap: num(e.window_cap) || 0,
        windowed_messages: num(e.windowed_messages) || 0,
        /* null is a real value here and means "no data", which is not zero. Coercing it
           would draw a perfectly answered service out of an empty one. */
        zero_response_share: num(e.zero_response_share),
        nick_diversity: num(e.nick_diversity),
        windowed_note_to_message_ratio: num(e.windowed_note_to_message_ratio)
      }
    });
  } catch (err) {
    res.status(502).json({ error: String((err && err.message) || err).slice(0, 160) });
  }
}
