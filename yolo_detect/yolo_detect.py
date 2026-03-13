import time
import math
import subprocess
from typing import Dict, List, Tuple, Optional

import cv2
import numpy as np
import mss
import win32gui
from ultralytics import YOLO


# =========================
# 基本配置
# =========================

MODEL_PATH = r"C:\Users\28478\Desktop\Run_Auto\Run_Auto\runs\detect\train5\weights\best.pt"
ADB_EXE = r"C:\Program Files\NetEase\MuMu Player 12\shell\adb.exe"
DEVICE_SERIAL = "127.0.0.1:16384"

WINDOW_TITLE_KEYWORD = "MuMu"

CONF_THRES = 0.30
IMGSZ = 416
DEVICE_ID = 0

# 模拟器竖屏分辨率
DEVICE_W = 910
DEVICE_H = 1600

ENABLE_CONTROL = True

# =========================
# 时序参数（这版是偏保守、偏稳定）
# =========================
ACTION_COOLDOWN = 0.05         # 任意动作最小间隔
LANE_CHANGE_LOCK = 0.10         # 换道后短暂禁止再次换道
POST_ACTION_FREEZE = 0.05       # jump/roll 后短暂冻结，防止连发
SAME_TARGET_SUPPRESS = 0.05    # 同一目标动作抑制时间

# =========================
# ROI
# =========================
ROI_X1 = 0.32
ROI_Y1 = 0.22
ROI_X2 = 0.68
ROI_Y2 = 0.66

# =========================
# 透视车道边界
# y_norm=0 顶部，y_norm=1 底部
# 这两个边界都做成斜线，而不是竖线
# 你后面可以微调这四个数
# =========================
LEFT_BOUND_TOP = 0.41
LEFT_BOUND_BOTTOM = 0.29

MID_BOUND_TOP = 0.59
MID_BOUND_BOTTOM = 0.72

# =========================
# 动作触发阈值（基于 danger_score）
# 数值越大，说明目标越“近 / 危险”
# =========================
LANE_CHANGE_TRIGGER = 0.25
JUMP_TRIGGER = 0.25
ROLL_TRIGGER = 0.25

# must_hit 对齐阈值
MUST_HIT_ALIGN_TRIGGER = 0.08

# 所有动作都做确认
REQUIRED_CONFIRM = {
    "none": 1,
    "move_left": 2,
    "move_right": 2,
    "jump": 1,
    "roll": 1,
}

# =========================
# 运行时状态
# =========================
current_lane = "middle"
last_action_time = 0.0
last_lane_change_time = 0.0
last_non_lane_action_time = 0.0
last_action = "none"

pending_action = "none"
pending_count = 0

last_executed_target_key = None
last_executed_target_time = 0.0

frame_idx = 0


# =========================
# 找窗口
# =========================

def find_mumu_window():
    hwnds = []

    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if WINDOW_TITLE_KEYWORD.lower() in title.lower():
                hwnds.append((hwnd, title))

    win32gui.EnumWindows(callback, None)

    if not hwnds:
        raise RuntimeError("没找到 MuMu 窗口，请确认模拟器已打开。")

    hwnd, title = hwnds[0]
    print(f"[WIN] 使用窗口: {title}")
    return hwnd


def get_client_rect_on_screen(hwnd):
    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    pt_left_top = win32gui.ClientToScreen(hwnd, (left, top))
    pt_right_bottom = win32gui.ClientToScreen(hwnd, (right, bottom))
    return pt_left_top[0], pt_left_top[1], pt_right_bottom[0], pt_right_bottom[1]


def crop_game_area(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    col_mean = gray.mean(axis=0)

    valid = col_mean > 12
    xs = np.where(valid)[0]

    if len(xs) < 50:
        return frame

    x1 = int(xs[0])
    x2 = int(xs[-1])

    pad = max(4, int((x2 - x1) * 0.01))
    x1 = min(max(0, x1 + pad), frame.shape[1] - 1)
    x2 = max(min(frame.shape[1] - 1, x2 - pad), x1 + 1)

    return frame[:, x1:x2].copy()


def capture_window(hwnd, sct):
    left, top, right, bottom = get_client_rect_on_screen(hwnd)

    monitor = {
        "left": left,
        "top": top,
        "width": right - left,
        "height": bottom - top,
    }

    img = np.array(sct.grab(monitor))
    frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    frame = crop_game_area(frame)
    return frame


# =========================
# ADB 控制
# =========================

def adb_swipe(x1, y1, x2, y2, duration=80):
    cmd = [
        ADB_EXE, "-s", DEVICE_SERIAL, "shell", "input", "swipe",
        str(x1), str(y1), str(x2), str(y2), str(duration)
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def do_action(action: str):
    global current_lane, last_action_time, last_lane_change_time
    global last_non_lane_action_time, last_action

    now = time.time()

    if action == "none":
        return False

    if now - last_action_time < ACTION_COOLDOWN:
        print(f"[DEBUG] block by ACTION_COOLDOWN: {action}")
        return False

    # 你手测成功的坐标
    cx = 455
    cy = 1180

    if action in ("move_left", "move_right"):
        if now - last_lane_change_time < LANE_CHANGE_LOCK:
            print(f"[DEBUG] block by LANE_CHANGE_LOCK: {action}")
            return False

    else:
        # jump / roll 之后，短时间不再发第二个 jump/roll
        if now - last_non_lane_action_time < POST_ACTION_FREEZE:
            print(f"[DEBUG] block by POST_ACTION_FREEZE: {action}")
            return False

    if action == "move_left":
        adb_swipe(cx, cy, 220, cy, 150)
        if current_lane == "middle":
            current_lane = "left"
        elif current_lane == "right":
            current_lane = "middle"

        last_lane_change_time = now
        last_action_time = now
        last_action = action
        return True

    if action == "move_right":
        adb_swipe(cx, cy, 700, cy, 150)
        if current_lane == "middle":
            current_lane = "right"
        elif current_lane == "left":
            current_lane = "middle"

        last_lane_change_time = now
        last_action_time = now
        last_action = action
        return True

    if action == "jump":
        adb_swipe(cx, cy, cx, 780, 150)
        last_action_time = now
        last_non_lane_action_time = now
        last_action = action
        return True

    if action == "roll":
        adb_swipe(cx, cy, cx, 1500, 150)
        last_action_time = now
        last_non_lane_action_time = now
        last_action = action
        return True

    return False


# =========================
# ROI / 车道 / 检测
# =========================

def crop_roi(frame):
    h, w = frame.shape[:2]
    x1 = int(w * ROI_X1)
    y1 = int(h * ROI_Y1)
    x2 = int(w * ROI_X2)
    y2 = int(h * ROI_Y2)
    return frame[y1:y2, x1:x2].copy(), (x1, y1, x2, y2)


def lane_bounds_at_y(y_norm: float) -> Tuple[float, float]:
    left_b = LEFT_BOUND_TOP + (LEFT_BOUND_BOTTOM - LEFT_BOUND_TOP) * y_norm
    mid_b = MID_BOUND_TOP + (MID_BOUND_BOTTOM - MID_BOUND_TOP) * y_norm
    return left_b, mid_b


def get_lane_by_xy(x_center: float, y_center: float, roi_width: int, roi_height: int) -> str:
    xn = x_center / max(roi_width, 1)
    yn = y_center / max(roi_height, 1)

    left_b, mid_b = lane_bounds_at_y(yn)

    if xn < left_b:
        return "left"
    elif xn < mid_b:
        return "middle"
    return "right"


def is_danger_label(label: str) -> bool:
    return label in {"lane", "jump", "roll"}


def make_target_key(d: Dict) -> Tuple:
    # 用类别 + 车道 + 量化位置 构成“同一目标”近似 key
    qx = int(d["x_center"] / 18)
    qy = int(d["y_bottom"] / 18)
    return (d["label"], d["lane"], qx, qy)


def calc_danger_score(d: Dict, roi_width: int, roi_height: int) -> float:
    """
    不同障碍用不同的危险感知：
    - lane：更看重提前换道，所以更重 y_bottom，也给 box_h 一点权重
    - jump / roll：更像“接近角色再触发”，主要看 y_bottom
    """
    yb = d["y_bottom"] / max(roi_height, 1)
    bh = d["box_h"] / max(roi_height, 1)

    label = d["label"]

    if label == "lane":
        # 更早判危险，方便提前换道
        score = yb * 0.72 + bh * 0.28

    elif label == "jump":
        # jump 要更靠近再触发，弱化 box_h 干扰
        score = yb * 0.90 + bh * 0.10

    elif label == "roll":
        # roll 也更靠近再触发
        score = yb * 0.92 + bh * 0.08

    else:
        score = yb * 0.85 + bh * 0.15

    return score


def lane_clearance_score(objs: List[Dict]) -> float:
    """
    越大越安全。
    """
    if not objs:
        return 1e9
    nearest = max(objs, key=lambda d: d["danger_score"])
    return 1.0 - nearest["danger_score"]


def parse_detections(results, names, roi_shape):
    rh, rw = roi_shape[:2]
    detections = []

    if len(results) == 0:
        return detections

    for box in results[0].boxes:
        bx1, by1, bx2, by2 = box.xyxy[0].tolist()
        cls_id = int(box.cls[0].item())
        conf = float(box.conf[0].item())

        label = names[cls_id]
        cx = (bx1 + bx2) / 2
        cy = (by1 + by2) / 2
        bw = max(1.0, bx2 - bx1)
        bh = max(1.0, by2 - by1)

        lane = get_lane_by_xy(cx, cy, rw, rh)

        d = {
            "label": label,
            "conf": conf,
            "lane": lane,
            "bbox": [int(bx1), int(by1), int(bx2), int(by2)],
            "x_center": cx,
            "y_center": cy,
            "y_bottom": by2,
            "box_w": bw,
            "box_h": bh,
        }
        d["danger_score"] = calc_danger_score(d, rw, rh)
        d["target_key"] = make_target_key(d)

        detections.append(d)

    return detections


def get_lane_danger_objects(detections: List[Dict]) -> Dict[str, List[Dict]]:
    lane_objs = {"left": [], "middle": [], "right": []}
    for d in detections:
        if is_danger_label(d["label"]):
            lane_objs[d["lane"]].append(d)
    return lane_objs


def get_best_safe_lane(current_lane: str, lane_objs: Dict[str, List[Dict]]) -> str:
    scores = {lane: lane_clearance_score(objs) for lane, objs in lane_objs.items()}
    candidate_lanes = [l for l in ["left", "middle", "right"] if l != current_lane]
    best_score = max(scores[l] for l in candidate_lanes)
    best_lanes = [l for l in candidate_lanes if scores[l] == best_score]

    # 从 middle 时偏右；其他情况按唯一可达方向
    if current_lane == "middle":
        return "right" if "right" in best_lanes else best_lanes[0]
    if current_lane == "left":
        return "middle"
    return "middle"


def action_to_reach_lane(current_lane: str, target_lane: str) -> str:
    if current_lane == target_lane:
        return "none"
    if current_lane == "left" and target_lane == "middle":
        return "move_right"
    if current_lane == "middle" and target_lane == "left":
        return "move_left"
    if current_lane == "middle" and target_lane == "right":
        return "move_right"
    if current_lane == "right" and target_lane == "middle":
        return "move_left"
    # 不能跨两道，先向中间走
    if current_lane == "left" and target_lane == "right":
        return "move_right"
    if current_lane == "right" and target_lane == "left":
        return "move_left"
    return "none"


def recently_executed_same_target(target_key) -> bool:
        return False


def register_executed_target(target_key):
    global last_executed_target_key, last_executed_target_time
    last_executed_target_key = target_key
    last_executed_target_time = time.time()


def decide_action(
    detections: List[Dict],
    roi_width: int,
    roi_height: int,
    current_lane: str = "middle"
):
    lane_objs = get_lane_danger_objects(detections)
    scores = {lane: lane_clearance_score(objs) for lane, objs in lane_objs.items()}
    current_objs = lane_objs[current_lane]

    debug = {
        "reason": "",
        "raw_target_key": None,
        "nearest_current": None,
        "nearest_must_hit": None,
    }

    print(f"[DEBUG] current_lane={current_lane}")
    print(f"[DEBUG] left={len(lane_objs['left'])}, middle={len(lane_objs['middle'])}, right={len(lane_objs['right'])}")

    # 0) must_hit 优先
    must_hits = [d for d in detections if d["label"] == "must_hit"]
    if must_hits:
        target = max(must_hits, key=lambda d: d["danger_score"])
        debug["nearest_must_hit"] = target
        print(
            f"[DEBUG] nearest must_hit: lane={target['lane']}, "
            f"score={target['danger_score']:.3f}, yb={target['y_bottom']:.1f}"
        )

        # must_hit 足够近时，只对齐，不做多余动作
        if target["danger_score"] >= MUST_HIT_ALIGN_TRIGGER:
            act = action_to_reach_lane(current_lane, target["lane"])
            if act != "none":
                debug["reason"] = "must_hit_align"
                debug["raw_target_key"] = target["target_key"]
                print(f"[DEBUG] return {act} for must_hit")
                return act, scores, lane_objs, debug
            else:
                debug["reason"] = "must_hit_aligned"
                print("[DEBUG] must_hit already aligned")
                return "none", scores, lane_objs, debug

    # 1) 只处理当前道最近危险，不再追“全局最近危险”
    if current_objs:
        nearest = max(current_objs, key=lambda d: d["danger_score"])
        debug["nearest_current"] = nearest
        label = nearest["label"]
        score = nearest["danger_score"]
        yb_norm = nearest["y_bottom"] / max(roi_height, 1)

        print(
            f"[DEBUG] nearest in current lane: {label}, lane={nearest['lane']}, "
            f"score={score:.3f}, yb={nearest['y_bottom']:.1f}, ybn={yb_norm:.3f}, bh={nearest['box_h']:.1f}"
        )

        # 1) 当前道 lane：优先提前换道
        if label == "lane":
            if score >= LANE_CHANGE_TRIGGER:
                best_lane = get_best_safe_lane(current_lane, lane_objs)
                act = action_to_reach_lane(current_lane, best_lane)
                debug["reason"] = "current_lane_obstacle"
                debug["raw_target_key"] = nearest["target_key"]
                print(f"[DEBUG] return {act} for current lane obstacle")
                return act, scores, lane_objs, debug
            else:
                debug["reason"] = "lane_not_urgent"
                print("[DEBUG] current lane obstacle not urgent yet")
                return "none", scores, lane_objs, debug

        # 2) 当前道 jump：更靠近再触发，主要看 y_bottom
        if label == "jump":
            if score >= JUMP_TRIGGER and yb_norm >= 0.60:
                debug["reason"] = "current_jump"
                debug["raw_target_key"] = nearest["target_key"]
                print("[DEBUG] return jump")
                return "jump", scores, lane_objs, debug
            else:
                debug["reason"] = "jump_not_urgent"
                print("[DEBUG] jump not urgent yet")
                return "none", scores, lane_objs, debug

        # 3) 当前道 roll：比 jump 稍微早一点点也可以
        if label == "roll":
            if score >= ROLL_TRIGGER and yb_norm >= 0.56:
                debug["reason"] = "current_roll"
                debug["raw_target_key"] = nearest["target_key"]
                print("[DEBUG] return roll")
                return "roll", scores, lane_objs, debug
            else:
                debug["reason"] = "roll_not_urgent"
                print("[DEBUG] roll not urgent yet")
                return "none", scores, lane_objs, debug

    # 2) 其他情况：什么都不做
    debug["reason"] = "idle"
    print("[DEBUG] action = none")
    return "none", scores, lane_objs, debug


def stabilize_action(raw_action: str, raw_target_key):
    global pending_action, pending_count

    if raw_action == "none":
        pending_action = "none"
        pending_count = 0
        return "none"

    if raw_action == pending_action:
        pending_count += 1
    else:
        pending_action = raw_action
        pending_count = 1

    need = REQUIRED_CONFIRM.get(raw_action, 1)

    if pending_count >= need:
        return raw_action
    return "none"


# =========================
# 可视化
# =========================

def draw_lane_guides(vis):
    h, w = vis.shape[:2]

    for y in range(0, h, 16):
        yn = y / max(h, 1)
        lb, mb = lane_bounds_at_y(yn)
        x1 = int(lb * w)
        x2 = int(mb * w)
        cv2.circle(vis, (x1, y), 1, (255, 255, 0), -1)
        cv2.circle(vis, (x2, y), 1, (255, 255, 0), -1)


def draw_debug_roi(roi, detections, raw_action, stable_action, fps, scores, debug):
    vis = roi.copy()
    h, w = vis.shape[:2]

    draw_lane_guides(vis)

    for d in detections:
        bx1, by1, bx2, by2 = d["bbox"]

        color = (0, 255, 0)
        if d["label"] == "must_hit":
            color = (0, 215, 255)
        elif d["label"] == "jump":
            color = (255, 180, 0)
        elif d["label"] == "roll":
            color = (255, 0, 255)
        elif d["label"] == "lane":
            color = (0, 120, 255)

        cv2.rectangle(vis, (bx1, by1), (bx2, by2), color, 2)
        cv2.putText(
            vis,
            f"{d['label']} {d['lane']} ds={d['danger_score']:.2f}",
            (bx1, max(20, by1 - 6)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.50,
            color,
            2
        )

    lines = [
        f"FPS: {fps:.1f}",
        f"CONTROL: {ENABLE_CONTROL}",
        f"LANE: {current_lane}",
        f"RAW: {raw_action}",
        f"EXEC: {stable_action}",
        f"reason: {debug.get('reason', '')}",
        f"scores: L={scores['left']:.2f} M={scores['middle']:.2f} R={scores['right']:.2f}",
    ]

    yy = 28
    for line in lines:
        color = (0, 0, 255) if line.startswith("EXEC") else (255, 255, 255)
        cv2.putText(
            vis,
            line,
            (10, yy),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.62,
            color,
            2
        )
        yy += 26

    return vis


# =========================
# 主循环
# =========================

def main():
    global ENABLE_CONTROL, frame_idx

    hwnd = find_mumu_window()
    model = YOLO(MODEL_PATH)
    names = model.names

    sct = mss.mss()
    last_t = time.time()

    while True:
        frame_idx += 1
        frame = capture_window(hwnd, sct)

        roi, _ = crop_roi(frame)
        rh, rw = roi.shape[:2]

        results = model.predict(
            source=roi,
            conf=CONF_THRES,
            imgsz=IMGSZ,
            device=DEVICE_ID,
            verbose=False
        )

        detections = parse_detections(results, names, roi.shape)

        raw_action, scores, lane_objs, debug = decide_action(
            detections, rw, rh, current_lane
        )
        print(f"[DEBUG] raw action={raw_action}, control={ENABLE_CONTROL}")

        stable_action = stabilize_action(raw_action, debug.get("raw_target_key"))
        print(f"[DEBUG] stable action={stable_action}")

        if ENABLE_CONTROL:
            executed = do_action(stable_action)
            print(f"[DEBUG] executed={executed}")
            if executed and stable_action != "none":
                register_executed_target(debug.get("raw_target_key"))
        else:
            print("[DEBUG] control disabled")

        now = time.time()
        fps = 1.0 / max(now - last_t, 1e-6)
        last_t = now

        roi_vis = draw_debug_roi(
            roi=roi,
            detections=detections,
            raw_action=raw_action,
            stable_action=stable_action,
            fps=fps,
            scores=scores,
            debug=debug
        )
        cv2.imshow("roi_detect", roi_vis)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("c"):
            ENABLE_CONTROL = not ENABLE_CONTROL
            print("ENABLE_CONTROL =", ENABLE_CONTROL)

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()