# Trade-offs (Current)

## Why mock analyzer is default
`AI_PROVIDER=mock` is the default for demo reliability. The architecture treats the analyzer as a pluggable dependency; provider instability should not break the interview demo.

## How provider flips
Set:
- `AI_PROVIDER=claude`
- `ANTHROPIC_API_KEY=<value>`

Plan:
- Validate Claude path end-to-end locally at least once
- Commit VCR cassette for CI contract tests to avoid token spend
