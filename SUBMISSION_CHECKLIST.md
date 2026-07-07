# Submission checklist — AMD Developer Hackathon ACT II (lablab.ai)

**Deadline: July 11, 2026, 9:00 AM PDT.** Track 3 (Unicorn) + "Best AMD-Hosted Gemma".
Team: Conjecture Hunters. Repo: https://github.com/Hawhaz/conjecture-hunters

## Required deliverables (lablab.ai submission form)

| # | Requirement | Status | Notes / action |
|---|-------------|--------|----------------|
| 1 | **Public GitHub repo** | ✅ done | Full commit history, README, LICENSE (MIT), Dockerfile. |
| 2 | **Containerized** (mandatory) | ✅ done | `docker build` green (full pytest passes inside); `docker run conjecture-hunters` runs the demo. Verified. |
| 3 | **Slides / pitch deck (PDF)** | ⚠️ pending export | Deck exists: `entrega/Conjecture_Hunters.pptx`. **Export to PDF** for the form. |
| 4 | **Video presentation** (2–3 min) | ❌ to record | Script deferred by owner; must record before deadline. Show: problem → AlphaEvolve-on-AMD system → Jia-Song refutation (exact) → 20-lane swarm + ledger → Gemma on MI300X. |
| 5 | **Application URL / working demo online** | ⚠️ decide | Prototype is the runnable container (`docker run ...`) + repo. Options for the URL: the GitHub repo, a hosted `dashboard/` page, or a Hugging Face Space running the demo. Pick one and paste it. |
| 6 | **Title, description, tags, cover image** | ⚠️ provide | Draft below. Cover image: can reuse a deck slide / the F2 motif. |
| 7 | **Signed up to AMD AI Developer Program** | ✅ done | Account active (team-3592); MI300X access via notebooks.amd.com. |

## Judging criteria (make sure each is evidenced)

- **Uniqueness / creativity** — ✅ AlphaEvolve-style refutation of open spectral-graph conjectures with an *un-gameable exact certificate*; not a chatbot/RAG clone.
- **Startup / product vision** — ✅ an automated "conjecture-refutation engine" (math discovery infra). Deck covers it.
- **Fully realized / functional** — ✅ 20 validated lanes (tests green), durable hit-ledger, swarm saturating CPU, exact certificates, one **real refuted+improved open conjecture (Jia-Song)**, Docker verified.
- **AMD infrastructure meaningfully incorporated** — ⚠️ **strongest gap.** Built: `deploy/run_gpu.sh` (Gemma on MI300X via vLLM), `RUNBOOK_MI300X.md`, LoRA on ROCm, `GPU_SESSION_LOG.md` (documents MI300X access). **Action: complete at least ONE Gemma-on-MI300X run** (GPU currently "unavailable" on the portal; retry until a slot frees) so the "Best AMD-Hosted Gemma" prize + this criterion are fully evidenced.

## Draft submission text

- **Title:** Conjecture Hunters — an evolutionary engine that refutes open graph-theory conjectures on AMD.
- **Short description:** Gemma (hosted on AMD MI300X) proposes graphs; a Rust + exact-arithmetic evaluator certifies them. The system refuted *and* improved an open 2018 spectral-graph conjecture (Jia-Song), runs a 20-conjecture parallel swarm with a crash-proof hit-ledger, and re-discovers SOTA counterexamples in seconds.
- **Tags:** spectral graph theory, AlphaEvolve, Gemma, AMD MI300X, ROCm, vLLM, LoRA, automated conjecture refutation.

## Remaining before submit
- [ ] Export deck to PDF.
- [ ] Record 2–3 min video.
- [ ] Complete one Gemma-on-MI300X run (AMD infra evidence + prize).
- [ ] Decide the "application URL" (repo / dashboard / HF Space).
- [ ] Fill the lablab.ai form (title, desc, tags, cover, links).
