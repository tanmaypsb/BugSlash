import assert from 'node:assert/strict';
import test from 'node:test';
import { getUserFriendlyError } from './apiErrors.js';

test('network failures are reported as API unavailable', () => {
  const message = getUserFriendlyError(new TypeError('Unable to reach BUGSLASH API. Make sure FastAPI is running at http://127.0.0.1:8000'), 'analysis');
  assert.match(message, /Unable to reach BUGSLASH API/);
  assert.doesNotMatch(message, /analysis failed/i);
});

test('HTTP 500 is reported as analysis failure, not API unavailable', () => {
  const error = Object.assign(new Error('Internal Server Error'), { name: 'ApiError', status: 500 });
  const message = getUserFriendlyError(error, 'analysis');
  assert.match(message, /Analysis failed/);
  assert.doesNotMatch(message, /unavailable|Unable to reach/i);
});

test('HTTP 422 includes the analyzer failure detail', () => {
  const error = Object.assign(new Error('staticcheck analysis failed: Go compile error'), { name: 'ApiError', status: 422 });
  assert.match(getUserFriendlyError(error, 'analysis'), /Go compile error/);
});
