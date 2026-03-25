import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const PROFILE = (__ENV.PROFILE || 'ramp').toLowerCase();
const SLEEP_SECONDS = Number(__ENV.SLEEP_SECONDS || 0.25);

const profiles = {
  ramp: {
    stages: [
      { duration: '1m', target: 50 },
      { duration: '2m', target: 150 },
      { duration: '1m', target: 300 },
      { duration: '1m', target: 0 },
    ],
  },
  spike: {
    stages: [
      { duration: '30s', target: 50 },
      { duration: '30s', target: 1000 },
      { duration: '1m', target: 1000 },
      { duration: '30s', target: 100 },
      { duration: '30s', target: 0 },
    ],
  },
  soak: {
    stages: [
      { duration: '2m', target: 200 },
      { duration: '8m', target: 200 },
      { duration: '2m', target: 0 },
    ],
  },
};

if (!profiles[PROFILE]) {
  throw new Error(`Unknown PROFILE: ${PROFILE}. Allowed: ${Object.keys(profiles).join(', ')}`);
}

export const options = {
  scenarios: {
    api_profile: {
      executor: 'ramping-vus',
      startVUs: 1,
      stages: profiles[PROFILE].stages,
      gracefulRampDown: '30s',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    checks: ['rate>0.99'],
  },
};

const endpoints = [
  { name: 'health', method: 'GET', path: '/health' },
  { name: 'metrics', method: 'GET', path: '/metrics' },
  {
    name: 'mfa_challenge',
    method: 'POST',
    path: '/api/v1/auth/mfa/challenge',
    body: JSON.stringify({ username: 'admin@example.com' }),
    params: { headers: { 'Content-Type': 'application/json' } },
  },
];

export default function () {
  for (const endpoint of endpoints) {
    const url = `${BASE_URL}${endpoint.path}`;
    const requestOptions = {
      ...(endpoint.params || {}),
      tags: { endpoint: endpoint.name, profile: PROFILE },
    };
    const response = endpoint.method === 'POST'
      ? http.post(url, endpoint.body || null, requestOptions)
      : http.get(url, requestOptions);

    check(response, {
      [`${endpoint.name} status 200`]: (r) => r.status === 200,
    });
  }

  sleep(SLEEP_SECONDS);
}

export function handleSummary(data) {
  return {
    stdout: `\nProfile ${PROFILE} completed for ${BASE_URL}\n` + JSON.stringify({
      checks: data.metrics.checks,
      http_req_failed: data.metrics.http_req_failed,
      http_req_duration: data.metrics.http_req_duration,
    }, null, 2),
  };
}
