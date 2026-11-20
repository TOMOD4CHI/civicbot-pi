import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";

import { colors, radius } from "../theme";

// ---------------------------------------------------------------- speed
export const SPEEDS = [
  { label: "Slow", value: 0.4 },
  { label: "Normal", value: 0.7 },
  { label: "Fast", value: 1 },
];

export function SpeedSelector({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  return (
    <View style={styles.seg} accessibilityRole="radiogroup">
      {SPEEDS.map((s) => {
        const active = s.value === value;
        return (
          <Pressable
            key={s.label}
            onPress={() => onChange(s.value)}
            style={[styles.segBtn, active && styles.segActive]}
            accessibilityRole="radio"
            accessibilityState={{ selected: active }}
          >
            <Text style={[styles.segText, active && styles.segTextActive]}>{s.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

// ---------------------------------------------------------------- stop
export function StopButton({ onPress }: { onPress: () => void }) {
  return (
    <Pressable
      onPressIn={onPress}
      style={({ pressed }) => [styles.stop, pressed && { backgroundColor: colors.dangerDark }]}
      accessibilityRole="button"
      accessibilityLabel="Emergency stop"
    >
      <Text style={styles.stopText}>STOP</Text>
    </Pressable>
  );
}

// ---------------------------------------------------------------- send location
export type SendState = "idle" | "sending" | "done" | "error";

export function SendLocationButton({ state, onPress, disabled }: {
  state: SendState; onPress: () => void; disabled?: boolean;
}) {
  const label = { idle: "Send location", sending: "Sending…", done: "Sent ✓", error: "Retry" }[state];
  const bg = state === "done" ? colors.ok : state === "error" ? colors.danger : colors.accent;
  const fg = state === "idle" || state === "sending" ? colors.accentInk : "#fff";
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled || state === "sending"}
      style={({ pressed }) => [styles.send, { backgroundColor: bg }, (pressed || disabled) && { opacity: 0.6 }]}
      accessibilityRole="button"
      accessibilityLabel="Report a pothole at the current location"
    >
      {state === "sending" ? <ActivityIndicator color={fg} /> : <Text style={styles.sendIcon}>📍</Text>}
      <Text style={[styles.sendText, { color: fg }]}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  seg: {
    flexDirection: "row", backgroundColor: colors.surface2, borderRadius: radius.sm + 2, padding: 3, gap: 2,
  },
  segBtn: { flex: 1, paddingVertical: 8, borderRadius: radius.sm, alignItems: "center" },
  segActive: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  segText: { color: colors.muted, fontWeight: "600", fontSize: 13 },
  segTextActive: { color: colors.text },

  stop: {
    width: 92, height: 92, borderRadius: 46, backgroundColor: colors.danger,
    alignItems: "center", justifyContent: "center", borderWidth: 4, borderColor: "#ffffff30",
    elevation: 6, shadowColor: "#000", shadowOpacity: 0.4, shadowRadius: 8,
  },
  stopText: { color: "#fff", fontWeight: "900", fontSize: 18, letterSpacing: 1 },

  send: {
    flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8,
    paddingVertical: 14, paddingHorizontal: 18, borderRadius: radius.md,
  },
  sendIcon: { fontSize: 18 },
  sendText: { fontWeight: "800", fontSize: 16 },
});
