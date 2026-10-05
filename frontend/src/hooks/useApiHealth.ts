import { useState, useEffect, useCallback } from 'react';
import { getHealth } from '../services/api';

type ConnectionStatus = 'connected' | 'offline' | 'checking';

/**
 * Periodically checks API health. Checks on mount, then every 30s.
 * Does NOT poll aggressively.
 */
export function useApiHealth(): ConnectionStatus {
  const [status, setStatus] = useState<ConnectionStatus>('checking');

  const check = useCallback((signal: AbortSignal) => {
    void getHealth(signal)
      .then(() => {
        if (!signal.aborted) setStatus('connected');
      })
      .catch(() => {
        if (!signal.aborted) setStatus('offline');
      });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    check(controller.signal);
    const interval = setInterval(() => check(controller.signal), 30000);

    return () => {
      clearInterval(interval);
      controller.abort();
    };
  }, [check]);

  return status;
}
