#!/usr/bin/env python3
"""
Serveur de commande à lancer sur le Raspberry Pi.
Reçoit des commandes texte (une par ligne) en TCP depuis l'appli desktop.

Protocole :
    DRIVE <gauche> <droite>     valeurs -1.0 .. 1.0
    ARCADE <gaz> <direction>    valeurs -1.0 .. 1.0
    STOP
    PING                        -> répond PONG

Sécurité : si plus aucune commande n'arrive pendant WATCHDOG_TIMEOUT
secondes (perte Wi-Fi, appli fermée...), la voiture s'arrête.
"""
import socket
import threading
import time

import config
from car import Car

car = Car()
last_cmd = time.monotonic()
lock = threading.Lock()


def watchdog():
    while True:
        time.sleep(0.1)
        with lock:
            moving = car.speed_l != 0 or car.speed_r != 0
            if moving and time.monotonic() - last_cmd > config.WATCHDOG_TIMEOUT:
                car.stop()
                print("[watchdog] plus de commande -> STOP")


def handle(line):
    global last_cmd
    parts = line.strip().split()
    if not parts:
        return None
    cmd = parts[0].upper()
    with lock:
        last_cmd = time.monotonic()
        if cmd == "DRIVE" and len(parts) == 3:
            car.drive(float(parts[1]), float(parts[2]))
        elif cmd == "ARCADE" and len(parts) == 3:
            car.arcade(float(parts[1]), float(parts[2]))
        elif cmd == "STOP":
            car.stop()
        elif cmd == "PING":
            return "PONG"
        else:
            return "ERR commande inconnue"
    return "OK"


def client_thread(conn, addr):
    print(f"[+] client connecté : {addr}")
    buf = b""
    try:
        with conn:
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                buf += data
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    try:
                        reply = handle(line.decode())
                    except ValueError:
                        reply = "ERR valeur invalide"
                    if reply:
                        conn.sendall((reply + "\n").encode())
    except OSError:
        pass
    finally:
        with lock:
            car.stop()
        print(f"[-] client déconnecté : {addr} -> STOP")


def main():
    threading.Thread(target=watchdog, daemon=True).start()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((config.HOST, config.PORT))
    srv.listen(1)
    print(f"Serveur voiture prêt sur le port {config.PORT}  (Ctrl+C pour quitter)")
    try:
        while True:
            conn, addr = srv.accept()
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            threading.Thread(target=client_thread, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("\nArrêt.")
    finally:
        car.close()
        srv.close()


if __name__ == "__main__":
    main()
