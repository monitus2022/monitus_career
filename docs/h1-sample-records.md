# H1 sample records — 20 from the first live dry run (human review)

Source run: `runs_test/reports/2026-11-02.json` (2026-11-02T10:29:30+0800); release: dry-run over the two
untracked LIVE captures (`fixtures/hkgov_quickview.html`, `fixtures/jobsdb_cards.html`).
Fields are server-side only (no profile scoring yet — `profile.yaml` is the
human's H2 step). Everything below is scraped public job data; nothing
personal is involved (framing per design doc §1).

Field null-rates are *expected* empties (source omitted the field), not bugs — flagged here so the human doesn't misread them:
- hkgov: company is null (anonymized in the quickview payload), posted_date null (SSR quickview has no listing date). districts 60 % null = row truly has no location.
- jobsdb: salary 73.3 % null = employer didn't post a salary on the card.

## What to check (H1 = human eyeball pass)
1. Titles/companies look real and are correctly extracted (no HTML debris).
2. Districts: `districts` should be plausible HK districts for the raw location.
3. Salary: `salary_min/max` should match `salary_raw` (month-equiv applied).
4. Anything that looks wrong → tell the agent; adapters get fixed before the
   next live run (caps allow 1－2 recaptures/day).

## Coverage report (from 2026-11-02.json)

| source | records | salary_raw null-rate | districts null-rate | dropped |
|---|---|---|---|---|
| hkgov | 20 | 0 % | 60 % (quickview shows no location for most rows) | 0 |
| jobsdb | 30 | 73.3 % (SSR omits salary unless employer posts one) | 3.3 % | 0 |

## The 20 records (first 20 of payload, mixed sources)

| # | source | title | company | salary_raw | districts | posted |
|---|---|---|---|---|---|---|
| 1 | hkgov | Customer Due Diligence Officer (SME / Commercial Banking) | — | $22,000 - $43,000 per month | — | — |
| 2 | hkgov | Claims Executive (P&I and FD&D)(Asia Pacific) | — | $60,000 - $90,000 per month | — | — |
| 3 | hkgov | General Service Attendant | — | $70 per hour | — | — |
| 4 | hkgov | (Senior) Customer Service Asst. (Wanchai)(9 Hrs Day Shift) | — | $17,000 - $19,000 per month | Wan Chai | — |
| 5 | hkgov | Refrigeration / AC Mechanics / Technician (Intermediate) | — | $25,000 - $39,000 per month | — | — |
| 6 | hkgov | Repair / Maintenance Technician | — | $18,000 - $21,000 per month | — | — |
| 7 | hkgov | Technician | — | $21,500 - $23,600 per month | — | — |
| 8 | hkgov | Club Receptionist | — | $16,000 - $17,000 per month | Wan Chai | — |
| 9 | hkgov | Workshop Assistant / Factory Assistant | — | $16,500 - $20,000 per month | — | — |
| 10 | hkgov | Building Supervisor | — | $24,000 - $26,000 per month | Sha Tin | — |
| 11 | hkgov | Horticultural Worker | — | $10,000 - $15,000 per month | — | — |
| 12 | hkgov | Security Guard(Kowloon Tong) | — | $15,000 per month | Kowloon City | — |
| 13 | hkgov | Customer Services Officer | — | $18,459 - $19,570 per month | Yau Tsim Mong | — |
| 14 | hkgov | Security Guard | — | $8,586 - $11,178 per month | Eastern | — |
| 15 | hkgov | Building Attendant/Security Guard | — | $19,500 - $21,930 per month | Tsuen Wan | — |
| 16 | hkgov | Security Guard | — | $18,000 - $19,000 per month | Sai Kung | — |
| 17 | hkgov | Linen Supplies Assistant | — | $17,700 - $22,000 per month | — | — |
| 18 | hkgov | Carpark Officer (Airport) | — | $17,255 per month | — | — |
| 19 | hkgov | Cleaner | — | $13,500 - $14,800 per month | — | — |
| 20 | hkgov | Cleaner | — | $13,600 - $15,900 per month | — | — |

## Full JSON of the 20 records

```json
[
 {
  "job_id": "91ee310545d88a58",
  "source": "hkgov",
  "source_job_id": "12-26-0017498",
  "title": "Customer Due Diligence Officer (SME / Commercial Banking)",
  "company": null,
  "salary_raw": "$22,000 - $43,000 per month",
  "salary_min": 22000.0,
  "salary_max": 43000.0,
  "salary_period": "month",
  "locations_raw": [
   "H.K. Island"
  ],
  "districts": [],
  "anywhere_in_hk": false,
  "region_norm": "unknown",
  "posted_date_raw": null,
  "posted_date": null,
  "url": "https://www2.jobs.gov.hk/0/en/jobseeker/jobCard/?order=ODRnelBHUGNVWGNYZEhuNktTT1ptajZ6aTR1YjR0dmpRVjU5ZWJaSmtIST0%3D&from=quickview&for=fulltime_epem",
  "content_hash": "f828637d781d5f15fad8e0e954c4b3730d721ba344b3d403458e335c4ba0808b",
  "dedupe_key": "||customer due diligence officer sme commercial banking||unknown",
  "cluster_id": null,
  "first_seen_at": "2026-11-02T10:29:30+08:00",
  "last_seen_at": "2026-11-02T10:29:30+08:00",
  "salary_month_min": 22000.0,
  "salary_month_max": 43000.0
 },
 {
  "job_id": "c18f27493cf81b76",
  "source": "hkgov",
  "source_job_id": "11-26-0013604",
  "title": "Claims Executive (P&I and FD&D)(Asia Pacific)",
  "company": null,
  "salary_raw": "$60,000 - $90,000 per month",
  "salary_min": 60000.0,
  "salary_max": 90000.0,
  "salary_period": "month",
  "locations_raw": [
   "Wanchai,Overseas"
  ],
  "districts": [],
  "anywhere_in_hk": false,
  "region_norm": "unknown",
  "posted_date_raw": null,
  "posted_date": null,
  "url": "https://www2.jobs.gov.hk/0/en/jobseeker/jobCard/?order=cFpPV3F5cWFuL3pUMDBWZTI0cHpuaS9WWWJHcHY1OWRRdzNmTzFPQTdXST0%3D&from=quickview&for=fulltime_epem",
  "content_hash": "a0c5a05cb470d7dd5eaea72ec4d594a2dec906779be382dfd3629eae38efb162",
  "dedupe_key": "||claims executive p&i and fd&d asia pacific||unknown",
  "cluster_id": null,
  "first_seen_at": "2026-11-02T10:29:30+08:00",
  "last_seen_at": "2026-11-02T10:29:30+08:00",
  "salary_month_min": 60000.0,
  "salary_month_max": 90000.0
 },
 {
  "job_id": "efebf58c10bcba0f",
  "source": "hkgov",
  "source_job_id": "11-26-0013565",
  "title": "General Service Attendant",
  "company": null,
  "salary_raw": "$70 per hour",
  "salary_min": 70.0,
  "salary_max": null,
  "salary_period": "hour",
  "locations_raw": [
   "Tin Hau"
  ],
  "districts": [],
  "anywhere_in_hk": false,
  "region_norm": "unknown",
  "posted_date_raw": null,
  "posted_date": null,
  "url": "https://www2.jobs.gov.hk/0/en/jobseeker/jobCard/?order=cFpPV3F5cWFuL3cyYmsrUkUvZHJFbzBFcW5ITG9VWTI1enpETjRXdk5oUT0%3D&from=quickview&for=fulltime_epem",
  "content_hash": "504f1c58cf2047fd0dcb75e6bf616668b64f1719ddc02cb82dcb26e022e4ed3b",
  "dedupe_key": "||general service attendant||unknown",
  "cluster_id": null,
  "first_seen_at": "2026-11-02T10:29:30+08:00",
  "last_seen_at": "2026-11-02T10:29:30+08:00",
  "salary_month_min": 12320.0
 },
 {
  "job_id": "4303f81ee209ef31",
  "source": "hkgov",
  "source_job_id": "11-26-0013553",
  "title": "(Senior) Customer Service Asst. (Wanchai)(9 Hrs Day Shift)",
  "company": null,
  "salary_raw": "$17,000 - $19,000 per month",
  "salary_min": 17000.0,
  "salary_max": 19000.0,
  "salary_period": "month",
  "locations_raw": [
   "Wanchai"
  ],
  "districts": [
   "Wan Chai"
  ],
  "anywhere_in_hk": false,
  "region_norm": "Wan Chai",
  "posted_date_raw": null,
  "posted_date": null,
  "url": "https://www2.jobs.gov.hk/0/en/jobseeker/jobCard/?order=cFpPV3F5cWFuL3lNUWdzVUNGZEN6MVB2Q1ZmYUFjZHF2VENIQW5zUDNMRT0%3D&from=quickview&for=fulltime_epem",
  "content_hash": "0cb92f0520290f6e3223216012a27f219358afae59e42388e2408f7b3e39cf21",
  "dedupe_key": "||senior customer service asst wanchai 9 hrs day shift||Wan Chai",
  "cluster_id": null,
  "first_seen_at": "2026-11-02T10:29:30+08:00",
  "last_seen_at": "2026-11-02T10:29:30+08:00",
  "salary_month_min": 17000.0,
  "salary_month_max": 19000.0
 },
 {
  "job_id": "771bb19f635a985e",
  "source": "hkgov",
  "source_job_id": "32-26-0014666",
  "title": "Refrigeration / AC Mechanics / Technician (Intermediate)",
  "company": null,
  "salary_raw": "$25,000 - $39,000 per month",
  "salary_min": 25000.0,
  "salary_max": 39000.0,
  "salary_period": "month",
  "locations_raw": [
   "Anywhere in H.K."
  ],
  "districts": [],
  "anywhere_in_hk": true,
  "region_norm": "unknown",
  "posted_date_raw": null,
  "posted_date": null,
  "url": "https://www2.jobs.gov.hk/0/en/jobseeker/jobCard/?order=N0xBYU1xaUNxWXByNWNSU1hEakcxSzR6ZkhMdnZPWEY2RlNZUEZReUtNYz0%3D&from=quickview&for=fulltime_epem",
  "content_hash": "9a5b3670b7ba747105d120938dd2c8d4e216df24284125dd1acd982f2fa17ae2",
  "dedupe_key": "||refrigeration ac mechanics technician intermediate||unknown",
  "cluster_id": null,
  "first_seen_at": "2026-11-02T10:29:30+08:00",
  "last_seen_at": "2026-11-02T10:29:30+08:00",
  "salary_month_min": 25000.0,
  "salary_month_max": 39000.0
 },
 {
  "job_id": "602e6892a9c9da53",
  "source": "hkgov",
  "source_job_id": "11-26-0013652",
  "title": "Repair / Maintenance Technician",
  "company": null,
  "salary_raw": "$18,000 - $21,000 per month",
  "salary_min": 18000.0,
  "salary_max": 21000.0,
  "salary_period": "month",
  "locations_raw": [
   "Kln. Peninsula"
  ],
  "districts": [],
  "anywhere_in_hk": false,
  "region_norm": "unknown",
  "posted_date_raw": null,
  "posted_date": null,
  "url": "https://www2.jobs.gov.hk/0/en/jobseeker/jobCard/?order=cFpPV3F5cWFuL3pkNk4xS2JmYlI2NENEWGNrZHc2anl4aFNrT1J1VFVwUT0%3D&from=quickview&for=fulltime_epem",
  "content_hash": "ae2b4b4d1322c2b1eb78c2da125ef12abf50fdb2a4e08e8e9216b56146e00cbb",
  "dedupe_key": "||repair maintenance technician||unknown",
  "cluster_id": null,
  "first_seen_at": "2026-11-02T10:29:30+08:00",
  "last_seen_at": "2026-11-02T10:29:30+08:00",
  "salary_month_min": 18000.0,
  "salary_month_max": 21000.0
 },
 {
  "job_id": "758d1ec18c6dfb63",
  "source": "hkgov",
  "source_job_id": "23-26-0018454",
  "title": "Technician",
  "company": null,
  "salary_raw": "$21,500 - $23,600 per month",
  "salary_min": 21500.0,
  "salary_max": 23600.0,
  "salary_period": "month",
  "locations_raw": [
   "Kln. Bay"
  ],
  "districts": [],
  "anywhere_in_hk": false,
  "region_norm": "unknown",
  "posted_date_raw": null,
  "posted_date": null,
  "url": "https://www2.jobs.gov.hk/0/en/jobseeker/jobCard/?order=RDlOSnVRa0x1d2JmcmhVSmFISk1vMFlNMlR3dlJGenNFTEVnY3B6WXBPdz0%3D&from=quickview&for=fulltime_epem",
  "content_hash": "1117ff8d7a4cd194a4a1f1f6f9bcd091555e5615bd559db96e9091f9f129b4b3",
  "dedupe_key": "||technician||unknown",
  "cluster_id": null,
  "first_seen_at": "2026-11-02T10:29:30+08:00",
  "last_seen_at": "2026-11-02T10:29:30+08:00",
  "salary_month_min": 21500.0,
  "salary_month_max": 23600.0
 },
 {
  "job_id": "34d529a845c8309c",
  "source": "hkgov",
  "source_job_id": "11-26-0013651",
  "title": "Club Receptionist",
  "company": null,
  "salary_raw": "$16,000 - $17,000 per month",
  "salary_min": 16000.0,
  "salary_max": 17000.0,
  "salary_period": "month",
  "locations_raw": [
   "Happy Valley"
  ],
  "districts": [
   "Wan Chai"
  ],
  "anywhere_in_hk": false,
  "region_norm": "Wan Chai",
  "posted_date_raw": null,
  "posted_date": null,
  "url": "https://www2.jobs.gov.hk/0/en/jobseeker/jobCard/?order=cFpPV3F5cWFuL3dmMURxZnpkbGNJQmlBc1U2aVJhbnNjZ3NPQkxrZ3RGQT0%3D&from=quickview&for=fulltime_epem",
  "content_hash": "857519b4595906551fabd8a7558d53fe380e05653bb8860f64894aab19d183c0",
  "dedupe_key": "||club receptionist||Wan Chai",
  "cluster_id": null,
  "first_seen_at": "2026-11-02T10:29:30+08:00",
  "last_seen_at": "2026-11-02T10:29:30+08:00",
  "salary_month_min": 16000.0,
  "salary_month_max": 17000.0
 },
 {
  "job_id": "c084a63115dff902",
  "source": "hkgov",
  "source_job_id": "12-26-0017589",
  "title": "Workshop Assistant / Factory Assistant",
  "company": null,
  "salary_raw": "$16,500 - $20,000 per month",
  "salary_min": 16500.0,
  "salary_max": 20000.0,
  "salary_period": "month",
  "locations_raw": [
   "Chai Wan"
  ],
  "districts": [],
  "anywhere_in_hk": false,
  "region_norm": "unknown",
  "posted_date_raw": null,
  "posted_date": null,
  "url": "https://www2.jobs.gov.hk/0/en/jobseeker/jobCard/?order=ODRnelBHUGNVWGZFTHZTYjNVZHdVdTFmRGw5QXk4ZHBZcVlaVVZXN2RtYz0%3D&from=quickview&for=fulltime_epem",
  "content_hash": "526b447f5ec05e177b07c48bed8dde3cc2f70a46ccebdb9d30502915d71cb1d9",
  "dedupe_key": "||workshop assistant factory assistant||unknown",
  "cluster_id": null,
  "first_seen_at": "2026-11-02T10:29:30+08:00",
  "last_seen_at": "2026-11-02T10:29:30+08:00",
  "salary_month_min": 16500.0,
  "salary_month_max": 20000.0
 },
 {
  "job_id": "542e67eb135266e3",
  "source": "hkgov",
  "source_job_id": "32-26-0014662",
  "title": "Building Supervisor",
  "company": null,
  "salary_raw": "$24,000 - $26,000 per month",
  "salary_min": 24000.0,
  "salary_max": 26000.0,
  "salary_period": "month",
  "locations_raw": [
   "Ma On Shan"
  ],
  "districts": [
   "Sha Tin"
  ],
  "anywhere_in_hk": false,
  "region_norm": "Sha Tin",
  "posted_date_raw": null,
  "posted_date": null,
  "url": "https://www2.jobs.gov.hk/0/en/jobseeker/jobCard/?order=N0xBYU1xaUNxWXAyRFpzd0lCNnVhSERuOG40M3hrNTUzaEZIK0RiVUl4az0%3D&from=quickview&for=fulltime_epem",
  "content_hash": "aec5f7f60c57df6a4e0d6e4be6b3fe4a396b07d1a75940a8d778977ffaf45560",
  "dedupe_key": "||building supervisor||Sha Tin",
  "cluster_id": null,
  "first_seen_at": "2026-11-02T10:29:30+08:00",
  "last_seen_at": "2026-11-02T10:29:30+08:00",
  "salary_month_min": 24000.0,
  "salary_month_max": 26000.0
 },
 {
  "job_id": "940a1d08e53809dc",
  "source": "hkgov",
  "source_job_id": "32-26-0014661",
  "title": "Horticultural Worker",
  "company": null,
  "salary_raw": "$10,000 - $15,000 per month",
  "salary_min": 10000.0,
  "salary_max": 15000.0,
  "salary_period": "month",
  "locations_raw": [
   "Anywhere in H.K."
  ],
  "districts": [],
  "anywhere_in_hk": true,
  "region_norm": "unknown",
  "posted_date_raw": null,
  "posted_date": null,
  "url": "https://www2.jobs.gov.hk/0/en/jobseeker/jobCard/?order=N0xBYU1xaUNxWXJpb0pDQTFYSG8vZy9GT2ZaNElGZWJvbWViSU84OUpvZz0%3D&from=quickview&for=fulltime_epem",
  "content_hash": "cdb1f6232d221bcf3355986b591b559cccbb9a84db0e19fbc592ab647b5ae0cd",
  "dedupe_key": "||horticultural worker||unknown",
  "cluster_id": null,
  "first_seen_at": "2026-11-02T10:29:30+08:00",
  "last_seen_at": "2026-11-02T10:29:30+08:00",
  "salary_month_min": 10000.0,
  "salary_month_max": 15000.0
 },
 {
  "job_id": "89cee532468a8325",
  "source": "hkgov",
  "source_job_id": "23-26-0018344",
  "title": "Security Guard(Kowloon Tong)",
  "company": null,
  "salary_raw": "$15,000 per month",
  "salary_min": 15000.0,
  "salary_max": null,
  "salary_period": "month",
  "locations_raw": [
   "Kln. Tong"
  ],
  "districts": [
   "Kowloon City"
  ],
  "anywhere_in_hk": false,
  "region_norm": "Kowloon City",
  "posted_date_raw": null,
  "posted_date": null,
  "url": "https://www2.jobs.gov.hk/0/en/jobseeker/jobCard/?order=RDlOSnVRa0x1d1p1K2FrVGJIWHAwb2h3WkZ1UHNXaCtBd2dkNE5ORWpWaz0%3D&from=quickview&for=fulltime_epem",
  "content_hash": "c247a133c96c8545023106dd9ffd2394cafa4826158e78336c2f711e4b03affc",
  "dedupe_key": "||security guard kowloon tong||Kowloon City",
  "cluster_id": null,
  "first_seen_at": "2026-11-02T10:29:30+08:00",
  "last_seen_at": "2026-11-02T10:29:30+08:00",
  "salary_month_min": 15000.0
 },
 {
  "job_id": "167f96f78b88753a",
  "source": "hkgov",
  "source_job_id": "22-26-0021547",
  "title": "Customer Services Officer",
  "company": null,
  "salary_raw": "$18,459 - $19,570 per month",
  "salary_min": 18459.0,
  "salary_max": 19570.0,
  "salary_period": "month",
  "locations_raw": [
   "Tai Wai,Tsuen Wan,West Kowloon Station/ Austin Station,Wu Kai Sha"
  ],
  "districts": [
   "Yau Tsim Mong"
  ],
  "anywhere_in_hk": false,
  "region_norm": "Yau Tsim Mong",
  "posted_date_raw": null,
  "posted_date": null,
  "url": "https://www2.jobs.gov.hk/0/en/jobseeker/jobCard/?order=TlpZMGdHM1NLaVZrN2NLa3Z4bXRTL2dlS3licVQ2TXBIcUs4SG5RaWxGRT0%3D&from=quickview&for=fulltime_epem",
  "content_hash": "7d1ec5bc0367d6dfb181bc160347f9d4f10b41a2cf14986d241e68d3c28f14d6",
  "dedupe_key": "||customer services officer||Yau Tsim Mong",
  "cluster_id": null,
  "first_seen_at": "2026-11-02T10:29:30+08:00",
  "last_seen_at": "2026-11-02T10:29:30+08:00",
  "salary_month_min": 18459.0,
  "salary_month_max": 19570.0
 },
 {
  "job_id": "98c8feb65552f66d",
  "source": "hkgov",
  "source_job_id": "22-26-0021544",
  "title": "Security Guard",
  "company": null,
  "salary_raw": "$8,586 - $11,178 per month",
  "salary_min": 8586.0,
  "salary_max": 11178.0,
  "salary_period": "month",
  "locations_raw": [
   "Central,North Point,Wanchai,Kennedy Town,Kwun Tong,Cheung Chau"
  ],
  "districts": [
   "Eastern"
  ],
  "anywhere_in_hk": false,
  "region_norm": "Eastern",
  "posted_date_raw": null,
  "posted_date": null,
  "url": "https://www2.jobs.gov.hk/0/en/jobseeker/jobCard/?order=TlpZMGdHM1NLaVdYaTlFZnBZazFpenlrRzIwRzI4SWlEcGNtSDlnbmZYND0%3D&from=quickview&for=fulltime_epem",
  "content_hash": "6cf15ebb516f2f754ef2b326485e3503bd84f9e6cfa96c3199e19501ff6a2bda",
  "dedupe_key": "||security guard||Eastern",
  "cluster_id": null,
  "first_seen_at": "2026-11-02T10:29:30+08:00",
  "last_seen_at": "2026-11-02T10:29:30+08:00",
  "salary_month_min": 8586.0,
  "salary_month_max": 11178.0
 },
 {
  "job_id": "b6b7eba99fde205a",
  "source": "hkgov",
  "source_job_id": "22-26-0021541",
  "title": "Building Attendant/Security Guard",
  "company": null,
  "salary_raw": "$19,500 - $21,930 per month",
  "salary_min": 19500.0,
  "salary_max": 21930.0,
  "salary_period": "month",
  "locations_raw": [
   "Tai Koo,Tai Wai,Kam Tin,Tsuen Wan West,Wu Kai Sha"
  ],
  "districts": [
   "Tsuen Wan"
  ],
  "anywhere_in_hk": false,
  "region_norm": "Tsuen Wan",
  "posted_date_raw": null,
  "posted_date": null,
  "url": "https://www2.jobs.gov.hk/0/en/jobseeker/jobCard/?order=TlpZMGdHM1NLaVVMTTNFUWNBNm5lUEhFY2dCSUdIUmRUNjNYVW9vT2tMZz0%3D&from=quickview&for=fulltime_epem",
  "content_hash": "1569a5e5e4eabad66d3195d1a5a77c6f165163bcbf338aeee0aebd0b95204db6",
  "dedupe_key": "||building attendant security guard||Tsuen Wan",
  "cluster_id": null,
  "first_seen_at": "2026-11-02T10:29:30+08:00",
  "last_seen_at": "2026-11-02T10:29:30+08:00",
  "salary_month_min": 19500.0,
  "salary_month_max": 21930.0
 },
 {
  "job_id": "016afb6fdfc82821",
  "source": "hkgov",
  "source_job_id": "22-26-0021539",
  "title": "Security Guard",
  "company": null,
  "salary_raw": "$18,000 - $19,000 per month",
  "salary_min": 18000.0,
  "salary_max": 19000.0,
  "salary_period": "month",
  "locations_raw": [
   "Shau Kei Wan,Aberdeen,Hung Hom,Tseung Kwan O,Tsing Yi,Shatin"
  ],
  "districts": [
   "Sai Kung"
  ],
  "anywhere_in_hk": false,
  "region_norm": "Sai Kung",
  "posted_date_raw": null,
  "posted_date": null,
  "url": "https://www2.jobs.gov.hk/0/en/jobseeker/jobCard/?order=TlpZMGdHM1NLaVhnUnNiRUxzcUVHbVZMcUpocUxOTHFmYkhFNFV1R09vMD0%3D&from=quickview&for=fulltime_epem",
  "content_hash": "2b8440823240c3e53677f2a08e4257faed2a7c554cc41731887542e0cc1fe257",
  "dedupe_key": "||security guard||Sai Kung",
  "cluster_id": null,
  "first_seen_at": "2026-11-02T10:29:30+08:00",
  "last_seen_at": "2026-11-02T10:29:30+08:00",
  "salary_month_min": 18000.0,
  "salary_month_max": 19000.0
 },
 {
  "job_id": "a7fc52da99f86af3",
  "source": "hkgov",
  "source_job_id": "11-26-0013613",
  "title": "Linen Supplies Assistant",
  "company": null,
  "salary_raw": "$17,700 - $22,000 per month",
  "salary_min": 17700.0,
  "salary_max": 22000.0,
  "salary_period": "month",
  "locations_raw": [
   "Mid-levels"
  ],
  "districts": [],
  "anywhere_in_hk": false,
  "region_norm": "unknown",
  "posted_date_raw": null,
  "posted_date": null,
  "url": "https://www2.jobs.gov.hk/0/en/jobseeker/jobCard/?order=cFpPV3F5cWFuL3gwcEFodlhyK3NIajcxRmw3ZVMzVUo5STg0VjVvOVRCRT0%3D&from=quickview&for=fulltime_epem",
  "content_hash": "6a0e5774baa0898b8b9d0ae6b16724cc9cf019de8a51a65b5f74b055edbf7104",
  "dedupe_key": "||linen supplies assistant||unknown",
  "cluster_id": null,
  "first_seen_at": "2026-11-02T10:29:30+08:00",
  "last_seen_at": "2026-11-02T10:29:30+08:00",
  "salary_month_min": 17700.0,
  "salary_month_max": 22000.0
 },
 {
  "job_id": "fba849d5e1b333d0",
  "source": "hkgov",
  "source_job_id": "37-26-0003766",
  "title": "Carpark Officer (Airport)",
  "company": null,
  "salary_raw": "$17,255 per month",
  "salary_min": 17255.0,
  "salary_max": null,
  "salary_period": "month",
  "locations_raw": [
   "Chek Lap Kok"
  ],
  "districts": [],
  "anywhere_in_hk": false,
  "region_norm": "unknown",
  "posted_date_raw": null,
  "posted_date": null,
  "url": "https://www2.jobs.gov.hk/0/en/jobseeker/jobCard/?order=SXBRUVhOeC9RRW1RYnhUMHdDMkVPZ3RMQ05wM1hXSndMVG4rbW1HR09waz0%3D&from=quickview&for=fulltime_epem",
  "content_hash": "115f83bd3852c269051602ffba730278f206885049890a070c8741c957e8435c",
  "dedupe_key": "||carpark officer airport||unknown",
  "cluster_id": null,
  "first_seen_at": "2026-11-02T10:29:30+08:00",
  "last_seen_at": "2026-11-02T10:29:30+08:00",
  "salary_month_min": 17255.0
 },
 {
  "job_id": "16602f2fe4e769dd",
  "source": "hkgov",
  "source_job_id": "37-26-0003772",
  "title": "Cleaner",
  "company": null,
  "salary_raw": "$13,500 - $14,800 per month",
  "salary_min": 13500.0,
  "salary_max": 14800.0,
  "salary_period": "month",
  "locations_raw": [
   "Chek Lap Kok"
  ],
  "districts": [],
  "anywhere_in_hk": false,
  "region_norm": "unknown",
  "posted_date_raw": null,
  "posted_date": null,
  "url": "https://www2.jobs.gov.hk/0/en/jobseeker/jobCard/?order=SXBRUVhOeC9RRW5mN3pqN3ZJNEF0aUtXOEFTeEgvQWZlWEF0VE14VWM2TT0%3D&from=quickview&for=fulltime_epem",
  "content_hash": "564c3363b41182caae415aa8a5cbec4b152722067a13de4da3463b45a33c4c42",
  "dedupe_key": "||cleaner||unknown",
  "cluster_id": null,
  "first_seen_at": "2026-11-02T10:29:30+08:00",
  "last_seen_at": "2026-11-02T10:29:30+08:00",
  "salary_month_min": 13500.0,
  "salary_month_max": 14800.0
 },
 {
  "job_id": "35a94a88131bfc7c",
  "source": "hkgov",
  "source_job_id": "37-26-0003773",
  "title": "Cleaner",
  "company": null,
  "salary_raw": "$13,600 - $15,900 per month",
  "salary_min": 13600.0,
  "salary_max": 15900.0,
  "salary_period": "month",
  "locations_raw": [
   "Chek Lap Kok"
  ],
  "districts": [],
  "anywhere_in_hk": false,
  "region_norm": "unknown",
  "posted_date_raw": null,
  "posted_date": null,
  "url": "https://www2.jobs.gov.hk/0/en/jobseeker/jobCard/?order=SXBRUVhOeC9RRWxBOTNGT2VYS3FTdlZXb2JPY2FhWUdjN2gzM3RDR2w3ST0%3D&from=quickview&for=fulltime_epem",
  "content_hash": "25f96030099068072895edc8f230370d452d1b7380df36738815bcfbd3f10a85",
  "dedupe_key": "||cleaner||unknown",
  "cluster_id": null,
  "first_seen_at": "2026-11-02T10:29:30+08:00",
  "last_seen_at": "2026-11-02T10:29:30+08:00",
  "salary_month_min": 13600.0,
  "salary_month_max": 15900.0
 }
]
```
