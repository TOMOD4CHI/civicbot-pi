import { StyleSheet, Text, View } from "react-native";

import { CarStatus } from "../api/carClient";
import { LinkState } from "../hooks/useCarControl";
import { colors, radius } from "../theme";

type Chip = { label: string; color: string };

export function CarStatusBar({ link, status }: { link: LinkState; status: CarStatus | null }) {
  const chips: Chip[] = [
    link === "online"
      ? { label: "Car connected", color: colors.ok }
      : link === "connecting"
        ? { label: "Connecting…", color: colors.warn }
        : { label: "Car offline", color: colors.danger },
  ];
  if (status) {
    const g = status.gps;
    chips.push(
      g.fix
        ? { label: `GPS fix · ${g.sats} sats`, color: colors.ok }
        : { label: g.connected ? `No GPS fix · ${g.sats} sats` : "GPS not connected", color: colors.warn },
    );
    chips.push(
      status.server.reachable
        ? { label: "Server OK", color: colors.ok }
        : { label: "Server unreachable", color: colors.danger },
    );
    if (status.simulate) chips.push({ label: "Simulation", color: colors.info });
  }

  return (
    <View style={styles.row}>
      {chips.map((c) => (
        <View key={c.label} style={styles.chip}>
          <View style={[styles.dot, { backgroundColor: c.color }]} />
          <Text style={styles.text} numberOfLines={1}>
            {c.label}
          </Text>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  chip: {
    flexDirection: "row", alignItems: "center", gap: 6, backgroundColor: colors.surface,
    borderWidth: 1, borderColor: colors.border, borderRadius: radius.pill, paddingHorizontal: 10, paddingVertical: 5,
  },
  dot: { width: 8, height: 8, borderRadius: 4 },
  text: { color: colors.text, fontSize: 12, fontWeight: "500" },
});
