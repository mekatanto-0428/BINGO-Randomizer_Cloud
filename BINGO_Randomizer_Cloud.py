import streamlit as st
import random, csv, io, os
from datetime import datetime
from dataclasses import dataclass, field

# =========================
# 管理者設定
# =========================
ADMIN_PIN = os.environ.get("ADMIN_PIN", "0000")
AUTO_BACKUP_INTERVAL = 5

# =========================
# 共有状態（複数司会対応）
# =========================
@st.cache_resource
def get_state():
    @dataclass
    class State:
        numbers: list = field(default_factory=lambda: random.sample(range(1, 76), 75))
        drawn: list = field(default_factory=list)
        last: int | None = None
        phase: str = "idle"          # idle / rolling
        draw_count: int = 0
        backup_csv: str | None = None
        confirm_reset: bool = False
    return State()

state = get_state()

# =========================
# モード判定
# =========================
VIEW_ONLY = st.query_params.get("view") == "viewer"

# =========================
# UI設定
# =========================
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

# =========================
# 効果音ON/OFF（司会のみ）
# =========================
sound_on = False
if not VIEW_ONLY:
    sound_on = st.toggle("🔊 効果音ON", value=True)

def play_audio(filename):
    if VIEW_ONLY or not sound_on:
        return
    try:
        with open(filename, "rb") as f:
            st.audio(f.read(), format="audio/mp3", autoplay=True)
    except Exception as e:
        st.error(f"音声再生エラー: {filename}")
        st.exception(e)

# =========================
# タイトル
# =========================
st.markdown(
    "<h1 style='text-align:center;font-size:56px;'>🎉 BINGO大会 🎉</h1>",
    unsafe_allow_html=True
)

# =========================
# プロジェクター向け特大数字
# =========================
st.markdown(
    f"""
    <div style="
      font-size:160px;
      text-align:center;
      color:white;
      background:#000;
      padding:40px;
      border-radius:30px;
      margin-bottom:20px;">
      {state.last if state.last else "START"}
    </div>
    """,
    unsafe_allow_html=True
)

# =========================
# 操作ボタン
# =========================

# =====================
# フェーズ①：抽選開始
# =====================
if not VIEW_ONLY:
    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "🎲 抽 選",
            use_container_width=True,
            disabled=(state.phase != "idle")
        ):
            state.phase = "rolling"
            play_audio("DrumRoll.mp3")
            #st.rerun()

    with col2:
        if st.button("🔄 リセット", use_container_width=True):
            state.confirm_reset = True

# =====================
# フェーズ②：次の rerun で数字確定
# =====================
if state.phase == "rolling":
    if state.numbers:
        num = state.numbers.pop()
        state.drawn.append(num)
        state.last = num
        state.draw_count += 1

        play_audio("DrumRoll_Finish.mp3")

        # BINGO演出（例：5個以上で）
        #if len(state.drawn) >= 5:
        #    play_audio("bingo.mp3")

        # 自動バックアップ
        if state.draw_count % AUTO_BACKUP_INTERVAL == 0:
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(["順番", "数字"])
            for i, n in enumerate(state.drawn, 1):
                w.writerow([i, n])
            state.backup_csv = buf.getvalue()

    state.phase = "idle"
    #st.rerun()


# =========================
# リセット確認ダイアログ
# =========================
if state.confirm_reset and not VIEW_ONLY:
    st.warning("⚠️ 本当にリセットしますか？")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("✅ はい"):
            state.numbers = random.sample(range(1, 76), 75)
            state.drawn.clear()
            state.last = None
            state.draw_count = 0
            state.backup_csv = None
            state.confirm_reset = False
            st.success("リセットしました")
    with c2:
        if st.button("❌ いいえ"):
            state.confirm_reset = False

# =========================
# CSVダウンロード
# =========================
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

# 自動バックアップDL
if state.backup_csv:
    st.download_button(
        "🛟 自動バックアップCSVを保存",
        state.backup_csv,
        file_name=f"backup_bingo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )

# =========================
# CSV復元（管理者PIN）
# =========================
if not VIEW_ONLY:
    st.divider()
    st.markdown("## 🔐 CSVから復元（管理者専用）")

    pin = st.text_input("管理者PIN", type="password")
    up = st.file_uploader("保存済みCSV", type=["csv"])

    if st.button("復元実行"):
        if pin != ADMIN_PIN:
            st.error("管理者PINが違います")
        elif not up:
            st.error("CSVを選択してください")
        else:
            reader = csv.reader(io.StringIO(up.getvalue().decode("utf-8")))
            rows = list(reader)
            nums = [int(r[1]) for r in rows[1:]]
            state.drawn = nums[:]
            state.last = nums[-1] if nums else None
            state.numbers = list(set(range(1, 76)) - set(nums))
            random.shuffle(state.numbers)
            st.success("✅ 抽選状態を復元しました")

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
