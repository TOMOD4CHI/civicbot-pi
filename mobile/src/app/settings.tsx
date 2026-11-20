import { useRouter } from "expo-router";
import { ReactNode, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Switch, Text, TextInput, View } from "react-native";

import { getStatus } from "../api/carClient";
import { useSettings } from "../settings/SettingsContext";
import { colors, radius, space } from "../theme";

export default function SettingsScreen() {
  const router = useRouter();
  const { settings, update } = useSettings();
  const [host, setHost] = useState(settings.carHost);
  const [port, setPort] = useState(String(settings.carPort));
  const [test, setTest] = useState<{ text: string; ok: boolean } | null>(null);

  const portNum = Number(port);
  const valid = host.trim().length > 0 && Number.isInteger(portNum) && portNum > 0 && portNum < 65536;

  async function testConnection() {
    setTest({ text: "Testing…", ok: true });
    try {
      const s = await getStatus(host.trim(), portNum);
      setTest({
        text: `Connected to ${s.device_id}${s.simulate ? " (simulation)" : ""} · camera: ${s.camera.source}` +
          ` · GPS ${s.gps.fix ? "fix" : "no fix"} · server ${s.server.reachable ? "OK" : "unreachable"}`,
        ok: true,
      });
    } catch (e) {
      setTest({ text: `Cannot reach the car: ${e instanceof Error ? e.message : e}`, ok: false });
    }
  }

  async function save() {
    await update({ carHost: host.trim(), carPort: portNum });
    router.back();
  }

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
      <Text style={styles.section}>Car (Raspberry Pi)</Text>
      <View style={styles.card}>
        <Text style={styles.label}>IP address</Text>
        <TextInput
          value={host}
          onChangeText={setHost}
          placeholder="192.168.1.50"
          placeholderTextColor={colors.muted}
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="numbers-and-punctuation"
          style={styles.input}
        />
        <Text style={styles.label}>Port</Text>
        <TextInput value={port} onChangeText={setPort} keyboardType="number-pad" style={styles.input} />
        <Pressable onPress={testConnection} disabled={!valid} style={[styles.btn, !valid && { opacity: 0.5 }]}>
          <Text style={styles.btnText}>Test connection</Text>
        </Pressable>
        {test ? <Text style={[styles.test, { color: test.ok ? colors.ok : colors.danger }]}>{test.text}</Text> : null}
      </View>

      <Text style={styles.section}>Options</Text>
      <View style={styles.card}>
        <Row label="Show live video" hint="Turn off to save Wi-Fi bandwidth">
          <Switch value={settings.showVideo} onValueChange={(v) => update({ showVideo: v })}
            trackColor={{ true: colors.accent }} />
        </Row>
        <Row label="Phone GPS fallback" hint="Used when the car's GPS has no fix">
          <Switch value={settings.usePhoneGpsFallback} onValueChange={(v) => update({ usePhoneGpsFallback: v })}
            trackColor={{ true: colors.accent }} />
        </Row>
      </View>

      <Pressable onPress={save} disabled={!valid} style={[styles.btn, styles.primary, !valid && { opacity: 0.5 }]}>
        <Text style={[styles.btnText, { color: colors.accentInk }]}>Save</Text>
      </Pressable>
      <Text style={styles.footer}>
        The phone, the car and the server must be on the same Wi-Fi network.
      </Text>
    </ScrollView>
  );
}

function Row({ label, hint, children }: { label: string; hint: string; children: ReactNode }) {
  return (
    <View style={styles.row}>
      <View style={{ flex: 1 }}>
        <Text style={styles.rowLabel}>{label}</Text>
        <Text style={styles.hint}>{hint}</Text>
      </View>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  content: { padding: space(4), gap: space(3) },
  section: { color: colors.muted, fontSize: 12, fontWeight: "700", textTransform: "uppercase", letterSpacing: 1 },
  card: {
    backgroundColor: colors.surface, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border,
    padding: space(4), gap: space(2),
  },
  label: { color: colors.muted, fontSize: 13 },
  input: {
    backgroundColor: colors.surface2, color: colors.text, borderRadius: radius.sm, borderWidth: 1,
    borderColor: colors.border, paddingHorizontal: 12, paddingVertical: 10, fontSize: 16, marginBottom: space(1),
  },
  btn: {
    backgroundColor: colors.surface2, borderRadius: radius.sm, paddingVertical: 12, alignItems: "center",
    borderWidth: 1, borderColor: colors.border,
  },
  primary: { backgroundColor: colors.accent, borderColor: colors.accent },
  btnText: { color: colors.text, fontWeight: "700", fontSize: 15 },
  test: { fontSize: 13 },
  row: { flexDirection: "row", alignItems: "center", gap: space(3), paddingVertical: space(1) },
  rowLabel: { color: colors.text, fontSize: 15 },
  hint: { color: colors.muted, fontSize: 12 },
  footer: { color: colors.muted, fontSize: 12, textAlign: "center" },
});
