# PriorAI Integration Test Results

**Last Run**: 2026-03-22 20:35:41

## Pass 1: ID-Only Results

| Patient ID | Status | Recommendation | Denial Risk Score |
|------------|--------|----------------|-------------------|
| 1000 | Pass | NEEDS_REVIEW | 0.85 |
| 1256 | Pass | NEEDS_REVIEW | 0.85 |
| 1958 | Pass | NEEDS_REVIEW | 0.85 |
| 2735 | Fail | N/A | N/A |
| 4440 | Fail | N/A | N/A |

## Pass 2: Multimodal Results

| Patient ID | Status | MM Consumed | Recommendation | Denial Risk Score |
|------------|--------|-------------|----------------|-------------------|
| 1000 | Pass | Yes | APPROVE | 0.21 |
| 1256 | Pass | Yes | NEEDS_REVIEW | 0.42 |
| 1958 | Pass | Yes | NEEDS_REVIEW | 0.408 |
