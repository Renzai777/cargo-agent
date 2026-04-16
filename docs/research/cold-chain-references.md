# Research References — Pharmaceutical Cold Chain

## Regulatory Standards (Public Sources)

| Standard | Description | Key Thresholds |
|----------|-------------|----------------|
| WHO Good Distribution Practice (GDP) | International cold-chain guidelines | Vaccines: 2–8°C; Frozen: -20°C |
| FDA 21 CFR Part 211 | US pharmaceutical manufacturing/distribution | Temperature excursion documentation required |
| FDA 21 CFR Part 11 | Electronic records/signatures | Audit trail format for automated systems |
| ICH Q10 | Pharmaceutical Quality System | Risk management framework |
| EU GDP Guidelines 2013/C 343/01 | European GDP for medicinal products | Qualified Person for Distribution |

## Vaccine Temperature Sensitivity (Public Data)

| Vaccine Type | Safe Temp Range | Max Excursion Duration |
|-------------|----------------|----------------------|
| Live attenuated (MMR, Varicella) | 2–8°C | 2 hours above 8°C |
| Inactivated (Flu, Hepatitis A) | 2–8°C | 24 hours cumulative |
| mRNA (COVID-19) | -90°C to -60°C (Pfizer) or -25°C to -15°C (Moderna) | <12 hours at 2–8°C |
| Oral Polio | 2–8°C or frozen | Very sensitive — discard if frozen |

## Key Data Points for Synthetic Generation

- Average NYC → Nairobi flight time: ~17 hours (with Frankfurt hub)
- Frankfurt customs average clearance: 2–6 hours
- Cold storage facilities: every major international airport
- DHL Pharma cold-chain container: logs every 5 minutes
- Insurance claim typical threshold: >$10,000 product loss

## LangGraph Resources

- LangGraph docs: https://langchain-ai.github.io/langgraph/
- interrupt_before HITL: https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/
- Send API for parallel nodes: https://langchain-ai.github.io/langgraph/how-tos/map-reduce/
- SQLite checkpointer: https://langchain-ai.github.io/langgraph/how-tos/persistence/

## Synthetic Data Generation Strategy

1. **Normal telemetry:** `numpy.random.normal(mean=4.5, std=0.3)` for vaccine temp
2. **Anomaly injection:** Step function or ramp up from baseline
3. **Route simulation:** Linear interpolation between GPS waypoints
4. **Customs hold:** Deterministic injection at step 15-20 of simulation
5. **Hospital schedules:** Claude generates 20 synthetic appointment records per facility
6. **Weather/delay events:** Random Poisson process, ~2 events per route
