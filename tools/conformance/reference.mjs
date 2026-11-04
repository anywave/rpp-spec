// Independent, lossless JSON reader and UTF-8 canonical emitter. No keys or network.
import { readFileSync } from 'node:fs';
class Scalar { constructor(raw) { this.raw = raw; } }
const DUP = Symbol('duplicate');
function parse(raw) {
  let at = 0, depth = 0;
  const space = () => { while (/[ \t\r\n]/.test(raw[at] ?? '') && at < raw.length) at++; };
  function string() {
    const start = at++;
    for (; at < raw.length; at++) {
      if (raw[at] === '\\') { at++; continue; }
      if (raw[at] === '"') {
        const value = JSON.parse(raw.slice(start, ++at));
        if (/[\ud800-\udfff]/u.test(value)) throw Error('unpaired surrogate');
        return value;
      }
    }
    throw Error('unterminated string');
  }
  function value() {
    space(); if (++depth > 128) throw Error('depth');
    let out;
    if (raw[at] === '"') out = string();
    else if (raw[at] === '{' || raw[at] === '[') {
      const object = raw[at++] === '{', close = object ? '}' : ']';
      out = object ? Object.create(null) : []; space();
      if (raw[at] !== close) for (;;) {
        if (object) {
          if (raw[at] !== '"') throw Error('key');
          const key = string(); space(); if (raw[at++] !== ':') throw Error('colon');
          if (Object.hasOwn(out, key) && !out[DUP]) Object.defineProperty(out, DUP, { value: true });
          out[key] = value();
        } else out.push(value());
        space(); if (raw[at] !== ',') break;
        at++; space();
      }
      if (raw[at++] !== close) throw Error('close');
    } else {
      const token = /^(?:true|false|null|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?)/.exec(raw.slice(at))?.[0];
      if (!token) throw Error('value'); at += token.length;
      out = /^[tfn]/.test(token) ? JSON.parse(token) : new Scalar(token);
    }
    depth--; return out;
  }
  const result = value(); space(); if (at !== raw.length) throw Error('trailing input');
  return result;
}
function scalar(raw) {
  if (/^-?(?:0|[1-9]\d*)$/.test(raw) && raw !== '-0') {
    const n = BigInt(raw);
    if (n >= -(1n << 63n) && n < (1n << 64n)) return n.toString();
  }
  const n = Number(raw);
  // The initial float diagnostics cover 1.0 and negative zero, not arbitrary f64.
  if (Object.is(n, -0)) return '-0.0';
  if (n === 1 && /[.eE]/.test(raw)) return '1.0';
  throw Error('reference float domain unavailable');
}
function canonical(v) {
  if (v instanceof Scalar) return scalar(v.raw);
  if (Array.isArray(v)) return '[' + v.map(canonical).join(',') + ']';
  if (v !== null && typeof v === 'object') return '{' + Object.keys(v)
    .sort((a, b) => Buffer.compare(Buffer.from(a), Buffer.from(b)))
    .map(k => JSON.stringify(k) + ':' + canonical(v[k])).join(',') + '}';
  return JSON.stringify(v);
}
const uint = v => v instanceof Scalar && /^(0|[1-9]\d*)$/.test(v.raw) && BigInt(v.raw) < (1n << 64n);
const optional = v => v == null || typeof v === 'string';
const object = v => v !== null && typeof v === 'object' && !Array.isArray(v) && !(v instanceof Scalar);
const keys = (v, allowed, required = allowed) => object(v) && !v[DUP] && Object.keys(v).every(k => allowed.includes(k)) && required.every(k => Object.hasOwn(v, k));
const fact = v => keys(v, ['value','source','signed_by','as_of','ttl_secs','sig'], ['value','source','ttl_secs']) && typeof v.source === 'string' && uint(v.ttl_secs) && ['signed_by','as_of','sig'].every(k => optional(v[k]));
function meter(rows) {
  if (!Array.isArray(rows)) return null;
  const order = ['row','tick','request','traffic','source','target','path','status','tokens','detail'];
  const statuses = ['OK','FAILED','INVALID_INPUT','DENIED','DENIED_SELF_TARGET','NO_CHANNEL','NO_INDEPENDENT_CHANNEL','DELIVERED','HELD_UNTIL_SINCE'];
  const cell = s => /[,"\r\n]/.test(s) ? '"' + s.replaceAll('"', '""') + '"' : s;
  const lines = [];
  for (const row of rows) {
    if (!keys(row, order) || !['row','request','tokens'].every(k => uint(row[k])) || !['tick','traffic','source','target','path','status','detail'].every(k => typeof row[k] === 'string') || !['data','control','billboard'].includes(row.traffic) || !statuses.includes(row.status)) return null;
    let tick; try { tick = BigInt(row.tick); } catch { return null; }
    if (tick.toString() !== row.tick || tick < -(1n << 127n) || tick >= (1n << 127n)) return null;
    lines.push(order.map(k => cell(row[k] instanceof Scalar ? row[k].raw : row[k])).join(','));
  }
  return order.join(',') + '\n' + (lines.length ? lines.join('\n') + '\n' : '');
}
function evaluate(c) {
  let v;
  try { v = parse(c.json); } catch { return { status: 'reject' }; }
  let result;
  if (c.profile === 'jobcard-json') {
    if (v !== null && !Array.isArray(v) && typeof v === 'object') delete v.sig;
    result = (c.domain ?? 'd') + '\n' + canonical(v);
  } else if (c.profile === 'jobcard-attempt') {
    const strings = ['job_id','attempt_id','worker','slot','by'], counters = ['revision','epoch','fence','until'];
    if (!keys(v, [...strings,...counters,'sig'], [...strings,...counters]) || !strings.every(k => typeof v[k] === 'string') || !counters.every(k => uint(v[k])) || !optional(v.sig)) return { status: 'reject' };
    delete v.sig; result = 'lw-jobcard/attempt/draft-v0\n' + canonical(v);
  } else if (c.profile === 'registry-json') result = canonical(v);
  else if (c.profile === 'registry-fact') {
    const r = v?.record, f = v?.fact;
    if (!keys(v,['record','name','fact']) || typeof v.name !== 'string' || !keys(r,['id','layer','subject','facts','admitted','public_key'],['id','layer','subject','facts']) || !['id','subject'].every(k => typeof r[k] === 'string') || typeof r.layer !== 'string' || !/^L[1-5]$/.test(r.layer) || !optional(r.public_key) || !(r.admitted == null || ['pending-root','admitted'].includes(r.admitted)) || !object(r.facts) || !Object.values(r.facts).every(fact) || !fact(f)) return { status: 'reject' };
    result = canonical(['lw-registry-fact/1',r.layer,r.subject,r.id,v.name,f.value,f.source,f.signed_by ?? null,f.as_of ?? null,f.ttl_secs]);
  } else if (c.profile === 'plan-json') {
    if (typeof c.value !== 'string') throw Error('native plan unavailable');
    result = canonical(parse(c.value));
  } else if (c.profile === 'meter-csv') {
    result = meter(v); if (result === null) return { status: 'reject' };
  } else if (c.profile === 'lend-proof') {
    if (!keys(v,['nonce_b','id_a','id_b']) || ![v.nonce_b,v.id_a,v.id_b].every(s => typeof s === 'string' && /^[a-f0-9]{64}$/.test(s))) return { status: 'reject' };
    result = `lw-link lend-key v1|${v.nonce_b}|${v.id_a}|${v.id_b}`;
  }
  else throw Error('unknown profile');
  return { status: 'bytes', hex: Buffer.from(result).toString('hex') };
}
try {
  const request = JSON.parse(readFileSync(0, 'utf8'));
  console.log(JSON.stringify(request.map(c => ({ id: c.id, outcome: evaluate(c) }))));
} catch {
  console.error('REFUSED: unsupported reference input or protocol'); process.exitCode = 2;
}
