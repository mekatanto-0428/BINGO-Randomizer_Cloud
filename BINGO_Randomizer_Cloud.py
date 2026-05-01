import streamlit as st
import random, csv, io, os, time
from dataclasses import dataclass, field
from datetime import datetime

# ======================
# 設定
# ======================
ROLLING_SECONDS = 5              # 抽選演出時間
REVEAL_SOUND_WAIT = 1.5          # MP3再生後のタメ時間
AUTO_BACKUP_INTERVAL = 5
ADMIN_PIN = os.environ.get("ADMIN_PIN", "0000")

# ======================
# 共有状態
# ======================
@st.cache_resource
def get_state():
    @dataclass
    class State:
        numbers: list = field(default_factory=lambda: random.sample(range(1, 76), 75))
        drawn: list = field(default_factory=list)
        last: int | None = None

        # フェーズ
        phase: str = "idle"              # idle / rolling / revealing
        phase_started_at: float | None = None
        reveal_started_at: float | None = None

        # 音声予約
        sound_to_play: str | None = None

        # その他
        draw_count: int = 0
        backup_csv: str | None = None

    return State()

state = get_state()

# ======================
# モード判定
# ======================
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
    with st.expander("🔊 効果音設定"):
        sound_on = st.toggle("効果音ON", value=True)

# ======================
# 音声再生（描画時）
# ======================
def play_audio_if_needed():
    if VIEW_ONLY or not sound_on:
        return
    if state.sound_to_play:
        try:
            with open(state.sound_to_play, "rb") as f:
                st.audio(f.read(), format="audio/mp3", autoplay=True)
        except Exception as e:
            st.warning(f"音声エラー: {state.sound_to_play}")
            st.exception(e)
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
# タイトル & 表示
# ======================
st.markdown("<h1 style='text-align:center;'>🎉 BINGO大会 🎉</h1>", unsafe_allow_html=True)

led_class = "led-rolling" if state.phase in ("rolling", "revealing") else "led-idle"
display_text = state.last if state.last else "START"

st.markdown(
    f"<div class='led-box {led_class}'>{display_text}</div>",
    unsafe_allow_html=True
)

# ======================
# フェーズ① idle → rolling
# ======================
if not VIEW_ONLY and state.phase == "idle":
    if st.button("🎲 抽 選", use_container_width=True):
        state.phase = "rolling"
        state.phase_started_at = time.monotonic()
        state.sound_to_play = "DrumRoll.mp3"
        st.rerun()

# ======================
# フェーズ② rolling（5秒演出）
# ======================
if state.phase == "rolling":
    elapsed = time.monotonic() - state.phase_started_at

    if elapsed < ROLLING_SECONDS:
        st.info(f"抽選中… {int(ROLLING_SECONDS - elapsed)} 秒")
        time.sleep(0.2)
        st.rerun()
    else:
        state.phase = "revealing"
        state.reveal_started_at = time.monotonic()
        state.sound_to_play = "DrumRoll_Finish.mp3"
        st.rerun()

# ======================
# フェーズ③ revealing（MP3後に数字表示）
# ======================
if state.phase == "revealing":
    elapsed = time.monotonic() - state.reveal_started_at

    if elapsed < REVEAL_SOUND_WAIT:
        st.info("結果発表…")
        time.sleep(0.1)
        st.rerun()
    else:
        if state.numbers:
            num = state.numbers.pop()
            state.drawn.append(num)
            state.last = num
            state.draw_count += 1

            #bingo演出
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
        file_name=f"bingo_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )
