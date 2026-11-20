import { useEffect, useState } from "react";

import { CarStatus, getStatus } from "../api/carClient";

/** Polls GET /api/status on the car every 2 s. */
export function useCarStatus(host: string, port: number, intervalMs = 2000) {
  const [status, setStatus] = useState<CarStatus | null>(null);

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const s = await getStatus(host, port);
        if (alive) setStatus(s);
      } catch {
        if (alive) setStatus(null);
      }
    };
    tick();
    const id = setInterval(tick, intervalMs);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [host, port, intervalMs]);

  return status;
}
