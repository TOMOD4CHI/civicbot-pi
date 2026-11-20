# =============================================================
#  Configuration du serveur GPS (machine Linux)
# =============================================================

HOST = "0.0.0.0"
PORT = 8000
DB_PATH = "gps_track.db"

# --- Géocodage inverse (coordonnées -> adresse) -------------------
# Fournisseur principal : Nominatim (OpenStreetMap), gratuit, sans clé.
# Politique d'utilisation à respecter :
#   https://operations.osmfoundation.org/policies/nominatim/
#   - User-Agent identifiant TON application (obligatoire)
#   - 1 requête par seconde MAXIMUM, pas d'usage intensif
#   - mettre les résultats en cache
# Mets ton e-mail ici (setup_linux.sh le fait pour toi) :
CONTACT_EMAIL = ""

USER_AGENT = "RobotCarGPS/1.0 (student project; contact: {email})"

# Secours si Nominatim ne répond pas : Photon (komoot), gratuit, sans clé
PHOTON_URL = "https://photon.komoot.io/reverse"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"

# On ne redemande une adresse que si la voiture a bougé d'au moins
# GEOCODE_MIN_DISTANCE_M mètres ET au plus une fois toutes les
# GEOCODE_MIN_INTERVAL_S secondes (bien en dessous de la limite).
GEOCODE_MIN_DISTANCE_M = 25
GEOCODE_MIN_INTERVAL_S = 15
LANGUAGE = "fr"
