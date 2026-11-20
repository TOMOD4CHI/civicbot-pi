import { useCallback, useEffect, useRef, useState } from "react";

import { arcadeMix, carUrls, DriveMessage } from "../api/carClient";

export type LinkState = "connecting" | "online" | "offline";

const SEND_PERIOD_MS = 100;     // car watchdog stops after 500 ms of silence
const RECONNECT_MS = 1500;

/**
 * Keeps a WebSocket to the car and streams drive commands at 10 Hz while the
 * joystick is held. Releasing the stick (or calling stop) sends one "stop".
 */
export function useCarControl(host: string, port: number) {
  const [link, setLink] = useState<LinkState>("connecting");
  const ws = useRef<WebSocket | null>(null);
  const stick = useRef({ throttle: 0, steering: 0, active: false });
  const speed = useRef(0.6);
  const wasActive = useRef(false);

  const send = useCallback((msg: DriveMessage) => {
    const sock = ws.current;
    if (sock && sock.readyState === WebSocket.OPEN) sock.send(JSON.stringify(msg));
  }, []);

  // connection with auto-reconnect
  useEffect(() => {
    let closed = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const connect = () => {
      setLink("connecting");
      const sock = new WebSocket(carUrls(host, port).ws);
      ws.current = sock;
      sock.onopen = () => setLink("online");
      sock.onclose = () => {
        if (ws.current === sock) ws.current = null;
        if (closed) return;
        setLink("offline");
        timer = setTimeout(connect, RECONNECT_MS);
      };
      sock.onerror = () => sock.close();
      sock.onmessage = () => {};
    };
    connect();

    return () => {
      closed = true;
      if (timer) clearTimeout(timer);
      ws.current?.close();
      ws.current = null;
    };
  }, [host, port]);

  // 10 Hz command loop
  useEffect(() => {
    const id = setInterval(() => {
      const s = stick.current;
      if (s.active) {
        const { left, right } = arcadeMix(s.throttle, s.steering);
        send({ type: "drive", left: left * speed.current, right: right * speed.current });
        wasActive.current = true;
      } else if (wasActive.current) {
        send({ type: "stop" });
        wasActive.current = false;
      }
    }, SEND_PERIOD_MS);
    return () => clearInterval(id);
  }, [send]);

  const setStick = useCallback((throttle: number, steering: number, active: boolean) => {
    stick.current = { throttle, steering, active };
  }, []);

  const setSpeed = useCallback((v: number) => {
    speed.current = v;
  }, []);

  const stop = useCallback(() => {
    stick.current = { throttle: 0, steering: 0, active: false };
    wasActive.current = false;
    send({ type: "stop" });
  }, [send]);

  return { link, setStick, setSpeed, stop };
}
