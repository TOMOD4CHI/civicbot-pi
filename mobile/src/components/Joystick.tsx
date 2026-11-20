import { useMemo, useRef } from "react";
import { Animated, PanResponder, StyleSheet, Text, View } from "react-native";

import { colors } from "../theme";

type Props = {
  size?: number;
  disabled?: boolean;
  /** throttle: -1 (back) .. 1 (forward), steering: -1 (left) .. 1 (right) */
  onMove: (throttle: number, steering: number, active: boolean) => void;
};

const DEADZONE = 0.08;

export function Joystick({ size = 180, disabled, onMove }: Props) {
  const knob = size * 0.38;
  const max = (size - knob) / 2;
  const pos = useRef(new Animated.ValueXY({ x: 0, y: 0 })).current;

  const responder = useMemo(
    () =>
      PanResponder.create({
        onStartShouldSetPanResponder: () => !disabled,
        onMoveShouldSetPanResponder: () => !disabled,
        onPanResponderTerminationRequest: () => false,
        onPanResponderGrant: () => onMove(0, 0, true),
        onPanResponderMove: (_, g) => {
          let x = g.dx;
          let y = g.dy;
          const d = Math.hypot(x, y);
          if (d > max) {
            x = (x / d) * max;
            y = (y / d) * max;
          }
          pos.setValue({ x, y });
          const nx = x / max;
          const ny = -y / max;
          onMove(Math.abs(ny) < DEADZONE ? 0 : ny, Math.abs(nx) < DEADZONE ? 0 : nx, true);
        },
        onPanResponderRelease: () => release(),
        onPanResponderTerminate: () => release(),
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [disabled, max, onMove],
  );

  function release() {
    onMove(0, 0, false);
    Animated.spring(pos, { toValue: { x: 0, y: 0 }, useNativeDriver: true, friction: 6 }).start();
  }

  return (
    <View
      {...responder.panHandlers}
      style={[styles.base, { width: size, height: size, borderRadius: size / 2 }, disabled && styles.disabled]}
      accessibilityLabel="Drive joystick"
    >
      <Text style={[styles.arrow, { top: 8 }]}>▲</Text>
      <Text style={[styles.arrow, { bottom: 8 }]}>▼</Text>
      <Text style={[styles.arrow, { left: 12, top: size / 2 - 10 }]}>◀</Text>
      <Text style={[styles.arrow, { right: 12, top: size / 2 - 10 }]}>▶</Text>
      <Animated.View
        style={[
          styles.knob,
          { width: knob, height: knob, borderRadius: knob / 2 },
          { transform: pos.getTranslateTransform() },
        ]}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  base: {
    backgroundColor: colors.surface2,
    borderWidth: 2,
    borderColor: colors.border,
    alignItems: "center",
    justifyContent: "center",
  },
  disabled: { opacity: 0.4 },
  knob: {
    backgroundColor: colors.accent,
    borderWidth: 4,
    borderColor: "#ffffff22",
    shadowColor: "#000",
    shadowOpacity: 0.4,
    shadowRadius: 6,
    elevation: 6,
  },
  arrow: { position: "absolute", color: colors.muted, fontSize: 14, alignSelf: "center" },
});
