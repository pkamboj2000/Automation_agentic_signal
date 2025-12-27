# Sample Inputs and Outputs

This document shows end-to-end examples of the re-engagement agent in action.

## Scenario A: Gmail Traction Signal

### Input

**Source**: Gmail inbox

**Email metadata**:
- From: maya.patel@northwind.ai
- Subject: Quick update - big milestone
- Date: December 1, 2025

**Email body**:
```
Hi Alex,

Hope you are well. Just wanted to share some exciting news. We closed our first Fortune 100 design partner last week. It is a major financial services company and they are piloting our compliance automation platform across their RegTech team.

We are also starting to build out the sales org. Posted our first Head of Sales role yesterday.

Would love to catch up if you have time. I remember you mentioned this was the kind of milestone that would make sense to reconnect.

Best,
Maya
```

**User profile** (from database):
- Name: Alex Chen
- Fund: Sago Ventures
- Thesis keywords: usage growth, product-led, efficient acquisition, compliance automation
- Tone: concise, direct, founder-friendly
- Availability: Tuesday 10am-1pm PT, Thursday 8am-12pm PT

**Past interaction** (from database):
- Date: September 10, 2025
- Outcome: pass_for_now
- Notes: "Team is strong (ex-Google, ex-Stripe). Product is pre-PMF, focused on compliance automation using LLMs. Too early for current fund stage requirements."
- Follow-up trigger: "enterprise pilot secured"

### Processing

**Signals detected**:
1. `{type: traction, title: "Fortune 100 pilot secured", confidence: 0.88}`
2. `{type: hiring, title: "Head of Sales role posted", confidence: 0.72}`

**Policy evaluation**:
- Confidence check: 0.88 > 0.6 threshold (pass)
- Trigger match: "Fortune 100 design partner" matches "enterprise pilot secured" (pass)
- Cooldown: 82 days since last interaction (pass)

**Decision**: Re-engage

### Output

**Planned actions**:
1. Draft personalized re-engagement email (requires approval)
2. Attach SOC2 readiness template (auto)
3. Offer sales candidate intros from network (requires approval)
4. Log to CRM (auto)

**Generated outreach**:
```
Hi Maya,

Congrats on the Fortune 100 pilot. That is exactly the kind of traction we talked about back in September.

I noticed you are also hiring your first sales lead. If helpful, I can connect you with a few enterprise sales folks from the portfolio who have sold into financial services. Also happy to share our SOC2 playbook since enterprise buyers tend to ask about that early.

I have time Tuesday 10am-1pm PT or Thursday 8am-12pm PT if you want to catch up. Let me know what works.

Best,
Alex
```

---

## Scenario B: Slack Need Signal

### Input

**Source**: Slack workspace (portfolio channel)

**Message metadata**:
- Channel: #founders
- User: @maya (matched to Northwind AI via user lookup)
- Timestamp: December 18, 2025

**Message content**:
```
Does anyone have a good SOC2 readiness checklist? Our enterprise buyer is asking about our security posture and I want to make sure we do not miss anything.
```

### Processing

**Signals detected**:
1. `{type: need, title: "SOC2 readiness help requested", confidence: 0.75}`

**Policy evaluation**:
- Confidence: 0.75 > 0.6 (pass)
- Trigger match: SOC2 is related to enterprise readiness; indirect match to "enterprise pilot" context (pass)
- Cooldown: 17 days since last signal (within same re-engagement window)

**Decision**: Add to existing re-engagement plan

### Output

**Additional action**:
- Share SOC2 template via Slack DM (auto, since it is a direct resource fulfillment)

**Slack DM generated**:
```
Hey Maya, saw your ask in #founders. Here is the SOC2 readiness checklist we share with portfolio companies: [link]. Also happy to connect you with our security advisor who has helped a few teams through their first audit. Let me know if that would be useful.
```

---

## Scenario C: Low-Confidence Signal (No Action)

### Input

**Source**: Gmail inbox

**Email metadata**:
- From: newsletter@techcrunch.com
- Subject: This week in AI startups

**Email body**:
```
...Northwind AI was mentioned in a roundup of compliance automation startups to watch...
```

### Processing

**Signals detected**:
1. `{type: traction, title: "Press mention in TechCrunch roundup", confidence: 0.42}`

**Policy evaluation**:
- Confidence: 0.42 < 0.6 threshold (fail)

**Decision**: No action. Signal logged but does not trigger re-engagement.

---

## Scenario D: Risk Signal (Flag for Review)

### Input

**Source**: LinkedIn (via news scrape)

**Content**:
```
Northwind AI CTO leaves company to join Google DeepMind.
```

### Processing

**Signals detected**:
1. `{type: executive_change, title: "CTO departure to Google", confidence: 0.81}`
2. `{type: risk, title: "Key technical leader exit", confidence: 0.76}`

**Policy evaluation**:
- Risk signals do not trigger outreach but are flagged for review

**Decision**: No outreach. Flag for investor review.

### Output

**Action**:
- Create internal note: "Northwind AI CTO departed. Review before next outreach."
- Add to portfolio risk dashboard
