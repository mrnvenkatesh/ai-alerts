"""
Mailer Module for Daily GenAI News Aggregator.

Renders responsive HTML & plain-text email templates using Jinja2 and delivers via SMTP.
"""

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import os
import re
import smtplib
from typing import Optional

from jinja2 import Template

try:
    from src.synthesizer import DailyDigestContent
except ImportError:
    from synthesizer import DailyDigestContent

logger = logging.getLogger("Mailer")

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Daily GenAI Intelligence Briefing — {{ content.date_str }}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;700&family=Outfit:wght@500;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    body {
      margin: 0;
      padding: 0;
      background-color: #060813;
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      color: #e2e8f0;
      -webkit-font-smoothing: antialiased;
    }
    .wrapper {
      width: 100%;
      background-color: #060813;
      background-image: radial-gradient(circle at 50% 0%, rgba(99, 102, 241, 0.18) 0%, rgba(6, 8, 19, 0) 65%);
      padding: 40px 15px;
      box-sizing: border-box;
    }
    .container {
      max-width: 680px;
      margin: 0 auto;
      background: #0b101e;
      border: 1px solid rgba(99, 102, 241, 0.22);
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 25px 60px -15px rgba(0, 0, 0, 0.8), 0 0 35px rgba(99, 102, 241, 0.12);
    }
    .energy-bar {
      height: 3px;
      background: linear-gradient(90deg, #38bdf8 0%, #818cf8 50%, #c084fc 100%);
      width: 100%;
    }
    .header {
      background: linear-gradient(180deg, rgba(30, 27, 75, 0.6) 0%, rgba(11, 16, 30, 0.95) 100%);
      padding: 34px 32px 26px;
      text-align: left;
      border-bottom: 1px solid rgba(99, 102, 241, 0.15);
    }
    .header-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
    }
    .header-badge {
      display: inline-flex;
      align-items: center;
      background: rgba(99, 102, 241, 0.15);
      border: 1px solid rgba(99, 102, 241, 0.35);
      color: #a5b4fc;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 1.2px;
      text-transform: uppercase;
      padding: 5px 12px;
      border-radius: 20px;
    }
    .pulse-dot {
      display: inline-block;
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: #10b981;
      box-shadow: 0 0 8px #10b981;
      margin-right: 8px;
    }
    .system-pill {
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: #64748b;
      letter-spacing: 0.5px;
    }
    .header h1 {
      margin: 0;
      font-family: 'Outfit', sans-serif;
      color: #ffffff;
      font-size: 27px;
      font-weight: 800;
      line-height: 1.25;
      letter-spacing: -0.3px;
    }
    .gradient-text {
      background: linear-gradient(135deg, #38bdf8 0%, #818cf8 50%, #c084fc 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    .header-date {
      margin: 8px 0 0 0;
      color: #94a3b8;
      font-size: 14px;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .telemetry-strip {
      margin-top: 18px;
      padding-top: 16px;
      border-top: 1px solid rgba(255, 255, 255, 0.06);
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      font-size: 12px;
      color: #94a3b8;
      font-family: 'JetBrains Mono', monospace;
    }
    .telemetry-chip {
      background: rgba(15, 23, 42, 0.8);
      border: 1px solid rgba(148, 163, 184, 0.15);
      border-radius: 6px;
      padding: 4px 10px;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
    .telemetry-chip strong {
      color: #38bdf8;
    }
    .section {
      padding: 26px 30px;
      border-bottom: 1px solid rgba(99, 102, 241, 0.12);
    }
    .section-title {
      font-family: 'Outfit', sans-serif;
      font-size: 13px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 1.2px;
      color: #818cf8;
      margin-top: 0;
      margin-bottom: 18px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .section-title-icon {
      font-size: 15px;
    }
    .macro-box {
      background: linear-gradient(135deg, rgba(30, 41, 59, 0.6) 0%, rgba(15, 23, 42, 0.85) 100%);
      border: 1px solid rgba(56, 189, 248, 0.25);
      border-left: 4px solid #38bdf8;
      border-radius: 10px;
      padding: 20px 22px;
      color: #f1f5f9;
      font-size: 15px;
      line-height: 1.65;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    }
    .card {
      background: #0d1322;
      border: 1px solid rgba(148, 163, 184, 0.12);
      border-radius: 10px;
      padding: 20px 22px;
      margin-bottom: 16px;
      transition: all 0.2s ease;
      position: relative;
    }
    .card:hover {
      border-color: rgba(56, 189, 248, 0.35);
      background: #10172a;
    }
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
    }
    .tag {
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      padding: 3px 9px;
      border-radius: 5px;
      display: inline-block;
    }
    .tag-Research { background: rgba(99, 102, 241, 0.15); color: #a5b4fc; border: 1px solid rgba(99, 102, 241, 0.35); }
    .tag-Product { background: rgba(16, 185, 129, 0.15); color: #6ee7b7; border: 1px solid rgba(16, 185, 129, 0.35); }
    .tag-OpenSource { background: rgba(168, 85, 247, 0.15); color: #d8b4fe; border: 1px solid rgba(168, 85, 247, 0.35); }
    .tag-Industry { background: rgba(245, 158, 11, 0.15); color: #fcd34d; border: 1px solid rgba(245, 158, 11, 0.35); }
    .tag-LabRelease { background: rgba(244, 63, 94, 0.15); color: #fda4af; border: 1px solid rgba(244, 63, 94, 0.35); }

    .source-name {
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: #64748b;
      background: rgba(30, 41, 59, 0.6);
      padding: 3px 8px;
      border-radius: 4px;
      border: 1px solid rgba(148, 163, 184, 0.1);
    }
    .card-title {
      font-family: 'Outfit', sans-serif;
      font-size: 17px;
      font-weight: 700;
      margin: 6px 0 10px 0;
      line-height: 1.4;
    }
    .card-title a {
      color: #f8fafc;
      text-decoration: none;
      transition: color 0.15s ease;
    }
    .card-title a:hover {
      color: #38bdf8;
    }
    .card-title a .arrow {
      color: #38bdf8;
      display: inline-block;
      margin-left: 4px;
      font-weight: 400;
    }
    .card-summary {
      font-size: 14px;
      color: #94a3b8;
      line-height: 1.65;
      margin: 0;
    }
    .footer {
      padding: 30px 32px;
      background: #080c16;
      text-align: center;
      font-size: 12px;
      color: #64748b;
    }
    .github-banner {
      background: linear-gradient(135deg, rgba(30, 27, 75, 0.4) 0%, rgba(15, 23, 42, 0.7) 100%);
      border: 1px solid rgba(99, 102, 241, 0.25);
      border-radius: 12px;
      padding: 18px 20px;
      margin-bottom: 22px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      text-align: left;
    }
    .github-info {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .github-icon-circle {
      width: 36px;
      height: 36px;
      border-radius: 8px;
      background: rgba(99, 102, 241, 0.15);
      border: 1px solid rgba(99, 102, 241, 0.3);
      display: flex;
      align-items: center;
      justify-content: center;
      color: #a5b4fc;
      flex-shrink: 0;
    }
    .github-title {
      font-family: 'Outfit', sans-serif;
      color: #f1f5f9;
      font-size: 14px;
      font-weight: 700;
      margin: 0 0 2px 0;
    }
    .github-desc {
      color: #94a3b8;
      font-size: 12px;
      margin: 0;
    }
    .github-btn {
      background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%);
      color: #ffffff !important;
      text-decoration: none !important;
      font-family: 'Outfit', sans-serif;
      font-size: 12px;
      font-weight: 700;
      padding: 8px 16px;
      border-radius: 6px;
      white-space: nowrap;
      transition: all 0.2s ease;
      box-shadow: 0 2px 8px rgba(59, 130, 246, 0.35);
      display: inline-block;
    }
    .github-btn:hover {
      box-shadow: 0 4px 14px rgba(59, 130, 246, 0.5);
      transform: translateY(-1px);
    }
    .footer-note {
      margin: 6px 0;
      color: #64748b;
    }
    .footer-subnote {
      margin: 2px 0;
      font-size: 11px;
      color: #475569;
      font-family: 'JetBrains Mono', monospace;
    }
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="container">
      
      <!-- Top Energy Strip -->
      <div class="energy-bar"></div>

      <!-- Header -->
      <div class="header">
        <div class="header-top">
          <span class="header-badge">
            <span class="pulse-dot"></span>Autonomous AI Radar
          </span>
          <span class="system-pill">Gemini-Engineered</span>
        </div>
        <h1>Daily GenAI <span class="gradient-text">Intelligence Digest</span></h1>
        <p class="header-date">
          <span>⚡ {{ content.date_str }}</span>
          <span>&bull;</span>
          <span>Executive Intelligence Pipeline</span>
        </p>

        <!-- Telemetry Strip -->
        <div class="telemetry-strip">
          <span class="telemetry-chip">
            📡 Feeds: <strong>{{ content.total_sources_scanned }}</strong>
          </span>
          <span class="telemetry-chip">
            ⚡ Ingested: <strong>{{ content.total_items_ingested }}</strong>
          </span>
          <span class="telemetry-chip">
            🎯 Breakthroughs: <strong>{{ content.top_breakthroughs|length }}</strong>
          </span>
        </div>
      </div>

      <!-- Section 1: Executive Macro Overview -->
      <div class="section">
        <div class="section-title">
          <span class="section-title-icon">⚡</span>
          <span>Executive Macro Radar</span>
        </div>
        <div class="macro-box">
          {{ content.macro_overview }}
        </div>
      </div>

      <!-- Section 2: Top Breakthroughs -->
      <div class="section">
        <div class="section-title">
          <span class="section-title-icon">🔥</span>
          <span>Core AI Breakthroughs & Key Launches</span>
        </div>
        {% for story in content.top_breakthroughs %}
        <div class="card">
          <div class="card-header">
            <span class="tag tag-{{ story.tag.replace(' ', '') }}">{{ story.tag }}</span>
            <span class="source-name">{{ story.source }}</span>
          </div>
          <h3 class="card-title">
            <a href="{{ story.url }}" target="_blank" rel="noopener">{{ story.headline }} <span class="arrow">&rarr;</span></a>
          </h3>
          <p class="card-summary">{{ story.summary }}</p>
        </div>
        {% endfor %}
      </div>

      {% if content.notable_releases %}
      <!-- Section 3: Notable Model & Code Releases -->
      <div class="section">
        <div class="section-title">
          <span class="section-title-icon">📦</span>
          <span>Notable Model & Code Releases</span>
        </div>
        {% for release in content.notable_releases %}
        <div class="card">
          <div class="card-header">
            <span class="tag tag-{{ release.tag.replace(' ', '') }}">{{ release.tag }}</span>
            <span class="source-name">{{ release.source }}</span>
          </div>
          <h3 class="card-title">
            <a href="{{ release.url }}" target="_blank" rel="noopener">{{ release.headline }} <span class="arrow">&rarr;</span></a>
          </h3>
          <p class="card-summary">{{ release.summary }}</p>
        </div>
        {% endfor %}
      </div>
      {% endif %}

      <!-- Footer -->
      <div class="footer">
        
        <!-- GitHub Contribution Banner -->
        <div class="github-banner">
          <div class="github-info">
            <div class="github-icon-circle">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"></path>
              </svg>
            </div>
            <div>
              <p class="github-title">Open-Source AI Radar</p>
              <p class="github-desc">Interested in contributing to the code or adding sources?</p>
            </div>
          </div>
          <a href="https://github.com/mrnvenkatesh/ai-alerts" target="_blank" rel="noopener" class="github-btn">
            Contribute on GitHub &rarr;
          </a>
        </div>

        <p class="footer-note">Daily GenAI Intelligence Aggregator &bull; Automated Briefing System</p>
        <p class="footer-subnote">Delivered via Scheduled Executive Pipeline &bull; Asia/Kolkata</p>
      </div>

    </div>
  </div>
</body>
</html>
"""

PLAIN_TEXT_TEMPLATE = """DAILY GENAI INTELLIGENCE BRIEFING — {{ content.date_str }}
====================================================================

EXECUTIVE MACRO OVERVIEW
--------------------------------------------------------------------
{{ content.macro_overview }}

TOP BREAKTHROUGHS & KEY LAUNCHES
--------------------------------------------------------------------
{% for story in content.top_breakthroughs %}
[{{ story.tag.upper() }}] {{ story.headline }}
Source: {{ story.source }}
Link: {{ story.url }}
Summary: {{ story.summary }}
--------------------------------------------------------------------
{% endfor %}

{% if content.notable_releases %}
NOTABLE MODEL & CODE RELEASES
--------------------------------------------------------------------
{% for release in content.notable_releases %}
[{{ release.tag.upper() }}] {{ release.headline }}
Source: {{ release.source }}
Link: {{ release.url }}
Summary: {{ release.summary }}
--------------------------------------------------------------------
{% endfor %}
{% endif %}

RUN METADATA
--------------------------------------------------------------------
Ingested {{ content.total_items_ingested }} raw updates from {{ content.total_sources_scanned }} feeds.
Generated automatically by Daily GenAI Intelligence Aggregator.

CONTRIBUTE
--------------------------------------------------------------------
Interested in contributing to the code? https://github.com/mrnvenkatesh/ai-alerts
"""


class DigestMailer:
    """Renders and transmits HTML and plain text email briefings."""

    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_pass = os.getenv("SMTP_PASS", "")
        self.sender_email = (os.getenv("SENDER_EMAIL", "").strip()) or self.smtp_user or "digest@genai.local"
        raw_recipients = os.getenv("RECIPIENT_EMAIL", "")
        self.recipient_list = [r.strip() for r in re.split(r"[,;]", raw_recipients) if r.strip()]
        self.use_bcc = os.getenv("USE_BCC", "true").strip().lower() in ("true", "1", "yes")

    def render_html(self, content: DailyDigestContent) -> str:
        """Renders HTML email template."""
        template = Template(HTML_TEMPLATE)
        return template.render(content=content)

    def render_text(self, content: DailyDigestContent) -> str:
        """Renders plain text fallback email."""
        template = Template(PLAIN_TEXT_TEMPLATE)
        return template.render(content=content)

    def save_local_preview(self, content: DailyDigestContent, output_dir: str = "output") -> tuple[str, str]:
        """Saves rendered HTML and plain text files for local previewing."""
        os.makedirs(output_dir, exist_ok=True)
        safe_date = content.date_str.replace(" ", "_").replace(",", "").lower()
        html_path = os.path.join(output_dir, f"digest_{safe_date}.html")
        text_path = os.path.join(output_dir, f"digest_{safe_date}.txt")

        html_body = self.render_html(content)
        text_body = self.render_text(content)

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_body)

        with open(text_path, "w", encoding="utf-8") as f:
            f.write(text_body)

        logger.info(f"Saved local HTML preview: {html_path}")
        logger.info(f"Saved local text preview: {text_path}")
        return html_path, text_path

    def send_digest(self, content: DailyDigestContent, dry_run: bool = False) -> bool:
        """Sends briefing via SMTP or saves to disk if dry_run=True or SMTP unconfigured."""
        html_body = self.render_html(content)
        text_body = self.render_text(content)

        if dry_run or not self.recipient_list or not self.smtp_host:
            logger.info("Dry-run mode active or SMTP credentials missing. Writing output to local files.")
            self.save_local_preview(content)
            return True

        subject = f"Daily GenAI Intelligence Briefing — {content.date_str}"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.sender_email

        # If BCC is enabled and there are multiple recipients, address the 'To' header
        # to the sender so recipients do not see each other's email addresses.
        if self.use_bcc and len(self.recipient_list) > 1:
            msg["To"] = self.sender_email
        else:
            msg["To"] = ", ".join(self.recipient_list)

        part1 = MIMEText(text_body, "plain", "utf-8")
        part2 = MIMEText(html_body, "html", "utf-8")
        msg.attach(part1)
        msg.attach(part2)

        try:
            logger.info(f"Connecting to SMTP server {self.smtp_host}:{self.smtp_port}...")
            server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=15)
            server.ehlo()

            # Start TLS if port is 587
            if self.smtp_port == 587:
                server.starttls()
                server.ehlo()

            if self.smtp_user and self.smtp_pass:
                server.login(self.smtp_user, self.smtp_pass)

            server.sendmail(self.sender_email, self.recipient_list, msg.as_string())
            server.quit()
            delivery_mode = "BCC" if (self.use_bcc and len(self.recipient_list) > 1) else "standard"
            logger.info(f"Successfully delivered email digest ({delivery_mode}) to {len(self.recipient_list)} recipient(s): {', '.join(self.recipient_list)}")
            return True
        except Exception as e:
            logger.error(f"Failed to deliver email via SMTP: {e}")
            logger.info("Saving fallback HTML/text files locally.")
            self.save_local_preview(content)
            return False


if __name__ == "__main__":
    from datetime import datetime

    # Test mailer rendering
    try:
        from src.synthesizer import DailyDigestContent, StoryBrief
    except ImportError:
        from synthesizer import DailyDigestContent, StoryBrief

    sample_content = DailyDigestContent(
        date_str=datetime.now().strftime("%B %d, %Y"),
        macro_overview="Major AI labs push forward with reasoning advancements and open model weights for multi-modal applications.",
        top_breakthroughs=[
            StoryBrief(
                headline="OpenAI Releases Advisory Group Guidelines",
                url="https://openai.com/index/advisory-group-on-mathematics-and-ai",
                source="OpenAI News",
                tag="Product",
                summary="OpenAI announced a new independent advisory panel focused on math and AI safety standards.",
            ),
            StoryBrief(
                headline="Pruning LLMs via Ising Optimization",
                url="https://huggingface.co/blog/pruning-llms",
                source="Hugging Face Blog",
                tag="Research",
                summary="Researchers present physics-inspired pruning techniques reducing parameter count by 30% with minimal loss.",
            ),
        ],
        total_sources_scanned=5,
        total_items_ingested=42,
    )

    mailer = DigestMailer()
    mailer.save_local_preview(sample_content)
