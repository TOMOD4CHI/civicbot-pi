#!/usr/bin/env python3
"""
Application desktop (Linux) pour piloter la voiture à distance.
Dépendance : python3-tk  (sudo apt install python3-tk)

    python3 car_control_app.py

Commandes clavier : flèches ou Z/Q/S/D (AZERTY) / W/A/S/D, Espace = STOP
"""
import socket
import tkinter as tk
from tkinter import ttk, messagebox

DEFAULT_HOST = "raspberrypi.local"
DEFAULT_PORT = 5005
SEND_PERIOD_MS = 100      # renvoi périodique (le Pi stoppe après 0.5 s sans commande)


class CarApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Voiture Raspberry Pi - L298N")
        self.resizable(False, False)
        self.sock = None
        self.keys = set()
        self.btn_throttle = 0.0
        self.btn_steer = 0.0
        self._build_ui()
        self.bind("<KeyPress>", self._key_down)
        self.bind("<KeyRelease>", self._key_up)
        self.protocol("WM_DELETE_WINDOW", self._quit)
        self.after(SEND_PERIOD_MS, self._loop)

    # ---------------- UI ----------------
    def _build_ui(self):
        pad = {"padx": 6, "pady": 4}
        top = ttk.LabelFrame(self, text="Connexion")
        top.pack(fill="x", **pad)
        ttk.Label(top, text="IP du Pi :").grid(row=0, column=0, **pad)
        self.host = tk.StringVar(value=DEFAULT_HOST)
        ttk.Entry(top, textvariable=self.host, width=18).grid(row=0, column=1, **pad)
        ttk.Label(top, text="Port :").grid(row=0, column=2, **pad)
        self.port = tk.IntVar(value=DEFAULT_PORT)
        ttk.Entry(top, textvariable=self.port, width=6).grid(row=0, column=3, **pad)
        self.btn_conn = ttk.Button(top, text="Connecter", command=self._toggle_conn)
        self.btn_conn.grid(row=0, column=4, **pad)
        self.status = tk.StringVar(value="● Déconnecté")
        self.status_lbl = tk.Label(top, textvariable=self.status, fg="red")
        self.status_lbl.grid(row=1, column=0, columnspan=5, sticky="w", **pad)

        pad_frame = ttk.LabelFrame(self, text="Pilotage (maintenir appuyé)")
        pad_frame.pack(**pad)
        btns = [
            ("▲", 0, 1, 1, 0), ("◀", 1, 0, 0, -1), ("■", 1, 1, None, None),
            ("▶", 1, 2, 0, 1), ("▼", 2, 1, -1, 0),
        ]
        for txt, r, c, t, s in btns:
            b = tk.Button(pad_frame, text=txt, width=5, height=2, font=("Arial", 16))
            b.grid(row=r, column=c, padx=3, pady=3)
            if t is None:
                b.config(bg="#d33", fg="white", command=self._stop)
            else:
                b.bind("<ButtonPress-1>", lambda e, t=t, s=s: self._set_btn(t, s))
                b.bind("<ButtonRelease-1>", lambda e: self._set_btn(0, 0))

        sp = ttk.LabelFrame(self, text="Vitesse max")
        sp.pack(fill="x", **pad)
        self.speed = tk.DoubleVar(value=60)
        ttk.Scale(sp, from_=10, to=100, variable=self.speed,
                  command=lambda v: self.speed_lbl.config(text=f"{float(v):.0f} %")
                  ).pack(side="left", fill="x", expand=True, **pad)
        self.speed_lbl = ttk.Label(sp, text="60 %", width=6)
        self.speed_lbl.pack(side="right", **pad)

        self.mode_pivot = tk.BooleanVar(value=True)
        ttk.Checkbutton(self, text="Tourner sur place (pivot) quand seule ◀/▶ est appuyée",
                        variable=self.mode_pivot).pack(anchor="w", **pad)

        self.info = tk.StringVar(value="G: 0 %   D: 0 %")
        ttk.Label(self, textvariable=self.info, font=("Courier", 12)).pack(**pad)
        ttk.Label(self, text="Clavier : flèches / ZQSD / WASD — Espace = STOP",
                  foreground="gray").pack(**pad)

    # ---------------- réseau ----------------
    def _toggle_conn(self):
        if self.sock:
            self._disconnect()
            return
        try:
            s = socket.create_connection((self.host.get(), self.port.get()), timeout=3)
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.sendall(b"PING\n")
            if s.recv(64).strip() != b"PONG":
                raise ConnectionError("réponse inattendue")
            s.settimeout(0.5)
            self.sock = s
            self.status.set(f"● Connecté à {self.host.get()}")
            self.status_lbl.config(fg="green")
            self.btn_conn.config(text="Déconnecter")
            self.focus_set()
        except Exception as e:
            messagebox.showerror("Connexion", f"Impossible de joindre le Pi :\n{e}\n\n"
                                 "Vérifie que server.py tourne sur le Pi.")

    def _disconnect(self):
        try:
            self.sock.sendall(b"STOP\n")
            self.sock.close()
        except Exception:
            pass
        self.sock = None
        self.status.set("● Déconnecté")
        self.status_lbl.config(fg="red")
        self.btn_conn.config(text="Connecter")

    def _send(self, line):
        if not self.sock:
            return
        try:
            self.sock.sendall((line + "\n").encode())
            self.sock.recv(64)   # vide la réponse OK
        except Exception:
            self._disconnect()
            messagebox.showwarning("Connexion", "Connexion perdue avec le Pi.")

    # ---------------- contrôle ----------------
    def _set_btn(self, t, s):
        self.btn_throttle, self.btn_steer = t, s

    def _key_down(self, e):
        self.keys.add(e.keysym.lower())
        if e.keysym == "space":
            self._stop()

    def _key_up(self, e):
        self.keys.discard(e.keysym.lower())

    def _stop(self):
        self.keys.clear()
        self.btn_throttle = self.btn_steer = 0
        self._send("STOP")

    def _compute(self):
        k = self.keys
        t = (1 if k & {"up", "z", "w"} else 0) - (1 if k & {"down", "s"} else 0)
        s = (1 if k & {"right", "d"} else 0) - (1 if k & {"left", "q", "a"} else 0)
        if t == 0 and s == 0:
            t, s = self.btn_throttle, self.btn_steer
        vmax = self.speed.get() / 100
        if t == 0 and s != 0:
            if self.mode_pivot.get():
                return s * vmax, -s * vmax                   # pivot sur place
            return (vmax if s > 0 else 0), (vmax if s < 0 else 0)  # une seule roue
        left = t + 0.5 * s * (1 if t >= 0 else -1)
        right = t - 0.5 * s * (1 if t >= 0 else -1)
        m = max(1.0, abs(left), abs(right))
        return left / m * vmax, right / m * vmax

    def _loop(self):
        l, r = self._compute()
        self.info.set(f"G: {l*100:+4.0f} %   D: {r*100:+4.0f} %")
        self._send(f"DRIVE {l:.2f} {r:.2f}")
        self.after(SEND_PERIOD_MS, self._loop)

    def _quit(self):
        if self.sock:
            self._disconnect()
        self.destroy()


if __name__ == "__main__":
    CarApp().mainloop()
