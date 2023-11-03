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

# Plot of the age distribution by stemi/nstemi
fig, ax = plt.subplots(figsize=(5,4.5))
df_age_stemi = df[df["idx_stemi"] == True]["dem_age"]
df_age_nstemi = df[df["idx_stemi"] == False]["dem_age"]
ax.hist(df_age_stemi, 30, alpha=0.5, label='STEMI')
ax.hist(df_age_nstemi, 30, alpha=0.5, label='NSTEMI')
ax.legend(loc='upper left')
ax.set_xlabel("Age at index")
ax.set_ylabel("Count in age range")
plt.show()

pyplot.hist(y, bins, alpha=0.5, label='NSTEMI')

# Plot of the correlations between outcome columns
outcomes = df.filter()
outcomes.columns = outcomes.columns.str.replace("_outcome", "")
corr = df.corr()

plt.matshow(corr)
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