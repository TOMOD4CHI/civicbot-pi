import * as Location from "expo-location";
import { useCallback } from "react";

import { PhoneFix } from "../api/carClient";

/**
 * Phone GPS, used as a fallback when the car's GPS has no fix.
 * Returns null (never throws) if permission is denied or no position is available.
 */
export function usePhoneLocation() {
  return useCallback(async (): Promise<PhoneFix | null> => {
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== "granted") return null;
      const recent = await Location.getLastKnownPositionAsync({ maxAge: 10_000, requiredAccuracy: 50 });
      const loc = recent ?? (await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High }));
      return { lat: loc.coords.latitude, lon: loc.coords.longitude, accuracy: loc.coords.accuracy ?? null };
    } catch {
      return null;
    }
  }, []);
}
