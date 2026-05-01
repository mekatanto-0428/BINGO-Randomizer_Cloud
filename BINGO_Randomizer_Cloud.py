import streamlit as st
import time, random, csv, io
from dataclasses import dataclass, field
from datetime import datetime

# ======================
# 設定値
# ======================
ROLLING_SECONDS = 5       # 抽選演出時間
REVEAL_WAIT = 1.5         # MP3後のタメ時間
AUTO_BACKUP_INTERVAL = 5  # 自動バックアップ間隔

# ======================
# 共有状態（複数端末対応）
# ======================
@st.cache_resource
def get_state():
    @dataclass
    class State:
        numbers: list = field(default_factory=lambda: random.sample(range(1, 76), 75))
        drawn: list = field(default_factory=list)
        last: int | None = None

        phase: str = "idle"   # idle / rolling / revealing
        phase_started_at: float | None = None
        reveal_started_at: float | None = None

        sound_to_play: str | None = None

        draw_count: int = 0
        backup_csv: str | None = None
        confirm_reset: bool = False

    return State()

state = get_state()

# 観客モード判定
VIEW_ONLY = st.query_params.get("view") == "viewer"

# ======================
# ページ設定
# ======================
st.set_page_config(layout="wide", page_title="BINGO大会")

# 起動時フルスクリーン（司会のみ）
if not VIEW_ONLY:
    st.markdown("""
    <script>
    setTimeout(()=>{
      if(!document.fullscreenElement){
        document.documentElement.requestFullscreen().catch(()=>{});
      }
    },700);
    </script>
    """, unsafe_allow_html=True)

# ======================
# 効果音 ON/OFF
# ======================
sound_on = False
if not VIEW_ONLY:
    sound_on = st.toggle("🔊 効果音ON", value=True)

audio_box = st.empty()

def play_audio_if_needed():
    if VIEW_ONLY or not sound_on:
        return
    if state.sound_to_play:
        with open(state.sound_to_play, "rb") as f:
            audio_box.audio(f.read(), format="audio/mp3", autoplay=True)
        state.sound_to_play = None

# 再生チェック（描画ごとに必ず最初）
play_audio_if_needed()

# ======================
# LED CSS
# ======================
st.markdown("""
<style>
.led-box {
  font-size: 160px;
  text-align: center;
  font-weight: bold;
  padding: 40px;
  border-radius: 30px;
  margin-bottom: 20px;
}
.led-idle {
  background: black;
  color: white;
}
.led-rolling {
  background: black;
  color: #00ffcc;
  animation: blink 0.7s infinite, glow 1.5s infinite alternate;
}
@keyframes blink {
  0% { opacity: 1; }
  50% { opacity: 0.4; }
  100% { opacity: 1; }
}
@keyframes glow {
  from { box-shadow: 0 0 10px #00ffcc; }
  to { box-shadow: 0 0 40px #00ffcc; }
}
</style>
""", unsafe_allow_html=True)

# ======================
# タイトル
# ======================
st.markdown("<h1 style='text-align:center;'>🎉 BINGO大会 🎉</h1>", unsafe_allow_html=True)

# 表示プレースホルダ
number_box = st.empty()
status_box = st.empty()

# ======================
# フェーズ制御
# ======================

# ===== idle =====
if state.phase == "idle":
    status_box.info("待機中")

    if not VIEW_ONLY:
        col1, col2 = st.columns(2)

        with col1:
            if st.button("🎲 抽 選", use_container_width=True):
                state.phase = "rolling"
                state.phase_started_at = time.monotonic()
                state.sound_to_play = "drumroll.mp3"
                st.rerun()

        with col2:
            if st.button("🔄 リセット", use_container_width=True):
                state.confirm_reset = True

# ===== rolling =====
elif state.phase == "rolling":
    elapsed = time.monotonic() - state.phase_started_at
    remain = int(ROLLING_SECONDS - elapsed)

    if elapsed < ROLLING_SECONDS:
        status_box.info(f"抽選中… {remain} 秒")
        time.sleep(0.3)
        st.rerun()
    else:
        state.phase = "revealing"
        state.reveal_started_at = time.monotonic()
        state.sound_to_play = "draw.mp3"
        st.rerun()

# ===== revealing =====
elif state.phase == "revealing":
    status_box.success("結果発表！")
    elapsed = time.monotonic() - state.reveal_started_at

    if elapsed < REVEAL_WAIT:
        st.stop()  # 音を最後まで鳴らす
    else:
        if state.numbers:
            num = state.numbers.pop()
            state.last = num
            state.drawn.append(num)
            state.draw_count += 1

            if len(state.drawn) >= 5:
                state.sound_to_play = "bingo.mp3"

            if state.draw_count % AUTO_BACKUP_INTERVAL == 0:
                buf = io.StringIO()
                w = csv.writer(buf)
                w.writerow(["順番", "数字"])
                for i, n in enumerate(state.drawn, 1):
                    w.writerow([i, n])
                state.backup_csv = buf.getvalue()

        state.phase = "idle"
        state.phase_started_at = None
        state.reveal_started_at = None
        st.rerun()

# ======================
# リセット確認
# ======================
if state.confirm_reset and not VIEW_ONLY:
    st.warning("⚠️ 本当にリセットしますか？")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("✅ はい（リセット）", use_container_width=True):
            state.numbers = random.sample(range(1, 76), 75)
            state.drawn.clear()
            state.last = None
            state.phase = "idle"
            state.draw_count = 0
            state.backup_csv = None
            state.confirm_reset = False
            st.success("リセットしました")

    with c2:
        if st.button("❌ いいえ", use_container_width=True):
            state.confirm_reset = False

# ======================
# 数字表示（必ず最後）
# ======================
led_class = "led-rolling" if state.phase in ("rolling", "revealing") else "led-idle"
number_box.markdown(
    f"<div class='led-box {led_class}'>{state.last if state.last else 'START'}</div>",
    unsafe_allow_html=True
)

# ======================
# CSVダウンロード
# ======================
if state.drawn:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["順番", "数字"])
    for i, n in enumerate(state.drawn, 1):
        w.writerow([i, n])

    st.download_button(
        "📥 抽選結果CSVダウンロード",
        buf.getvalue(),
        file_name=f"bingo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )

# =========================
# B I N G O 列表示
# =========================
st.divider()
st.markdown("<h2 style='text-align:center;'>出た数字</h2>", unsafe_allow_html=True)

cols = st.columns(5)
labels = {
    "B": range(1,16),
    "I": range(16,31),
    "N": range(31,46),
    "G": range(46,61),
    "O": range(61,76),
}

for col, (lab, rng) in zip(cols, labels.items()):
    with col:
        st.markdown(f"<h3 style='text-align:center'>{lab}</h3>", unsafe_allow_html=True)
        for n in rng:
            if n in state.drawn:
                st.markdown(
                    f"<div style='background:#2ecc71;color:white;"
                    f"text-align:center;font-size:26px;margin:5px;border-radius:8px;'>{n}</div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"<div style='text-align:center;font-size:22px;margin:5px;color:#aaa;'>{n}</div>",
                    unsafe_allow_html=True
                )
