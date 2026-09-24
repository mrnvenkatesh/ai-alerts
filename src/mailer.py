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
  <style>
    body {
      margin: 0;
      padding: 0;
      background-color: #0f172a;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      color: #e2e8f0;
      -webkit-font-smoothing: antialiased;
    }
    .wrapper {
      width: 100%;
      background-color: #0f172a;
      padding: 30px 15px;
      box-sizing: border-box;
    }
    .container {
      max-width: 680px;
      margin: 0 auto;
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
    }
    .header {
      background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
      padding: 32px 28px;
      text-align: left;
    }
    .header-badge {
      display: inline-block;
      background: rgba(255, 255, 255, 0.2);
      color: #ffffff;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 1px;
      text-transform: uppercase;
      padding: 4px 10px;
      border-radius: 20px;
      margin-bottom: 12px;
    }
    .header h1 {
      margin: 0;
      color: #ffffff;
      font-size: 24px;
      font-weight: 800;
      line-height: 1.3;
    }
    .header p {
      margin: 8px 0 0 0;
      color: rgba(255, 255, 255, 0.85);
      font-size: 14px;
    }
    .section {
      padding: 24px 28px;
      border-bottom: 1px solid #334155;
    }
    .section-title {
      font-size: 14px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      color: #94a3b8;
      margin-top: 0;
      margin-bottom: 16px;
      display: flex;
      align-items: center;
    }
    .macro-box {
      background: rgba(59, 130, 246, 0.1);
      border-left: 4px solid #3b82f6;
      border-radius: 6px;
      padding: 16px 20px;
      color: #f1f5f9;
      font-size: 15px;
      line-height: 1.6;
    }
    .card {
      background: #0f172a;
      border: 1px solid #334155;
      border-radius: 8px;
      padding: 18px 20px;
      margin-bottom: 16px;
      transition: all 0.2s ease;
    }
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
    }
    .tag {
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      padding: 3px 8px;
      border-radius: 4px;
      display: inline-block;
    }
    .tag-Research { background: #1e1b4b; color: #818cf8; border: 1px solid #3730a3; }
    .tag-Product { background: #064e3b; color: #34d399; border: 1px solid #065f46; }
    .tag-OpenSource { background: #4c1d95; color: #c084fc; border: 1px solid #581c87; }
    .tag-Industry { background: #7c2d12; color: #fb923c; border: 1px solid #9a3412; }

    .source-name {
      font-size: 12px;
      color: #64748b;
      font-weight: 500;
    }
    .card-title {
      font-size: 16px;
      font-weight: 700;
      margin: 6px 0 10px 0;
      line-height: 1.4;
    }
    .card-title a {
      color: #38bdf8;
      text-decoration: none;
    }
    .card-title a:hover {
      text-decoration: underline;
    }
    .card-summary {
      font-size: 14px;
      color: #cbd5e1;
      line-height: 1.6;
      margin: 0;
    }
    .footer {
      padding: 24px 28px;
      background: #0f172a;
      text-align: center;
      font-size: 12px;
      color: #64748b;
    }
    .footer p {
      margin: 4px 0;
    }
    .meta-bar {
      display: inline-block;
      background: #1e293b;
      padding: 6px 14px;
      border-radius: 20px;
      font-size: 12px;
      color: #94a3b8;
      margin-bottom: 12px;
    }
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="container">
      
      <!-- Header -->
      <div class="header">
        <span class="header-badge">Executive Briefing</span>
        <h1>Daily GenAI Intelligence Digest</h1>
        <p>{{ content.date_str }}</p>
      </div>

      <!-- Section 1: Executive Macro Overview -->
      <div class="section">
        <div class="section-title">⚡ Executive Macro Overview</div>
        <div class="macro-box">
          {{ content.macro_overview }}
        </div>
      </div>

      <!-- Section 2: Top Breakthroughs -->
      <div class="section">
        <div class="section-title">🔥 Top AI Breakthroughs & Key Launches</div>
        {% for story in content.top_breakthroughs %}
        <div class="card">
          <div class="card-header">
            <span class="tag tag-{{ story.tag.replace(' ', '') }}">{{ story.tag }}</span>
            <span class="source-name">{{ story.source }}</span>
          </div>
          <div class="card-title">
            <a href="{{ story.url }}" target="_blank" rel="noopener">{{ story.headline }}</a>
          </div>
          <p class="card-summary">{{ story.summary }}</p>
        </div>
        {% endfor %}
      </div>

      {% if content.notable_releases %}
      <!-- Section 3: Notable Model & Code Releases -->
      <div class="section">
        <div class="section-title">📦 Notable Model & Code Releases</div>
        {% for release in content.notable_releases %}
        <div class="card">
          <div class="card-header">
            <span class="tag tag-{{ release.tag.replace(' ', '') }}">{{ release.tag }}</span>
            <span class="source-name">{{ release.source }}</span>
          </div>
          <div class="card-title">
            <a href="{{ release.url }}" target="_blank" rel="noopener">{{ release.headline }}</a>
          </div>
          <p class="card-summary">{{ release.summary }}</p>
        </div>
        {% endfor %}
      </div>
      {% endif %}

      <!-- Footer -->
      <div class="footer">
        <div class="meta-bar">
          Scanned {{ content.total_items_ingested }} articles across {{ content.total_sources_scanned }} feeds
        </div>
        <p>Daily GenAI Intelligence Aggregator &bull; Automated Briefing System</p>
        <p>Delivered via Scheduled Executive Pipeline</p>
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
            logger.info(f"Successfully delivered email digest to {len(self.recipient_list)} recipient(s): {', '.join(self.recipient_list)}")
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
