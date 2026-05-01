import streamlit as st
import time, random, csv, io, os
from dataclasses import dataclass, field
from datetime import datetime

# ======================
# 設定
# ======================
ROLLING_SECONDS = 7
REVEAL_WAIT = 2
AUTO_BACKUP_INTERVAL = 5

# ======================
# 共有状態（複数司会）
# ======================
@st.cache_resource
def get_state():
    @dataclass
    class State:
        numbers: list = field(default_factory=lambda: random.sample(range(1, 76), 75))
        drawn: list = field(default_factory=list)
        last: int | None = None

        phase: str = "idle"           # idle / rolling / revealing
        phase_started_at: float | None = None
        reveal_started_at: float | None = None

        sound_to_play: str | None = None

        draw_count: int = 0
        backup_csv: str | None = None

    return State()

state = get_state()

VIEW_ONLY = st.query_params.get("view") == "viewer"

# ======================
# UI設定
# ======================
st.set_page_config(layout="wide", page_title="BINGO大会")

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
# 効果音設定
# ======================
sound_on = False
if not VIEW_ONLY:
    sound_on = st.toggle("🔊 効果音ON", value=True)

# ======================
# 音声再生（描画時に1回だけ）
# ======================
audio_box = st.empty()

def play_audio_if_needed():
    if VIEW_ONLY or not sound_on:
        return
    if state.sound_to_play:
        with open(state.sound_to_play, "rb") as f:
            audio_box.audio(f.read(), format="audio/mp3", autoplay=True)
        state.sound_to_play = None

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

# ======================
# 表示プレースホルダ（重要）
# ======================
number_box = st.empty()
status_box = st.empty()

led_class = "led-rolling" if state.phase in ("rolling", "revealing") else "led-idle"
number_box.markdown(
    f"<div class='led-box {led_class}'>{state.last if state.last else 'START'}</div>",
    unsafe_allow_html=True
)

# ======================
# idle
# ======================
if state.phase == "idle":
    status_box.info("待機中")

    if not VIEW_ONLY:
        col1, col2 = st.columns(2)

    with col1:
        if not VIEW_ONLY and st.button("🎲 抽 選"):
            state.phase = "rolling"
            state.phase_started_at = time.monotonic()
            state.sound_to_play = "DrumRoll.mp3"
            st.rerun()

# ======================
# rolling
# ======================
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
        state.sound_to_play = "DrumRoll_Finish.mp3"
        st.rerun()

# ======================
# revealing（音 → タメ → 数字）
# ======================
elif state.phase == "revealing":
    elapsed = time.monotonic() - state.reveal_started_at
    status_box.success("結果発表！")

    if elapsed < REVEAL_WAIT:
        st.stop()   # 音を鳴らし切る
    else:
        if state.numbers:
            num = state.numbers.pop()
            state.last = num
            state.drawn.append(num)
            state.draw_count += 1

            #if len(state.drawn) >= 5:
            #    state.sound_to_play = "bingo.mp3"

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
