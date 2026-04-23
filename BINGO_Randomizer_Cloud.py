import streamlit as st
import random, time, csv, io, os
from datetime import datetime
from dataclasses import dataclass, field

# =========================
# Cloud / 管理者設定
# =========================
ADMIN_PIN = os.environ.get("ADMIN_PIN", "8240")   # Secrets推奨
AUTO_BACKUP_INTERVAL = 5                          # 抽選◯回ごと

# =========================
# 共有状態（複数司会）
# =========================
@st.cache_resource
def get_state():
    @dataclass
    class State:
        numbers: list = field(default_factory=lambda: random.sample(range(1, 76), 75))
        drawn: list = field(default_factory=list)
        last: int | None = None
        lock: bool = False
        flash: bool = False
        draw_count: int = 0
        backup_csv: str | None = None
    return State()

state = get_state()

# =========================
# モード判定（観客/司会）
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
# タイトル
# =========================
st.markdown(
    "<h1 style='text-align:center;font-size:56px;'>🎉 BINGO大会 🎉</h1>",
    unsafe_allow_html=True
)

# =========================
# 特大数字表示
# =========================
bg = "#ff3333" if state.flash else "#000000"
st.markdown(f"""
<div style="
  font-size:160px;
  text-align:center;
  color:white;
  background:{bg};
  padding:40px;
  border-radius:30px;
  margin-bottom:20px;">
  {state.last if state.last else "START"}
</div>
""", unsafe_allow_html=True)

# =========================
# 抽選・操作（司会のみ）
# =========================
if not VIEW_ONLY:
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🎲 抽 選", use_container_width=True, disabled=state.lock):
            if state.numbers:
                state.lock = True

                st.audio("DrumRoll.mp3", autoplay=True)
                time.sleep(2)

                num = state.numbers.pop()
                state.drawn.append(num)
                state.last = num
                state.draw_count += 1

                st.audio("DrumRoll_Finish.mp3", autoplay=True)

                # BINGO演出
                if len(state.drawn) >= 5:
                    state.flash = True
                    st.audio("bingo.mp3", autoplay=True)
                    time.sleep(1.2)
                    state.flash = False

                # 自動バックアップ（CSV生成）
                if state.draw_count % AUTO_BACKUP_INTERVAL == 0:
                    buf = io.StringIO()
                    w = csv.writer(buf)
                    w.writerow(["順番", "数字"])
                    for i, n in enumerate(state.drawn, 1):
                        w.writerow([i, n])
                    state.backup_csv = buf.getvalue()

                state.lock = False

    with col2:
        with st.expander("🔄 リセット（管理者）"):
            if st.button("✅ リセット実行"):
                state.numbers = random.sample(range(1, 76), 75)
                state.drawn.clear()
                state.last = None
                state.draw_count = 0
                state.backup_csv = None
                st.success("リセットしました")

# =========================
# CSVダウンロード（正式記録）
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

# =========================
# 自動バックアップCSV（DL）
# =========================
if state.backup_csv:
    st.download_button(
        "🛟 自動バックアップCSVを保存",
        state.backup_csv,
        file_name=f"backup_bingo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )

# =========================
# CSV復元（管理者PIN必須）
# =========================
if not VIEW_ONLY:
    st.divider()
    st.markdown("## 🔐 CSVから復元（管理者専用）")

    pin = st.text_input("管理者PIN", type="password")
    up = st.file_uploader("保存済みCSVを選択", type=["csv"])

    if st.button("復元実行"):
        if pin != ADMIN_PIN:
            st.error("管理者PINが違います")
        elif not up:
            st.error("CSVを選択してください")
        else:
            reader = csv.reader(io.StringIO(up.getvalue().decode("utf-8")))
            rows = list(reader)
            if rows[0] != ["順番", "数字"]:
                st.error("形式が正しくありません")
            else:
                nums = [int(r[1]) for r in rows[1:]]
                state.drawn = nums[:]
                state.last = nums[-1] if nums else None
                state.numbers = list(set(range(1, 76)) - set(nums))
                random.shuffle(state.numbers)
                st.success("✅ 抽選状態を復元しました")

# =========================
# B I N G O 表（全員）
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
