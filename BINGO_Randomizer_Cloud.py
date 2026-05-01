import streamlit as st
import random, csv, io, os, time
from dataclasses import dataclass, field
from datetime import datetime

# ======================
# 設定
# ======================
ADMIN_PIN = os.environ.get("ADMIN_PIN", "0000")
ROLLING_SECONDS = 5
AUTO_BACKUP_INTERVAL = 5

# ======================
# 共有状態（複数司会対応）
# ======================
@st.cache_resource
def get_state():
    @dataclass
    class State:
        numbers: list = field(default_factory=lambda: random.sample(range(1, 76), 75))
        drawn: list = field(default_factory=list)
        last: int | None = None

        # フェーズ制御
        phase: str = "idle"                 # idle / rolling
        phase_started_at: float | None = None

        # 音声管理（★ここが重要）
        sound_to_play: str | None = None

        # その他
        draw_count: int = 0
        backup_csv: str | None = None
        confirm_reset: bool = False

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
# 効果音設定（司会のみ）
# ======================
sound_on = False
volume = 1.0

if not VIEW_ONLY:
    with st.expander("🔊 効果音設定", expanded=False):
        sound_on = st.toggle("効果音ON", value=True)
        volume = st.slider("音量", 0.0, 1.0, 0.8, 0.1)

# ======================
# 音声再生（描画フェーズ専用）
# ======================
def play_audio_if_needed():
    """状態に応じて一度だけ音を再生する"""
    if VIEW_ONLY or not sound_on:
        return

    if state.sound_to_play:
        try:
            with open(state.sound_to_play, "rb") as f:
                st.audio(
                    f.read(),
                    format="audio/mp3",
                    autoplay=True,
                    start_time=0
                )
        except Exception as e:
            st.warning(f"音声再生エラー: {state.sound_to_play}")
            st.exception(e)

        # ★ 重要：1回再生したら必ずクリア
        state.sound_to_play = None


# ===== 描画開始時に必ず呼ぶ =====
play_audio_if_needed()

# ======================
# LED風CSS
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
# 特大数字（LED）
# ======================
led_class = "led-rolling" if state.phase == "rolling" else "led-idle"
display_text = state.last if state.last else "START"

st.markdown(
    f"<div class='led-box {led_class}'>{display_text}</div>",
    unsafe_allow_html=True
)

# ======================
# フェーズ① 抽選開始
# ======================
if not VIEW_ONLY and state.phase == "idle":
    if st.button("🎲 抽 選", use_container_width=True):
        state.phase = "rolling"
        state.phase_started_at = time.monotonic()

        # ★ ドラムロール音を予約
        state.sound_to_play = "DrumRoll.mp3"

        st.rerun()

# ======================
# フェーズ② 5秒後に数字確定
# ======================
if state.phase == "rolling":
    elapsed = time.monotonic() - state.phase_started_at

    if elapsed < ROLLING_SECONDS:
        st.info(f"抽選中…")
        
        # ★ 0.2秒後に再評価させる
        time.sleep(0.2)
        st.rerun()

    else:
        if state.numbers:
            num = state.numbers.pop()
            state.drawn.append(num)
            state.last = num
            state.draw_count += 1

            # ★ 確定音を予約
            state.sound_to_play = "DrumRoll_Finish.mp3"

            # ★ BINGO演出（例：5個以上）
            #if len(state.drawn) >= 5:
            #    state.sound_to_play = "bingo.mp3"

            # 自動バックアップ
            if state.draw_count % AUTO_BACKUP_INTERVAL == 5:
                buf = io.StringIO()
                w = csv.writer(buf)
                w.writerow(["順番", "数字"])
                for i, n in enumerate(state.drawn, 1):
                    w.writerow([i, n])
                state.backup_csv = buf.getvalue()

        state.phase = "idle"
        state.phase_started_at = None
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
