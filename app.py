# MEMBER 5's Code (Danny)
# Human-in-the-loop review console. Web app, runs with:  streamlit run app.py
# Controls: language (EN / BM / 中文), appearance (auto / light / dark), text size.
# Makes no AI calls, so it costs no tokens.

import html
from pathlib import Path

import streamlit as st

from src import audit, escalation, store

st.set_page_config(page_title="Verification", page_icon="\u25c9",
                   layout="wide", initial_sidebar_state="collapsed")

# ------------------------------------------------------------------ language
T = {
"en": {"lang":"Language","appear":"Appearance","size":"Text size",
 "auto":"Auto","light":"Light","dark":"Dark","sm":"Standard","md":"Large","lg":"Larger",
 "inbox":"Inbox","review":"Review","failures":"Failures","report":"Report",
 "processed":"emails processed","hero":"discrepancies",
 "sub":"Found across the whole inbox. {n} more could not be decided and are waiting on a person.",
 "t_total":"emails processed","t_disc":"discrepancies found","t_wait":"waiting on a person","t_clear":"cleared",
 "f_all":"All","f_d":"Discrepancies","f_w":"Needs review","f_x":"Failed","f_g":"Cleared",
 "showing":"{a} of {b}","first":"Showing the first {n}.",
 "si":"Shipping instruction","bl":"Draft bill of lading",
 "tab_f":"Fields","tab_s":"Documents","tab_a":"Audit",
 "v_d":"{n} of 7 fields disagree","v_dt":"Correct the draft before it is finalised.",
 "v_g":"All seven fields agree.","v_gt":"No mismatch detected.",
 "v_w":"sent for review rather than guessed at.",
 "v_x":"Processing failed","v_xt":"The batch completed.",
 "v_p":"Not processed yet","v_pt":"Run the pipeline.",
 "v_cat":"no document check needed for this category.",
 "blank":"blank in document","handled":"Handled","notproc":"Not processed",
 "b_conf":"Confirm","b_clear":"Clear","b_rev":"Send to review","b_undo":"Undo",
 "hint":"Decisions go to the audit trail and into submission.json.",
 "setby":"Set by {who}","noaudit":"No audit entries yet.",
 "h_rev":"Review queue","l_rev":"Cases the system could not settle on its own. Each carries the evidence and the reason it stopped, so a person can decide in seconds.",
 "h_fail":"Processing failures","l_fail":"A single bad file never stops a run. Failures are recorded with the error and can be retried once the cause is fixed.",
 "h_rep":"Run report","clear_q":"Queue clear. Every case has been handled.",
 "no_fail":"No processing failures in this run.","decided":"decided by a person",
 "export":"Export","l_exp":"Writes outputs/submission.json with every review decision folded in. This is the file the scorer reads.",
 "b_exp":"Write submission.json","wrote":"Wrote {n} emails to outputs/submission.json",
 "nodata":"No emails found. Expected data_v2/inbox/ beside this file.",
 "nopipe":"outputs/results.json not found, so every email shows as pending. The console fills in as soon as the pipeline writes it."},
"ms": {"lang":"Bahasa","appear":"Penampilan","size":"Saiz teks",
 "auto":"Auto","light":"Cerah","dark":"Gelap","sm":"Biasa","md":"Besar","lg":"Lebih besar",
 "inbox":"Peti masuk","review":"Semakan","failures":"Kegagalan","report":"Laporan",
 "processed":"e-mel diproses","hero":"percanggahan",
 "sub":"Dijumpai dalam keseluruhan peti masuk. {n} lagi tidak dapat diputuskan dan menunggu orang.",
 "t_total":"e-mel diproses","t_disc":"percanggahan dijumpai","t_wait":"menunggu orang","t_clear":"selesai",
 "f_all":"Semua","f_d":"Percanggahan","f_w":"Perlu semakan","f_x":"Gagal","f_g":"Selesai",
 "showing":"{a} daripada {b}","first":"Menunjukkan {n} yang pertama.",
 "si":"Arahan penghantaran","bl":"Draf bil muatan",
 "tab_f":"Medan","tab_s":"Dokumen","tab_a":"Audit",
 "v_d":"{n} daripada 7 medan tidak sepadan","v_dt":"Betulkan draf sebelum dimuktamadkan.",
 "v_g":"Kesemua tujuh medan sepadan.","v_gt":"Tiada percanggahan dikesan.",
 "v_w":"dihantar untuk semakan, bukan diteka.",
 "v_x":"Pemprosesan gagal","v_xt":"Kelompok selesai.",
 "v_p":"Belum diproses","v_pt":"Jalankan saluran.",
 "v_cat":"tiada pemeriksaan dokumen diperlukan untuk kategori ini.",
 "blank":"kosong dalam dokumen","handled":"Diuruskan","notproc":"Belum diproses",
 "b_conf":"Sahkan","b_clear":"Selesai","b_rev":"Hantar semakan","b_undo":"Buat asal",
 "hint":"Keputusan ditulis ke jejak audit dan ke submission.json.",
 "setby":"Ditetapkan oleh {who}","noaudit":"Tiada jejak audit lagi.",
 "h_rev":"Barisan semakan","l_rev":"Kes yang sistem tidak dapat putuskan sendiri. Setiap satu membawa bukti dan sebab ia berhenti.",
 "h_fail":"Kegagalan pemprosesan","l_fail":"Satu fail rosak tidak menghentikan larian. Kegagalan direkod dan boleh dicuba semula.",
 "h_rep":"Laporan larian","clear_q":"Barisan kosong. Semua kes telah diuruskan.",
 "no_fail":"Tiada kegagalan dalam larian ini.","decided":"diputuskan oleh orang",
 "export":"Eksport","l_exp":"Menulis outputs/submission.json dengan setiap keputusan semakan.",
 "b_exp":"Tulis submission.json","wrote":"Menulis {n} e-mel ke outputs/submission.json",
 "nodata":"Tiada e-mel dijumpai. Jangkakan data_v2/inbox/ di sebelah fail ini.",
 "nopipe":"outputs/results.json tidak dijumpai, jadi semua e-mel ditunjukkan sebagai belum diproses."},
"zh": {"lang":"语言","appear":"外观","size":"字号",
 "auto":"跟随系统","light":"浅色","dark":"深色","sm":"标准","md":"大","lg":"更大",
 "inbox":"收件箱","review":"待人工","failures":"处理失败","report":"报告",
 "processed":"封邮件已处理","hero":"处不符",
 "sub":"从整个收件箱中找出。另有 {n} 件无法判断，正在等人处理。",
 "t_total":"封邮件已处理","t_disc":"处发现不符","t_wait":"件待人工判断","t_clear":"封已通过",
 "f_all":"全部","f_d":"不符","f_w":"待人工","f_x":"失败","f_g":"已通过",
 "showing":"{a} ／ {b}","first":"仅显示前 {n} 封。",
 "si":"装运指示","bl":"提单草稿",
 "tab_f":"字段","tab_s":"原始文件","tab_a":"审计记录",
 "v_d":"7 个字段中有 {n} 个不一致","v_dt":"草稿定稿前必须更正。",
 "v_g":"七个字段全部一致。","v_gt":"未发现不符。",
 "v_w":"已送人工处理，未作猜测。",
 "v_x":"处理失败","v_xt":"整批仍然跑完。",
 "v_p":"尚未处理","v_pt":"请先跑一次流程。",
 "v_cat":"此类别无需核对文件。",
 "blank":"文件中为空白","handled":"已处理","notproc":"尚未处理",
 "b_conf":"确认","b_clear":"判定通过","b_rev":"送人工","b_undo":"撤销",
 "hint":"判断会写入审计记录，并带进 submission.json。",
 "setby":"由 {who} 设定","noaudit":"暂无审计记录。",
 "h_rev":"待人工处理","l_rev":"系统无法自行判断的个案。每一件都附上证据和停下来的原因，让人几秒内就能决定。",
 "h_fail":"处理失败","l_fail":"一个坏档不会让整批停掉。失败会连同错误记录下来，可以单独重跑。",
 "h_rep":"整批报告","clear_q":"队列已清空，所有个案都处理完了。",
 "no_fail":"这一批没有处理失败。","decided":"由人判定",
 "export":"导出","l_exp":"写出 outputs/submission.json，包含所有人工判断。这是评分器读的文件。",
 "b_exp":"写出 submission.json","wrote":"已写出 {n} 封到 outputs/submission.json",
 "nodata":"找不到邮件。应有 data_v2/inbox/ 在本文件旁边。",
 "nopipe":"找不到 outputs/results.json，所以所有邮件显示为尚未处理。"}}

CAT_NAMES = {
"en": {"BL_COMPARISON":"Document comparison","SI_REQUEST":"New SI request",
       "INVOICE_QUERY":"Invoice query","GENERAL":"General","SPAM":"Spam",None:"Not classified"},
"ms": {"BL_COMPARISON":"Perbandingan dokumen","SI_REQUEST":"Permintaan SI",
       "INVOICE_QUERY":"Pertanyaan invois","GENERAL":"Am","SPAM":"Spam",None:"Belum dikelaskan"},
"zh": {"BL_COMPARISON":"文件比对","SI_REQUEST":"新装运指示","INVOICE_QUERY":"发票查询",
       "GENERAL":"一般通知","SPAM":"垃圾邮件",None:"未分类"}}

FIELD_NAMES = {
"en": {"shipper":"Shipper","consignee":"Consignee","notify_party":"Notify party",
 "port_of_loading":"Port of loading","port_of_discharge":"Port of discharge",
 "container_count":"Container count","gross_weight_kg":"Gross weight"},
"ms": {"shipper":"Penghantar","consignee":"Penerima","notify_party":"Pihak dimaklumkan",
 "port_of_loading":"Pelabuhan muat","port_of_discharge":"Pelabuhan punggah",
 "container_count":"Bilangan kontena","gross_weight_kg":"Berat kasar"},
"zh": {"shipper":"发货人","consignee":"收货人","notify_party":"通知方",
 "port_of_loading":"起运港","port_of_discharge":"卸货港",
 "container_count":"柜数","gross_weight_kg":"毛重"}}

REASON_NAMES = {
"en": {"missing_attachment":"An attachment is missing","unreadable":"A document could not be read",
 "wrong_doc_type":"The wrong document type was attached",
 "missing_value":"A required value is blank in the document"},
"ms": {"missing_attachment":"Lampiran tiada","unreadable":"Dokumen tidak dapat dibaca",
 "wrong_doc_type":"Jenis dokumen salah dilampirkan","missing_value":"Nilai yang diperlukan kosong"},
"zh": {"missing_attachment":"缺少附件","unreadable":"文件无法读取",
 "wrong_doc_type":"附件文件类型错误","missing_value":"必填值为空白"}}

# ------------------------------------------------------------------ controls
st.session_state.setdefault("lang", "en")
st.session_state.setdefault("theme", "auto")
st.session_state.setdefault("size", "sm")

L = st.session_state["lang"]
def t(k, **kw):
    s = T[L].get(k, k)
    return s.format(**kw) if kw else s

c1, c2, c3, c4 = st.columns([5, 1.5, 1.5, 1.5])
with c2:
    st.selectbox(t("lang"), ["en", "ms", "zh"], key="lang",
                 format_func=lambda x: {"en": "English", "ms": "Bahasa Melayu",
                                        "zh": "\u4e2d\u6587"}[x])
with c3:
    st.selectbox(t("appear"), ["auto", "light", "dark"], key="theme",
                 format_func=lambda x: t(x))
with c4:
    st.selectbox(t("size"), ["sm", "md", "lg"], key="size",
                 format_func=lambda x: t(x))

L = st.session_state["lang"]
CATS, FLDS, RSNS = CAT_NAMES[L], FIELD_NAMES[L], REASON_NAMES[L]

# --------------------------------------------------------------------- style
LIGHT = """--bg:#F5F5F7;--card:#FFFFFF;--fill:#EFEFF2;--label:#1D1D1F;--label2:#6E6E73;
--label3:#8E8E93;--sep:rgba(0,0,0,.09);--sep2:rgba(0,0,0,.055);--blue:#0066CC;
--red:#C8102E;--red-bg:#FDEEF0;--green:#1D7A44;--green-bg:#EAF6EE;--orange:#9A5B00;
--orange-bg:#FDF3E4;--sh:0 1px 2px rgba(0,0,0,.04),0 8px 28px rgba(0,0,0,.05);"""
DARK = """--bg:#000000;--card:#1C1C1E;--fill:#2C2C2E;--label:#F5F5F7;--label2:#A1A1A6;
--label3:#8E8E93;--sep:rgba(255,255,255,.12);--sep2:rgba(255,255,255,.07);--blue:#0A84FF;
--red:#FF6961;--red-bg:#2C1315;--green:#4ADE80;--green-bg:#0F2418;--orange:#FFB340;
--orange-bg:#2A1E08;--sh:0 1px 2px rgba(0,0,0,.5),0 8px 28px rgba(0,0,0,.4);"""
SIZES = {"sm": "16px", "md": "17.5px", "lg": "19px"}

theme = st.session_state["theme"]
if theme == "light":
    root = f":root{{{LIGHT}}}"
elif theme == "dark":
    root = f":root{{{DARK}}}"
else:
    root = f":root{{{LIGHT}}}@media(prefers-color-scheme:dark){{:root{{{DARK}}}}}"

st.markdown(f"""<style>
{root}
html{{font-size:{SIZES[st.session_state['size']]}}}
html,body,[class*="css"]{{font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text",
  Inter,system-ui,sans-serif;-webkit-font-smoothing:antialiased}}
.stApp{{background:var(--bg) !important}}
.stApp, .stApp p, .stApp span, .stApp label, .stApp div{{color:var(--label)}}
#MainMenu, footer, header{{visibility:hidden}}
.block-container{{padding-top:1.4rem;padding-bottom:5rem;max-width:1060px}}
.eyebrow{{font-size:.86rem;color:var(--label2) !important;margin:0 0 6px}}
.big{{font-size:clamp(2.3rem,6vw,3.5rem);font-weight:700;letter-spacing:-.036em;
  line-height:1.04;margin:0;color:var(--label) !important}}
.big em{{font-style:normal;color:var(--red) !important}}
.sub{{font-size:1.02rem;color:var(--label2) !important;letter-spacing:-.012em;
  margin:12px 0 0;max-width:44ch;line-height:1.5}}
.band{{display:flex;gap:3px;height:9px;margin:24px 0 10px}}
.band i{{display:block;border-radius:4px}}
.keys{{display:flex;flex-wrap:wrap;gap:5px 18px;font-size:.79rem;
  color:var(--label2) !important;margin:0 0 6px}}
.keys span{{display:flex;align-items:center;gap:7px}}
.keys u{{width:9px;height:9px;border-radius:3px;text-decoration:none;flex:none}}
.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));
  gap:13px;margin:6px 0 22px}}
.tile{{background:var(--card);border-radius:18px;padding:18px 20px;box-shadow:var(--sh)}}
.tile b{{display:block;font-size:1.95rem;font-weight:700;letter-spacing:-.032em;
  line-height:1.1;font-variant-numeric:tabular-nums;color:var(--label) !important}}
.tile span{{display:block;font-size:.81rem;color:var(--label2) !important;margin-top:3px}}
.tile.r b{{color:var(--red) !important}} .tile.a b{{color:var(--orange) !important}}
.tile.g b{{color:var(--green) !important}} .tile.b b{{color:var(--blue) !important}}
.dot{{display:inline-flex;align-items:center;gap:7px;font-size:.77rem;font-weight:600;
  margin-bottom:6px}}
.dot i{{width:8px;height:8px;border-radius:50%;flex:none}}
.dot.d{{color:var(--red) !important}} .dot.d i{{background:var(--red)}}
.dot.w{{color:var(--orange) !important}} .dot.w i{{background:var(--orange)}}
.dot.g{{color:var(--green) !important}} .dot.g i{{background:var(--green)}}
.dot.n{{color:var(--label2) !important}} .dot.n i{{background:var(--label3)}}
.verdict{{padding:13px 17px;border-radius:14px;font-size:.89rem;line-height:1.52;margin:2px 0 14px}}
.verdict.d{{background:var(--red-bg)}} .verdict.d, .verdict.d b{{color:var(--red) !important}}
.verdict.w{{background:var(--orange-bg)}} .verdict.w, .verdict.w b{{color:var(--orange) !important}}
.verdict.g{{background:var(--green-bg)}} .verdict.g, .verdict.g b{{color:var(--green) !important}}
.rowhead{{display:grid;grid-template-columns:1fr 1fr;gap:20px;padding:0 0 9px;
  font-size:.73rem;font-weight:600;color:var(--label3) !important;
  border-bottom:.5px solid var(--sep)}}
.fr{{padding:13px 0;border-bottom:.5px solid var(--sep2)}}
.fn{{display:flex;align-items:center;gap:7px;font-size:.78rem;
  color:var(--label3) !important;margin:0 0 6px}}
.fn i{{width:6px;height:6px;border-radius:50%;background:var(--red);flex:none}}
.fr.d .fn{{color:var(--red) !important;font-weight:600}}
.fr.lo .fn{{color:var(--orange) !important;font-weight:600}}
.fv{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
@media(max-width:640px){{.fv,.rowhead{{grid-template-columns:1fr;gap:9px}}}}
.fval{{font-family:ui-monospace,SFMono-Regular,monospace;font-size:.82rem;line-height:1.5;
  word-break:break-word;color:var(--label) !important;font-variant-numeric:tabular-nums}}
.fr.d .fval{{color:var(--red) !important;font-weight:500}}
.flab{{display:block;font-size:.71rem;color:var(--label3) !important;margin-top:5px}}
.cnf{{display:block;font-size:.69rem;color:var(--label3) !important;margin-top:3px;
  font-family:ui-monospace,monospace}}
.cnf.lo{{color:var(--orange) !important;font-weight:600}}
.nil{{color:var(--orange) !important;font-weight:500;font-size:.82rem}}
.evid{{margin-top:14px;padding:13px 16px;border-radius:14px;background:var(--fill);
  font-size:.85rem;color:var(--label2) !important;line-height:1.62}}
.trail{{margin:8px 0 0;padding:0;list-style:none}}
.trail li{{display:grid;grid-template-columns:135px 1fr;gap:14px;padding:9px 0;
  border-bottom:.5px solid var(--sep2);font-size:.83rem;line-height:1.55}}
.trail time{{font-family:ui-monospace,monospace;font-size:.72rem;color:var(--label3) !important}}
.trail p{{margin:0;color:var(--label2) !important}}
.trail b{{color:var(--label) !important;font-weight:600}}
div[data-testid="stExpander"]{{border:0 !important;border-radius:20px !important;
  background:var(--card) !important;box-shadow:var(--sh) !important;
  margin-bottom:12px !important;overflow:hidden !important}}
div[data-testid="stExpander"] summary{{padding:15px 21px !important;font-weight:600 !important}}
.stButton > button{{border-radius:980px !important;border:0 !important;padding:8px 18px !important;
  font-size:.86rem !important;font-weight:500 !important;background:var(--fill) !important;
  color:var(--label) !important;min-height:42px !important}}
.stButton > button[kind="primary"]{{background:var(--blue) !important;color:#fff !important}}
.stTabs [data-baseweb="tab-list"]{{gap:2px;background:var(--fill);border-radius:10px;padding:3px}}
.stTabs [data-baseweb="tab"]{{border-radius:8px;padding:6px 15px;font-size:.85rem;
  font-weight:500;color:var(--label2) !important}}
.stTabs [aria-selected="true"]{{background:var(--card) !important;color:var(--label) !important}}
.stTabs [data-baseweb="tab-highlight"],.stTabs [data-baseweb="tab-border"]{{display:none}}
div[data-testid="stSelectbox"] label{{font-size:.74rem !important;color:var(--label3) !important}}
div[role="radiogroup"] label{{color:var(--label) !important}}
h3{{font-size:1.1rem !important;font-weight:600 !important;letter-spacing:-.02em !important}}
</style>""", unsafe_allow_html=True)

CAT_COLOURS = {"BL_COMPARISON":"#0066CC","SI_REQUEST":"#3D8FDD",
               "INVOICE_QUERY":"#76B3E8","GENERAL":"#AECFF1","SPAM":"#8E8E93"}
TH = escalation.CONFIDENCE_THRESHOLD


@st.cache_data(ttl=5)
def cases():
    return store.load_cases()


def esc(x):
    return html.escape(str(x)) if x is not None else ""


def kind(s):
    return {"MISMATCH":"d","NEEDS_REVIEW":"w","FAILED":"w","PENDING":"n"}.get(s,"g")


def badge(c):
    s = c["status"]
    if c.get("reviewed_by"):
        return t("handled")
    if s == "MISMATCH":
        return t("f_d")
    if s == "NEEDS_REVIEW":
        return RSNS.get(c.get("review_reason"), t("f_w"))
    if s == "FAILED":
        return t("f_x")
    if s == "PENDING":
        return t("notproc")
    return CATS.get(c.get("category"), t("f_g"))


def comparison_html(c):
    f = c.get("fields") or {}
    if not f:
        return ""
    rows = [f'<div class="rowhead"><span>{t("si")}</span><span>{t("bl")}</span></div>']
    for key in store.FIELDS:
        v = f.get(key, {})
        si, bl = v.get("si_raw", v.get("si_value")), v.get("bl_raw", v.get("bl_value"))
        ca, cb = v.get("si_confidence") or 0.0, v.get("bl_confidence") or 0.0
        bad = v.get("match") is False
        low = (not bad) and min(ca, cb) < TH
        cls = "d" if bad else ("lo" if low else "")
        si_html = (f'<span class="nil">{t("blank")}</span>' if escalation.is_blank(si)
                   else f'<span class="fval">{esc(si)}</span>')
        rows.append(
            f'<div class="fr {cls}"><p class="fn">{"<i></i>" if bad else ""}{FLDS[key]}</p>'
            f'<div class="fv"><div>{si_html}'
            f'<span class="flab">{esc(v.get("si_label", key))}</span>'
            f'<span class="cnf{" lo" if ca < TH else ""}">{ca:.2f}</span></div>'
            f'<div><span class="fval">{esc(bl)}</span>'
            f'<span class="flab">{esc(v.get("bl_label", key))}</span>'
            f'<span class="cnf{" lo" if cb < TH else ""}">{cb:.2f}</span></div>'
            f'</div></div>')
    return "".join(rows)


def verdict_html(c):
    s = c["status"]
    if s == "MISMATCH":
        n = len(c.get("defect_fields", []))
        names = " / ".join(FLDS.get(x, x) for x in c.get("defect_fields", []))
        return f'<p class="verdict d"><b>{t("v_d", n=n)}</b> \u2014 {names}. {t("v_dt")}</p>'
    if s == "NEEDS_REVIEW":
        return (f'<p class="verdict w"><b>{RSNS.get(c.get("review_reason"), t("f_w"))}</b> '
                f'\u2014 {t("v_w")}</p>')
    if s == "FAILED":
        return f'<p class="verdict w"><b>{t("v_x")}</b> \u2014 {t("v_xt")}</p>'
    if s == "PENDING":
        return f'<p class="verdict w"><b>{t("v_p")}</b> \u2014 {t("v_pt")}</p>'
    if c.get("category") == "BL_COMPARISON":
        return f'<p class="verdict g"><b>{t("v_g")}</b> {t("v_gt")}</p>'
    return f'<p class="verdict g"><b>{CATS.get(c.get("category"))}</b> \u2014 {t("v_cat")}</p>'


def trail_html(c):
    entries = audit.read(c["email_id"]) or audit.from_result(c)
    if not entries:
        return f'<p class="evid">{t("noaudit")}</p>'
    items = []
    for e in entries:
        extra = ""
        if e.get("source"):
            extra += f' \u00b7 {esc(e["source"])}'
        if e.get("model"):
            extra += f' \u00b7 {esc(e["model"])}'
        if e.get("confidence") is not None:
            extra += f' \u00b7 {e["confidence"]:.2f}'
        items.append(f'<li><time>{esc(e["at"])[:19].replace("T"," ")}</time>'
                     f'<p><b>{esc(e["action"]).title()}</b> \u2014 {esc(e["detail"])}{extra}</p></li>')
    return f'<ul class="trail">{"".join(items)}</ul>'


def decide(eid, d):
    store.save_decision(eid, d)
    audit.record(eid, "reviewed", f"Decided {d}", actor="reviewer")
    cases.clear()


def undo(eid):
    store.clear_decision(eid)
    audit.record(eid, "reviewed", "Decision withdrawn", actor="reviewer")
    cases.clear()


def render_case(c, prefix):
    eid = c["email_id"]
    k = "g" if c.get("reviewed_by") else kind(c["status"])
    with st.expander(f"{badge(c)}  \u00b7  {c['subject'][:74]}"):
        st.markdown(
            f'<div class="dot {k}"><i></i>{badge(c)}</div>'
            f'<div style="font-size:.84rem;color:var(--label3);margin-bottom:12px">'
            f'{eid} \u00b7 {esc(c["from"])} \u00b7 {CATS.get(c.get("category"))}</div>'
            + verdict_html(c), unsafe_allow_html=True)

        names = []
        if c.get("fields"):
            names.append(t("tab_f"))
        atts = c.get("attachments") or []
        has_docs = len(atts) >= 2 and store.read_attachment(atts[0])
        if has_docs:
            names.append(t("tab_s"))
        names.append(t("tab_a"))
        tabs = st.tabs(names)

        i = 0
        if c.get("fields"):
            with tabs[i]:
                st.markdown(comparison_html(c), unsafe_allow_html=True)
            i += 1
        if has_docs:
            with tabs[i]:
                a, b = st.columns(2)
                with a:
                    st.caption(Path(atts[0]).name)
                    st.code(store.read_attachment(atts[0]) or "", language=None)
                with b:
                    st.caption(Path(atts[1]).name)
                    st.code(store.read_attachment(atts[1]) or "", language=None)
            i += 1
        with tabs[i]:
            st.markdown(trail_html(c), unsafe_allow_html=True)

        ev = (c.get("escalation") or {}).get("evidence") or c.get("error")
        if ev:
            st.markdown(f'<p class="evid">{esc(ev)}</p>', unsafe_allow_html=True)

        st.write("")
        if c.get("reviewed_by"):
            a, b = st.columns([1, 4])
            a.button(t("b_undo"), key=f"{prefix}_u_{eid}", on_click=undo, args=(eid,))
            b.caption(t("setby", who=c["reviewed_by"]))
        else:
            a, b, d, e = st.columns([1.2, 1, 1.5, 3])
            a.button(t("b_conf"), key=f"{prefix}_c_{eid}", type="primary",
                     on_click=decide, args=(eid, "MISMATCH"))
            b.button(t("b_clear"), key=f"{prefix}_o_{eid}", on_click=decide, args=(eid, "OK"))
            d.button(t("b_rev"), key=f"{prefix}_r_{eid}", on_click=decide, args=(eid, "NEEDS_REVIEW"))
            e.caption(t("hint"))


all_cases = cases()
s = store.summary(all_cases)

if not all_cases:
    st.error(t("nodata"))
    st.stop()
if not store.pipeline_has_run():
    st.warning(t("nopipe"))

t1, t2, t3, t4 = st.tabs([t("inbox"),
                          f'{t("review")} ({s["by_status"].get("NEEDS_REVIEW",0)})',
                          f'{t("failures")} ({s["by_status"].get("FAILED",0)})',
                          t("report")])

with t1:
    mism = s["by_status"].get("MISMATCH", 0)
    st.markdown(f'<p class="eyebrow">{s["total"]} {t("processed")}</p>'
                f'<h1 class="big"><em>{mism}</em> {t("hero")}</h1>'
                f'<p class="sub">{t("sub", n=s["by_status"].get("NEEDS_REVIEW",0))}</p>',
                unsafe_allow_html=True)
    if s["by_category"]:
        band = "".join(f'<i style="flex:{n};background:{CAT_COLOURS.get(c,"#8E8E93")}"></i>'
                       for c, n in s["by_category"].items())
        keys = "".join(f'<span><u style="background:{CAT_COLOURS.get(c,"#8E8E93")}"></u>'
                       f'{CATS.get(c)} {n}</span>' for c, n in s["by_category"].items())
        st.markdown(f'<div class="band">{band}</div><p class="keys">{keys}</p>',
                    unsafe_allow_html=True)
    st.markdown('<div class="tiles">'
                f'<div class="tile"><b>{s["total"]}</b><span>{t("t_total")}</span></div>'
                f'<div class="tile r"><b>{mism}</b><span>{t("t_disc")}</span></div>'
                f'<div class="tile a"><b>{s["by_status"].get("NEEDS_REVIEW",0)}</b>'
                f'<span>{t("t_wait")}</span></div>'
                f'<div class="tile g"><b>{s["by_status"].get("OK",0)}</b>'
                f'<span>{t("t_clear")}</span></div></div>', unsafe_allow_html=True)

    opts = [t("f_all"), t("f_d"), t("f_w"), t("f_x"), t("f_g")]
    pick = st.radio("f", opts, horizontal=True, label_visibility="collapsed")
    wanted = {opts[1]:"MISMATCH", opts[2]:"NEEDS_REVIEW",
              opts[3]:"FAILED", opts[4]:"OK"}.get(pick)
    shown = [c for c in all_cases if wanted is None or c["status"] == wanted]
    st.caption(t("showing", a=len(shown), b=len(all_cases)))
    for c in shown[:60]:
        render_case(c, "inbox")
    if len(shown) > 60:
        st.caption(t("first", n=60))

with t2:
    st.subheader(t("h_rev"))
    st.markdown(f'<p class="sub" style="margin-bottom:18px">{t("l_rev")}</p>',
                unsafe_allow_html=True)
    if s["by_reason"]:
        tiles = "".join(f'<div class="tile a"><b>{n}</b><span>{RSNS.get(r,r)}</span></div>'
                        for r, n in s["by_reason"].items())
        st.markdown(f'<div class="tiles">{tiles}</div>', unsafe_allow_html=True)
    q = [c for c in all_cases if c["status"] == "NEEDS_REVIEW"]
    if not q:
        st.success(t("clear_q"))
    for c in q[:60]:
        render_case(c, "review")

with t3:
    st.subheader(t("h_fail"))
    st.markdown(f'<p class="sub" style="margin-bottom:18px">{t("l_fail")}</p>',
                unsafe_allow_html=True)
    fail = [c for c in all_cases if c["status"] == "FAILED"]
    if not fail:
        st.success(t("no_fail"))
    for c in fail:
        render_case(c, "fail")

with t4:
    st.subheader(t("h_rep"))
    tiles = "".join(f'<div class="tile"><b>{n}</b><span>{str(k).replace("_"," ").lower() if k else "n/a"}</span></div>'
                for k, n in s["by_status"].items())
    st.markdown(f'<div class="tiles">{tiles}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="tiles"><div class="tile b"><b>{s["reviewed"]}</b>'
                f'<span>{t("decided")}</span></div></div>', unsafe_allow_html=True)
    st.markdown(f"### {t('export')}")
    st.write(t("l_exp"))
    if st.button(t("b_exp"), type="primary"):
        n = store.export_submission(all_cases)
        st.success(t("wrote", n=n))
