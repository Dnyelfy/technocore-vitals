# Technocore Vitals

A live read of how much of [technocore.chat](https://technocore.chat) is agents talking
to nobody.

The service publishes its own decay tripwires on `/rooms`: the share of a bounded tail
window where no different agent spoke next, how many of those messages came from a key not
already counted, and durable notes per message. This page draws them — one headline number
and a room-by-room strip, sorted deadest first.

Nothing here is an outside estimate. Every figure comes from the service's own aggregates.

## What the bar means

Bar length is `zero_response_share`: the fraction of the scanned window where no *different*
agent spoke next. A room with a single writer scores 1.0, so a full red bar is not a busy
room — it is one agent posting into silence. The cyan tick is `nick_diversity`, the share of
messages from a distinct key.

A room whose window holds nothing reports `null`, which is not zero. Those rooms are left
out rather than drawn at the bottom of the scale, because "no data" and "perfectly answered"
must not land in the same place on the bar.

## Why there is a server at all

The upstream trusts no browser origin, so a page cannot fetch it. `api/rooms.js` is a
read-only proxy over one upstream path with a short shared cache: the service meters reads
per IP, so a hundred open tabs cost one upstream read every few seconds instead of a
hundred. `?limit=` is fixed rather than forwarded — a caller cycling it would miss the cache
on every request and turn the proxy into an amplifier pointed at the service it depends on.

## Tested

`test.py` drives the page in a headless browser against a mock upstream and checks the
headline maths, the deadest-first ordering, that a `null` window is omitted rather than
drawn as zero, and that a failed read leaves the last good numbers on screen with the
failure stated instead of blanking the page.

```bash
./build.sh          # public/index.html from src/
python3 test.py     # needs playwright
vercel deploy       # public/ static, api/ serverless
```

## Notes

Ratios cover a bounded tail window per room, so they describe the recent past, not the
service's lifetime. Room names and topics are written by anonymous strangers and are
rendered as text, never as links.

## License

Apache-2.0
