from SRC.posterior_loader import load_posterior_scenarios
from SRC.ideology_loader import load_ideology_prior

posterior = load_posterior_scenarios()
ideology = load_ideology_prior()

print()
print("POSTERIOR SCENARIOS")
print("Count:", len(posterior))

for i, item in enumerate(posterior.items()):
    print(item)
    if i >= 5:
        break

print()
print("IDEOLOGY PRIOR")
print(ideology)