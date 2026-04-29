# Add a new Engine tool

## Steps

1. **Spec.** Brief — function signature, return shape, the question it answers,
   when the LLM should pick it over alternatives.
2. **Define typed return models.** Pydantic v2 in `engine/<module>/tools.py`.
3. **Implement the tool.**
   ```python
   @engine_tool(
       name="get_xyz",
       module="<module>",
       description="<for the LLM tool catalog — be specific about when to use>",
       cost_class="cheap",
   )
   def get_xyz(...) -> EngineResult[Xyz]:
       ...
   ```
4. **Reads only Tier-2 and Tier-3.** No HTTP. No LLM calls (except the briefing
   composer, which is its own carve-out).
5. **Idempotent + deterministic.** Same params at same `as_of_date` → same result.
6. **Source refs.** Populate `EngineResult.sources` with `SourceRef` entries
   linking back to Tier-1 raw rows.
7. **Tests.** Unit tests covering: happy path, empty input, oversized input,
   missing data, boundary dates (weekends, holidays, very old, very new).
8. **Eval.** Add a fixture to `evals/citation_discipline/` if the tool produces
   numbers that the LLM will cite.

## Discipline

- Tool descriptions are read by the LLM. Write them like API docs for a smart
  intern who has not seen this codebase.
- Cost-class accurate: "cheap" (single indexed read), "moderate" (joins or LLM),
  "expensive" (multi-table aggregation).
- Don't expose a tool that returns more than 1000 rows; truncate or paginate.
