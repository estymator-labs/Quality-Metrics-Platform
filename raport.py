import os
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter, defaultdict
from html import escape

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

from dotenv import load_dotenv
from pymongo import MongoClient


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "sandmark-db")

COLLECTION_REVIEW_LOGS = os.getenv("COLLECTION_REVIEW_LOGS", "sandmark-history")

OUTPUT_HTML = "QualityMetrics_Sandmark_real_data_report.html"
OUTPUT_PDF = "QualityMetrics_Sandmark_real_data_report.pdf"

ASSETS_DIR = Path("sandmark_report_assets")
ASSETS_DIR.mkdir(exist_ok=True)

sns.set_theme(
    style="whitegrid",
    context="talk",
    font="DejaVu Sans"
)

COLORS = {
    "primary": "#00a991",
    "secondary": "#3b82f6",
    "danger": "#d95f5f",
    "warning": "#f0a93b",
    "dark": "#0b1f2a",
    "muted": "#64748b"
}


# ============================================================
# HELPERS
# ============================================================

def safe(value):
    if value is None:
        return ""
    return escape(str(value))


def pct(part, total):
    if total == 0:
        return 0.0
    return round((part / total) * 100, 2)


def parse_datetime(value):
    if value is None:
        return None

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    return None


def save_chart(path):
    plt.tight_layout()
    plt.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close()


def get_db():
    if not MONGODB_URI:
        raise RuntimeError("Missing MONGODB_URI in .env file")

    client = MongoClient(MONGODB_URI)
    return client[MONGO_DB_NAME]


# ============================================================
# REAL SANDMARK DATA LOADING
# ============================================================

def load_sandmark_reviews(db):
    return list(db[COLLECTION_REVIEW_LOGS].find({}))


# ============================================================
# REAL METRICS FROM SANDMARK
# ============================================================

def calculate_review_density(review_docs):
    comments_by_type = Counter()
    comments_by_file = Counter()
    comments_by_mr = []

    total_comments = 0

    for doc in review_docs:
        comments = doc.get("review_json", {}).get("comments", [])
        total_comments += len(comments)

        mr_url = doc.get("mr_url", "unknown")

        comments_by_mr.append({
            "mr_url": mr_url,
            "comments_count": len(comments)
        })

        for comment in comments:
            comment_type = comment.get("type", "unknown")
            file_name = comment.get("file", "unknown")

            comments_by_type[comment_type] += 1
            comments_by_file[file_name] += 1

    total_mrs = len(review_docs)
    average_comments = round(total_comments / total_mrs, 2) if total_mrs else 0

    return {
        "metric": "review_density",
        "value": average_comments,
        "unit": "avg comments per MR",
        "total_mrs": total_mrs,
        "total_comments": total_comments,
        "comments_by_type": dict(comments_by_type),
        "top_files": comments_by_file.most_common(10),
        "comments_by_mr": comments_by_mr
    }


def calculate_defect_escape(review_docs):
    mrs_with_bug = 0
    total_bug_comments = 0

    bug_files = Counter()
    mr_by_month = defaultdict(int)
    bug_mr_by_month = defaultdict(int)

    for doc in review_docs:
        timestamp = parse_datetime(doc.get("timestamp"))
        month = timestamp.strftime("%Y-%m") if timestamp else "unknown"

        mr_by_month[month] += 1

        comments = doc.get("review_json", {}).get("comments", [])
        has_bug = False

        for comment in comments:
            if comment.get("type") == "bug":
                has_bug = True
                total_bug_comments += 1
                bug_files[comment.get("file", "unknown")] += 1

        if has_bug:
            mrs_with_bug += 1
            bug_mr_by_month[month] += 1

    total_mrs = len(review_docs)

    monthly = []

    for month in sorted(mr_by_month.keys()):
        total = mr_by_month[month]
        bug_count = bug_mr_by_month.get(month, 0)

        monthly.append({
            "month": month,
            "total_mrs": total,
            "mrs_with_bug": bug_count,
            "bug_percentage": pct(bug_count, total)
        })

    return {
        "metric": "defect_escape",
        "value": pct(mrs_with_bug, total_mrs),
        "unit": "% MR with bug comments",
        "total_mrs": total_mrs,
        "mrs_with_bug": mrs_with_bug,
        "total_bug_comments": total_bug_comments,
        "top_bug_files": bug_files.most_common(10),
        "monthly": monthly
    }


# ============================================================
# EVIDENCE FROM REAL SANDMARK DATA
# ============================================================

def build_real_data_evidence(review_docs):
    evidence = {
        "database": MONGO_DB_NAME,
        "collection": COLLECTION_REVIEW_LOGS,
        "documents_count": len(review_docs),
        "example_fields": [],
        "sample_review": {},
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    if not review_docs:
        return evidence

    sample = review_docs[0]
    comments = sample.get("review_json", {}).get("comments", [])

    evidence["example_fields"] = list(sample.keys())

    evidence["sample_review"] = {
        "timestamp": sample.get("timestamp"),
        "mr_url": sample.get("mr_url"),
        "prompt_name": sample.get("prompt_name"),
        "prompt_hash": sample.get("prompt_hash"),
        "llm_model": sample.get("llm_model"),
        "tokens_used": sample.get("tokens_used"),
        "elapsed_ms": sample.get("elapsed_ms"),
        "review_json_present": "review_json" in sample,
        "comments_count": len(comments),
        "first_comment_type": comments[0].get("type") if comments else None,
        "first_comment_file": comments[0].get("file") if comments else None
    }

    return evidence


# ============================================================
# SEABORN CHARTS FOR REAL SANDMARK DATA ONLY
# ============================================================

def generate_real_sandmark_charts(review_density, defect_escape):
    paths = {}

    # 1. Comment type distribution
    comments_by_type = review_density["comments_by_type"]

    df_comment_types = pd.DataFrame([
        {"type": key, "count": value}
        for key, value in comments_by_type.items()
    ]).sort_values("count", ascending=False)

    plt.figure(figsize=(10, 6))
    ax = sns.barplot(
        data=df_comment_types,
        x="count",
        y="type",
        hue="type",
        dodge=False,
        palette="viridis",
        legend=False
    )
    ax.set_title("Rozkład komentarzy Gemini według typu", fontsize=18, weight="bold")
    ax.set_xlabel("Liczba komentarzy")
    ax.set_ylabel("Typ komentarza")

    for container in ax.containers:
        ax.bar_label(container, fmt="%.0f", padding=4)

    paths["comments_by_type"] = ASSETS_DIR / "comments_by_type.png"
    save_chart(paths["comments_by_type"])

    # 2. Monthly defect escape
    df_monthly = pd.DataFrame(defect_escape["monthly"])

    if not df_monthly.empty:
        plt.figure(figsize=(11, 6))
        ax = sns.lineplot(
            data=df_monthly,
            x="month",
            y="bug_percentage",
            marker="o",
            linewidth=3,
            color=COLORS["danger"]
        )
        sns.scatterplot(
            data=df_monthly,
            x="month",
            y="bug_percentage",
            s=120,
            color=COLORS["danger"]
        )
        ax.set_title("% MR z bug-komentarzem według miesiąca", fontsize=18, weight="bold")
        ax.set_xlabel("Miesiąc")
        ax.set_ylabel("% MR z bug-komentarzem")
        ax.set_ylim(0, max(100, df_monthly["bug_percentage"].max() + 10))

        for index, row in df_monthly.iterrows():
            ax.text(
                index,
                row["bug_percentage"] + 2,
                f'{row["bug_percentage"]:.1f}%',
                ha="center",
                fontsize=11
            )

        paths["defect_escape_monthly"] = ASSETS_DIR / "defect_escape_monthly.png"
        save_chart(paths["defect_escape_monthly"])

    # 3. Top files by all Gemini comments
    top_files = review_density["top_files"]

    df_files = pd.DataFrame([
        {"file": file_name, "comments": count}
        for file_name, count in top_files
    ])

    if not df_files.empty:
        plt.figure(figsize=(12, 7))
        ax = sns.barplot(
            data=df_files,
            x="comments",
            y="file",
            hue="file",
            dodge=False,
            palette="mako",
            legend=False
        )
        ax.set_title("Najczęściej komentowane pliki", fontsize=18, weight="bold")
        ax.set_xlabel("Liczba komentarzy Gemini")
        ax.set_ylabel("Plik")

        for container in ax.containers:
            ax.bar_label(container, fmt="%.0f", padding=4)

        paths["top_commented_files"] = ASSETS_DIR / "top_commented_files.png"
        save_chart(paths["top_commented_files"])

    # 4. Top bug files
    top_bug_files = defect_escape["top_bug_files"]

    df_bug_files = pd.DataFrame([
        {"file": file_name, "bug_comments": count}
        for file_name, count in top_bug_files
    ])

    if not df_bug_files.empty:
        plt.figure(figsize=(12, 7))
        ax = sns.barplot(
            data=df_bug_files,
            x="bug_comments",
            y="file",
            hue="file",
            dodge=False,
            palette="rocket",
            legend=False
        )
        ax.set_title("Pliki z największą liczbą bug-komentarzy", fontsize=18, weight="bold")
        ax.set_xlabel("Liczba bug-komentarzy")
        ax.set_ylabel("Plik")

        for container in ax.containers:
            ax.bar_label(container, fmt="%.0f", padding=4)

        paths["top_bug_files"] = ASSETS_DIR / "top_bug_files.png"
        save_chart(paths["top_bug_files"])

    return paths


# ============================================================
# HTML REPORT
# ============================================================

def img(path):
    return str(path).replace("\\", "/")


def render_top_files_rows(top_files):
    if not top_files:
        return "<tr><td colspan='3'>Brak danych.</td></tr>"

    rows = ""

    for index, item in enumerate(top_files, start=1):
        file_name, count = item

        rows += f"""
        <tr>
            <td>{index}</td>
            <td><code>{safe(file_name)}</code></td>
            <td>{count}</td>
        </tr>
        """

    return rows


def render_report(review_density, defect_escape, evidence, chart_paths):
    sample = evidence["sample_review"]

    comments_chart = ""
    if "comments_by_type" in chart_paths:
        comments_chart = f"""
        <div class="chart-card">
            <img src="{img(chart_paths["comments_by_type"])}" alt="Rozkład komentarzy">
        </div>
        """

    monthly_chart = ""
    if "defect_escape_monthly" in chart_paths:
        monthly_chart = f"""
        <div class="chart-card">
            <img src="{img(chart_paths["defect_escape_monthly"])}" alt="Defect escape monthly">
        </div>
        """

    top_files_chart = ""
    if "top_commented_files" in chart_paths:
        top_files_chart = f"""
        <div class="chart-card">
            <img src="{img(chart_paths["top_commented_files"])}" alt="Top commented files">
        </div>
        """

    bug_files_chart = ""
    if "top_bug_files" in chart_paths:
        bug_files_chart = f"""
        <div class="chart-card">
            <img src="{img(chart_paths["top_bug_files"])}" alt="Top bug files">
        </div>
        """

    html = f"""
<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="UTF-8">
<title>QualityMetrics — raport z realnych danych Sandmark</title>

<style>
    :root {{
        --bg: #f5f7fb;
        --paper: #ffffff;
        --ink: #17212f;
        --muted: #64748b;
        --line: #e2e8f0;
        --primary: #00a991;
        --primary-dark: #007f71;
        --danger: #d95f5f;
        --warning: #f0a93b;
        --soft-green: #eefaf7;
        --soft-yellow: #fff8e8;
        --soft-blue: #eef5ff;
    }}

    body {{
        margin: 0;
        background: var(--bg);
        color: var(--ink);
        font-family: Arial, Helvetica, sans-serif;
        line-height: 1.55;
    }}

    .report {{
        max-width: 1180px;
        margin: 0 auto;
        padding: 36px;
    }}

    .cover {{
        background: linear-gradient(135deg, #082f3d, #0b1f2a);
        color: white;
        border-radius: 28px;
        padding: 48px;
        box-shadow: 0 18px 45px rgba(0,0,0,0.18);
        margin-bottom: 34px;
    }}

    .cover-label {{
        color: #77f7df;
        text-transform: uppercase;
        letter-spacing: 2px;
        font-size: 13px;
        font-weight: 700;
    }}

    h1 {{
        font-size: 42px;
        line-height: 1.15;
        margin: 12px 0 12px 0;
    }}

    .cover-subtitle {{
        color: #c5d6e4;
        font-size: 18px;
        max-width: 920px;
    }}

    .cover-grid {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 14px;
        margin-top: 30px;
    }}

    .cover-box {{
        background: rgba(255,255,255,0.08);
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 16px;
        padding: 15px;
    }}

    .cover-box-title {{
        color: #8fded0;
        text-transform: uppercase;
        font-size: 12px;
        letter-spacing: 1px;
        font-weight: 700;
    }}

    .cover-box-value {{
        margin-top: 7px;
        font-size: 16px;
        word-break: break-word;
    }}

    h2 {{
        margin-top: 44px;
        padding-bottom: 10px;
        border-bottom: 2px solid var(--line);
        font-size: 26px;
    }}

    h3 {{
        margin-top: 26px;
        font-size: 19px;
    }}

    .lead {{
        color: var(--muted);
        font-size: 17px;
        max-width: 1000px;
    }}

    .kpi-grid {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 18px;
        margin: 24px 0 28px 0;
    }}

    .kpi {{
        background: var(--paper);
        border: 1px solid var(--line);
        border-radius: 22px;
        padding: 22px;
        box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
    }}

    .kpi-title {{
        color: var(--muted);
        text-transform: uppercase;
        letter-spacing: 1px;
        font-size: 12px;
        font-weight: 700;
    }}

    .kpi-value {{
        margin-top: 10px;
        font-size: 36px;
        color: var(--primary-dark);
        font-weight: 800;
    }}

    .kpi-value.danger {{
        color: var(--danger);
    }}

    .kpi-desc {{
        margin-top: 6px;
        color: var(--muted);
        font-size: 13px;
    }}

    .section-card {{
        background: var(--paper);
        border: 1px solid var(--line);
        border-radius: 22px;
        padding: 26px;
        margin-top: 18px;
        box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
    }}

    .real-data-box {{
        background: var(--soft-green);
        border-left: 6px solid var(--primary);
        border-radius: 16px;
        padding: 18px 20px;
        margin: 18px 0;
    }}

    .future-box {{
        background: var(--soft-blue);
        border-left: 6px solid #3b82f6;
        border-radius: 16px;
        padding: 18px 20px;
        margin: 18px 0;
    }}

    .warning-box {{
        background: var(--soft-yellow);
        border-left: 6px solid var(--warning);
        border-radius: 16px;
        padding: 18px 20px;
        margin: 18px 0;
    }}

    .two-col {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 24px;
        margin-top: 22px;
    }}

    .chart-card {{
        background: var(--paper);
        border: 1px solid var(--line);
        border-radius: 22px;
        padding: 20px;
        box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
    }}

    .chart-card img {{
        width: 100%;
        display: block;
        border-radius: 14px;
    }}

    table {{
        width: 100%;
        border-collapse: collapse;
        margin-top: 14px;
        background: var(--paper);
        border: 1px solid var(--line);
        border-radius: 16px;
        overflow: hidden;
    }}

    th {{
        background: #edf2f7;
        color: #334155;
        padding: 12px;
        text-align: left;
        font-size: 13px;
        text-transform: uppercase;
        letter-spacing: 0.7px;
    }}

    td {{
        padding: 12px;
        border-top: 1px solid var(--line);
        font-size: 14px;
        vertical-align: top;
    }}

    code {{
        background: #eef6f5;
        color: #007f71;
        padding: 2px 5px;
        border-radius: 5px;
        font-family: Consolas, monospace;
        font-size: 13px;
        word-break: break-word;
    }}

    ul {{
        margin-top: 10px;
    }}

    li {{
        margin-bottom: 7px;
    }}

    .footer {{
        margin-top: 50px;
        padding-top: 20px;
        border-top: 1px solid var(--line);
        color: var(--muted);
        font-size: 13px;
    }}

    @media print {{
        body {{
            background: white;
        }}

        .report {{
            padding: 20px;
        }}

        .cover,
        .kpi,
        .section-card,
        .chart-card {{
            box-shadow: none;
        }}

        .two-col {{
            grid-template-columns: 1fr;
        }}

        .kpi-grid {{
            grid-template-columns: repeat(2, 1fr);
        }}
    }}
</style>
</head>

<body>
<div class="report">

    <section class="cover">
        <div class="cover-label">Sandmark · QualityMetrics</div>
        <h1>Raport z realnych danych Sandmark</h1>
        <div class="cover-subtitle">
            Raport przedstawia wyniki metryk, które zostały policzone bezpośrednio na podstawie
            rzeczywistych logów przeglądów kodu AI zapisanych przez Sandmark w MongoDB Atlas.
            Agenty wymagające innych źródeł danych są opisane jako gotowe rozszerzenia modułu.
        </div>

        <div class="cover-grid">
            <div class="cover-box">
                <div class="cover-box-title">Baza danych</div>
                <div class="cover-box-value">{safe(evidence["database"])}</div>
            </div>
            <div class="cover-box">
                <div class="cover-box-title">Kolekcja realna</div>
                <div class="cover-box-value">{safe(evidence["collection"])}</div>
            </div>
            <div class="cover-box">
                <div class="cover-box-title">Dokumenty Sandmark</div>
                <div class="cover-box-value">{evidence["documents_count"]}</div>
            </div>
            <div class="cover-box">
                <div class="cover-box-title">Wygenerowano</div>
                <div class="cover-box-value">{safe(evidence["generated_at"])}</div>
            </div>
        </div>
    </section>

    <h2>1. Zakres raportu</h2>

    <p class="lead">
        Ten raport celowo oddziela metryki policzone na rzeczywistych danych Sandmarka od agentów,
        które są już zaimplementowane, ale wymagają osobnych źródeł danych organizacyjnych.
        Dzięki temu raport pokazuje wyłącznie potwierdzone wyniki z kolekcji 
        <code>{safe(COLLECTION_REVIEW_LOGS)}</code>, a pozostałe agenty opisuje jako gotowe do integracji.
    </p>

    <div class="real-data-box">
        <strong>Metryki policzone na realnych danych Sandmark:</strong>
        <ul>
            <li><code>review_density</code> — średnia liczba komentarzy Gemini na Merge Request.</li>
            <li><code>defect_escape</code> — procent MR z co najmniej jednym komentarzem typu <code>bug</code>.</li>
        </ul>
    </div>

    <div class="future-box">
        <strong>Agenty gotowe do użycia po podłączeniu realnych kolekcji organizacyjnych:</strong>
        <ul>
            <li><code>traceability</code> — wymaga realnej kolekcji wymagań i powiązań z testami.</li>
            <li><code>risk_closure</code> — wymaga realnego rejestru ryzyk.</li>
            <li><code>soup_completeness</code> — wymaga realnego rejestru SOUP.</li>
        </ul>
    </div>

    <h2>2. Executive summary — wyniki z Sandmark</h2>

    <div class="kpi-grid">
        <div class="kpi">
            <div class="kpi-title">Review density</div>
            <div class="kpi-value">{review_density["value"]}</div>
            <div class="kpi-desc">średnia liczba komentarzy Gemini na MR</div>
        </div>

        <div class="kpi">
            <div class="kpi-title">Defect escape</div>
            <div class="kpi-value danger">{defect_escape["value"]}%</div>
            <div class="kpi-desc">{defect_escape["mrs_with_bug"]} MR z bug-komentarzem</div>
        </div>

        <div class="kpi">
            <div class="kpi-title">MR logs</div>
            <div class="kpi-value">{review_density["total_mrs"]}</div>
            <div class="kpi-desc">dokumentów w kolekcji Sandmark</div>
        </div>

        <div class="kpi">
            <div class="kpi-title">Komentarze Gemini</div>
            <div class="kpi-value">{review_density["total_comments"]}</div>
            <div class="kpi-desc">łączna liczba komentarzy AI</div>
        </div>
    </div>

    <div class="real-data-box">
        <strong>Wniosek:</strong>
        Sandmark wygenerował <strong>{review_density["total_comments"]}</strong> komentarzy dla 
        <strong>{review_density["total_mrs"]}</strong> dokumentów Merge Request.
        Średnia liczba komentarzy na MR wynosi <strong>{review_density["value"]}</strong>,
        a <strong>{defect_escape["value"]}%</strong> MR zawierało przynajmniej jeden komentarz typu bug.
    </div>

    <h2>3. Dowód pracy na realnych danych</h2>

    <div class="section-card">
        <p>
            Dane zostały odczytane bezpośrednio z MongoDB Atlas, z bazy
            <code>{safe(evidence["database"])}</code> i kolekcji
            <code>{safe(evidence["collection"])}</code>.
            Ta kolekcja zawiera dokumenty zapisane przez Sandmark po wykonaniu code review przez model Gemini.
        </p>

        <table>
            <tbody>
                <tr>
                    <th>Baza danych</th>
                    <td><code>{safe(evidence["database"])}</code></td>
                </tr>
                <tr>
                    <th>Kolekcja</th>
                    <td><code>{safe(evidence["collection"])}</code></td>
                </tr>
                <tr>
                    <th>Liczba dokumentów</th>
                    <td>{safe(evidence["documents_count"])}</td>
                </tr>
                <tr>
                    <th>Przykładowe pola</th>
                    <td>{safe(", ".join(evidence["example_fields"]))}</td>
                </tr>
            </tbody>
        </table>

        <h3>Przykładowy dokument Sandmark</h3>

        <table>
            <tbody>
                <tr><th>timestamp</th><td>{safe(sample.get("timestamp"))}</td></tr>
                <tr><th>mr_url</th><td><code>{safe(sample.get("mr_url"))}</code></td></tr>
                <tr><th>prompt_name</th><td>{safe(sample.get("prompt_name"))}</td></tr>
                <tr><th>prompt_hash</th><td>{safe(sample.get("prompt_hash"))}</td></tr>
                <tr><th>llm_model</th><td>{safe(sample.get("llm_model"))}</td></tr>
                <tr><th>tokens_used</th><td>{safe(sample.get("tokens_used"))}</td></tr>
                <tr><th>elapsed_ms</th><td>{safe(sample.get("elapsed_ms"))}</td></tr>
                <tr><th>review_json present</th><td>{safe(sample.get("review_json_present"))}</td></tr>
                <tr><th>comments_count</th><td>{safe(sample.get("comments_count"))}</td></tr>
                <tr><th>first_comment_type</th><td>{safe(sample.get("first_comment_type"))}</td></tr>
                <tr><th>first_comment_file</th><td><code>{safe(sample.get("first_comment_file"))}</code></td></tr>
            </tbody>
        </table>

        <div class="real-data-box">
            Obecność pól <code>mr_url</code>, <code>prompt_name</code>, <code>prompt_hash</code>,
            <code>llm_model</code>, <code>tokens_used</code>, <code>elapsed_ms</code>
            oraz <code>review_json.comments</code> potwierdza, że dane pochodzą z rzeczywistego procesu
            działania Sandmarka, a nie z ręcznie wpisanego dashboardu.
        </div>
    </div>

    <h2>4. Metryka review_density</h2>

    <div class="section-card">
        <p>
            Agent <code>review_density</code> mierzy średnią liczbę komentarzy Gemini przypadającą na jeden
            Merge Request. Każdy dokument w kolekcji <code>{safe(COLLECTION_REVIEW_LOGS)}</code>
            reprezentuje jeden przegląd MR, a komentarze znajdują się w polu 
            <code>review_json.comments</code>.
        </p>

        <div class="real-data-box">
            Wartość metryki wynosi <strong>{review_density["value"]}</strong>.
            Oznacza to, że Gemini zostawiał średnio 
            <strong>{review_density["value"]}</strong> komentarza na jeden Merge Request.
        </div>

        <div class="two-col">
            {comments_chart}
            {top_files_chart}
        </div>

        <h3>Najczęściej komentowane pliki</h3>

        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Plik</th>
                    <th>Liczba komentarzy</th>
                </tr>
            </thead>
            <tbody>
                {render_top_files_rows(review_density["top_files"])}
            </tbody>
        </table>
    </div>

    <h2>5. Metryka defect_escape</h2>

    <div class="section-card">
        <p>
            Agent <code>defect_escape</code> mierzy procent Merge Requestów, w których Gemini wykrył
            przynajmniej jeden komentarz typu <code>bug</code>. Wskaźnik ten można interpretować jako
            sygnał potencjalnego ryzyka jakościowego w zmianach kodu.
        </p>

        <div class="real-data-box">
            Wartość metryki wynosi <strong>{defect_escape["value"]}%</strong>.
            Oznacza to, że <strong>{defect_escape["mrs_with_bug"]}</strong>
            z <strong>{defect_escape["total_mrs"]}</strong> MR zawierało co najmniej jeden komentarz typu bug.
            Łącznie znaleziono <strong>{defect_escape["total_bug_comments"]}</strong> bug-komentarzy.
        </div>

        <div class="two-col">
            {monthly_chart}
            {bug_files_chart}
        </div>

        <h3>Pliki z największą liczbą bug-komentarzy</h3>

        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Plik</th>
                    <th>Liczba bug-komentarzy</th>
                </tr>
            </thead>
            <tbody>
                {render_top_files_rows(defect_escape["top_bug_files"])}
            </tbody>
        </table>
    </div>

    <h2>6. Agenty gotowe do integracji z dodatkowymi danymi</h2>

    <div class="section-card">
        <p>
            Poniższe trzy agenty zostały zaimplementowane w module QualityMetrics, ale ich wyniki nie są
            prezentowane w tym raporcie jako realne wyniki Sandmarka. Powód jest prosty:
            Sandmark zapisuje logi przeglądów kodu, ale nie tworzy automatycznie rejestru wymagań,
            rejestru ryzyk ani rejestru SOUP. Te dane muszą pochodzić z osobnych systemów organizacyjnych.
        </p>

        <table>
            <thead>
                <tr>
                    <th>Agent</th>
                    <th>Co mierzy</th>
                    <th>Wymagana kolekcja</th>
                    <th>Minimalne pola</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><code>traceability</code></td>
                    <td>Procent wymagań pokrytych testami.</td>
                    <td><code>requirements</code></td>
                    <td><code>req_id</code>, <code>title</code>, <code>linked_test_ids</code></td>
                    <td>Agent gotowy, wymaga realnego źródła wymagań.</td>
                </tr>
                <tr>
                    <td><code>risk_closure</code></td>
                    <td>Procent zamkniętych lub zmitygowanych ryzyk.</td>
                    <td><code>risks</code></td>
                    <td><code>risk_id</code>, <code>severity</code>, <code>created_at</code>, <code>closed_at</code>, <code>mitigation_status</code></td>
                    <td>Agent gotowy, wymaga realnego rejestru ryzyk.</td>
                </tr>
                <tr>
                    <td><code>soup_completeness</code></td>
                    <td>Kompletność rejestru bibliotek zewnętrznych.</td>
                    <td><code>soup_register</code></td>
                    <td><code>library_name</code>, <code>version</code>, <code>license</code>, <code>has_risk_assessment</code>, <code>has_validation_record</code>, <code>last_reviewed_at</code></td>
                    <td>Agent gotowy, wymaga realnego rejestru SOUP.</td>
                </tr>
            </tbody>
        </table>

        <div class="future-box">
            <strong>Jak użyć tych agentów w praktyce:</strong>
            wystarczy podłączyć realne kolekcje MongoDB z wymaganiami, ryzykami i SOUP.
            Nazwy kolekcji można ustawić w pliku <code>.env</code>:
            <ul>
                <li><code>COLLECTION_REQUIREMENTS=requirements</code></li>
                <li><code>COLLECTION_RISKS=risks</code></li>
                <li><code>COLLECTION_SOUP=soup_register</code></li>
            </ul>
            Po uzupełnieniu tych kolekcji agentów można uruchomić przez endpoint
            <code>/metrics/summary</code> albo osobno przez <code>/metrics/{{agent_name}}</code>.
        </div>
    </div>

    <h2>7. Co zostało wykonane</h2>

    <div class="section-card">
        <ul>
            <li>Utworzono moduł QualityMetrics jako warstwę analityczną dla danych Sandmarka.</li>
            <li>Podłączono projekt do MongoDB Atlas przez konfigurację <code>.env</code>.</li>
            <li>Zaimplementowano agent <code>review_density</code> dla realnych logów code review.</li>
            <li>Zaimplementowano agent <code>defect_escape</code> dla realnych logów code review.</li>
            <li>Zaimplementowano dodatkowe agenty: <code>traceability</code>, <code>risk_closure</code> i <code>soup_completeness</code> jako gotowe rozszerzenia.</li>
            <li>Udostępniono wyniki przez API FastAPI.</li>
            <li>Przygotowano dashboard i automatycznie generowany raport dowodowy.</li>
            <li>Dodano mechanizm potwierdzający źródło danych przez liczbę dokumentów, pola dokumentu i przykładowy log Sandmark.</li>
        </ul>
    </div>

    <h2>8. Następne kroki</h2>

    <div class="section-card">
        <ol>
            <li>
                Podłączyć rzeczywisty system zarządzania wymaganiami do kolekcji 
                <code>requirements</code>, aby metryka <code>traceability</code> była liczona na danych produkcyjnych.
            </li>
            <li>
                Podłączyć rzeczywisty rejestr ryzyk do kolekcji <code>risks</code>,
                aby metryka <code>risk_closure</code> pokazywała rzeczywisty stan zarządzania ryzykiem.
            </li>
            <li>
                Podłączyć rzeczywisty rejestr bibliotek zewnętrznych do kolekcji 
                <code>soup_register</code>, aby metryka <code>soup_completeness</code>
                mogła służyć do kontroli zgodności.
            </li>
            <li>
                Dodać filtrowanie wyników po projekcie, repozytorium, okresie czasu i typie komentarza.
            </li>
            <li>
                Dodać trendy porównawcze, np. ostatnie 30 dni względem poprzednich 30 dni.
            </li>
            <li>
                Dodać eksport raportu z poziomu dashboardu.
            </li>
        </ol>
    </div>

    <h2>9. Wniosek końcowy</h2>

    <div class="section-card">
        <p>
            Projekt QualityMetrics pokazuje, że dane generowane przez Sandmark można skutecznie
            przekształcić w metryki zarządcze. W aktualnej wersji raport prezentuje wyłącznie te wyniki,
            które są policzone bezpośrednio na rzeczywistych logach Sandmarka z kolekcji 
            <code>{safe(COLLECTION_REVIEW_LOGS)}</code>.
        </p>

        <p>
            Pozostałe trzy agenty są gotowe technicznie, ale wymagają podłączenia realnych źródeł
            organizacyjnych. Dzięki temu projekt jest przygotowany nie tylko jako demonstracja,
            ale jako baza do dalszej integracji z procesami jakości, wymagań, ryzyk i zgodności.
        </p>

        <div class="real-data-box">
            <strong>Najważniejsza konkluzja:</strong>
            realnie potwierdzona część systemu obejmuje analizę code review Sandmarka:
            <code>review_density</code> i <code>defect_escape</code>.
            Architektura pozostałych agentów jest gotowa do użycia po podłączeniu właściwych danych.
        </div>
    </div>

    <div class="footer">
        Raport wygenerowany automatycznie przez QualityMetrics · MongoDB Atlas · Sandmark · Seaborn
    </div>

</div>
</body>
</html>
"""

    return html


# ============================================================
# MAIN
# ============================================================

def main():
    db = get_db()

    review_docs = load_sandmark_reviews(db)

    review_density = calculate_review_density(review_docs)
    defect_escape = calculate_defect_escape(review_docs)

    evidence = build_real_data_evidence(review_docs)

    chart_paths = generate_real_sandmark_charts(
        review_density=review_density,
        defect_escape=defect_escape
    )

    html = render_report(
        review_density=review_density,
        defect_escape=defect_escape,
        evidence=evidence,
        chart_paths=chart_paths
    )

    with open(OUTPUT_HTML, "w", encoding="utf-8") as file:
        file.write(html)

    print(f"HTML report generated: {OUTPUT_HTML}")

    try:
        from weasyprint import HTML

        HTML(OUTPUT_HTML).write_pdf(OUTPUT_PDF)
        print(f"PDF report generated: {OUTPUT_PDF}")

    except Exception as error:
        print("PDF was not generated.")
        print("HTML report is ready and can be opened in browser.")
        print("To enable PDF export, install WeasyPrint:")
        print("pip install weasyprint")
        print(f"Details: {error}")


if __name__ == "__main__":
    main()