import * as Haptics from "expo-haptics";
import { Stack, useRouter } from "expo-router";
import { useCallback, useEffect, useRef, useState } from "react";
import { Pressable, StyleSheet, Text, useWindowDimensions, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { carUrls, sendReport } from "../api/carClient";
import { CameraFeed } from "../components/CameraFeed";
import { SendLocationButton, SendState, SpeedSelector, SPEEDS, StopButton } from "../components/Controls";
import { Joystick } from "../components/Joystick";
import { CarStatusBar } from "../components/StatusBar";
import { Toast, ToastMessage } from "../components/Toast";
import { useCarControl } from "../hooks/useCarControl";
import { useCarStatus } from "../hooks/useCarStatus";
import { usePhoneLocation } from "../hooks/usePhoneLocation";
import { useSettings } from "../settings/SettingsContext";
import { colors, space } from "../theme";

export default function DriveScreen() {
  const router = useRouter();
  const { settings } = useSettings();
  const { carHost: host, carPort: port } = settings;
  const { width, height } = useWindowDimensions();
  const landscape = width > height;

  const control = useCarControl(host, port);
  const status = useCarStatus(host, port);
  const getPhoneLocation = usePhoneLocation();

  const [speed, setSpeed] = useState(SPEEDS[1].value);
  const [sendState, setSendState] = useState<SendState>("idle");
  const [toast, setToast] = useState<ToastMessage>(null);
  const resetTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const { setSpeed: setCarSpeed, stop: stopCar } = control;
  useEffect(() => setCarSpeed(speed), [speed, setCarSpeed]);
  useEffect(() => () => clearTimeout(resetTimer.current), []);

  const showToast = (text: string, kind: "ok" | "error") => setToast({ text, kind, id: Date.now() });

  const onStop = useCallback(() => {
    stopCar();
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy).catch(() => {});
  }, [stopCar]);

  // "Send location": the car picks its own GPS fix, or falls back to the phone's.
  const onSendLocation = useCallback(async () => {
    setSendState("sending");
    clearTimeout(resetTimer.current);
    try {
      const phone = settings.usePhoneGpsFallback ? await getPhoneLocation() : null;
      const r = await sendReport(host, port, phone);
      setSendState("done");
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
      showToast(
        `Pothole #${r.id} saved · ${r.source === "car_gps" ? "car GPS" : "phone GPS"} · ` +
          `${r.lat.toFixed(5)}, ${r.lon.toFixed(5)}${r.has_image ? " · with photo" : ""}`,
        "ok",
      );
    } catch (e) {
      setSendState("error");
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error).catch(() => {});
      showToast(`Could not send location: ${e instanceof Error ? e.message : String(e)}`, "error");
    } finally {
      resetTimer.current = setTimeout(() => setSendState("idle"), 2500);
    }
  }, [host, port, settings.usePhoneGpsFallback, getPhoneLocation]);

  const online = control.link === "online";
  const joystickSize = Math.min(landscape ? height * 0.5 : width * 0.46, 200);

  const camera = (
    <CameraFeed
      url={carUrls(host, port).viewer}
      enabled={settings.showVideo}
      online={status !== null}
      label={status?.simulate ? "SIM" : "LIVE"}
    />
  );

  const controls = (
    <View style={[styles.controls, landscape && styles.controlsLandscape]}>
      <View style={styles.driveRow}>
        <Joystick size={joystickSize} disabled={!online} onMove={control.setStick} />
        <View style={styles.side}>
          <StopButton onPress={onStop} />
          <Text style={styles.hint}>{online ? "Hold the stick to drive" : "Waiting for the car…"}</Text>
        </View>
      </View>
      <SpeedSelector value={speed} onChange={setSpeed} />
      <SendLocationButton state={sendState} onPress={onSendLocation} disabled={status === null} />
    </View>
  );

  return (
    <SafeAreaView style={styles.screen} edges={["left", "right", "bottom"]}>
      <Stack.Screen
        options={{
          headerRight: () => (
            <Pressable onPress={() => router.navigate("/settings")} hitSlop={12} accessibilityLabel="Settings">
              <Text style={styles.gear}>⚙</Text>
            </Pressable>
          ),
        }}
      />
      <CarStatusBar link={control.link} status={status} />
      {landscape ? (
        <View style={styles.landscape}>
          <View style={{ flex: 1.4 }}>{camera}</View>
          {controls}
        </View>
      ) : (
        <>
          <View style={styles.cameraPortrait}>{camera}</View>
          {controls}
        </>
      )}
      <Toast message={toast} />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg, padding: space(3), gap: space(3) },
  cameraPortrait: { flex: 1, minHeight: 200 },
  landscape: { flex: 1, flexDirection: "row", gap: space(3) },
  controls: { gap: space(3) },
  controlsLandscape: { flex: 1, justifyContent: "center" },
  driveRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: space(3) },
  side: { flex: 1, alignItems: "center", gap: space(2) },
  hint: { color: colors.muted, fontSize: 12, textAlign: "center" },
  gear: { color: colors.text, fontSize: 22, paddingHorizontal: 4 },
});
