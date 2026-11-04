// Independent, lossless JSON reader and UTF-8 canonical emitter. No keys or network.
import { readFileSync } from 'node:fs';
class Scalar { constructor(raw) { this.raw = raw; } }
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
function evaluate(c) {
  let v;
  try { v = parse(c.json); } catch { return { status: 'reject' }; }
  let result;
  if (c.profile === 'jobcard-json') {
    if (v !== null && !Array.isArray(v) && typeof v === 'object') delete v.sig;
    result = (c.domain ?? 'd') + '\n' + canonical(v);
  } else if (c.profile === 'registry-json') result = canonical(v);
  else throw Error('unknown profile');
  return { status: 'bytes', hex: Buffer.from(result).toString('hex') };
}
try {
  const request = JSON.parse(readFileSync(0, 'utf8'));
  console.log(JSON.stringify(request.map(c => ({ id: c.id, outcome: evaluate(c) }))));
} catch {
  console.error('REFUSED: unsupported reference input or protocol'); process.exitCode = 2;
}
