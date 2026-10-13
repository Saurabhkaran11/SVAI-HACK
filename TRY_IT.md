# Try WhyBot with real-world data

**Live app:** https://whybot-ytcu.onrender.com
**Code:** https://github.com/Saurabhkaran11/SVAI-HACK

No sign-up and no install. Add any public page or file, wait about a minute, then ask questions about it.
Every source below was added to the live app and answered correctly on Oct 12, 2026.

> **Public demo rules:** everyone shares one brain, so only add **public** data, never confidential company files.
> Anything you add is cleared when the server restarts. Limits: 12 questions per minute and 20 uploads per hour per visitor.
> On the free plan the first visit after 15 idle minutes takes about a minute to wake up.

---

## 1. Five-minute test (built-in sample company)

The app starts with a sample company brain: an architecture decision, a meeting, a Slack thread, a post-mortem and an onboarding guide.

| Step | Go to | Type or click | What you should see |
|---|---|---|---|
| 1 | **Blast Radius** | `Deprecate payments-api-v1 next month` | High risk (100), 6+ affected systems, 3 owning teams, a past incident (INC-0312), a rollout checklist, draft heads-up messages |
| 2 | **Ask the Brain** | `Why are we migrating to payments v2?` | Plain search next to WhyBot's answer, with sources and relationships |
| 3 | **Ask the Brain** | Change "Asking as" to **Manager**, ask `Who should I talk to before changing billing-service?` | An answer pitched for a manager, naming the owner |
| 4 | **Graph Explorer** | Click `payments-api-v1`, then **Check blast radius** | Its connections, then the full impact report |
| 5 | **Blast Radius** | `Migrate auth-service to a new rate-limit-config` | Medium risk (58) |

---

## 2. Real-world tests (public post-mortems and docs)

For each one: open **Knowledge**, paste the URL under **Add a web page**, click **Add**, wait 1–2 minutes, then ask the questions on **Ask the Brain**.

| Real source | URL to paste | Questions to ask |
|---|---|---|
| GitHub outage, Oct 21, 2018 | `https://github.blog/news-insights/company-news/oct21-post-incident-analysis/` | `What caused the GitHub outage on October 21 2018 and which systems were affected?` · `How long did recovery take and why?` |
| Amazon S3 outage, Feb 28, 2017 | `https://aws.amazon.com/message/41926/` | `What caused the Amazon S3 outage in us-east-1 in February 2017?` · `What did AWS change to stop it happening again?` |
| GitLab database incident, Jan 31, 2017 | `https://about.gitlab.com/blog/2017/02/10/postmortem-of-database-outage-of-january-31/` | `How did GitLab lose production data and what did they change?` · `Which backups failed and why?` |
| Slack outage, Jan 4, 2021 | `https://slack.engineering/slacks-outage-on-january-4th-2021/` | `Why did Slack go down on January 4 2021?` · `Which systems were involved?` |
| HydraDB documentation | `https://docs.hydradb.com/` | `What is the difference between memories and knowledge in HydraDB?` · `How do I query the context graph?` |

**Cross-document test:** after adding two or more post-mortems, ask
`What do the GitHub and GitLab incidents have in common, and what should my team check before a database failover change?`

**Blast Radius on real data:** give HydraDB about 5 minutes to extract relationships from a new page, then try
`Change the database failover settings` or `Run maintenance on the primary database cluster`.
It should list the related past incidents; affected systems appear once their relationships are indexed.

---

## 3. Test with your own data

- **Your own public pages:** any company engineering blog, public status-page incident report, product docs or GitHub README (paste the URL).
- **Files:** drag in a PDF, Markdown, TXT, CSV or JSON file up to 10 MB: meeting notes, an architecture decision record, a runbook, a Slack or Jira export you are allowed to share publicly.
- **Good questions to ask:** *Why did we decide X?* · *Who owns Y?* · *What breaks if we change Z?* · *What went wrong last time we touched Z?*
- **Your profile:** click the avatar (top right) and set your name and role; answers adapt to who is asking.

---

## 4. Test the API directly

Interactive docs are under **Settings → API reference**, or use `curl`:

```bash
# Add a public page
curl -X POST https://whybot-ytcu.onrender.com/api/url \
  -H "Content-Type: application/json" \
  -d '{"url":"https://aws.amazon.com/message/41926/"}'

# Ask a question (wait about a minute after adding)
curl -X POST https://whybot-ytcu.onrender.com/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"What caused the Amazon S3 outage in February 2017?","graph":true}'

# Blast radius of a planned change
curl -X POST https://whybot-ytcu.onrender.com/api/impact \
  -H "Content-Type: application/json" \
  -d '{"change":"Deprecate payments-api-v1 next month"}'
```

---

## 5. If something looks off

| You see | Why | What to do |
|---|---|---|
| The page takes about a minute to load | The free server was asleep | Wait; it stays fast while people use it |
| "The AI writer is busy right now" | The shared free AI quota (Groq) is used up for this minute | Ask again in a minute; you still get the evidence summary |
| "You're sending questions faster than this shared demo allows" | Per-visitor limit | Wait the number of seconds shown |
| A page you added is gone | The server restarted (free plan) | Add it again |
| A URL fails to add | Some sites block automated fetching or are very large | Try another page, or save it as PDF and upload the file |
| Blast Radius shows 0 systems for new data | Relationships are still being extracted | Wait about 5 minutes and try again |

Run it locally instead: see [README.md](README.md) (one-click `WhyBot.command` on macOS, `start.sh` / `start.bat` elsewhere).
