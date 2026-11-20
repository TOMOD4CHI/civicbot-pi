import { useEffect, useRef } from "react";
import { Animated, StyleSheet, Text } from "react-native";

import { colors, radius } from "../theme";

export type ToastMessage = { text: string; kind: "ok" | "error"; id: number } | null;

export function Toast({ message }: { message: ToastMessage }) {
  const opacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (!message) return;
    opacity.setValue(0);
    Animated.sequence([
      Animated.timing(opacity, { toValue: 1, duration: 180, useNativeDriver: true }),
      Animated.delay(3200),
      Animated.timing(opacity, { toValue: 0, duration: 300, useNativeDriver: true }),
    ]).start();
  }, [message, opacity]);

  if (!message) return null;
  return (
    <Animated.View
      pointerEvents="none"
      style={[styles.toast, { opacity, borderColor: message.kind === "ok" ? colors.ok : colors.danger }]}
    >
      <Text style={styles.text}>{message.text}</Text>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  toast: {
    position: "absolute", left: 16, right: 16, bottom: 24, padding: 14, borderRadius: radius.md,
    backgroundColor: colors.surface, borderWidth: 1, borderLeftWidth: 5,
    elevation: 8, shadowColor: "#000", shadowOpacity: 0.4, shadowRadius: 10,
  },
  text: { color: colors.text, fontSize: 14 },
});
