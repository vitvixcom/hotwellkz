# Setup conversion tracking + warm-pixel audience


**One prompt sets up everything you need to track form leads and retarget warm visitors. Zero clicks in the Google Ads UI.**


## What this does, end-to-end


1. Asks you a handful of questions (lead value, domain, ad group to attach to, etc.)
2. Creates the conversion action in Google Ads via the API
3. Writes the resulting tag IDs into your Next.js `.env.local`
4. Verifies the global tag and conversion ping are already wired (or wires them if missing)
5. Runs a Playwright test that fills the form, submits it, and confirms the conversion fires
6. Creates a "warm pixel" audience = anyone who has hit any page on your site (last 540 days)
7. Attaches that audience to your existing SKAG ad group as an RLSA observation, with a +50% bid modifier


Claude time: ~2 minutes. Your time: ~30 seconds answering questions.


## What this does NOT do (intentionally)


- **Phone call conversion tracking** — separate SOP. Set up form tracking first; phone tracking once you confirm leads are flowing.
- **Display retargeting campaign** — separate SOP (`display-retargeting-campaign.md`). RLSA on your existing SKAG is the higher-ROI move and uses the same audience this SOP creates.
- **Enhanced conversions** (hashed email/phone matching) — separate SOP. Adds ~5% match rate; not worth the setup time on day one.
- **Server-side tracking** (gtag → Cloudflare worker → Google) — Ch 12 of the masterclass.


---


## Prerequisites (check these before running)


Claude must verify ALL of these before asking the user any questions or running any API calls. If any fails, stop and report what's missing — don't try to work around it.


- [ ] Google Ads account with API access — `python3 google-ads-api-setup/test_connection.py` returns success
- [ ] `google-ads.yaml` or `.env` in the project root with valid credentials
- [ ] An existing campaign + ad group you want to attach the audience to (built via `build-your-first-skag.md`). If you don't have one yet, this SOP will still create the conversion action and audience — it'll just skip step 7.
- [ ] Next.js landing pages site at `landing-pages/` with `<GoogleTags />` component already in `app/layout.tsx`
- [ ] **Dev server running** on a known port (typically `localhost:6544`) OR Claude has permission to start it. If unsure, ask the user.
- [ ] **A verification method** — at least ONE of the following must be available, or step 4 can't run:
 - **(Preferred · automated)** Playwright installed in `landing-pages/`: run `cd landing-pages && npx --no-install playwright --version`. If it returns "not installed," run `npm install -D playwright && npx playwright install chromium` first.
 - **(Fallback · manual)** Google Tag Assistant Chrome extension — install from **https://tagassistant.google.com/**. If Playwright isn't installed and the user doesn't want to install it, Claude must instruct them to install Tag Assistant and walk through the manual verify (see Step 4b below) before proceeding to Step 5.


If any are missing, Claude will detect and either offer to set them up or stop with a clear message.


---


## How to invoke


In Claude Code, paste this:


> *"Run the conversion tracking + warm-pixel audience SOP at `prompts/setup-conversion-tracking-and-audience.md`. Ask me the questions, then do everything end-to-end."*


That's the whole interaction. Claude reads this file and executes.


---


## Questions Claude will ask you


Claude must ask all of these BEFORE running any API calls. If you've answered them before in this session, Claude can pre-fill but should still confirm.


### 1. Domain
> *"What's the domain of your landing page site? (e.g., automatable.co)"*


Used for: matching URL patterns in the audience rule, naming the audience.


### 2. Google Ads customer ID
> *"What's your Google Ads customer ID? (10 digits, no dashes — e.g., 7720948031)"*


Used for: every API call. Reject if not 10 digits.


### 3. Conversion action name
> *"What should I name the conversion action? (default: 'Lead · Form Submit')"*


Used for: the conversion's display name in Google Ads. Show next to it: *"You can rename anytime in the UI later — this is just the initial label."*


### 4. Lead value
> *"What's a lead worth to you, in dollars? This is your **average deal size × close rate**, not your top deal. For a plumber averaging $500/job at 40% close, that's $200. For a B2B SaaS at $10K ACV and 20% close, that's $2,000. Smart Bidding uses this number to decide what to bid — so it doesn't need to be perfect, just directionally honest."*


Validate: must be a positive number. Reject zero (defeats the purpose of value-based bidding).


### 5. Currency
> *"What currency? (default: matches your Google Ads account)"*


Used for: `default_currency_code` on the conversion action. Default to the account's currency if you can query it; otherwise prompt.


### 6. Ad group ID for RLSA attachment
> *"Which ad group should the warm-pixel audience attach to? (numeric ID, or 'skip' to set up the conversion + audience without attaching). You can find this in the Google Ads UI under your campaign, or by running `python google-ads-api-setup/verify_skag.py`."*


If they answer 'skip': skip step 7, finish at step 6. Tell them: *"Audience created but not attached. You can attach later by re-running this SOP and providing the ad group ID."*


### 7. Bid modifier for warm pixel
> *"Bid modifier when a warm pixel user re-searches? Default +50% — meaning if your normal max CPC is $2, you'll bid up to $3 on someone who's already been to your site. Higher = more aggressive. Stay between +25% and +100%."*


Validate: between -90 and +900. Warn outside +25 to +100.


### 8. Final confirmation
> *"Confirm: I'm about to create a conversion action named '{name}' valued at ${value} {currency}, plus a warm-pixel audience for {domain} attached to ad group {ad_group_id} with a +{modifier}% bid. This makes live changes to Google Ads account {customer_id}. Proceed? (yes/no)"*


If 'no': stop immediately, explain nothing has happened, ask what they'd like to change.


---


## Step-by-step execution (what Claude does after the user confirms)


### Step 1: Create the conversion action


Use `google-ads-api-setup/setup_conversion_action.py`. If the script doesn't exist, generate it using `ConversionActionService.MutateConversionActions`. Key fields:


```python
op.create.name = conversion_name
op.create.category = ConversionActionCategoryEnum.SUBMIT_LEAD_FORM
op.create.type_ = ConversionActionTypeEnum.WEBPAGE
op.create.status = ConversionActionStatusEnum.ENABLED
op.create.value_settings.default_value = lead_value
op.create.value_settings.default_currency_code = currency
op.create.value_settings.always_use_default_value = False  # Allow per-event overrides
op.create.counting_type = ConversionActionCountingTypeEnum.ONE_PER_CLICK
op.create.click_through_lookback_window_days = 90
op.create.view_through_lookback_window_days = 1
op.create.primary_for_goal = True  # Used for bidding optimization
op.create.attribution_model_settings.attribution_model = (
   AttributionModelEnum.GOOGLE_ADS_DATA_DRIVEN
)
```


After mutate, fetch the conversion action back to get `tag_snippets`. Extract:
- The `AW-XXXXXXXXXX` from the global tag
- The `AW-XXXXXXXXXX/AbC-D_efGhIjKlMnOp` conversion label from the event snippet


Print both to stdout so you can see them.


### Step 2: Wire IDs into the Next.js site


Write `landing-pages/.env.local`:


```
NEXT_PUBLIC_GTAG_ID=AW-XXXXXXXXXX
NEXT_PUBLIC_GADS_CONVERSION_LABEL=AW-XXXXXXXXXX/AbC-D_efGhIjKlMnOp
```


If `.env.local` already has these keys, **update the values, don't append.** If they're set and different from the new ones, ask the user: *"Existing tag ID found. Replace with the new one, or keep existing?"*


### Step 3: Verify the site-side wiring is in place


Check that these files exist and contain the expected exports. If any is missing, generate from the template in [landing-pages/src/components/GoogleTags.tsx](landing-pages/src/components/GoogleTags.tsx):


- `landing-pages/src/components/GoogleTags.tsx` — loads gtag.js from `NEXT_PUBLIC_GTAG_ID`
- `landing-pages/src/lib/analytics.ts` — exports `trackConversion()` reading `NEXT_PUBLIC_GADS_CONVERSION_LABEL`
- `landing-pages/src/app/layout.tsx` — mounts `<GoogleTags />` in `<body>`
- `landing-pages/src/app/thank-you/ConversionPing.tsx` — calls `trackConversion()` on mount
- `landing-pages/src/components/LeadForm.tsx` — routes to `/thank-you?label=...` on successful submit


If everything is in place, log: *"Site is already wired for gtag — only the env vars changed."*


### Step 4a: Verify the conversion fires (automated · preferred)


Run `landing-pages/scripts/verify-conversion-fires.ts` via Playwright. If the script doesn't exist, generate one that:


1. Starts the Next.js dev server on a known port (or assumes one is already running on `localhost:6544`)
2. Opens the first landing page (e.g., `/emergency-plumber`)
3. Fills ALL required fields on the form — read the form config to know which fields are required; don't assume just name/email/phone
4. Submits the form
5. Waits for the redirect to `/thank-you?label=...`
6. Asserts a network request was made to `googletagmanager.com` or `google-analytics.com` with `data=event%3Dconversion` (or `en=conversion`) in the query string
7. Asserts the `send_to` parameter matches the conversion label written in step 2


Exit code 0 = pass. Exit code 1 = fail with a specific reason.


If the test fails because the form submission errored (e.g., `/api/lead` returned 4xx), that's NOT a tag bug — that's a form-input-validation bug surfaced by the test. Fix the test's form-filling to satisfy validation, then re-run.


### Step 4b: Verify the conversion fires (manual · Tag Assistant fallback)


If Playwright isn't installed and the user opted for the manual path, walk them through these exact steps:


1. **Install the Tag Assistant Chrome extension**: https://tagassistant.google.com/ → "Add to Chrome"
2. **Restart the dev server** (`Ctrl+C` then `npm run dev`) so the new `.env.local` values load
3. **Hard reload** the landing page (`Cmd+Shift+R` / `Ctrl+Shift+R`)
4. **Click the Tag Assistant icon** → "Add domain" → enter the landing page URL → "Connect"
5. **Click "Start a new test"** — a fresh tab opens with debugging enabled
6. **Fill the form with real-looking data** (the form rejects junk)
7. **Submit**
8. **Back to Tag Assistant** → Hits Sent panel — look for the conversion name (the name you gave it in step 1, e.g., `Demo 2.0 Delete`)


**Expected**: the conversion name appears once (in production) or twice (in dev, due to React Strict Mode — both count as one in Google's dedup).


**If the conversion name doesn't appear**:
- Confirm `Console (0)` — any errors here would point to the cause
- Confirm "Source: On-page gtag('config')" — if missing, the global tag isn't loading
- Confirm the AW-ID matches what's in `.env.local`


**If the conversion does appear**: paste the Tag Assistant output into Claude with "did it fire?" Claude reads the events, confirms, and proceeds to Step 5.


In both 4a and 4b: if verification fails, **stop and report.** Don't proceed to steps 5-7 with a broken tag.


### Step 5: Create the warm-pixel audience


Use `google-ads-api-setup/setup_warm_pixel_audience.py`. If missing, generate using `UserListService.MutateUserLists` with a `RuleBasedUserListInfo`:


```python
op.create.name = f"Warm pixel · all visitors · {domain} · 540d"
op.create.description = (
   f"Anyone who has visited any page on {domain} in the last 540 days. "
   "Populated automatically by the global gtag we just installed."
)
op.create.membership_status = UserListMembershipStatusEnum.OPEN
op.create.membership_life_span = 540  # max allowed


# The rule: URL contains the domain
rule_item = UserListRuleItemInfo()
rule_item.name = "url__"  # special name for URL field
rule_item.string_rule_item.operator = UserListStringRuleItemOperatorEnum.CONTAINS
rule_item.string_rule_item.value = domain


rule_item_group = UserListRuleItemGroupInfo()
rule_item_group.rule_items.append(rule_item)


op.create.rule_based_user_list.flexible_rule_user_list.inclusive_operands.append(
   create_flexible_operand_from_group(rule_item_group, lookback_days=540)
)
op.create.rule_based_user_list.flexible_rule_user_list.inclusive_rule_operator = (
   UserListFlexibleRuleOperatorEnum.AND
)
```


**Why "any page on the domain" and not "specific page"?** This SOP intentionally creates a broad audience. Anyone who hit your site is warm — doesn't matter how they got there. Narrowing to "people who clicked an ad first" cuts the pool by 70-90%, which is fatal for low-traffic accounts. If the user wants to narrow later, they can run `narrow-warm-pixel-audience.md` (separate SOP).


After creating, save the resource name (e.g., `customers/7720948031/userLists/12345`) for step 7.


### Step 6: Wait for the audience to register


Print to the user:
> *"Audience created. It will populate automatically as people visit {domain}. Audience size hits zero on day one and grows as traffic comes in — expect ~24-72 hours for the first members to appear in Google Ads UI. This is normal."*


### Step 7: Attach the audience to the SKAG ad group (skip if user chose 'skip')


Use `AdGroupCriterionService.MutateAdGroupCriteria`:


```python
op.create.ad_group = f"customers/{customer_id}/adGroups/{ad_group_id}"
op.create.user_list.user_list = user_list_resource_name
op.create.bid_modifier = 1.0 + (bid_modifier_pct / 100)  # e.g., 1.5 for +50%
op.create.status = AdGroupCriterionStatusEnum.ENABLED
# No need to set type — inferred from user_list field
```


For RLSA, the **ad group targeting setting** also needs to be Observation mode (not Targeting), or this restricts the ad group to ONLY the warm audience. Verify the ad group's targeting setting via `AdGroupService.GetAdGroup` before attaching. If it's set to Targeting (restrictive), change it to Observation.


### Step 8: Report results


Print to the user:


```
✓ Conversion action created: AW-XXXXXXXXXX/XXXXXXX
✓ Tag IDs written to landing-pages/.env.local
✓ Site verification: PASS (conversion fires on form submit)
✓ Warm-pixel audience created: customers/.../userLists/XXXXX
✓ Audience attached to ad group XXXXXXXXX as +50% bid observation


Next steps:
1. Check Google Ads UI in 24-48h to confirm conversion status flips to "Recording conversions"
2. Audience will populate as real traffic hits {domain}
3. RLSA bid adjustments will start firing once the audience has ~100 members
```


---


## Why the broad audience (vs "people who clicked your ad")


You will be tempted to narrow the audience to "people who came from your ad." Don't. Two reasons:


**1. Small audiences don't optimize.** Google Ads RLSA bid modifiers only fire when an audience has ~100 active members. Most service business landing pages get fewer than 100 ad clicks per month in the first 90 days. If you gate the audience by "came from ad," your pool will be too small to use for the first quarter.


**2. Warm is warm.** Someone who hit your site via organic search, a referral, or direct traffic is just as warm as someone who hit it via your ad. They've seen your brand, your offer, your reviews. If they're searching again, you want them — regardless of how they got there the first time.


**The narrow version is documented in `narrow-warm-pixel-audience.md`** for the day you have enough traffic to slice further. Until then, broad is correct.


---


## Common failure modes and how to handle them


### "INVALID_TAG_FOR_PERSONALIZED_ADS"
Cause: account doesn't have personalized advertising enabled.
Fix: have the user enable it in Google Ads UI under Admin → Preferences. Document this in the error message.


### "USER_LIST_NOT_ELIGIBLE"
Cause: account hasn't accepted the Customer Match policy.
Fix: have the user accept the policy in Google Ads UI under Tools → Audience Manager. Re-run the SOP after acceptance.


### Verification step fails: no conversion request in network
Most likely causes, in order:
1. Dev server cached old `.env.local` → restart `npm run dev`
2. Ad blocker active in Playwright's browser → run with `--disable-extensions` (default in headless)
3. `<GoogleTags />` not in layout.tsx → check the file
4. `trackConversion()` not called on `/thank-you` → check `ConversionPing.tsx`


### Audience attach fails with "TARGETING_SETTING_CONTAINS_INVALID_CRITERION_TYPE_GROUP"
Cause: ad group's targeting setting doesn't allow USER_LIST criteria.
Fix: update the ad group's targeting setting to allow USER_LIST in Observation mode. The script should handle this automatically (see step 7) — if it doesn't, fall back to UI.


---


## Files this SOP creates or modifies


| File | Action |
|---|---|
| `google-ads-api-setup/setup_conversion_action.py` | Created if missing |
| `google-ads-api-setup/setup_warm_pixel_audience.py` | Created if missing |
| `landing-pages/.env.local` | Created/updated with new IDs |
| `landing-pages/scripts/verify-conversion-fires.ts` | Created if missing |
| `landing-pages/src/components/GoogleTags.tsx` | Verified (created if missing) |
| `landing-pages/src/lib/analytics.ts` | Verified (created if missing) |
| `landing-pages/src/app/thank-you/ConversionPing.tsx` | Verified (created if missing) |


Nothing else is touched. The SOP is idempotent — running it twice with the same answers should not create duplicate conversion actions (Claude should check for an existing one with the same name first).


---


## Last note for Claude


Before running anything against the live Google Ads API, **show the user a one-line summary of what's about to happen and require explicit "yes" to proceed.** This makes live changes to a paid advertising account — there's no undo button if you create the wrong thing.


After completion, save the conversion label and audience resource name to a runlog at `prompts/runlogs/conversion-tracking-{date}.md` so the user has a record.





