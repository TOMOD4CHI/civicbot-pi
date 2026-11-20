import { useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";
import { WebView } from "react-native-webview";

import { colors, radius } from "../theme";

type Props = { url: string; enabled: boolean; online: boolean; label?: string };

/**
 * Live MJPEG stream from the car. React Native's <Image> can't play MJPEG on
 * Android, so the car's /viewer page is shown in a WebView.
 */
export function CameraFeed({ url, enabled, online, label }: Props) {
  const [reloadKey, setReloadKey] = useState(0);
  const [loading, setLoading] = useState(true);

  let overlay: string | null = null;
  if (!enabled) overlay = "Video turned off in settings";
  else if (!online) overlay = "Car not reachable";

  return (
    <View style={styles.frame}>
      {enabled && online ? (
        <WebView
          key={`${url}-${reloadKey}`}
          source={{ uri: url }}
          style={styles.web}
          originWhitelist={["*"]}
          scrollEnabled={false}
          bounces={false}
          javaScriptEnabled={false}
          mixedContentMode="always"
          onLoadStart={() => setLoading(true)}
          onLoadEnd={() => setLoading(false)}
          onError={() => setLoading(false)}
        />
      ) : null}

      {overlay ? (
        <View style={styles.overlay}>
          <Text style={styles.overlayText}>{overlay}</Text>
        </View>
      ) : loading ? (
        <View style={styles.overlay} pointerEvents="none">
          <ActivityIndicator color={colors.accent} />
        </View>
      ) : null}

      <View style={styles.badge} pointerEvents="none">
        <View style={[styles.liveDot, { backgroundColor: online && enabled ? colors.danger : colors.muted }]} />
        <Text style={styles.badgeText}>{label ?? "LIVE"}</Text>
      </View>

      {enabled && online ? (
        <Pressable style={styles.reload} onPress={() => setReloadKey((k) => k + 1)} hitSlop={10}>
          <Text style={styles.reloadText}>↻</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  frame: {
    flex: 1,
    backgroundColor: "#000",
    borderRadius: radius.md,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: colors.border,
  },
  web: { flex: 1, backgroundColor: "#000" },
  overlay: { ...StyleSheet.absoluteFill, alignItems: "center", justifyContent: "center" },
  overlayText: { color: colors.muted, fontSize: 15 },
  badge: {
    position: "absolute", top: 10, left: 10, flexDirection: "row", alignItems: "center", gap: 6,
    backgroundColor: "#000a", paddingHorizontal: 10, paddingVertical: 4, borderRadius: radius.pill,
  },
  liveDot: { width: 8, height: 8, borderRadius: 4 },
  badgeText: { color: "#fff", fontSize: 12, fontWeight: "700", letterSpacing: 1 },
  reload: {
    position: "absolute", top: 8, right: 8, width: 34, height: 34, borderRadius: 17,
    backgroundColor: "#000a", alignItems: "center", justifyContent: "center",
  },
  reloadText: { color: "#fff", fontSize: 18 },
});
