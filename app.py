
from dataclasses import dataclass
import math
import streamlit as st
import pandas as pd

st.set_page_config(page_title="메이플키우기 계산기/Hyedan", page_icon="📈", layout="wide")

# ---------- Core model ----------
@dataclass
class Settings:
    balance_ratio: float = 90.0      # 데미지 : 주스텟
    target_spread: float = 20.0      # 최대-최소 목표 편차
    # 효율 계산 증분(“+이만큼 올리면 딜이 몇% 오르나”)
    d_crit_chance: float = 1.0
    d_crit_dmg: float = 1.0
    d_damage: float = 1.0
    d_main_stat: float = 1000.0
    d_min_mult: float = 1.0
    d_max_mult: float = 1.0
    d_final_dmg: float = 1.0

@dataclass
class UpgradeSteps:
    # “실제로” 한 번 강화/교체로 오르는 평균값을 넣는 칸
    per_damage: float = 0.0      # 데미지 +%p / 1회
    per_main_stat: float = 0.0   # 주스텟 +수치 / 1회
    per_min_mult: float = 0.0    # 최소배율 +%p / 1회

@dataclass
class Stats:
    crit_chance: float      # 크확(%)
    crit_dmg: float         # 크뎀(%)
    damage: float           # 데미지(%)
    main_stat: float        # 주스텟(수치)
    min_mult: float         # 최소배율(%)
    max_mult: float         # 최대배율(%)
    final_dmg: float        # 최종데미지(%)
    ancient_on: bool
    ancient_awaken: int

ANCIENT_COEF = {0:0.30, 1:0.36, 2:0.42, 3:0.48, 4:0.54, 5:0.60}

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def ancient_coef(on: bool, awaken: int) -> float:
    if not on:
        return 0.0
    awaken = int(clamp(awaken, 0, 5))
    return ANCIENT_COEF[awaken]

def effective_crit_dmg(s: Stats) -> float:
    # 적용 크뎀 = 기본 크뎀 + (크확 × 계수)
    coef = ancient_coef(s.ancient_on, s.ancient_awaken)
    return s.crit_dmg + s.crit_chance * coef

def crit_expected_multiplier(s: Stats) -> float:
    cc = clamp(s.crit_chance, 0.0, 100.0) / 100.0
    cd = effective_crit_dmg(s) / 100.0
    return (1.0 - cc) + cc * (1.0 + cd)

def damage_multiplier(s: Stats) -> float:
    return 1.0 + s.damage / 100.0

def final_multiplier(s: Stats) -> float:
    return 1.0 + s.final_dmg / 100.0

def avg_minmax_multiplier(s: Stats) -> float:
    return ((s.min_mult + s.max_mult) / 2.0) / 100.0

def dps_index(s: Stats) -> float:
    return s.main_stat * crit_expected_multiplier(s) * damage_multiplier(s) * final_multiplier(s) * avg_minmax_multiplier(s)

def pct_gain(base: float, new: float) -> float:
    return (new / base - 1.0) * 100.0

def efficiencies(s: Stats, stt: Settings):
    base = dps_index(s)
    out = {}

    out["크확"] = pct_gain(base, dps_index(Stats(**{**s.__dict__, "crit_chance": s.crit_chance + stt.d_crit_chance})))
    out["크뎀"] = pct_gain(base, dps_index(Stats(**{**s.__dict__, "crit_dmg": s.crit_dmg + stt.d_crit_dmg})))
    out["데미지"] = pct_gain(base, dps_index(Stats(**{**s.__dict__, "damage": s.damage + stt.d_damage})))
    out["주스텟"] = pct_gain(base, dps_index(Stats(**{**s.__dict__, "main_stat": s.main_stat + stt.d_main_stat})))
    out["최소배율"] = pct_gain(base, dps_index(Stats(**{**s.__dict__, "min_mult": s.min_mult + stt.d_min_mult})))
    out["최대배율"] = pct_gain(base, dps_index(Stats(**{**s.__dict__, "max_mult": s.max_mult + stt.d_max_mult})))
    out["최종데미지"] = pct_gain(base, dps_index(Stats(**{**s.__dict__, "final_dmg": s.final_dmg + stt.d_final_dmg})))

    return out

def balance_and_goals(s: Stats, stt: Settings):
    # 목표 주스텟/데미지
    target_stat = s.damage * stt.balance_ratio
    stat_diff = target_stat - s.main_stat  # + 부족, - 과다

    target_damage = s.main_stat / stt.balance_ratio
    damage_diff = target_damage - s.damage  # + 부족, - 과다

    spread = s.max_mult - s.min_mult
    target_min = s.max_mult - stt.target_spread
    min_need = target_min - s.min_mult  # + 필요

    return {
        "목표주스텟": target_stat,
        "주스텟차이": stat_diff,
        "목표데미지": target_damage,
        "데미지차이": damage_diff,
        "현재편차": spread,
        "목표최소": target_min,
        "최소필요": min_need,
    }

def counts_needed(diff: float, per_step: float):
    """diff>0이면 부족. per_step은 1회당 상승량."""
    if diff <= 0:
        return 0
    if per_step <= 0:
        return None  # 계산 불가(입력 필요)
    return int(math.ceil(diff / per_step))

def recommendation(s: Stats, stt: Settings):
    g = balance_and_goals(s, stt)
    if s.crit_chance < 100:
        return "크확 100% 먼저"
    if g["최소필요"] > 0:
        return f"최소배율 +{g['최소필요']:.1f}%p (편차 {stt.target_spread:g} 목표)"
    if g["데미지차이"] > 0:
        return f"데미지 +{g['데미지차이']:.1f}%p (주스텟 대비 부족)"
    if g["주스텟차이"] > 0:
        return f"주스텟 +{g['주스텟차이']:.0f} (데미지 대비 부족)"
    return "미세최적화(크뎀/최종뎀/최소) 단계"

# ---------- UI ----------
st.markdown("""
<style>
/* 모바일에서도 보기 좋게 */
.block-container {padding-top: 1.2rem; padding-bottom: 2.5rem;}
div[data-testid="stMetricValue"] {font-size: 1.6rem;}
div[data-testid="stMetricLabel"] {font-size: 0.9rem;}
</style>
""", unsafe_allow_html=True)

st.title("📈 메이플키우기 계산기")
st.caption("Hyedan 69섭 테토클럽 전용")

# Sidebar inputs
with st.sidebar:
    st.header("스탯 입력")

    crit_chance = st.number_input("크확(%)", min_value=0.0, max_value=200.0, value=100.0, step=1.0)
    crit_dmg = st.number_input("크뎀(%)", min_value=0.0, max_value=9999.0, value=150.0, step=1.0)

    c1, c2 = st.columns(2)
    with c1:
        damage = st.number_input("데미지(%)", min_value=0.0, max_value=9999.0, value=545.0, step=1.0)
        min_mult = st.number_input("최소배율(%)", min_value=0.0, max_value=9999.0, value=155.6, step=0.1)
    with c2:
        main_stat = st.number_input("주스텟", min_value=0.0, max_value=10_000_000.0, value=46406.0, step=100.0)
        max_mult = st.number_input("최대배율(%)", min_value=0.0, max_value=9999.0, value=185.0, step=0.1)

    final_dmg = st.number_input("최종데미지(%)", min_value=0.0, max_value=9999.0, value=0.0, step=0.1)

    st.divider()
    st.subheader("고대책")
    ancient_on = st.toggle("고대책 적용", value=True)
    ancient_awaken = st.slider("각성(0~5)", min_value=0, max_value=5, value=0, disabled=not ancient_on)

    st.divider()
    st.subheader("목표 설정")
    balance_ratio = st.number_input("균형비율(데미지:주스텟)", min_value=1.0, max_value=300.0, value=90.0, step=1.0)
    target_spread = st.number_input("목표 편차(최대-최소)", min_value=0.0, max_value=200.0, value=20.0, step=1.0)

    st.divider()
    st.subheader("필요횟수 계산(선택)")
    st.caption("‘1회당 평균 상승량’을 입력하면 목표 달성까지 필요한 횟수를 계산해줘요.")
    per_damage = st.number_input("데미지 +%p / 1회", min_value=0.0, max_value=500.0, value=0.0, step=0.5)
    per_main_stat = st.number_input("주스텟 + / 1회", min_value=0.0, max_value=1_000_000.0, value=0.0, step=100.0)
    per_min = st.number_input("최소배율 +%p / 1회", min_value=0.0, max_value=500.0, value=0.0, step=0.5)

    with st.expander("효율 계산 증분(고급)"):
        d_cc = st.number_input("크확 증분(%p)", min_value=0.1, max_value=50.0, value=1.0, step=0.1)
        d_cd = st.number_input("크뎀 증분(%p)", min_value=0.1, max_value=200.0, value=1.0, step=0.1)
        d_dmg = st.number_input("데미지 증분(%p)", min_value=0.1, max_value=200.0, value=1.0, step=0.1)
        d_stat = st.number_input("주스텟 증분(+)", min_value=1.0, max_value=1_000_000.0, value=1000.0, step=100.0)
        d_min = st.number_input("최소배율 증분(%p)", min_value=0.1, max_value=200.0, value=1.0, step=0.1)
        d_max = st.number_input("최대배율 증분(%p)", min_value=0.1, max_value=200.0, value=1.0, step=0.1)
        d_final = st.number_input("최종뎀 증분(%p)", min_value=0.1, max_value=200.0, value=1.0, step=0.1)

settings = Settings(
    balance_ratio=float(balance_ratio),
    target_spread=float(target_spread),
    d_crit_chance=float(d_cc),
    d_crit_dmg=float(d_cd),
    d_damage=float(d_dmg),
    d_main_stat=float(d_stat),
    d_min_mult=float(d_min),
    d_max_mult=float(d_max),
    d_final_dmg=float(d_final),
)

steps = UpgradeSteps(
    per_damage=float(per_damage),
    per_main_stat=float(per_main_stat),
    per_min_mult=float(per_min),
)

stats = Stats(
    crit_chance=float(crit_chance),
    crit_dmg=float(crit_dmg),
    damage=float(damage),
    main_stat=float(main_stat),
    min_mult=float(min_mult),
    max_mult=float(max_mult),
    final_dmg=float(final_dmg),
    ancient_on=bool(ancient_on),
    ancient_awaken=int(ancient_awaken),
)

coef = ancient_coef(stats.ancient_on, stats.ancient_awaken)
applied_cd = effective_crit_dmg(stats)
base_index = dps_index(stats)
goals = balance_and_goals(stats, settings)
eff = efficiencies(stats, settings)

# Top metrics
m1, m2, m3, m4 = st.columns(4)
m1.metric("딜지수", f"{base_index:,.2f}")
m2.metric("고대책 계수", f"{coef:.2f}")
m3.metric("적용 크뎀(%)", f"{applied_cd:.1f}")
m4.metric("편차(최대-최소)", f"{(stats.max_mult-stats.min_mult):.1f}")

st.success("추천: " + recommendation(stats, settings))

# Tabs
tab1, tab2 = st.tabs(["균형/목표 & 필요횟수", "효율(증분 기준)"])

with tab1:
    left_col, right_col = st.columns([1.15, 0.85])

    with left_col:
        st.subheader("균형 진단 + 목표치")
        df = pd.DataFrame([
            ["목표 주스텟(=데미지×비율)", goals["목표주스텟"]],
            ["주스텟 차이(+부족 / -과다)", goals["주스텟차이"]],
            ["목표 데미지(=주스텟/비율)", goals["목표데미지"]],
            ["데미지 차이(+부족 / -과다)", goals["데미지차이"]],
            ["목표 최소(=최대-목표편차)", goals["목표최소"]],
            ["최소 필요(+필요 / -여유)", goals["최소필요"]],
        ], columns=["항목", "값"])
        st.dataframe(df, use_container_width=True, hide_index=True)

    with right_col:
        st.subheader("필요횟수(입력한 1회 상승량 기준)")
        dmg_cnt = counts_needed(goals["데미지차이"], steps.per_damage)
        stat_cnt = counts_needed(goals["주스텟차이"], steps.per_main_stat)
        min_cnt = counts_needed(goals["최소필요"], steps.per_min_mult)

        def fmt_cnt(x):
            if x is None:
                return "상승량 입력 필요"
            return f"{x}회"

        st.write("아래는 ‘부족(+)'일 때만 계산돼요. (과다/여유면 0회)")
        st.metric("데미지 목표까지", fmt_cnt(dmg_cnt))
        st.metric("주스텟 목표까지", fmt_cnt(stat_cnt))
        st.metric("최소배율 목표까지", fmt_cnt(min_cnt))

        st.caption("※ 예: 주스텟 +650/회라면 ‘주스텟 +/1회’에 650 입력")

with tab2:
    st.subheader("효율(증분 기준 딜 상승률 %)")
    edf = pd.DataFrame([{"항목": k, "효율(%)": v} for k, v in eff.items()]).sort_values("효율(%)", ascending=False)
    st.dataframe(edf, use_container_width=True, hide_index=True)

    top = edf.iloc[0]
    st.info(f"현재 증분 기준 1순위: **{top['항목']}** (약 {top['효율(%)']:.3f}%)")

with st.expander("계산 방식(요약)"):
    st.write("""
- 딜지수 = 주스텟 × 치명타기대배율 × (1+데미지%) × (1+최종뎀%) × 평균배율(최소/최대)
- 치명타기대배율 = (1-크확)×1 + (크확)×(1+적용크뎀)
- 고대책 적용 크뎀 = 기본 크뎀 + 크확×계수(0각~5각)
""")
