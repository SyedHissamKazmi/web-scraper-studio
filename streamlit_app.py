from __future__ import annotations

import traceback
from datetime import datetime
from urllib.parse import urlparse

import pandas as pd
import streamlit as st

from app.analyzer import (
    build_dataframe,
    clean_dataframe,
    extract_emails,
    extract_phones,
    to_excel_bytes,
    word_frequency,
)
from app.scraper import scrape

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="Web Scraper Studio",
    page_icon="🕸️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# THEME
# ============================================================================
CSS = """
<style>
    .stApp {
        background: radial-gradient(circle at 15% 15%, rgba(124,108,255,0.10), transparent 55%),
                    radial-gradient(circle at 85% 85%, rgba(6,182,212,0.10), transparent 55%),
                    linear-gradient(135deg, #080b12 0%, #0f1419 50%, #0a0d14 100%);
        color: #f5f7fb;
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }
    h1, h2, h3 { font-family: 'Share Tech Mono', monospace; letter-spacing: 1px; }
    .stButton > button {
        background: linear-gradient(90deg, #7c6cff, #06b6d4);
        color: white; border: none; border-radius: 12px;
        padding: 0.6rem 1.5rem; font-weight: 700;
        box-shadow: 0 4px 18px rgba(124,108,255,0.35);
        transition: all 0.25s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 28px rgba(124,108,255,0.55);
    }
    .stMetric {
        background: rgba(18,24,36,0.85);
        border: 1px solid rgba(157,147,255,0.2);
        border-radius: 16px; padding: 16px;
    }
    .stDataFrame {
        border-radius: 12px; overflow: hidden;
        border: 1px solid rgba(157,147,255,0.15);
    }
    .badge-ok { background: rgba(34,197,94,0.15); color: #22c55e;
                padding: 6px 14px; border-radius: 30px; font-weight: 700; }
    .badge-warn { background: rgba(245,158,11,0.15); color: #f59e0b;
                  padding: 6px 14px; border-radius: 30px; font-weight: 700; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ============================================================================
# SESSION STATE
# ============================================================================
if "history" not in st.session_state:
    st.session_state.history = []
if "current_result" not in st.session_state:
    st.session_state.current_result = None
if "current_df" not in st.session_state:
    st.session_state.current_df = None

# ============================================================================
# SIDEBAR
# ============================================================================
with st.sidebar:
    st.title("🕸️ Web Scraper Studio")
    st.caption("Extract structured data from any public web page.")

    st.markdown("### ⚙️ Options")
    timeout = st.slider("Request timeout (seconds)", 5, 30, 15)
    clean_enabled = st.checkbox("Clean & deduplicate results", value=True)
    respect_robots = st.checkbox("Respect robots.txt", value=True)

    st.markdown("### 🎭 User-Agent")
    use_custom_ua = st.checkbox("Use custom User-Agent", value=False)
    custom_ua = st.text_input(
        "Custom User-Agent",
        value="",
        disabled=not use_custom_ua,
    )

    st.markdown("---")
    st.markdown("### 👤 Author")
    st.write("Syed Hissam Kazmi")
    st.markdown("[GitHub](https://github.com/SyedHissamKazmi)")

    st.markdown("---")
    st.caption(f"History: {len(st.session_state.history)} scans")

# ============================================================================
# HERO
# ============================================================================
st.markdown(
    """
    <div style="text-align:center; padding:30px 10px 10px;">
        <h1 style="margin-bottom:0;">Web Scraper Studio</h1>
        <p style="color:#a6afc0; margin-top:6px;">
            Extract headings, links, contacts, and SEO data from any public web page.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown("---")

# ============================================================================
# INPUT
# ============================================================================
mode = st.radio(
    "Input mode",
    ["Single URL", "Batch URLs (one per line)"],
    horizontal=True,
)

urls: list[str] = []
if mode == "Single URL":
    single = st.text_input(
        "Target URL",
        placeholder="e.g. https://en.wikipedia.org/wiki/Artificial_intelligence",
        label_visibility="collapsed",
    )
    if single.strip():
        urls = [single.strip()]
else:
    batch = st.text_area(
        "One URL per line",
        placeholder="https://example.com\nhttps://another.com",
        height=130,
    )
    urls = [u.strip() for u in batch.splitlines() if u.strip()]

col_a, col_b = st.columns([1, 4])
with col_a:
    run = st.button("🚀 Scrape", use_container_width=True)

if run:
    if not urls:
        st.warning("Please enter at least one URL.")
        st.stop()

    results = []
    df_list = []
    progress = st.progress(0.0, text="Starting…")

    for i, u in enumerate(urls):
        try:
            result = scrape(
                u,
                timeout=(5, timeout),
                user_agent=custom_ua if use_custom_ua and custom_ua else None,
                respect_robots=respect_robots,
            )

            if result.error:
                st.warning(f"❌ {u}: {result.error}")
                continue

            if not result.headings and not result.links:
                st.info(f"⚠️ {u}: no extractable content.")
                continue

            df = build_dataframe(result.headings, result.links)
            if clean_enabled:
                df, _ = clean_dataframe(df)

            results.append(result)
            df_list.append(df)

            st.session_state.history.append({
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "url": result.url,
                "headings": len(result.headings),
                "links": len(result.links),
                "robots": "✅" if result.robots_allowed else "⚠️",
            })
        except Exception as exc:
            st.error(f"❌ {u}: {exc}")
            with st.expander("Show details"):
                st.code(traceback.format_exc())

        progress.progress((i + 1) / len(urls), text=f"{i+1}/{len(urls)} done")

    progress.empty()

    if results:
        st.session_state.current_result = results[0]
        st.session_state.current_df = df_list[0]
        st.success(f"Scraped {len(results)} page(s).")

# ============================================================================
# RESULTS
# ============================================================================
result = st.session_state.current_result
df = st.session_state.current_df

if result is None or df is None:
    st.info("Enter a URL above and click **Scrape** to begin.")
    st.stop()

# Robots badge
if result.robots_allowed:
    st.markdown('<span class="badge-ok">✅ robots.txt allows scraping</span>', unsafe_allow_html=True)
else:
    st.markdown('<span class="badge-warn">⚠️ robots.txt disallows scraping</span>', unsafe_allow_html=True)

st.markdown("### 📊 Summary")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Headings", len(result.headings))
c2.metric("Unique Links", len(result.links))
c3.metric("Rows After Cleaning", len(df))
c4.metric(
    "Unique Hosts",
    df["Extracted Network Host"].nunique() if "Extracted Network Host" in df.columns else 0,
)

# SEO preview
if result.title or result.meta_description or result.og_title:
    with st.expander("🔎 SEO & Open Graph Preview", expanded=True):
        if result.title:
            st.markdown(f"**Page Title:** {result.title}")
        if result.meta_description:
            st.markdown(f"**Meta Description:** {result.meta_description}")
        if result.og_title:
            st.markdown(f"**OG Title:** {result.og_title}")
        if result.og_type:
            st.markdown(f"**OG Type:** {result.og_type}")
        if result.og_image:
            st.markdown(f"**OG Image:** {result.og_image}")

# Tabs
tab_table, tab_head, tab_links, tab_keys, tab_domains, tab_contacts, tab_history = st.tabs(
    ["📋 Table", "🎯 Headings", "🔗 Links", "🔑 Keywords", "🌐 Domains", "📧 Contacts", "📜 History"]
)

with tab_table:
    filter_text = st.text_input("Filter results", placeholder="type to filter…")
    filtered = df
    if filter_text:
        mask = df.apply(
            lambda r: filter_text.lower() in r.astype(str).str.lower().to_string().lower(),
            axis=1,
        )
        filtered = df[mask]
    st.dataframe(filtered, use_container_width=True, height=400)

with tab_head:
    if result.headings:
        for h in result.headings:
            st.code(h, language=None)
    else:
        st.info("No headings found.")

with tab_links:
    if result.links:
        for l in result.links:
            st.code(l, language=None)
    else:
        st.info("No links found.")

with tab_keys:
    if result.content:
        top = word_frequency(result.content, top_n=20)
        if top:
            kdf = pd.DataFrame(top, columns=["Keyword", "Count"]).set_index("Keyword")
            st.bar_chart(kdf)
            st.dataframe(kdf, use_container_width=True)
        else:
            st.info("No keywords found.")
    else:
        st.info("No content available for keyword analysis.")

with tab_domains:
    if "Extracted Network Host" in df.columns:
        counts = df["Extracted Network Host"].value_counts().head(20)
        st.bar_chart(counts)
    else:
        st.info("No domain data available.")

with tab_contacts:
    if result.content:
        emails = extract_emails(result.content)
        phones = extract_phones(result.content)

        st.markdown("**📧 Emails**")
        if emails:
            for e in emails:
                st.code(e, language=None)
        else:
            st.write("_None found._")

        st.markdown("**📞 Phone Numbers**")
        if phones:
            for p in phones:
                st.code(p, language=None)
        else:
            st.write("_None found._")
    else:
        st.info("No content available for contact extraction.")

with tab_history:
    if st.session_state.history:
        hdf = pd.DataFrame(st.session_state.history)
        st.dataframe(hdf, use_container_width=True)
        if st.button("Clear History"):
            st.session_state.history = []
            st.rerun()
    else:
        st.info("No scans yet.")

# ============================================================================
# DOWNLOAD
# ============================================================================
st.markdown("### 📥 Download")

domain = urlparse(result.url).netloc.replace("www.", "").replace(".", "_")
base = f"scraped_{domain}_{datetime.now():%Y%m%d_%H%M%S}"

col_x, col_c, col_j = st.columns(3)
with col_x:
    st.download_button(
        "📊 Excel (.xlsx)",
        data=to_excel_bytes(df),
        file_name=f"{base}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
with col_c:
    st.download_button(
        "📄 CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=f"{base}.csv",
        mime="text/csv",
        use_container_width=True,
    )
with col_j:
    st.download_button(
        "🧾 JSON",
        data=df.to_json(orient="records", indent=2).encode("utf-8"),
        file_name=f"{base}.json",
        mime="application/json",
        use_container_width=True,
    )

st.caption(f"Scraped at {datetime.now():%Y-%m-%d %H:%M:%S}")