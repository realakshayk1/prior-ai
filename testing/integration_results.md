# PriorAI Integration Test Results

**Last Run**: 2026-03-23 12:44:53

## Pass 1: ID-Only Results

| Patient ID | Status | Decision | Denial Risk Score |
|------------|--------|----------------|-------------------|
| 1000 | Pass | NEEDS_REVIEW | 0.95 |
| 1256 | Pass | DENY | 0.95 |
| 1512 | Pass | DENY | 0.95 |
| 2214 | Pass | DENY | 0.95 |
| 2991 | Pass | NEEDS_REVIEW | 0.85 |

## Pass 2: Multimodal Results

| Patient ID | Status | MM Consumed | Decision | Denial Risk Score |
|------------|--------|-------------|----------------|-------------------|
| 1000 | Pass | Yes | NEEDS_REVIEW | 0.85 |
| 1256 | Pass | Yes | DENY | 0.95 |
| 1512 | Pass | Yes | NEEDS_REVIEW | 0.95 |
