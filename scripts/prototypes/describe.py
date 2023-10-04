import os
os.chdir("scripts/prototypes")

import save_datasets as ds

import importlib
importlib.reload(ds)

import matplotlib.pyplot as plt
import seaborn as sns
sns.set_theme()

df = ds.load_dataset_interactive("hes_code_groups_dataset")

df["mace"] = df["hussain_ami_stroke_outcome"] | df["all_cause_death_outcome"]

# Plot of the age distribution by stemi/nstemi
sns.displot(data=df, x="dem_age", hue="idx_stemi", bins=30)
plt.show()

# Plot of the correlations between outcome columns
outcomes = df.filter(regex="outcome")
outcomes.columns = outcomes.columns.str.replace("_outcome", "")
corr = outcomes.corr()
sns.heatmap(corr,xticklabels=True, yticklabels=True)
plt.tight_layout()
plt.show()

# Show correlations between index features (i.e. not prior code counts)
idx_features = df.filter(regex="(dem|idx)")
idx_features.columns = idx_features.columns.str.replace("(idx_|dem_)", "", regex=True)
corr = idx_features.corr()
sns.heatmap(corr,xticklabels=True, yticklabels=True)
plt.tight_layout()
plt.show()

# Show correlations between index features (i.e. not prior code counts)
idx_features = df.filter(regex="(dem|idx)")
idx_features.columns = idx_features.columns.str.replace("(idx_|dem_)", "", regex=True)
corr = df.corr()
sns.heatmap(corr,xticklabels=True, yticklabels=True)
plt.tight_layout()
plt.show()