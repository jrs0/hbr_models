import os
os.chdir("scripts/prototypes")

import save_datasets as ds

import importlib
importlib.reload(ds)

import matplotlib.pyplot as plt
import seaborn as sns
sns.set_theme()

df = ds.load_dataset("manual_codes", False)

df["mace"] = df["hussain_ami_stroke_outcome"] | df["all_cause_death_outcome"]

bleeding_prop = df[["bleeding_al_ani_outcome"]].mean()
ami_stroke_prop = df[["hussain_ami_stroke_outcome"]].mean()

df.rename(columns={"dem_age": "Age at index", "idx_stemi": "STEMI"}, inplace=True)

# Plot of the age distribution by stemi/nstemi
sns.displot(data=df, x="Age at index", hue="STEMI", bins=30).set(title='Proportion of STEMI and NSTEMI by age')
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